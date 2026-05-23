"""Project orchestration. Combines projects + files + conversations."""
from __future__ import annotations

import asyncio
import logging

from fastapi import HTTPException

from src.models.conversation import ConversationSummary
from src.models.file import FileRecord
from src.models.project import ProjectDetail, ProjectSummary
from src.providers import storage_provider
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.file_repository import FileRepository
from src.repositories.project_repository import ProjectRepository

logger = logging.getLogger("ollyuw.project")


def _file_to_model(row: dict) -> FileRecord:
    return FileRecord(
        id=row["id"],
        original_name=row["original_name"],
        storage_path=row["storage_path"],
        file_size=row.get("file_size"),
        status=row["status"],
        error_message=row.get("error_message"),
        created_at=row["created_at"],
    )


def _conv_to_summary(row: dict) -> ConversationSummary:
    return ConversationSummary(
        id=row["id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class ProjectService:
    def __init__(
        self,
        project_repo: ProjectRepository,
        file_repo: FileRepository,
        conversation_repo: ConversationRepository,
    ) -> None:
        self._projects = project_repo
        self._files = file_repo
        self._conversations = conversation_repo

    async def create(self, user_id: str, name: str, description: str | None) -> ProjectDetail:
        row = await asyncio.to_thread(self._projects.create, user_id, name, description)
        return ProjectDetail(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            files=[],
            conversations=[],
        )

    async def list_for_user(self, user_id: str) -> list[ProjectSummary]:
        rows = await asyncio.to_thread(self._projects.list_for_user, user_id)
        if not rows:
            return []

        project_ids = [r["id"] for r in rows]
        file_counts, conv_counts = await asyncio.gather(
            asyncio.to_thread(self._files.count_by_project, user_id, project_ids),
            asyncio.to_thread(self._conversations.count_by_project, user_id, project_ids),
        )

        return [
            ProjectSummary(
                id=r["id"],
                name=r["name"],
                description=r.get("description"),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                file_count=file_counts.get(r["id"], 0),
                conversation_count=conv_counts.get(r["id"], 0),
            )
            for r in rows
        ]

    async def get(self, user_id: str, project_id: str) -> ProjectDetail:
        project_row, file_rows, conv_rows = await asyncio.gather(
            asyncio.to_thread(self._projects.get, user_id, project_id),
            asyncio.to_thread(self._files.list_for_project, user_id, project_id),
            asyncio.to_thread(self._conversations.list_for_project, user_id, project_id),
        )
        if project_row is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        return ProjectDetail(
            id=project_row["id"],
            name=project_row["name"],
            description=project_row.get("description"),
            created_at=project_row["created_at"],
            updated_at=project_row["updated_at"],
            files=[_file_to_model(f) for f in file_rows],
            conversations=[_conv_to_summary(c) for c in conv_rows],
        )

    async def delete(self, user_id: str, project_id: str) -> None:
        exists = await asyncio.to_thread(self._projects.exists, user_id, project_id)
        if not exists:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        # Remove storage objects first (idempotent), then cascade DB delete.
        paths = await asyncio.to_thread(self._files.storage_paths_for_project, user_id, project_id)
        if paths:
            try:
                await asyncio.to_thread(storage_provider.delete, paths)
            except Exception as exc:
                logger.warning("storage cleanup failed for project %s: %s", project_id, exc)

        await asyncio.to_thread(self._projects.delete, user_id, project_id)
