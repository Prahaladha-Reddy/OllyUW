from __future__ import annotations

import logging
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

        if not self._install_agent_deps(desktop):
            return

        self._launch_worker(desktop, env)

    def _install_agent_deps(self, desktop: DesktopSandbox) -> bool:
        # The desktop template ships system Python 3.10 with pip 22, which the
        # unprivileged "user" account cannot write to system site-packages with.
        # So install into the per-user site (~/.local) with --user. The worker
        # also runs as "user", so these packages are importable at runtime.
        #
        # Only the packages the agent actually imports are installed. The heavy
        # document/image libraries are deliberately excluded: nothing in the
        # agent imports them, and their wheel builds are what made the install
        # slow and prone to failure.
        # redis is pinned: redis-py 8.x defaults to RESP3 and regresses blocking
        # XREADGROUP reads into a socket timeout against Upstash. 7.4.0 is the
        # version verified to return cleanly on an idle blocking read.
        install_cmd = (
            "pip3 install --user --quiet --no-warn-script-location "
            "'redis==7.4.0' python-dotenv langchain-openai langchain-core openai "
            "tiktoken mem0ai parallel-web langfuse"
        )
        try:
            # No exit-code masking here: commands.run raises on a non-zero exit
            # so a failed install is loud instead of silently swallowed.
            desktop.commands.run(install_cmd, timeout=300)
        except Exception as exc:
            logger.error("agent dep install failed on %s: %s", desktop.sandbox_id, exc)
            return False

        # Verify the critical imports actually resolve before launching the
        # worker, so we never start a process that will crash on import.
        verify = "import dotenv, redis, langchain_openai, langchain_core, openai, tiktoken"
        try:
            desktop.commands.run(f"python3 -c '{verify}'", timeout=40)
        except Exception as exc:
            logger.error("agent deps installed but imports fail on %s: %s", desktop.sandbox_id, exc)
            return False

        logger.info("agent Python deps installed on sandbox %s", desktop.sandbox_id)
        return True

    def _launch_worker(self, desktop: DesktopSandbox, env: dict[str, str]) -> None:
        # Kill any stale worker from a previous start. The [a]gent.worker pattern
        # is the classic self-exclusion trick: the regex matches the running
        # worker's command line ("...-m agent.worker") but NOT pkill's own shell
        # command line (which contains the literal "[a]gent.worker"), so pkill
        # does not kill itself and exit with a signal code.
        try:
            desktop.commands.run("pkill -f '[a]gent.worker'; true", timeout=10)
        except Exception as exc:
            logger.warning("pkill of stale worker failed (continuing): %s", exc)

        # Use the SDK's native envs= and background=True so env vars are passed
        # directly without any shell quoting, and the process is backgrounded
        # cleanly without nohup/& hacks.
        try:
            desktop.commands.run(
                "mkdir -p /home/user/workspace && cd /home/user && "
                "python3 -u -m agent.worker > /tmp/worker.log 2>&1",
                envs=env,
                background=True,
            )
        except Exception as exc:
            logger.error("failed to start agent worker: %s", exc)
            return

        # Confirm the worker is actually alive and report the truth in the logs.
        time.sleep(3)
        try:
            check = desktop.commands.run(
                "pgrep -f '[a]gent.worker' >/dev/null && echo ALIVE || echo DEAD",
                timeout=10,
            )
            if "ALIVE" in (check.stdout or ""):
                logger.info("agent worker started (session=%s)", env.get("SESSION_ID"))
            else:
                log = desktop.commands.run("tail -20 /tmp/worker.log 2>&1 || true", timeout=10)
                logger.error(
                    "agent worker exited immediately (session=%s). worker.log tail:\n%s",
                    env.get("SESSION_ID"),
                    (log.stdout or "") + (log.stderr or ""),
                )
        except Exception as exc:
            logger.warning("could not verify worker status: %s", exc)

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
