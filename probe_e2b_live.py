"""
Live E2B integration probe — run this directly to test everything end-to-end.

Usage:
    cd c:/Users/bored/Documents/olive_assignment
    uv run --project backend python probe_e2b_live.py

What it does:
1. Creates a fresh E2B desktop sandbox
2. Uploads agent files + installs deps
3. Installs BrowserOS + waits for port 9000
4. Starts the agent worker
5. Sends a test message via Redis and waits for the response
6. Prints a full health report

Takes ~3-5 minutes on first run (BrowserOS .deb download).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "e2b-template"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import redis as redis_lib
from e2b_desktop import Sandbox as DesktopSandbox

from src.providers.e2b_provider import E2BDesktopRuntime, AGENT_DIR
from src.config import get_settings


OK  = "[OK]"
ERR = "[FAIL]"
WARN = "[WARN]"

def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check(label: str, ok: bool, detail: str = "") -> None:
    sym = OK if ok else ERR
    print(f"  {sym} {label}" + (f": {detail}" if detail else ""))


# ── 1. Settings ────────────────────────────────────────────────────────────────
section("1. Settings")
s = get_settings()
check("USE_LOCAL_AGENT=false", not s.use_local_agent)
check("Redis URL set", bool(s.redis_url), s.redis_url[:40])
check("E2B API key set", bool(s.e2b_api_key), s.e2b_api_key[:20])
check("DeepSeek key set", bool(s.deepseek_api_key))
check("MIMO key set", bool(s.mimo_api_key))
check("Agent dir exists", AGENT_DIR.exists(), str(AGENT_DIR))

if s.use_local_agent:
    print(f"\n{ERR} USE_LOCAL_AGENT is True — set to false in .env first!")
    sys.exit(1)


# ── 2. Redis connectivity ──────────────────────────────────────────────────────
section("2. Redis (Upstash)")
try:
    r = redis_lib.from_url(s.redis_url, socket_connect_timeout=5, decode_responses=True)
    r.ping()
    check("Ping OK", True)
    r.close()
except Exception as exc:
    check("Ping", False, str(exc))
    print(f"\n{ERR} Redis failed — cannot continue")
    sys.exit(1)


# ── 3. Create E2B sandbox ──────────────────────────────────────────────────────
section("3. Creating E2B desktop sandbox")
print("  Starting fresh sandbox (this takes ~30-60s)...")

runtime = E2BDesktopRuntime()
SESSION_ID = f"probe-{int(time.time())}"

agent_env = {
    "SESSION_ID": SESSION_ID,
    "OLLYUW_USER_ID": "probe-user",
    "REDIS_URL": s.redis_url,
    "WORKSPACE": "/home/user/workspace",
    "DEEPSEEK_API_KEY": s.deepseek_api_key,
    "DEEPSEEK_BASE_URL": s.deepseek_base_url,
    "DEEPSEEK_MODEL": s.deepseek_model,
    "MIMO_API_KEY": s.mimo_api_key,
    "MIMI_API_KEY": s.mimo_api_key,
    "MIMO_BASE_URL": s.mimo_base_url,
    "MIMO_MODEL": s.mimo_model,
    "MEM0_API_KEY": s.mem0_api_key,
    "PARALLEL_API_KEY": s.parallel_api_key,
    "LANGFUSE_PUBLIC_KEY": s.langfuse_public_key,
    "LANGFUSE_SECRET_KEY": s.langfuse_secret_key,
    "LANGFUSE_BASE_URL": s.langfuse_base_url,
}

try:
    t0 = time.monotonic()
    handle = runtime.start(
        computer_id=SESSION_ID,
        user_id="probe-user",
        sandbox_id=None,
        snapshot_id=None,
        agent_env=agent_env,
    )
    elapsed = time.monotonic() - t0
    check("Sandbox created", True, f"id={handle.sandbox_id} ({elapsed:.0f}s)")
    SANDBOX_ID = handle.sandbox_id
except Exception as exc:
    check("Sandbox create", False, str(exc))
    sys.exit(1)


# ── 4. Connect and probe sandbox health ───────────────────────────────────────
section("4. Sandbox health probe")

desktop = DesktopSandbox.connect(SANDBOX_ID, api_key=s.e2b_api_key)

def run(cmd: str, timeout: int = 15) -> str:
    try:
        r = desktop.commands.run(cmd, timeout=timeout)
        return ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception as exc:
        return f"ERROR: {exc}"

# Worker
worker_out = run("pgrep -af '[a]gent.worker'")
check("Agent worker running", bool(worker_out) and "ERROR" not in worker_out, worker_out[:100])

# BrowserOS process
bros_proc = run("pgrep -af '[b]rowseros'")
check("BrowserOS process", bool(bros_proc) and "ERROR" not in bros_proc, (bros_proc or "not found")[:100])

# BrowserOS port
bros_port = run("ss -tlnp | grep ':9000'")
check("BrowserOS port 9000", bool(bros_port) and "ERROR" not in bros_port, (bros_port or "not open")[:80])

# Agent files uploaded
skills_out = run("ls /home/user/agent/skills/catalog/ 2>/dev/null")
check("Skills uploaded", bool(skills_out) and "ERROR" not in skills_out, skills_out[:100])

yaml_out = run("ls /home/user/agent/subagents/definitions/ 2>/dev/null")
check("Subagent YAML uploaded", bool(yaml_out) and "ERROR" not in yaml_out, yaml_out[:100])

# Memory / soul (will be empty on fresh sandbox — that's fine)
mem_out = run("cat /home/user/memory.md 2>/dev/null || echo EMPTY")
check("memory.md accessible", True, ("custom" if "EMPTY" not in mem_out else "empty (fresh sandbox — OK)"))

soul_out = run("cat /home/user/soul.md 2>/dev/null || echo EMPTY")
check("soul.md accessible", True, ("custom" if "EMPTY" not in soul_out else "empty → default used"))

# Worker log
worker_log = run("tail -20 /tmp/worker.log 2>/dev/null || echo NO_LOG")
worker_ready = "worker_ready" in worker_log or "WORKER_READY" in worker_log.upper()
check("Worker reported READY", worker_ready, worker_log[-200:] if not worker_ready else "")

# BrowserOS log
bros_log = run("tail -10 /tmp/browseros.log 2>/dev/null || echo NO_LOG")
print(f"  [INFO] BrowserOS log: {bros_log[:200]}")


# ── 5. Send a test message and wait for response ───────────────────────────────
section("5. Agent message round-trip")

INPUT_STREAM  = f"agent:{SESSION_ID}:messages"
OUTPUT_CHANNEL = f"agent:{SESSION_ID}:chunks"

r2 = redis_lib.from_url(s.redis_url, socket_connect_timeout=10, decode_responses=True)

# Ensure stream consumer group
try:
    r2.xgroup_create(INPUT_STREAM, "agent", id="0", mkstream=True)
except Exception:
    pass

# Send message
msg = "Reply with exactly three words: AGENT IS ALIVE"
r2.xadd(INPUT_STREAM, {"data": json.dumps({"message": msg, "model": "deepseek", "session_id": SESSION_ID})})
print(f"  -> Sent message to {INPUT_STREAM}")

pubsub = r2.pubsub()
pubsub.subscribe(OUTPUT_CHANNEL)
print(f"  Waiting for response (timeout=120s)...")

final_text = None
t_start = time.monotonic()
while time.monotonic() - t_start < 120:
    msg_raw = pubsub.get_message(timeout=2)
    if msg_raw and msg_raw["type"] == "message":
        try:
            payload = json.loads(msg_raw["data"])
            if payload.get("type") == "final":
                final_text = payload.get("text", "")
                elapsed_msg = time.monotonic() - t_start
                print(f"  Response received in {elapsed_msg:.1f}s")
                break
            elif payload.get("type") in ("status", "tool_call", "tool_result"):
                evt_type = payload.get("type", "")
                detail = payload.get("text", payload.get("tool", ""))[:60]
                t_rel = time.monotonic() - t_start
                print(f"    +{t_rel:.1f}s [{evt_type}] {detail}")
        except Exception:
            pass

pubsub.unsubscribe()
r2.close()

if final_text:
    check("Got final response", True, final_text[:100])
else:
    check("Got final response", False, "timed out after 120s")
    # Dump worker log to debug
    print("\n  Worker log (last 40 lines):")
    print(run("tail -40 /tmp/worker.log 2>/dev/null", timeout=10))


# ── 6. Summary ────────────────────────────────────────────────────────────────
section("Summary")
print(f"  Sandbox ID : {SANDBOX_ID}")
print(f"  Session ID : {SESSION_ID}")
print(f"  To probe again: uv run --project backend python tests/test_e2e_components.py --sandbox {SANDBOX_ID}")
print(f"\n  Final response: {(final_text or 'NONE')[:200]}")
print()
