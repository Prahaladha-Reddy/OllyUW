from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

class FileType(str, Enum):
    FILE = "file"
    FOLDER = "folder"

class FileRecord(BaseModel):
    id: str
    user_id: str
    parent_folder_id: str | None
    name: str
    storage_path: str | None
    file_type: FileType
    automation_trigger_id: str | None
    created_at: datetime
    updated_at: datetime

class CreateFolderRequest(BaseModel):
    name: str
    parent_folder_id: str | None = None
    automation_trigger_id: str | None = None


class UpdateNodeRequest(BaseModel):
    name: str | None = None
    parent_folder_id: str | None = None


class FileResponse(BaseModel):
    file: FileRecord

class FileListResponse(BaseModel):
    files: list[FileRecord]

class UploadFilesResponse(BaseModel):
    files: list[FileRecord]
