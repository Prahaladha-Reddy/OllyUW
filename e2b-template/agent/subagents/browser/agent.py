"""
Browser subagent — BrowserOS MCP + MiMo v2.5 vision.

Entry point: run_browser_task()
Called by:   agent/subagents/runner.py when toolset contains "browser"

BrowserOS must be open and its MCP server enabled.
Configure via env: BROWSEROS_MCP_URL (default http://localhost:9000/mcp)

MiMo auth note:
  MiMo authenticates via the "api-key" request header, not the standard
  Authorization: Bearer header. The OpenAI SDK requires a non-empty api_key
  parameter to construct the client — we pass the literal string "not-used"
  there and put the real key in default_headers instead.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from openai import OpenAI

from agent.llm.providers import normalise_base_url, resolve
from agent.log import log

from .mcp import URL as BROWSEROS_URL
from .mcp import MCPClient, to_openai_tools

# ── skill system ────────────────────────────────────────────────────────────────
# Uses the same catalog as the main agent (agent/skills/catalog/).
# Tier 1: skill names + descriptions injected into system prompt.
# Tier 2: full SKILL.md loaded on demand when agent calls use_skill(name).

def _skills_index() -> str:
    """Return the concise skill list for the system prompt (name + description)."""
    try:
        from agent.skills.loader import list_skills_index
        return list_skills_index()
    except Exception as exc:
        log.debug("skills index unavailable: %s", exc)
        return ""


def _load_skill(name: str) -> str:
    """Load full skill body by name. Returns error string if not found."""
    try:
        from agent.skills.loader import load_skill
        body = load_skill(name)
        if body:
            log.info("browser_agent use_skill=%s (%d chars)", name, len(body))
            return body
        return f"Skill '{name}' not found. Available skills are listed in your system prompt."
    except Exception as exc:
        return f"Failed to load skill '{name}': {exc}"


# Synthetic use_skill tool definition — added to every browser agent's tool list
_USE_SKILL_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "use_skill",
        "description": (
            "Load the full instructions for a named skill. "
            "Skills are listed in your system prompt with names and descriptions. "
            "Call this before starting any task where a relevant skill is available — "
            "it gives you verified playbooks, code patterns, and failure modes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Exact skill name from the skills list (e.g. 'linkedin-jobs-apply')",
                }
            },
            "required": ["name"],
        },
    },
}


# ── MiMo client factory ────────────────────────────────────────────────────────

VISION_MODEL = "mimo-v2.5"   # Omni series — the only MiMo variant with image input


def _make_mimo_client() -> tuple[OpenAI, str]:
    """
    Return (OpenAI client, model_name) configured for MiMo vision.

    MiMo uses header-based auth ("api-key") rather than the standard Bearer
    token. We satisfy the OpenAI SDK's required api_key parameter with the
    string "not-used"; the real key goes in default_headers.

    Model is pinned to mimo-v2.5 (Omni / vision-capable). mimo-v2.5-pro is
    text-only and will 404 on any message containing image_url content.
    """
    base_url, api_key, _ = resolve("mimo")   # discard model_name — vision model is fixed
    client = OpenAI(
        api_key         = "not-used",
        base_url        = normalise_base_url(base_url),
        default_headers = {"api-key": api_key},
    )
    return client, VISION_MODEL


# ── system prompt builder ──────────────────────────────────────────────────────

def _build_system_prompt(return_schema: dict | None, window_id: int | None = None) -> str:
    window_rule = (
        f"WINDOW ISOLATION: You are running in browser window {window_id}. "
        f"Always pass windowId={window_id} when calling new_page. "
        "Never touch pages outside your window."
        if window_id is not None else ""
    )

    skills_index = _skills_index()

    parts = [
        "You are a browser automation agent with full control of a real web browser.",
        "",
        "PAGE ID RULE: list_pages returns '3. Title (tab 99999)' — page ID is 3, NOT 99999.",
    ]

    if window_rule:
        parts += ["", window_rule]

    if skills_index:
        parts += [
            "",
            "## Available Skills",
            "Call use_skill(name) to load full instructions for a skill before starting a task.",
            "Do this at your FIRST turn if a relevant skill exists — don't browse blindly.",
            "",
            skills_index,
        ]

    parts += [
        "",
        "When take_screenshot returns, the image appears in the very next message.",
        "When you have the final answer, respond with plain text only (no tool call).",
    ]

    if return_schema:
        parts += [
            "",
            "Return your final answer as JSON matching this schema:",
            json.dumps(return_schema, indent=2),
        ]

    return "\n".join(parts)


# ── agent loop ─────────────────────────────────────────────────────────────────

async def _run_loop(
    mcp:          MCPClient,
    openai_tools: list[dict],
    messages:     list[dict],
    client:       OpenAI,
    model_name:   str,
    max_turns:    int,
) -> dict[str, Any]:
    """Core agent loop. Returns a result dict."""
    turns         = 0
    tool_count    = 0
    screenshot_ct = 0
    last_call_at  = 0.0
    start         = time.monotonic()

    for _ in range(max_turns):
        await _rate_limit(last_call_at)

        try:
            resp = await asyncio.to_thread(
                client.chat.completions.create,
                model    = model_name,
                messages = messages,        # type: ignore[arg-type]
                tools    = openai_tools,    # type: ignore[arg-type]
                timeout  = 120,
            )
        except Exception as exc:
            if "429" in str(exc):
                log.warning("browser_agent rate-limited, sleeping 10s")
                await asyncio.sleep(10)
                continue
            raise

        last_call_at = time.monotonic()
        turns += 1
        msg = resp.choices[0].message

        if msg.content:
            log.info("browser_agent thinking: %s", str(msg.content)[:200])

        if not msg.tool_calls:
            return _success(msg.content or "", turns, tool_count, start)

        messages.append(_assistant_message(msg))

        for tc in msg.tool_calls:
            tool_count += 1
            name = tc.function.name        # type: ignore[union-attr]
            args = _parse_args(tc.function.arguments)  # type: ignore[union-attr]
            log.info("browser_agent tool[%d] %s %s", tool_count, name, str(args)[:120])

            # Skill load — inject full skill body as tool result
            if name == "use_skill":
                skill_body = _load_skill(args.get("name", ""))
                _append_tool_result(messages, tc.id, name, skill_body)
                continue

            if _is_screenshot(name):
                screenshot_ct += 1
                if screenshot_ct > 3:
                    _append_tool_result(messages, tc.id, name,
                                        "Screenshot limit reached (max 3). Use take_snapshot or evaluate_script instead.")
                    continue

            result = await mcp.call(name, args)
            log.info("browser_agent result: %s", result.text[:200])
            _append_tool_result(messages, tc.id, name, result.text)

            if result.image_b64:
                _inject_image(messages, name, result.image_b64)

    return {
        "agent": "browser", "success": False,
        "error": f"reached max_turns={max_turns}",
        "turns": turns, "tool_calls": tool_count,
        "elapsed": round(time.monotonic() - start, 1),
    }


# ── message helpers ────────────────────────────────────────────────────────────

def _assistant_message(msg: Any) -> dict:
    return {
        "role": "assistant",
        "content": msg.content or "",
        "tool_calls": [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}  # type: ignore[union-attr]
            for tc in msg.tool_calls
        ],
    }


def _append_tool_result(messages: list, call_id: str, name: str, text: str) -> None:
    messages.append({"role": "tool", "content": text, "tool_call_id": call_id, "name": name})


def _inject_image(messages: list, tool_name: str, image_b64: str) -> None:
    """Inject a screenshot as a user message so MiMo can see it.
    Images cannot live inside tool messages (OpenAI spec) — they must be user messages."""
    messages.append({
        "role": "user",
        "content": [
            {"type": "text",      "text": f"[Screenshot from {tool_name}]"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
        ],
    })


def _parse_args(raw: str | None) -> dict:
    try:
        return json.loads(raw or "{}") if raw else {}
    except json.JSONDecodeError:
        return {}


def _is_screenshot(name: str) -> bool:
    return name in {"take_screenshot", "save_screenshot"}


async def _rate_limit(last_call_at: float, min_interval: float = 1.0) -> None:
    gap = min_interval - (time.monotonic() - last_call_at)
    if gap > 0:
        await asyncio.sleep(gap)


def _success(output: str, turns: int, tool_count: int, start: float) -> dict:
    return {
        "agent": "browser", "success": True, "data": output,
        "turns": turns, "tool_calls": tool_count,
        "elapsed": round(time.monotonic() - start, 1),
    }


# ── public entry point ─────────────────────────────────────────────────────────

async def run_browser_task(
    goal:          str,
    context:       dict[str, Any],
    return_schema: dict | None,
    defn:          dict,
) -> dict[str, Any]:
    """
    Run a browser task. Called by subagents/runner.py.

    Args:
        goal:          What the agent should accomplish.
        context:       Extra context from the parent agent.
        return_schema: If set, agent must return JSON matching this schema.
        defn:          Task definition dict (max_turns, model overrides, etc.)
    """
    async with MCPClient() as mcp:
        mcp_tools = await mcp.list_tools()
        if mcp_tools is None:
            return {
                "agent": "browser", "goal": goal, "success": False,
                "error": f"BrowserOS MCP not reachable at {BROWSEROS_URL}. "
                         "Open BrowserOS and enable its MCP server.",
            }

        log.info("browser_agent start goal=%s tools=%d", goal[:80], len(mcp_tools))

        client, model_name = _make_mimo_client()
        # BrowserOS tools + use_skill synthetic tool
        openai_tools  = to_openai_tools(mcp_tools) + [_USE_SKILL_TOOL]
        system_prompt = _build_system_prompt(return_schema, mcp.window_id)
        max_turns          = int(defn.get("max_turns", 60))

        user_content = f"TASK: {goal}"
        if context:
            user_content = f"CONTEXT: {json.dumps(context)}\n\n{user_content}"

        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ]

        result = await _run_loop(mcp, openai_tools, messages, client, model_name, max_turns)
        result["goal"] = goal
        return result
