from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from agent.config import TOOL_SPECS
from agent.events import MODEL_END, MODEL_START, TEXT_DELTA
from agent.llm.messages import build_openai, obj_field
from agent.llm.providers import normalise_base_url, resolve
from agent.log import log, preview
from agent.observability.langfuse_setup import openai_module
from agent.redis_io import publish


def step(
    messages: list[dict[str, Any]], model: str, step_num: int, emit_text: bool = True,
) -> dict[str, Any]:
    """Run a single model step: send messages, stream the response, return parsed result."""
    base_url, api_key, model_name = resolve(model)
    base_url = normalise_base_url(base_url)

    # Use the Langfuse-aware openai shim when Langfuse is configured;
    # falls back to plain openai otherwise.
    OpenAI = openai_module().OpenAI

    log.info(
        "step=%d model=%s base_url=%s history_len=%d",
        step_num, model, base_url, len(messages),
    )
    if log.isEnabledFor(logging.DEBUG):
        for i, m in enumerate(messages[-6:]):
            log.debug("  history[-%d] role=%s preview=%s",
                      len(messages[-6:]) - i, m.get("role"), preview(m.get("content")))

    client = OpenAI(api_key=api_key, base_url=base_url)
    publish({"type": MODEL_START, "model": model})

    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    tc_acc: dict[int, dict[str, str]] = {}
    chunks_seen = 0
    text_chunks_seen = 0
    t_start = time.monotonic()

    try:
        stream = client.chat.completions.create(
            model=model_name,
            messages=build_openai(messages, model),
            tools=TOOL_SPECS,
            stream=True,
        )
        for chunk in stream:
            chunks_seen += 1
            choices = obj_field(chunk, "choices", []) or []
            if not choices:
                continue
            delta = obj_field(choices[0], "delta")

            reasoning = obj_field(delta, "reasoning_content")
            if reasoning:
                reasoning_parts.append(str(reasoning))

            text = obj_field(delta, "content")
            if text:
                text_chunks_seen += 1
                content_parts.append(str(text))
                if emit_text:
                    publish({"type": TEXT_DELTA, "text": str(text)})

            for tcc in (obj_field(delta, "tool_calls", []) or []):
                idx = obj_field(tcc, "index", 0) or 0
                slot = tc_acc.setdefault(idx, {"id": "", "name": "", "args": ""})
                call_id = obj_field(tcc, "id")
                if call_id:
                    slot["id"] = str(call_id)
                function = obj_field(tcc, "function")
                name = obj_field(function, "name")
                if name:
                    slot["name"] = str(name)
                args = obj_field(function, "arguments")
                if args:
                    slot["args"] = slot["args"] + str(args)
    except Exception:
        log.exception("model stream failed at step=%d model=%s", step_num, model)
        publish({"type": MODEL_END, "model": model, "error": True})
        raise

    return _finalise(model, step_num, t_start, chunks_seen, text_chunks_seen,
                     content_parts, tc_acc, reasoning_buf="".join(reasoning_parts))


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
    publish({"type": MODEL_END, "model": model})

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
                     calls[-1]["name"], calls[-1]["id"], preview(args))
        return {
            "kind": "tools",
            "calls": calls,
            "text": text_buf,
            "reasoning_content": reasoning_buf,
        }

    return {"kind": "final", "text": text_buf}
