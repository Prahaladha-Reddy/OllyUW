"""
DeepSeek V4 Flash — Multi-Turn Stress Test
===========================================
Tests that multi-turn conversations work correctly with:
  - reasoning_content being passed back in history (the critical bug from screenshot)
  - tool calls in the middle of a conversation
  - multiple exchanges with and without reasoning
  - 6+ back-and-forth turns

The bug: DeepSeek returns reasoning_content on assistant messages.
On the NEXT turn, if you don't include reasoning_content in the history,
the API returns HTTP 400. This test verifies our fix works.

Usage:
  python test_multiturn.py
"""

from __future__ import annotations

import io
import json
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

if not API_KEY:
    print("[FAIL] DEEPSEEK_API_KEY not set in .env")
    sys.exit(1)

if not BASE_URL.endswith("/v1"):
    BASE_URL = f"{BASE_URL}/v1"

from openai import OpenAI

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ── Tools available during the conversation ──────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Perform a mathematical calculation. Returns the numeric result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression to evaluate, e.g. '17 * 23 + 4'"},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fact",
            "description": "Get an interesting fact about a number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer", "description": "The number to get a fact about"},
                },
                "required": ["number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "store_note",
            "description": "Store a note or result for later reference in this conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key to store the note under"},
                    "value": {"type": "string", "description": "Value to store"},
                },
                "required": ["key", "value"],
            },
        },
    },
]

# ── Tool executor (simulated) ─────────────────────────────────────────────────

_notes: dict[str, str] = {}

def execute_tool(name: str, args: dict) -> str:
    if name == "calculate":
        expr = args.get("expression", "")
        try:
            # Safe eval for math only
            allowed = set("0123456789+-*/().% ")
            if not all(c in allowed for c in expr):
                return f"Error: unsafe expression: {expr!r}"
            result = eval(expr)
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {e}"
    elif name == "get_fact":
        number = args.get("number", 0)
        facts = {
            42: "42 is the Answer to the Ultimate Question of Life, the Universe, and Everything.",
            391: "391 = 17 × 23. It is a semiprime number.",
            100: "100 is a perfect square (10²) and a Harshad number.",
            7: "7 is the most commonly chosen 'random' number when people are asked to pick one between 1 and 10.",
            1024: "1024 is 2^10 — a power of two often used in computing.",
        }
        return facts.get(number, f"{number} is a number. It has {len(str(number))} digit(s) and is {'even' if number % 2 == 0 else 'odd'}.")
    elif name == "store_note":
        key = args.get("key", "")
        value = args.get("value", "")
        _notes[key] = value
        return f"Stored: {key} = {value}"
    return f"Unknown tool: {name}"


# ── Core helpers ──────────────────────────────────────────────────────────────

def _sep(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def _call_api(messages: list[dict], use_tools: bool = True) -> dict:
    """
    Single API call. Returns dict with:
      content, reasoning_content, tool_calls (list or None), finish_reason
    """
    kwargs = dict(
        model=MODEL,
        messages=messages,
        temperature=0,
        stream=False,
    )
    if use_tools:
        kwargs["tools"] = TOOLS

    response = client.chat.completions.create(**kwargs)
    choice = response.choices[0]
    msg = choice.message

    return {
        "content": msg.content or "",
        "reasoning_content": getattr(msg, "reasoning_content", None) or "",
        "tool_calls": msg.tool_calls or [],
        "finish_reason": choice.finish_reason,
    }


def _append_assistant(messages: list[dict], result: dict) -> list[dict]:
    """
    Append assistant turn to history — THIS IS THE CRITICAL PART.
    We MUST include reasoning_content if present, or the next API call will 400.
    """
    item: dict = {"role": "assistant", "content": result["content"] or None}
    if result["reasoning_content"]:
        # KEY FIX: preserve reasoning_content in history
        item["reasoning_content"] = result["reasoning_content"]
    if result["tool_calls"]:
        item["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in result["tool_calls"]
        ]
    messages.append(item)
    return messages


def _append_tool_results(messages: list[dict], tool_calls) -> list[dict]:
    """Execute tools and append their results."""
    for tc in tool_calls:
        args = json.loads(tc.function.arguments)
        tool_output = execute_tool(tc.function.name, args)
        print(f"    [TOOL] {tc.function.name}({tc.function.arguments}) -> {tool_output}")
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": tool_output,
        })
    return messages


def _show_turn(turn_num: int, role: str, result: dict):
    print(f"\n  Turn {turn_num} [{role}]")
    if result.get("reasoning_content"):
        rc = result["reasoning_content"]
        print(f"    [REASONING] ({len(rc)} chars): {rc[:150]}{'...' if len(rc) > 150 else ''}")
    content = result.get("content", "")
    if content:
        print(f"    [CONTENT] {content[:200]}{'...' if len(content) > 200 else ''}")
    if result.get("tool_calls"):
        names = [tc.function.name for tc in result["tool_calls"]]
        print(f"    [TOOL CALLS] {names}")


# ── Test A: Pure text multi-turn, 6 exchanges, reasoning throughout ──────────

def test_a_pure_text_multiturn():
    _sep("TEST A: Pure text multi-turn — 6 exchanges with reasoning")
    print("  Testing: Can we pass reasoning_content back in history without 400?")

    system = {"role": "system", "content": "You are a math tutor. Think step by step."}
    messages = [system]
    passed = True
    errors = []

    exchanges = [
        "What is 7 squared?",
        "Now add 3 to that result.",
        "Multiply by 2.",
        "Subtract 10. What do you have?",
        "Is this number prime? Reason carefully.",
        "Great. What was the original number I started with, 7 squares? Confirm.",
    ]

    for i, user_msg in enumerate(exchanges, start=1):
        messages.append({"role": "user", "content": user_msg})
        print(f"\n  Turn {i} — User: {user_msg}")
        try:
            result = _call_api(messages, use_tools=False)
            _show_turn(i, "Assistant", result)
            _append_assistant(messages, result)

            if not result["content"]:
                errors.append(f"Turn {i}: No content")
                passed = False
            if not result["reasoning_content"]:
                errors.append(f"Turn {i}: No reasoning (might be okay for some turns)")
        except Exception as exc:
            errors.append(f"Turn {i}: API ERROR — {exc}")
            passed = False
            break

    print(f"\n  Total messages in history: {len(messages)}")
    if passed and not errors:
        print("  [PASS] All 6 turns completed, reasoning_content passed back safely")
    else:
        for e in errors:
            print(f"  [WARN] {e}")
        if all("reasoning" in e for e in errors):
            print("  [PASS] (no 400 errors, reasoning warnings only)")
            passed = True

    return passed


# ── Test B: Tool calls embedded in multi-turn conversation ────────────────────

def test_b_tool_calls_in_multiturn():
    _sep("TEST B: Tool calls embedded in multi-turn — 6 exchanges")
    print("  Testing: Does history with tool calls + reasoning pass correctly?")

    system = {"role": "system", "content": (
        "You are a helpful math assistant. When you need to calculate something, "
        "use the calculate tool. When done, use store_note to save the result."
    )}
    messages = [system]
    passed = True
    turn_num = 0

    conversation_script = [
        "Calculate 17 * 23 for me.",
        "Now add 100 to that result. Calculate it.",
        "Get a fact about that number you just computed.",
        "Now store the fact you just got under the key 'main_result'.",
        "What was the very first number we calculated in this conversation?",
        "Great! Can you summarize everything we did in this conversation?",
    ]

    for i, user_msg in enumerate(conversation_script, start=1):
        turn_num = i
        messages.append({"role": "user", "content": user_msg})
        print(f"\n  Turn {i} — User: {user_msg}")

        try:
            # Agentic loop: keep calling until no more tool calls
            loop_iterations = 0
            while True:
                loop_iterations += 1
                if loop_iterations > 5:
                    print("    [WARN] Too many tool call loops!")
                    break

                result = _call_api(messages, use_tools=True)
                _show_turn(i, f"Assistant (loop {loop_iterations})", result)
                _append_assistant(messages, result)

                if result["tool_calls"]:
                    _append_tool_results(messages, result["tool_calls"])
                else:
                    # No more tool calls — assistant gave a final answer
                    break

            if not result["content"] and not result["tool_calls"]:
                print(f"    [WARN] Turn {i}: No content and no tool calls")

        except Exception as exc:
            print(f"\n  [ERROR] API request failed on turn {i}: {exc}")
            passed = False
            break

    print(f"\n  Total messages in history: {len(messages)}")
    print(f"  Turns completed: {turn_num}/6")
    if passed and turn_num == 6:
        print("  [PASS] All 6 turns with tool calls completed successfully")
    elif passed:
        print(f"  [WARN] Only {turn_num}/6 turns completed (no API error)")
    else:
        print("  [FAIL] API error occurred")

    return passed and turn_num == 6


# ── Test C: Parallel tool calls embedded in multi-turn ───────────────────────

def test_c_parallel_tools_in_multiturn():
    _sep("TEST C: Parallel tool calls + reasoning in multi-turn history")
    print("  Testing: Parallel calls → reasoning_content preserved → no 400 on next turn")

    system = {"role": "system", "content": (
        "You are an assistant. When asked about multiple things at once, "
        "call all relevant tools in parallel in a single response."
    )}
    messages = [system]
    passed = True

    # Turn 1: Ask something that triggers parallel calls
    messages.append({"role": "user", "content": "Calculate both 12*12 and 15*15 at the same time."})
    print("\n  Turn 1 — Parallel tool calls")
    try:
        result = _call_api(messages, use_tools=True)
        _show_turn(1, "Assistant", result)
        _append_assistant(messages, result)

        if len(result["tool_calls"]) >= 2:
            print(f"    [PASS] Got {len(result['tool_calls'])} parallel tool calls")
        else:
            print(f"    [WARN] Only {len(result['tool_calls'])} calls (expected >=2)")

        _append_tool_results(messages, result["tool_calls"])

        # Tool results → need final answer
        result2 = _call_api(messages, use_tools=True)
        _show_turn(1, "Assistant (final)", result2)
        _append_assistant(messages, result2)
    except Exception as exc:
        print(f"\n  [ERROR] Turn 1 API request failed: {exc}")
        return False

    # Turn 2: Follow-up — THIS is where the 400 bug would appear without the fix
    messages.append({"role": "user", "content": "Which of those two results is larger? Now add them together using the calculate tool."})
    print("\n  Turn 2 — Follow-up after parallel tool calls (the 400 bug trigger)")
    try:
        result = _call_api(messages, use_tools=True)
        _show_turn(2, "Assistant", result)
        _append_assistant(messages, result)

        if result["tool_calls"]:
            _append_tool_results(messages, result["tool_calls"])
            result_final = _call_api(messages, use_tools=True)
            _show_turn(2, "Assistant (final)", result_final)
            _append_assistant(messages, result_final)

        print("    [PASS] No 400 error! reasoning_content passback working correctly")
    except Exception as exc:
        print(f"\n  [ERROR] Turn 2 API request failed: {exc}")
        print("    [FAIL] This is the reasoning_content 400 bug!")
        passed = False
        return passed

    # Turn 3: Simple follow-up to confirm conversation context is preserved
    messages.append({"role": "user", "content": "What were the two original numbers we multiplied at the start of this conversation?"})
    print("\n  Turn 3 — Context retention check")
    try:
        result = _call_api(messages, use_tools=False)
        _show_turn(3, "Assistant", result)
        _append_assistant(messages, result)
        content_lower = result["content"].lower()
        if "12" in content_lower and "15" in content_lower:
            print("    [PASS] Context retained across turns (correctly recalled 12 and 15)")
        else:
            print(f"    [WARN] Content didn't mention 12 and 15: {result['content'][:100]}")
    except Exception as exc:
        print(f"\n  [ERROR] Turn 3 API request failed: {exc}")
        passed = False

    if passed:
        print("\n  [PASS] Parallel tool calls + reasoning in multi-turn - no 400 errors")
    return passed


# ── Test D: WITHOUT the fix — simulate broken history passback ────────────────

def test_d_broken_history_intentionally():
    _sep("TEST D: Reproduce the 400 bug (intentionally broken — for comparison)")
    print("  Testing: Does the API 400 if we STRIP reasoning_content from history?")

    system = {"role": "system", "content": "You are a helpful assistant."}
    messages = [system]

    # Turn 1
    messages.append({"role": "user", "content": "What is 6 * 7?"})
    result = _call_api(messages, use_tools=False)

    # INTENTIONALLY BROKEN: strip reasoning_content before appending
    broken_item: dict = {"role": "assistant", "content": result["content"]}
    # NOTE: deliberately NOT including reasoning_content here
    messages.append(broken_item)

    has_reasoning = bool(result["reasoning_content"])
    print(f"\n  Turn 1 had reasoning: {has_reasoning}")
    print(f"  Stripped reasoning from history. Now sending Turn 2...")

    # Turn 2 — this should 400 if DeepSeek enforces reasoning_content passback
    messages.append({"role": "user", "content": "Now multiply that result by 3."})
    try:
        result2 = _call_api(messages, use_tools=False)
        content = result2["content"]
        print(f"  Turn 2 succeeded: {content[:100]}")
        if has_reasoning:
            print("  [WARN] NOTE: No 400 error even without reasoning_content (API may be lenient)")
            print("         But our code preserves it anyway for safety.")
        else:
            print("  [INFO] Turn 1 had no reasoning, so stripping had no effect.")
        return True  # Not a failure of our code; just documenting API behavior
    except Exception as exc:
        error_str = str(exc)
        if "400" in error_str:
            print(f"  [ERROR] Got 400 as expected: {error_str[:200]}")
            print("  [PASS] CONFIRMED: Stripping reasoning_content causes 400")
            print("  [PASS] This proves our fix (keeping reasoning_content in history) is NECESSARY")
        else:
            print(f"  [ERROR] Unexpected error: {error_str[:200]}")
        return True  # Either result is informative, not a code failure


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  DeepSeek V4 Flash — Multi-Turn Stress Test")
    print("=" * 60)
    print(f"  Model:    {MODEL}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  API Key:  {API_KEY[:8]}...{API_KEY[-4:]}")

    results = {}

    t = time.monotonic()
    results["A"] = test_a_pure_text_multiturn()
    print(f"\n  [TIME] Test A done in {time.monotonic()-t:.1f}s")

    t = time.monotonic()
    results["B"] = test_b_tool_calls_in_multiturn()
    print(f"\n  [TIME] Test B done in {time.monotonic()-t:.1f}s")

    t = time.monotonic()
    results["C"] = test_c_parallel_tools_in_multiturn()
    print(f"\n  [TIME] Test C done in {time.monotonic()-t:.1f}s")

    t = time.monotonic()
    results["D"] = test_d_broken_history_intentionally()
    print(f"\n  [TIME] Test D done in {time.monotonic()-t:.1f}s")

    print(f"\n{'='*60}")
    print("  FINAL SUMMARY")
    print(f"{'='*60}")
    for label, passed in results.items():
        icon = "[PASS]" if passed else "[FAIL]"
        names = {
            "A": "Pure text multi-turn (6 exchanges, with reasoning)",
            "B": "Tool calls embedded in multi-turn (6 exchanges)",
            "C": "Parallel tools + reasoning in multi-turn (400 bug trigger)",
            "D": "Intentionally broken history (documents API behavior)",
        }
        print(f"  {icon} Test {label}: {names[label]}")
    total = sum(1 for v in results.values() if v)
    print(f"\n  {total}/{len(results)} tests passed")


if __name__ == "__main__":
    main()
