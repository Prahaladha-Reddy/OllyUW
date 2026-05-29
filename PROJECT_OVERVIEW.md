# OllyUW - AI Underwriting Agent

## What is this?

OllyUW is a **persistent second computer in the browser**. A user gets a real Linux desktop running in the cloud (hosted on E2B), and an AI agent worker living inside that same sandbox, all streamed to their browser via VNC.

Think of it like a remote desktop + a co-pilot AI that can see the desktop and execute tasks, all in one interface.

## Why?

**Traditional agents are stateless.** They start fresh each turn, can't maintain a workspace, can't see a real desktop, can't handle document uploads the way a human would (on a filesystem the agent can browse and reference).

**OllyUW is stateful.** The computer persists across sessions via snapshots. Files you upload stay there. The agent can see the desktop, read files from disk, create new ones. The workspace feels real because it is.

## Core Architecture

```
Browser
  ├─ Desktop iframe (streaming via noVNC)
  ├─ Chat panel (SSE for agent response)
  └─ File browser + upload zone

Backend (FastAPI)
  ├─ Computer lifecycle (start/pause/snapshot)
  ├─ Session management (chat threads)
  ├─ Workspace file sync
  └─ Redis pub/sub for agent events

E2B Sandbox (Linux VM in cloud)
  ├─ XFCE desktop (Xvfb + x11vnc + noVNC)
  ├─ Agent worker (Python loop reading from Redis)
  └─ /home/user/workspace/ (persistent via snapshots)
```

## Key Components

### 1. **The Desktop (iframe)**
- Streams a real XFCE Linux desktop to the browser
- User can interact: open terminal, navigate filesystem, run commands
- Lives in an E2B sandbox that can be paused/resumed
- Snapshots preserve state (all files, installed packages, agent state)

### 2. **The Chat (SSE stream)**
- User sends message → backend publishes to Redis stream inside sandbox
- Agent worker reads the message, processes it, emits events back on Redis
- Backend forwards events to browser as SSE: `status`, `tool_call`, `text_delta`, `final`
- When agent finishes, the response is saved to the database

### 3. **File Upload & Workspace**
- User sees a folder tree (from `GET /computer/workspace`)
- User picks a destination folder by clicking it
- User uploads files → they land in that folder inside the sandbox
- Files persist in snapshots
- Agent can read/write files in the workspace

### 4. **Sessions (Chat Threads)**
- Each session is an independent chat thread
- One active session at a time (the computer is handling one conversation)
- All sessions share the same computer/workspace/agent
- Session messages are saved to the database

## Data Flow: User Uploads a File

1. User is viewing the desktop and file browser side-by-side
2. User clicks on a folder in the file tree (e.g., "submissions/acme/")
3. User drags a file or clicks "Upload" → multipart POST with file + path
4. Backend writes file to sandbox workspace via E2B SDK
5. Backend takes a snapshot to preserve it
6. File is visible in the desktop immediately (it's real filesystem)
7. User can instruct the agent to read/process it

## Data Flow: User Sends a Message

1. User types in chat → `POST /sessions/{id}/messages { text, model }`
2. Backend saves message to DB, publishes to Redis stream `agent:{computer_id}:messages`
3. Agent worker reads from stream, calls LLM, runs tools
4. Agent publishes events: `status`, `tool_call`, `text_delta`, etc. to Redis channel
5. Backend SSE stream forwards them to browser in real-time
6. User sees streaming response in chat panel
7. When agent finishes, `final` event is published → backend saves full response to DB

## The Desktop Experience

- **Persistence:** Computer pauses when you close the browser. Next time you return, it resumes from the last snapshot. Files you uploaded are still there. The agent's memory (state saved to disk) is still there.
- **Real filesystem:** Everything the agent does with files is visible on the desktop. Open a terminal, run `ls`, see what the agent created. No virtual abstraction.
- **Snapshots:** Every significant action (pause, upload files, agent turn) creates a snapshot. So if the sandbox crashes, the latest snapshot is restored.

## UI Layout (Conceptual)

```
┌─────────────────────────────────────────┐
│ Header: Computer status, Session list   │
├──────────────────┬──────────────────────┤
│                  │                      │
│   Desktop        │    Chat Panel        │
│   (iframe)       │    (messages)        │
│   640x480        │                      │
│                  │  Upload zone         │
├──────────────────┼──────────────────────┤
│  Workspace Files │ (file browser below) │
│  (folder tree)   │                      │
│  click → select  │                      │
│  dest folder     │                      │
└──────────────────┴──────────────────────┘
```

The exact layout, colors, spacing, fonts — that's your design work.

## Core Endpoints You'll Call from Frontend

**Computer:**
- `POST /computer/runtime/start` — boot desktop
- `POST /computer/runtime/pause` — pause with snapshot
- `GET /computer` — current state (has desktop_url for iframe src)

**Sessions:**
- `POST /sessions` — create chat thread
- `POST /sessions/{id}/messages` — send message
- `GET /sessions/{id}/stream` — SSE for live response
- `GET /sessions/{id}/messages` — load history

**Workspace:**
- `GET /computer/workspace` — file tree
- `POST /computer/workspace/upload` — upload files to chosen folder

That's it. Everything else (auth, snapshots, agent internals) is backend detail.

## What Makes This Different

1. **Real desktop, not terminal UI** — user can see and interact with a graphical environment
2. **Persistent workspace** — files don't vanish, agent can maintain context
3. **Single computer, multiple sessions** — share the same sandbox/workspace across conversations
4. **Agent runs inside the same VM** — can see the desktop, access files directly, no network round-trip for file I/O
5. **Snapshots = time machine** — come back weeks later, everything is as you left it
