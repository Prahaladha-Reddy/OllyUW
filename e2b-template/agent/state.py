from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.config import HISTORY_WINDOW, STATE_PATH
from agent.log import log


def load(path: Path = STATE_PATH) -> list[dict[str, Any]]:
    """Read messages from agent_state.json. Tolerates missing/corrupt files."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        messages = data.get("messages", [])
        return messages if isinstance(messages, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("could not read state file: %s", exc)
        return []


def save(messages: list[dict[str, Any]], path: Path = STATE_PATH) -> None:
    """Persist messages to agent_state.json (pretty-printed for debuggability)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"messages": messages}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def recent(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    start = max(0, len(messages) - HISTORY_WINDOW)
    while start > 0 and messages[start].get("role") == "tool":
        start -= 1

    window = messages[start:]
    seen_tool_call_ids: set[str] = set()
    safe: list[dict[str, Any]] = []
    skipped_orphan_tools = 0

    for message in window:
        role = message.get("role", "")
        if role == "assistant":
            for call in message.get("tool_calls") or []:
                call_id = str(call.get("id") or "")
                if call_id:
                    seen_tool_call_ids.add(call_id)
            safe.append(message)
        elif role == "tool":
            tool_call_id = str(message.get("tool_call_id") or "")
            if tool_call_id and tool_call_id in seen_tool_call_ids:
                safe.append(message)
            else:
                skipped_orphan_tools += 1
        else:
            safe.append(message)

    if skipped_orphan_tools:
        log.warning(
            "dropped %d orphan tool message(s) while building model history",
            skipped_orphan_tools,
        )
    return safe
