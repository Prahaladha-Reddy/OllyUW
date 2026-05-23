from __future__ import annotations

from supabase import Client


class ConversationRepository:
    def __init__(self, db: Client) -> None:
        self._db = db

    def create(self, user_id: str, project_id: str, title: str) -> dict:
        result = (
            self._db.table("conversations")
            .insert({"user_id": user_id, "project_id": project_id, "title": title})
            .execute()
        )
        return result.data[0]

    def list_for_project(self, user_id: str, project_id: str) -> list[dict]:
        result = (
            self._db.table("conversations")
            .select("id, project_id, title, session_id, created_at, updated_at")
            .eq("project_id", project_id)
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []

    def get(self, user_id: str, project_id: str, conversation_id: str) -> dict | None:
        result = (
            self._db.table("conversations")
            .select("id, project_id, title, session_id, created_at, updated_at")
            .eq("id", conversation_id)
            .eq("project_id", project_id)
            .eq("user_id", user_id)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    def update_session_id(self, user_id: str, conversation_id: str, session_id: str | None) -> None:
        self._db.table("conversations").update({"session_id": session_id}).eq(
            "id", conversation_id
        ).eq("user_id", user_id).execute()

    def delete(self, user_id: str, conversation_id: str) -> None:
        self._db.table("conversations").delete().eq("id", conversation_id).eq("user_id", user_id).execute()

    def count_by_project(self, user_id: str, project_ids: list[str]) -> dict[str, int]:
        if not project_ids:
            return {}
        result = (
            self._db.table("conversations")
            .select("project_id")
            .in_("project_id", project_ids)
            .eq("user_id", user_id)
            .execute()
        )
        counts: dict[str, int] = {}
        for row in (result.data or []):
            pid = row["project_id"]
            counts[pid] = counts.get(pid, 0) + 1
        return counts
