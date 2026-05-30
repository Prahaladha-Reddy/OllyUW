"""
Generic subagent runner.

The delegate tool calls run_tasks(tasks) which:
1. Loads the subagent definition from subagents/definitions/<name>.yaml
2. Builds an isolated context for each task (goal + selective context only)
3. Runs all tasks in parallel via asyncio.gather (unless sequential=True)
4. Returns structured results back to the parent agent

Depth=1 is enforced: subagents run with AGENT_DEPTH=1 and cannot call delegate.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import yaml

from agent.config import AGENT_DEPTH, MAX_DEPTH
from agent.log import log

_DEFINITIONS_DIR = Path(__file__).parent / "definitions"


async def run_tasks(tasks: list[dict[str, Any]]) -> str:
    """Entry point from the delegate tool. Returns a JSON string of results."""
    if AGENT_DEPTH >= MAX_DEPTH:
        return json.dumps({
            "error": f"delegation depth limit reached (max={MAX_DEPTH}). Subagents cannot spawn further subagents."
        })

    if not tasks:
        return json.dumps({"error": "no tasks provided"})

    # Split sequential vs parallel
    sequential: list[dict] = [t for t in tasks if t.get("sequential")]
    parallel:   list[dict] = [t for t in tasks if not t.get("sequential")]

    results: list[Any] = []

    # Run parallel tasks together
    if parallel:
        parallel_results = await asyncio.gather(
            *[_run_one(task) for task in parallel],
            return_exceptions=True,
        )
        for task, result in zip(parallel, parallel_results):
            if isinstance(result, Exception):
                results.append({"agent": task.get("agent"), "goal": task.get("goal"),
                                 "success": False, "error": str(result)})
            else:
                results.append(result)

    # Run sequential tasks one by one
    prev_result: Any = None
    for task in sequential:
        if prev_result is not None:
            # Inject previous result into context so sequential tasks can chain
            ctx = dict(task.get("context") or {})
            ctx["_previous_result"] = prev_result
            task = {**task, "context": ctx}
        result = await _run_one(task)
        prev_result = result.get("data") if isinstance(result, dict) else result
        results.append(result)

    if len(results) == 1:
        return json.dumps(results[0], indent=2, ensure_ascii=False)
    return json.dumps(results, indent=2, ensure_ascii=False)


async def _run_one(task: dict[str, Any]) -> dict[str, Any]:
    agent_type = task.get("agent", "")
    goal       = task.get("goal", "")
    context    = task.get("context") or {}
    return_schema = task.get("return_schema")

    log.info("subagent start type=%s goal=%s", agent_type, goal[:80])

    defn = _load_definition(agent_type)
    if defn is None:
        return {
            "agent": agent_type, "goal": goal, "success": False,
            "error": f"unknown agent type: {agent_type!r}. "
                     f"Available: {_list_definitions()}",
        }

    tool_source = defn.get("tool_source", "builtin")

    try:
        if tool_source == "mcp" and agent_type == "browser":
            from agent.subagents.browser.agent import run_browser_task
            result = await run_browser_task(goal, context, return_schema, defn)
        elif tool_source == "composio":
            result = await _run_composio_task(goal, context, return_schema, defn)
        else:
            result = await _run_builtin_task(goal, context, return_schema, defn)

        log.info("subagent done type=%s success=%s", agent_type, result.get("success"))
        return result

    except Exception as exc:
        log.exception("subagent error type=%s", agent_type)
        return {"agent": agent_type, "goal": goal, "success": False, "error": str(exc)}


def _load_definition(name: str) -> dict | None:
    path = _DEFINITIONS_DIR / f"{name}.yaml"
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _list_definitions() -> str:
    if not _DEFINITIONS_DIR.exists():
        return "(none)"
    names = [p.stem for p in sorted(_DEFINITIONS_DIR.glob("*.yaml"))]
    return ", ".join(names) if names else "(none)"


async def _run_builtin_task(
    goal: str,
    context: dict,
    return_schema: dict | None,
    defn: dict,
) -> dict[str, Any]:
    """Run a subagent using the standard agent loop with a subset of tools."""
    from agent.config import DEFAULT_MODEL
    from agent.llm.streaming import step as model_step
    from agent.tools import dispatch as tool_dispatch, ALL_TOOL_SPECS

    model = defn.get("model") or DEFAULT_MODEL
    max_turns = int(defn.get("max_turns", 20))
    system_prompt = defn.get("system_prompt", "")

    schema_hint = (
        f"\n\nReturn your answer as JSON matching this schema:\n{json.dumps(return_schema, indent=2)}"
        if return_schema
        else ""
    )
    context_str = json.dumps(context, indent=2) if context else ""
    user_message = (
        f"TASK: {goal}\n"
        + (f"\nCONTEXT:\n{context_str}\n" if context_str else "")
        + schema_hint
    )

    messages: list[dict] = [{"role": "user", "content": user_message}]
    if system_prompt:
        # Prepend as a system message in history (injected by build_openai)
        messages = [{"role": "system_override", "content": system_prompt}, *messages]

    for turn_idx in range(max_turns):
        turn = await model_step(messages, model, turn_idx + 1, emit_text=False)

        if turn["kind"] == "final":
            text = turn.get("text", "")
            # Try to parse JSON if return_schema was given
            if return_schema:
                try:
                    data = json.loads(text)
                    return {"agent": defn.get("name"), "goal": goal, "success": True, "data": data}
                except json.JSONDecodeError:
                    pass
            return {"agent": defn.get("name"), "goal": goal, "success": True, "data": text}

        messages.append({
            "role": "assistant",
            "content": turn.get("text", "") or "",
            "tool_calls": turn["calls"],
        })

        results = await asyncio.gather(*[
            tool_dispatch(call["name"], call["args"] if isinstance(call["args"], dict) else {})
            for call in turn["calls"]
        ], return_exceptions=True)

        for call, result in zip(turn["calls"], results):
            messages.append({
                "role":         "tool",
                "content":      str(result),
                "tool_call_id": call["id"],
                "name":         call["name"],
            })

    return {"agent": defn.get("name"), "goal": goal, "success": False,
            "error": f"reached max_turns={max_turns} without completing"}


async def _run_composio_task(
    goal: str,
    context: dict,
    return_schema: dict | None,
    defn: dict,
) -> dict[str, Any]:
    """Placeholder for Composio-based subagents. Register tools then call builtin runner."""
    tools_list = defn.get("tools", [])
    if not tools_list:
        return {"success": False, "error": "composio subagent has no tools defined"}

    # TODO: Register composio tools into the registry, then run builtin task.
    # For now, return a clear stub message.
    return {
        "success": False,
        "error": "Composio subagent not yet wired. Add composio tool registration to runner.py.",
    }
