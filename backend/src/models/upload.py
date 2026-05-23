from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class FileStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    SKIPPED = "skipped"


class ProcessedFile(BaseModel):
    original_name: str
    storage_path: str | None = None
    status: FileStatus
    error: str | None = None


class UploadResponse(BaseModel):
    submission_id: str
    files: list[ProcessedFile]
