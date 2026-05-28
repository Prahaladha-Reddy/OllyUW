from __future__ import annotations

from src.models.vault import VaultItemRecord
from src.repositories.vault_repository import VaultRepository


def _to_record(row: dict) -> VaultItemRecord:
    return VaultItemRecord(
        id=row["id"],
        user_id=row["user_id"],
        item_type=row["item_type"],
        key=row["key"],
        encrypted_data=row["encrypted_data"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class VaultService:
    def __init__(self, vault_repo: VaultRepository) -> None:
        self._vault = vault_repo

    def list_items(self, user_id: str) -> list[VaultItemRecord]:
        return [_to_record(row) for row in self._vault.list_for_user(user_id)]
