from __future__ import annotations

import asyncio
import logging
import mimetypes
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile

from src.models.file import CreateFolderRequest, FileRecord, UpdateNodeRequest, UploadFilesResponse
from src.providers import storage_provider
from src.repositories.computer_repository import ComputerRepository
from src.repositories.file_repository import FileRepository

logger = logging.getLogger("olly.file")

MAX_FILE_SIZE = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".tsv",
    ".json", ".yaml", ".yml", ".toml",
    ".txt", ".md", ".html", ".xml",
}


def _to_record(row: dict) -> FileRecord:
    return FileRecord(
        id=row["id"],
        user_id=row["user_id"],
        parent_folder_id=row.get("parent_folder_id"),
        name=row.get("name") or row.get("original_name"),
        storage_path=row.get("storage_path"),
        file_type=row["file_type"],
        automation_trigger_id=row.get("automation_trigger_id"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@dataclass(frozen=True)
class DownloadedFile:
    filename: str
    media_type: str
    content: bytes


class FileService:
    def __init__(self, computer_repo: ComputerRepository, file_repo: FileRepository) -> None:
        self._computers = computer_repo
        self._files = file_repo

    def list_files(self, user_id: str) -> list[FileRecord]:
        self._ensure_computer(user_id)
        rows = self._files.list_for_user(user_id)
        return [_to_record(row) for row in rows]

    def list_folder_children(self, user_id: str, folder_id: str) -> list[FileRecord]:
        rows = self._list_rows(user_id)
        target, _ = self._get_target(rows, folder_id, expected_type="folder")
        children = [
            _to_record(row)
            for row in rows
            if row.get("parent_folder_id") == target["id"]
        ]
        children.sort(key=lambda record: (record.file_type.value, record.name.lower()))
        return children

    def get_file(self, user_id: str, file_id: str) -> FileRecord:
        rows = self._list_rows(user_id)
        target, _ = self._get_target(rows, file_id, expected_type="file")
        return _to_record(target)

    def create_folder(self, user_id: str, request: CreateFolderRequest) -> FileRecord:
        computer = self._ensure_computer(user_id)
        rows = self._files.list_for_user(user_id)
        rows_by_id = {row["id"]: row for row in rows}
        index = self._build_index(rows)
        folder_name = request.name.strip()

        if request.parent_folder_id is not None:
            parent = rows_by_id.get(request.parent_folder_id)
            if parent is None or parent["file_type"] != "folder":
                raise HTTPException(status_code=404, detail="Parent folder not found")

        if index.get((request.parent_folder_id, folder_name, "folder")) is not None:
            raise HTTPException(status_code=409, detail=f"Folder '{folder_name}' already exists")

        row = self._ensure_folder(
            user_id=user_id,
            computer_id=computer["id"],
            parent_folder_id=request.parent_folder_id,
            name=folder_name,
            automation_trigger_id=request.automation_trigger_id,
            index=index,
        )
        return _to_record(row)

    async def download_file(self, user_id: str, file_id: str) -> DownloadedFile:
        rows = self._list_rows(user_id)
        target, _ = self._get_target(rows, file_id, expected_type="file")
        storage_path = target.get("storage_path")
        if not storage_path:
            raise HTTPException(status_code=404, detail="File content is not available")

        try:
            content = await asyncio.to_thread(storage_provider.download, storage_path)
        except Exception as exc:
            logger.error("storage download failed for %s: %s", target["name"], exc)
            raise HTTPException(status_code=502, detail=f"Storage download failed for '{target['name']}'") from exc

        media_type, _ = mimetypes.guess_type(target["name"])
        return DownloadedFile(
            filename=target["name"],
            media_type=media_type or "application/octet-stream",
            content=content,
        )

    async def update_file(self, user_id: str, file_id: str, request: UpdateNodeRequest) -> FileRecord:
        return await self._update_node(user_id, file_id, request, expected_type="file")

    async def update_folder(self, user_id: str, folder_id: str, request: UpdateNodeRequest) -> FileRecord:
        return await self._update_node(user_id, folder_id, request, expected_type="folder")

    async def delete_file(self, user_id: str, file_id: str) -> None:
        await self._delete_node(user_id, file_id, expected_type="file")

    async def delete_folder(self, user_id: str, folder_id: str) -> None:
        await self._delete_node(user_id, folder_id, expected_type="folder")

    async def upload_files(
        self,
        *,
        user_id: str,
        uploads: list[UploadFile],
        parent_folder_id: str | None = None,
        relative_paths: list[str] | None = None,
    ) -> UploadFilesResponse:
        if not uploads:
            raise HTTPException(status_code=400, detail="No files provided")

        if relative_paths is not None and len(relative_paths) != len(uploads):
            raise HTTPException(status_code=400, detail="relative_paths must match the number of files")

        computer = self._ensure_computer(user_id)
        rows = self._files.list_for_user(user_id)
        rows_by_id = {row["id"]: row for row in rows}
        index = self._build_index(rows)

        if parent_folder_id is not None:
            parent = rows_by_id.get(parent_folder_id)
            if parent is None or parent["file_type"] != "folder":
                raise HTTPException(status_code=404, detail="Parent folder not found")

        results: list[FileRecord] = []
        for idx, upload in enumerate(uploads):
            relative_path = relative_paths[idx] if relative_paths is not None else upload.filename
            record = await self._upload_one(
                computer_id=computer["id"],
                user_id=user_id,
                parent_folder_id=parent_folder_id,
                upload=upload,
                relative_path=relative_path,
                index=index,
            )
            results.append(record)

        return UploadFilesResponse(files=results)

    def _build_index(self, rows: list[dict]) -> dict[tuple[str | None, str, str], dict]:
        index: dict[tuple[str | None, str, str], dict] = {}
        for row in rows:
            name = row.get("name") or row.get("original_name")
            index[(row.get("parent_folder_id"), name, row["file_type"])] = row
        return index

    async def _delete_node(self, user_id: str, file_id: str, *, expected_type: str) -> None:
        rows = self._list_rows(user_id)
        target, rows_by_id = self._get_target(rows, file_id, expected_type=expected_type)
        targets = self._collect_tree(rows_by_id, target)
        storage_paths = [row["storage_path"] for row in targets if row["file_type"] == "file" and row.get("storage_path")]

        for chunk_start in range(0, len(storage_paths), 1000):
            chunk = storage_paths[chunk_start:chunk_start + 1000]
            try:
                await asyncio.to_thread(storage_provider.delete, chunk)
            except Exception as exc:
                logger.error("storage delete failed for %s: %s", file_id, exc)
                raise HTTPException(status_code=502, detail="Storage delete failed") from exc

        self._files.delete_many(user_id=user_id, file_ids=[row["id"] for row in targets])

    def _ensure_folder(
        self,
        *,
        user_id: str,
        computer_id: str,
        parent_folder_id: str | None,
        name: str,
        automation_trigger_id: str | None,
        index: dict[tuple[str | None, str, str], dict],
    ) -> dict:
        folder_name = name.strip()
        if not folder_name:
            raise HTTPException(status_code=400, detail="Folder name is required")
        if folder_name in {".", ".."} or "/" in folder_name or "\\" in folder_name:
            raise HTTPException(status_code=400, detail=f"Invalid folder name '{name}'")

        file_conflict = index.get((parent_folder_id, folder_name, "file"))
        if file_conflict is not None:
            raise HTTPException(status_code=409, detail=f"A file named '{folder_name}' already exists")

        existing = index.get((parent_folder_id, folder_name, "folder"))
        if existing is not None:
            return existing

        row = self._files.create_folder(
            file_id=str(uuid.uuid4()),
            computer_id=computer_id,
            user_id=user_id,
            parent_folder_id=parent_folder_id,
            name=folder_name,
            automation_trigger_id=automation_trigger_id,
        )
        index[(parent_folder_id, folder_name, "folder")] = row
        return row

    async def _update_node(
        self,
        user_id: str,
        file_id: str,
        request: UpdateNodeRequest,
        *,
        expected_type: str,
    ) -> FileRecord:
        changed_fields = request.model_fields_set
        if not changed_fields:
            raise HTTPException(status_code=400, detail="No updates provided")

        rows = self._list_rows(user_id)
        target, rows_by_id = self._get_target(rows, file_id, expected_type=expected_type)
        index = self._build_index(rows)

        new_name = target["name"]
        if "name" in changed_fields:
            if request.name is None:
                raise HTTPException(status_code=400, detail="Name is required")
            new_name = self._validate_node_name(request.name)

        new_parent_id = target.get("parent_folder_id")
        if "parent_folder_id" in changed_fields:
            new_parent_id = request.parent_folder_id
            self._validate_parent(rows_by_id, target, new_parent_id)

        if new_name == target["name"] and new_parent_id == target.get("parent_folder_id"):
            return _to_record(target)

        self._validate_conflict(
            index=index,
            target=target,
            new_parent_id=new_parent_id,
            new_name=new_name,
        )

        values = {
            "name": new_name,
            "original_name": new_name,
            "parent_folder_id": new_parent_id,
        }

        if target["file_type"] == "file":
            new_storage_path = await self._maybe_rename_storage_object(target, new_name)
            if new_storage_path is not None:
                values["storage_path"] = new_storage_path

        row = self._files.update_node(file_id=file_id, user_id=user_id, values=values)
        return _to_record(row)

    async def _upload_one(
        self,
        *,
        computer_id: str,
        user_id: str,
        parent_folder_id: str | None,
        upload: UploadFile,
        relative_path: str | None,
        index: dict[tuple[str | None, str, str], dict],
    ) -> FileRecord:
        path_parts = self._relative_path_parts(relative_path or upload.filename or "unnamed")
        current_parent_id = parent_folder_id

        for folder_name in path_parts[:-1]:
            folder_row = self._ensure_folder(
                user_id=user_id,
                computer_id=computer_id,
                parent_folder_id=current_parent_id,
                name=folder_name,
                automation_trigger_id=None,
                index=index,
            )
            current_parent_id = folder_row["id"]

        filename = path_parts[-1]
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"File type {suffix or '(none)'} is not supported")

        folder_conflict = index.get((current_parent_id, filename, "folder"))
        if folder_conflict is not None:
            raise HTTPException(status_code=409, detail=f"A folder named '{filename}' already exists")

        try:
            content = await upload.read()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not read upload '{filename}': {exc}") from exc

        size = len(content)
        if size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"File '{filename}' exceeds the 50 MB limit")

        existing = index.get((current_parent_id, filename, "file"))
        file_id = existing["id"] if existing is not None else str(uuid.uuid4())
        storage_path = existing["storage_path"] if existing and existing.get("storage_path") else (
            f"{user_id}/computers/{computer_id}/{file_id}/{filename}"
        )
        content_type, _ = mimetypes.guess_type(filename)

        try:
            await asyncio.to_thread(
                storage_provider.upload,
                storage_path,
                content,
                content_type or "application/octet-stream",
            )
        except Exception as exc:
            logger.error("storage upload failed for %s: %s", filename, exc)
            raise HTTPException(status_code=502, detail=f"Storage upload failed for '{filename}'") from exc

        if existing is not None:
            row = self._files.update_file(
                file_id=file_id,
                user_id=user_id,
                storage_path=storage_path,
                file_size=size,
            )
        else:
            row = self._files.create_file(
                file_id=file_id,
                computer_id=computer_id,
                user_id=user_id,
                parent_folder_id=current_parent_id,
                name=filename,
                storage_path=storage_path,
                file_size=size,
            )
        index[(current_parent_id, filename, "file")] = row
        return _to_record(row)

    def _relative_path_parts(self, raw_path: str) -> list[str]:
        normalized = raw_path.replace("\\", "/").strip()
        parts = [part.strip() for part in normalized.split("/") if part.strip() not in {"", "."}]
        if not parts:
            raise HTTPException(status_code=400, detail="Upload path is empty")
        if any(part == ".." for part in parts):
            raise HTTPException(status_code=400, detail=f"Invalid upload path '{raw_path}'")
        return parts

    def _ensure_computer(self, user_id: str) -> dict:
        row = self._computers.get_by_user(user_id)
        if row is None:
            row = self._computers.create_default(user_id)
        return row

    def _collect_tree(self, rows_by_id: dict[str, dict], target: dict) -> list[dict]:
        children_by_parent: dict[str, list[dict]] = {}
        for row in rows_by_id.values():
            parent_id = row.get("parent_folder_id")
            if parent_id is not None:
                children_by_parent.setdefault(parent_id, []).append(row)

        stack = [target]
        ordered: list[dict] = []
        while stack:
            current = stack.pop()
            ordered.append(current)
            stack.extend(children_by_parent.get(current["id"], []))
        return ordered

    def _get_target(self, rows: list[dict], file_id: str, *, expected_type: str) -> tuple[dict, dict[str, dict]]:
        rows_by_id = {row["id"]: row for row in rows}
        target = rows_by_id.get(file_id)
        if target is None or target["file_type"] != expected_type:
            detail = "File not found" if expected_type == "file" else "Folder not found"
            raise HTTPException(status_code=404, detail=detail)
        return target, rows_by_id

    def _list_rows(self, user_id: str) -> list[dict]:
        self._ensure_computer(user_id)
        return self._files.list_for_user(user_id)

    async def _maybe_rename_storage_object(self, target: dict, new_name: str) -> str | None:
        current_storage_path = target.get("storage_path")
        if not current_storage_path or new_name == target["name"]:
            return None

        current_path = Path(current_storage_path.replace("\\", "/"))
        new_storage_path = str(current_path.with_name(new_name)).replace("\\", "/")

        try:
            await asyncio.to_thread(storage_provider.copy, current_storage_path, new_storage_path)
            await asyncio.to_thread(storage_provider.delete, [current_storage_path])
        except Exception as exc:
            logger.error("storage rename failed for %s: %s", target["id"], exc)
            raise HTTPException(status_code=502, detail=f"Storage rename failed for '{target['name']}'") from exc

        return new_storage_path

    def _validate_conflict(
        self,
        *,
        index: dict[tuple[str | None, str, str], dict],
        target: dict,
        new_parent_id: str | None,
        new_name: str,
    ) -> None:
        for file_type in ("file", "folder"):
            existing = index.get((new_parent_id, new_name, file_type))
            if existing is not None and existing["id"] != target["id"]:
                raise HTTPException(status_code=409, detail=f"An item named '{new_name}' already exists")

    def _validate_node_name(self, name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise HTTPException(status_code=400, detail="Name is required")
        if normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
            raise HTTPException(status_code=400, detail=f"Invalid name '{name}'")
        return normalized

    def _validate_parent(self, rows_by_id: dict[str, dict], target: dict, parent_folder_id: str | None) -> None:
        if parent_folder_id is None:
            return
        if parent_folder_id == target["id"]:
            raise HTTPException(status_code=400, detail="An item cannot be its own parent")

        parent = rows_by_id.get(parent_folder_id)
        if parent is None or parent["file_type"] != "folder":
            raise HTTPException(status_code=404, detail="Parent folder not found")

        if target["file_type"] != "folder":
            return

        cursor = parent
        while cursor is not None:
            if cursor["id"] == target["id"]:
                raise HTTPException(status_code=400, detail="A folder cannot be moved into its descendant")
            next_parent_id = cursor.get("parent_folder_id")
            cursor = rows_by_id.get(next_parent_id) if next_parent_id is not None else None
