from __future__ import annotations

from supabase import Client


class FileRepository:
    def __init__(self, db: Client) -> None:
        self._db = db

    def list_for_user(self, user_id: str) -> list[dict]:
        result = (
            self._db.table("files")
            .select(
                "id, user_id, parent_folder_id, name, original_name, storage_path, file_size, "
                "file_type, automation_trigger_id, created_at, updated_at"
            )
            .eq("user_id", user_id)
            .order("file_type", desc=False)
            .order("name", desc=False)
            .execute()
        )
        return result.data or []

    def get_for_user(self, user_id: str, file_id: str) -> dict | None:
        result = (
            self._db.table("files")
            .select(
                "id, user_id, parent_folder_id, name, original_name, storage_path, file_size, "
                "file_type, automation_trigger_id, created_at, updated_at"
            )
            .eq("user_id", user_id)
            .eq("id", file_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    def create_folder(
        self,
        *,
        file_id: str,
        computer_id: str,
        user_id: str,
        parent_folder_id: str | None,
        name: str,
        automation_trigger_id: str | None,
    ) -> dict:
        row = {
            "id": file_id,
            "computer_id": computer_id,
            "project_id": None,
            "user_id": user_id,
            "parent_folder_id": parent_folder_id,
            "name": name,
            "storage_path": None,
            "original_name": name,
            "file_type": "folder",
            "automation_trigger_id": automation_trigger_id,
            "status": "ready",
        }
        result = self._db.table("files").insert(row).execute()
        return result.data[0]

    def create_file(
        self,
        *,
        file_id: str,
        computer_id: str,
        user_id: str,
        parent_folder_id: str | None,
        name: str,
        storage_path: str,
        file_size: int,
    ) -> dict:
        row = {
            "id": file_id,
            "computer_id": computer_id,
            "project_id": None,
            "user_id": user_id,
            "parent_folder_id": parent_folder_id,
            "name": name,
            "storage_path": storage_path,
            "original_name": name,
            "file_size": file_size,
            "file_type": "file",
            "automation_trigger_id": None,
            "status": "ready",
            "error_message": None,
        }
        result = self._db.table("files").insert(row).execute()
        return result.data[0]

    def update_file(
        self,
        *,
        file_id: str,
        user_id: str,
        storage_path: str,
        file_size: int,
    ) -> dict:
        result = (
            self._db.table("files")
            .update(
                {
                    "storage_path": storage_path,
                    "file_size": file_size,
                    "status": "ready",
                    "error_message": None,
                }
            )
            .eq("id", file_id)
            .eq("user_id", user_id)
            .select(
                "id, user_id, parent_folder_id, name, original_name, storage_path, file_size, "
                "file_type, automation_trigger_id, created_at, updated_at"
            )
            .execute()
        )
        return result.data[0]

    def update_node(
        self,
        *,
        file_id: str,
        user_id: str,
        values: dict,
    ) -> dict:
        result = (
            self._db.table("files")
            .update(values)
            .eq("id", file_id)
            .eq("user_id", user_id)
            .select(
                "id, user_id, parent_folder_id, name, original_name, storage_path, file_size, "
                "file_type, automation_trigger_id, created_at, updated_at"
            )
            .execute()
        )
        return result.data[0]

    def delete_many(self, *, user_id: str, file_ids: list[str]) -> None:
        if not file_ids:
            return
        (
            self._db.table("files")
            .delete()
            .eq("user_id", user_id)
            .in_("id", file_ids)
            .execute()
        )
