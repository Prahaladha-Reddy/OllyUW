from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    # E2B
    e2b_api_key: str
    e2b_template_id: str = "base"  # override once custom template is built
    e2b_sandbox_timeout: int = 1200  # seconds before idle sandbox is killed (20 min)

    # Redis
    redis_url: str

    # LLM — Modal (OSS)
    modal_standard_base_url: str = ""
    modal_turbo_base_url: str = ""
    modal_api_key: str = "unused"
    modal_model: str = "google/gemma-4-26B-A4B-it"

    # LLM — DeepSeek (frontier)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=[ROOT / ".env", ROOT / "backend" / ".env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
