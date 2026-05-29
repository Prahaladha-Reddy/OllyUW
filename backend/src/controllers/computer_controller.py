from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

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


@router.post("/runtime/reset", response_model=ComputerResponse)
async def reset_runtime(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[ComputerService, Depends(get_computer_service)],
) -> ComputerResponse:
    """Clear sandbox_id and snapshot_id so the next Start creates fresh from template."""
    return ComputerResponse(computer=service.reset_runtime(current_user["user_id"]))


@router.get("/runtime/debug")
async def debug_runtime(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[ComputerService, Depends(get_computer_service)],
) -> dict:
    """Run diagnostic commands inside the sandbox and return output."""
    return await service.debug_runtime(current_user["user_id"])


@router.post("/workspace/upload", status_code=201)
async def upload_workspace_files(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[ComputerService, Depends(get_computer_service)],
    files: list[UploadFile] = File(description="One or more files to upload to the workspace"),
    path: str = Form(default="", description="Destination folder inside workspace (e.g. 'submissions/acme/')"),
) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    file_data = [(f.filename or "file", await f.read()) for f in files]
    try:
        written = await service.upload_workspace_files(current_user["user_id"], file_data, path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"written": written}


@router.get("/workspace")
async def list_workspace_files(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[ComputerService, Depends(get_computer_service)],
) -> dict:
    try:
        files = await service.list_workspace_files(current_user["user_id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"files": files}
