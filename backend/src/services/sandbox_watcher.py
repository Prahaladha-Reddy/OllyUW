"""Background task: keep E2B sandboxes alive while the agent is actively working.

Policy: extend the sandbox timeout only while agent:{computer_id}:activity
exists in Redis. The worker sets this key (TTL = 20 min) every time it starts
processing a message. As long as tasks arrive the key keeps refreshing. Once
the last task finishes and no new ones arrive for 20 minutes, the key expires,
the watcher stops extending, and E2B idles-pauses the sandbox (on_timeout=pause
is set at create time).

This means:
  - Tab open, chatting       -> activity key is fresh -> extend -> stays alive
  - Tab open, quiet for 20m  -> activity key expires  -> stop extending -> pauses
  - Tab closed, task running -> worker keeps touching key -> extends -> stays alive
  - Tab closed, idle for 20m -> key expires -> pauses -> reconnect_runtime resumes

set_timeout is the static form (no connect/resume side-effect), matching how
the e2b-sandbox-orchestrator does it.
"""
from __future__ import annotations

import asyncio
import logging

from e2b_desktop import Sandbox as DesktopSandbox

from src.config import get_settings
from src.providers import redis_provider, supabase_provider

logger = logging.getLogger("ollyuw.watcher")

_TICK_SECONDS = 300  # 5 minutes

_RUNNING = False


async def start() -> None:
    global _RUNNING
    if _RUNNING:
        return
    _RUNNING = True
    asyncio.create_task(_loop(), name="sandbox-watcher")
    logger.info("sandbox watcher started (5-min tick, 20-min activity window)")


async def stop() -> None:
    global _RUNNING
    _RUNNING = False


async def _loop() -> None:
    while _RUNNING:
        await asyncio.sleep(_TICK_SECONDS)
        try:
            await _tick()
        except Exception as exc:
            logger.error("watcher tick failed: %s", exc)


async def _tick() -> None:
    settings = get_settings()
    db = supabase_provider.get_service_client()
    redis = redis_provider.get_client()

    resp = (
        db.table("computers")
        .select("id, sandbox_id")
        .eq("runtime_state", "running")
        .not_.is_("sandbox_id", "null")
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return

    extended = 0
    idle = 0

    for row in rows:
        computer_id: str = row["id"]
        sandbox_id: str = row["sandbox_id"]
        activity_key = f"agent:{computer_id}:activity"

        # Key exists -> agent processed something within the last 20 min -> extend.
        # Key absent -> agent has been idle for 20+ min -> stop extending, let E2B pause.
        active = await redis.exists(activity_key)

        if active:
            try:
                await asyncio.to_thread(
                    _set_timeout, sandbox_id, settings.e2b_sandbox_timeout, settings.e2b_api_key
                )
                extended += 1
            except Exception as exc:
                logger.warning("watcher: extend failed sandbox=%s: %s", sandbox_id, exc)
        else:
            idle += 1

    logger.info(
        "watcher tick: %d running, %d extended, %d idle (will auto-pause when E2B timeout hits)",
        len(rows), extended, idle,
    )


def _set_timeout(sandbox_id: str, timeout: int, api_key: str) -> None:
    # Static form: pure API call, does not connect to or resume the sandbox.
    DesktopSandbox.set_timeout(sandbox_id, timeout, api_key=api_key)
