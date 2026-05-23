from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class ConversationSummary(BaseModel):

    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):

    id: str
    project_id: str
    title: str
    session_id: str | None
    created_at: datetime
    updated_at: datetime


class ConversationsListResponse(BaseModel):
    conversations: list[ConversationDetail]
