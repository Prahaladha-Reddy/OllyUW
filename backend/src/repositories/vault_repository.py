from __future__ import annotations

from supabase import Client


class VaultRepository:
    def __init__(self, db: Client) -> None:
        self._db = db

    def list_for_user(self, user_id: str) -> list[dict]:
        result = (
            self._db.table("vault_items")
            .select("id, user_id, item_type, key, encrypted_data, created_at, updated_at")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []
