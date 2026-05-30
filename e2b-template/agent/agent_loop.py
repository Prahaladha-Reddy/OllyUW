"""
Async agent loop.

Key changes from the sync version:
- Fully async (asyncio throughout)
- Parallel tool calls via asyncio.gather — all calls in a step run concurrently
- Post-task skill curator pass (fire-and-forget)
- No underwriting-specific validation
- mem0 removed
"""
from __future__ import annotations

import asyncio
import time
import traceback
from pathlib import Path
from typing import Any

from agent.config import DEFAULT_MODEL, MAX_STEPS, SESSION_ID, SESSIONS_DIR, WORKSPACE
from agent.events import FINAL, STATUS, TOOL_CALL, TOOL_RESULT
from agent.llm.streaming import step as model_step
from agent.log import log, preview
from agent.observability.langfuse_setup import flush as _langfuse_flush
from agent.redis_io import publish_sync as publish
from agent.state import load as load_state
from agent.state import save as save_state
from agent.tools import dispatch as tool_dispatch


async def process_message(
    user_text: str,
    model: str = DEFAULT_MODEL,
    session_id: str = SESSION_ID,
) -> None:
    log.info("process_message model=%s session=%s text=%s", model, session_id, preview(user_text, 120))

    state_path = SESSIONS_DIR / session_id / "agent_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)

    messages = load_state(state_path)
    messages.append({"role": "user", "content": user_text})
    publish({"type": STATUS, "text": "Processing message", "model": model})

    transcript: list[str] = []
    all_tool_calls: list[dict] = []

    for step_idx in range(MAX_STEPS):
        from agent.redis_io import heartbeat
        heartbeat()
        publish({"type": STATUS, "text": f"Step {step_idx + 1}/{MAX_STEPS}"})

        turn = await model_step(messages, model, step_idx + 1, emit_text=True)
        if turn.get("text"):
            transcript.append(turn["text"])

        if turn["kind"] == "final":
            full_text = "\n\n".join(s.strip() for s in transcript if s.strip()) or turn["text"]

            messages.append({"role": "assistant", "content": full_text})
            save_state(messages, state_path)

            _langfuse_flush()
            log.info("final model=%s steps=%d text_len=%d", model, step_idx + 1, len(full_text))

            publish({
                "type":       FINAL,
                "text":       full_text,
                "model":      model,
                "tool_calls": all_tool_calls or None,
            })

            # Post-task skill curation — fire and forget, don't block the response.
            trajectory = _build_trajectory(messages[-40:])
            asyncio.create_task(_curate(trajectory, model))
            return

        # Accumulate tool calls for the final event
        for call in turn["calls"]:
            all_tool_calls.append({"id": call["id"], "tool": call["name"], "args": call["args"]})

        messages.append({
            "role":              "assistant",
            "content":           turn.get("text", "") or "",
            "tool_calls":        turn["calls"],
            "reasoning_content": turn.get("reasoning_content", "") or "",
        })

        # Execute ALL tool calls in this step in parallel.
        await asyncio.gather(*[_execute_tool_call(call, messages) for call in turn["calls"]])

        save_state(messages, state_path)

    # Hit MAX_STEPS
    stop_msg = f"Reached max steps ({MAX_STEPS}). Ask me to continue if needed."
    messages.append({"role": "assistant", "content": stop_msg})
    save_state(messages, state_path)
    log.warning("hit MAX_STEPS=%d model=%s", MAX_STEPS, model)
    publish({"type": FINAL, "text": stop_msg, "model": model})


async def _execute_tool_call(call: dict[str, Any], messages: list[dict[str, Any]]) -> None:
    """Dispatch one tool call, publish events, append result to messages."""
    call_id   = call["id"]
    tool_name = call["name"]
    tool_args = call["args"] if isinstance(call["args"], dict) else {}

    publish({"type": TOOL_CALL, "id": call_id, "tool": tool_name, "args": tool_args})

    t_tool = time.monotonic()
    try:
        output = await tool_dispatch(tool_name, tool_args)
        ok = True
        log.info(
            "tool_result name=%s id=%s ok=true duration_ms=%d output=%s",
            tool_name, call_id, int((time.monotonic() - t_tool) * 1000), preview(output),
        )
    except Exception as exc:
        output = f"ERROR: {exc}\n{traceback.format_exc()}"
        ok = False
        log.error(
            "tool_result name=%s id=%s ok=false duration_ms=%d err=%s",
            tool_name, call_id, int((time.monotonic() - t_tool) * 1000), exc,
        )

    wire_output = output if len(output) < 2000 else output[:2000] + f"...<+{len(output) - 2000}b>"
    publish({"type": TOOL_RESULT, "id": call_id, "tool": tool_name, "ok": ok, "output": wire_output})

    messages.append({
        "role":         "tool",
        "content":      output,
        "tool_call_id": call_id,
        "name":         tool_name,
    })


async def _curate(trajectory: str, model: str) -> None:
    try:
        from agent.skills.curator import curate
        await curate(trajectory, model)
    except Exception as exc:
        log.debug("curator error (non-fatal): %s", exc)


def _build_trajectory(messages: list[dict[str, Any]]) -> str:
    """Summarise recent messages into a trajectory string for the curator."""
    parts = []
    for m in messages:
        role = m.get("role", "")
        if role == "user":
            parts.append(f"USER: {str(m.get('content', ''))[:300]}")
        elif role == "assistant":
            text = str(m.get("content", ""))[:300]
            calls = m.get("tool_calls") or []
            call_names = [c.get("name", "") for c in calls]
            if call_names:
                parts.append(f"AGENT: {text}  [tools: {', '.join(call_names)}]")
            elif text:
                parts.append(f"AGENT: {text}")
        elif role == "tool":
            name = m.get("name", "tool")
            out = str(m.get("content", ""))[:200]
            parts.append(f"  → {name}: {out}")
    return "\n".join(parts)
