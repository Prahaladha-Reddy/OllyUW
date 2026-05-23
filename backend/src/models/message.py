from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class SendMessageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20_000)


class Message(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    citations: list[dict[str, Any]] | None = None
    created_at: datetime


class SendMessageResponse(BaseModel):
    message: Message
    queued_id: str  # Redis stream message id — caller can correlate with SSE events


class MessagesListResponse(BaseModel):
    messages: list[Message]
