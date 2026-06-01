"""
Browser subagent: MiMo v2.5 (vision) + BrowserOS MCP.

Screenshots are NOT auto-injected. The agent calls take_screenshot
when it needs to see the page. When it does, the image is properly
passed as an image_url content block in a follow-up user message
(OpenAI spec: tool messages must have string content, images go in user messages).
"""
from __future__ import annotations

import sys
sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]
sys.stderr.reconfigure(line_buffering=True)  # type: ignore[union-attr]

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MIMO_API_KEY   = os.environ["MIMI_API_KEY"]
BROWSEROS_URL  = os.getenv("BROWSEROS_MCP_URL", "http://127.0.0.1:9000/mcp")
MIMO_BASE_URL  = "https://api.xiaomimimo.com/v1"
MODEL          = "mimo-v2.5"   # Omni — vision-capable

_MCP_HEADERS  = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
_MIN_INTERVAL = 1.0
_MAX_RETRIES  = 4

_initialized = False


# ── live log ──────────────────────────────────────────────────────────────────

_LOG_FILE: Path | None = None

def set_log_file(path: Path) -> None:
    global _LOG_FILE
    _LOG_FILE = path
    path.parent.mkdir(exist_ok=True)
    path.write_text("", encoding="utf-8")

def log(msg: str) -> None:
    ts   = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if _LOG_FILE:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")


# ── rate limiter ──────────────────────────────────────────────────────────────

class RateLimiter:
    def __init__(self, min_interval: float = _MIN_INTERVAL) -> None:
        self._min_interval = min_interval
        self._last         = 0.0

    def wait(self) -> None:
        gap = self._min_interval - (time.monotonic() - self._last)
        if gap > 0:
            time.sleep(gap)
        self._last = time.monotonic()

_limiter = RateLimiter()


# ── MCP helpers ───────────────────────────────────────────────────────────────

def _mcp_init() -> None:
    global _initialized
    if _initialized:
        return
    try:
        requests.post(BROWSEROS_URL, headers=_MCP_HEADERS, timeout=5, json={
            "jsonrpc": "2.0", "method": "initialize", "id": 0,
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "browser-eval", "version": "1.0"}},
        })
        requests.post(BROWSEROS_URL, headers=_MCP_HEADERS, timeout=5,
                      json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        _initialized = True
    except Exception:
        pass


def _mcp_post(payload: dict, timeout: int = 30) -> dict:
    _mcp_init()
    resp = requests.post(BROWSEROS_URL, json=payload, headers=_MCP_HEADERS, timeout=timeout)
    ct   = resp.headers.get("content-type", "")
    if "text/event-stream" in ct:
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        return {}
    if resp.text.strip():
        return resp.json()
    return {}


def _mcp_tools_list() -> list[dict] | None:
    try:
        data = _mcp_post({"jsonrpc": "2.0", "method": "tools/list", "id": 1}, timeout=5)
        return data.get("result", {}).get("tools") or []
    except Exception as exc:
        log(f"[BrowserOS] not reachable: {exc}")
        return None


class ToolResult:
    """Holds the result of an MCP tool call, separating text from image data."""
    def __init__(self, text: str, image_b64: str | None = None):
        self.text      = text
        self.image_b64 = image_b64   # base64 JPEG, only set for screenshot tools


def _mcp_call(name: str, args: dict) -> ToolResult:
    """Call a BrowserOS MCP tool. Returns ToolResult with text and optional image."""
    # Screenshots on heavy pages can take a while
    timeout = 60 if name in ("take_screenshot", "save_screenshot") else 30
    try:
        data    = _mcp_post({"jsonrpc": "2.0", "method": "tools/call", "id": 1,
                             "params": {"name": name, "arguments": args}}, timeout=timeout)
        if data.get("error"):
            return ToolResult(f"MCP error: {data['error'].get('message', data['error'])}")

        content = data.get("result", {}).get("content", [])
        if not content:
            return ToolResult(json.dumps(data.get("result", {})))

        # Collect all content items — there can be text + image together
        texts:  list[str] = []
        img_b64: str | None = None

        for item in content:
            if item.get("type") == "image":
                img_b64 = item.get("data")   # base64 string from BrowserOS
            else:
                texts.append(str(item.get("text", json.dumps(item))))

        combined = "\n".join(texts) if texts else ("[image]" if img_b64 else "{}")
        # BrowserOS appends "--- Additional context (auto-included) ---" to every
        # tool result. Strip it — the agent calls take_snapshot when it wants the page.
        separator = "--- Additional context (auto-included) ---"
        if separator in combined:
            combined = combined.split(separator)[0].strip()
        return ToolResult(combined, img_b64)

    except Exception as exc:
        return ToolResult(f"tool call failed ({name}): {exc}")


def close_all_tabs() -> None:
    """Close all tabs except the first one, then navigate it to blank."""
    try:
        data  = _mcp_post({"jsonrpc": "2.0", "method": "tools/call", "id": 1,
                           "params": {"name": "list_pages", "arguments": {}}})
        lines = (data.get("result", {}).get("content") or [{}])[0].get("text", "")
        ids = []
        for line in lines.splitlines():
            line = line.strip()
            if line and line[0].isdigit():
                try:
                    ids.append(int(line.split(".")[0]))
                except ValueError:
                    pass
        # Keep the first tab alive — close everything else
        keep = ids[0] if ids else None
        for pid in ids[1:]:
            _mcp_post({"jsonrpc": "2.0", "method": "tools/call", "id": 1,
                       "params": {"name": "close_page", "arguments": {"page": pid}}})
        # Navigate the surviving tab to a clean state
        if keep is not None:
            _mcp_post({"jsonrpc": "2.0", "method": "tools/call", "id": 1,
                       "params": {"name": "navigate_page", "arguments": {"page": keep, "url": "about:blank"}}})
    except Exception as exc:
        log(f"  [cleanup] tab cleanup failed: {exc}")


def _mcp_to_openai_tools(mcp_tools: list[dict]) -> list[dict]:
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


# ── Agent ─────────────────────────────────────────────────────────────────────

class BrowserAgent:

    def __init__(self) -> None:
        # MiMo uses "api-key" header, not "Authorization: Bearer"
        self._client = OpenAI(
            api_key         = "dummy",
            base_url        = MIMO_BASE_URL,
            default_headers = {"api-key": MIMO_API_KEY},
        )
        self._tools: list[dict] | None = None

    def _ensure_tools(self) -> list[dict]:
        if self._tools is None:
            mcp = _mcp_tools_list()
            if not mcp:
                raise RuntimeError(
                    "BrowserOS MCP not reachable.\n"
                    "  1. Open BrowserOS\n"
                    "  2. Settings > BrowserOS as MCP\n"
                    f"  3. URL should be: {BROWSEROS_URL}"
                )
            self._tools = _mcp_to_openai_tools(mcp)
            log(f"[BrowserOS] {len(self._tools)} tools loaded")
        return self._tools

    def _call_mimo(self, messages: list, tools: list) -> Any:
        for attempt in range(_MAX_RETRIES):
            _limiter.wait()
            try:
                return self._client.chat.completions.create(
                    model    = MODEL,
                    messages = messages,  # type: ignore[arg-type]
                    tools    = tools,     # type: ignore[arg-type]
                    timeout  = 120,       # 2 min max per API call — prevents silent hangs
                )
            except Exception as exc:
                msg = str(exc)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    wait = 2 ** attempt * 5
                    log(f"  [rate-limit] 429 -- waiting {wait}s")
                    time.sleep(wait)
                    continue
                raise
        raise RuntimeError("Max retries exceeded")

    def run(self, goal: str, max_turns: int = 20) -> dict[str, Any]:
        tools = self._ensure_tools()

        system = (
            "You are a browser automation agent. You have full control of a real web browser "
            "through 66 tools — use whatever you need to complete the task.\n\n"
            "ONE RULE about page IDs:\n"
            "list_pages returns lines like '3. Page Title (tab 99999)' — "
            "the page ID is the leading number (3), NOT the tab number in parentheses (99999).\n\n"
            "When you call take_screenshot, the image will appear in the very next message so you can see it.\n\n"
            "When you have the answer, respond with plain text only (no tool call)."
        )

        messages: list = [
            {"role": "system", "content": system},
            {"role": "user",   "content": f"TASK: {goal}"},
        ]

        turns         = 0
        tool_count    = 0
        screenshot_ct = 0
        MAX_SCREENSHOTS = 3   # prevent context bloat from stacked images
        start         = time.monotonic()

        try:
            for _ in range(max_turns):
                resp   = self._call_mimo(messages, tools)
                turns += 1
                choice = resp.choices[0]
                msg    = choice.message

                if msg.content:
                    log(f"  [thinking] {str(msg.content)[:200]}")

                if not msg.tool_calls:
                    return {"success": True, "output": msg.content or "(no output)",
                            "turns": turns, "tool_calls": tool_count, "error": None,
                            "elapsed": round(time.monotonic() - start, 1)}

                messages.append({
                    "role": "assistant", "content": msg.content or "",
                    "tool_calls": [{"id": tc.id, "type": "function",
                                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                                   for tc in msg.tool_calls],
                })

                for tc in msg.tool_calls:
                    tool_count += 1
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}

                    log(f"  --> [{tool_count}] {name}({json.dumps(args)[:100]})")

                    # Cap screenshots to avoid context bloat
                    if name in ("take_screenshot", "save_screenshot"):
                        screenshot_ct += 1
                        if screenshot_ct > MAX_SCREENSHOTS:
                            result = ToolResult("Screenshot limit reached (max 3 per task). Use take_snapshot or get_page_content instead.")
                            log(f"  [screenshot cap] skipped — use text tools")
                            messages.append({"role": "tool", "content": result.text, "tool_call_id": tc.id, "name": name})
                            continue

                    result = _mcp_call(name, args)
                    log(f"  <-- {result.text[:200]}{'...' if len(result.text) > 200 else ''}")

                    # Tool message must have string content (OpenAI spec)
                    messages.append({
                        "role": "tool", "content": result.text,
                        "tool_call_id": tc.id, "name": name,
                    })

                    # If the tool returned an image (screenshot), inject it as a
                    # separate user message so MiMo can actually see it
                    if result.image_b64:
                        log(f"  [vision] screenshot injected as image_url")
                        messages.append({
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"[Screenshot from {name}]"},
                                {"type": "image_url",
                                 "image_url": {"url": f"data:image/jpeg;base64,{result.image_b64}"}},
                            ],
                        })

            return {"success": False, "output": "(max turns reached)",
                    "turns": turns, "tool_calls": tool_count, "error": "max_turns_exceeded",
                    "elapsed": round(time.monotonic() - start, 1)}

        except Exception as exc:
            return {"success": False, "output": "", "turns": turns, "tool_calls": tool_count,
                    "error": str(exc), "elapsed": round(time.monotonic() - start, 1)}


if __name__ == "__main__":
    set_log_file(Path("results/eval.log"))
    agent  = BrowserAgent()
    result = agent.run("Go to https://example.com, take a screenshot, and tell me what you see.")
    log(json.dumps(result, indent=2))
