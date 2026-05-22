from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

import redis.asyncio as aioredis

from src.models.session import (
    ChatResponse,
    CreateSessionResponse,
    FilesResponse,
    SessionMeta,
    SessionStatus,
    SessionStatusResponse,
)
from src.providers import e2b_provider
from src.repositories.session_repository import SessionRepository


class SessionService:
    def __init__(self, repo: SessionRepository, redis: aioredis.Redis) -> None:
        self._repo = repo
        self._redis = redis

    async def create_session(self) -> CreateSessionResponse:
        sandbox, sandbox_id = await asyncio.to_thread(e2b_provider.create_sandbox)

        session = SessionMeta(
            session_id=sandbox_id,  # use sandbox_id as session_id for simplicity
            sandbox_id=sandbox_id,
            input_stream=f"agent:{sandbox_id}:messages",
            output_channel=f"agent:{sandbox_id}:chunks",
            heartbeat_key=f"agent:{sandbox_id}:heartbeat",
            status=SessionStatus.CREATING,
        )

        # Persist before starting worker (worker publishes immediately)
        await self._repo.save(session)

        e2b_provider.register(session.session_id, sandbox)
        await asyncio.to_thread(e2b_provider.upload_and_start_worker, sandbox, session)

        await self._repo.update_status(session.session_id, SessionStatus.READY)

        return CreateSessionResponse(
            session_id=session.session_id,
            sandbox_id=session.sandbox_id,
            input_stream=session.input_stream,
            output_channel=session.output_channel,
        )

    async def send_message(self, session_id: str, message: str) -> ChatResponse:
        session = await self._repo.get(session_id)
        if session is None:
            raise KeyError(session_id)

        # Reset the sandbox idle timer on every user message so the sandbox
        # doesn't die out from under an active conversation.
        await asyncio.to_thread(e2b_provider.extend_timeout, session_id)

        message_id = await self._repo.enqueue_message(session_id, message)
        return ChatResponse(ok=True, session_id=session_id, message_id=message_id)

    async def get_status(self, session_id: str) -> SessionStatusResponse:
        session = await self._repo.get(session_id)
        if session is None:
            raise KeyError(session_id)

        alive = await self._repo.worker_alive(session_id)
        pending = await self._repo.pending_messages(session_id)

        return SessionStatusResponse(
            session_id=session_id,
            sandbox_id=session.sandbox_id,
            worker_alive=alive,
            pending_messages=pending,
            status=session.status,
        )

    async def stream_events(self, session_id: str) -> AsyncGenerator[str, None]:
        """Async generator yielding raw SSE `data:` lines from Redis Pub/Sub."""
        session = await self._repo.get(session_id)
        if session is None:
            raise KeyError(session_id)

        pubsub = self._redis.pubsub()
        await pubsub.subscribe(session.output_channel)

        connected = json.dumps(
            {"type": "stream_connected", "session_id": session_id, "channel": session.output_channel}
        )
        yield f"data: {connected}\n\n"

        try:
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
                if msg is None:
                    heartbeat = json.dumps({"type": "sse_heartbeat", "session_id": session_id})
                    yield f"data: {heartbeat}\n\n"
                    continue

                data = msg.get("data", "")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                yield f"data: {data}\n\n"
                await asyncio.sleep(0)
        finally:
            await pubsub.unsubscribe(session.output_channel)
            await pubsub.aclose()

    async def list_files(self, session_id: str) -> FilesResponse:
        session = await self._repo.get(session_id)
        if session is None:
            raise KeyError(session_id)

        sandbox = e2b_provider.get(session_id)
        if sandbox is None:
            raise RuntimeError("Sandbox not in local registry — server may have restarted.")

        result = await asyncio.to_thread(
            sandbox.commands.run,
            "find /home/user/workspace -maxdepth 3 -type f | sort",
            timeout=30,
        )
        files = [f for f in result.stdout.strip().splitlines() if f]
        return FilesResponse(files=files)
