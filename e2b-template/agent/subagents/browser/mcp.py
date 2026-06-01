"""BrowserOS MCP client — all HTTP communication with the BrowserOS MCP server.

Window isolation:
  Each MCPClient creates its own browser window on __aenter__ and destroys it
  on __aexit__. This means parallel browser subagents never share tabs — each
  operates in a completely separate window with its own page ID space.

  Two interceptions happen transparently in call():
    • new_page  → windowId is auto-injected so new tabs land in this window
    • list_pages → result is filtered to only show pages in this window
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import aiohttp

from agent.log import log

URL = os.getenv("BROWSEROS_MCP_URL", "http://localhost:9000/mcp")

_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
_SCREENSHOT_TOOLS = {"take_screenshot", "save_screenshot"}
_AUTO_CONTEXT_SEP = "--- Additional context (auto-included) ---"


class ToolResult:
    def __init__(self, text: str, image_b64: str | None = None):
        self.text      = text
        self.image_b64 = image_b64


class MCPClient:
    """Async BrowserOS MCP client with per-instance window isolation.

    Usage:
        async with MCPClient() as mcp:
            tools = await mcp.list_tools()
            result = await mcp.call("navigate_page", {"page": 1, "url": "..."})

    Each context-manager enter creates a dedicated browser window.
    Each context-manager exit closes that window and all its tabs.
    """

    def __init__(self) -> None:
        self._session:     aiohttp.ClientSession | None = None
        self._initialized: bool = False
        self.window_id:    int | None = None   # set after _create_window()

    # ── MCP protocol ───────────────────────────────────────────────────────────

    async def _init_handshake(self) -> None:
        if self._initialized:
            return
        await self._post({
            "jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "e2b-browser-agent", "version": "1.0"},
            },
        }, timeout=5)
        await self._post(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            timeout=5,
        )
        self._initialized = True

    async def _post(self, payload: dict, timeout: int = 30) -> dict:
        assert self._session is not None, "MCPClient must be used as async context manager"
        try:
            async with self._session.post(
                URL, json=payload, headers=_HEADERS,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                content_type = resp.headers.get("Content-Type", "")
                body = await resp.text()

                if "text/event-stream" in content_type:
                    for line in body.splitlines():
                        if line.startswith("data:"):
                            return json.loads(line[5:].strip())
                    return {}

                return json.loads(body) if body.strip() else {}

        except Exception as exc:
            log.debug("BrowserOS mcp_post method=%s err=%s", payload.get("method"), exc)
            return {}

    # ── window management ──────────────────────────────────────────────────────

    async def _create_window(self) -> None:
        """Create a dedicated browser window for this agent instance."""
        await self._init_handshake()

        # Snapshot window IDs before creating so we can detect the new one
        before = await self._list_window_ids()

        await self._post({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "create_window", "arguments": {}},
        }, timeout=10)

        after = await self._list_window_ids()
        new_ids = after - before

        if new_ids:
            self.window_id = max(new_ids)
        elif after:
            self.window_id = max(after)   # fallback: use highest known window

        log.info("browser_agent window_id=%s", self.window_id)

    async def _list_window_ids(self) -> set[int]:
        """Return the set of all current browser window IDs."""
        data = await self._post({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "list_windows", "arguments": {}},
        }, timeout=5)

        ids: set[int] = set()
        content = data.get("result", {}).get("content", [])

        for item in content:
            text = item.get("text", "")

            # Try JSON first: {"windows": [{"windowId": 123, ...}, ...]}
            try:
                parsed = json.loads(text)
                for w in parsed.get("windows", []):
                    if isinstance(w.get("windowId"), int):
                        ids.add(w["windowId"])
                if ids:
                    return ids
            except (json.JSONDecodeError, TypeError):
                pass

            # Fallback: extract any large integer that looks like a windowId
            # BrowserOS window IDs are typically 10-digit Chrome tab/window IDs
            for match in re.finditer(r'\b(1\d{9})\b', text):
                ids.add(int(match.group(1)))

        return ids

    async def _close_window(self) -> None:
        if self.window_id is None:
            return
        await self._post({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "close_window", "arguments": {"windowId": self.window_id}},
        }, timeout=5)
        log.info("browser_agent window_id=%s closed", self.window_id)

    # ── public API ─────────────────────────────────────────────────────────────

    async def list_tools(self) -> list[dict] | None:
        """Return raw MCP tool list, or None if BrowserOS is unreachable."""
        data = await self._post(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            timeout=5,
        )
        tools = data.get("result", {}).get("tools")
        return tools  # None if key missing → caller treats as unreachable

    async def call(self, name: str, args: dict) -> ToolResult:
        """Execute one BrowserOS tool with automatic window isolation."""
        await self._init_handshake()

        args = _apply_window_isolation(name, args, self.window_id)
        timeout = 60 if name in _SCREENSHOT_TOOLS else 30

        data = await self._post({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": args},
        }, timeout=timeout)

        result = _parse_tool_result(data)

        # list_pages filtering: isolation is enforced via new_page windowId injection,
        # so no post-processing needed here.

        return result

    # ── context manager ────────────────────────────────────────────────────────

    async def __aenter__(self) -> "MCPClient":
        self._session = aiohttp.ClientSession()
        await self._create_window()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self._close_window()
        if self._session:
            await self._session.close()
            self._session = None


# ── isolation helpers ──────────────────────────────────────────────────────────

def _apply_window_isolation(name: str, args: dict, window_id: int | None) -> dict:
    """Inject windowId into new_page so tabs land in this agent's window."""
    if name == "new_page" and window_id is not None and "windowId" not in args:
        return {**args, "windowId": window_id}
    return args


# ── schema helpers ─────────────────────────────────────────────────────────────

def to_openai_tools(mcp_tools: list[dict]) -> list[dict]:
    """Convert BrowserOS MCP tool list to OpenAI function-calling format."""
    result = []
    for tool in mcp_tools:
        schema = dict(tool.get("inputSchema") or {"type": "object", "properties": {}})
        schema.pop("$schema", None)
        result.append({"type": "function", "function": {
            "name":        tool["name"],
            "description": tool.get("description", ""),
            "parameters":  schema,
        }})
    return result


def _parse_tool_result(data: dict) -> ToolResult:
    if data.get("error"):
        err = data["error"]
        return ToolResult(f"MCP error: {err.get('message', err)}")

    content = data.get("result", {}).get("content", [])
    if not content:
        return ToolResult(json.dumps(data.get("result", {})))

    texts:   list[str] = []
    img_b64: str | None = None

    for item in content:
        if item.get("type") == "image":
            img_b64 = item.get("data")
        else:
            texts.append(str(item.get("text", json.dumps(item))))

    text = "\n".join(texts) if texts else ("[image]" if img_b64 else "{}")

    if _AUTO_CONTEXT_SEP in text:
        text = text.split(_AUTO_CONTEXT_SEP)[0].strip()

    return ToolResult(text, img_b64)
