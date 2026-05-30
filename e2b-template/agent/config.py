from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# ── identity ──────────────────────────────────────────────────────────────────

SESSION_ID: str             = os.environ["SESSION_ID"]
OLLYUW_USER_ID: str         = os.environ.get("OLLYUW_USER_ID", "anon")
OLLYUW_PROJECT_ID: str      = os.environ.get("OLLYUW_PROJECT_ID", "default")
OLLYUW_CONVERSATION_ID: str = os.environ.get("OLLYUW_CONVERSATION_ID", SESSION_ID)


# ── redis ─────────────────────────────────────────────────────────────────────

REDIS_URL: str      = os.environ["REDIS_URL"]
INPUT_STREAM: str   = os.environ.get("INPUT_STREAM",   f"agent:{SESSION_ID}:messages")
OUTPUT_CHANNEL: str = os.environ.get("OUTPUT_CHANNEL", f"agent:{SESSION_ID}:chunks")
HEARTBEAT_KEY: str  = os.environ.get("HEARTBEAT_KEY",  f"agent:{SESSION_ID}:heartbeat")
ACTIVITY_KEY: str   = os.environ.get("ACTIVITY_KEY",   f"agent:{SESSION_ID}:activity")
ACTIVITY_TTL: int   = int(os.environ.get("ACTIVITY_TTL", "1200"))
CONSUMER_GROUP: str = "agent"
CONSUMER_NAME: str  = f"sandbox-{SESSION_ID}"


# ── paths ─────────────────────────────────────────────────────────────────────

WORKSPACE:  Path = Path(os.environ.get("WORKSPACE",        "/home/user/workspace")).resolve()
STATE_PATH: Path = Path(os.environ.get("AGENT_STATE_PATH", "/home/user/agent_state.json"))
SESSIONS_DIR: Path = Path(os.environ.get("SESSIONS_DIR", "/home/user/sessions"))


# ── model ─────────────────────────────────────────────────────────────────────

DEFAULT_MODEL:      str = "deepseek"
HEARTBEAT_INTERVAL: int = 10
MAX_STEPS:          int = 120
HISTORY_WINDOW:     int = 24
LOG_LEVEL:          str = os.environ.get("WORKER_LOG_LEVEL", "INFO")

# Depth tracking — passed into subagent runners to prevent recursion
AGENT_DEPTH: int = int(os.environ.get("AGENT_DEPTH", "0"))
MAX_DEPTH:   int = 1


# ── system prompt ─────────────────────────────────────────────────────────────

_BASE_PROMPT = """\
You are Second PC — a persistent AI computer. You run inside an E2B Linux sandbox \
and can do anything a person can do on a computer: write and run code, manage files, \
browse the web, connect to apps, automate workflows, research topics, and more.

Your workspace: /home/user/workspace
Your sessions:  /home/user/sessions/{session_id}/

## Core Principles

1. **Plan first.** For any non-trivial task, add todos before acting.
2. **Never read entire large files.** Use start_line/end_line, get_file_outline, or search_files to find what you need first.
3. **Parallelise.** Call independent tools in the SAME response so they run concurrently. Before any multi-step plan, ask: "can these run at the same time?"
4. **Prefer apply_unified_patch over write_file** for editing existing files. Patches are surgical; full rewrites lose context.
5. **Use tool_search** to discover extended tools (web, memory, file utilities, app integrations) before assuming a tool doesn't exist.
6. **Memory**: update memory.md when you learn something durable about the user or project. Soul.md controls your communication style.

## Tool Strategy

Core tools are always available (read_file, write_file, apply_unified_patch, run_shell, todo, use_skill, delegate).
Everything else — web search, file utilities, memory updates, Composio app tools — is behind the bridge:
  tool_search("what you want to do")  →  discover tool names
  tool_describe("tool_name")          →  see parameters
  tool_call("tool_name", {{...}})      →  execute

## Parallel Tool Calls

You MUST call independent tools in a single response. If you need to read 3 files,
send all 3 read_file calls at once. If you need to search and read, do both at once.
Do not make sequential calls when parallel calls work.

## Subagents (delegate tool)

Use delegate() for browser automation, app integrations, or parallelising heavy research.
- agent: "browser" → BrowserOS + MiMo vision model (for web tasks needing real navigation)
- agent: any YAML-defined agent name
- Subagents run in parallel by default. They have isolated contexts — pass ONLY what they need.
- Depth limit: 1. Subagents cannot spawn further subagents.
"""


def build_system_prompt() -> str:
    """Assemble the system prompt: base + skills index + soul.md + memory.md."""
    from agent.context.memory import memory_section
    from agent.context.soul import soul_section
    from agent.skills.loader import allskills_section

    parts = [_BASE_PROMPT.replace("{session_id}", SESSION_ID)]

    skills = allskills_section()
    if skills.strip():
        parts.append(f"\n---\n## Available Skills\n\n{skills}")

    parts.append(soul_section())

    mem = memory_section()
    if mem:
        parts.append(mem)

    return "\n".join(parts)


# Eagerly build once per worker start; imported by messages.py.
# Re-imported modules share the same object so this is effectively per-process.
SYSTEM_PROMPT: str = build_system_prompt()

# Tool specs — imported from tools module (avoids circular at import time).
# messages.py and streaming.py use this via lazy import.
def get_tool_specs() -> list[dict]:
    from agent.tools import ALL_TOOL_SPECS
    return ALL_TOOL_SPECS
