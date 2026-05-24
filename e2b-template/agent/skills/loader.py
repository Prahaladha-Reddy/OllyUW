"""
Load a skill body by name. Returns the markdown body (everything after the
--- frontmatter block), or None if the skill is not found.
"""
from __future__ import annotations

from pathlib import Path

from agent.skills.discovery import CATALOG_DIR, list_skills


def load_skill(name: str) -> str | None:
    """Return skill body for `name`, or None if not found."""
    # Try exact filename match first.
    direct = CATALOG_DIR / f"{name}.md"
    if direct.exists():
        return _body(direct)

    # Fall back to matching the `name:` frontmatter field.
    for entry in list_skills():
        if entry["name"] == name:
            return _body(Path(entry["path"]))

    return None


def _body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text
