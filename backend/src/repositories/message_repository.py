"""Message persistence — chat history for conversations."""
from __future__ import annotations

from typing import Any

from supabase import Client


class MessageRepository:
    def __init__(self, db: Client) -> None:
        self._db = db

    def append(
        self,
        *,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        citations: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> dict:
        row = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "citations": citations,
            "model": model,
        }
        result = self._db.table("messages").insert(row).execute()
        return result.data[0]

    def list_for_conversation(
        self,
        user_id: str,
        conversation_id: str,
        limit: int = 200,
    ) -> list[dict]:
        result = (
            self._db.table("messages")
            .select("id, conversation_id, role, content, citations, model, created_at")
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return result.data or []
