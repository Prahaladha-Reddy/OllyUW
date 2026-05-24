"""
OllyUW agent worker — runs inside the E2B sandbox.

Lifecycle:
  1. Blocks on Redis Stream (INPUT_STREAM) waiting for user messages.
  2. For each message: runs an agentic loop using **native tool calling**
     via LangChain's `ChatOpenAI.bind_tools(...)`. The model is selected
     per-message (Modal-hosted Gemma 4 with vLLM's `gemma4` tool parser,
     or DeepSeek's native function calling). Same code path for both —
     only the (base_url, api_key, model_name) triple changes.
  3. Publishes events (text_delta, tool_call, tool_result, final, ...)
     to Redis Pub/Sub (OUTPUT_CHANNEL) so the backend can SSE-stream them.
  4. Heartbeats every HEARTBEAT_INTERVAL seconds so the backend can
     detect a dead sandbox.

Why native tool calling (and not a JSON-in-text prompt contract):
  vLLM's `--tool-call-parser gemma4` and DeepSeek's API both return
  structured `tool_calls` in a dedicated response field, separate from
  the visible `content` channel. That lets us publish clean `text_delta`
  events from `chunk.content` and accumulate `tool_call_chunks` into
  proper `tool_call` events — no streaming-JSON extractor, no risk of
  format markers leaking into the user-visible text.
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
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

DEFAULT_MODEL = "modal"
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
# Conversation history is a JSON-serialisable list of dicts:
#   {"role": "user",      "content": str}
#   {"role": "assistant", "content": str, "tool_calls"?: [{"id","name","args"}]}
#   {"role": "tool",      "content": str, "tool_call_id": str, "name": str}
# The tool_call/tool_result pairing (matching `tool_call_id`) is what stops
# the model from re-calling tools it already called on the previous step.

def _load_state() -> list[dict[str, Any]]:
    if not STATE_PATH.exists():
        return []
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        messages = data.get("messages", [])
        return messages if isinstance(messages, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_state(messages: list[dict[str, Any]]) -> None:
    STATE_PATH.write_text(
        json.dumps({"messages": messages}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── LLM ─────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are OllyUW, an AI agent helping the user analyse documents and code "
    "inside an E2B Linux sandbox. Your workspace is /home/user/workspace, "
    "where the user has uploaded files. Use the available tools to inspect, "
    "read, search, and run shell commands on those files before answering. "
    "When you have enough information, reply directly to the user in clear "
    "Markdown."
)


# OpenAI-spec tool descriptors. The model sees these via bind_tools(); the
# actual execution still goes through `_tools.run_tool(name, args)` so the
# workspace-safety guards in tools.py stay authoritative.
_TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List the contents of a directory inside the workspace. "
                "Returns one entry per line; directories end with '/'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path relative to the workspace. Default: '.' (workspace root).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file from the workspace and return its full contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write a UTF-8 text file to the workspace. Creates parent "
                "directories as needed. Overwrites existing files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "Path relative to the workspace."},
                    "content": {"type": "string", "description": "Full file contents to write."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": (
                "Run a shell command inside the workspace and return stdout, "
                "stderr, and the exit code. Use sparingly — prefer read_file "
                "and list_files for inspection."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute."},
                },
                "required": ["command"],
            },
        },
    },
]


def _resolve_llm_config(model: str) -> tuple[str, str, str]:
    """
    Map a stable model id to the concrete (base_url, api_key, model_name)
    triple for that provider. Both backends are OpenAI-compatible; the
    *server-side* tool parser (vLLM's `gemma4` for Modal, DeepSeek's
    native parser for DeepSeek) takes care of structured tool_calls.
    """
    if model == "deepseek":
        return (
            os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            os.environ.get("DEEPSEEK_API_KEY", ""),
            os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        )
    # default: Modal-hosted Gemma 4 via vLLM
    return (
        os.environ.get("MODAL_TURBO_BASE_URL", ""),
        os.environ.get("MODAL_API_KEY", "unused"),
        os.environ.get("MODAL_MODEL", "google/gemma-4-26B-A4B-it"),
    )


def _build_chat_messages(messages: list[dict[str, Any]]):
    """
    Translate persisted history into proper LangChain message objects.

    Critical: assistant turns that called tools must be re-materialised as
    AIMessage(tool_calls=[...]) and their results as ToolMessage with matching
    tool_call_id, so the model sees the call/result pairing and doesn't
    re-invoke the same tool on the next iteration.
    """
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )

    chat: list[Any] = [SystemMessage(content=_SYSTEM_PROMPT)]
    for m in messages[-24:]:
        role = m.get("role", "")
        content = m.get("content", "") or ""
        if role == "user":
            chat.append(HumanMessage(content=content))
        elif role == "assistant":
            tcs = m.get("tool_calls") or []
            chat.append(AIMessage(content=content, tool_calls=tcs))
        elif role == "tool":
            chat.append(ToolMessage(
                content=content,
                tool_call_id=m.get("tool_call_id", ""),
                name=m.get("name", ""),
            ))
    return chat


def _call_model_step(
    messages: list[dict[str, Any]], model: str,
) -> dict[str, Any]:
    """
    One model invocation. Streams visible text to clients as it arrives,
    accumulates streamed tool_call_chunks server-side, and returns the
    resolved turn:

      {"kind": "final", "text": str}                  — model answered
      {"kind": "tools", "calls": [{id,name,args}]}    — model wants tools
    """
    from langchain_openai import ChatOpenAI

    base_url, api_key, model_name = _resolve_llm_config(model)
    base_url = base_url.rstrip("/")
    if base_url and not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"

    llm = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=0,
        timeout=180,
        max_retries=1,
        streaming=True,
    ).bind_tools(_TOOL_SPECS)

    _publish({"type": "model_start", "model": model})

    content_parts: list[str] = []
    # tool_call_chunks come with a stable `index` we use to group fragments.
    tc_acc: dict[int, dict[str, str]] = {}

    for chunk in llm.stream(_build_chat_messages(messages)):
        # 1) Visible text (clean — no JSON wrapper, no extractor needed).
        text = getattr(chunk, "content", "") or ""
        if isinstance(text, str) and text:
            content_parts.append(text)
            _publish({"type": "text_delta", "text": text})

        # 2) Streamed tool-call fragments (name / args arrive piece-by-piece).
        for tcc in (getattr(chunk, "tool_call_chunks", None) or []):
            idx = tcc.get("index") or 0
            slot = tc_acc.setdefault(idx, {"id": "", "name": "", "args": ""})
            if tcc.get("id"):
                slot["id"] = tcc["id"]
            if tcc.get("name"):
                slot["name"] = tcc["name"]
            if tcc.get("args"):
                slot["args"] = slot["args"] + tcc["args"]

    _publish({"type": "model_end", "model": model})

    if tc_acc:
        calls: list[dict[str, Any]] = []
        for idx in sorted(tc_acc):
            slot = tc_acc[idx]
            raw_args = slot["args"]
            try:
                args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                args = {"_raw": raw_args}
            if not isinstance(args, dict):
                args = {"_value": args}
            calls.append({
                "id":   slot["id"] or f"call_{uuid.uuid4().hex[:12]}",
                "name": slot["name"],
                "args": args,
            })
        return {"kind": "tools", "calls": calls}

    return {"kind": "final", "text": "".join(content_parts)}


# ── Agent loop ───────────────────────────────────────────────────────────────

def _process_message(user_text: str, model: str) -> None:
    messages = _load_state()
    messages.append({"role": "user", "content": user_text})
    _publish({"type": "status", "text": "Processing message", "model": model})

    for step in range(MAX_STEPS):
        _heartbeat()
        _publish({"type": "status", "text": f"Step {step + 1}/{MAX_STEPS}"})

        turn = _call_model_step(messages, model)

        if turn["kind"] == "final":
            text = turn["text"]
            messages.append({"role": "assistant", "content": text})
            _save_state(messages)
            _publish({"type": "final", "text": text, "model": model})
            return

        # turn["kind"] == "tools"
        # Persist the assistant's tool-call turn so the model has the
        # tool_call/tool_result pairing on the next pass.
        messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": turn["calls"],
        })

        for call in turn["calls"]:
            call_id   = call["id"]
            tool_name = call["name"]
            tool_args = call["args"] if isinstance(call["args"], dict) else {}

            _publish({
                "type": "tool_call",
                "id":   call_id,
                "tool": tool_name,
                "args": tool_args,
            })
            try:
                output = _tools.run_tool(tool_name, tool_args)
                ok = True
            except Exception as exc:
                output = f"ERROR: {exc}"
                ok = False

            _publish({
                "type":   "tool_result",
                "id":     call_id,
                "tool":   tool_name,
                "ok":     ok,
                "output": output,
            })
            messages.append({
                "role":         "tool",
                "content":      output,
                "tool_call_id": call_id,
                "name":         tool_name,
            })

        _save_state(messages)

    stop_msg = f"Reached max steps ({MAX_STEPS}). Ask me to continue if needed."
    messages.append({"role": "assistant", "content": stop_msg})
    _save_state(messages)
    _publish({"type": "final", "text": stop_msg, "model": model})


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
                    model = str(payload.get("model") or DEFAULT_MODEL)
                    _publish({"type": "message_received", "message_id": message_id, "model": model})
                    _process_message(user_text, model)
                    _redis.xack(INPUT_STREAM, CONSUMER_GROUP, message_id)
                    _publish({"type": "message_acked", "message_id": message_id})
                except Exception as exc:
                    _publish({"type": "error", "text": str(exc), "message_id": message_id})
                    _redis.xack(INPUT_STREAM, CONSUMER_GROUP, message_id)

        time.sleep(0.05)


if __name__ == "__main__":
    main()
