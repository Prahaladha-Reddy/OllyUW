"""
Composio client factory.

One cached instance per process — the Composio client holds no stateful
connections, so caching is safe and avoids re-reading the API key on every
request.
"""
from __future__ import annotations

from functools import lru_cache

from composio import Composio

from src.config import get_settings


@lru_cache(maxsize=1)
def get_client() -> Composio:
    settings = get_settings()
    if not settings.composio_api_key:
        raise RuntimeError("Composio is not configured: missing COMPOSIO_API_KEY")
    return Composio(api_key=settings.composio_api_key)
