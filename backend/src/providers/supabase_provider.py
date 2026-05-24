"""
Supabase client factory.
No queries here — repositories use these clients, storage_provider uses them too.

NOTE: We intentionally do NOT cache clients. The Supabase SDK uses httpx with
HTTP/2 connection pooling, and Supabase's load balancer drops idle HTTP/2
connections. Reusing a cached client across requests hits stale connections
and throws `httpx.RemoteProtocolError: Server disconnected`. Creating a fresh
client per request avoids this entirely. Overhead is negligible (~1ms per call)
for our volume.
"""
from __future__ import annotations

from supabase import Client, create_client

from src.config import get_settings


def get_anon_client() -> Client:
    """Publishable / anon key client. Use for auth flows that act AS the user."""
    settings = get_settings()
    if not settings.supabase.url or not settings.supabase.publishable_key:
        raise RuntimeError("Supabase is not configured: missing SUPABASE_URL or SUPABASE_PUBLISHABLE_KEY")
    return create_client(settings.supabase.url, settings.supabase.publishable_key)


def get_service_client() -> Client:
    """Service-role key client. Use for backend-only DB / Storage ops that bypass RLS."""
    settings = get_settings()
    key = settings.supabase.secret_key or settings.supabase.publishable_key
    if not settings.supabase.url or not key:
        raise RuntimeError("Supabase is not configured: missing SUPABASE_URL or SUPABASE_SECRET_KEY")
    return create_client(settings.supabase.url, key)
