from __future__ import annotations

from src.models.computer import ComputerRecord
from src.repositories.computer_repository import ComputerRepository


def _to_record(row: dict) -> ComputerRecord:
    return ComputerRecord(
        id=row["id"],
        user_id=row["user_id"],
        status=row["status"],
        last_active=row["last_active"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class ComputerService:
    def __init__(self, computer_repo: ComputerRepository) -> None:
        self._computers = computer_repo

    def get_or_create(self, user_id: str) -> ComputerRecord:
        row = self._computers.get_by_user(user_id)
        if row is None:
            row = self._computers.create_default(user_id)
        return _to_record(row)
