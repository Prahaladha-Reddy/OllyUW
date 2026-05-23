"""Auth orchestration. Wraps Supabase auth so the controller stays thin."""
from __future__ import annotations

import asyncio
import logging

from fastapi import HTTPException

from src.models.auth import AuthResponse
from src.providers import supabase_provider

logger = logging.getLogger("ollyuw.auth")


class AuthService:
    async def signup(self, email: str, password: str) -> AuthResponse | dict:
        try:
            client = supabase_provider.get_anon_client()
            result = await asyncio.to_thread(
                client.auth.sign_up, {"email": email, "password": password}
            )
            if not result.session:
                return {"status": "pending_confirmation", "email": result.user.email}
            return AuthResponse(
                access_token=result.session.access_token,
                refresh_token=result.session.refresh_token,
                user_id=result.user.id,
                email=result.user.email,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("signup error: %s", exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc

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
        try:
            client = supabase_provider.get_anon_client()
            resp = await asyncio.to_thread(client.auth.get_user, token)
            if not resp.user:
                raise HTTPException(status_code=401, detail="Invalid token")
            return {"user_id": resp.user.id, "email": resp.user.email}
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Authentication failed") from exc
