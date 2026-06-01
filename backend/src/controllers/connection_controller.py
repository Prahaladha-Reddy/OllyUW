from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.dependencies import get_connection_service, require_auth
from src.models.connection import (
    ConnectionListResponse,
    InitiateConnectionResponse,
    ToolkitListResponse,
)
from src.services.connection_service import ConnectionService

router = APIRouter(prefix="/computer", tags=["connections"])


@router.get("/connections", response_model=ConnectionListResponse)
async def list_connections(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[ConnectionService, Depends(get_connection_service)],
) -> ConnectionListResponse:
    return ConnectionListResponse(connections=service.list_connections(current_user["user_id"]))


@router.get("/connections/toolkits", response_model=ToolkitListResponse)
async def list_toolkits(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[ConnectionService, Depends(get_connection_service)],
    connected_only: bool = False,
) -> ToolkitListResponse:
    return ToolkitListResponse(
        toolkits=service.list_toolkits(current_user["user_id"], connected_only=connected_only)
    )


@router.post("/connections/{toolkit}/connect", response_model=InitiateConnectionResponse)
async def initiate_connection(
    toolkit: str,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[ConnectionService, Depends(get_connection_service)],
    callback_url: str | None = None,
) -> InitiateConnectionResponse:
    try:
        return service.initiate_connection(current_user["user_id"], toolkit, callback_url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/connections/{toolkit}", status_code=204)
async def disconnect(
    toolkit: str,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[ConnectionService, Depends(get_connection_service)],
) -> None:
    service.disconnect(current_user["user_id"], toolkit)
