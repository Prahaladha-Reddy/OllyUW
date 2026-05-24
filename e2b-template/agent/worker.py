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

Every significant event is also logged to stderr (captured by worker.log
in the sandbox) with timestamps so an operator can pull the log via the
backend `/debug/worker-log` endpoint and see exactly what happened.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import redis

# Worker code lives at /home/user/; tools.py is uploaded alongside it.
sys.path.insert(0, "/home/user")
import tools as _tools  # noqa: E402
load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────────────
# Emit to stderr so it lands in worker.log (the wrapping shell redirects
# both stdout and stderr there). Default INFO, DEBUG via env var.

logging.basicConfig(
    level=os.environ.get("WORKER_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("ollyuw.worker")


def _preview(s: Any, n: int = 200) -> str:
    """Short, single-line preview of arbitrary content for log lines."""
    text = s if isinstance(s, str) else json.dumps(s, ensure_ascii=False, default=str)
    text = text.replace("\n", "\\n")
    return text if len(text) <= n else text[:n] + f"...<+{len(text)-n}b>"


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
HISTORY_WINDOW = 24

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
#   {"role": "assistant", "content": str, "tool_calls"?: [{"id","name","args"}],
#    "reasoning_content"?: str}
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
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("could not read state file: %s", exc)
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
    if model == "deepseek":
        return (
            os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            os.environ.get("DEEPSEEK_API_KEY", ""),
            os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        )
    return (
        os.environ.get("MODAL_TURBO_BASE_URL", ""),
        os.environ.get("MODAL_API_KEY", "unused"),
        os.environ.get("MODAL_MODEL", "google/gemma-4-26B-A4B-it"),
    )


def _history_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Return a recent history slice without breaking OpenAI tool-call ordering.
    A plain `messages[-N:]` can start with a ToolMessage whose matching
    assistant `tool_calls` turn was just outside the window, which providers
    reject as an orphan tool result.
    """
    start = max(0, len(messages) - HISTORY_WINDOW)
    while start > 0 and messages[start].get("role") == "tool":
        start -= 1

    window = messages[start:]
    seen_tool_call_ids: set[str] = set()
    safe: list[dict[str, Any]] = []
    skipped_orphan_tools = 0

    for message in window:
        role = message.get("role", "")
        if role == "assistant":
            for call in message.get("tool_calls") or []:
                call_id = str(call.get("id") or "")
                if call_id:
                    seen_tool_call_ids.add(call_id)
            safe.append(message)
        elif role == "tool":
            tool_call_id = str(message.get("tool_call_id") or "")
            if tool_call_id and tool_call_id in seen_tool_call_ids:
                safe.append(message)
            else:
                skipped_orphan_tools += 1
        else:
            safe.append(message)

    if skipped_orphan_tools:
        log.warning(
            "dropped %d orphan tool message(s) while building model history",
            skipped_orphan_tools,
        )
    return safe


def _build_chat_messages(messages: list[dict[str, Any]]):
    """
    Translate persisted history into LangChain message objects. Assistant
    turns that called tools come back as AIMessage(tool_calls=...) and their
    results as ToolMessage with matching tool_call_id — that's what keeps the
    model from re-calling tools it already called on the next step.
    """
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )

    chat: list[Any] = [SystemMessage(content=_SYSTEM_PROMPT)]
    for m in _history_messages(messages):
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


def _obj_field(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    value = getattr(obj, key, default)
    if value is not default:
        return value
    model_dump = getattr(obj, "model_dump", None)
    if callable(model_dump):
        try:
            return model_dump(exclude_none=True).get(key, default)
        except TypeError:
            return model_dump().get(key, default)
    return default


def _openai_tool_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for call in calls:
        args = call.get("args") or {}
        if isinstance(args, str):
            arguments = args
        else:
            arguments = json.dumps(args, ensure_ascii=False)
        out.append({
            "id": call.get("id", ""),
            "type": "function",
            "function": {
                "name": call.get("name", ""),
                "arguments": arguments,
            },
        })
    return out


def _build_deepseek_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chat: list[dict[str, Any]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for m in _history_messages(messages):
        role = m.get("role", "")
        content = m.get("content", "") or ""
        if role == "user":
            chat.append({"role": "user", "content": content})
        elif role == "assistant":
            item: dict[str, Any] = {"role": "assistant", "content": content}
            reasoning_content = m.get("reasoning_content")
            if reasoning_content:
                item["reasoning_content"] = reasoning_content
            tcs = m.get("tool_calls") or []
            if tcs:
                item["content"] = content or None
                item["tool_calls"] = _openai_tool_calls(tcs)
            chat.append(item)
        elif role == "tool":
            chat.append({
                "role": "tool",
                "tool_call_id": m.get("tool_call_id", ""),
                "content": content,
            })
    return chat


def _chunk_text(chunk: Any) -> str:
    """Pull visible text out of a streaming chunk. content can be a str or a
    list of content-blocks (multimodal LLMs); we want only the text bits."""
    content = getattr(chunk, "content", "") or ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out: list[str] = []
        for block in content:
            if isinstance(block, str):
                out.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                out.append(str(block.get("text", "")))
        return "".join(out)
    return str(content)


def _call_deepseek_step(
    messages: list[dict[str, Any]],
    model: str,
    step: int,
    base_url: str,
    api_key: str,
    model_name: str,
) -> dict[str, Any]:
    from openai import OpenAI

    log.info(
        "step=%d model=%s base_url=%s history_len=%d",
        step, model, base_url, len(messages),
    )
    if log.isEnabledFor(logging.DEBUG):
        for i, m in enumerate(messages[-6:]):
            log.debug("  history[-%d] role=%s preview=%s",
                      len(messages[-6:]) - i, m.get("role"), _preview(m.get("content")))

    client = OpenAI(api_key=api_key, base_url=base_url)
    _publish({"type": "model_start", "model": model})

    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    tc_acc: dict[int, dict[str, str]] = {}
    chunks_seen = 0
    text_chunks_seen = 0
    t_start = time.monotonic()

    try:
        stream = client.chat.completions.create(
            model=model_name,
            messages=_build_deepseek_messages(messages),
            tools=_TOOL_SPECS,
            temperature=0,
            timeout=180,
            stream=True,
        )
        for chunk in stream:
            chunks_seen += 1
            choices = _obj_field(chunk, "choices", []) or []
            if not choices:
                continue
            delta = _obj_field(choices[0], "delta")
            reasoning = _obj_field(delta, "reasoning_content")
            if reasoning:
                reasoning_parts.append(str(reasoning))

            text = _obj_field(delta, "content")
            if text:
                text_chunks_seen += 1
                content_parts.append(str(text))
                _publish({"type": "text_delta", "text": str(text)})

            for tcc in (_obj_field(delta, "tool_calls", []) or []):
                idx = _obj_field(tcc, "index", 0) or 0
                slot = tc_acc.setdefault(idx, {"id": "", "name": "", "args": ""})
                call_id = _obj_field(tcc, "id")
                if call_id:
                    slot["id"] = str(call_id)
                function = _obj_field(tcc, "function")
                name = _obj_field(function, "name")
                if name:
                    slot["name"] = str(name)
                args = _obj_field(function, "arguments")
                if args:
                    slot["args"] = slot["args"] + str(args)
    except Exception:
        log.exception("model stream failed at step=%d model=%s", step, model)
        _publish({"type": "model_end", "model": model, "error": True})
        raise

    elapsed_ms = int((time.monotonic() - t_start) * 1000)
    text_buf = "".join(content_parts)
    reasoning_buf = "".join(reasoning_parts)
    _publish({"type": "model_end", "model": model})

    log.info(
        "step=%d model=%s done elapsed_ms=%d chunks=%d text_chunks=%d "
        "text_len=%d reasoning_len=%d tool_calls=%d",
        step, model, elapsed_ms, chunks_seen, text_chunks_seen,
        len(text_buf), len(reasoning_buf), len(tc_acc),
    )
    if text_buf:
        log.info("  text_preview: %s", _preview(text_buf))

    if tc_acc:
        calls: list[dict[str, Any]] = []
        for idx in sorted(tc_acc):
            slot = tc_acc[idx]
            raw_args = slot["args"]
            try:
                args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError as exc:
                log.warning("could not parse tool args idx=%d raw=%r err=%s",
                            idx, raw_args, exc)
                args = {"_raw": raw_args}
            if not isinstance(args, dict):
                args = {"_value": args}
            calls.append({
                "id":   slot["id"] or f"call_{uuid.uuid4().hex[:12]}",
                "name": slot["name"],
                "args": args,
            })
            log.info("  tool_call name=%s id=%s args=%s",
                     calls[-1]["name"], calls[-1]["id"], _preview(args))
        return {
            "kind": "tools",
            "calls": calls,
            "text": text_buf,
            "reasoning_content": reasoning_buf,
        }

    return {"kind": "final", "text": text_buf}


def _call_model_step(
    messages: list[dict[str, Any]], model: str, step: int,
) -> dict[str, Any]:
    """
    One model invocation. Streams visible text to clients as it arrives,
    accumulates streamed tool_call_chunks server-side, and returns the
    resolved turn:

      {"kind": "final", "text": str}
      {"kind": "tools", "calls": [{id,name,args}], "text": str}

    The 'text' on a 'tools' turn captures any preface the model emitted
    *before* its tool calls — important for models like DeepSeek that
    sometimes narrate ("I'll create that file…") then call the tool.
    """
    from langchain_openai import ChatOpenAI

    base_url, api_key, model_name = _resolve_llm_config(model)
    base_url = base_url.rstrip("/")
    if base_url and not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"

    if model == "deepseek":
        return _call_deepseek_step(messages, model, step, base_url, api_key, model_name)

    log.info(
        "step=%d model=%s base_url=%s history_len=%d",
        step, model, base_url, len(messages),
    )
    if log.isEnabledFor(logging.DEBUG):
        for i, m in enumerate(messages[-6:]):
            log.debug("  history[-%d] role=%s preview=%s",
                      len(messages[-6:]) - i, m.get("role"), _preview(m.get("content")))

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
    tc_acc: dict[int, dict[str, str]] = {}
    chunks_seen = 0
    text_chunks_seen = 0
    t_start = time.monotonic()

    try:
        for chunk in llm.stream(_build_chat_messages(messages)):
            chunks_seen += 1

            # Visible text (clean — no JSON wrapper, no extractor needed).
            text = _chunk_text(chunk)
            if text:
                text_chunks_seen += 1
                content_parts.append(text)
                _publish({"type": "text_delta", "text": text})

            # Streamed tool-call fragments (name / args arrive piece-by-piece).
            for tcc in (getattr(chunk, "tool_call_chunks", None) or []):
                idx = tcc.get("index") or 0
                slot = tc_acc.setdefault(idx, {"id": "", "name": "", "args": ""})
                if tcc.get("id"):
                    slot["id"] = tcc["id"]
                if tcc.get("name"):
                    slot["name"] = tcc["name"]
                if tcc.get("args"):
                    slot["args"] = slot["args"] + tcc["args"]
    except Exception:
        log.exception("model stream failed at step=%d model=%s", step, model)
        _publish({"type": "model_end", "model": model, "error": True})
        raise

    elapsed_ms = int((time.monotonic() - t_start) * 1000)
    text_buf = "".join(content_parts)
    _publish({"type": "model_end", "model": model})

    log.info(
        "step=%d model=%s done elapsed_ms=%d chunks=%d text_chunks=%d "
        "text_len=%d tool_calls=%d",
        step, model, elapsed_ms, chunks_seen, text_chunks_seen,
        len(text_buf), len(tc_acc),
    )
    if text_buf:
        log.info("  text_preview: %s", _preview(text_buf))

    if tc_acc:
        calls: list[dict[str, Any]] = []
        for idx in sorted(tc_acc):
            slot = tc_acc[idx]
            raw_args = slot["args"]
            try:
                args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError as exc:
                log.warning("could not parse tool args idx=%d raw=%r err=%s",
                            idx, raw_args, exc)
                args = {"_raw": raw_args}
            if not isinstance(args, dict):
                args = {"_value": args}
            calls.append({
                "id":   slot["id"] or f"call_{uuid.uuid4().hex[:12]}",
                "name": slot["name"],
                "args": args,
            })
            log.info("  tool_call name=%s id=%s args=%s",
                     calls[-1]["name"], calls[-1]["id"], _preview(args))
        return {"kind": "tools", "calls": calls, "text": text_buf}

    return {"kind": "final", "text": text_buf}


# ── Agent loop ───────────────────────────────────────────────────────────────

def _process_message(user_text: str, model: str) -> None:
    log.info("process_message model=%s text=%s", model, _preview(user_text, 120))
    messages = _load_state()
    messages.append({"role": "user", "content": user_text})
    _publish({"type": "status", "text": "Processing message", "model": model})

    # Visible text accumulated across all iterations of this turn. The
    # *frontend* sees every delta live, but the *persisted* assistant
    # message has to capture the whole thing too (preface text from
    # tool-calling turns + the final answer text), otherwise refetch
    # would replace the live transcript with just the final iteration.
    transcript: list[str] = []

    for step in range(MAX_STEPS):
        _heartbeat()
        _publish({"type": "status", "text": f"Step {step + 1}/{MAX_STEPS}"})

        turn = _call_model_step(messages, model, step + 1)
        if turn.get("text"):
            transcript.append(turn["text"])

        if turn["kind"] == "final":
            full_text = "\n\n".join(s.strip() for s in transcript if s.strip())
            if not full_text:
                full_text = turn["text"]
            messages.append({"role": "assistant", "content": full_text})
            _save_state(messages)
            log.info("final model=%s steps=%d text_len=%d", model, step + 1, len(full_text))
            _publish({"type": "final", "text": full_text, "model": model})
            return

        # turn["kind"] == "tools"
        # Persist the assistant's tool-call turn (including any preface
        # text) so the model has the call/result pairing on the next pass.
        messages.append({
            "role":       "assistant",
            "content":    turn.get("text", "") or "",
            "tool_calls": turn["calls"],
            "reasoning_content": turn.get("reasoning_content", "") or "",
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

            t_tool = time.monotonic()
            try:
                output = _tools.run_tool(tool_name, tool_args)
                ok = True
                log.info(
                    "tool_result name=%s id=%s ok=true duration_ms=%d output=%s",
                    tool_name, call_id, int((time.monotonic() - t_tool) * 1000),
                    _preview(output),
                )
            except Exception as exc:
                output = f"ERROR: {exc}\n{traceback.format_exc()}"
                ok = False
                log.error(
                    "tool_result name=%s id=%s ok=false duration_ms=%d err=%s",
                    tool_name, call_id, int((time.monotonic() - t_tool) * 1000), exc,
                )

            _publish({
                "type":   "tool_result",
                "id":     call_id,
                "tool":   tool_name,
                "ok":     ok,
                # Keep stream payload small; the model still sees full output below.
                "output": output if len(output) < 2000 else output[:2000] + f"...<+{len(output)-2000}b>",
            })
            messages.append({
                "role":         "tool",
                "content":      output,
                "tool_call_id": call_id,
                "name":         tool_name,
            })

        _save_state(messages)

    stop_msg = f"Reached max steps ({MAX_STEPS}). Ask me to continue if needed."
    transcript.append(stop_msg)
    full_text = "\n\n".join(s.strip() for s in transcript if s.strip())
    messages.append({"role": "assistant", "content": full_text})
    _save_state(messages)
    log.warning("hit MAX_STEPS=%d for model=%s", MAX_STEPS, model)
    _publish({"type": "final", "text": full_text, "model": model})


# ── Main event loop ──────────────────────────────────────────────────────────

def main() -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    _ensure_consumer_group()
    log.info(
        "worker_ready session=%s workspace=%s stream=%s channel=%s",
        SESSION_ID, WORKSPACE, INPUT_STREAM, OUTPUT_CHANNEL,
    )
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
                    log.info("message_received id=%s model=%s len=%d",
                             message_id, model, len(user_text))
                    _publish({"type": "message_received", "message_id": message_id, "model": model})
                    _process_message(user_text, model)
                    _redis.xack(INPUT_STREAM, CONSUMER_GROUP, message_id)
                    _publish({"type": "message_acked", "message_id": message_id})
                except Exception as exc:
                    log.exception("failed to process message id=%s", message_id)
                    _publish({
                        "type": "error",
                        "text": f"{type(exc).__name__}: {exc}",
                        "message_id": message_id,
                    })
                    _redis.xack(INPUT_STREAM, CONSUMER_GROUP, message_id)

        time.sleep(0.05)


if __name__ == "__main__":
    main()
