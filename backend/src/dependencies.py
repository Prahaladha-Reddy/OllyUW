from __future__ import annotations

import asyncio

from fastapi import Header, HTTPException

from src.providers import supabase_provider


async def require_auth(authorization: str | None = Header(None)) -> dict:
    """FastAPI dependency — validates a Supabase JWT and returns {user_id, email}."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[7:]
    try:
        client = supabase_provider.get_client()
        resp = await asyncio.to_thread(client.auth.get_user, token)
        if not resp.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": resp.user.id, "email": resp.user.email}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Authentication failed") from exc
