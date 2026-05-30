"""
Browser subagent — BrowserOS MCP + MiMo vision model.

BrowserOS must be installed and running inside the E2B sandbox:
  pip install browseros
  browseros start  (starts the MCP server on localhost:7788 by default)

This agent:
1. Connects to the BrowserOS MCP server
2. Gets all browser tool schemas
3. Runs a MiMo vision loop: navigate → screenshot → analyse → act
4. Returns a structured result to the parent agent
"""
from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

from agent.log import log

_BROWSEROS_MCP_URL = "http://localhost:7788"
_SCREENSHOT_WS_URL = "ws://localhost:7788/screencast"


async def run_browser_task(
    goal: str,
    context: dict[str, Any],
    return_schema: dict | None,
    defn: dict,
) -> dict[str, Any]:
    """Run a browser task using BrowserOS MCP + MiMo vision."""
    # Check if BrowserOS MCP is reachable
    mcp_tools = await _get_mcp_tools()
    if mcp_tools is None:
        return {
            "success": False,
            "error": (
                "BrowserOS MCP server is not running. "
                "Install with: pip install browseros  "
                "Start with: browseros start"
            ),
        }

    log.info("browser_agent start goal=%s tools=%d", goal[:80], len(mcp_tools))

    max_turns = int(defn.get("max_turns", 30))
    model = defn.get("model", "mimo")
    system_prompt = defn.get("system_prompt", "")

    schema_hint = (
        f"\n\nReturn your final answer as JSON matching this schema:\n{json.dumps(return_schema, indent=2)}"
        if return_schema
        else ""
    )

    user_message = f"TASK: {goal}{schema_hint}"
    if context:
        user_message = f"CONTEXT: {json.dumps(context)}\n\n{user_message}"

    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]

    from agent.llm.streaming import step as model_step

    for turn_idx in range(max_turns):
        # Capture screenshot and inject as vision context
        screenshot_b64 = await _capture_screenshot()
        if screenshot_b64:
            # Inject screenshot as the most recent visual state
            _inject_screenshot(messages, screenshot_b64)

        turn = await model_step(messages, model, turn_idx + 1, emit_text=False)

        if turn["kind"] == "final":
            text = turn.get("text", "")
            if return_schema:
                try:
                    data = json.loads(text)
                    return {"agent": "browser", "goal": goal, "success": True, "data": data}
                except json.JSONDecodeError:
                    pass
            return {"agent": "browser", "goal": goal, "success": True, "data": text}

        messages.append({
            "role":       "assistant",
            "content":    turn.get("text", "") or "",
            "tool_calls": turn["calls"],
        })

        # Execute each browser tool via MCP
        for call in turn["calls"]:
            result = await _call_mcp_tool(call["name"], call.get("args") or {})

            # RLM: capture screenshot after tool to verify action worked
            after_screenshot = await _capture_screenshot()

            messages.append({
                "role":         "tool",
                "content":      str(result),
                "tool_call_id": call["id"],
                "name":         call["name"],
            })

    return {
        "agent": "browser", "goal": goal, "success": False,
        "error": f"reached max_turns={max_turns}",
    }


async def _get_mcp_tools() -> list[dict] | None:
    """Fetch available tools from BrowserOS MCP server. Returns None if unreachable."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{_BROWSEROS_MCP_URL}/mcp",
                json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                data = await resp.json()
                return data.get("result", {}).get("tools", [])
    except Exception as exc:
        log.debug("BrowserOS MCP not reachable: %s", exc)
        return None


async def _call_mcp_tool(name: str, args: dict) -> str:
    """Execute a BrowserOS MCP tool."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{_BROWSEROS_MCP_URL}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method":  "tools/call",
                    "id":      1,
                    "params":  {"name": name, "arguments": args},
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                result = data.get("result", {})
                content = result.get("content", [])
                if content:
                    return str(content[0].get("text", result))
                return str(result)
    except Exception as exc:
        return f"MCP tool error ({name}): {exc}"


async def _capture_screenshot() -> str | None:
    """Capture current browser screenshot as base64. Returns None on failure."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{_BROWSEROS_MCP_URL}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method":  "tools/call",
                    "id":      1,
                    "params":  {"name": "screenshot", "arguments": {}},
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
                content = data.get("result", {}).get("content", [])
                for item in content:
                    if item.get("type") == "image":
                        return item.get("data")
        return None
    except Exception:
        return None


def _inject_screenshot(messages: list[dict], screenshot_b64: str) -> None:
    """Inject screenshot as vision content into the last user message."""
    # Add a new user message with the screenshot so MiMo can see the current state
    messages.append({
        "role": "user",
        "content": [
            {"type": "text",  "text": "[Current browser state]"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{screenshot_b64}"}},
        ],
    })
