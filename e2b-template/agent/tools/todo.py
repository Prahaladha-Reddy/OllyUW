"""Persistent todo list."""
from __future__ import annotations

import json
import os
from pathlib import Path

# Stored alongside the agent state file.
_state_dir = Path(os.environ.get("AGENT_STATE_PATH", "/home/user/agent_state.json")).parent
_TODO_FILE = _state_dir / "agent_todo.json"


def _load() -> list[dict]:
    if _TODO_FILE.exists():
        try:
            return json.loads(_TODO_FILE.read_text())
        except Exception:
            pass
    return []


def _save(todos: list[dict]) -> None:
    _TODO_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TODO_FILE.write_text(json.dumps(todos, indent=2))


def _fmt(todos: list[dict]) -> str:
    if not todos:
        return "(no todos)"
    return "\n".join(
        f"{t['id']}. {'[x]' if t.get('done') else '[ ]'} {t['text']}"
        for t in todos
    )


def todo(action: str, text: str = "", id: int = 0) -> str:
    todos = _load()
    match action:
        case "list":
            return _fmt(todos)
        case "add":
            if not text:
                return "error: text required for 'add'"
            next_id = max((t["id"] for t in todos), default=0) + 1
            todos.append({"id": next_id, "text": text, "done": False})
            _save(todos)
            return f"added #{next_id}: {text}\n\n" + _fmt(todos)
        case "check" | "uncheck":
            done = action == "check"
            for t in todos:
                if t["id"] == id:
                    t["done"] = done
                    _save(todos)
                    return f"{'checked' if done else 'unchecked'} #{id}\n\n" + _fmt(todos)
            return f"#{id} not found"
        case "remove":
            before = len(todos)
            todos = [t for t in todos if t["id"] != id]
            _save(todos)
            return (f"removed #{id}" if len(todos) < before else f"#{id} not found") + "\n\n" + _fmt(todos)
        case _:
            return f"unknown action {action!r} — use: list | add | check | uncheck | remove"
