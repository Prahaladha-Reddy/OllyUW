from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as aioredis

from src.config import get_settings

_pool: aioredis.ConnectionPool | None = None


def _get_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            get_settings().redis_url,
            decode_responses=True,
            max_connections=20,
        )
    return _pool


def get_client() -> aioredis.Redis:
    """Return a Redis client backed by the shared connection pool."""
    return aioredis.Redis(connection_pool=_get_pool())


@asynccontextmanager
async def redis_client() -> AsyncGenerator[aioredis.Redis, None]:
    """Context manager that yields a client and ensures it's closed."""
    client = get_client()
    try:
        yield client
    finally:
        await client.aclose()


async def ping() -> bool:
    async with redis_client() as r:
        return bool(await r.ping())


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
