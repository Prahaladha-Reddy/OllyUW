from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

class ComputerStatus(str, Enum):
    SLEEPING = "sleeping"
    ONLINE = "online"


class ComputerRuntimeState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"

class ComputerRecord(BaseModel):
    id: str
    user_id: str
    status: ComputerStatus
    runtime_state: ComputerRuntimeState
    sandbox_id: str | None = None
    snapshot_id: str | None = None
    workspace_path: str = "/home/user/workspace"
    git_enabled: bool = True
    desktop_host: str | None = None
    desktop_port: int | None = None
    desktop_url: str | None = None
    last_booted_at: datetime | None = None
    last_paused_at: datetime | None = None
    last_snapshot_at: datetime | None = None
    error_message: str | None = None
    last_active: datetime
    created_at: datetime
    updated_at: datetime

class ComputerResponse(BaseModel):
    computer: ComputerRecord
