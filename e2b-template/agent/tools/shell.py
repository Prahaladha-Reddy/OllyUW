"""Async shell execution."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", "/home/user/workspace")).resolve()
_TIMEOUT = 60
_OUTPUT_LIMIT = 10_000


async def run_shell(command: str, timeout: int = _TIMEOUT) -> str:
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(WORKSPACE),
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=float(timeout))
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return f"[exit_code] -1\n[error] command timed out after {timeout}s"

    out = stdout.decode("utf-8", errors="replace")
    if stderr:
        out += "\n[stderr]\n" + stderr.decode("utf-8", errors="replace")
    out += f"\n[exit_code] {proc.returncode}"
    return out.strip()[:_OUTPUT_LIMIT]
