from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from e2b_desktop import Sandbox as DesktopSandbox

from src.config import get_settings

logger = logging.getLogger("ollyuw.e2b")

AGENT_DIR = Path(__file__).parent.parent.parent.parent / "e2b-template" / "agent"

# The e2b desktop template boots at 1024x768 by default, which looks cramped
# and dated. 1280x800 is the MacBook 16:10 ratio: roomier and sharper without
# pushing enough extra pixels through VNC to noticeably hurt latency. Set at
# create() time because resolution is an Xvfb startup parameter (display :0),
# so it only takes effect on a fresh boot, not on reconnect to a live sandbox.
DESKTOP_RESOLUTION = (1280, 800)
DESKTOP_DPI = 96

# One-shot script that restyles the running XFCE desktop to look like macOS:
# WhiteSur GTK theme + icons, a Plank dock, a wallpaper, and the compositor
# turned off (a pure latency win for VNC). It is written to be safe to run
# more than once and to never hard fail: every step degrades gracefully so a
# missing package or a failed clone does not abort the rest.
#
# It runs as the same user that e2b uses for startxfce4, so $HOME and the live
# session (display :0) line up. Settings are applied through xfconf-query,
# which writes them to the on-disk xfconf XML via the daemon, so once the
# sandbox is snapshotted the look survives every future boot.
MAC_LOOK_SCRIPT = """\
#!/bin/bash
LOG() { echo "[mac-look] $*"; }
export DISPLAY=:0

apt_get() {
    sudo -n DEBIAN_FRONTEND=noninteractive apt-get "$@" 2>/dev/null \\
      || DEBIAN_FRONTEND=noninteractive apt-get "$@" 2>/dev/null || true
}

LOG "installing packages"
apt_get update -qq
apt_get install -y -qq plank sassc git libglib2.0-dev-bin curl

SPID="$(pgrep -f xfce4-session | head -n1 || true)"
if [ -n "${SPID}" ]; then
    BUS="$(tr '\\0' '\\n' < /proc/$SPID/environ 2>/dev/null | sed -n 's/^DBUS_SESSION_BUS_ADDRESS=//p' | head -n1)"
    [ -n "${BUS}" ] && export DBUS_SESSION_BUS_ADDRESS="$BUS"
fi
LOG "xfce session pid=${SPID:-none}"

if [ ! -d "$HOME/.themes/WhiteSur-Dark" ]; then
    LOG "cloning WhiteSur GTK theme"
    rm -rf /tmp/WhiteSur-gtk-theme
    if git clone --depth=1 https://github.com/vinceliuice/WhiteSur-gtk-theme.git /tmp/WhiteSur-gtk-theme 2>/dev/null; then
        /tmp/WhiteSur-gtk-theme/install.sh -c Dark -d "$HOME/.themes" >/dev/null 2>&1 || LOG "gtk theme build had errors"
    else
        LOG "gtk theme clone failed"
    fi
fi

if [ ! -d "$HOME/.local/share/icons/WhiteSur-dark" ] && [ ! -d "$HOME/.icons/WhiteSur-dark" ]; then
    LOG "cloning WhiteSur icon theme"
    rm -rf /tmp/WhiteSur-icon-theme
    if git clone --depth=1 https://github.com/vinceliuice/WhiteSur-icon-theme.git /tmp/WhiteSur-icon-theme 2>/dev/null; then
        /tmp/WhiteSur-icon-theme/install.sh >/dev/null 2>&1 || LOG "icon theme had errors"
    else
        LOG "icon theme clone failed"
    fi
fi

mkdir -p "$HOME/Pictures"
if [ ! -f "$HOME/Pictures/wallpaper.jpg" ]; then
    WP="$(find /tmp/WhiteSur-gtk-theme -iname '*.jpg' -o -iname '*.png' 2>/dev/null | grep -im1 -E 'wallpaper|monterey|ventura|sonoma|whitesur' || true)"
    [ -n "${WP}" ] && cp "$WP" "$HOME/Pictures/wallpaper.jpg" 2>/dev/null || true
fi

LOG "applying xfconf theme settings"
xfconf-query -c xsettings -p /Net/ThemeName -s "WhiteSur-Dark" 2>/dev/null || true
xfconf-query -c xsettings -p /Net/IconThemeName -s "WhiteSur-dark" 2>/dev/null || true
xfconf-query -c xfwm4 -p /general/theme -s "WhiteSur-Dark" 2>/dev/null || true
xfconf-query -c xfwm4 -p /general/use_compositing -s false 2>/dev/null || true

if [ -f "$HOME/Pictures/wallpaper.jpg" ]; then
    for prop in $(xfconf-query -c xfce4-desktop -l 2>/dev/null | grep -E 'last-image$'); do
        xfconf-query -c xfce4-desktop -p "$prop" -s "$HOME/Pictures/wallpaper.jpg" 2>/dev/null || true
    done
fi

mkdir -p "$HOME/.config/autostart"
printf '[Desktop Entry]\\nType=Application\\nName=Plank\\nExec=plank\\nX-GNOME-Autostart-enabled=true\\n' \\
    > "$HOME/.config/autostart/plank.desktop"
pkill -f '[p]lank' 2>/dev/null || true
nohup plank >/dev/null 2>&1 &

LOG "done"
"""


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
        # start() always creates a brand new sandbox (fresh, or restored from a
        # snapshot). Reconnecting to an existing/paused sandbox is a separate
        # path (reconnect()), because the desktop SDK only wires up its VNC
        # server inside create() - a plain connect() leaves desktop.stream
        # uninitialised, so get_url() would crash here.
        desktop = self._create_sandbox(
            computer_id=computer_id,
            user_id=user_id,
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

    def write_workspace_file(
        self, sandbox_id: str, workspace_path: str, content: bytes
    ) -> None:
        desktop = self._connect(sandbox_id)
        # Ensure the parent directory exists before writing.
        parent = workspace_path.rsplit("/", 1)[0]
        if parent:
            desktop.commands.run(f"mkdir -p {parent}", timeout=10)
        desktop.files.write(workspace_path, content)

    def list_workspace_files(self, sandbox_id: str, workspace_root: str) -> list[str]:
        desktop = self._connect(sandbox_id)
        result = desktop.commands.run(
            f"find {workspace_root} -type f | sort 2>/dev/null || true",
            timeout=15,
        )
        lines = (result.stdout or "").strip().splitlines()
        prefix = workspace_root.rstrip("/") + "/"
        return [line[len(prefix):] for line in lines if line.startswith(prefix)]

    def list_workspace_folders(self, sandbox_id: str, workspace_root: str) -> list[str]:
        """Return all subdirectories inside workspace_root, relative to it.

        Includes the root itself as "" so the picker can show "/ (root)" as a
        valid drop target. Results are sorted so the tree renders in order.
        """
        desktop = self._connect(sandbox_id)
        result = desktop.commands.run(
            f"find {workspace_root} -type d | sort 2>/dev/null || true",
            timeout=15,
        )
        lines = (result.stdout or "").strip().splitlines()
        prefix = workspace_root.rstrip("/") + "/"
        folders: list[str] = []
        for line in lines:
            line = line.strip()
            if line == workspace_root.rstrip("/"):
                folders.append("")
            elif line.startswith(prefix):
                folders.append(line[len(prefix):])
        return folders

    def apply_mac_look(self, sandbox_id: str) -> str:
        """Restyle the live desktop to look like macOS. Returns the script log.

        Run this once per computer while it is running, then snapshot: the
        theme/icons/dock settings persist on disk and are reapplied on every
        future boot. Generous timeout because the first run clones theme repos
        and may build the GTK theme with sassc.

        The script is written to a file first because commands.run() does not
        reliably execute long multiline bash strings directly (heredocs and
        multi-statement scripts cause exit code -1 in the e2b SDK).
        """
        desktop = self._connect(sandbox_id)
        desktop.files.write("/tmp/mac_look.sh", MAC_LOOK_SCRIPT.encode())
        result = desktop.commands.run("bash /tmp/mac_look.sh", timeout=600)
        output = (result.stdout or "") + (result.stderr or "")
        logger.info("mac-look applied on %s:\n%s", sandbox_id, output)
        return output

    def reconnect(self, sandbox_id: str) -> ComputerRuntimeHandle:
        """Resume an existing (possibly idle-paused) sandbox and return a fresh
        desktop URL.

        connect() auto-resumes a paused sandbox and preserves every running
        process across the pause: Xvfb, x11vnc, noVNC, and the agent worker all
        come back. So we do not reinstall anything or relaunch the worker - we
        just wait for the noVNC port to answer again and rebuild the stream URL.

        The URL is built by hand rather than via desktop.stream.get_url()
        because the desktop SDK only constructs its VNC server object inside
        create(); a connected sandbox has no desktop.stream to ask.

        Passing timeout on connect also resets the idle TTL, so returning to the
        tab gives a full fresh idle window.
        """
        desktop = self._connect(sandbox_id)
        if not desktop.is_running():
            raise RuntimeError(f"sandbox {sandbox_id} is not running after connect")

        self._wait_for_novnc_port(desktop)
        host = desktop.get_host(6080)
        url = f"https://{host}/vnc.html?autoconnect=true&resize=scale"
        logger.info("reconnected sandbox %s, stream %s", sandbox_id, url)
        return ComputerRuntimeHandle(
            sandbox_id=sandbox_id,
            desktop_host=host,
            desktop_port=6080,
            desktop_url=url,
        )

    def keepalive(self, sandbox_id: str) -> None:
        """Reset the sandbox idle timeout.

        Called periodically while a browser tab is open so the sandbox stays
        alive during active use, including long agent tasks. When the tab
        closes the pings stop and E2B pauses the sandbox once the idle window
        (sandbox_timeout) elapses, preserving its state for the next resume.
        """
        desktop = self._connect(sandbox_id)
        desktop.set_timeout(self._settings.e2b.sandbox_timeout)

    def _connect(self, sandbox_id: str) -> DesktopSandbox:
        return DesktopSandbox.connect(
            sandbox_id,
            timeout=self._settings.e2b.sandbox_timeout,
            api_key=self._settings.e2b.api_key,
        )

    def _wait_for_novnc_port(self, desktop: DesktopSandbox, attempts: int = 10) -> None:
        """Wait for noVNC (port 6080) to answer after a resume before we hand
        the URL to the browser, so the client does not race a still-settling
        sandbox and show 'Failed to connect to server'."""
        for _ in range(attempts):
            try:
                result = desktop.commands.run(
                    "ss -tlnp 2>/dev/null | grep -q ':6080' && echo READY || echo WAIT",
                    timeout=5,
                )
                if "READY" in (result.stdout or ""):
                    return
            except Exception:
                pass
            time.sleep(1.5)
        logger.warning("noVNC port 6080 not ready after resume on %s", desktop.sandbox_id)

    def _create_sandbox(
        self,
        *,
        computer_id: str,
        user_id: str,
        snapshot_id: str | None,
    ) -> DesktopSandbox:
        metadata = {"computer_id": computer_id, "user_id": user_id}
        # on_timeout=pause: when the idle window elapses with no keepalive, E2B
        # pauses the sandbox (state preserved) rather than killing it, so the
        # next reconnect() can resume it instantly.
        lifecycle = {"on_timeout": "pause", "auto_resume": False}

        if snapshot_id:
            logger.info("creating sandbox from snapshot: %s", snapshot_id)
            return DesktopSandbox.create(
                snapshot_id,
                resolution=DESKTOP_RESOLUTION,
                dpi=DESKTOP_DPI,
                timeout=self._settings.e2b.sandbox_timeout,
                metadata=metadata,
                lifecycle=lifecycle,
                api_key=self._settings.e2b.api_key,
            )

        logger.info("creating fresh desktop sandbox")
        return DesktopSandbox.create(
            resolution=DESKTOP_RESOLUTION,
            dpi=DESKTOP_DPI,
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
