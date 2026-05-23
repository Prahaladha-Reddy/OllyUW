from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    CREATING = "creating"
    READY = "ready"
    ERROR = "error"


class SessionMeta(BaseModel):
    """Serialisable session metadata stored in Redis."""

    session_id: str
    sandbox_id: str
    conversation_id: str | None = None
    input_stream: str
    output_channel: str
    heartbeat_key: str
    status: SessionStatus = SessionStatus.CREATING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionStatusResponse(BaseModel):
    session_id: str
    sandbox_id: str
    worker_alive: bool
    pending_messages: int
    status: SessionStatus


class WorkerLogResponse(BaseModel):
    session_id: str
    log: str
