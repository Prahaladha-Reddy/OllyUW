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

    def upsert(self, user_id: str, provider: str, composio_account_id: str) -> None:
        # Delete existing record first (no unique constraint on user_id+provider yet),
        # then insert fresh. Migration 006 adds the constraint so this becomes a
        # true upsert going forward.
        self._db.table("connections").delete().eq("user_id", user_id).eq("provider", provider).execute()
        self._db.table("connections").insert(
            {
                "user_id": user_id,
                "provider": provider,
                "composio_account_id": composio_account_id,
            }
        ).execute()

    def delete_by_provider(self, user_id: str, provider: str) -> None:
        self._db.table("connections").delete().eq("user_id", user_id).eq("provider", provider).execute()
