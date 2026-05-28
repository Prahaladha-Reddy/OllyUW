from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    refresh_token: str | None = None
    user_id: str | None = None
    email: str | None = None


class UserResponse(BaseModel):
    user_id: str
    email: str
