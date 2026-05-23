from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from src.dependencies import get_file_service, get_project_service, require_auth
from src.models.file import UploadFilesResponse
from src.models.project import (
    CreateProjectRequest,
    ProjectDetail,
    ProjectsListResponse,
)
from src.services.file_service import FileService
from src.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectDetail, status_code=201)
async def create_project(
    body: CreateProjectRequest,
    service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[dict, Depends(require_auth)],
) -> ProjectDetail:
    return await service.create(current_user["user_id"], body.name, body.description)


@router.get("", response_model=ProjectsListResponse)
async def list_projects(
    service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[dict, Depends(require_auth)],
) -> ProjectsListResponse:
    projects = await service.list_for_user(current_user["user_id"])
    return ProjectsListResponse(projects=projects)


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[dict, Depends(require_auth)],
) -> ProjectDetail:
    return await service.get(current_user["user_id"], project_id)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[dict, Depends(require_auth)],
) -> Response:
    await service.delete(current_user["user_id"], project_id)
    return Response(status_code=204)


@router.post("/{project_id}/files", response_model=UploadFilesResponse, status_code=202)
async def upload_files(
    project_id: str,
    service: Annotated[FileService, Depends(get_file_service)],
    current_user: Annotated[dict, Depends(require_auth)],
    files: list[UploadFile] = File(description="One or more files to attach to the project"),
) -> UploadFilesResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    return await service.upload(
        user_id=current_user["user_id"], project_id=project_id, uploads=files,
    )


@router.delete("/{project_id}/files/{file_id}")
async def delete_file(
    project_id: str,
    file_id: str,
    service: Annotated[FileService, Depends(get_file_service)],
    current_user: Annotated[dict, Depends(require_auth)],
) -> Response:
    await service.delete(current_user["user_id"], project_id, file_id)
    return Response(status_code=204)
