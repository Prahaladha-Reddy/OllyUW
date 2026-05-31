from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", "/home/user/workspace")).resolve()
_READ_LIMIT = 20_000


def safe_path(user_path: str) -> Path:
    target = (WORKSPACE / user_path).resolve()
    if target != WORKSPACE and WORKSPACE not in target.parents:
        raise ValueError(f"path escapes workspace: {user_path!r}")
    return target


# ── read ──────────────────────────────────────────────────────────────────────

def read_file(path: str, start_line: int = 0, end_line: int | None = None) -> str:
    """Read lines [start_line, end_line) from a workspace file. 0-based. Returns ≤20K chars."""
    target = safe_path(path)
    if not target.exists():
        return f"error: file not found: {path}"
    if not target.is_file():
        return f"error: not a file: {path}"

    lines = target.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    total = len(lines)
    start = max(0, start_line)
    end = min(end_line, total) if end_line is not None else total
    chunk = "".join(lines[start:end])

    if len(chunk) > _READ_LIMIT:
        chunk = chunk[:_READ_LIMIT]
        last_nl = chunk.rfind("\n")
        if last_nl > 0:
            chunk = chunk[: last_nl + 1]
        shown = chunk.count("\n")
        next_start = start + shown
        chunk += (
            f"\n...[truncated — {total} lines total; "
            f"call read_file(path={path!r}, start_line={next_start}) to continue]"
        )
    elif end < total and end_line is not None:
        chunk += f"\n...[lines {start + 1}–{end} of {total}]"

    header = f"[{path}  lines {start + 1}–{min(start + chunk.count(chr(10)), total)} / {total}]"
    return f"{header}\n{chunk}"


# ── write ─────────────────────────────────────────────────────────────────────

def write_file(path: str, content: str) -> str:
    target = safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    return f"wrote {path}  ({lines} lines, {len(content)} bytes)"


# ── patch ─────────────────────────────────────────────────────────────────────

def apply_unified_patch(path: str, diff: str) -> str:
    """Apply a standard unified diff to a workspace file.

    Generate the diff in this format:
        --- a/filename
        +++ b/filename
        @@ -start,count +start,count @@
         context line
        -removed line
        +added line
    """
    target = safe_path(path)
    if not target.exists():
        return f"error: file not found: {path}"

    # Try strip-levels 1 then 0 (handles a/b prefixes and bare paths).
    last_result = None
    for strip in ("1", "0"):
        last_result = subprocess.run(
            ["patch", f"-p{strip}", "--no-backup-if-mismatch", str(target)],
            input=diff,
            capture_output=True,
            text=True,
        )
        if last_result.returncode == 0:
            changed = diff.count("\n+") + diff.count("\n-")
            return f"patched {path}  (~{changed} changed lines)"

    stderr = last_result.stderr.strip() if last_result else "unknown error"
    return (
        f"patch failed:\n{stderr}\n\n"
        "Ensure standard unified format:  --- a/file  +++ b/file  @@ -N,N +N,N @@"
    )


# ── outline ───────────────────────────────────────────────────────────────────

def get_file_outline(path: str) -> str:
    """Token-efficient file outline: classes/functions with line numbers, no content."""
    target = safe_path(path)
    if not target.exists():
        return f"error: file not found: {path}"

    text = target.read_text(encoding="utf-8", errors="replace")
    suffix = target.suffix.lower()

    if suffix == ".py":
        return _outline_python(text, path)
    return _outline_generic(text, path, suffix)


def _outline_python(text: str, path: str) -> str:
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return f"syntax error in {path}: {e}"

    items: list[tuple[int, str]] = []

    class V(ast.NodeVisitor):
        def __init__(self):
            self._depth = 0

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            items.append((node.lineno, "  " * self._depth + f"class {node.name}  [L{node.lineno}]"))
            self._depth += 1
            self.generic_visit(node)
            self._depth -= 1

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            args = [a.arg for a in node.args.args]
            items.append((node.lineno, "  " * self._depth + f"def {node.name}({', '.join(args)})  [L{node.lineno}]"))

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            args = [a.arg for a in node.args.args]
            items.append((node.lineno, "  " * self._depth + f"async def {node.name}({', '.join(args)})  [L{node.lineno}]"))

    V().visit(tree)
    items.sort(key=lambda x: x[0])
    body = "\n".join(line for _, line in items)
    return f"[outline: {path}]\n{body}" if body else f"[{path}: no classes or functions]"


def _outline_generic(text: str, path: str, suffix: str) -> str:
    if suffix in (".js", ".ts", ".jsx", ".tsx"):
        patterns = [
            (r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)", "fn"),
            (r"^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)", "class"),
            (r"^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(", "fn"),
        ]
    elif suffix == ".go":
        patterns = [
            (r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)", "func"),
            (r"^type\s+(\w+)\s+struct", "struct"),
        ]
    elif suffix in (".java", ".kt"):
        patterns = [
            (r"^\s*(?:public|private|protected|static|\s)+\w+\s+(\w+)\s*\(", "method"),
            (r"^\s*(?:public|private|protected)?\s+class\s+(\w+)", "class"),
        ]
    else:
        patterns = [
            (r"^\s*(?:def|function|func|sub|proc)\s+(\w+)", "fn"),
            (r"^\s*class\s+(\w+)", "class"),
        ]

    results = []
    for i, line in enumerate(text.splitlines(), 1):
        for pat, kind in patterns:
            m = re.match(pat, line)
            if m:
                results.append(f"  {kind} {m.group(1)}  [L{i}]")
                break

    return (
        f"[outline: {path}]\n" + "\n".join(results)
        if results
        else f"[{path}: no recognizable structure]"
    )


# ── search / find ─────────────────────────────────────────────────────────────

def find_files(pattern: str, path: str = ".") -> str:
    import glob as _g
    base = safe_path(path)
    matches = _g.glob(str(base / pattern), recursive=True)
    results = sorted(
        str(Path(m).relative_to(WORKSPACE))
        for m in matches
        if Path(m).is_file()
    )
    return "\n".join(results) if results else f"no files matching {pattern!r}"


def search_files(pattern: str, path: str = ".", file_glob: str = "*") -> str:
    base = safe_path(path)
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"invalid regex: {e}"

    matches: list[str] = []
    for f in sorted(base.rglob(file_glob)):
        if not f.is_file():
            continue
        try:
            for i, line in enumerate(
                f.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                if rx.search(line):
                    rel = f.relative_to(WORKSPACE)
                    matches.append(f"{rel}:{i}: {line.strip()}")
                    if len(matches) >= 300:
                        matches.append("...(truncated at 300 matches)")
                        return "\n".join(matches)
        except (UnicodeDecodeError, PermissionError):
            continue
    return "\n".join(matches) if matches else f"no matches for {pattern!r}"


def list_directory(path: str = ".", recursive: bool = False) -> str:
    target = safe_path(path)
    if not target.exists():
        return f"error: not found: {path}"
    if target.is_file():
        return target.name

    if not recursive:
        entries = sorted(
            p.name + ("/" if p.is_dir() else "") for p in target.iterdir()
        )
        return "\n".join(entries) if entries else "(empty)"

    lines: list[str] = [str(path) + "/"]

    def _tree(p: Path, prefix: str) -> None:
        try:
            children = sorted(p.iterdir())
        except PermissionError:
            return
        for i, child in enumerate(children):
            last = i == len(children) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{child.name}{'/' if child.is_dir() else ''}")
            if child.is_dir():
                _tree(child, prefix + ("    " if last else "│   "))

    _tree(target, "")
    return "\n".join(lines)


# ── move / delete ─────────────────────────────────────────────────────────────

def move_file(src: str, dst: str) -> str:
    s = safe_path(src)
    d = safe_path(dst)
    if not s.exists():
        return f"error: source not found: {src}"
    d.parent.mkdir(parents=True, exist_ok=True)
    s.rename(d)
    return f"moved {src} → {dst}"


def delete_file(path: str) -> str:
    target = safe_path(path)
    if not target.exists():
        return f"error: not found: {path}"
    if target.is_dir():
        shutil.rmtree(target)
        return f"deleted directory {path}"
    target.unlink()
    return f"deleted {path}"
