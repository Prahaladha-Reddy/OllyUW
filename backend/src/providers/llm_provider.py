from __future__ import annotations

from enum import Enum
from typing import Any
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI

from src.config import get_settings

load_dotenv()
class LLMMode(str, Enum):
    MODAL_STANDARD = "modal_standard"
    MODAL_TURBO = "modal_turbo"
    DEEPSEEK = "deepseek"


def get_llm(mode: LLMMode = LLMMode.MODAL_TURBO, **kwargs: Any) -> ChatOpenAI:
    """
    Return a LangChain ChatOpenAI instance pointed at the right provider.
    All providers expose an OpenAI-compatible endpoint so the agent code is identical.
    """
    settings = get_settings()

    if mode == LLMMode.DEEPSEEK:
        return ChatOpenAI(
            model=settings.deepseek_model,
            base_url=f"{settings.deepseek_base_url}/v1",
            api_key=settings.deepseek_api_key,
            temperature=0,
            **kwargs,
        )

    base_url = (
        settings.modal_turbo_base_url
        if mode == LLMMode.MODAL_TURBO
        else settings.modal_standard_base_url
    )
    if not base_url:
        raise RuntimeError(f"No base URL configured for LLM mode: {mode}")

    base_url = base_url.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"

    return ChatOpenAI(
        model=settings.modal_model,
        base_url=base_url,
        api_key=settings.modal_api_key,
        temperature=0,
        timeout=180,
        max_retries=1,
        **kwargs,
    )


def ask_once(prompt: str, mode: LLMMode = LLMMode.MODAL_TURBO) -> str:
    """Convenience wrapper for quick one-shot queries (testing / evals)."""
    llm = get_llm(mode)
    response = llm.invoke(prompt)
    return str(response.content)
