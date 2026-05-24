from __future__ import annotations

import os


def resolve(model: str) -> tuple[str, str, str]:
    """Return (base_url, api_key, model_name). `model` is one of: 'modal', 'deepseek'."""
    if model == "deepseek":
        return (
            os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            os.environ.get("DEEPSEEK_API_KEY", ""),
            os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        )
    # default: Modal-hosted Gemma 4 via vLLM
    return (
        os.environ.get("MODAL_TURBO_BASE_URL", ""),
        os.environ.get("MODAL_API_KEY", "unused"),
        os.environ.get("MODAL_MODEL", "google/gemma-4-26B-A4B-it"),
    )


def normalise_base_url(base_url: str) -> str:
    """Trim trailing slash and ensure the path ends in `/v1`."""
    base_url = base_url.rstrip("/")
    if base_url and not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    return base_url
