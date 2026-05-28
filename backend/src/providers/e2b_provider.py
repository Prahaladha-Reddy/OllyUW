from __future__ import annotations

import logging
from dataclasses import dataclass

from e2b import Sandbox

from src.config import get_settings

logger = logging.getLogger("ollyuw.e2b")


@dataclass(frozen=True)
class ComputerRuntimeHandle:
    sandbox_id: str
    desktop_host: str
    desktop_port: int

    @property
    def desktop_url(self) -> str:
        return f"https://{self.desktop_host}/vnc.html?autoconnect=true&resize=scale&reconnect=true"


class E2BDesktopRuntime:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._desktop_port = 6080

    def start(self, *, computer_id: str, user_id: str, sandbox_id: str | None, snapshot_id: str | None, agent_env: dict[str, str] | None = None) -> ComputerRuntimeHandle:
        sandbox = self._connect_or_create(computer_id=computer_id, user_id=user_id, sandbox_id=sandbox_id, snapshot_id=snapshot_id)
        self._bootstrap_workspace(sandbox)
        self._start_agent_worker(sandbox, agent_env or {})
        return self._handle_for(sandbox)

    def pause(self, sandbox_id: str) -> None:
        sandbox = self.connect(sandbox_id)
        sandbox.pause()

    def snapshot(self, sandbox_id: str, name: str | None = None) -> str:
        sandbox = self.connect(sandbox_id)
        info = sandbox.create_snapshot(name=name)
        return info.snapshot_id

    def power_off(self, sandbox_id: str, snapshot_name: str | None = None) -> str:
        sandbox = self.connect(sandbox_id)
        info = sandbox.create_snapshot(name=snapshot_name)
        sandbox.kill()
        return info.snapshot_id

    def run_command(self, sandbox_id: str, command: str) -> str:
        sandbox = self.connect(sandbox_id)
        result = sandbox.commands.run(command, timeout=30)
        return result.stdout + result.stderr

    def connect(self, sandbox_id: str) -> Sandbox:
        return Sandbox.connect(
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
    ) -> Sandbox:
        # First preference: reconnect to the existing sandbox if it still exists.
        # This gives us the exact same sandbox identity and live paused state.
        if sandbox_id:
            try:
                return self.connect(sandbox_id)
            except Exception as exc:
                logger.warning("could not reconnect sandbox %s: %s", sandbox_id, exc)
        if snapshot_id:
            return self._create_from_snapshot(
                snapshot_id=snapshot_id,
                computer_id=computer_id,
                user_id=user_id,
            )

        # Final fallback: create a brand new sandbox from the desktop template.
        return self._create_from_template(
            computer_id=computer_id,
            user_id=user_id,
        )

    def _create_from_snapshot(self, *, snapshot_id: str, computer_id: str, user_id: str) -> Sandbox:
        lifecycle = {"on_timeout": "pause", "auto_resume": False}
        metadata = {"computer_id": computer_id, "user_id": user_id}
        return Sandbox.create(
            snapshot_id,
            timeout=self._settings.e2b.sandbox_timeout,
            metadata=metadata,
            lifecycle=lifecycle,
            api_key=self._settings.e2b.api_key,
        )

    def _create_from_template(self, *, computer_id: str, user_id: str) -> Sandbox:
        lifecycle = {"on_timeout": "pause", "auto_resume": False}
        metadata = {"computer_id": computer_id, "user_id": user_id}
        template_id = self._settings.e2b.desktop_template_id or "desktop"
        logger.info("creating sandbox from template: %s", template_id)
        return Sandbox.create(
            template_id,
            timeout=self._settings.e2b.sandbox_timeout,
            metadata=metadata,
            lifecycle=lifecycle,
            api_key=self._settings.e2b.api_key,
        )

    def _handle_for(self, sandbox: Sandbox) -> ComputerRuntimeHandle:
        sandbox_id = str(getattr(sandbox, "sandbox_id", None) or getattr(sandbox, "sandboxId", ""))
        desktop_host = sandbox.get_host(self._desktop_port)
        return ComputerRuntimeHandle(
            sandbox_id=sandbox_id,
            desktop_host=desktop_host,
            desktop_port=self._desktop_port,
        )

    def _bootstrap_workspace(self, sandbox: Sandbox) -> None:
        workspace_path = self._settings.e2b.workspace_path
        bootstrap_script = f"""\
set -e
mkdir -p {workspace_path}
cd {workspace_path}
if ! command -v git >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1; then
    sudo apt-get update >/dev/null 2>&1
    sudo apt-get install -y git >/dev/null 2>&1
  else
    apt-get update >/dev/null 2>&1
    apt-get install -y git >/dev/null 2>&1
  fi
fi
if [ ! -d .git ]; then
  git init -b main . >/dev/null 2>&1 || (git init . >/dev/null 2>&1 && git branch -M main >/dev/null 2>&1)
fi
if [ ! -f .gitignore ]; then
  cat > .gitignore <<'EOF'
.cache/
.local/
Downloads/
tmp/
*.log
EOF
fi
"""
        sandbox.commands.run(bootstrap_script, timeout=120)

        # Launch desktop in background then wait for noVNC to be ready on port 6080.
        # The script runs: Xvfb -> XFCE -> x11vnc -> websockify (foreground, keeps alive).
        try:
            sandbox.commands.run(
                "nohup /usr/local/bin/start-desktop.sh > /tmp/desktop.log 2>&1 &",
                timeout=10,
            )
            logger.info("desktop startup initiated on sandbox %s", sandbox.sandbox_id)
        except Exception as e:
            logger.warning("failed to start desktop: %s", e)
            return

        # Poll until websockify is listening on 6080 (up to 30s).
        import time
        for attempt in range(15):
            try:
                result = sandbox.commands.run(
                    "ss -tlnp 2>/dev/null | grep -q ':6080' && echo READY || echo WAIT",
                    timeout=5,
                )
                if "READY" in (result.stdout or ""):
                    logger.info("desktop ready on port 6080 (attempt %d)", attempt + 1)
                    return
            except Exception:
                pass
            time.sleep(2)
        logger.warning("desktop did not become ready within 30s — check /tmp/desktop.log")

    def _start_agent_worker(self, sandbox: Sandbox, env: dict[str, str]) -> None:
        if not env.get("SESSION_ID") or not env.get("REDIS_URL"):
            logger.warning("skipping agent worker: SESSION_ID or REDIS_URL missing")
            return
        import shlex
        env_str = " ".join(f"{k}={shlex.quote(str(v))}" for k, v in env.items() if v)
        # Kill any stale worker from a previous connect, then start fresh.
        kill_cmd = "pkill -f 'python -m agent.worker' 2>/dev/null || true"
        start_cmd = f"nohup env {env_str} python -m agent.worker > /tmp/worker.log 2>&1 &"
        try:
            sandbox.commands.run(kill_cmd, timeout=5)
            sandbox.commands.run(start_cmd, timeout=10)
            logger.info("agent worker started on sandbox %s (session=%s)", sandbox.sandbox_id, env.get("SESSION_ID"))
        except Exception as exc:
            logger.warning("failed to start agent worker: %s", exc)
