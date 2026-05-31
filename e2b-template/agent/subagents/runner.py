"""
Hermes-style generic subagent delegation.

delegate(tasks=[
    {"goal": "Research X", "context": "...", "toolsets": ["web"]},
    {"goal": "Analyse this CSV", "context": "file at workspace/data.csv", "toolsets": ["file", "shell"]},
])

Toolsets (choose any combination):
  "web"     → web_search, web_research
  "file"    → read_file, write_file, apply_unified_patch, find_files,
               search_files, get_file_outline, list_directory, move_file, delete_file
  "shell"   → run_shell
  "all"     → everything above combined
  "browser" → special: BrowserOS MCP + MiMo vision model

Subagents are stateless. They have NO parent history. Pass ALL needed context explicitly.
Blocked for subagents: delegate (no recursion), update_memory, update_soul (no side effects).
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from agent.config import AGENT_DEPTH, MAX_DEPTH
from agent.log import log


# ── toolset → tool specs ──────────────────────────────────────────────────────

def _build_toolset_specs(toolsets: list[str]) -> list[dict]:
    """Return the OpenAI tool spec list for the given toolset names."""
    from agent.tools import CORE_TOOL_SPECS
    from agent.tools.registry import get_registry

    # Index core specs by name for quick lookup
    core_by_name = {s["function"]["name"]: s for s in CORE_TOOL_SPECS}

    # Toolset → tool name lists
    _FILE_TOOLS  = ["read_file", "write_file", "apply_unified_patch",
                    "find_files", "search_files", "get_file_outline",
                    "list_directory", "move_file", "delete_file"]
    _SHELL_TOOLS = ["run_shell"]
    _WEB_TOOLS   = ["web_search", "web_research"]
    _TODO_TOOLS  = ["todo"]

    wanted: set[str] = set()
    for ts in toolsets:
        match ts.lower():
            case "file":
                wanted.update(_FILE_TOOLS)
            case "shell":
                wanted.update(_SHELL_TOOLS)
            case "web":
                wanted.update(_WEB_TOOLS)
            case "todo":
                wanted.update(_TODO_TOOLS)
            case "all":
                wanted.update(_FILE_TOOLS + _SHELL_TOOLS + _WEB_TOOLS + _TODO_TOOLS)
            case "browser":
                pass  # handled separately

    specs: list[dict] = []
    registry = get_registry()

    for name in wanted:
        if name in core_by_name:
            specs.append(core_by_name[name])
        else:
            # Try deferred registry (web_search, web_research live there)
            schema = registry.describe(name)
            if schema:
                specs.append(schema)

    return specs


# ── tool dispatch for subagents (no delegate, no memory writes) ───────────────

async def _dispatch_subagent_tool(name: str, args: dict) -> str:
    """Dispatch a tool call inside a subagent. Blocks delegate + memory mutations."""
    _BLOCKED = {"delegate", "update_memory", "update_soul", "append_memory",
                "tool_search", "tool_describe", "tool_call"}
    if name in _BLOCKED:
        return f"tool '{name}' is not available in subagents."

    from agent.tools.file_ops import (
        apply_unified_patch, delete_file, find_files, get_file_outline,
        list_directory, move_file, read_file, search_files, write_file,
    )
    from agent.tools.shell import run_shell
    from agent.tools.todo import todo

    match name:
        case "read_file":           return await asyncio.to_thread(read_file, **args)
        case "write_file":          return await asyncio.to_thread(write_file, **args)
        case "apply_unified_patch": return await asyncio.to_thread(apply_unified_patch, **args)
        case "run_shell":           return await run_shell(**args)
        case "todo":                return await asyncio.to_thread(todo, **args)
        case "find_files":          return await asyncio.to_thread(find_files, **args)
        case "search_files":        return await asyncio.to_thread(search_files, **args)
        case "get_file_outline":    return await asyncio.to_thread(get_file_outline, **args)
        case "list_directory":      return await asyncio.to_thread(list_directory, **args)
        case "move_file":           return await asyncio.to_thread(move_file, **args)
        case "delete_file":         return await asyncio.to_thread(delete_file, **args)
        case "web_search":
            from agent.web.parallel_client import web_search as _ws
            return await asyncio.to_thread(_ws, **args)
        case "web_research":
            from agent.web.parallel_client import web_research as _wr
            return await asyncio.to_thread(_wr, **args)
        case _:
            return f"unknown tool '{name}' for subagent"


# ── main entry point ──────────────────────────────────────────────────────────

async def run_tasks(tasks: list[dict[str, Any]]) -> str:
    if AGENT_DEPTH >= MAX_DEPTH:
        return json.dumps({
            "error": f"max delegation depth ({MAX_DEPTH}) reached — subagents cannot spawn subagents"
        })
    if not tasks:
        return json.dumps({"error": "no tasks provided to delegate"})

    sequential = [t for t in tasks if t.get("sequential")]
    parallel   = [t for t in tasks if not t.get("sequential")]

    # Assign stable IDs before launching so events are identifiable immediately.
    for i, t in enumerate(parallel):
        t.setdefault("_sa_id", f"sa-{i}")
    for i, t in enumerate(sequential):
        t.setdefault("_sa_id", f"sa-seq-{i}")

    results: list[Any] = []

    if parallel:
        parallel_results = await asyncio.gather(
            *[_run_one(t) for t in parallel],
            return_exceptions=True,
        )
        for task, result in zip(parallel, parallel_results):
            if isinstance(result, Exception):
                results.append({"goal": task.get("goal"), "success": False, "error": str(result)})
            else:
                results.append(result)

    prev_output: Any = None
    for task in sequential:
        if prev_output is not None:
            ctx = str(task.get("context") or "")
            task = {**task, "context": f"{ctx}\n\nPrevious result:\n{prev_output}".strip()}
        result = await _run_one(task)
        prev_output = result.get("output", "")
        results.append(result)

    if len(results) == 1:
        return json.dumps(results[0], indent=2, ensure_ascii=False)
    return json.dumps(results, indent=2, ensure_ascii=False)


async def _run_one(task: dict[str, Any]) -> dict[str, Any]:
    goal      = str(task.get("goal", ""))
    context   = str(task.get("context") or "")
    toolsets  = list(task.get("toolsets") or ["file", "shell", "web"])
    max_turns = int(task.get("max_turns") or 30)
    sa_id     = str(task.get("_sa_id", f"sa-{id(task)}"))
    sa_label  = f"{sa_id} [{','.join(toolsets)}]"

    log.info("subagent start id=%s toolsets=%s goal=%s", sa_id, toolsets, goal[:80])
    _pub_start(sa_id, sa_label, goal, toolsets)

    # Browser is a special subagent (different model + BrowserOS MCP)
    if "browser" in toolsets:
        from agent.subagents.browser.agent import run_browser_task
        result = await run_browser_task(goal, {"context": context}, None, {
            "model": "mimo", "max_turns": max_turns,
        })
        _pub_done(sa_id, sa_label, result.get("success", False),
                  str(result.get("error") or result.get("data") or "")[:300])
        log.info("subagent done id=%s browser success=%s", sa_id, result.get("success"))
        return result

    tool_specs = _build_toolset_specs(toolsets)
    if not tool_specs:
        err = f"no tools available for toolsets {toolsets}"
        _pub_done(sa_id, sa_label, False, err)
        return {"goal": goal, "success": False, "error": err}

    try:
        output = await _run_agent_loop(goal, context, tool_specs, max_turns, sa_id, sa_label)
        _pub_done(sa_id, sa_label, True, output[:300])
        log.info("subagent done id=%s output_len=%d", sa_id, len(output))
        return {"goal": goal, "success": True, "output": output}
    except Exception as exc:
        log.exception("subagent error id=%s", sa_id)
        _pub_done(sa_id, sa_label, False, str(exc))
        return {"goal": goal, "success": False, "error": str(exc)}


# ── event helpers ─────────────────────────────────────────────────────────────

def _pub_start(sa_id: str, label: str, goal: str, toolsets: list[str]) -> None:
    try:
        from agent.events import SUBAGENT_START
        from agent.redis_io import publish_sync
        publish_sync({
            "type":     SUBAGENT_START,
            "subagent_id":    sa_id,
            "subagent_label": label,
            "goal":     goal,
            "toolsets": toolsets,
        })
    except Exception:
        pass


def _pub_done(sa_id: str, label: str, success: bool, summary: str) -> None:
    try:
        from agent.events import SUBAGENT_DONE
        from agent.redis_io import publish_sync
        publish_sync({
            "type":     SUBAGENT_DONE,
            "subagent_id":    sa_id,
            "subagent_label": label,
            "success":  success,
            "summary":  summary,
        })
    except Exception:
        pass


def _pub_tool_call(sa_id: str, label: str, call_id: str, name: str, args: dict) -> None:
    try:
        from agent.events import TOOL_CALL
        from agent.redis_io import publish_sync
        wire_args = args if len(str(args)) < 500 else {"_truncated": str(args)[:500]}
        publish_sync({
            "type":           TOOL_CALL,
            "id":             call_id,
            "tool":           name,
            "args":           wire_args,
            "subagent_id":    sa_id,
            "subagent_label": label,
        })
    except Exception:
        pass


def _pub_tool_result(sa_id: str, label: str, call_id: str, name: str, ok: bool, output: str) -> None:
    try:
        from agent.events import TOOL_RESULT
        from agent.redis_io import publish_sync
        wire_out = output if len(output) < 1000 else output[:1000] + f"...<+{len(output)-1000}b>"
        publish_sync({
            "type":           TOOL_RESULT,
            "id":             call_id,
            "tool":           name,
            "ok":             ok,
            "output":         wire_out,
            "subagent_id":    sa_id,
            "subagent_label": label,
        })
    except Exception:
        pass


async def _run_agent_loop(
    goal: str,
    context: str,
    tool_specs: list[dict],
    max_turns: int,
    sa_id: str = "",
    sa_label: str = "",
) -> str:
    """Run a mini agent loop with an isolated context and the given tool specs."""
    from agent.config import DEFAULT_MODEL
    from agent.llm.providers import normalise_base_url, resolve
    from agent.llm.messages import obj_field
    from agent.observability.langfuse_setup import openai_module

    base_url, api_key, model_name = resolve(DEFAULT_MODEL)
    base_url = normalise_base_url(base_url)
    OpenAI = openai_module().OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)

    system = (
        "You are a focused subagent. Complete the given task using the tools available.\n\n"
        "PARALLELISM: You MUST call multiple independent tools in a SINGLE response whenever possible. "
        "If you need to search for 3 things, call web_search 3 times in the same response — not one at a time. "
        "Never make a tool call sequentially when you could make it in parallel.\n\n"
        "Return a clear, concise summary of what you accomplished and any important findings. "
        "Do NOT ask clarifying questions — work with what you have."
    )
    user_msg = f"TASK: {goal}"
    if context:
        user_msg = f"CONTEXT:\n{context}\n\nTASK: {goal}"

    messages: list[dict] = [{"role": "user", "content": user_msg}]

    import json as _json

    for turn_idx in range(max_turns):
        def _call_model() -> list[tuple]:
            stream = client.chat.completions.create(  # type: ignore[call-overload]
                model=model_name,
                messages=[{"role": "system", "content": system}, *messages],  # type: ignore[arg-type]
                tools=tool_specs,  # type: ignore[arg-type]
                stream=True,
            )
            collected: list[tuple] = []
            tc_acc: dict[int, dict] = {}
            text_parts: list[str] = []
            for chunk in stream:
                choices = obj_field(chunk, "choices", []) or []
                if not choices:
                    continue
                delta = obj_field(choices[0], "delta")
                text = obj_field(delta, "content") or ""
                if text:
                    text_parts.append(str(text))
                for tcc in (obj_field(delta, "tool_calls", []) or []):
                    idx = obj_field(tcc, "index", 0) or 0
                    slot = tc_acc.setdefault(idx, {"id": "", "name": "", "args": ""})
                    cid = obj_field(tcc, "id")
                    if cid:
                        slot["id"] = str(cid)
                    fn = obj_field(tcc, "function")
                    nm = obj_field(fn, "name")
                    if nm:
                        slot["name"] = str(nm)
                    ar = obj_field(fn, "arguments")
                    if ar:
                        slot["args"] += str(ar)
            return [("text", "".join(text_parts)), ("tc_acc", tc_acc)]

        collected = await asyncio.to_thread(_call_model)
        text = next((v for k, v in collected if k == "text"), "")
        tc_acc = next((v for k, v in collected if k == "tc_acc"), {})

        # Parse tool calls
        calls = []
        for idx in sorted(tc_acc):
            slot = tc_acc[idx]
            try:
                args = _json.loads(slot["args"]) if slot["args"] else {}
            except _json.JSONDecodeError:
                args = {}
            calls.append({"id": slot["id"], "name": slot["name"], "args": args})

        if not calls:
            # Final response
            return text or "(no output)"

        messages.append({
            "role": "assistant",
            "content": text or "",
            "tool_calls": [
                {"id": c["id"], "type": "function",
                 "function": {"name": c["name"], "arguments": _json.dumps(c["args"])}}
                for c in calls
            ],
        })

        # Publish tool_call events for each call in this step
        for c in calls:
            _pub_tool_call(sa_id, sa_label, c["id"], c["name"],
                           c["args"] if isinstance(c["args"], dict) else {})

        # Execute all tool calls in parallel
        tool_results = await asyncio.gather(*[
            _dispatch_subagent_tool(c["name"], c["args"] if isinstance(c["args"], dict) else {})
            for c in calls
        ], return_exceptions=True)

        for call, result in zip(calls, tool_results):
            ok = not isinstance(result, Exception)
            content = str(result) if ok else f"ERROR: {result}"
            _pub_tool_result(sa_id, sa_label, call["id"], call["name"], ok, content)
            messages.append({
                "role": "tool",
                "content": content,
                "tool_call_id": call["id"],
                "name": call["name"],
            })

    return f"(reached max_turns={max_turns})"
