from __future__ import annotations

import functools


TOKEN_BUDGETS: dict[str, int] = {
    "modal":    190_000,   
    "deepseek":  900_000,   
}
DEFAULT_BUDGET = 50_000


@functools.lru_cache(maxsize=1)
def _encoder():
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def count(text: str) -> int:
    """Approximate token count. Falls back to char/4 if tiktoken is missing."""
    if not text:
        return 0
    enc = _encoder()
    if enc is None:
        return max(1, len(text) // 4)
    try:
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def budget_for(model: str) -> int:
    return TOKEN_BUDGETS.get(model, DEFAULT_BUDGET)


def count_message(msg: dict) -> int:
    """Count tokens for one history message, including tool_call payload size."""
    content = str(msg.get("content") or "")
    n = count(content)
    # tool_calls add JSON overhead — approximate
    for tc in msg.get("tool_calls") or []:
        n += count(str(tc.get("name", ""))) + count(str(tc.get("args", "")))
    if msg.get("reasoning_content"):
        n += count(str(msg["reasoning_content"]))
    return n
