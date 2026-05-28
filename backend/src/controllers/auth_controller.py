from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm

from src.dependencies import get_auth_service, require_auth
from src.models.auth import TokenResponse, UserResponse
from src.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Issue OAuth2 bearer token",
    description="Swagger and API clients should use this endpoint. Put the email address in the username field.",
)
async def issue_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    result = await auth.login(form_data.username, form_data.password)
    return TokenResponse(
        access_token=result.access_token,
        token_type="bearer",
        refresh_token=result.refresh_token,
        user_id=result.user_id,
        email=result.email,
    )


@router.post("/logout")
async def logout(_: Annotated[dict, Depends(require_auth)]) -> Response:
    # Supabase JWTs are stateless; the client just discards them.
    return Response(status_code=204)


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[dict, Depends(require_auth)]) -> UserResponse:
    return UserResponse(user_id=current_user["user_id"], email=current_user["email"])
