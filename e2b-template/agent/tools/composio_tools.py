"""
Composio deferred tools — app integrations for the agent.

Registered in the tool registry and discovered via:
  tool_search("gmail")  →  composio_list_apps, composio_find_actions, composio_execute

The Composio user_id is OLLYUW_USER_ID (the user's Supabase UUID), injected into
the sandbox environment when the computer starts.

Uses the Composio v1 SDK (package `composio`, 1.0.0rc10) lower-level API:
  connected_accounts.list / tools.get_raw_composio_tools / tools.get / tools.execute
"""
from __future__ import annotations

import json
import os


def _composio():
    from composio import Composio
    api_key = os.environ.get("COMPOSIO_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "COMPOSIO_API_KEY is not set. The user may need to reconnect their computer."
        )
    return Composio(api_key=api_key)


def _user_id() -> str:
    return os.environ.get("OLLYUW_USER_ID", "anon")


def composio_list_apps() -> str:
    """List all apps the user has connected (Gmail, Slack, Notion, GitHub, etc.)."""
    c = _composio()
    resp = c.connected_accounts.list(user_ids=[_user_id()], statuses=["ACTIVE"])
    if not resp.items:
        return (
            "No apps connected. The user can connect apps from the Apps menu "
            "in the OllyUW dashboard."
        )
    slugs = sorted({item.toolkit.slug for item in resp.items})
    return "Connected apps: " + ", ".join(slugs)


def composio_find_actions(toolkit: str, query: str = "") -> str:
    """Find available actions for an app (e.g. toolkit='GMAIL', query='send').

    Returns each action's slug plus its parameter names so you know what to pass
    to composio_execute.
    """
    c = _composio()
    tools = c.tools.get_raw_composio_tools(
        toolkits=[toolkit.upper()],
        search=query or None,
        limit=30,
    )
    if not tools:
        return (
            f"No actions found for {toolkit!r}. "
            "Confirm the app is connected with composio_list_apps."
        )
    lines = []
    for t in tools:
        params = t.input_parameters if isinstance(t.input_parameters, dict) else {}
        props = params.get("properties") or {}
        required = params.get("required") or []
        param_hints = ", ".join(
            f"{p}*" if p in required else p for p in list(props.keys())[:12]
        )
        lines.append(
            f"  {t.slug}: {(t.description or '')[:90]}\n    params: {param_hints or '(none)'}"
        )
    return (
        f"Actions for {toolkit.upper()} ({len(lines)} shown; * = required):\n"
        + "\n".join(lines)
    )


def composio_execute(action: str, params: dict | None = None) -> str:
    """Execute a Composio action using the user's connected app.

    action: tool slug e.g. 'GMAIL_SEND_EMAIL', 'GOOGLEDRIVE_LIST_FILES'
    params: action arguments — use composio_find_actions to discover the schema
    """
    c = _composio()
    uid = _user_id()
    # The SDK's tools.execute() looks the slug up in an internal schema cache and
    # raises KeyError if the tool was never fetched in this process. Pre-fetch it
    # with tools.get() (which populates that cache) before executing.
    try:
        c.tools.get(user_id=uid, tools=[action])
    except Exception:
        pass  # If prefetch fails, execute() will surface the real error below.

    result = c.tools.execute(action, arguments=params or {}, user_id=uid)
    return json.dumps(result, indent=2, default=str)
