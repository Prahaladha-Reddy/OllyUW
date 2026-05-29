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
    ("desktop: x11vnc running",
     "ps -ef | grep x11vnc | grep -v grep || echo 'NOT RUNNING'"),
    ("desktop: xfce4-session running",
     "ps -ef | grep xfce4-session | grep -v grep || echo 'NOT RUNNING'"),
    ("desktop: noVNC port 6080",
     "ss -tlnp 2>/dev/null | grep ':6080' || echo 'NOT LISTENING'"),
    ("agent: worker process",
     "ps -ef | grep 'agent.worker' | grep -v grep || echo 'NOT RUNNING'"),
    ("agent: startup script",
     "cat /home/user/.agent_env.sh 2>&1 | head -10 || echo 'MISSING'"),
    ("agent: worker log (last 40 lines)",
     "tail -40 /tmp/worker.log 2>&1 || echo 'NO LOG FILE'"),
    ("agent: files present",
     "ls /home/user/agent/ 2>&1 || echo 'MISSING'"),
    ("all listening ports",
     "ss -tlnp 2>/dev/null || echo 'no ss'"),
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
    print(f"Connected.")
    print(f"  port 6901 (KasmVNC): https://{sandbox.get_host(6901)}/")
    print(f"  port 6080 (legacy):  https://{sandbox.get_host(6080)}/")
    print()

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
