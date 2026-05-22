"""
OllyUW agent worker — runs inside the E2B sandbox.

Lifecycle:
  1. Blocks on Redis Stream (INPUT_STREAM) waiting for user messages.
  2. For each message: calls the LLM in an agentic loop (up to MAX_STEPS).
  3. Publishes events (model_delta, tool_call, tool_result, final, …)
     to Redis Pub/Sub (OUTPUT_CHANNEL) so the backend can SSE-stream them.
  4. Heartbeats OUTPUT every HEARTBEAT_INTERVAL seconds so the backend can
     detect a dead sandbox.

LLM protocol:
  The model must reply with exactly one JSON object per turn:
    {"type": "tool_call", "tool": "<name>", "args": {...}}   → execute tool
    {"type": "final",     "text": "<answer>"}                 → done
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import redis

# Worker code lives at /home/user/; tools.py is uploaded alongside it.
sys.path.insert(0, "/home/user")
import tools as _tools  # noqa: E402
load_dotenv()

# ── Config from env ──────────────────────────────────────────────────────────

SESSION_ID = os.environ["SESSION_ID"]
REDIS_URL = os.environ["REDIS_URL"]
INPUT_STREAM = os.environ.get("INPUT_STREAM", f"agent:{SESSION_ID}:messages")
OUTPUT_CHANNEL = os.environ.get("OUTPUT_CHANNEL", f"agent:{SESSION_ID}:chunks")
HEARTBEAT_KEY = os.environ.get("HEARTBEAT_KEY", f"agent:{SESSION_ID}:heartbeat")
CONSUMER_GROUP = "agent"
CONSUMER_NAME = f"sandbox-{SESSION_ID}"
WORKSPACE = Path(os.environ.get("WORKSPACE", "/home/user/workspace")).resolve()
STATE_PATH = Path("/home/user/agent_state.json")

LLM_BASE_URL = os.environ.get("MODAL_TURBO_BASE_URL", "")
LLM_MODEL = os.environ.get("MODAL_MODEL", "google/gemma-4-26B-A4B-it")
LLM_API_KEY = os.environ.get("MODAL_API_KEY", "unused")

HEARTBEAT_INTERVAL = 10  # seconds between heartbeats
MAX_STEPS = 12

# Update tools module's WORKSPACE so path checks use our env var
_tools.WORKSPACE = WORKSPACE

# ── Redis ────────────────────────────────────────────────────────────────────

_redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
_seq = 0


def _publish(event: dict[str, Any]) -> None:
    global _seq
    _seq += 1
    event.setdefault("session_id", SESSION_ID)
    event["seq"] = _seq
    _redis.publish(OUTPUT_CHANNEL, json.dumps(event, ensure_ascii=False))


def _heartbeat() -> None:
    _redis.set(HEARTBEAT_KEY, "1", ex=HEARTBEAT_INTERVAL * 3)


def _ensure_consumer_group() -> None:
    try:
        _redis.xgroup_create(INPUT_STREAM, CONSUMER_GROUP, id="0", mkstream=True)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


# ── State persistence ────────────────────────────────────────────────────────

def _load_state() -> list[dict[str, str]]:
    if not STATE_PATH.exists():
        return []
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        messages = data.get("messages", [])
        return messages if isinstance(messages, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_state(messages: list[dict[str, str]]) -> None:
    STATE_PATH.write_text(
        json.dumps({"messages": messages}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── LLM ─────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are a long-running AI agent inside an E2B Linux sandbox. "
    "Your workspace is /home/user/workspace. "
    "You have access to these tools: list_files, read_file, write_file, run_shell. "
    "Respond with exactly one JSON object — no markdown, no extra text. "
    "To call a tool: "
    '{"type":"tool_call","tool":"<name>","args":{...}}. '
    "To answer the user: "
    '{"type":"final","text":"<your answer>"}. '
    "Always use tools for any file, code, or shell request before answering."
)


def _call_model(messages: list[dict[str, str]]) -> dict[str, Any]:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    base_url = LLM_BASE_URL.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"

    llm = ChatOpenAI(
        model=LLM_MODEL,
        base_url=base_url,
        api_key=LLM_API_KEY,
        temperature=0,
        timeout=180,
        max_retries=1,
        streaming=True,
    )

    chat_msgs = [SystemMessage(content=_SYSTEM_PROMPT)]
    for m in messages[-24:]:
        role, content = m.get("role", ""), m.get("content", "")
        if role == "user":
            chat_msgs.append(HumanMessage(content=content))
        else:
            chat_msgs.append(HumanMessage(content=f"{role}: {content}"))

    _publish({"type": "model_start"})
    parts: list[str] = []
    for chunk in llm.stream(chat_msgs):
        text = str(chunk.content)
        if not text:
            continue
        parts.append(text)
        _publish({"type": "model_delta", "text": text})

    raw = "".join(parts).strip()
    _publish({"type": "model_end"})
    _publish({"type": "model_raw", "text": raw})

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"type": "final", "text": raw}


# ── Agent loop ───────────────────────────────────────────────────────────────

def _process_message(user_text: str) -> None:
    messages = _load_state()
    messages.append({"role": "user", "content": user_text})
    _publish({"type": "status", "text": "Processing message"})

    for step in range(MAX_STEPS):
        _heartbeat()
        _publish({"type": "status", "text": f"Step {step + 1}/{MAX_STEPS}"})

        action = _call_model(messages)

        if action.get("type") == "final":
            text = str(action.get("text", ""))
            messages.append({"role": "assistant", "content": text})
            _save_state(messages)
            _publish({"type": "final", "text": text})
            return

        if action.get("type") != "tool_call":
            fallback = f"Unexpected model response: {action}"
            messages.append({"role": "assistant", "content": fallback})
            _save_state(messages)
            _publish({"type": "final", "text": fallback})
            return

        tool = str(action.get("tool", ""))
        tool_args = action.get("args", {})
        if not isinstance(tool_args, dict):
            tool_args = {}

        _publish({"type": "tool_call", "tool": tool, "args": tool_args})
        try:
            output = _tools.run_tool(tool, tool_args)
            _publish({"type": "tool_result", "tool": tool, "ok": True, "output": output})
        except Exception as exc:
            output = f"ERROR: {exc}"
            _publish({"type": "tool_result", "tool": tool, "ok": False, "output": output})

        messages.append({"role": "assistant", "content": json.dumps(action)})
        messages.append({"role": "tool", "content": f"{tool} result:\n{output}"})

    stop_msg = f"Reached max steps ({MAX_STEPS}). Ask me to continue if needed."
    messages.append({"role": "assistant", "content": stop_msg})
    _save_state(messages)
    _publish({"type": "final", "text": stop_msg})


# ── Main event loop ──────────────────────────────────────────────────────────

def main() -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    _ensure_consumer_group()
    _publish({"type": "worker_ready", "text": "Agent worker is running"})

    last_heartbeat = 0.0

    while True:
        now = time.monotonic()
        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            _heartbeat()
            last_heartbeat = now

        response = _redis.xreadgroup(
            CONSUMER_GROUP,
            CONSUMER_NAME,
            {INPUT_STREAM: ">"},
            count=1,
            block=5000,
        )
        if not response:
            continue

        for _stream, entries in response:
            for message_id, fields in entries:
                try:
                    raw = fields.get("data", "{}")
                    payload = json.loads(raw)
                    user_text = str(payload.get("message", ""))
                    _publish({"type": "message_received", "message_id": message_id})
                    _process_message(user_text)
                    _redis.xack(INPUT_STREAM, CONSUMER_GROUP, message_id)
                    _publish({"type": "message_acked", "message_id": message_id})
                except Exception as exc:
                    _publish({"type": "error", "text": str(exc), "message_id": message_id})
                    _redis.xack(INPUT_STREAM, CONSUMER_GROUP, message_id)

        time.sleep(0.05)


if __name__ == "__main__":
    main()
