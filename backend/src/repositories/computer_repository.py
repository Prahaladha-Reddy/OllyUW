from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client


class ComputerRepository:
    def __init__(self, db: Client) -> None:
        self._db = db
        self._columns = (
            "id, user_id, status, runtime_state, sandbox_id, snapshot_id, "
            "workspace_path, git_enabled, desktop_host, desktop_port, desktop_url, "
            "last_booted_at, last_paused_at, last_snapshot_at, error_message, "
            "last_active, created_at, updated_at"
        )

    def get_by_user(self, user_id: str) -> dict | None:
        result = (
            self._db.table("computers")
            .select(self._columns)
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
            "runtime_state": "stopped",
            "last_active": now,
        }
        result = self._db.table("computers").insert(row).execute()
        return result.data[0]

    def update(self, computer_id: str, fields: dict) -> dict:
        result = (
            self._db.table("computers")
            .update(fields)
            .eq("id", computer_id)
            .select(self._columns)
            .execute()
        )
        rows = result.data or []
        if not rows:
            raise ValueError(f"computer not found: {computer_id}")
        return rows[0]
