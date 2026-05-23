"""
Supabase Storage wrapper. All storage I/O lives here — no DB, no business logic.
Sync calls to the Supabase SDK; callers wrap in asyncio.to_thread.
"""
from __future__ import annotations

from src.config import get_settings
from src.providers import supabase_provider


def _bucket():
    settings = get_settings()
    return supabase_provider.get_service_client().storage.from_(settings.supabase.bucket)


def upload(path: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    _bucket().upload(
        path=path,
        file=data,
        file_options={"content-type": content_type, "upsert": "true"},
    )


def download(path: str) -> bytes:
    return _bucket().download(path)


def delete(paths: list[str]) -> None:
    if paths:
        _bucket().remove(paths)
