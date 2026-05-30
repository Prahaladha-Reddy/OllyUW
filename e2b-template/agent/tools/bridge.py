"""
Hermes-style deferred tool bridge.

The LLM discovers and calls non-core tools in three steps:
  1. tool_search("send email")           → names + one-line descriptions
  2. tool_describe("composio_gmail")     → full JSON schema
  3. tool_call("composio_gmail", {...})  → execute

BM25 scoring keeps relevant tools surfaced without embedding lookups.
"""
from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any

from agent.tools.registry import get_registry


def tool_search(query: str, top_k: int = 5) -> str:
    results = get_registry().search(query, top_k=top_k)
    if not results:
        return "no matching tools found — try a different query"
    lines = ["Matching tools (use tool_describe for full schema, tool_call to execute):"]
    for r in results:
        lines.append(f"  {r['name']}: {r['description']}")
    return "\n".join(lines)


def tool_describe(name: str) -> str:
    schema = get_registry().describe(name)
    if schema is None:
        close = [n for n in get_registry().all_names() if name.lower() in n.lower()]
        hint = f"  Did you mean: {', '.join(close[:3])}?" if close else ""
        return f"tool not found: {name!r}.{hint}  Use tool_search to find available tools."
    return json.dumps(schema, indent=2)


async def tool_call(name: str, args: dict[str, Any] | None = None) -> str:
    handler = get_registry().get_handler(name)
    if handler is None:
        return f"tool not found: {name!r}.  Use tool_search to discover tools."
    try:
        actual = args or {}
        if inspect.iscoroutinefunction(handler):
            result = await handler(**actual)
        else:
            result = await asyncio.to_thread(handler, **actual)
        return str(result)
    except TypeError as e:
        schema = get_registry().describe(name)
        params = (
            list(
                (schema.get("function") or {})
                .get("parameters", {})
                .get("properties", {})
                .keys()
            )
            if schema
            else []
        )
        return (
            f"wrong arguments for {name!r}: {e}\n"
            f"Parameters: {params}\n"
            "Use tool_describe to see the full schema."
        )
    except Exception as e:
        return f"error in {name!r}: {e}"
