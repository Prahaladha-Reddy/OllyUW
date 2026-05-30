"""Load /home/user/soul.md — agent personality and style preferences."""
from __future__ import annotations

from pathlib import Path

_SOUL_PATH = Path("/home/user/soul.md")

_DEFAULT_SOUL = """\
# Communication Style
- Be direct and concise. No filler words or corporate speak.
- Use code examples instead of long explanations when possible.
- When you don't know something, say so clearly.

# Approach
- Think step by step for complex problems.
- Ask clarifying questions when requirements are ambiguous.
- Show your work: explain reasoning for non-obvious decisions.
"""


def load_soul() -> str:
    """Return soul.md content or a sensible default."""
    if _SOUL_PATH.exists():
        content = _SOUL_PATH.read_text(encoding="utf-8").strip()
        if content:
            return content
    return _DEFAULT_SOUL


def soul_section() -> str:
    """Formatted section for injection into the system prompt."""
    content = load_soul()
    return f"\n---\n## Your Personality & Style\n{content}"
