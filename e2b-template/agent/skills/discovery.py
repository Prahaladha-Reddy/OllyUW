from __future__ import annotations

import re
from pathlib import Path
from typing import Any

CATALOG_DIR = Path(__file__).resolve().parent / "catalog"


def list_skills() -> list[dict[str, str]]:
    """Return [{name, description}, ...] for every skill in the catalog."""
    skills: list[dict[str, str]] = []
    if not CATALOG_DIR.exists():
        return skills
    for path in sorted(CATALOG_DIR.glob("*.md")):
        meta = _parse_frontmatter(path)
        name = meta.get("name") or path.stem
        desc = meta.get("description") or ""
        skills.append({"name": name, "description": desc, "path": str(path)})
    return skills


def _parse_frontmatter(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end].strip()
    result: dict[str, Any] = {}
    for line in block.splitlines():
        m = re.match(r"^(\w[\w-]*):\s*(.*)", line)
        if m:
            result[m.group(1)] = m.group(2).strip()
    return result
