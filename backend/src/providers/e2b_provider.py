from __future__ import annotations

import asyncio

from e2b import Sandbox

from src.config import get_settings

_sandboxes: dict[str, Sandbox] = {}
_lock = asyncio.Lock()


async def register(session_id: str, sandbox: Sandbox) -> None:
    async with _lock:
        _sandboxes[session_id] = sandbox


async def get(session_id: str) -> Sandbox | None:
    async with _lock:
        return _sandboxes.get(session_id)


async def deregister(session_id: str) -> None:
    async with _lock:
        _sandboxes.pop(session_id, None)


def create_sandbox(envs: dict[str, str] | None = None) -> tuple[Sandbox, str]:
    settings = get_settings()
    kwargs: dict = {"timeout": settings.e2b.sandbox_timeout}
    if envs:
        kwargs["envs"] = envs

    template_id = settings.e2b.template_id
    if template_id and template_id != "base":
        sandbox = Sandbox.create(template_id, **kwargs)
    else:
        sandbox = Sandbox.create(**kwargs)

    sandbox_id: str = getattr(sandbox, "sandbox_id", None) or getattr(sandbox, "sandboxId", "")
    return sandbox, str(sandbox_id)


def extend_timeout(sandbox: Sandbox, seconds: int | None = None) -> None:
    """Reset the idle timer. Call on every user message."""
    if seconds is None:
        seconds = int(get_settings().e2b.sandbox_timeout)
    sandbox.set_timeout(int(seconds))


def upload_raw_files(sandbox: Sandbox, files: dict[str, bytes]) -> None:
    """Upload raw bytes to /home/user/workspace/. Filename → bytes."""
    for filename, data in files.items():
        sandbox.files.write(f"/home/user/workspace/{filename}", data)


def list_workspace_files(sandbox: Sandbox) -> list[str]:
    result = sandbox.commands.run(
        "find /home/user/workspace -maxdepth 4 -type f | sort",
        timeout=15,
    )
    return [f for f in result.stdout.strip().splitlines() if f]


def read_worker_log(sandbox: Sandbox, tail_lines: int = 200) -> str:
    result = sandbox.commands.run(
        f"tail -n {tail_lines} /home/user/worker.log 2>/dev/null || echo '(no log yet)'",
        timeout=10,
    )
    return result.stdout


def kill_sandbox(sandbox: Sandbox) -> None:
    """Best-effort kill — ignore errors if it's already dead."""
    try:
        sandbox.kill()
    except Exception:
        pass
