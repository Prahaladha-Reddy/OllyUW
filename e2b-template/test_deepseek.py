"""
DeepSeek V4 Flash — Comprehensive Test Suite
=============================================
Tests (run sequentially):
  1. Plain text + thinking/reasoning tokens
  2. Streaming + thinking tokens stream
  3. Single tool call
  4. Parallel tool calling
  5. Image understanding (base64 image)
  6. Tool-returned image (LLM calls tool → gets image → analyzes it)

Usage:
  python test_deepseek.py          # run all tests
  python test_deepseek.py 1        # run only test 1
  python test_deepseek.py 3 5      # run tests 3 and 5
"""

from __future__ import annotations

import base64
import io
import json
import os
import struct
import sys
import zlib
import time

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

if not API_KEY:
    print("[FAIL] DEEPSEEK_API_KEY not set in .env")
    sys.exit(1)

# Ensure base_url ends with /v1
if not BASE_URL.endswith("/v1"):
    BASE_URL = f"{BASE_URL}/v1"

from openai import OpenAI

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ── Helpers ──────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_population",
            "description": "Get the population of a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capture_screenshot",
            "description": "Capture a screenshot of the user's desktop. Returns the image as a base64-encoded PNG.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


def _create_test_png(width: int = 200, height: int = 150) -> bytes:
    """Create a minimal valid PNG in memory — a red/blue gradient rectangle.
    No external dependencies needed."""

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    # PNG signature
    sig = b"\x89PNG\r\n\x1a\n"

    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    ihdr = _chunk(b"IHDR", ihdr_data)

    # IDAT — raw pixel data (filter byte 0 per row + RGB)
    raw_rows = []
    for y in range(height):
        row = b"\x00"  # filter: None
        for x in range(width):
            r = int(255 * x / width)
            g = int(100 * y / height)
            b = int(255 * (1 - x / width))
            row += struct.pack("BBB", r, g, b)
        raw_rows.append(row)
    compressed = zlib.compress(b"".join(raw_rows))
    idat = _chunk(b"IDAT", compressed)

    # IEND
    iend = _chunk(b"IEND", b"")

    return sig + ihdr + idat + iend


def _img_b64() -> str:
    """Return a base64-encoded test PNG."""
    return base64.b64encode(_create_test_png()).decode()


def _separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def _pass(msg: str):
    print(f"  [PASS] {msg}")


def _fail(msg: str):
    print(f"  [FAIL] {msg}")


# ── Test 1: Plain text + thinking tokens (non-streaming) ────────────────────

def test_1_plain_text():
    _separator("TEST 1: Plain text + thinking/reasoning tokens")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is 17 * 23? Think step by step."},
        ],
        temperature=0,
        stream=False,
    )

    choice = response.choices[0]
    content = choice.message.content
    reasoning = getattr(choice.message, "reasoning_content", None)

    print(f"  [REASONING] {reasoning[:300] if reasoning else '(none)'}{'...' if reasoning and len(reasoning) > 300 else ''}")
    print(f"  [CONTENT] {content[:300] if content else '(none)'}")

    if content:
        _pass("Got text response")
    else:
        _fail("No text response")

    if reasoning:
        _pass("Got reasoning/thinking tokens")
    else:
        _fail("No reasoning/thinking tokens (model may not support it or it's disabled)")

    return bool(content)


# ── Test 2: Streaming + thinking tokens ──────────────────────────────────────

def test_2_streaming():
    _separator("TEST 2: Streaming + thinking tokens")

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Explain why the sky is blue in 2 sentences."},
        ],
        temperature=0,
        stream=True,
    )

    reasoning_parts = []
    content_parts = []
    chunk_count = 0

    for chunk in stream:
        chunk_count += 1
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        # Check for reasoning_content
        rc = getattr(delta, "reasoning_content", None)
        if rc:
            reasoning_parts.append(rc)

        # Check for content
        if delta.content:
            content_parts.append(delta.content)

    reasoning_text = "".join(reasoning_parts)
    content_text = "".join(content_parts)

    print(f"  [CHUNKS] Total chunks: {chunk_count}")
    print(f"  [REASONING] ({len(reasoning_parts)} chunks): {reasoning_text[:200]}{'...' if len(reasoning_text) > 200 else ''}")
    print(f"  [CONTENT] ({len(content_parts)} chunks): {content_text[:200]}{'...' if len(content_text) > 200 else ''}")

    if content_text:
        _pass("Streamed text content")
    else:
        _fail("No streamed text content")

    if reasoning_parts:
        _pass(f"Streamed reasoning in {len(reasoning_parts)} chunks")
    else:
        _fail("No reasoning chunks in stream")

    return bool(content_text)


# ── Test 3: Single tool call ─────────────────────────────────────────────────

def test_3_single_tool_call():
    _separator("TEST 3: Single tool call")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant with access to tools."},
            {"role": "user", "content": "What's the weather in Tokyo?"},
        ],
        tools=TOOLS,
        temperature=0,
        stream=False,
    )

    choice = response.choices[0]
    tool_calls = choice.message.tool_calls

    if tool_calls:
        for tc in tool_calls:
            print(f"  [TOOL] {tc.function.name}")
            print(f"     ID:   {tc.id}")
            print(f"     Args: {tc.function.arguments}")
        _pass(f"Got {len(tool_calls)} tool call(s)")

        # Verify it called get_weather
        names = [tc.function.name for tc in tool_calls]
        if "get_weather" in names:
            _pass("Correctly called get_weather")
        else:
            _fail(f"Expected get_weather, got: {names}")
    else:
        content = choice.message.content
        print(f"  [CONTENT] Response (no tool call): {content[:200] if content else '(none)'}")
        _fail("No tool calls returned")

    return bool(tool_calls)


# ── Test 4: Parallel tool calling ────────────────────────────────────────────

def test_4_parallel_tool_calls():
    _separator("TEST 4: Parallel tool calling")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant with access to tools. When you need multiple pieces of info, call all relevant tools at once in parallel."},
            {"role": "user", "content": "I need the weather AND population for both Tokyo and London. Call all the tools you need right now."},
        ],
        tools=TOOLS,
        temperature=0,
        stream=False,
    )

    choice = response.choices[0]
    tool_calls = choice.message.tool_calls

    if tool_calls:
        for tc in tool_calls:
            print(f"  [TOOL] {tc.function.name}({tc.function.arguments})")
        _pass(f"Got {len(tool_calls)} tool call(s)")

        if len(tool_calls) >= 2:
            _pass(f"Multiple parallel calls: {len(tool_calls)}")
        else:
            _fail(f"Expected >=2 parallel calls, got {len(tool_calls)}")
    else:
        content = choice.message.content
        print(f"  [CONTENT] Response (no tool calls): {content[:200] if content else '(none)'}")
        _fail("No tool calls returned")

    return bool(tool_calls and len(tool_calls) >= 2)


# ── Test 5: Image understanding ──────────────────────────────────────────────

def test_5_image_understanding():
    _separator("TEST 5: Image understanding (base64 PNG)")

    img_b64 = _img_b64()
    print(f"  [IMAGE] Created test PNG (200x150 red-blue gradient), base64 length: {len(img_b64)}")

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that can see images."},
                {"role": "user", "content": [
                    {"type": "text", "text": "Describe what you see in this image. What colors are present? What kind of image is it?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ]},
            ],
            temperature=0,
            stream=False,
        )

        choice = response.choices[0]
        content = choice.message.content
        reasoning = getattr(choice.message, "reasoning_content", None)

        if reasoning:
            print(f"  [REASONING] {reasoning[:200]}{'...' if len(reasoning) > 200 else ''}")
        print(f"  [CONTENT] Answer: {content[:400] if content else '(none)'}")

        if content:
            _pass("Got image description")
            # Check if it mentions colors
            lower = content.lower()
            if any(c in lower for c in ["red", "blue", "gradient", "color"]):
                _pass("Response mentions colors/gradient (image was understood)")
            else:
                _fail("Response doesn't mention colors — may not have seen the image")
        else:
            _fail("No content in response")

        return bool(content)

    except Exception as exc:
        print(f"  [ERROR] Exception: {exc}")
        _fail(f"Image API call failed: {exc}")
        return False


# ── Test 6: Tool-returned image ──────────────────────────────────────────────

def test_6_tool_returned_image():
    _separator("TEST 6: Tool-returned image (LLM calls tool → gets image → analyzes)")

    # Step 1: Ask the LLM to capture a screenshot (which triggers capture_screenshot tool)
    print("  Step 1: Asking LLM to capture a screenshot...")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant with access to tools. When the user asks to see or capture the screen, use the capture_screenshot tool."},
            {"role": "user", "content": "Please capture a screenshot of the desktop and tell me what you see."},
        ],
        tools=TOOLS,
        temperature=0,
        stream=False,
    )

    choice = response.choices[0]
    tool_calls = choice.message.tool_calls

    if not tool_calls:
        print(f"  [CONTENT] Response: {choice.message.content[:200] if choice.message.content else '(none)'}")
        _fail("LLM did not call capture_screenshot tool")
        return False

    tc = tool_calls[0]
    print(f"  [TOOL] Tool called: {tc.function.name} (id={tc.id})")

    if tc.function.name != "capture_screenshot":
        _fail(f"Expected capture_screenshot, got {tc.function.name}")
        return False

    _pass("LLM called capture_screenshot")

    # Step 2: Simulate the tool returning a base64 image
    print("  Step 2: Returning image from tool as multimodal content...")

    img_b64 = _img_b64()

    # Build the continuation: assistant message with tool call + tool result with image
    messages = [
        {"role": "system", "content": "You are a helpful assistant that can see images. When you receive an image from a tool, describe what you see in detail."},
        {"role": "user", "content": "Please capture a screenshot of the desktop and tell me what you see."},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": "capture_screenshot",
                        "arguments": "{}",
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": tc.id,
            "content": [
                {"type": "text", "text": "Screenshot captured successfully. Here is the image:"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
            ],
        },
    ]

    try:
        response2 = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0,
            stream=False,
        )

        choice2 = response2.choices[0]
        content2 = choice2.message.content
        reasoning2 = getattr(choice2.message, "reasoning_content", None)

        if reasoning2:
            print(f"  [REASONING] {reasoning2[:200]}{'...' if len(reasoning2) > 200 else ''}")
        print(f"  [CONTENT] Answer: {content2[:400] if content2 else '(none)'}")

        if content2:
            _pass("LLM analyzed the tool-returned image")
            lower = content2.lower()
            if any(c in lower for c in ["red", "blue", "gradient", "color", "image"]):
                _pass("LLM understood the image content from tool response")
            else:
                _fail("LLM response doesn't indicate image understanding")
        else:
            _fail("No content in response")

        return bool(content2)

    except Exception as exc:
        print(f"  [ERROR] Exception: {exc}")
        # If multimodal tool response fails, try plain text fallback
        print("  [WARN] Multimodal tool response may not be supported. Trying text-only fallback...")

        messages[-1] = {
            "role": "tool",
            "tool_call_id": tc.id,
            "content": f"Screenshot captured. The image is a 200x150 pixel PNG showing a smooth horizontal gradient from red on the left to blue on the right, with a slight green tint increasing from top to bottom. [base64 image data: {img_b64[:100]}...]",
        }

        try:
            response3 = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0,
                stream=False,
            )
            content3 = response3.choices[0].message.content
            print(f"  [CONTENT] Fallback answer: {content3[:300] if content3 else '(none)'}")
            if content3:
                _pass("Fallback (text description) worked — LLM can process tool results")
                _fail("But multimodal image in tool response is NOT supported")
            return bool(content3)
        except Exception as exc2:
            _fail(f"Fallback also failed: {exc2}")
            return False


# ── Main ─────────────────────────────────────────────────────────────────────

ALL_TESTS = {
    1: test_1_plain_text,
    2: test_2_streaming,
    3: test_3_single_tool_call,
    4: test_4_parallel_tool_calls,
    5: test_5_image_understanding,
    6: test_6_tool_returned_image,
}


def main():
    print(f"[TOOL] Model:    {MODEL}")
    print(f"[API]  Base URL: {BASE_URL}")
    print(f"[API]  API Key:  {API_KEY[:8]}...{API_KEY[-4:]}")

    # Parse which tests to run
    if len(sys.argv) > 1:
        test_nums = [int(x) for x in sys.argv[1:]]
    else:
        test_nums = list(ALL_TESTS.keys())

    results = {}
    for num in test_nums:
        if num not in ALL_TESTS:
            print(f"\n[WARN] Unknown test number: {num}")
            continue
        try:
            t_start = time.monotonic()
            passed = ALL_TESTS[num]()
            elapsed = time.monotonic() - t_start
            results[num] = passed
            status = "[PASS] PASSED" if passed else "[FAIL] FAILED"
            print(f"\n  {status} (took {elapsed:.1f}s)")
        except Exception as exc:
            results[num] = False
            print(f"\n  [ERROR] CRASHED: {exc}")

    # Summary
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    for num, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} Test {num}: {ALL_TESTS[num].__doc__ or ALL_TESTS[num].__name__}")
    total = len(results)
    passed_count = sum(1 for v in results.values() if v)
    print(f"\n  {passed_count}/{total} tests passed")


if __name__ == "__main__":
    main()
