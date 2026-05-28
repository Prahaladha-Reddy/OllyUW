from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from src.dependencies import get_computer_service, require_auth
from src.models.computer import ComputerResponse
from src.services.computer_service import ComputerService

router = APIRouter(prefix="/computer", tags=["computer"])

@router.get("", response_model=ComputerResponse)
async def get_computer(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[ComputerService, Depends(get_computer_service)],
) -> ComputerResponse:
    return ComputerResponse(computer=service.get_or_create(current_user["user_id"]))
