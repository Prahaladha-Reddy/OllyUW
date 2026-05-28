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
        return f"https://{self.desktop_host}"


class E2BDesktopRuntime:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._desktop_port = 6080

    def start(self, *, computer_id: str, user_id: str, sandbox_id: str | None, snapshot_id: str | None) -> ComputerRuntimeHandle:
        sandbox = self._connect_or_create(computer_id=computer_id, user_id=user_id, sandbox_id=sandbox_id, snapshot_id=snapshot_id)
        self._bootstrap_workspace(sandbox)
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

        # Start desktop environment (if the template includes it)
        # This runs the VNC + noVNC servers on port 6080
        try:
            sandbox.commands.run("/usr/local/bin/start-desktop.sh", timeout=30)
        except Exception as e:
            logger.warning("failed to start desktop: %s", e)
