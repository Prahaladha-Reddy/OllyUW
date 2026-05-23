from __future__ import annotations

from src.config import get_settings

_client = None
_service_client = None


def get_client():
    """Publishable-key client — used for auth operations."""
    global _client
    if _client is not None:
        return _client

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in .env."
        )

    from supabase import create_client

    _client = create_client(settings.supabase_url, settings.supabase_publishable_key)
    return _client


def get_service_client():
    """Secret-key client — used for storage operations (bypasses RLS).
    Falls back to the publishable-key client if SUPABASE_SECRET_KEY is not set."""
    global _service_client
    if _service_client is not None:
        return _service_client

    settings = get_settings()
    key = settings.supabase_secret_key or settings.supabase_publishable_key
    if not settings.supabase_url or not key:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SECRET_KEY in .env."
        )

    from supabase import create_client

    _service_client = create_client(settings.supabase_url, key)
    return _service_client
