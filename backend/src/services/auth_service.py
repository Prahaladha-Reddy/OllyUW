"""Auth orchestration. Wraps Supabase auth so the controller stays thin."""
from __future__ import annotations

import asyncio
import logging
import time

from fastapi import HTTPException

from src.models.auth import AuthResponse
from src.providers import supabase_provider

logger = logging.getLogger("ollyuw.auth")

# Cache verified tokens for a short window so we don't call Supabase Auth on
# every backend request. JWTs are valid for an hour by default; 60 seconds of
# staleness is acceptable in exchange for cutting one Supabase round-trip per
# request. Cache is keyed by raw token and stored as (expires_at, user_info).
_TOKEN_CACHE_TTL_S = 60.0
_token_cache: dict[str, tuple[float, dict]] = {}
_token_cache_lock = asyncio.Lock()


class AuthService:
    async def login(self, email: str, password: str) -> AuthResponse:
        try:
            client = supabase_provider.get_anon_client()
            result = await asyncio.to_thread(
                client.auth.sign_in_with_password,
                {"email": email, "password": password},
            )
            if not result.session:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            return AuthResponse(
                access_token=result.session.access_token,
                refresh_token=result.session.refresh_token,
                user_id=result.user.id,
                email=result.user.email,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("login error: %s", exc)
            raise HTTPException(status_code=401, detail="Invalid email or password") from exc

    async def verify_token(self, token: str) -> dict:
        now = time.monotonic()
        async with _token_cache_lock:
            cached = _token_cache.get(token)
            if cached and cached[0] > now:
                return cached[1]

        try:
            client = supabase_provider.get_anon_client()
            resp = await asyncio.to_thread(client.auth.get_user, token)
            if not resp.user:
                raise HTTPException(status_code=401, detail="Invalid token")
            user_info = {"user_id": resp.user.id, "email": resp.user.email}
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Authentication failed") from exc

        async with _token_cache_lock:
            _token_cache[token] = (now + _TOKEN_CACHE_TTL_S, user_info)
            # Opportunistic GC: drop expired entries so the dict doesn't grow
            # unbounded over a long-lived process.
            if len(_token_cache) > 256:
                expired = [k for k, (exp, _) in _token_cache.items() if exp <= now]
                for k in expired:
                    _token_cache.pop(k, None)
        return user_info
