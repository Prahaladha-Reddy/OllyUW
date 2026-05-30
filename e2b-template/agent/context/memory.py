"""Load /home/user/memory.md — persistent user facts and project context."""
from __future__ import annotations

from pathlib import Path

_MEMORY_PATH = Path("/home/user/memory.md")


def load_memory() -> str | None:
    """Return memory.md content, or None if it doesn't exist yet."""
    if _MEMORY_PATH.exists():
        content = _MEMORY_PATH.read_text(encoding="utf-8").strip()
        return content if content else None
    return None


def memory_section() -> str:
    """Formatted section for injection into the system prompt. Empty string if no memory."""
    content = load_memory()
    if not content:
        return ""
    return f"\n---\n## User Context & Memory\n{content}"
