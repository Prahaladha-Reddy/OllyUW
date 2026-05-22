from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class EventType(str, Enum):
    WORKER_READY = "worker_ready"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_ACKED = "message_acked"
    STATUS = "status"
    MODEL_START = "model_start"
    MODEL_DELTA = "model_delta"
    MODEL_END = "model_end"
    MODEL_RAW = "model_raw"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FINAL = "final"
    ERROR = "error"
    STREAM_CONNECTED = "stream_connected"
    SSE_HEARTBEAT = "sse_heartbeat"


class AgentEvent(BaseModel):
    type: EventType
    session_id: str | None = None
    seq: int | None = None
    text: str | None = None
    tool: str | None = None
    args: dict[str, Any] | None = None
    ok: bool | None = None
    output: str | None = None
    message_id: str | None = None
    channel: str | None = None
