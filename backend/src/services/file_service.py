from __future__ import annotations

import asyncio
import logging
import mimetypes
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from src.models.file import FileRecord, FileStatus, UploadFilesResponse
from src.providers import storage_provider
from src.repositories.file_repository import FileRepository
from src.repositories.project_repository import ProjectRepository

logger = logging.getLogger("ollyuw.file")

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB per file

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".tsv",
    ".json", ".yaml", ".yml", ".toml",
    ".txt", ".md", ".html", ".xml"}


def _to_record(row: dict) -> FileRecord:
    return FileRecord(
        id=row["id"],
        original_name=row["original_name"],
        storage_path=row["storage_path"],
        file_size=row.get("file_size"),
        status=row["status"],
        error_message=row.get("error_message"),
        created_at=row["created_at"],
    )


class FileService:
    def __init__(self, project_repo: ProjectRepository, file_repo: FileRepository) -> None:
        self._projects = project_repo
        self._files = file_repo

    async def upload(
        self,
        *,
        user_id: str,
        project_id: str,
        uploads: list[UploadFile],
    ) -> UploadFilesResponse:
        if not await asyncio.to_thread(self._projects.exists, user_id, project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        tasks = [self._process_one(user_id, project_id, u) for u in uploads]
        records = list(await asyncio.gather(*tasks))
        return UploadFilesResponse(project_id=project_id, files=records)

    async def delete(self, user_id: str, project_id: str, file_id: str) -> None:
        row = await asyncio.to_thread(self._files.get, user_id, project_id, file_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"File '{file_id}' not found")

        path = row["storage_path"]
        if path:
            try:
                await asyncio.to_thread(storage_provider.delete, [path])
            except Exception as exc:
                logger.warning("storage delete failed for %s: %s", path, exc)

        await asyncio.to_thread(self._files.delete, user_id, file_id)


    async def _process_one(
        self, user_id: str, project_id: str, upload: UploadFile,
    ) -> FileRecord:
        filename = upload.filename or "unnamed"
        file_id = str(uuid.uuid4())
        suffix = Path(filename).suffix.lower()

        if suffix not in ALLOWED_EXTENSIONS:
            return await self._record_error(
                user_id, project_id, file_id, filename,
                error=f"File type {suffix or '(none)'!r} not supported",
            )

        try:
            content = await upload.read()
        except Exception as exc:
            return await self._record_error(
                user_id, project_id, file_id, filename,
                error=f"Could not read upload: {exc}",
            )

        size = len(content)
        if size > MAX_FILE_SIZE:
            return await self._record_error(
                user_id, project_id, file_id, filename, error="File exceeds 50 MB limit",
                file_size=size,
            )

        storage_path = f"{user_id}/projects/{project_id}/{file_id}/{filename}"
        content_type, _ = mimetypes.guess_type(filename)

        try:
            await asyncio.to_thread(
                storage_provider.upload, storage_path, content, content_type or "application/octet-stream"
            )
        except Exception as exc:
            logger.error("storage upload failed for %s: %s", filename, exc)
            return await self._record_error(
                user_id, project_id, file_id, filename, error=str(exc), file_size=size,
            )

        row = await asyncio.to_thread(
            self._files.create,
            file_id=file_id,
            user_id=user_id,
            project_id=project_id,
            original_name=filename,
            storage_path=storage_path,
            file_size=size,
            status=FileStatus.READY.value,
        )
        return _to_record(row)

    async def _record_error(
        self,
        user_id: str,
        project_id: str,
        file_id: str,
        filename: str,
        *,
        error: str,
        file_size: int | None = None,
    ) -> FileRecord:
        row = await asyncio.to_thread(
            self._files.create,
            file_id=file_id,
            user_id=user_id,
            project_id=project_id,
            original_name=filename,
            storage_path="",
            file_size=file_size,
            status=FileStatus.ERROR.value,
            error_message=error,
        )
        return _to_record(row)
