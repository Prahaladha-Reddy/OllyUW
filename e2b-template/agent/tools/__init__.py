"""
Tool dispatcher — async entry point for all tool execution.

Core tools (always in LLM context — 10 total):
  read_file, write_file, apply_unified_patch, run_shell, todo,
  use_skill, delegate, tool_search, tool_describe, tool_call

Deferred tools (behind the bridge — discovered via tool_search):
  list_directory, find_files, search_files, get_file_outline,
  move_file, delete_file, update_memory, append_memory,
  update_soul, read_session_summary, web_search, web_research
"""
from __future__ import annotations

import asyncio
from typing import Any

from agent.tools.bridge import tool_call as _bridge_tool_call
from agent.tools.bridge import tool_describe, tool_search
from agent.tools.file_ops import (
    apply_unified_patch,
    delete_file,
    find_files,
    get_file_outline,
    list_directory,
    move_file,
    read_file,
    search_files,
    write_file,
)
from agent.tools.memory_tools import (
    append_memory,
    read_session_summary,
    update_memory,
    update_soul,
)
from agent.tools.registry import ToolEntry, get_registry
from agent.tools.shell import run_shell
from agent.tools.todo import todo


# ── deferred tool registration ────────────────────────────────────────────────

def _schema(name: str, description: str, props: list[tuple]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    p: {"type": t, "description": d}
                    for p, t, d in props
                },
            },
        },
    }


def _web_search(query: str, max_results: int = 5) -> str:
    from agent.web.parallel_client import web_search
    return web_search(query, max_results=max_results)


def _web_research(question: str, timeout: int = 90) -> str:
    from agent.web.parallel_client import web_research
    return web_research(question, timeout=timeout)


def _install_skill(name_or_url: str) -> str:
    from agent.skills.installer import install_skill
    return install_skill(name_or_url)


def _init_registry() -> None:
    get_registry().register_many([
        ToolEntry(
            name="list_directory",
            description="List files and folders in a directory. recursive=True shows a tree view.",
            tags=["file", "list", "ls", "dir", "tree"],
            schema=_schema("list_directory", "List directory contents",
                [("path", "string", "Directory path (default '.')"),
                 ("recursive", "boolean", "Show recursive tree view")]),
            handler=list_directory,
        ),
        ToolEntry(
            name="find_files",
            description="Find files matching a glob pattern in the workspace. Supports ** for recursive search.",
            tags=["file", "glob", "find", "pattern"],
            schema=_schema("find_files", "Glob search for files",
                [("pattern", "string", "Glob pattern e.g. '**/*.py'"),
                 ("path", "string", "Base directory (default workspace root)")]),
            handler=find_files,
        ),
        ToolEntry(
            name="search_files",
            description="Search file contents with a regex pattern. Returns filename:line:content matches.",
            tags=["grep", "search", "regex", "content", "find"],
            schema=_schema("search_files", "Regex search in file contents",
                [("pattern", "string", "Regex pattern"),
                 ("path", "string", "Directory to search (default workspace root)"),
                 ("file_glob", "string", "Restrict to files matching this glob e.g. '*.py'")]),
            handler=search_files,
        ),
        ToolEntry(
            name="get_file_outline",
            description="Token-efficient file outline: class/function names and line numbers only — no content.",
            tags=["outline", "structure", "ast", "functions", "classes", "overview"],
            schema=_schema("get_file_outline", "Get file structure outline",
                [("path", "string", "File path relative to workspace")]),
            handler=get_file_outline,
        ),
        ToolEntry(
            name="move_file",
            description="Move or rename a file or directory within the workspace.",
            tags=["move", "rename", "file"],
            schema=_schema("move_file", "Move or rename a file",
                [("src", "string", "Source path"),
                 ("dst", "string", "Destination path")]),
            handler=move_file,
        ),
        ToolEntry(
            name="delete_file",
            description="Delete a file or directory from the workspace.",
            tags=["delete", "remove", "rm", "file"],
            schema=_schema("delete_file", "Delete a file or directory",
                [("path", "string", "Path to delete")]),
            handler=delete_file,
        ),
        ToolEntry(
            name="update_memory",
            description="Overwrite memory.md with new content. Saves facts about the user, preferences, project context for future sessions.",
            tags=["memory", "remember", "save", "persist", "user"],
            schema=_schema("update_memory", "Overwrite /home/user/memory.md",
                [("content", "string", "Full markdown content")]),
            handler=update_memory,
        ),
        ToolEntry(
            name="append_memory",
            description="Append a new section to memory.md without overwriting existing content.",
            tags=["memory", "remember", "append", "add", "note"],
            schema=_schema("append_memory", "Append section to memory.md",
                [("section", "string", "Section heading"),
                 ("content", "string", "Content to add")]),
            handler=append_memory,
        ),
        ToolEntry(
            name="update_soul",
            description="Overwrite soul.md with new content. Controls personality, communication style, and behavior preferences.",
            tags=["soul", "personality", "style", "behavior", "preferences"],
            schema=_schema("update_soul", "Overwrite /home/user/soul.md",
                [("content", "string", "Full markdown content")]),
            handler=update_soul,
        ),
        ToolEntry(
            name="read_session_summary",
            description="Read the summary or chat history from a previous session. Use for cross-session context.",
            tags=["session", "history", "summary", "previous", "context"],
            schema=_schema("read_session_summary", "Read a session summary or history",
                [("session_id", "string", "Session ID (empty = list all sessions)")]),
            handler=read_session_summary,
        ),
        ToolEntry(
            name="web_search",
            description="Quick web search. Returns relevant excerpts from top results. Good for facts, recent events, quick lookups.",
            tags=["web", "search", "internet", "google", "lookup"],
            schema=_schema("web_search", "Quick web search",
                [("query", "string", "Search query"),
                 ("max_results", "integer", "Max results (default 5)")]),
            handler=_web_search,
        ),
        ToolEntry(
            name="web_research",
            description="Deep web research with multi-source synthesis and citations. Slower (~30-90s) but comprehensive.",
            tags=["web", "research", "deep", "synthesize", "citations", "comprehensive"],
            schema=_schema("web_research", "Deep web research with synthesis",
                [("question", "string", "Research question"),
                 ("timeout", "integer", "Max seconds (default 90)")]),
            handler=_web_research,
        ),
        ToolEntry(
            name="install_skill",
            description="Install a new skill by name or URL. Skills are saved to the catalog and available immediately.",
            tags=["skill", "install", "add", "download"],
            schema=_schema("install_skill", "Install a skill from the registry or a URL",
                [("name_or_url", "string", "Skill name (looked up in registry) or direct URL to a .md file")]),
            handler=_install_skill,
        ),
    ])


_init_registry()


# ── core tool specs (always sent to LLM) ─────────────────────────────────────

CORE_TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a workspace file. Use start_line/end_line for large files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":       {"type": "string",  "description": "Path relative to workspace"},
                    "start_line": {"type": "integer", "description": "First line to read (0-based, default 0)"},
                    "end_line":   {"type": "integer", "description": "Last line exclusive (default EOF)"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write a complete file to the workspace. Creates parent dirs. Overwrites existing files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "Path relative to workspace"},
                    "content": {"type": "string", "description": "Full file contents"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_unified_patch",
            "description": (
                "Apply a unified diff patch to edit an existing file. "
                "Preferred over write_file for editing. "
                "Format: --- a/file  +++ b/file  @@ -N,N +N,N @@  context/-/+"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File to patch (relative to workspace)"},
                    "diff": {"type": "string", "description": "Unified diff string"},
                },
                "required": ["path", "diff"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command in the workspace directory. Returns stdout + stderr + exit code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string",  "description": "Shell command to run"},
                    "timeout": {"type": "integer", "description": "Max seconds (default 60)"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo",
            "description": "Persistent task list. Plan complex work before starting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "add", "check", "uncheck", "remove"],
                        "description": "Operation",
                    },
                    "text": {"type": "string",  "description": "Task text (required for 'add')"},
                    "id":   {"type": "integer", "description": "Task ID (required for check/uncheck/remove)"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "use_skill",
            "description": "Load a domain skill guide by name. Available skills are listed in the system prompt under 'Available Skills'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Skill name from the Available Skills list, or 'list' to enumerate"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delegate",
            "description": (
                "Spawn one or more subagents to run tasks in parallel. "
                "Each subagent has its own context window and tool set. "
                "Available types: 'browser' (BrowserOS + mimo vision), plus any YAML-defined agents. "
                "Pass only the minimum context each agent needs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "description": "Tasks to run (in parallel unless sequential=true)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "agent":         {"type": "string",  "description": "Agent type name (e.g. 'browser')"},
                                "goal":          {"type": "string",  "description": "What to accomplish"},
                                "context":       {"type": "object",  "description": "Minimal context the agent needs"},
                                "return_schema": {"type": "object",  "description": "Expected output structure"},
                                "sequential":    {"type": "boolean", "description": "If true, run after previous task (use when output feeds next task)"},
                            },
                            "required": ["agent", "goal"],
                        },
                    },
                },
                "required": ["tasks"],
            },
        },
    },
]

BRIDGE_TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "tool_search",
            "description": (
                "Search the extended tool catalog by natural language. "
                "Discovers tools not listed above — file utilities, web search, "
                "memory tools, Composio app integrations, and more."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query":  {"type": "string",  "description": "What you want to do"},
                    "top_k":  {"type": "integer", "description": "Max results (default 5)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_describe",
            "description": "Get the full parameter schema for any tool found via tool_search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Exact tool name from tool_search results"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tool_call",
            "description": "Execute any deferred tool by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Tool name"},
                    "args": {"type": "object", "description": "Arguments (see tool_describe for schema)"},
                },
                "required": ["name"],
            },
        },
    },
]

ALL_TOOL_SPECS: list[dict] = CORE_TOOL_SPECS + BRIDGE_TOOL_SPECS


# ── async dispatcher ──────────────────────────────────────────────────────────

async def dispatch(name: str, args: dict[str, Any]) -> str:
    """Route any tool call by name. Handles both core and bridge tools."""
    match name:
        # File ops — sync wrapped in thread
        case "read_file":
            return await asyncio.to_thread(read_file, **args)
        case "write_file":
            return await asyncio.to_thread(write_file, **args)
        case "apply_unified_patch":
            return await asyncio.to_thread(apply_unified_patch, **args)
        # Shell — natively async
        case "run_shell":
            return await run_shell(**args)
        # Misc sync tools
        case "todo":
            return await asyncio.to_thread(todo, **args)
        case "use_skill":
            return await asyncio.to_thread(_use_skill, **args)
        # Delegation — async, spawns subagents
        case "delegate":
            return await _delegate(**args)
        # Bridge tools
        case "tool_search":
            return await asyncio.to_thread(tool_search, **args)
        case "tool_describe":
            return await asyncio.to_thread(tool_describe, **args)
        case "tool_call":
            return await _bridge_tool_call(**args)
        case _:
            raise ValueError(
                f"unknown tool: {name!r}. "
                "Use tool_search to find deferred tools, then tool_call to execute them."
            )


def _use_skill(name: str) -> str:
    from agent.skills.loader import list_skills_index, load_skill
    if name == "list":
        return list_skills_index()
    body = load_skill(name)
    if body is None:
        return f"skill not found: {name!r}. Check 'Available Skills' in system prompt."
    return body


async def _delegate(tasks: list[dict]) -> str:
    from agent.subagents.runner import run_tasks
    return await run_tasks(tasks)
