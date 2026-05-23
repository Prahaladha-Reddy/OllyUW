from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import HTTPException

from src.config import get_settings
from src.models.file import FileRecord, FileStatus
from src.models.message import Message, MessageRole, MessagesListResponse, SendMessageResponse
from src.providers import e2b_provider, storage_provider
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.file_repository import FileRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.session_repository import SessionRepository

logger = logging.getLogger("ollyuw.session")


def _to_message_model(row: dict) -> Message:
    return Message(
        id=row["id"],
        conversation_id=row["conversation_id"],
        role=row["role"],
        content=row["content"],
        citations=row.get("citations"),
        created_at=row["created_at"],
    )


class SessionService:
    """
    One instance per request. Holds repos + a Redis client.
    Stateless across requests — sandbox handles live in e2b_provider.
    """

    def __init__(
        self,
        *,
        conversation_repo: ConversationRepository,
        file_repo: FileRepository,
        message_repo: MessageRepository,
        session_repo: SessionRepository,
        redis: aioredis.Redis,
    ) -> None:
        self._conversations = conversation_repo
        self._files = file_repo
        self._messages = message_repo
        self._sessions = session_repo
        self._redis = redis


    async def list_messages(
        self, user_id: str, project_id: str, conversation_id: str,
    ) -> MessagesListResponse:
        await self._require_conversation(user_id, project_id, conversation_id)
        rows = await asyncio.to_thread(
            self._messages.list_for_conversation, user_id, conversation_id
        )
        return MessagesListResponse(messages=[_to_message_model(r) for r in rows])

    async def send_message(
        self, user_id: str, project_id: str, conversation_id: str, text: str,
    ) -> SendMessageResponse:
        conv = await self._require_conversation(user_id, project_id, conversation_id)

        # Persist the user message immediately so history is durable even if
        # the sandbox creation below fails.
        user_msg_row = await asyncio.to_thread(
            self._messages.append,
            user_id=user_id,
            conversation_id=conversation_id,
            role=MessageRole.USER.value,
            content=text,
        )

        session_id = await self._ensure_session(user_id, project_id, conv)

        # Reset idle timer
        sandbox = await e2b_provider.get(session_id)
        if sandbox is not None:
            await asyncio.to_thread(e2b_provider.extend_timeout, sandbox)

        # Push to the worker's input stream
        queued_id = await self._sessions.enqueue_message(session_id, text)

        return SendMessageResponse(message=_to_message_model(user_msg_row), queued_id=queued_id)

    async def stream(
        self, user_id: str, project_id: str, conversation_id: str,
    ) -> AsyncGenerator[str, None]:
        """SSE generator. Bridges Redis Pub/Sub → browser."""
        conv = await self._require_conversation(user_id, project_id, conversation_id)

        if not conv.get("session_id"):
            # No live session yet — nothing to stream. Emit a hint and close.
            yield f"data: {json.dumps({'type': 'no_session'})}\n\n"
            return

        session_id = conv["session_id"]
        channel = f"agent:{session_id}:chunks"
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)

        hello = json.dumps({"type": "stream_connected", "session_id": session_id})
        yield f"data: {hello}\n\n"

        try:
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
                if msg is None:
                    yield f"data: {json.dumps({'type': 'sse_heartbeat'})}\n\n"
                    continue

                data = msg.get("data", "")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")

                # Persist final agent answers to history (best-effort, fire-and-forget)
                try:
                    parsed = json.loads(data)
                    if parsed.get("type") == "final":
                        asyncio.create_task(self._persist_final(user_id, conversation_id, parsed))
                except Exception:
                    pass

                yield f"data: {data}\n\n"
                await asyncio.sleep(0)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


    async def push_files_to_sandbox(
        self,
        user_id: str,
        project_id: str,
        conversation_id: str,
        file_records: list[FileRecord],
    ) -> None:
        """After a mid-conversation upload, push new files into the running sandbox."""
        conv = await self._require_conversation(user_id, project_id, conversation_id)
        session_id = conv.get("session_id")
        if not session_id:
            return  # No sandbox yet — files will be materialized at session start

        sandbox = await e2b_provider.get(session_id)
        if sandbox is None:
            return  # Stale session — will be recreated on next message

        workspace: dict[str, bytes] = {}
        for record in file_records:
            if record.status != FileStatus.READY or not record.storage_path:
                continue
            try:
                workspace[record.original_name] = await asyncio.to_thread(
                    storage_provider.download, record.storage_path
                )
            except Exception as exc:
                logger.warning("could not download %s for sandbox push: %s", record.storage_path, exc)

        if workspace:
            await asyncio.to_thread(e2b_provider.upload_raw_files, sandbox, workspace)

    async def _require_conversation(
        self, user_id: str, project_id: str, conversation_id: str,
    ) -> dict:
        row = await asyncio.to_thread(
            self._conversations.get, user_id, project_id, conversation_id
        )
        if row is None:
            raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
        return row

    async def _ensure_session(self, user_id: str, project_id: str, conv: dict) -> str:
        """Return a live session_id for this conversation. Create one if needed."""
        existing = conv.get("session_id")
        if existing:
            sandbox = await e2b_provider.get(existing)
            if sandbox is not None:
                return existing
            # Session id is stale (server restart or sandbox died). Fall through to recreate.
            logger.info("conversation %s has stale session %s — recreating", conv["id"], existing)

        return await self._start_session(user_id, project_id, conv["id"])

    async def _start_session(self, user_id: str, project_id: str, conversation_id: str) -> str:
        settings = get_settings()
        session_id = str(uuid.uuid4())

        envs = {
            "SESSION_ID": session_id,
            "REDIS_URL": settings.redis.url,
            "INPUT_STREAM": f"agent:{session_id}:messages",
            "OUTPUT_CHANNEL": f"agent:{session_id}:chunks",
            "HEARTBEAT_KEY": f"agent:{session_id}:heartbeat",
            "WORKSPACE": "/home/user/workspace",
            "MODAL_TURBO_BASE_URL": settings.modal.turbo_base_url,
            "MODAL_STANDARD_BASE_URL": settings.modal.standard_base_url,
            "MODAL_API_KEY": settings.modal.api_key,
            "MODAL_MODEL": settings.modal.model,
            "DEEPSEEK_API_KEY": settings.deepseek.api_key,
            "DEEPSEEK_BASE_URL": settings.deepseek.base_url,
            "DEEPSEEK_MODEL": settings.deepseek.model,
            "LANGSMITH_API_KEY": settings.langsmith.api_key,
            "LANGSMITH_ENDPOINT": settings.langsmith.base_url,
            "LANGCHAIN_TRACING_V2": str(settings.langsmith.tracing).lower(),
        }

        sandbox, sandbox_id = await asyncio.to_thread(e2b_provider.create_sandbox, envs)
        logger.info("started sandbox %s for conversation %s", sandbox_id, conversation_id)

        # Materialise project files into the sandbox workspace (raw bytes — no conversion)
        file_rows = await asyncio.to_thread(
            self._files.list_ready_for_project, user_id, project_id
        )
        workspace: dict[str, bytes] = {}
        for row in file_rows:
            try:
                workspace[row["original_name"]] = await asyncio.to_thread(
                    storage_provider.download, row["storage_path"]
                )
            except Exception as exc:
                logger.warning("could not download %s: %s", row["storage_path"], exc)
        if workspace:
            await asyncio.to_thread(e2b_provider.upload_raw_files, sandbox, workspace)

        await e2b_provider.register(session_id, sandbox)
        await asyncio.to_thread(
            self._conversations.update_session_id, user_id, conversation_id, session_id
        )
        return session_id

    async def _persist_final(self, user_id: str, conversation_id: str, event: dict) -> None:
        try:
            await asyncio.to_thread(
                self._messages.append,
                user_id=user_id,
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT.value,
                content=str(event.get("text", "")),
                citations=event.get("citations"),
            )
        except Exception as exc:
            logger.warning("failed to persist final message: %s", exc)
