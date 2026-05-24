from __future__ import annotations

from typing import Any

from agent.llm.tokens import budget_for, count_message
from agent.log import log


_MIN_KEEP_RECENT = 4


def recent_within_budget(
    messages: list[dict[str, Any]], model: str
) -> list[dict[str, Any]]:
    """Walk newest → oldest, keep until token budget is hit."""
    if not messages:
        return []

    budget = budget_for(model)
    keeping: list[dict[str, Any]] = []
    total = 0

    for i, msg in enumerate(reversed(messages)):
        cost = count_message(msg)
        if total + cost > budget and i >= _MIN_KEEP_RECENT:
            break
        keeping.insert(0, msg)
        total += cost

    # Orphan-tool guard: drop leading tool messages whose assistant turn was cut.
    while keeping and keeping[0].get("role") == "tool":
        dropped = keeping.pop(0)
        log.debug("compaction dropped orphan tool message id=%s",
                  dropped.get("tool_call_id"))

    # Cross-check: drop tool messages whose tool_call_id has no matching
    # assistant tool_call inside the kept window.
    call_ids: set[str] = set()
    for m in keeping:
        if m.get("role") == "assistant":
            for tc in m.get("tool_calls") or []:
                tcid = tc.get("id")
                if tcid:
                    call_ids.add(tcid)
    keeping = [
        m for m in keeping
        if m.get("role") != "tool" or m.get("tool_call_id") in call_ids
    ]

    if log.isEnabledFor(10):  # DEBUG
        log.debug(
            "compaction model=%s kept=%d/%d total_tokens=%d budget=%d",
            model, len(keeping), len(messages), total, budget,
        )

    return keeping
