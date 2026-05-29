from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

import redis.asyncio as aioredis

from src.repositories.computer_repository import ComputerRepository
from src.repositories.session_repository import SessionRepository

logger = logging.getLogger("ollyuw.session")

# How long the SSE stream will wait for events before sending a keepalive comment.
_POLL_TIMEOUT = 15.0
# Hard cap on how long a single stream connection stays open (seconds).
_MAX_STREAM_SECONDS = 600


class SessionService:
    def __init__(
        self,
        session_repo: SessionRepository,
        computer_repo: ComputerRepository,
        redis: aioredis.Redis,
    ) -> None:
        self._sessions = session_repo
        self._computers = computer_repo
        self._redis = redis

    def list_sessions(self, user_id: str) -> list[dict]:
        return self._sessions.list_by_user(user_id)

    def create_session(self, user_id: str, title: str) -> dict:
        computer = self._computers.get_by_user(user_id)
        if not computer:
            raise ValueError("no computer found for user")
        return self._sessions.create(user_id, computer["id"], title)

    def delete_session(self, user_id: str, session_id: str) -> None:
        self._sessions.delete(session_id, user_id)

    def get_messages(self, user_id: str, session_id: str) -> list[dict]:
        self._require_session(user_id, session_id)
        return self._sessions.list_messages(session_id, user_id)

    async def send_message(
        self, user_id: str, session_id: str, text: str, model: str
    ) -> dict:
        self._require_session(user_id, session_id)
        computer = self._computers.get_by_user(user_id)
        if not computer:
            raise ValueError("no computer found for user")

        msg = self._sessions.add_message(session_id, user_id, "user", text, model=model or None)

        stream_key = f"agent:{computer['id']}:messages"
        payload = json.dumps({"message": text, "model": model, "session_id": session_id})
        await self._redis.xadd(stream_key, {"data": payload})
        logger.info("published to %s session=%s", stream_key, session_id)

        return msg

    async def stream_session(
        self, user_id: str, session_id: str
    ) -> AsyncGenerator[dict, None]:
        self._require_session(user_id, session_id)
        computer = self._computers.get_by_user(user_id)
        if not computer:
            raise ValueError("no computer found for user")

        channel = f"agent:{computer['id']}:chunks"
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        logger.info("SSE subscribed to %s session=%s", channel, session_id)

        elapsed = 0.0

        try:
            while elapsed < _MAX_STREAM_SECONDS:
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=_POLL_TIMEOUT,
                )
                if msg is None:
                    elapsed += _POLL_TIMEOUT
                    # Yield an SSE comment to keep the connection alive.
                    yield {"type": "_keepalive"}
                    continue

                try:
                    event = json.loads(msg["data"])
                except (json.JSONDecodeError, KeyError):
                    continue

                is_final = event.get("type") == "final"

                if is_final:
                    # Save to DB BEFORE yielding so the row already exists by the
                    # time the client receives this event and re-fetches messages.
                    try:
                        self._sessions.add_message(
                            session_id,
                            user_id,
                            "assistant",
                            event.get("text", ""),
                            model=event.get("model"),
                            citations=event.get("citations"),
                        )
                        logger.info("saved assistant message session=%s", session_id)
                    except Exception as exc:
                        logger.warning("failed to save assistant message: %s", exc)

                yield event

                if is_final:
                    break
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            except Exception:
                pass

    def _require_session(self, user_id: str, session_id: str) -> dict:
        session = self._sessions.get(session_id, user_id)
        if not session:
            raise LookupError(f"session not found: {session_id}")
        return session
