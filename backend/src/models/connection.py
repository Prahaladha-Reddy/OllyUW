from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel

class ConnectionRecord(BaseModel):
    id: str
    user_id: str
    composio_account_id: str
    provider: str
    created_at: datetime

class CreateConnectionRequest(BaseModel):
    composio_account_id: str
    provider: str

class ConnectionResponse(BaseModel):
    connection: ConnectionRecord

class ConnectionListResponse(BaseModel):
    connections: list[ConnectionRecord]
