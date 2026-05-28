from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

class ComputerStatus(str, Enum):
    SLEEPING = "sleeping"
    ONLINE = "online"

class ComputerRecord(BaseModel):
    id: str
    user_id: str
    status: ComputerStatus
    last_active: datetime
    created_at: datetime
    updated_at: datetime

class ComputerResponse(BaseModel):
    computer: ComputerRecord
