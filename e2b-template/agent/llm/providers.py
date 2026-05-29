from __future__ import annotations

import os


def resolve(model: str) -> tuple[str, str, str]:
    """Return (base_url, api_key, model_name). Always uses DeepSeek."""
    return (
        os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        os.environ.get("DEEPSEEK_API_KEY", ""),
        os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    )


def normalise_base_url(base_url: str) -> str:
    """Trim trailing slash and ensure the path ends in `/v1`."""
    base_url = base_url.rstrip("/")
    if base_url and not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    return base_url
