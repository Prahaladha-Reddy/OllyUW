from __future__ import annotations

import asyncio
from pathlib import Path

from e2b import Sandbox

from src.config import get_settings

_sandboxes: dict[str, Sandbox] = {}
_lock = asyncio.Lock()

AGENT_DIR = Path(__file__).resolve().parents[3] / "e2b-template" / "agent"
AGENT_FILES = ("worker.py", "tools.py")
WORKER_LOG = "/home/user/worker.log"


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
        sandbox.files.write(f"/home/user/workspace/{filename}", data)


def upload_agent_code(sandbox: Sandbox) -> None:
    for filename in AGENT_FILES:
        source = AGENT_DIR / filename
        if not source.exists():
            raise RuntimeError(f"Agent file missing: {source}")
        sandbox.files.write(f"/home/user/{filename}", source.read_bytes())


def start_worker(sandbox: Sandbox, envs: dict[str, str]) -> None:
    sandbox.commands.run(
        f"mkdir -p /home/user/workspace && python -u /home/user/worker.py > {WORKER_LOG} 2>&1",
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
