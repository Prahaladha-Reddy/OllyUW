"""Conversation CRUD. Chat-specific logic lives in session_service."""
from __future__ import annotations

import asyncio
import logging

from fastapi import HTTPException

from src.models.conversation import ConversationDetail
from src.providers import e2b_provider
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.project_repository import ProjectRepository

logger = logging.getLogger("ollyuw.conversation")


def _to_detail(row: dict) -> ConversationDetail:
    return ConversationDetail(
        id=row["id"],
        project_id=row["project_id"],
        title=row["title"],
        session_id=row.get("session_id"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class ConversationService:
    def __init__(
        self,
        project_repo: ProjectRepository,
        conversation_repo: ConversationRepository,
    ) -> None:
        self._projects = project_repo
        self._conversations = conversation_repo

    async def create(self, user_id: str, project_id: str, title: str) -> ConversationDetail:
        await self._require_project(user_id, project_id)
        row = await asyncio.to_thread(self._conversations.create, user_id, project_id, title)
        return _to_detail(row)

    async def list_for_project(self, user_id: str, project_id: str) -> list[ConversationDetail]:
        await self._require_project(user_id, project_id)
        rows = await asyncio.to_thread(self._conversations.list_for_project, user_id, project_id)
        return [_to_detail(r) for r in rows]

    async def get(self, user_id: str, project_id: str, conversation_id: str) -> ConversationDetail:
        await self._require_project(user_id, project_id)
        row = await asyncio.to_thread(self._conversations.get, user_id, project_id, conversation_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
        return _to_detail(row)

    async def delete(self, user_id: str, project_id: str, conversation_id: str) -> None:
        conv = await self.get(user_id, project_id, conversation_id)

        # Kill the sandbox if one is alive for this conversation
        if conv.session_id:
            sandbox = await e2b_provider.get(conv.session_id)
            if sandbox is not None:
                await asyncio.to_thread(e2b_provider.kill_sandbox, sandbox)
                await e2b_provider.deregister(conv.session_id)

        await asyncio.to_thread(self._conversations.delete, user_id, conversation_id)

    async def _require_project(self, user_id: str, project_id: str) -> None:
        ok = await asyncio.to_thread(self._projects.exists, user_id, project_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
