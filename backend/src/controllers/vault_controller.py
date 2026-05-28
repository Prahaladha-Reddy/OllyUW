from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from src.dependencies import get_vault_service, require_auth
from src.models.vault import VaultItemListResponse
from src.services.vault_service import VaultService

router = APIRouter(prefix="/computer/vault", tags=["vault"])


@router.get("/items", response_model=VaultItemListResponse)
async def list_vault_items(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[VaultService, Depends(get_vault_service)],
) -> VaultItemListResponse:
    return VaultItemListResponse(items=service.list_items(current_user["user_id"]))
