"""
Skill installer — `npx skills add` equivalent.

Usage (the agent calls run_shell or we call directly):
  python -m agent.skills.installer add owner/repo
  python -m agent.skills.installer add https://github.com/owner/repo
  python -m agent.skills.installer add https://github.com/owner/repo/tree/main/skill-name
  python -m agent.skills.installer list

Skills are installed to /home/user/.agents/skills/ (user-installed location).
Built-in skills in agent/skills/catalog/ are never overwritten.

GitHub API is used to download skill directories (no git clone needed).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

from agent.skills.discovery import _USER_AGENTS_DIR
from agent.skills.loader import regenerate_allskills

_INSTALL_DIR = _USER_AGENTS_DIR
_GH_API = "https://api.github.com"
_KNOWN_REGISTRIES = [
    "anthropics/skills",
    "vercel-labs/agent-skills",
]


def install_skill(source: str) -> str:
    """
    Install a skill from:
      - GitHub shorthand:  owner/repo  or  owner/repo/skill-name
      - Full GitHub URL:   https://github.com/owner/repo  or  .../tree/branch/path
      - Local path:        ./path/to/skill  or  /absolute/path
    """
    _INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    # Local path
    if source.startswith("./") or source.startswith("/") or Path(source).exists():
        return _install_local(Path(source))

    # Full GitHub URL
    if source.startswith("https://github.com"):
        return _install_github_url(source)

    # GitHub shorthand: owner/repo or owner/repo/skill-path
    parts = source.split("/")
    if len(parts) >= 2:
        owner, repo = parts[0], parts[1]
        subpath = "/".join(parts[2:]) if len(parts) > 2 else ""
        return _install_github(owner, repo, subpath)

    return f"error: unrecognised source format: {source!r}\nUse: owner/repo, full GitHub URL, or local path"


def list_available() -> str:
    """List skills available in known registries."""
    lines = ["Skills available from known registries:"]
    for registry in _KNOWN_REGISTRIES:
        owner, repo = registry.split("/")
        try:
            skills = _list_github_skills(owner, repo)
            lines.append(f"\n{registry}:")
            for s in skills:
                lines.append(f"  {owner}/{repo}/{s}")
        except Exception as e:
            lines.append(f"\n{registry}: error listing — {e}")
    return "\n".join(lines)


# ── GitHub install ────────────────────────────────────────────────────────────

def _install_github_url(url: str) -> str:
    """Parse a GitHub URL and delegate to _install_github."""
    # https://github.com/owner/repo
    # https://github.com/owner/repo/tree/branch/path/to/skill
    url = url.rstrip("/")
    parts = url.replace("https://github.com/", "").split("/")
    if len(parts) < 2:
        return f"error: cannot parse GitHub URL: {url}"
    owner, repo = parts[0], parts[1]
    # Strip tree/branch prefix if present
    rest = parts[2:]
    if rest and rest[0] == "tree" and len(rest) >= 2:
        rest = rest[2:]  # skip "tree/branch"
    subpath = "/".join(rest)
    return _install_github(owner, repo, subpath)


def _install_github(owner: str, repo: str, subpath: str = "") -> str:
    """Download a skill from GitHub. subpath is the folder inside the repo."""
    # Use GitHub's zip download to avoid needing git
    zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
    fallback_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        zip_path = tmp / "repo.zip"

        # Try main then master branch
        for url in (zip_url, fallback_url):
            try:
                _download(url, zip_path)
                break
            except Exception:
                continue
        else:
            return f"error: could not download {owner}/{repo} — check repo name and network"

        # Extract zip
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp)

        # Find extracted root (GitHub names it owner-repo-branch/)
        roots = [d for d in tmp.iterdir() if d.is_dir() and d.name != "__MACOSX"]
        if not roots:
            return "error: zip extraction failed"
        repo_root = roots[0]

        # Navigate to subpath if given
        skill_source = repo_root / subpath if subpath else repo_root

        if not skill_source.exists():
            return f"error: path {subpath!r} not found in {owner}/{repo}"

        # If subpath points directly to a skill directory (has SKILL.md)
        if (skill_source / "SKILL.md").exists():
            return _copy_skill_dir(skill_source)

        # Otherwise scan for skill directories inside it
        results = []
        for entry in sorted(skill_source.iterdir()):
            if entry.is_dir() and (entry / "SKILL.md").exists():
                results.append(_copy_skill_dir(entry))
        if results:
            return "\n".join(results)

        # Last resort: look for any .md with frontmatter
        for md in sorted(skill_source.glob("*.md")):
            if md.name in ("README.md", "CHANGELOG.md"):
                continue
            text = md.read_text(encoding="utf-8", errors="replace")
            if text.startswith("---") and "description:" in text:
                return _copy_skill_file(md)

        return f"error: no skills found in {owner}/{repo}/{subpath}"


def _list_github_skills(owner: str, repo: str) -> list[str]:
    """List skill directories available in a GitHub repo."""
    api_url = f"{_GH_API}/repos/{owner}/{repo}/contents"
    with urllib.request.urlopen(api_url, timeout=10) as resp:
        contents = json.loads(resp.read())
    return [
        item["name"]
        for item in contents
        if item["type"] == "dir" and not item["name"].startswith(".")
    ]


# ── local install ─────────────────────────────────────────────────────────────

def _install_local(source: Path) -> str:
    if not source.exists():
        return f"error: path not found: {source}"
    if source.is_dir() and (source / "SKILL.md").exists():
        return _copy_skill_dir(source)
    if source.is_file() and source.suffix == ".md":
        return _copy_skill_file(source)
    return f"error: {source} is not a skill directory (needs SKILL.md) or .md file"


def _copy_skill_dir(source: Path) -> str:
    dest = _INSTALL_DIR / source.name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest)
    regenerate_allskills()
    return f"installed skill: {source.name} → {dest}"


def _copy_skill_file(source: Path) -> str:
    dest = _INSTALL_DIR / source.name
    shutil.copy2(source, dest)
    regenerate_allskills()
    return f"installed skill: {source.stem} → {dest}"


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "second-pc-agent/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        dest.write_bytes(resp.read())


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: python -m agent.skills.installer add <source>  |  list")
        sys.exit(1)
    cmd = args[0]
    if cmd == "add" and len(args) >= 2:
        print(install_skill(args[1]))
    elif cmd == "list":
        print(list_available())
    else:
        print("Usage: python -m agent.skills.installer add <source>  |  list")
        sys.exit(1)
