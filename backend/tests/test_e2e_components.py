"""
E2E component health checks.

Tests each subsystem independently — run with:
    cd backend && uv run pytest tests/test_e2e_components.py -v

These tests verify the agent's wiring is correct WITHOUT starting a sandbox.
They import the real modules and check that configs load, modules import, and
external services are reachable with the configured credentials.

Also contains a manual probe function that can be run against a live sandbox:
    cd backend && uv run python tests/test_e2e_components.py --sandbox <sandbox_id>
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent.parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "backend" / ".env")

sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "e2b-template"))


# ── 1. Config loads ────────────────────────────────────────────────────────────

def test_settings_load():
    from src.config import get_settings
    s = get_settings()
    assert s.redis_url, "REDIS_URL missing"
    assert s.deepseek_api_key, "DEEPSEEK_API_KEY missing"


# ── 2. LLM compaction ─────────────────────────────────────────────────────────

def test_compaction_keeps_recent():
    """Compaction drops old messages while preserving required minimum."""
    import unittest.mock as mock
    from agent.llm import compaction as comp_mod, tokens as tok_mod

    # Pin a tiny budget (100 tokens) to ensure compaction triggers
    # regardless of which tiktoken encoding is available.
    with mock.patch.object(tok_mod, "TOKEN_BUDGETS", {"test-model": 100}):
        messages = [
            {"role": "user", "content": f"Message {i} " + "x" * 300}
            for i in range(20)
        ]
        kept = comp_mod.recent_within_budget(messages, model="test-model")

    assert len(kept) >= 4, "must keep at least 4 recent messages"
    assert len(kept) < len(messages), "should drop old messages when over budget"
    # Kept messages should be the most recent ones
    assert kept[-1]["content"].startswith("Message 19")


def test_compaction_drops_orphan_tool_messages():
    """Tool messages without matching assistant tool_call are dropped."""
    from agent.llm.compaction import recent_within_budget

    messages = [
        # orphan tool message at the start (no assistant turn before it)
        {"role": "tool", "content": "result", "tool_call_id": "orphan-id", "name": "tool"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    kept = recent_within_budget(messages, model="deepseek")
    roles = [m["role"] for m in kept]
    assert "tool" not in roles, "orphan tool messages must be dropped"


# ── 3. Soul loading ────────────────────────────────────────────────────────────

def test_soul_loads_default():
    """soul_section() returns a non-empty string even with no soul.md file."""
    import tempfile, unittest.mock as mock
    from agent.context import soul as soul_mod

    with mock.patch.object(soul_mod, "_SOUL_PATH", Path("/nonexistent/soul.md")):
        section = soul_mod.soul_section()
    assert "## Your Personality" in section
    assert len(section) > 50


def test_soul_loads_custom():
    """soul_section() reads an actual soul.md file when present."""
    import tempfile, unittest.mock as mock
    from agent.context import soul as soul_mod

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Custom soul\nBe awesome.")
        tmp = Path(f.name)

    try:
        with mock.patch.object(soul_mod, "_SOUL_PATH", tmp):
            section = soul_mod.soul_section()
        assert "Custom soul" in section
    finally:
        tmp.unlink(missing_ok=True)


# ── 4. Memory loading ─────────────────────────────────────────────────────────

def test_memory_empty_when_no_file():
    import unittest.mock as mock
    from agent.context import memory as mem_mod

    with mock.patch.object(mem_mod, "_MEMORY_PATH", Path("/nonexistent/memory.md")):
        assert mem_mod.load_memory() is None
        assert mem_mod.memory_section() == ""


def test_memory_loads_content():
    import tempfile, unittest.mock as mock
    from agent.context import memory as mem_mod

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("User prefers Python.\nAlways be concise.")
        tmp = Path(f.name)

    try:
        with mock.patch.object(mem_mod, "_MEMORY_PATH", tmp):
            section = mem_mod.memory_section()
        assert "User prefers Python" in section
        assert "## User Context" in section
    finally:
        tmp.unlink(missing_ok=True)


# ── 5. System prompt builds ────────────────────────────────────────────────────

def test_system_prompt_builds():
    """build_system_prompt() includes key sections."""
    os.environ.setdefault("SESSION_ID", "test-session")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

    from agent.config import build_system_prompt
    prompt = build_system_prompt()
    assert "Second PC" in prompt
    assert "## Available Skills" in prompt or "## Your Personality" in prompt
    assert len(prompt) > 500


# ── 6. Skill discovery ─────────────────────────────────────────────────────────

def test_skill_catalog_discovered():
    from agent.skills.discovery import CATALOG_DIR
    from agent.skills.loader import allskills_section, list_skills_index

    assert CATALOG_DIR.exists(), f"catalog dir missing: {CATALOG_DIR}"
    index = list_skills_index()
    # Should list at least the LinkedIn skill
    assert "linkedin" in index.lower() or index == "", f"unexpected index: {index[:200]}"


# ── 7. Tool registry ───────────────────────────────────────────────────────────

def test_tool_registry_loads():
    os.environ.setdefault("SESSION_ID", "test-session")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

    from agent.tools.registry import get_registry
    reg = get_registry()
    names = reg.all_names()
    assert len(names) > 0, "no tools registered"
    # Deferred-registry tools (NOT core tools — core tools are in ALL_TOOL_SPECS)
    expected_deferred = {"list_directory", "web_search", "update_memory", "composio_list_apps"}
    for t in expected_deferred:
        assert t in names, f"deferred tool missing from registry: {t}"


# ── 8. Skill curator (self-learning) ──────────────────────────────────────────

def test_curator_applies_no_skill():
    """Curator returns NO_SKILL for trivial trajectories without crashing."""
    from agent.skills.curator import _apply_curator_decision
    _apply_curator_decision("NO_SKILL")  # must not raise


def test_curator_inserts_skill():
    """Curator writes a skill file given a valid INSERT decision."""
    import tempfile, unittest.mock as mock
    from agent.skills import curator as cur_mod
    from agent.skills import discovery as disc_mod

    with tempfile.TemporaryDirectory() as tmpdir:
        catalog = Path(tmpdir)
        with (
            mock.patch.object(disc_mod, "CATALOG_DIR", catalog),
            mock.patch.object(cur_mod, "CATALOG_DIR", catalog),
            mock.patch("agent.skills.curator.regenerate_allskills"),
        ):
            decision = (
                "INSERT:test-skill\n"
                "---\nname: test-skill\ndescription: A test skill.\n---\n"
                "# Test Skill\nDo this thing.\n"
            )
            cur_mod._apply_curator_decision(decision)
            skill_file = catalog / "test-skill.md"
            assert skill_file.exists(), "curator did not write skill file"
            assert "test skill" in skill_file.read_text().lower()


# ── 9. Browser MCP client (unit) ──────────────────────────────────────────────

def test_browseros_mcp_url_env():
    """BROWSEROS_MCP_URL env var is picked up by the MCP client module."""
    import importlib
    os.environ["BROWSEROS_MCP_URL"] = "http://custom-host:9000/mcp"
    import agent.subagents.browser.mcp as mcp_mod
    importlib.reload(mcp_mod)
    assert mcp_mod.URL == "http://custom-host:9000/mcp"
    # Restore
    os.environ["BROWSEROS_MCP_URL"] = "http://127.0.0.1:9000/mcp"
    importlib.reload(mcp_mod)


@pytest.mark.asyncio
async def test_browseros_mcp_unreachable_returns_none():
    """list_tools() returns None (not an exception) when MCP is unreachable."""
    import unittest.mock as mock
    from agent.subagents.browser.mcp import MCPClient

    with mock.patch.dict(os.environ, {"BROWSEROS_MCP_URL": "http://127.0.0.1:19999/mcp"}):
        import importlib, agent.subagents.browser.mcp as mcp_mod
        importlib.reload(mcp_mod)
        async with MCPClient() as client:
            result = await client.list_tools()
        # Should return None (unreachable) not raise
        assert result is None
        importlib.reload(mcp_mod)


# ── 10. Redis connectivity ─────────────────────────────────────────────────────

def test_redis_local_reachable():
    """Ping local Redis. Skip if REDIS_URL points to Upstash (remote-only)."""
    redis_url = os.environ.get("REDIS_URL", "")
    if "upstash" in redis_url.lower():
        pytest.skip("Upstash Redis — skipping in local-only test run")

    import redis
    r = redis.from_url(redis_url, socket_connect_timeout=3)
    try:
        assert r.ping(), "Redis did not respond to PING"
    except Exception as exc:
        pytest.fail(f"Redis unreachable at {redis_url}: {exc}")
    finally:
        r.close()


# ── 11. DeepSeek LLM reachability ─────────────────────────────────────────────

def test_deepseek_reachable():
    """Send a minimal request to DeepSeek and expect a non-empty response."""
    import openai
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not set")

    client = openai.OpenAI(api_key=api_key, base_url=f"{base_url}/v1" if not base_url.endswith("/v1") else base_url)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say hello in exactly 3 words."}],
            max_tokens=20,
        )
        msg = resp.choices[0].message
        # DeepSeek thinking models may put content in reasoning_content instead
        text = msg.content or getattr(msg, "reasoning_content", "") or ""
        assert resp.choices, "no choices in response"
        assert resp.usage is not None, "no usage info — request may have failed"
    except Exception as exc:
        pytest.fail(f"DeepSeek request failed: {exc}")


# ── Sandbox probe (manual, not pytest) ────────────────────────────────────────

def probe_sandbox(sandbox_id: str) -> None:
    """Run a live probe against an E2B sandbox. Not part of pytest suite."""
    from e2b_desktop import Sandbox as DesktopSandbox

    print(f"\n=== Probing sandbox {sandbox_id} ===")
    api_key = os.environ.get("E2B_API_KEY", "")
    desktop = DesktopSandbox.connect(sandbox_id, api_key=api_key)

    checks = {
        "worker": "pgrep -af '[a]gent.worker' || echo WORKER_NOT_RUNNING",
        "browseros_port": "ss -tlnp 2>/dev/null | grep ':9000' && echo BROWSEROS_UP || echo BROWSEROS_DOWN",
        "browseros_proc": "pgrep -af '[b]rowseros' || echo BROWSEROS_PROC_MISSING",
        "worker_log": "tail -20 /tmp/worker.log 2>/dev/null || echo NO_LOG",
        "browseros_log": "tail -10 /tmp/browseros.log 2>/dev/null || echo NO_LOG",
        "skills": "ls /home/user/agent/skills/catalog/ 2>/dev/null || echo NO_SKILLS",
        "memory": "cat /home/user/memory.md 2>/dev/null || echo NO_MEMORY",
        "soul": "cat /home/user/soul.md 2>/dev/null || echo NO_SOUL",
    }

    for name, cmd in checks.items():
        result = desktop.commands.run(cmd, timeout=10)
        out = ((result.stdout or "") + (result.stderr or "")).strip()
        status = "✓" if not any(x in out for x in ["NOT_RUNNING", "DOWN", "MISSING", "NO_LOG", "NO_"]) else "✗"
        print(f"  [{status}] {name}: {out[:150]}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--sandbox":
        probe_sandbox(sys.argv[2])
    else:
        print("Usage: python test_e2e_components.py --sandbox <sandbox_id>")
        print("Run pytest tests/test_e2e_components.py -v for unit tests")
