"""Update memory.md and soul.md; read session summaries."""
from __future__ import annotations

import json
from pathlib import Path

_MEMORY = Path("/home/user/memory.md")
_SOUL = Path("/home/user/soul.md")
_SESSIONS = Path("/home/user/sessions")


def update_memory(content: str) -> str:
    """Overwrite /home/user/memory.md with new markdown content."""
    _MEMORY.parent.mkdir(parents=True, exist_ok=True)
    _MEMORY.write_text(content, encoding="utf-8")
    return f"memory.md updated ({len(content)} chars)"


def append_memory(section: str, content: str) -> str:
    """Append a new section to memory.md without clobbering existing content."""
    current = _MEMORY.read_text(encoding="utf-8") if _MEMORY.exists() else ""
    new_content = (
        current.rstrip() + f"\n\n## {section}\n{content}\n"
        if current.strip()
        else f"## {section}\n{content}\n"
    )
    _MEMORY.parent.mkdir(parents=True, exist_ok=True)
    _MEMORY.write_text(new_content, encoding="utf-8")
    return f"appended section '{section}' to memory.md"


def update_soul(content: str) -> str:
    """Overwrite /home/user/soul.md with new content (personality / style)."""
    _SOUL.parent.mkdir(parents=True, exist_ok=True)
    _SOUL.write_text(content, encoding="utf-8")
    return f"soul.md updated ({len(content)} chars)"


def read_session_summary(session_id: str = "") -> str:
    """Read summary.md for a session; falls back to recent chat history.
    Pass an empty session_id to list all available sessions."""
    if not _SESSIONS.exists():
        return "no sessions directory found"

    if session_id:
        sess_dir = _SESSIONS / session_id
        summary = sess_dir / "summary.md"
        if summary.exists():
            return summary.read_text(encoding="utf-8")
        state = sess_dir / "agent_state.json"
        if state.exists():
            try:
                data = json.loads(state.read_text())
                msgs = data.get("messages", [])[-10:]
                lines = [
                    f"**{m['role']}:** {str(m.get('content', ''))[:500]}"
                    for m in msgs
                    if m.get("role") in ("user", "assistant")
                ]
                return "\n\n".join(lines) or "no messages"
            except Exception as e:
                return f"error reading session: {e}"
        return f"session not found: {session_id}"

    results = []
    for d in sorted(_SESSIONS.iterdir()):
        if not d.is_dir():
            continue
        summary = d / "summary.md"
        preview = (
            summary.read_text(encoding="utf-8")[:200] + "..."
            if summary.exists()
            else "(no summary)"
        )
        results.append(f"**{d.name}**: {preview}")
    return "\n\n".join(results) if results else "no sessions found"
