from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.providers import redis_provider

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    ok: bool
    redis: bool


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    try:
        redis_ok = await redis_provider.ping()
    except Exception:
        redis_ok = False
    return HealthResponse(ok=redis_ok, redis=redis_ok)


@router.get("/health/redis")
async def redis_health() -> dict:
    try:
        ok = await redis_provider.ping()
        return {"ok": ok}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc
