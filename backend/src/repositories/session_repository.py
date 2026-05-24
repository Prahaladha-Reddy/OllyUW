from __future__ import annotations

import json

import redis.asyncio as aioredis

from src.models.session import SessionMeta, SessionStatus

SESSION_TTL = 3600 * 4  # 4 hours


def _key(session_id: str) -> str:
    return f"session:{session_id}:meta"


class SessionRepository:
    """
    Redis-backed session metadata store.
    Stores only serialisable data — Sandbox objects live in e2b_provider._sandboxes.
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self._r = redis

    async def save(self, session: SessionMeta) -> None:
        await self._r.set(
            _key(session.session_id),
            session.model_dump_json(),
            ex=SESSION_TTL,
        )

    async def get(self, session_id: str) -> SessionMeta | None:
        raw = await self._r.get(_key(session_id))
        if raw is None:
            return None
        return SessionMeta.model_validate(json.loads(raw))

    async def update_status(self, session_id: str, status: SessionStatus) -> None:
        session = await self.get(session_id)
        if session is None:
            return
        session.status = status
        await self.save(session)

    async def delete(self, session_id: str) -> None:
        await self._r.delete(_key(session_id))

    async def worker_alive(self, session_id: str) -> bool:
        key = f"agent:{session_id}:heartbeat"
        return bool(await self._r.exists(key))

    async def pending_messages(self, session_id: str) -> int:
        key = f"agent:{session_id}:messages"
        length = await self._r.xlen(key)
        return int(length)

    async def enqueue_message(self, session_id: str, message: str, model: str) -> str:
        """
        Push a user message onto the worker's input stream. `model` selects
        which LLM the worker should call for this turn (e.g. 'modal',
        'deepseek') — credentials for all providers are already in the
        sandbox env, so this is a per-turn switch, not a session-wide one.
        """
        key = f"agent:{session_id}:messages"
        payload = {"message": message, "model": model}
        message_id: str = await self._r.xadd(
            key,
            {"data": json.dumps(payload, ensure_ascii=False)},
        )
        return message_id
