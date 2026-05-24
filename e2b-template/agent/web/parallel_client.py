from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from agent.log import log


@lru_cache(maxsize=1)
def _client():
    api_key = os.environ.get("PARALLEL_API_KEY", "").strip()
    if not api_key:
        log.info("parallel disabled (no PARALLEL_API_KEY)")
        return None
    try:
        from parallel import Parallel

        return Parallel(api_key=api_key, timeout=60.0, max_retries=1)
    except Exception:
        log.exception("parallel client init failed")
        return None


def web_search(query: str, max_results: int = 5) -> str:
    """
    LLM-optimised web search. Returns formatted text excerpts from top results.
    """
    client = _client()
    if client is None:
        return "web_search unavailable (no PARALLEL_API_KEY or SDK missing)"

    try:
        response = client.beta.search(
            objective=query,
            search_queries=[query],
            max_results=max_results,
        )
        return _format_search(response)
    except Exception as exc:
        log.exception("parallel.beta.search failed")
        return f"web search error: {type(exc).__name__}: {exc}"


def web_research(question: str, timeout: int = 90) -> str:
    """
    Deeper research via the `core` task processor. Slower (~30-60s) but
    returns a synthesised answer with citations rather than raw excerpts.
    Good for cross-referencing questions.
    """
    client = _client()
    if client is None:
        return "web_research unavailable (no PARALLEL_API_KEY or SDK missing)"

    try:
        result = client.task_run.execute(
            input=question,
            processor="core",
            timeout=float(timeout),
        )
        return _format_task_result(result)
    except Exception as exc:
        log.exception("parallel.task_run.execute failed")
        return f"web research error: {type(exc).__name__}: {exc}"




def _format_search(response: Any) -> str:
    """Pull excerpts out of a SearchResult-shaped response."""
    results = _attr(response, "results") or _attr(response, "search_results") or []
    if not results:
        if isinstance(response, dict):
            results = response.get("results", []) or response.get("search_results", [])
    if not results:
        return f"(no search results) raw: {str(response)[:300]}"

    lines: list[str] = []
    for r in results:
        title = _attr(r, "title") or "(untitled)"
        url   = _attr(r, "url") or ""
        excerpt = (
            _attr(r, "excerpt")
            or _attr(r, "snippet")
            or _attr(r, "content")
            or _attr(r, "text")
            or ""
        )
        lines.append(f"## {title}")
        if url:
            lines.append(f"<{url}>")
        if excerpt:
            lines.append(str(excerpt).strip())
        lines.append("")
    return "\n".join(lines).strip()


def _format_task_result(result: Any) -> str:
    output = _attr(result, "output")
    content = _attr(output, "content") if output is not None else None
    if content:
        return str(content)
    # Fall back to dict-ish access
    if isinstance(result, dict):
        if "output" in result and isinstance(result["output"], dict):
            return str(result["output"].get("content", result))
    return str(result)


def _attr(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)
