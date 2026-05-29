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
    ("template check: kasmvncserver installed",
     "which kasmvncserver 2>&1 || echo MISSING"),
    ("template check: xfce4-session installed",
     "which xfce4-session 2>&1 || echo MISSING"),
    ("template check: firefox installed",
     "which firefox 2>&1 || echo MISSING"),
    ("running processes (desktop stack)",
     "ps -ef | grep -E 'Xvnc|kasmvnc|xfce4-session|xfdesktop|xfwm4|xfce4-panel' | grep -v grep || echo 'NO DESKTOP PROCESSES'"),
    ("agent worker process",
     "ps -ef | grep 'agent.worker' | grep -v grep || echo 'NO AGENT WORKER'"),
    ("listening ports",
     "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null || echo 'no ss/netstat'"),
    ("port 6901 (KasmVNC) check",
     "ss -tlnp 2>/dev/null | grep ':6901' || echo 'NOT LISTENING'"),
    ("desktop log (last 40 lines)",
     "tail -40 /tmp/desktop.log 2>&1 || echo 'NO LOG FILE'"),
    ("worker log (last 40 lines)",
     "tail -40 /tmp/worker.log 2>&1 || echo 'NO LOG FILE'"),
    ("xfconf check (Unable to contact settings server?)",
     "DISPLAY=:1 sudo -u user xfconf-query -c xfwm4 -p /general/use_compositing 2>&1 || echo 'xfconf FAILED'"),
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
