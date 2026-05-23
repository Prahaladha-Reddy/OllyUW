from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class FileStatus(str, Enum):
    READY = "ready"
    ERROR = "error"


class FileRecord(BaseModel):
    id: str
    original_name: str
    storage_path: str
    file_size: int | None
    status: FileStatus
    error_message: str | None
    created_at: datetime


class UploadFilesResponse(BaseModel):
    project_id: str
    files: list[FileRecord]
