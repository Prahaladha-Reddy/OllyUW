from __future__ import annotations

import logging

from composio import Composio

from src.models.connection import (
    ConnectionRecord,
    InitiateConnectionResponse,
    ToolkitStatus,
)
from src.repositories.connection_repository import ConnectionRepository

logger = logging.getLogger("ollyuw.connections")


def _to_record(row: dict) -> ConnectionRecord:
    return ConnectionRecord(
        id=row["id"],
        user_id=row["user_id"],
        composio_account_id=row["composio_account_id"],
        provider=row["provider"],
        created_at=row["created_at"],
    )


class ConnectionService:
    def __init__(self, connection_repo: ConnectionRepository, composio: Composio) -> None:
        self._connections = connection_repo
        self._composio = composio

    def list_toolkits(self, user_id: str, connected_only: bool = False) -> list[ToolkitStatus]:
        """List toolkits. connected_only=True returns only the user's active connections."""
        try:
            resp = self._composio.connected_accounts.list(
                user_ids=[user_id],
                statuses=["ACTIVE"],
            )
            connected = {item.toolkit.slug.lower() for item in resp.items}

            if connected_only:
                return [
                    ToolkitStatus(
                        slug=slug,
                        name=slug.replace("_", " ").title(),
                        is_connected=True,
                    )
                    for slug in sorted(connected)
                ]

            # All-toolkits view: page through the catalog, mark which are connected.
            catalog = self._composio.toolkits.get()
            return [
                ToolkitStatus(
                    slug=item.slug,
                    name=getattr(item, "name", None) or item.slug.replace("_", " ").title(),
                    is_connected=item.slug.lower() in connected,
                )
                for item in catalog
            ]
        except Exception:
            logger.exception("failed to list toolkits for user %s", user_id)
            return []

    def initiate_connection(
        self, user_id: str, toolkit: str, callback_url: str | None = None
    ) -> InitiateConnectionResponse:
        toolkit = toolkit.lower()
        # Resolve (or auto-create) the Composio-managed auth config for this toolkit,
        # then initiate the connection. Passing callback_url makes Composio redirect
        # the user back to our app when OAuth completes.
        auth_config_id = self._composio.toolkits._get_auth_config_id(toolkit=toolkit)
        conn_req = self._composio.connected_accounts.initiate(
            user_id=user_id,
            auth_config_id=auth_config_id,
            callback_url=callback_url,
        )
        # Persist a pending record so the connections table stays in sync.
        self._connections.upsert(
            user_id=user_id,
            provider=toolkit,
            composio_account_id=conn_req.id,
        )
        if not conn_req.redirect_url:
            raise RuntimeError(
                f"Composio did not return a redirect URL for {toolkit!r}"
            )
        return InitiateConnectionResponse(
            toolkit=toolkit,
            redirect_url=conn_req.redirect_url,
        )

    def disconnect(self, user_id: str, toolkit: str) -> None:
        toolkit = toolkit.lower()
        # Delete every connected account for this user+toolkit on Composio's side.
        try:
            resp = self._composio.connected_accounts.list(
                user_ids=[user_id],
                toolkit_slugs=[toolkit],
            )
            for item in resp.items:
                try:
                    self._composio.connected_accounts.delete(item.id)
                except Exception:
                    logger.warning(
                        "could not delete Composio connected account %s (toolkit=%s)",
                        item.id,
                        toolkit,
                    )
        except Exception:
            logger.exception(
                "error fetching connections to delete for user=%s toolkit=%s", user_id, toolkit
            )
        # Always clean up our local record.
        self._connections.delete_by_provider(user_id, toolkit)

    def list_connections(self, user_id: str) -> list[ConnectionRecord]:
        return [_to_record(row) for row in self._connections.list_for_user(user_id)]
