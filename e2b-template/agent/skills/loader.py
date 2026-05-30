"""Load skill bodies and the allskills.md index."""
from __future__ import annotations

from pathlib import Path

from agent.skills.discovery import CATALOG_DIR, list_skills


def load_skill(name: str) -> str | None:
    """Return the full markdown body of a skill, or None if not found."""
    direct = CATALOG_DIR / f"{name}.md"
    if direct.exists():
        return _body(direct)
    for entry in list_skills():
        if entry["name"] == name:
            return _body(Path(entry["path"]))
    return None


def list_skills_index() -> str:
    """Concise index string: - name: description (one per line)."""
    skills = list_skills()
    if not skills:
        return "(no skills available)"
    return "\n".join(f"- {s['name']}: {s['description']}" for s in skills)


def regenerate_allskills() -> None:
    """Re-generate skills/catalog/allskills.md from the current catalog."""
    skills = list_skills()
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Available Skills\n"]
    for s in skills:
        lines.append(f"- **{s['name']}**: {s['description']}")
    (CATALOG_DIR / "allskills.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def allskills_section() -> str:
    """Skills index for injection into the system prompt."""
    allskills_path = CATALOG_DIR / "allskills.md"
    if not allskills_path.exists():
        regenerate_allskills()
    if allskills_path.exists():
        return allskills_path.read_text(encoding="utf-8")
    return list_skills_index()


def _body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text
