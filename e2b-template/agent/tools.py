from __future__ import annotations

import glob as _glob_module
import json
import re
import subprocess
from pathlib import Path

from dotenv import load_dotenv

try:
    from agent.safety.injection_scanner import sanitize_for_model as _sanitize_for_model
except ImportError:  
    from safety.injection_scanner import sanitize_for_model as _sanitize_for_model

WORKSPACE = Path("/home/user/workspace").resolve()
SHELL_TIMEOUT = 60
OUTPUT_LIMIT = 10000
READ_FILE_LIMIT = 20_000  
_TODO_FILE = Path("/home/user/agent_todo.json")
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


def tool_read_file(path: str, offset: int = 0, limit: int = 0) -> str:
    """Read a workspace file, up to READ_FILE_LIMIT chars. Use offset/limit to paginate large files."""
    target = safe_path(path)
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    total = len(lines)

    start = max(0, offset)
    end = min(start + limit, total) if limit > 0 else total
    chunk = "".join(lines[start:end])

    if len(chunk) > READ_FILE_LIMIT:
        chunk = chunk[:READ_FILE_LIMIT]
        last_nl = chunk.rfind("\n")
        if last_nl > 0:
            chunk = chunk[: last_nl + 1]
        lines_shown = chunk.count("\n")
        next_offset = start + lines_shown
        chunk += (
            f"\n...[truncated — file has {total} lines total; "
            f"call read_file(path={path!r}, offset={next_offset}) to continue]"
        )
    elif end < total:
        chunk += (
            f"\n...[showing lines {start + 1}–{end} of {total}; "
            f"call read_file(path={path!r}, offset={end}) for more]"
        )

    safe_chunk, _ = _sanitize_for_model(chunk, source=path)
    return safe_chunk


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


def tool_edit_file(path: str, old_str: str, new_str: str) -> str:
    target = safe_path(path)
    if not target.exists():
        return f"file not found: {path}"
    content = target.read_text(encoding="utf-8")
    if old_str not in content:
        return f"string not found in {path!r}"
    target.write_text(content.replace(old_str, new_str, 1), encoding="utf-8")
    return f"edited {path}"


def tool_glob_files(pattern: str, path: str = ".") -> str:
    base = safe_path(path)
    full_pattern = str(base / pattern)
    matches = _glob_module.glob(full_pattern, recursive=True)
    results = []
    for m in sorted(matches):
        mp = Path(m)
        if mp.is_file():
            try:
                results.append(str(mp.relative_to(WORKSPACE)))
            except ValueError:
                pass
    return "\n".join(results) if results else f"no files matching {pattern!r}"


def tool_grep_files(pattern: str, path: str = ".", file_glob: str = "*") -> str:
    base = safe_path(path)
    compiled = re.compile(pattern, re.IGNORECASE)
    matches: list[str] = []
    for f in sorted(base.rglob(file_glob)):
        if not f.is_file():
            continue
        try:
            for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if compiled.search(line):
                    rel = f.relative_to(WORKSPACE)
                    line_text = line.strip()
                    safe_line, _ = _sanitize_for_model(line_text, source=f"{rel}:{i}")
                    matches.append(f"{rel}:{i}: {safe_line}")
                    if len(matches) >= 300:
                        matches.append("...(truncated at 300 matches)")
                        return "\n".join(matches)
        except (UnicodeDecodeError, PermissionError):
            continue
    return "\n".join(matches) if matches else f"no matches for {pattern!r}"


def _load_todos() -> list[dict]:
    if _TODO_FILE.exists():
        try:
            return json.loads(_TODO_FILE.read_text())
        except Exception:
            pass
    return []


def _save_todos(todos: list[dict]) -> None:
    _TODO_FILE.write_text(json.dumps(todos, indent=2), encoding="utf-8")


def _fmt_todos(todos: list[dict]) -> str:
    if not todos:
        return "(no todos)"
    return "\n".join(
        f"{t['id']}. {'[x]' if t.get('done') else '[ ]'} {t['text']}"
        for t in todos
    )


def tool_todo(action: str, text: str = "", id: int = 0) -> str:
    todos = _load_todos()
    if action == "list":
        return _fmt_todos(todos)
    elif action == "add":
        if not text:
            return "error: text is required for 'add'"
        next_id = max((t["id"] for t in todos), default=0) + 1
        todos.append({"id": next_id, "text": text, "done": False})
        _save_todos(todos)
        return f"added #{next_id}: {text}\n\n" + _fmt_todos(todos)
    elif action in ("check", "uncheck"):
        done = action == "check"
        for t in todos:
            if t["id"] == id:
                t["done"] = done
                _save_todos(todos)
                return f"{'checked' if done else 'unchecked'} #{id}\n\n" + _fmt_todos(todos)
        return f"todo #{id} not found"
    elif action == "remove":
        before = len(todos)
        todos = [t for t in todos if t["id"] != id]
        _save_todos(todos)
        return (f"removed #{id}" if len(todos) < before else f"#{id} not found") + "\n\n" + _fmt_todos(todos)
    else:
        return f"unknown action {action!r} — use: list | add | check | uncheck | remove"


def tool_skill(name: str) -> str:
    from agent.skills.discovery import list_skills
    from agent.skills.loader import load_skill

    if name == "list":
        entries = list_skills()
        if not entries:
            return "(no skills available)"
        lines = ["Available skills:"]
        for e in entries:
            lines.append(f"  {e['name']}: {e['description']}")
        return "\n".join(lines)

    body = load_skill(name)
    if body is None:
        available = ", ".join(e["name"] for e in list_skills())
        return f"skill not found: {name!r}. Available: {available}"
    return body


def tool_memory_search(query: str, limit: int = 5) -> str:
    from agent.memory.mem0_client import format_search_results, search

    return format_search_results(search(query, limit=limit))


def tool_memory_add(text: str, category: str = "note") -> str:
    from agent.memory.mem0_client import add_note

    return add_note(text, category=category)


def tool_web_search(query: str, max_results: int = 5) -> str:
    from agent.web.parallel_client import web_search

    return web_search(query, max_results=max_results)


def tool_web_research(question: str, timeout: int = 90) -> str:
    from agent.web.parallel_client import web_research

    return web_research(question, timeout=timeout)


def run_tool(tool: str, args: dict) -> str:
    """Dispatch a tool call by name. Raises ValueError for unknown tools."""
    match tool:
        case "list_files":
            return tool_list_files(str(args.get("path", ".")))
        case "read_file":
            return tool_read_file(
                str(args["path"]),
                int(args.get("offset", 0)),
                int(args.get("limit", 0)),
            )
        case "write_file":
            return tool_write_file(str(args["path"]), str(args.get("content", "")))
        case "run_shell":
            return tool_run_shell(str(args["command"]))
        case "edit_file":
            return tool_edit_file(
                str(args["path"]),
                str(args.get("old_str", "")),
                str(args.get("new_str", "")),
            )
        case "glob_files":
            return tool_glob_files(str(args["pattern"]), str(args.get("path", ".")))
        case "grep_files":
            return tool_grep_files(
                str(args["pattern"]),
                str(args.get("path", ".")),
                str(args.get("file_glob", "*")),
            )
        case "todo":
            return tool_todo(
                str(args["action"]),
                str(args.get("text", "")),
                int(args.get("id", 0)),
            )
        case "skill":
            return tool_skill(str(args["name"]))
        case "memory_search":
            return tool_memory_search(
                str(args["query"]),
                int(args.get("limit", 5)),
            )
        case "memory_add":
            return tool_memory_add(
                str(args["text"]),
                str(args.get("category", "note")),
            )
        case "web_search":
            return tool_web_search(
                str(args["query"]),
                int(args.get("max_results", 5)),
            )
        case "web_research":
            return tool_web_research(
                str(args["question"]),
                int(args.get("timeout", 90)),
            )
        case _:
            raise ValueError(f"unknown tool: {tool!r}")