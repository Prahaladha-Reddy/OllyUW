from __future__ import annotations

import logging
import shlex
import time
from dataclasses import dataclass
from pathlib import Path

from e2b_desktop import Sandbox as DesktopSandbox

from src.config import get_settings

logger = logging.getLogger("ollyuw.e2b")

AGENT_DIR = Path(__file__).parent.parent.parent.parent / "e2b-template" / "agent"


@dataclass(frozen=True)
class ComputerRuntimeHandle:
    sandbox_id: str
    desktop_host: str
    desktop_port: int
    desktop_url: str


class E2BDesktopRuntime:
    def __init__(self) -> None:
        self._settings = get_settings()

    def start(
        self,
        *,
        computer_id: str,
        user_id: str,
        sandbox_id: str | None,
        snapshot_id: str | None,
        agent_env: dict[str, str] | None = None,
    ) -> ComputerRuntimeHandle:
        desktop = self._connect_or_create(
            computer_id=computer_id,
            user_id=user_id,
            sandbox_id=sandbox_id,
            snapshot_id=snapshot_id,
        )

        self._start_stream(desktop)
        self._upload_and_start_agent(desktop, agent_env or {})

        url = desktop.stream.get_url()
        host = desktop.get_host(6080)
        sid = str(getattr(desktop, "sandbox_id", None) or getattr(desktop, "sandboxId", ""))

        return ComputerRuntimeHandle(
            sandbox_id=sid,
            desktop_host=host,
            desktop_port=6080,
            desktop_url=url,
        )

    def pause(self, sandbox_id: str) -> None:
        desktop = self._connect(sandbox_id)
        desktop.pause()

    def snapshot(self, sandbox_id: str, name: str | None = None) -> str:
        desktop = self._connect(sandbox_id)
        info = desktop.create_snapshot(name=name)
        return info.snapshot_id

    def power_off(self, sandbox_id: str, snapshot_name: str | None = None) -> str:
        desktop = self._connect(sandbox_id)
        info = desktop.create_snapshot(name=snapshot_name)
        desktop.kill()
        return info.snapshot_id

    def run_command(self, sandbox_id: str, command: str) -> str:
        desktop = self._connect(sandbox_id)
        result = desktop.commands.run(command, timeout=30)
        return result.stdout + result.stderr

    def _connect(self, sandbox_id: str) -> DesktopSandbox:
        return DesktopSandbox.connect(
            sandbox_id,
            timeout=self._settings.e2b.sandbox_timeout,
            api_key=self._settings.e2b.api_key,
        )

    def _connect_or_create(
        self,
        *,
        computer_id: str,
        user_id: str,
        sandbox_id: str | None,
        snapshot_id: str | None,
    ) -> DesktopSandbox:
        if sandbox_id:
            try:
                return self._connect(sandbox_id)
            except Exception as exc:
                logger.warning("could not reconnect sandbox %s: %s", sandbox_id, exc)

        metadata = {"computer_id": computer_id, "user_id": user_id}
        lifecycle = {"on_timeout": "pause", "auto_resume": False}

        if snapshot_id:
            logger.info("creating sandbox from snapshot: %s", snapshot_id)
            return DesktopSandbox.create(
                snapshot_id,
                timeout=self._settings.e2b.sandbox_timeout,
                metadata=metadata,
                lifecycle=lifecycle,
                api_key=self._settings.e2b.api_key,
            )

        logger.info("creating fresh desktop sandbox")
        return DesktopSandbox.create(
            timeout=self._settings.e2b.sandbox_timeout,
            metadata=metadata,
            lifecycle=lifecycle,
            api_key=self._settings.e2b.api_key,
        )

    def _start_stream(self, desktop: DesktopSandbox) -> None:
        try:
            desktop.stream.start(require_auth=False)
            logger.info("desktop stream started on sandbox %s", desktop.sandbox_id)
        except Exception as exc:
            logger.warning("stream.start() failed: %s", exc)
            return

        # Wait up to 30s for noVNC port 6080 to be ready.
        for attempt in range(15):
            try:
                result = desktop.commands.run(
                    "ss -tlnp 2>/dev/null | grep -q ':6080' && echo READY || echo WAIT",
                    timeout=5,
                )
                if "READY" in (result.stdout or ""):
                    logger.info("noVNC ready on port 6080 (attempt %d)", attempt + 1)
                    return
            except Exception:
                pass
            time.sleep(2)

        logger.warning("noVNC did not become ready within 30s")

    def _upload_and_start_agent(self, desktop: DesktopSandbox, env: dict[str, str]) -> None:
        if not env.get("SESSION_ID") or not env.get("REDIS_URL"):
            logger.warning("skipping agent worker: SESSION_ID or REDIS_URL missing")
            return

        # Upload agent package if source is available locally.
        if AGENT_DIR.exists():
            self._upload_agent_files(desktop)
        else:
            logger.warning("agent source not found at %s, skipping upload", AGENT_DIR)

        # Install Python agent dependencies (they are not on the desktop template).
        install_cmd = (
            "pip3 install --quiet --break-system-packages "
            "redis langchain-openai langchain-core openai python-dotenv tiktoken "
            "mem0ai parallel-web langfuse pdfplumber pymupdf pytesseract "
            "pillow pandas 2>&1 | tail -5"
        )
        try:
            desktop.commands.run(install_cmd, timeout=180)
            logger.info("agent Python deps installed on sandbox %s", desktop.sandbox_id)
        except Exception as exc:
            logger.warning("failed to install agent deps: %s", exc)
            return

        # Start the worker process.
        env_str = " ".join(f"{k}={shlex.quote(str(v))}" for k, v in env.items() if v)
        kill_cmd = "pkill -f 'python3 -m agent.worker' 2>/dev/null || true"
        start_cmd = (
            f"cd /home/user && nohup env {env_str} "
            "python3 -m agent.worker > /tmp/worker.log 2>&1 &"
        )
        try:
            desktop.commands.run(kill_cmd, timeout=5)
            desktop.commands.run(start_cmd, timeout=10)
            logger.info("agent worker started (session=%s)", env.get("SESSION_ID"))
        except Exception as exc:
            logger.warning("failed to start agent worker: %s", exc)

    def _upload_agent_files(self, desktop: DesktopSandbox) -> None:
        try:
            desktop.commands.run("mkdir -p /home/user/agent", timeout=5)
            for path in AGENT_DIR.rglob("*.py"):
                relative = path.relative_to(AGENT_DIR)
                remote_path = f"/home/user/agent/{relative.as_posix()}"
                # Ensure parent directory exists.
                parent = remote_path.rsplit("/", 1)[0]
                desktop.commands.run(f"mkdir -p {parent}", timeout=5)
                desktop.files.write(remote_path, path.read_text(encoding="utf-8"))
            logger.info("agent files uploaded to sandbox %s", desktop.sandbox_id)
        except Exception as exc:
            logger.warning("failed to upload agent files: %s", exc)
