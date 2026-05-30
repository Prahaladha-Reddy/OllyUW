from __future__ import annotations

import json
from typing import Any

from agent.config import SYSTEM_PROMPT
from agent.llm.compaction import recent_within_budget


def build_openai(messages: list[dict[str, Any]], model: str = "deepseek") -> list[dict[str, Any]]:
    """Translate history into raw OpenAI Chat Completions dicts."""
    chat: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in recent_within_budget(messages, model):
        role = m.get("role", "")
        content = m.get("content", "") or ""
        if role == "user":
            chat.append({"role": "user", "content": content})
        elif role == "assistant":
            item: dict[str, Any] = {"role": "assistant", "content": content}
            reasoning_content = m.get("reasoning_content")
            if reasoning_content:
                item["reasoning_content"] = reasoning_content
            tcs = m.get("tool_calls") or []
            if tcs:
                item["content"] = content or None
                item["tool_calls"] = _to_openai_tool_calls(tcs)
            chat.append(item)
        elif role == "tool":
            chat.append({
                "role": "tool",
                "tool_call_id": m.get("tool_call_id", ""),
                "content": content,
            })
    return chat


def _to_openai_tool_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert our compact tool-call dicts into the OpenAI wire format."""
    out: list[dict[str, Any]] = []
    for call in calls:
        args = call.get("args") or {}
        arguments = args if isinstance(args, str) else json.dumps(args, ensure_ascii=False)
        out.append({
            "id": call.get("id", ""),
            "type": "function",
            "function": {
                "name": call.get("name", ""),
                "arguments": arguments,
            },
        })
    return out


def obj_field(obj: Any, key: str, default: Any = None) -> Any:
    """
    Generic accessor that works whether `obj` is a dict, a pydantic model,
    or a plain SDK object. Used to read fields off raw OpenAI streaming
    chunks without caring which library's response objects we got back.
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    value = getattr(obj, key, default)
    if value is not default:
        return value
    model_dump = getattr(obj, "model_dump", None)
    if callable(model_dump):
        try:
            return model_dump(exclude_none=True).get(key, default)
        except TypeError:
            return model_dump().get(key, default)
    return default
