from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.dependencies import require_auth
from src.models.auth import AuthResponse, LoginRequest, SignUpRequest, UserResponse
from src.providers import supabase_provider

logger = logging.getLogger("ollyuw.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(req: SignUpRequest):
    try:
        client = supabase_provider.get_client()
        result = await asyncio.to_thread(
            client.auth.sign_up, {"email": req.email, "password": req.password}
        )
        if not result.session:
            # Email confirmation is enabled in Supabase — user must confirm before they get tokens.
            return JSONResponse(
                status_code=202,
                content={"status": "pending_confirmation", "email": result.user.email},
            )
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


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest) -> AuthResponse:
    try:
        client = supabase_provider.get_client()
        result = await asyncio.to_thread(
            client.auth.sign_in_with_password,
            {"email": req.email, "password": req.password},
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


@router.post("/logout", status_code=204)
async def logout(current_user: Annotated[dict, Depends(require_auth)]) -> None:
    # Supabase JWTs are stateless short-lived tokens; the client discards them.
    # Server-side revocation via admin API can be added when needed.
    pass


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[dict, Depends(require_auth)]) -> UserResponse:
    return UserResponse(user_id=current_user["user_id"], email=current_user["email"])
