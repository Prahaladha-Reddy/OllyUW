from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from agent.log import log

_base_url = os.environ.get("LANGFUSE_BASE_URL", "").strip()
if _base_url and not os.environ.get("LANGFUSE_HOST"):
    os.environ["LANGFUSE_HOST"] = _base_url


def _enabled() -> bool:
    return bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
        and os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
    )


@lru_cache(maxsize=1)
def _langfuse():
    if not _enabled():
        log.info("langfuse disabled (no LANGFUSE_PUBLIC_KEY/SECRET_KEY)")
        return None
    try:
        from langfuse import Langfuse

        return Langfuse()
    except Exception:
        log.exception("langfuse init failed")
        return None


def _trace_metadata() -> dict[str, Any]:
    session_id = os.environ.get("SESSION_ID", "unknown")
    return {
        "user_id":    os.environ.get("OLLYUW_USER_ID", "anon"),
        "session_id": os.environ.get("OLLYUW_CONVERSATION_ID", session_id),
        "tags":       ["ollyuw", os.environ.get("OLLYUW_PROJECT_ID", "default")],
    }


def callback_handler() -> list[Any]:
    """Return a list with a Langfuse CallbackHandler, or [] if disabled."""
    client = _langfuse()
    if client is None:
        return []
    try:
        from langfuse.langchain import CallbackHandler

        return [CallbackHandler(langfuse_client=client)]
    except Exception:
        log.exception("langfuse CallbackHandler init failed")
        return []


def openai_module():
    if _enabled():
        try:
            from langfuse import openai as lf_openai  

            return lf_openai
        except Exception:
            log.exception("langfuse.openai wrapper unavailable; using stock openai")
    import openai

    return openai


def flush() -> None:
    client = _langfuse()
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        log.exception("langfuse flush failed")


def trace_metadata() -> dict[str, Any]:
    return _trace_metadata()
