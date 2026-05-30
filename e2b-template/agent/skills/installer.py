"""
Install skills from a registry or URL.

Usage (agent calls run_shell):
    python -m agent.skills.installer add <skill-name-or-url>

CLI mimic of `npx skill add <name>`:
    python -m agent.skills.installer add code-review
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

from agent.skills.discovery import CATALOG_DIR
from agent.skills.loader import regenerate_allskills

# Public skill registry index — maps skill name → raw markdown URL.
# You can host your own and point SKILL_REGISTRY_URL at it.
SKILL_REGISTRY_URL = "https://raw.githubusercontent.com/Prahaladha-Reddy/OllyUW/second-pc/skills-registry/index.json"


def install_skill(name_or_url: str) -> str:
    """Download and install a skill. Returns a status message."""
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    # Direct URL
    if name_or_url.startswith("http"):
        return _install_from_url(name_or_url)

    # Try registry lookup
    try:
        import json
        with urllib.request.urlopen(SKILL_REGISTRY_URL, timeout=10) as resp:
            registry = json.loads(resp.read())
        url = registry.get(name_or_url)
        if not url:
            available = ", ".join(registry.keys())
            return f"skill '{name_or_url}' not found in registry. Available: {available}"
        return _install_from_url(url, name=name_or_url)
    except Exception as e:
        return f"error reaching skill registry: {e}\nTry passing a direct URL instead."


def _install_from_url(url: str, name: str | None = None) -> str:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            content = resp.read().decode("utf-8")
    except Exception as e:
        return f"error downloading skill: {e}"

    # Extract name from frontmatter if not provided
    if not name:
        import re
        m = re.search(r"^name:\s*(\S+)", content, re.MULTILINE)
        name = m.group(1) if m else url.rstrip("/").split("/")[-1].replace(".md", "")

    skill_file = CATALOG_DIR / f"{name}.md"
    skill_file.write_text(content, encoding="utf-8")
    regenerate_allskills()
    return f"installed skill: {name} → {skill_file}"


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "add":
        print(install_skill(sys.argv[2]))
    else:
        print("Usage: python -m agent.skills.installer add <skill-name-or-url>")
