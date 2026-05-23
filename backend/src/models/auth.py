from __future__ import annotations

from pydantic import BaseModel


class SignUpRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str


class UserResponse(BaseModel):
    user_id: str
    email: str
