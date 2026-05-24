from __future__ import annotations

import asyncio
import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType

from e2b import Sandbox

from src.config import get_settings

logger = logging.getLogger("ollyuw.e2b")

_sandboxes: dict[str, Sandbox] = {}
_lock = asyncio.Lock()

AGENT_DIR = Path(__file__).resolve().parents[3] / "e2b-template" / "agent"
WORKER_LOG = "/home/user/worker.log"

# Files under AGENT_DIR we don't want to ship to the sandbox (bytecode caches,
# editor cruft). Everything else is uploaded recursively at session start.
_AGENT_SKIP_NAMES = {"__pycache__", ".pytest_cache", ".DS_Store"}
_AGENT_SKIP_SUFFIXES = {".pyc", ".pyo"}
_TEXT_UPLOAD_SUFFIXES = {
    ".csv",
    ".html",
    ".json",
    ".log",
    ".md",
    ".txt",
    ".toml",
    ".xml",
    ".yaml",
    ".yml",
}
_SCANNER_MODULE: ModuleType | None = None


async def register(session_id: str, sandbox: Sandbox) -> None:
    async with _lock:
        _sandboxes[session_id] = sandbox


async def get(session_id: str) -> Sandbox | None:
    async with _lock:
        return _sandboxes.get(session_id)


async def deregister(session_id: str) -> None:
    async with _lock:
        _sandboxes.pop(session_id, None)


def create_sandbox() -> tuple[Sandbox, str]:
    settings = get_settings()
    template_id = settings.e2b.template_id
    timeout = settings.e2b.sandbox_timeout
    api_key = settings.e2b.api_key

    if template_id and template_id != "base":
        sandbox = Sandbox.create(template_id, timeout=timeout, api_key=api_key)
    else:
        sandbox = Sandbox.create(timeout=timeout, api_key=api_key)

    sandbox_id: str = getattr(sandbox, "sandbox_id", None) or getattr(sandbox, "sandboxId", "")
    return sandbox, str(sandbox_id)


def extend_timeout(sandbox: Sandbox, seconds: int | None = None) -> None:
    if seconds is None:
        seconds = int(get_settings().e2b.sandbox_timeout)
    sandbox.set_timeout(int(seconds))


def upload_raw_files(sandbox: Sandbox, files: dict[str, bytes]) -> None:
    for filename, data in files.items():
        sandbox.files.write(f"/home/user/workspace/{filename}", _sanitize_upload(filename, data))


def _sanitize_upload(filename: str, data: bytes) -> bytes:
    """
    Layer 1 also runs before files are materialized in the sandbox.

    Binary/PDF files are preserved as-is; text-like files with injection-shaped
    content are wrapped so any tool path, including run_shell, sees the fence.
    """
    if Path(filename).suffix.lower() not in _TEXT_UPLOAD_SUFFIXES:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data

    scanner = _load_injection_scanner()
    result = scanner.scan_text(text, source=f"upload:{filename}")
    if not result.flagged:
        return data

    logger.warning("upload injection scan flagged %s: %s", filename, result.summary())
    wrapped = scanner.wrap_untrusted_content(text, result)
    return wrapped.encode("utf-8")


def _load_injection_scanner() -> ModuleType:
    global _SCANNER_MODULE
    if _SCANNER_MODULE is not None:
        return _SCANNER_MODULE

    module_path = AGENT_DIR / "safety" / "injection_scanner.py"
    spec = importlib.util.spec_from_file_location("ollyuw_injection_scanner", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load injection scanner from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _SCANNER_MODULE = module
    return module


def upload_agent_code(sandbox: Sandbox) -> None:
    """
    Upload the entire `e2b-template/agent/` tree into the sandbox at
    `/home/user/agent/`, preserving relative paths. The worker is then
    launched as `python -u -m agent.worker` with cwd `/home/user/`, so
    the `agent` package is importable.
    """
    if not AGENT_DIR.exists():
        raise RuntimeError(f"Agent source directory missing: {AGENT_DIR}")

    uploaded = 0
    for source in AGENT_DIR.rglob("*"):
        if not source.is_file():
            continue
        if source.name in _AGENT_SKIP_NAMES or source.suffix in _AGENT_SKIP_SUFFIXES:
            continue
        if any(part in _AGENT_SKIP_NAMES for part in source.parts):
            continue
        rel = source.relative_to(AGENT_DIR).as_posix()
        sandbox.files.write(f"/home/user/agent/{rel}", source.read_bytes())
        uploaded += 1

    if uploaded == 0:
        raise RuntimeError(f"No agent files found under {AGENT_DIR}")


def start_worker(sandbox: Sandbox, envs: dict[str, str]) -> None:
    sandbox.commands.run(
        "mkdir -p /home/user/workspace && "
        f"cd /home/user && python -u -m agent.worker > {WORKER_LOG} 2>&1",
        envs=envs,
        background=True,
    )


def list_workspace_files(sandbox: Sandbox) -> list[str]:
    result = sandbox.commands.run(
        "find /home/user/workspace -maxdepth 4 -type f | sort",
        timeout=15,
    )
    return [f for f in result.stdout.strip().splitlines() if f]


def read_worker_log(sandbox: Sandbox, tail_lines: int = 200) -> str:
    result = sandbox.commands.run(
        f"tail -n {tail_lines} {WORKER_LOG} 2>/dev/null || echo '(no log yet)'",
        timeout=10,
    )
    return result.stdout


def kill_sandbox(sandbox: Sandbox) -> None:
    try:
        sandbox.kill()
    except Exception:
        pass
