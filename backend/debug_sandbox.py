"""
Standalone sandbox diagnostic.

Usage:
    cd backend
    uv run python debug_sandbox.py <sandbox_id>

Connects to a running sandbox and reports what's actually installed and running.
"""
from __future__ import annotations

import sys
from dotenv import load_dotenv
from pathlib import Path

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "backend" / ".env", override=True)

from e2b import Sandbox  # noqa: E402

CHECKS = [
    ("template check: start-desktop.sh exists",
     "ls -la /usr/local/bin/start-desktop.sh 2>&1 || echo MISSING"),
    ("template check: Xvnc installed",
     "which Xvnc 2>&1 || echo MISSING"),
    ("template check: openbox installed",
     "which openbox 2>&1 || echo MISSING"),
    ("template check: websockify installed",
     "which websockify 2>&1 || echo MISSING"),
    ("template check: novnc directory",
     "ls -d /usr/share/novnc 2>&1 || echo MISSING"),
    ("running processes (desktop stack)",
     "ps aux | grep -E 'Xvnc|websockify|openbox|thunar|xterm' | grep -v grep || echo 'NO DESKTOP PROCESSES'"),
    ("listening ports",
     "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null || echo 'no ss/netstat'"),
    ("desktop log",
     "cat /tmp/desktop.log 2>&1 || echo 'NO LOG FILE'"),
    ("startup script content",
     "cat /usr/local/bin/start-desktop.sh 2>&1 | head -30 || echo MISSING"),
]


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python debug_sandbox.py <sandbox_id>")
        print("\nOr to run start-desktop.sh manually: python debug_sandbox.py <sandbox_id> --run-script")
        sys.exit(1)

    sandbox_id = sys.argv[1]
    run_script = "--run-script" in sys.argv

    print(f"Connecting to sandbox: {sandbox_id}")
    sandbox = Sandbox.connect(sandbox_id)
    print(f"Connected. Host for port 6080: {sandbox.get_host(6080)}\n")

    if run_script:
        print("=== Running start-desktop.sh manually (background) ===")
        sandbox.commands.run(
            "nohup /usr/local/bin/start-desktop.sh > /tmp/desktop.log 2>&1 &",
            timeout=10,
        )
        print("Triggered. Sleeping 8s for it to start...\n")
        import time
        time.sleep(8)

    for label, cmd in CHECKS:
        print(f"--- {label} ---")
        try:
            result = sandbox.commands.run(cmd, timeout=10)
            output = (result.stdout + result.stderr).strip()
            print(output if output else "(empty)")
        except Exception as exc:
            print(f"ERROR: {exc}")
        print()


if __name__ == "__main__":
    main()
