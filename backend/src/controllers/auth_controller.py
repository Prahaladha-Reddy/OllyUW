from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from src.dependencies import get_auth_service, require_auth
from src.models.auth import AuthResponse, LoginRequest, SignUpRequest, UserResponse
from src.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(
    req: SignUpRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
):
    result = await auth.signup(req.email, req.password)
    if isinstance(result, AuthResponse):
        return result
    return JSONResponse(status_code=202, content=result)


@router.post("/login", response_model=AuthResponse)
async def login(
    req: LoginRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    return await auth.login(req.email, req.password)


@router.post("/logout")
async def logout(_: Annotated[dict, Depends(require_auth)]) -> Response:
    # Supabase JWTs are stateless; the client just discards them.
    return Response(status_code=204)


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[dict, Depends(require_auth)]) -> UserResponse:
    return UserResponse(user_id=current_user["user_id"], email=current_user["email"])
