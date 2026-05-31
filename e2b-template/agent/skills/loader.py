"""
Skill loader — three-tier progressive disclosure.

Tier 1: name + description (always in system prompt, ~100 tokens per skill)
Tier 2: SKILL.md body — loaded when agent calls use_skill(name)
Tier 3: scripts/, references/ — agent runs scripts via run_shell / reads refs
         on demand. Script code NEVER goes into context.
"""
from __future__ import annotations

from pathlib import Path

from agent.skills.discovery import CATALOG_DIR, find_skill_dir, list_skills


def load_skill(name: str) -> str | None:
    """Return the full SKILL.md instructions for a skill, enriched with
    hints about available scripts and reference docs. Returns None if not found."""
    location = find_skill_dir(name)
    if location is None:
        return None

    # Directory format
    if location.is_dir():
        skill_md = location / "SKILL.md"
        body = _body(skill_md)

        # Append scripts hint — agent knows they exist without code in context
        scripts_dir = location / "scripts"
        if scripts_dir.is_dir():
            scripts = sorted(p for p in scripts_dir.iterdir() if p.is_file())
            if scripts:
                lines = ["\n---\n## Scripts Available\n",
                         f"Skill scripts are in `{scripts_dir}`. Run them via `run_shell`.",
                         "Use `uv run <path>` for Python scripts (handles inline deps automatically),",
                         "or `bash <path>` for shell scripts.",
                         "Run `<script> --help` first to see usage.\n"]
                for s in scripts:
                    lines.append(f"- `{s}`")
                body += "\n".join(lines)

        # Append references hint — agent can read them with read_file when needed
        refs_dir = location / "references"
        if refs_dir.is_dir():
            refs = sorted(p for p in refs_dir.iterdir() if p.is_file())
            if refs:
                lines = ["\n---\n## Reference Docs\n",
                         "Read these with `read_file` only when needed for the task:\n"]
                for r in refs:
                    lines.append(f"- `{r}`")
                body += "\n".join(lines)

        return body

    # Flat format (legacy .md file)
    if location.is_file():
        return _body(location)

    return None


def list_skills_index() -> str:
    """Concise index for system prompt injection — name + description per skill."""
    skills = list_skills()
    if not skills:
        return "(no skills available)"
    lines = []
    for s in skills:
        extras = []
        if s.get("has_scripts") == "true":
            extras.append("scripts")
        if s.get("has_references") == "true":
            extras.append("references")
        suffix = f"  [{', '.join(extras)}]" if extras else ""
        lines.append(f"- **{s['name']}**: {s['description']}{suffix}")
    return "\n".join(lines)


def regenerate_allskills() -> None:
    """Re-generate skills/catalog/allskills.md from the current catalog."""
    skills = list_skills()
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Available Skills\n",
             "_Load a skill with `use_skill(name)`. Skills marked [scripts] include",
             "executable scripts you can run; [references] have extra docs to read._\n"]
    for s in skills:
        extras = []
        if s.get("has_scripts") == "true":
            extras.append("scripts")
        if s.get("has_references") == "true":
            extras.append("references")
        suffix = f"  [{', '.join(extras)}]" if extras else ""
        lines.append(f"- **{s['name']}**: {s['description']}{suffix}")
    (CATALOG_DIR / "allskills.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def allskills_section() -> str:
    """Full skills section for system prompt injection."""
    allskills_path = CATALOG_DIR / "allskills.md"
    # Regenerate if stale or missing
    if not allskills_path.exists():
        regenerate_allskills()
    if allskills_path.exists():
        return allskills_path.read_text(encoding="utf-8")
    return list_skills_index()


def _body(path: Path) -> str:
    """Return the markdown body after the frontmatter block."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text
