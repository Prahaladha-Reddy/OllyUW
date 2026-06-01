from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ConnectionRecord(BaseModel):
    id: str
    user_id: str
    composio_account_id: str
    provider: str
    created_at: datetime


class ConnectionListResponse(BaseModel):
    connections: list[ConnectionRecord]


class ToolkitStatus(BaseModel):
    slug: str
    name: str
    is_connected: bool


class ToolkitListResponse(BaseModel):
    toolkits: list[ToolkitStatus]


class InitiateConnectionResponse(BaseModel):
    toolkit: str
    redirect_url: str
