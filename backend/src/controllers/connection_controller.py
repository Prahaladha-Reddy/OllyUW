from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from src.dependencies import get_connection_service, require_auth
from src.models.connection import ConnectionListResponse
from src.services.connection_service import ConnectionService

router = APIRouter(prefix="/computer", tags=["connections"])


@router.get("/connections", response_model=ConnectionListResponse)
async def list_connections(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[ConnectionService, Depends(get_connection_service)],
) -> ConnectionListResponse:
    return ConnectionListResponse(connections=service.list_connections(current_user["user_id"]))
