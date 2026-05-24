from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).parent.parent.parent




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
class Mem0Group:
    api_key: str


@dataclass(frozen=True)
class ParallelGroup:
    api_key: str


@dataclass(frozen=True)
class LangfuseGroup:
    public_key: str
    secret_key: str
    base_url: str


@dataclass(frozen=True)
class ServerGroup:
    host: str
    port: int
    log_level: str
    cors_origins: list[str]
    backend_url: str
    frontend_url: str



class Settings(BaseSettings):
    e2b_api_key: str
    e2b_template_id: str = "base"
    e2b_sandbox_timeout: int = 1200

    redis_url: str

    modal_standard_base_url: str = ""
    modal_turbo_base_url: str = ""
    modal_api_key: str = "unused"
    modal_model: str = "google/gemma-4-26B-A4B-it"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"

    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_bucket: str = "submissions"

    langsmith_api_key: str = ""
    langsmith_base_url: str = "https://smith.langchain.com"
    langsmith_tracing: bool = False

    mem0_api_key: str = ""

    parallel_api_key: str = ""

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"

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
    def mem0(self) -> Mem0Group:
        return Mem0Group(self.mem0_api_key)

    @property
    def parallel(self) -> ParallelGroup:
        return ParallelGroup(self.parallel_api_key)

    @property
    def langfuse(self) -> LangfuseGroup:
        return LangfuseGroup(
            self.langfuse_public_key,
            self.langfuse_secret_key,
            self.langfuse_base_url,
        )

    @property
    def server(self) -> ServerGroup:
        return ServerGroup(
            self.host, self.port, self.log_level, self.cors_origins,
            self.backend_url, self.frontend_url,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
