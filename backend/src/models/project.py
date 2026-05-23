from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.models.conversation import ConversationSummary
from src.models.file import FileRecord


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)


class ProjectSummary(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    file_count: int
    conversation_count: int


class ProjectDetail(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    files: list[FileRecord]
    conversations: list[ConversationSummary]


class ProjectsListResponse(BaseModel):
    projects: list[ProjectSummary]
