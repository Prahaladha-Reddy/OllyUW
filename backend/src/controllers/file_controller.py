from __future__ import annotations

import urllib.parse

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from src.dependencies import get_file_service, require_auth
from src.models.file import (
    CreateFolderRequest,
    FileListResponse,
    FileResponse,
    UpdateNodeRequest,
    UploadFilesResponse,
)
from src.services.file_service import FileService

router = APIRouter(prefix="/computer", tags=["files"])


@router.get("/files", response_model=FileListResponse)
async def list_files(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[FileService, Depends(get_file_service)],
) -> FileListResponse:
    return FileListResponse(files=service.list_files(current_user["user_id"]))


@router.get("/files/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[FileService, Depends(get_file_service)],
) -> FileResponse:
    return FileResponse(file=service.get_file(current_user["user_id"], file_id))


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[FileService, Depends(get_file_service)],
) -> Response:
    downloaded = await service.download_file(current_user["user_id"], file_id)
    quoted_filename = urllib.parse.quote(downloaded.filename)
    return Response(
        content=downloaded.content,
        media_type=downloaded.media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}",
        },
    )


@router.post("/files", response_model=UploadFilesResponse, status_code=201)
async def upload_files(
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[FileService, Depends(get_file_service)],
    parent_folder_id: str | None = Form(default=None),
    relative_paths: list[str] | None = Form(default=None),
    files: list[UploadFile] = File(description="One or more files to attach to the computer"),
) -> UploadFilesResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    return await service.upload_files(
        user_id=current_user["user_id"],
        uploads=files,
        parent_folder_id=parent_folder_id,
        relative_paths=relative_paths,
    )


@router.post("/folders", response_model=FileResponse, status_code=201)
async def create_folder(
    request: CreateFolderRequest,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[FileService, Depends(get_file_service)],
) -> FileResponse:
    return FileResponse(file=service.create_folder(current_user["user_id"], request))


@router.get("/folders/{folder_id}/children", response_model=FileListResponse)
async def list_folder_children(
    folder_id: str,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[FileService, Depends(get_file_service)],
) -> FileListResponse:
    return FileListResponse(files=service.list_folder_children(current_user["user_id"], folder_id))


@router.patch("/files/{file_id}", response_model=FileResponse)
async def update_file(
    file_id: str,
    request: UpdateNodeRequest,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[FileService, Depends(get_file_service)],
) -> FileResponse:
    return FileResponse(file=await service.update_file(current_user["user_id"], file_id, request))


@router.patch("/folders/{folder_id}", response_model=FileResponse)
async def update_folder(
    folder_id: str,
    request: UpdateNodeRequest,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[FileService, Depends(get_file_service)],
) -> FileResponse:
    return FileResponse(file=await service.update_folder(current_user["user_id"], folder_id, request))


@router.delete("/files/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[FileService, Depends(get_file_service)],
) -> Response:
    await service.delete_file(current_user["user_id"], file_id)
    return Response(status_code=204)


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(
    folder_id: str,
    current_user: Annotated[dict, Depends(require_auth)],
    service: Annotated[FileService, Depends(get_file_service)],
) -> Response:
    await service.delete_folder(current_user["user_id"], folder_id)
    return Response(status_code=204)
