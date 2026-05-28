from __future__ import annotations

from supabase import Client


class ConnectionRepository:
    def __init__(self, db: Client) -> None:
        self._db = db

    def list_for_user(self, user_id: str) -> list[dict]:
        result = (
            self._db.table("connections")
            .select("id, user_id, composio_account_id, provider, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []
