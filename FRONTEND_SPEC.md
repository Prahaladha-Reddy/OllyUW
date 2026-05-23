# OllyUW Frontend Specification

## Project Overview

**OllyUW** is an AI-powered underwriting copilot that helps underwriters review AI company risk. Users upload documents (PDFs, Word docs, spreadsheets, etc.), which are converted to markdown and organized into **Projects**. Within each project, users can have multiple **Conversations** with an AI agent that analyzes the documents and answers questions about AI agent liability, risk dimensions, and underwriting concerns.

## Current Architecture

- **Framework**: React 18 with Vite
- **Styling**: CSS (existing styles in `frontend/src/styles.css`)
- **Auth**: Supabase JS (`@supabase/supabase-js`) with email/password
- **Routing**: Custom client-side routing (no react-router)
- **State Management**: React hooks (useState, useContext if needed)

## Phase 1: Projects + File Upload UI

This document covers the frontend needed to support:
1. Creating projects (user-named containers for files)
2. Uploading files to projects
3. Browsing files by project
4. Managing projects
5. Setting up infrastructure for conversations (UI only, no chat logic yet)

---

## Routes & Navigation

### Route Structure

```
/                          → Home page (landing)
/review                    → Auth page (sign-in/sign-up)
/scoring                   → Scoring explainer page (existing)
/projects                  → Projects dashboard (NEW)
/projects/:projectId       → Project detail view (NEW)
/projects/:projectId/...   → Project management (NEW)
```

**Navigation Rules:**
- Unauthenticated users cannot access `/projects/*` — redirect to `/review`
- Authenticated users on `/review` redirect to `/projects`
- Header shows "Sign out" button when logged in (already implemented)

---

## Pages & Layouts

### 1. Projects Dashboard (`/projects`)

**Purpose**: Show all projects, allow creating new projects.

**Layout:**

```
┌─────────────────────────────────────────────────────────────────┐
│ OllyUW                                          [Sign out]       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SIDEBAR (see sidebar spec below)             │  MAIN CONTENT   │
│                                                │                 │
│  ├─ FILES                                      │  Projects       │
│  │  ├─ Company A Review                        │                 │
│  │  ├─ Company B Review                        │  [+ New Project]│
│  │                                             │                 │
│  ├─ PROJECTS                                   │  ┌────────────┐ │
│  │  ├─ Company A Review                        │  │ Company A  │ │
│  │  ├─ Company B Review                        │  │ Review     │ │
│  │                                             │  │ 3 files    │ │
│  │ [+ New Project]                             │  │ 2 conv.    │ │
│  │                                             │  └────────────┘ │
│  │                                             │                 │
│  │                                             │  ┌────────────┐ │
│  │                                             │  │ Company B  │ │
│  │                                             │  │ Assessment │ │
│  │                                             │  │ 2 files    │ │
│  │                                             │  │ 1 conv.    │ │
│  │                                             │  └────────────┘ │
│  │                                             │                 │
│  │                                             │  [+ New Project]│
│  │                                             │                 │
└─────────────────────────────────────────────────────────────────┘
```

**Components:**
- `ProjectsDashboard` (page)
  - Shows grid of project cards (or list)
  - Each card shows:
    - Project name
    - File count
    - Conversation count
    - Created date
    - Click to open project
  - "New Project" button (launches modal)

**States:**
- Loading (fetching projects)
- Empty (no projects yet)
- Loaded with projects
- Error (failed to fetch)

---

### 2. Project Detail View (`/projects/:projectId`)

**Purpose**: View/manage a single project — upload files, view files, manage conversations.

**Layout:**

```
┌─────────────────────────────────────────────────────────────────┐
│ OllyUW                                          [Sign out]       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SIDEBAR                                      │ PROJECT: Company A Review                 │
│  ├─ FILES                                     │                                            │
│  │  ├─ Company A Review [ACTIVE]              │ ┌──────────────────────────────────────┐ │
│  │  │  ├─ policy.pdf                          │ │ UPLOAD AREA (Drag & Drop)           │ │
│  │  │  ├─ contract.docx                       │ │                                      │ │
│  │  │  └─ financials.csv                      │ │ Drop files here or click to browse   │ │
│  │  ├─ Company B Review                       │ │                                      │ │
│  │  │  ├─ pitch.pdf                           │ │ Supported: PDF, DOCX, PPTX, CSV,   │ │
│  │  │  └─ team.docx                           │ │ JSON, YAML, TOML, TXT, MD           │ │
│  │  │                                          │ └──────────────────────────────────────┘ │
│  │ [+ New Project]                             │                                            │
│  │                                             │ FILES IN PROJECT                           │
│  ├─ PROJECTS                                   │ ┌──────────────────────────────────────┐ │
│  │  ├─ Company A Review [ACTIVE]              │ │ ✓ policy.pdf (5.2 MB)   [Delete]   │ │
│  │  │  ├─ 📄 Files (3)                         │ │ ✓ contract.docx (2.1 MB) [Delete]  │ │
│  │  │  ├─ 💬 Conversations (2)                 │ │ ✓ financials.csv (1.8 MB) [Delete] │ │
│  │  │  │  ├─ Liability analysis                │ │                                      │ │
│  │  │  │  └─ Data review                       │ │ Processing... (if any)               │ │
│  │  │  │                                        │ └──────────────────────────────────────┘ │
│  │  │  └─ [+ New Conversation]                │                                            │
│  │  │                                          │ CONVERSATIONS IN PROJECT                  │
│  │  ├─ Company B Review                       │ ┌──────────────────────────────────────┐ │
│  │  │  ├─ 📄 Files (2)                         │ │ "Liability analysis" [Click to open]│ │
│  │  │  └─ 💬 Conversations (1)                 │ │ Created: 2024-05-20 at 14:23        │ │
│  │  │                                          │ │                                      │ │
│  │  │                                          │ │ "Data handling review"               │ │
│  │  │                                          │ │ Created: 2024-05-20 at 15:45        │ │
│  │  │                                          │ │ [Click to open]                      │ │
│  │  │                                          │ │                                      │ │
│  │  │                                          │ │ [+ New Conversation]                 │ │
│  │  │                                          │ └──────────────────────────────────────┘ │
│  │                                             │                                            │
│  │                                             │ [← Back to Projects]                       │
│  │                                             │                                            │
└─────────────────────────────────────────────────────────────────┘
```

**Components:**
- `ProjectDetail` (page)
  - **Upload Section**
    - Drag-drop area
    - File input button
    - Shows file size limits (50 MB per file, or TBD)
    - Shows supported file types
  
  - **File List**
    - Shows all files in project
    - Each file shows:
      - Filename
      - File size
      - Upload status (✓ uploaded, ⏳ processing, ✗ error)
      - Delete button (if uploaded)
    - Empty state: "No files uploaded yet"
  
  - **Conversations List**
    - Shows all conversations in this project
    - Each conversation shows:
      - Conversation name/title
      - Created date
      - Click to open conversation
    - Empty state: "No conversations yet"
    - "New Conversation" button

**States:**
- Loading (fetching project data)
- Uploading (files being processed)
- Uploaded (files ready)
- Error (upload failed, show error message)
- Empty (no files/conversations yet)

**API Calls:**
- `GET /projects/:projectId` → get project details (name, files, conversations)
- `POST /projects/:projectId/files` → upload files
- `DELETE /projects/:projectId/files/:fileId` → delete file
- `POST /projects/:projectId/conversations` → create new conversation

---

### 3. Conversation View (`/projects/:projectId/conversations/:conversationId`)

**Purpose**: Chat interface where user can ask questions about project files.

**Layout:**

```
┌─────────────────────────────────────────────────────────────────┐
│ OllyUW > Projects > Company A > Liability analysis  [Sign out]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SIDEBAR                                      │ CONVERSATION                              │
│  ├─ FILES                                     │ "Liability analysis"                     │
│  │  ├─ Company A Review [ACTIVE]              │                                            │
│  │  │  ├─ policy.pdf                          │ ┌──────────────────────────────────────┐ │
│  │  │  ├─ contract.docx                       │ │ CHAT MESSAGES                        │ │
│  │  │  └─ financials.csv                      │ │                                      │ │
│  │  │                                          │ │ User: What are the main liability   │ │
│  │  ├─ PROJECTS                               │ │ risks?                               │ │
│  │  │  ├─ Company A Review [ACTIVE]           │ │                                      │ │
│  │  │  │  ├─ 📄 Files (3)                     │ │ Agent: Based on the documents...    │ │
│  │  │  │  ├─ 💬 Conversations (2)             │ │ [Citations: policy.pdf:5, contract] │ │
│  │  │  │  │  ├─ Liability analysis [ACTIVE]  │ │                                      │ │
│  │  │  │  │  └─ Data review                   │ │ User: What about data handling?     │ │
│  │  │  │  │                                    │ │                                      │ │
│  │  │  │  └─ [+ New Conversation]             │ │ Agent: The documents show...        │ │
│  │  │  │                                       │ │ [Citations: financials.csv:3]       │ │
│  │  │  │                                       │ │                                      │ │
│  │  │  └─ [Back to Project]                   │ │ [Scroll for more]                   │ │
│  │  │                                          │ └──────────────────────────────────────┘ │
│  │                                             │                                            │
│  │                                             │ UPLOAD FILES TO THIS CONVERSATION       │
│  │                                             │ ┌──────────────────────────────────────┐ │
│  │                                             │ │ [+ Upload files]                    │ │
│  │                                             │ │ (Adds to project, visible in all   │ │
│  │                                             │ │  conversations)                     │ │
│  │                                             │ └──────────────────────────────────────┘ │
│  │                                             │                                            │
│  │                                             │ MESSAGE INPUT                              │
│  │                                             │ ┌──────────────────────────────────────┐ │
│  │                                             │ │ Ask a question about the documents │ │
│  │                                             │ │ ________________________    [Send]   │ │
│  │                                             │ └──────────────────────────────────────┘ │
│  │                                             │                                            │
└─────────────────────────────────────────────────────────────────┘
```

**Note**: For Phase 1, the chat logic (agent integration) is not needed yet. We only need the UI structure and placeholder for messages. The backend will handle the actual agent responses in Phase 2.

**Components:**
- `ConversationView` (page)
  - **Header** - breadcrumb or title showing: Projects > ProjectName > ConversationName
  - **Messages Area**
    - Scrollable list of messages
    - Each message shows:
      - Who sent it (User or Agent)
      - Message text
      - Timestamp
      - Citations (if agent message) — links to source files/line numbers
  - **File Upload Section** (in conversation)
    - "Add files to conversation" button
    - Shows recently added files
  - **Message Input**
    - Text input field
    - Send button
    - Send on Enter key

**States:**
- Loading (fetching conversation)
- Empty (no messages yet, show prompt)
- Loaded with messages
- Sending (message being processed)
- Error

---

## Sidebar Component (Persistent)

The sidebar appears on all authenticated pages. It has two main sections: **FILES** and **PROJECTS**.

### Sidebar Layout

```
┌──────────────────────────┐
│ ═══ FILES               │
│ ┌──────────────────────┐│
│ │ Company A Review ▼   ││  ← Collapsible
│ │  • policy.pdf        ││
│ │  • contract.docx     ││
│ │  • financials.csv    ││
│ └──────────────────────┘│
│                          │
│ ┌──────────────────────┐│
│ │ Company B Review ▼   ││  ← Collapsible
│ │  • pitch.pdf         ││
│ └──────────────────────┘│
│                          │
│ ═══ PROJECTS            │
│ ┌──────────────────────┐│
│ │ ▶ Company A Review   ││  ← Expandable
│ │   ├─ 📄 Files (3)    ││
│ │   └─ 💬 Conv. (2)    ││
│ │    ├─ Liability...   ││
│ │    └─ Data review    ││
│ └──────────────────────┘│
│                          │
│ ┌──────────────────────┐│
│ │ ▶ Company B Review   ││  ← Expandable
│ │   ├─ 📄 Files (2)    ││
│ │   └─ 💬 Conv. (1)    ││
│ └──────────────────────┘│
│                          │
│ [+ New Project]          │
│                          │
└──────────────────────────┘
```

### Sidebar Components

**`Sidebar` (main component)**
- Fixed left sidebar (persistent across pages)
- Two sections: FILES and PROJECTS

**`FilesSection`**
- Header "FILES"
- List of projects (by name)
- Each project is collapsible
  - Click to expand/collapse
  - Shows files within
  - Each file is clickable (future: view file details)

**`ProjectsSection`**
- Header "PROJECTS"
- List of projects
- Each project is expandable/collapsible
  - Shows "📄 Files (count)"
  - Shows "💬 Conversations (count)"
  - Nested conversations list (collapsible)
    - Each conversation is clickable
    - Leads to `/projects/:projectId/conversations/:conversationId`
- "New Project" button at bottom

### Sidebar Interactions

**Files Section:**
- Click project name → expands/collapses file list
- Click file → (future: show file preview/details)
- Empty state: "No files yet"

**Projects Section:**
- Click project name → expands/collapses section
- Click "Files (N)" → goes to `/projects/:projectId` (project detail view)
- Click "Conversations (N)" → (maybe shows count, expands list)
- Click specific conversation → goes to `/projects/:projectId/conversations/:conversationId`
- "New Project" → opens "Create Project" modal
- "New Conversation" → opens "Create Conversation" modal (within expanded project)

---

## Modals & Forms

### 1. New Project Modal

**Triggered by:** "New Project" button in sidebar or projects dashboard

**Form:**
```
┌─────────────────────────────────┐
│ Create New Project              │
├─────────────────────────────────┤
│                                 │
│ Project Name                    │
│ [________________________]       │
│ (e.g., "Company A Underwriting")│
│                                 │
│ Description (optional)          │
│ [_______________________]       │
│ [_______________________]       │
│                                 │
│                  [Cancel] [Create] │
│                                 │
└─────────────────────────────────┘
```

**Fields:**
- Project name (required, max 100 chars, min 3 chars)
- Description (optional, max 500 chars)

**Validation:**
- Name is required
- Name is unique (for this user)
- Show error if project name already exists

**API Call:**
- `POST /projects` with `{ name, description }`
- Returns `{ project_id, name, ... }`
- On success: close modal, redirect to `/projects/:projectId`
- On error: show error message in modal

---

### 2. New Conversation Modal

**Triggered by:** "New Conversation" button in project detail or projects section

**Form:**
```
┌─────────────────────────────────┐
│ Start New Conversation          │
├─────────────────────────────────┤
│                                 │
│ Conversation Title              │
│ [________________________]       │
│ (e.g., "Liability Analysis")    │
│                                 │
│                  [Cancel] [Create] │
│                                 │
└─────────────────────────────────┘
```

**Fields:**
- Conversation title (required, max 100 chars, min 3 chars)

**API Call:**
- `POST /projects/:projectId/conversations` with `{ title }`
- Returns `{ conversation_id, title, created_at, ... }`
- On success: close modal, go to conversation view
- On error: show error message

---

### 3. Upload Files Modal / Drag-Drop Area

**Location:** Project detail page (main content area)

**Behavior:**
- **Drag-drop zone**: Accept files (PDF, DOCX, PPTX, CSV, JSON, YAML, TOML, TXT, MD)
- **Click to browse**: File input dialog
- **Show progress**: As files upload, show upload progress per file
- **Max file size**: 50 MB per file (enforced on backend)
- **Max total**: 100 MB per upload request (or TBD)

**States:**
- Idle: "Drop files here or click to browse"
- Dragging: Highlight zone (visual feedback)
- Uploading: Show progress bar per file
  ```
  policy.pdf: ████████░░ 80%
  contract.docx: ██████████ 100% ✓
  financials.csv: ⏳ Waiting...
  ```
- Complete: Show all files with checkmarks
- Error: Show error message for failed files

**API Call:**
- `POST /projects/:projectId/files` with `FormData(files)`
- Backend returns status for each file
- Frontend shows success/error per file

---

## State Management

Use React hooks (`useState`, `useContext` if needed).

**Global State (Context):**
```javascript
// AuthContext
- session: { user_id, email, ... }
- isLoading: boolean

// ProjectsContext (optional, if many pages need it)
- projects: Project[]
- currentProject: Project | null
- isLoading: boolean
- error: string | null

// ConversationsContext (optional)
- conversations: Conversation[]
- currentConversation: Conversation | null
```

**Local State (useState):**
- Form fields (project name, conversation title, etc.)
- Modal visibility (open/close)
- Upload progress
- File list
- Messages (in conversation view)

---

## API Integration

All API calls use the authenticated access token from Supabase session.

### API Endpoints

**Projects:**
```
GET /projects
  → { projects: [ { id, name, created_at, file_count, conversation_count }, ... ] }

POST /projects
  → { name, description? } 
  → { project_id, name, description, created_at }

GET /projects/:projectId
  → { project_id, name, description, files: [ {...}, ... ], conversations: [ {...}, ... ] }

DELETE /projects/:projectId
  → { success: true }
```

**Files:**
```
POST /projects/:projectId/files
  → FormData(files)
  → { submission_id, files: [ { filename, status, error? }, ... ] }

DELETE /projects/:projectId/files/:fileId
  → { success: true }
```

**Conversations:**
```
GET /projects/:projectId/conversations
  → { conversations: [ { id, title, created_at }, ... ] }

POST /projects/:projectId/conversations
  → { title }
  → { conversation_id, title, created_at }

GET /projects/:projectId/conversations/:conversationId
  → { conversation_id, title, messages: [ {...}, ... ] }

DELETE /projects/:projectId/conversations/:conversationId
  → { success: true }
```

**Messages (Phase 2, not needed for Phase 1):**
```
POST /projects/:projectId/conversations/:conversationId/messages
  → { text }
  → { message_id, text, role, timestamp, citations? }
```

---

## Styling & Design

### Design Tokens (from existing styles)

- **Dark theme**: Dark background (#1a1a1a or similar)
- **Accent color**: Green (#4ade80 or #22c55e)
- **Text colors**: Light text on dark
- **Borders**: Subtle, light gray
- **Shadows**: Minimal, for depth

### Components to Style

1. **Sidebar**
   - Fixed width (~250px)
   - Dark background
   - Collapsible sections
   - Nested indentation for projects/files/conversations
   - Hover effects on clickable items
   - Active state (highlight current project/conversation)

2. **Project Cards** (on dashboard)
   - Light card on dark background
   - Rounded corners
   - Hover effect (slight scale or shadow)
   - Shows: name, file count, conversation count, created date
   - Click to open

3. **Upload Area**
   - Dashed border or highlighted area
   - Drag-over state (visual feedback)
   - Icons (📄 or upload icon)

4. **File List**
   - Clean list format
   - Show file icon, name, size, status
   - Hover: show delete button
   - Status indicator: ✓ (done), ⏳ (processing), ✗ (error)

5. **Conversation Messages**
   - Alternating layout (user on right, agent on left)
   - Different background colors for user vs agent
   - Timestamp and citations
   - Code blocks for any markdown in messages

6. **Buttons**
   - Consistent with existing `.pill-button` style
   - Disabled state when processing
   - Loading indicators (spinner) when needed

---

## Loading & Error States

### Loading States

- **Page loading**: Show spinner in main content area
- **File uploading**: Show progress bar per file
- **Fetching projects**: Show skeleton cards or spinner
- **Sending message**: Show "Typing..." indicator or spinner

### Error States

- **Upload failed**: Show red error message, retry button
- **API error**: Show user-friendly error ("Something went wrong. Try again.")
- **File too large**: Show error message with size limit
- **Invalid file type**: Show which types are supported
- **Unauthenticated**: Redirect to `/review`

### Empty States

- **No projects**: Show "Create your first project" with CTA
- **No files in project**: Show "Upload files to get started"
- **No conversations**: Show "Start a conversation to analyze documents"
- **No messages**: Show "Ask a question to get started"

---

## Navigation & Routing

### Route Transitions

```
/                      (home page)
    ↓ [authenticated]
/projects              (projects dashboard)
    ↓ [click project card]
/projects/:projectId   (project detail)
    ↓ [click conversation]
/projects/:projectId/conversations/:conversationId
    ↓ [back button or sidebar]
/projects              (back to dashboard)
```

### Back Navigation

- Project detail: "[← Back to Projects]" button
- Conversation: "[← Back to Project]" button or sidebar click
- Use browser back button where applicable

---

## Future Considerations (Phase 2+)

These are NOT part of Phase 1, but keep in mind:

- **Chat**: Conversation messages, agent integration
- **File preview**: Click file to view markdown content
- **Search**: Search files or conversations
- **Sharing**: Share project with other users (collaboration)
- **Scoring UI**: Display 12 risk dimensions with scores
- **Report generation**: Export underwriting memo

---

## Summary: What to Build

### Phase 1 Deliverables

1. **Pages:**
   - Projects Dashboard (`/projects`)
   - Project Detail (`/projects/:projectId`)
   - Conversation View (`/projects/:projectId/conversations/:conversationId`) — UI only, no chat logic

2. **Sidebar:**
   - Persistent sidebar with FILES and PROJECTS sections
   - Collapsible/expandable navigation

3. **Modals:**
   - New Project modal
   - New Conversation modal

4. **Components:**
   - Project cards
   - File list with upload drag-drop
   - Conversation list
   - Breadcrumb/header navigation

5. **Features:**
   - Create projects
   - Upload files to projects
   - Create conversations within projects
   - Navigate between projects and conversations
   - Delete files/projects/conversations

6. **States:**
   - Loading, success, error, empty states for all features
   - Upload progress indicators
   - Responsive design (sidebar should be collapsible on mobile)

7. **Integration:**
   - Call backend APIs for all operations
   - Handle auth (redirect if no session)
   - Show error messages from API
   - Handle file upload validation

---

## File Structure (Suggested)

```
frontend/src/
├─ pages/
│  ├─ ProjectsDashboard.jsx
│  ├─ ProjectDetail.jsx
│  └─ ConversationView.jsx
├─ components/
│  ├─ Sidebar.jsx
│  ├─ FilesSection.jsx
│  ├─ ProjectsSection.jsx
│  ├─ ProjectCard.jsx
│  ├─ FileList.jsx
│  ├─ UploadArea.jsx
│  ├─ FileUpload.jsx
│  ├─ ConversationList.jsx
│  ├─ MessageList.jsx
│  ├─ MessageInput.jsx
│  └─ modals/
│     ├─ NewProjectModal.jsx
│     └─ NewConversationModal.jsx
├─ lib/
│  ├─ supabase.js (already exists)
│  └─ api.js (API helper functions)
├─ hooks/
│  ├─ useProjects.js
│  ├─ useConversations.js
│  └─ useFiles.js
└─ App.jsx (already exists)
```

---

## Key Notes for Development

1. **Reuse existing styles**: The CSS file already has `.pill-button`, `.auth-form`, etc. Build on those.
2. **Keep routing simple**: Use the existing `navigate()` function and route mapping.
3. **Handle auth**: Check `session` context to prevent unauthorized access.
4. **Error handling**: Always show user-friendly errors, not stack traces.
5. **Loading states**: Every async operation should have a loading state.
6. **Empty states**: Every section should have an empty state.
7. **API integration**: Helper functions in `lib/api.js` for cleaner components.

---

This spec is comprehensive enough for another agent to start building. Good luck!
