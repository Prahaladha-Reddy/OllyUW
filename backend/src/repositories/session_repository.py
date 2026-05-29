from __future__ import annotations

from supabase import Client


class SessionRepository:
    def __init__(self, db: Client) -> None:
        self._db = db
        self._session_cols = "id, user_id, computer_id, title, created_at, updated_at"
        self._message_cols = "id, session_id, user_id, role, content, model, citations, created_at"

    def list_by_user(self, user_id: str) -> list[dict]:
        result = (
            self._db.table("sessions")
            .select(self._session_cols)
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    def get(self, session_id: str, user_id: str) -> dict | None:
        result = (
            self._db.table("sessions")
            .select(self._session_cols)
            .eq("id", session_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    def create(self, user_id: str, computer_id: str, title: str) -> dict:
        result = (
            self._db.table("sessions")
            .insert({"user_id": user_id, "computer_id": computer_id, "title": title})
            .select(self._session_cols)
            .execute()
        )
        return result.data[0]

    def delete(self, session_id: str, user_id: str) -> None:
        self._db.table("sessions").delete().eq("id", session_id).eq("user_id", user_id).execute()

    def list_messages(self, session_id: str, user_id: str) -> list[dict]:
        result = (
            self._db.table("session_messages")
            .select(self._message_cols)
            .eq("session_id", session_id)
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []

    def add_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        model: str | None = None,
        citations: list | None = None,
    ) -> dict:
        row: dict = {
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "content": content,
        }
        if model:
            row["model"] = model
        if citations:
            row["citations"] = citations
        result = (
            self._db.table("session_messages")
            .insert(row)
            .select(self._message_cols)
            .execute()
        )
        return result.data[0]
