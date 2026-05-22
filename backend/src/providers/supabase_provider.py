from __future__ import annotations

from src.config import get_settings

_client = None


def get_client():
    """
    Return a Supabase client.
    Stub — wire up once Supabase project is configured.
    """
    global _client
    if _client is not None:
        return _client

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY in .env."
        )

    from supabase import create_client  # lazy import

    _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client
