from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionRecord:
    id: str
    user_id: str
    computer_id: str
    title: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class MessageRecord:
    id: str
    session_id: str
    user_id: str
    role: str
    content: str
    model: str | None
    citations: list | None
    created_at: str


# ---------- Pydantic request/response models ----------

from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    title: str = "New Session"


class SendMessageRequest(BaseModel):
    text: str
    model: str = ""


class SessionResponse(BaseModel):
    session: dict


class SessionListResponse(BaseModel):
    sessions: list[dict]


class MessageListResponse(BaseModel):
    messages: list[dict]


class MessageResponse(BaseModel):
    message: dict
