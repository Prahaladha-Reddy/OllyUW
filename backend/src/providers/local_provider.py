from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from src.providers.e2b_provider import ComputerRuntimeHandle

logger = logging.getLogger("ollyuw.local")

AGENT_TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent / "e2b-template"
LOCAL_SANDBOX_ID = "local"
E2B_WORKSPACE_PREFIX = "/home/user/workspace"

# Module-level singleton so the process survives across requests.
_worker_process: subprocess.Popen | None = None
_worker_env: dict[str, str] = {}


class LocalRuntime:
    """Drop-in replacement for E2BDesktopRuntime for local agent development.

    Runs the agent worker as a local subprocess instead of inside an E2B sandbox.
    No VNC desktop — desktop_url is None. Everything else (Redis, SSE, sessions)
    works identically to the E2B path.

    Switch via USE_LOCAL_AGENT=true in .env.
    """

    def __init__(self, workspace_path: str) -> None:
        self._workspace = Path(workspace_path).resolve()

    def start(
        self,
        *,
        computer_id: str,
        user_id: str,
        sandbox_id: str | None,
        snapshot_id: str | None,
        agent_env: dict[str, str] | None = None,
    ) -> ComputerRuntimeHandle:
        self._workspace.mkdir(parents=True, exist_ok=True)
        _kill_worker()
        _launch_worker(agent_env or {}, self._workspace)
        return _local_handle()

    def reconnect(self, sandbox_id: str) -> ComputerRuntimeHandle:
        # If the worker process is gone (backend restart, crash), raise so
        # computer_service falls back to start_runtime and relaunches it.
        if _worker_process is None or _worker_process.poll() is not None:
            raise RuntimeError("local agent worker is not running")
        return _local_handle()

    def pause(self, sandbox_id: str) -> None:
        _kill_worker()

    def snapshot(self, sandbox_id: str, name: str | None = None) -> str:
        return "local-snapshot"

    def power_off(self, sandbox_id: str, snapshot_name: str | None = None) -> str:
        _kill_worker()
        return "local-snapshot"

    def keepalive(self, sandbox_id: str) -> None:
        pass

    def run_command(self, sandbox_id: str, command: str) -> str:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(self._workspace),
            timeout=30,
        )
        return result.stdout + result.stderr

    def write_workspace_file(self, sandbox_id: str, workspace_path: str, content: bytes) -> None:
        if workspace_path.startswith(E2B_WORKSPACE_PREFIX):
            rel = workspace_path[len(E2B_WORKSPACE_PREFIX):].lstrip("/")
            target = self._workspace / rel
        else:
            target = self._workspace / Path(workspace_path).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def list_workspace_files(self, sandbox_id: str, workspace_root: str) -> list[str]:
        if not self._workspace.exists():
            return []
        return sorted(
            str(p.relative_to(self._workspace)).replace("\\", "/")
            for p in self._workspace.rglob("*")
            if p.is_file() and not p.name.startswith(".")
        )

    def list_workspace_folders(self, sandbox_id: str, workspace_root: str) -> list[str]:
        if not self._workspace.exists():
            return [""]
        folders = [""]
        for p in self._workspace.rglob("*"):
            if p.is_dir() and not p.name.startswith("."):
                folders.append(str(p.relative_to(self._workspace)).replace("\\", "/"))
        return sorted(folders)

    def apply_mac_look(self, sandbox_id: str) -> str:
        return "mac-look not available in local mode"


def _local_handle() -> ComputerRuntimeHandle:
    return ComputerRuntimeHandle(
        sandbox_id=LOCAL_SANDBOX_ID,
        desktop_host="",
        desktop_port=0,
        desktop_url=None,
    )


def _kill_worker() -> None:
    global _worker_process
    if _worker_process and _worker_process.poll() is None:
        _worker_process.terminate()
        try:
            _worker_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _worker_process.kill()
    _worker_process = None


def _launch_worker(env: dict[str, str], workspace: Path) -> None:
    global _worker_process, _worker_env

    if not env.get("SESSION_ID") or not env.get("REDIS_URL"):
        logger.warning("skipping local agent worker: SESSION_ID or REDIS_URL missing")
        return

    _worker_env = env
    worker_env = {
        **os.environ,
        **env,
        "WORKSPACE": str(workspace),
        "AGENT_STATE_PATH": str(workspace / ".agent_state.json"),
    }

    log_path = workspace / "worker.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(log_path, "w") as log_file:
            _worker_process = subprocess.Popen(
                [sys.executable, "-m", "agent.worker"],
                cwd=str(AGENT_TEMPLATE_DIR),
                env=worker_env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
        logger.info(
            "local agent worker started pid=%d session=%s workspace=%s log=%s",
            _worker_process.pid,
            env.get("SESSION_ID"),
            workspace,
            log_path,
        )
    except Exception as exc:
        logger.error("failed to start local agent worker: %s", exc)
