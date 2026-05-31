"""
Skill discovery — finds skills across all standard locations.

Search order (highest priority first):
  1. /home/user/.agents/skills/     ← user-installed via `npx skills add`
  2. /home/user/.claude/skills/     ← Claude Code compat
  3. agent/skills/catalog/          ← built-in skills (shipped with agent)

Supports two formats:
  Directory format (preferred):  skill-name/SKILL.md
  Legacy flat format:             skill-name.md   (backward compat)
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

# Built-in skills live next to this file
CATALOG_DIR = Path(__file__).resolve().parent / "catalog"

# User-installed skills (inside the E2B snapshot)
_USER_AGENTS_DIR = Path(os.environ.get("AGENTS_SKILLS_DIR", "/home/user/.agents/skills"))
_USER_CLAUDE_DIR = Path(os.environ.get("CLAUDE_SKILLS_DIR", "/home/user/.claude/skills"))

SEARCH_DIRS: list[Path] = [_USER_AGENTS_DIR, _USER_CLAUDE_DIR, CATALOG_DIR]


def list_skills() -> list[dict[str, str]]:
    """Return [{name, description, path, has_scripts, has_references}, ...]
    across all search dirs. Later entries in the list are lower priority;
    first match by name wins."""
    seen: set[str] = set()
    skills: list[dict[str, str]] = []

    for base in SEARCH_DIRS:
        if not base.exists():
            continue
        for entry in sorted(base.iterdir()):
            skill = _load_entry(entry)
            if skill is None:
                continue
            name = skill["name"]
            if name in seen or name == "allskills":
                continue
            seen.add(name)
            skills.append(skill)

    return skills


def find_skill_dir(name: str) -> Path | None:
    """Return the Path to the skill's root directory/file, or None."""
    for base in SEARCH_DIRS:
        if not base.exists():
            continue
        # Directory format: base/skill-name/SKILL.md
        dir_path = base / name
        if dir_path.is_dir() and (dir_path / "SKILL.md").exists():
            return dir_path
        # Legacy flat format: base/skill-name.md
        flat_path = base / f"{name}.md"
        if flat_path.exists() and flat_path.is_file():
            return flat_path
        # Try matching by frontmatter name field
        for entry in base.iterdir():
            skill = _load_entry(entry)
            if skill and skill["name"] == name:
                return Path(skill["path"]).parent

    return None


def _load_entry(entry: Path) -> dict[str, str] | None:
    """Parse a skill directory or flat .md file. Returns None if not a valid skill."""
    if entry.is_dir():
        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            return None
        meta = _parse_frontmatter(skill_md)
        name = meta.get("name") or entry.name
        has_scripts = (entry / "scripts").is_dir() and any((entry / "scripts").iterdir())
        has_refs = (entry / "references").is_dir() and any((entry / "references").iterdir())
        return {
            "name":           name,
            "description":    meta.get("description") or "",
            "path":           str(skill_md),
            "root":           str(entry),
            "has_scripts":    str(has_scripts).lower(),
            "has_references": str(has_refs).lower(),
            "format":         "directory",
        }

    if entry.suffix == ".md" and entry.name != "allskills.md":
        meta = _parse_frontmatter(entry)
        name = meta.get("name") or entry.stem
        return {
            "name":           name,
            "description":    meta.get("description") or "",
            "path":           str(entry),
            "root":           str(entry.parent),
            "has_scripts":    "false",
            "has_references": "false",
            "format":         "flat",
        }

    return None


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
        m = re.match(r"^([\w-]+):\s*(.*)", line)
        if m:
            result[m.group(1)] = m.group(2).strip()
    return result
