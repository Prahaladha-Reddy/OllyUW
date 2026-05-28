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


@router.post("/runtime/start", response_model=ComputerResponse)
async def start_runtime(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[ComputerService, Depends(get_computer_service)],
) -> ComputerResponse:
    return ComputerResponse(computer=await service.start_runtime(current_user["user_id"]))


@router.post("/runtime/pause", response_model=ComputerResponse)
async def pause_runtime(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[ComputerService, Depends(get_computer_service)],
) -> ComputerResponse:
    return ComputerResponse(computer=await service.pause_runtime(current_user["user_id"]))


@router.post("/runtime/snapshot", response_model=ComputerResponse)
async def snapshot_runtime(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[ComputerService, Depends(get_computer_service)],
) -> ComputerResponse:
    return ComputerResponse(computer=await service.snapshot_runtime(current_user["user_id"]))


@router.post("/runtime/power-off", response_model=ComputerResponse)
async def power_off_runtime(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[ComputerService, Depends(get_computer_service)],
) -> ComputerResponse:
    return ComputerResponse(computer=await service.power_off_runtime(current_user["user_id"]))
