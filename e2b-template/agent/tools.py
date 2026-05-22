"""
Agent tool implementations.
All file operations are confined to WORKSPACE via safe_path().
Imported by worker.py; also importable by tests without any Redis/LLM deps.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from dotenv import load_dotenv
WORKSPACE = Path("/home/user/workspace").resolve()
SHELL_TIMEOUT = 60
OUTPUT_LIMIT = 8000
load_dotenv()

def safe_path(user_path: str) -> Path:
    """Resolve user_path relative to WORKSPACE and block traversal."""
    target = (WORKSPACE / user_path).resolve()
    if target != WORKSPACE and WORKSPACE not in target.parents:
        raise ValueError(f"path escapes workspace: {user_path!r}")
    return target


def tool_list_files(path: str = ".") -> str:
    target = safe_path(path)
    if not target.exists():
        return f"missing: {path}"
    if target.is_file():
        return target.name
    entries = sorted(
        p.name + ("/" if p.is_dir() else "")
        for p in target.iterdir()
    )
    return "\n".join(entries) if entries else "(empty directory)"


def tool_read_file(path: str) -> str:
    return safe_path(path).read_text(encoding="utf-8")


def tool_write_file(path: str, content: str) -> str:
    target = safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} bytes → {path}"


def tool_run_shell(command: str) -> str:
    result = subprocess.run(
        command,
        cwd=str(WORKSPACE),
        shell=True,
        text=True,
        capture_output=True,
        timeout=SHELL_TIMEOUT,
    )
    output = result.stdout or ""
    if result.stderr:
        output += "\n[stderr]\n" + result.stderr
    output += f"\n[exit_code] {result.returncode}"
    return output.strip()[:OUTPUT_LIMIT]


def run_tool(tool: str, args: dict) -> str:
    """Dispatch a tool call by name. Raises ValueError for unknown tools."""
    match tool:
        case "list_files":
            return tool_list_files(str(args.get("path", ".")))
        case "read_file":
            return tool_read_file(str(args["path"]))
        case "write_file":
            return tool_write_file(str(args["path"]), str(args.get("content", "")))
        case "run_shell":
            return tool_run_shell(str(args["command"]))
        case _:
            raise ValueError(f"unknown tool: {tool!r}")
