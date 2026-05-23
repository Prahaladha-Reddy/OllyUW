"""
Application settings.

Flat env-var schema (no nesting) so the existing .env keeps working.
Grouped accessors expose them by concern: `settings.e2b.api_key`, `settings.supabase.url`, …
Providers and services only depend on the group they need.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).parent.parent.parent


# ── Grouped views (read-only dataclasses, populated from Settings) ──────────


@dataclass(frozen=True)
class E2BGroup:
    api_key: str
    template_id: str
    sandbox_timeout: int


@dataclass(frozen=True)
class RedisGroup:
    url: str


@dataclass(frozen=True)
class ModalGroup:
    standard_base_url: str
    turbo_base_url: str
    api_key: str
    model: str


@dataclass(frozen=True)
class DeepSeekGroup:
    api_key: str
    base_url: str
    model: str


@dataclass(frozen=True)
class SupabaseGroup:
    url: str
    publishable_key: str
    secret_key: str
    bucket: str


@dataclass(frozen=True)
class LangSmithGroup:
    api_key: str
    base_url: str
    tracing: bool


@dataclass(frozen=True)
class ServerGroup:
    host: str
    port: int
    log_level: str
    cors_origins: list[str]
    backend_url: str
    frontend_url: str


# ── Raw flat settings, loaded from .env ─────────────────────────────────────


class Settings(BaseSettings):
    # E2B
    e2b_api_key: str
    e2b_template_id: str = "base"
    e2b_sandbox_timeout: int = 1200

    # Redis
    redis_url: str

    # Modal (OSS LLM)
    modal_standard_base_url: str = ""
    modal_turbo_base_url: str = ""
    modal_api_key: str = "unused"
    modal_model: str = "google/gemma-4-26B-A4B-it"

    # DeepSeek (frontier LLM)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Supabase
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_bucket: str = "submissions"

    # LangSmith
    langsmith_api_key: str = ""
    langsmith_base_url: str = "https://smith.langchain.com"
    langsmith_tracing: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    cors_origins: list[str] = ["*"]
    backend_url: str = "http://localhost:8000"
    frontend_url: str = ""

    model_config = SettingsConfigDict(
        env_file=[ROOT / ".env", ROOT / "backend" / ".env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Grouped accessors (computed lazily; cheap)

    @property
    def e2b(self) -> E2BGroup:
        return E2BGroup(self.e2b_api_key, self.e2b_template_id, self.e2b_sandbox_timeout)

    @property
    def redis(self) -> RedisGroup:
        return RedisGroup(self.redis_url)

    @property
    def modal(self) -> ModalGroup:
        return ModalGroup(
            self.modal_standard_base_url,
            self.modal_turbo_base_url,
            self.modal_api_key,
            self.modal_model,
        )

    @property
    def deepseek(self) -> DeepSeekGroup:
        return DeepSeekGroup(self.deepseek_api_key, self.deepseek_base_url, self.deepseek_model)

    @property
    def supabase(self) -> SupabaseGroup:
        return SupabaseGroup(
            self.supabase_url,
            self.supabase_publishable_key,
            self.supabase_secret_key,
            self.supabase_bucket,
        )

    @property
    def langsmith(self) -> LangSmithGroup:
        return LangSmithGroup(self.langsmith_api_key, self.langsmith_base_url, self.langsmith_tracing)

    @property
    def server(self) -> ServerGroup:
        return ServerGroup(
            self.host, self.port, self.log_level, self.cors_origins,
            self.backend_url, self.frontend_url,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
