"""
Supabase client factory.
No queries here — repositories use these clients, storage_provider uses them too.
"""
from __future__ import annotations

import threading

from supabase import Client, create_client

from src.config import get_settings

_lock = threading.Lock()
_anon_client: Client | None = None
_service_client: Client | None = None


def get_anon_client() -> Client:
    """Publishable / anon key client. Use for auth flows that act AS the user."""
    global _anon_client
    if _anon_client is not None:
        return _anon_client

    with _lock:
        if _anon_client is not None:
            return _anon_client
        settings = get_settings()
        if not settings.supabase.url or not settings.supabase.publishable_key:
            raise RuntimeError("Supabase is not configured: missing SUPABASE_URL or SUPABASE_PUBLISHABLE_KEY")
        _anon_client = create_client(settings.supabase.url, settings.supabase.publishable_key)
    return _anon_client


def get_service_client() -> Client:
    """Service-role key client. Use for backend-only DB / Storage ops that bypass RLS."""
    global _service_client
    if _service_client is not None:
        return _service_client

    with _lock:
        if _service_client is not None:
            return _service_client
        settings = get_settings()
        key = settings.supabase.secret_key or settings.supabase.publishable_key
        if not settings.supabase.url or not key:
            raise RuntimeError("Supabase is not configured: missing SUPABASE_URL or SUPABASE_SECRET_KEY")
        _service_client = create_client(settings.supabase.url, key)
    return _service_client
