"""Async streaming step — single LLM call, returns parsed tool calls or final text."""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from agent.config import get_tool_specs
from agent.events import MODEL_END, MODEL_START, TEXT_DELTA
from agent.llm.messages import build_openai
from agent.llm.providers import normalise_base_url, resolve
from agent.log import log, preview
from agent.observability.langfuse_setup import openai_module
from agent.redis_io import publish_sync


async def step(
    messages: list[dict[str, Any]],
    model: str,
    step_num: int,
    emit_text: bool = True,
) -> dict[str, Any]:
    """Run one async model step. Returns {kind, calls, text, reasoning_content}."""
    base_url, api_key, model_name = resolve(model)
    base_url = normalise_base_url(base_url)

    OpenAI = openai_module().OpenAI
    log.info("step=%d model=%s base_url=%s history_len=%d", step_num, model, base_url, len(messages))

    import asyncio
    client = OpenAI(api_key=api_key, base_url=base_url)
    publish_sync({"type": MODEL_START, "model": model})

    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    tc_acc: dict[int, dict[str, str]] = {}
    chunks_seen = 0
    text_chunks_seen = 0
    t_start = time.monotonic()

    from agent.llm.messages import obj_field

    # Run the blocking stream in a thread so the event loop stays free.
    def _run_stream() -> list[tuple]:
        """Collect (reasoning, text, tcs) tuples from the stream."""
        collected: list[tuple] = []
        stream = client.chat.completions.create(  # type: ignore[call-overload]
            model=model_name,
            messages=build_openai(messages, model),  # type: ignore[arg-type]
            tools=get_tool_specs(),  # type: ignore[arg-type]
            stream=True,
        )
        for chunk in stream:
            choices = obj_field(chunk, "choices", []) or []
            if not choices:
                continue
            delta = obj_field(choices[0], "delta")
            reasoning = obj_field(delta, "reasoning_content") or ""
            text = obj_field(delta, "content") or ""
            tcs = obj_field(delta, "tool_calls", []) or []
            collected.append((reasoning, text, tcs))
        return collected

    try:
        collected = await asyncio.to_thread(_run_stream)
    except Exception:
        log.exception("model stream failed step=%d model=%s", step_num, model)
        publish_sync({"type": MODEL_END, "model": model, "error": True})
        raise

    # Process collected chunks
    for entry in collected:
        reasoning, text, tcs = entry[0], entry[1], entry[2]
        chunks_seen += 1
        if reasoning:
            reasoning_parts.append(str(reasoning))
        if text:
            text_chunks_seen += 1
            content_parts.append(str(text))
            if emit_text:
                publish_sync({"type": TEXT_DELTA, "text": str(text)})
        for tcc in tcs:
            idx = obj_field(tcc, "index", 0) or 0
            slot = tc_acc.setdefault(idx, {"id": "", "name": "", "args": ""})
            call_id = obj_field(tcc, "id")
            if call_id:
                slot["id"] = str(call_id)
            fn = obj_field(tcc, "function")
            name = obj_field(fn, "name")
            if name:
                slot["name"] = str(name)
            args = obj_field(fn, "arguments")
            if args:
                slot["args"] += str(args)

    return _finalise(model, step_num, t_start, chunks_seen, text_chunks_seen,
                     content_parts, tc_acc, "".join(reasoning_parts))


def _finalise(
    model: str,
    step_num: int,
    t_start: float,
    chunks_seen: int,
    text_chunks_seen: int,
    content_parts: list[str],
    tc_acc: dict[int, dict[str, str]],
    reasoning_buf: str,
) -> dict[str, Any]:
    elapsed_ms = int((time.monotonic() - t_start) * 1000)
    text_buf = "".join(content_parts)
    publish_sync({"type": MODEL_END, "model": model})

    log.info(
        "step=%d model=%s done elapsed_ms=%d chunks=%d text_chunks=%d "
        "text_len=%d reasoning_len=%d tool_calls=%d",
        step_num, model, elapsed_ms, chunks_seen, text_chunks_seen,
        len(text_buf), len(reasoning_buf), len(tc_acc),
    )
    if text_buf:
        log.info("  text_preview: %s", preview(text_buf))

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
            log.info("  tool_call name=%s id=%s args=%s",
                     calls[-1]["name"], calls[-1]["id"], preview(args))
        return {"kind": "tools", "calls": calls, "text": text_buf, "reasoning_content": reasoning_buf}

    return {"kind": "final", "text": text_buf}
