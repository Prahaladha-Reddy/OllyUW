from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.dependencies import require_auth
from src.models.upload import UploadResponse
from src.services.upload_service import process_upload

logger = logging.getLogger("ollyuw.upload")
router = APIRouter(prefix="/upload", tags=["upload"])

_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB per file


@router.post("", response_model=UploadResponse, status_code=202)
async def upload_files(
    files: list[UploadFile] = File(description="One or more files to process"),
    current_user: dict = Depends(require_auth),
) -> UploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    for f in files:
        if f.size is not None and f.size > _MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"'{f.filename}' exceeds the 50 MB per-file limit",
            )

    try:
        return await process_upload(files, current_user["user_id"])
    except Exception as exc:
        logger.error("upload failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
