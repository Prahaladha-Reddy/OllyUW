"""File data access."""
from __future__ import annotations

from supabase import Client


class FileRepository:
    def __init__(self, db: Client) -> None:
        self._db = db

    def create(
        self,
        *,
        file_id: str,
        user_id: str,
        project_id: str,
        original_name: str,
        storage_path: str,
        file_size: int | None,
        status: str,
        error_message: str | None = None,
    ) -> dict:
        row = {
            "id": file_id,
            "project_id": project_id,
            "user_id": user_id,
            "original_name": original_name,
            "storage_path": storage_path,
            "file_size": file_size,
            "status": status,
            "error_message": error_message,
        }
        result = self._db.table("files").insert(row).execute()
        return result.data[0]

    def list_for_project(self, user_id: str, project_id: str) -> list[dict]:
        result = (
            self._db.table("files")
            .select("id, original_name, storage_path, file_size, status, error_message, created_at")
            .eq("project_id", project_id)
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []

    def list_ready_for_project(self, user_id: str, project_id: str) -> list[dict]:
        """Only files that uploaded successfully — used when materialising a sandbox workspace."""
        result = (
            self._db.table("files")
            .select("original_name, storage_path")
            .eq("project_id", project_id)
            .eq("user_id", user_id)
            .eq("status", "ready")
            .execute()
        )
        return result.data or []

    def get(self, user_id: str, project_id: str, file_id: str) -> dict | None:
        result = (
            self._db.table("files")
            .select("id, storage_path")
            .eq("id", file_id)
            .eq("project_id", project_id)
            .eq("user_id", user_id)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    def delete(self, user_id: str, file_id: str) -> None:
        self._db.table("files").delete().eq("id", file_id).eq("user_id", user_id).execute()

    def storage_paths_for_project(self, user_id: str, project_id: str) -> list[str]:
        """Used during cascade delete — returns all storage paths to remove from the bucket."""
        result = (
            self._db.table("files")
            .select("storage_path")
            .eq("project_id", project_id)
            .eq("user_id", user_id)
            .execute()
        )
        return [r["storage_path"] for r in (result.data or []) if r["storage_path"]]

    def count_by_project(self, user_id: str, project_ids: list[str]) -> dict[str, int]:
        if not project_ids:
            return {}
        result = (
            self._db.table("files")
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
