from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


# Stable, frontend-visible identifiers for the LLM backend. The worker maps
# these to (base_url, api_key, model_name). Adding a new provider = one entry
# here + one branch in worker._resolve_llm_config.
ModelId = Literal["modal", "deepseek"]
DEFAULT_MODEL: ModelId = "modal"


class SendMessageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20_000)
    model: ModelId = DEFAULT_MODEL


class Message(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    citations: list[dict[str, Any]] | None = None
    model: str | None = None  # null for user messages and pre-migration rows
    created_at: datetime


class SendMessageResponse(BaseModel):
    message: Message
    queued_id: str  # Redis stream message id — caller can correlate with SSE events


class MessagesListResponse(BaseModel):
    messages: list[Message]
