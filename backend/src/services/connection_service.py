from __future__ import annotations

from src.models.connection import ConnectionRecord
from src.repositories.connection_repository import ConnectionRepository


def _to_record(row: dict) -> ConnectionRecord:
    return ConnectionRecord(
        id=row["id"],
        user_id=row["user_id"],
        composio_account_id=row["composio_account_id"],
        provider=row["provider"],
        created_at=row["created_at"],
    )


class ConnectionService:
    def __init__(self, connection_repo: ConnectionRepository) -> None:
        self._connections = connection_repo

    def list_connections(self, user_id: str) -> list[ConnectionRecord]:
        return [_to_record(row) for row in self._connections.list_for_user(user_id)]
