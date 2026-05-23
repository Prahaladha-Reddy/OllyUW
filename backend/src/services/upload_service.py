from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import UploadFile

from src.config import get_settings
from src.models.upload import FileStatus, ProcessedFile, UploadResponse
from src.providers import supabase_provider, unstructured_provider
from src.services.conversion_service import (
    classify,
    convert_direct,
    elements_to_markdown,
)


async def process_upload(files: list[UploadFile], user_id: str) -> UploadResponse:
    """Process all uploaded files in parallel and store markdown to Supabase."""
    submission_id = str(uuid.uuid4())
    tasks = [_process_one(f, user_id, submission_id) for f in files]
    results: list[ProcessedFile] = list(await asyncio.gather(*tasks))
    return UploadResponse(submission_id=submission_id, files=results)


async def _process_one(upload: UploadFile, user_id: str, submission_id: str) -> ProcessedFile:
    filename = upload.filename or "unnamed_file"
    kind = classify(filename)

    if kind == "rejected":
        suffix = Path(filename).suffix.lower() or "(no extension)"
        return ProcessedFile(
            original_name=filename,
            status=FileStatus.SKIPPED,
            error=f"File type {suffix!r} is not supported yet",
        )

    try:
        content = await upload.read()

        if kind == "unstructured":
            elements = await unstructured_provider.partition(content, filename)
            md_text = elements_to_markdown(elements)
        else:
            md_text = await asyncio.to_thread(convert_direct, content, filename)

        storage_path = f"{user_id}/{submission_id}/{Path(filename).stem}.md"

        await asyncio.to_thread(
            _upload_to_storage,
            storage_path,
            md_text.encode("utf-8"),
        )

        return ProcessedFile(
            original_name=filename,
            status=FileStatus.OK,
            storage_path=storage_path,
        )

    except Exception as exc:
        return ProcessedFile(
            original_name=filename,
            status=FileStatus.ERROR,
            error=str(exc),
        )


def _upload_to_storage(path: str, data: bytes) -> None:
    settings = get_settings()
    client = supabase_provider.get_service_client()
    client.storage.from_(settings.supabase_bucket).upload(
        path=path,
        file=data,
        file_options={"content-type": "text/markdown", "upsert": "true"},
    )
