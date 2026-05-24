from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from agent.log import log


@lru_cache(maxsize=1)
def _client():
    api_key = os.environ.get("MEM0_API_KEY", "").strip()
    if not api_key:
        log.info("mem0 disabled (no MEM0_API_KEY)")
        return None
    try:
        from mem0 import MemoryClient

        return MemoryClient(api_key=api_key)
    except Exception:
        log.exception("mem0 client init failed")
        return None


def _scope() -> dict[str, str]:
    session_id = os.environ.get("SESSION_ID", "unknown")
    return {
        "user_id":  os.environ.get("OLLYUW_USER_ID", "anon"),
        "agent_id": os.environ.get("OLLYUW_PROJECT_ID", "default"),
        "run_id":   os.environ.get("OLLYUW_CONVERSATION_ID", session_id),
    }


def add_exchange(user_text: str, assistant_text: str) -> None:
    """Persist a (user, assistant) pair to long-term memory."""
    client = _client()
    if client is None or not (user_text or assistant_text):
        return
    try:
        client.add(
            messages=[
                {"role": "user",      "content": user_text},
                {"role": "assistant", "content": assistant_text},
            ],
            **_scope(),
        )
        log.info("mem0_add stored exchange user_len=%d asst_len=%d",
                 len(user_text), len(assistant_text))
    except Exception:
        log.exception("mem0_add failed")


def add_note(text: str, category: str = "note") -> str:
    """Explicitly write a single note. Returns a human message."""
    client = _client()
    if client is None:
        return "mem0 not configured (no MEM0_API_KEY)"
    try:
        client.add(
            messages=[{"role": "user", "content": text}],
            metadata={"category": category},
            **_scope(),
        )
        return f"saved note: {text[:80]}{'...' if len(text) > 80 else ''}"
    except Exception as exc:
        log.exception("mem0_add note failed")
        return f"mem0 error: {exc}"


def search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Semantic search over the current scope's memories."""
    client = _client()
    if client is None:
        return []
    try:
        scope = _scope()
        results = client.search(
            query=query,
            filters={"user_id": scope["user_id"], "agent_id": scope["agent_id"]},
            limit=limit,
        )
        if isinstance(results, dict):
            results = results.get("results", []) or results.get("memories", [])
        return list(results or [])
    except Exception:
        log.exception("mem0_search failed")
        return []


def format_search_results(results: list[dict[str, Any]]) -> str:
    """Format search results as human-readable text for the model."""
    if not results:
        return "(no relevant memories found)"
    lines = []
    for r in results:
        text = r.get("memory") or r.get("text") or r.get("content") or ""
        score = r.get("score")
        score_str = f" (score={score:.2f})" if isinstance(score, (int, float)) else ""
        lines.append(f"- {text}{score_str}")
    return "\n".join(lines)
