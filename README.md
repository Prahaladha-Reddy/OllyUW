# Olly — A Persistent AI Computer

Olly is a computing environment — real browser, real shell, real desktop, connected apps — where the AI agent carries its state across sessions. It knows your workflows, your preferences, your auth tokens, and your history from previous sessions. You do not re-explain yourself.

## Why This Exists

Every AI assistant today is stateless. Each session starts from zero: no memory of last week, no saved browser state, no learned workflows, no retained credentials. A capable system that forgets everything is not an assistant — it is a fast search engine you re-train every time you open it.

Kairos fixes that directly. Persistent conversation history. Compressed session recall. Durable user preferences and agent identity that survive restarts. OAuth tokens stored in Vault, not re-authorized every session. Browser state snapshotted and restored. Skills that accumulate as the agent learns your repeated workflows and writes reusable files for them. The delta between session one and session fifty is visible.
---

## Table of Contents

- [Why This Exists](#why-this-exists)
- [Architecture](#architecture)
  - [Persistence Model](#persistence-model)
  - [Memory Files](#memory-files)
  - [Self-Evolving Skills](#self-evolving-skills)
  - [Subagent Orchestration](#subagent-orchestration)
  - [Tool Access Per Agent Type](#tool-access-per-agent-type)
- [Capabilities](#capabilities)
  - [Real Browser Automation](#real-browser-automation)
  - [Shell and File System](#shell-and-file-system)
  - [Desktop Sandbox with Snapshot/Restore](#desktop-sandbox-with-snapshotrestore)
  - [Connected Apps via OAuth](#connected-apps-via-oauth)
  - [Semantic Tool Search](#semantic-tool-search)
  - [Cross-Session Memory and Identity](#cross-session-memory-and-identity)
- [Demo: 300 LinkedIn Job Applications in 20 Minutes for $0.50](#demo-300-linkedin-job-applications-in-20-minutes-for-050)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Observability](#observability)
- [Contributing / Status](#contributing--status)

---

## Architecture

### Persistence Model

Most agent frameworks are stateless by design — each session starts from a blank context window. Kairos maintains state across sessions through a two-layer memory system.

**Layer 1 — Exact history.** Every session writes a verbatim conversation log to `{sessionid}/agent_conv.json`. This is grep-able, diffable, and used to reconstruct precise context when needed.

**Layer 2 — Compressed recall.** Long sessions produce `{sessionid}/summary.md`, a condensed representation of what happened, what was decided, and what state the environment is in. On session start, the agent loads the summary rather than replaying the full log, keeping the context window lean while preserving continuity.

Two durable files sit above the session layer and persist indefinitely:

| File | Purpose |
|------|---------|
| `Memory.md` | User preferences, behavioral patterns, accumulated facts about the user's workflow |
| `Soul.md` | Agent identity, personality, and operating principles — stable across all sessions |

Together, these four artifacts mean the agent resumes where it left off rather than asking you to re-explain yourself.

---

### Memory Files

```
workspace/
├── {sessionid}/
│   ├── agent_conv.json   # Verbatim message history — exact, searchable
│   └── summary.md        # Compressed recall for long sessions
├── Memory.md             # Durable: user prefs + behavioral patterns
└── Soul.md               # Durable: agent identity + personality
```

- **`agent_conv.json`** — Full fidelity record. Used for auditing, debugging, and reconstructing context when the summary alone is insufficient.
- **`summary.md`** — Written at compaction boundaries. Captures decisions made, tasks completed, current environment state. Loaded preferentially on resume.
- **`Memory.md`** — Updated continuously as the agent learns about the user. Drives personalization without requiring re-explanation.
- **`Soul.md`** — Read-only by default during normal operation. Defines how the agent reasons, prioritizes, and handles ambiguity.

---

### Self-Evolving Skills

When a workflow is repeated across sessions, the agent extracts it into a reusable skill file stored in the workspace. Skills are loaded on demand via semantic search against a skill index — only matching skills are pulled into context, avoiding bloat from a growing library.

The agent's capability surface expands over time within its own workspace. A workflow automated once becomes a reusable tool for future sessions.

---

### Subagent Orchestration

Long-horizon tasks are broken into parallel workstreams. Each subagent runs in isolation with its own tool access:

```
User Prompt
     │
     ▼
┌─────────────────────────────────────────┐
│            Orchestrator Agent            │
│         (task decomposition)            │
└──┬──────┬──────┬──────┬────────────────┘
   │      │      │      │
   ▼      ▼      ▼      ▼
Browser  Shell   Web   File/App
Agent   Agent  Agent   Agent
(BrowserOS) (E2B) (search) (OAuth tools)
   │      │      │      │
   └──────┴──────┴──────┘
              │
        Redis Pub/Sub
         (inter-agent messaging)
              │
        FastAPI SSE
         (streaming output to client)
```

**Inter-agent messaging** uses Redis Pub/Sub. Agents publish results and status to named channels; the orchestrator subscribes and coordinates.

**Client streaming** uses FastAPI Server-Sent Events. Output streams to the frontend as agents complete work, rather than waiting for full task completion.

**Desktop state** is preserved via E2B sandbox snapshots. A browser session mid-task can be suspended and resumed without losing open tabs, scroll position, or filled forms.

---

### Tool Access Per Agent Type

| Agent | Primary Tools |
|-------|--------------|
| Browser | BrowserOS MCP — 40+ app integrations, click/fill/navigate, DOM access |
| Shell | E2B sandbox — full Linux shell, file system, process execution |
| Web | Web search + fetch — open-web retrieval |
| App | OAuth-connected integrations — Gmail, LinkedIn, GitHub, Slack, Notion, Drive, Sheets |

OAuth tokens are stored in Supabase Vault. The agent never handles raw credentials directly — authorization flows go through a first-party custody layer before tokens are vaulted.

---

## Capabilities

### Real Browser Automation

The agent drives a full Chromium browser via BrowserOS MCP — clicking, scrolling, filling forms, handling auth dialogs, navigating SPAs. The browser holds real sessions, cookies, and localStorage across runs. BrowserOS exposes 40+ app-specific action sets (LinkedIn, Gmail, Google Sheets, etc.) alongside low-level primitives like `click_at`, `fill`, `evaluate_script`, and `take_screenshot`.

### Shell and File System

The agent has persistent shell access inside an E2B sandbox. It can write and execute scripts, install packages, manipulate files, run long-running processes, and pipe output back into the conversation. The file system survives across sessions unless explicitly reset.

### Desktop Sandbox with Snapshot/Restore

E2B desktop snapshots capture the full state of the sandbox — open apps, file system, browser state, running processes. When a session resumes, the snapshot is restored and the agent continues where it left off.

### Connected Apps via OAuth

The agent has authenticated access to:

| App | What it can do |
|---|---|
| Gmail | Read, compose, send, label, search |
| LinkedIn | Browse jobs, fill Easy Apply forms, message connections |
| Google Sheets | Read and write cells, create sheets |
| Google Drive | Upload, download, organize files |
| GitHub | Read repos, open issues, comment on PRs |
| Slack | Send messages, read channels |
| Notion | Read and write pages and databases |

OAuth tokens are stored in Supabase Vault. Users authorize once through a first-party flow. The agent never sees raw credentials.

### Semantic Tool Search

The agent has access to a large tool registry but only loads what it needs. Tool schemas are deferred — the agent issues a semantic search query at runtime and fetches the matching tool definition on demand. This keeps the active context window lean even when the full tool surface is large.

### Cross-Session Memory and Identity

Four layers of persistence survive across sessions:

- `sessionid/agent_conv.json` — full conversation history, grep-able
- `sessionid/summary.md` — compressed recall for sessions that exceed context limits
- `Memory.md` — user preferences, working patterns, and behavioral context the agent has accumulated
- `Soul.md` — agent identity and operating principles, stable across all sessions

When a new session starts, the agent loads its soul, reads recent memory, and resumes with full context about who it is and who it is working with.

---

## Demo: 300 LinkedIn Job Applications in 20 Minutes for $0.50

### What it does

A single user prompt triggers 6 parallel browser subagents. Each subagent opens a LinkedIn session, searches for Easy Apply jobs matching the user's criteria, fills each application form, and submits. The agent skips jobs requiring external redirects, handles multi-step forms (cover letter, screening questions, resume upload), and tracks submission status.

Result: ~300 applications submitted in approximately 20 minutes at a total cost of roughly ₹40 / $0.50 in API and compute.

### What is happening under the hood

```
User prompt
    │
    ▼
Orchestrator agent
    ├── spawns 6 browser subagents (parallel)
    │       each subagent:
    │       ├── authenticates to LinkedIn via stored OAuth token
    │       ├── queries job listings (role, location, Easy Apply filter)
    │       ├── iterates listings → fill form fields → submit
    │       └── publishes completion events to Redis Pub/Sub
    │
    ├── FastAPI SSE stream → real-time progress to client
    └── Langfuse traces every subagent action for replay/debugging
```

Each subagent operates in an isolated BrowserOS page. Redis Pub/Sub coordinates deduplication — two agents will not apply to the same job posting. The orchestrator collects results and writes a summary back to the user's session memory.

### Running the demo

1. Authorize LinkedIn through the OAuth flow (one-time).
2. Start the FastAPI server and the Redis broker.
3. Send a prompt to the agent endpoint, e.g.:

```
Apply to software engineering roles in Bangalore with Easy Apply.
Prefer Series A–C startups. Skip anything requiring a cover letter longer than 250 words.
```

4. Watch the SSE stream for live application status. Final results land in the session summary.

This pattern generalizes to any workflow requiring parallel form submission or multi-site data entry — LinkedIn is one instance, not a special case.

---

## Tech Stack

| Component | Role |
|---|---|
| **Deepseek-v4-flash** | Core LLM powering the orchestrator and all subagents |
| **BrowserOS MCP** | Browser automation server exposing 40+ app integrations as MCP tools; drives real Chromium sessions |
| **E2B** | Cloud sandbox providing the persistent shell, filesystem, and desktop environment; snapshots preserve state across sessions |
| **Redis** | Pub/Sub backbone for inter-agent messaging; decouples parallel subagents from the orchestrator |
| **FastAPI** | HTTP API layer with Server-Sent Events (SSE) for streaming agent output to clients |
| **Supabase Vault** | Encrypted storage for OAuth tokens and secrets; tokens never touch application memory at rest |
| **Langfuse** | LLM observability — traces every agent call, tool invocation, and token cost |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Redis (local or hosted — [Upstash](https://upstash.com) works)
- An [E2B](https://e2b.dev) account with a desktop-capable sandbox template
- A [BrowserOS](https://browseros.com) MCP server running locally or remotely
- [Langfuse](https://langfuse.com) project (cloud or self-hosted)
- Supabase project with Vault enabled

### 1. Clone and install

```bash
git clone https://github.com/your-org/kairos.git
cd kairos
pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file at the project root:

```env
# E2B
E2B_API_KEY=e2b_...
E2B_TEMPLATE_ID=<your-desktop-template-id>

# BrowserOS MCP
BROWSEROS_MCP_URL=http://localhost:8931

# Redis
REDIS_URL=redis://localhost:6379

# Supabase
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Session config
SESSION_ID=<uuid>
MEMORY_DIR=./memory
```

### 3. Start Redis

```bash
redis-server
# or point REDIS_URL at an existing Upstash instance
```

### 4. Start BrowserOS MCP

Follow the [BrowserOS setup guide](https://browseros.com/docs) to launch the MCP server, then confirm it is reachable at the URL in `BROWSEROS_MCP_URL`.

### 5. Run the agent

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The FastAPI server exposes an SSE endpoint at `/stream` — connect a client there to receive streamed agent output in real time.

### 6. Resume a session

The agent automatically loads `memory/{SESSION_ID}/agent_conv.json` and `memory/{SESSION_ID}/summary.md` on startup. Set `SESSION_ID` to an existing session UUID to resume where it left off. A new UUID starts a fresh session while still inheriting `Memory.md` and `Soul.md`.

---

## Observability

**Langfuse tracing** — every LLM call, tool invocation, subagent spawn, and token count is recorded as a trace. Open the dashboard to inspect latency, cost per session, and individual tool call chains.

**E2B snapshot recovery** — the desktop sandbox state is periodically snapshotted via the E2B API. If the orchestrator crashes mid-task, restarting with the same `SESSION_ID` and snapshot ID restores the browser tabs, open files, and shell working directory to the last checkpoint.
