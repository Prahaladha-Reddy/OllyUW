"""
Project data access. Returns plain dicts (rows) — services map them to Pydantic models.
All methods are sync; callers wrap in asyncio.to_thread for non-blocking I/O.
"""
from __future__ import annotations

from supabase import Client


class ProjectRepository:
    def __init__(self, db: Client) -> None:
        self._db = db

    def create(self, user_id: str, name: str, description: str | None) -> dict:
        result = (
            self._db.table("projects")
            .insert({"user_id": user_id, "name": name, "description": description})
            .execute()
        )
        return result.data[0]

    def list_for_user(self, user_id: str) -> list[dict]:
        result = (
            self._db.table("projects")
            .select("id, name, description, created_at, updated_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    def get(self, user_id: str, project_id: str) -> dict | None:
        result = (
            self._db.table("projects")
            .select("id, name, description, created_at, updated_at")
            .eq("id", project_id)
            .eq("user_id", user_id)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    def exists(self, user_id: str, project_id: str) -> bool:
        return self.get(user_id, project_id) is not None

    def delete(self, user_id: str, project_id: str) -> None:
        self._db.table("projects").delete().eq("id", project_id).eq("user_id", user_id).execute()
