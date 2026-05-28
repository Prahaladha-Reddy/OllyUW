from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client


class ComputerRepository:
    def __init__(self, db: Client) -> None:
        self._db = db

    def get_by_user(self, user_id: str) -> dict | None:
        result = (
            self._db.table("computers")
            .select("id, user_id, status, last_active, created_at, updated_at")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    def create_default(self, user_id: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "user_id": user_id,
            "status": "sleeping",
            "last_active": now,
        }
        result = self._db.table("computers").insert(row).execute()
        return result.data[0]
