# OllyUW

OllyUW is an AI underwriting copilot for insurance products that cover AI agents.
It ingests messy AI-vendor submission packages, extracts risk signals, runs model
and agent evaluations, and helps produce citable underwriting analysis across
hallucination, bias, safety, autonomy, tool risk, HITL controls, and evidence
grounding.

The project is framed around Ollive's take-home assignment: compare an
open-source model path against a frontier model path on hallucination rate,
bias, and content safety. Instead of a generic chatbot benchmark, this repo
implements that comparison in the product domain Ollive cares about: underwriting
AI-agent liability risk.

## What This Builds

- A React underwriting workspace for projects, conversations, file upload, model
  selection, and risk/scoring views.
- A FastAPI backend for auth-aware project, file, conversation, and session APIs.
- An E2B sandboxed agent runtime that can process workspace files and stream
  results back through Redis.
- Modal deployment scripts for serving Gemma 4 through an OpenAI-compatible vLLM
  endpoint, with standard and TurboQuant variants.
- Evaluation runners for hallucination, bias, and content safety using both
  direct model calls and the full E2B agent harness.
- Langfuse observability for tracing LLM calls from the sandboxed agent runtime.

## Repository Layout

```text
backend/              FastAPI API, services, providers, migrations, tests
frontend/             Vite + React application
e2b-template/         E2B sandbox image and agent runtime code
infrastructure/modal/ Modal vLLM deployment and benchmark scripts
evals/                Evaluation datasets, harnesses, judges, and reports
tools/                Local utility scripts
```

## Architecture

The local web app has three main runtime pieces:

1. The frontend authenticates users with Supabase and calls the backend API.
2. The backend stores project/conversation/file metadata in Supabase, stores
   uploaded artifacts in Supabase Storage, and coordinates agent sessions.
3. The E2B agent worker receives workspace files, calls the selected model
   provider, performs tool-backed analysis, and publishes streamed events through
   Redis.

Model providers are configured behind OpenAI-compatible surfaces:

- `modal-standard`: Gemma 4 served by Modal/vLLM.
- `modal-turbo`: Gemma 4 served by Modal/vLLM with TurboQuant KV cache settings.
- `deepseek`: frontier-model comparison path.

## Prerequisites

- Python 3.12+
- `uv`
- Node.js and npm
- Supabase project credentials
- Redis URL
- E2B API key
- At least one model provider configured, usually DeepSeek for local testing or
  Modal URLs after deployment

## Environment

Create a root `.env` file. The backend loads the root `.env` and
`backend/.env`; root-level configuration is the simplest path for this repo.

Common backend variables:

```env
# Modal / open-source model serving
MODAL_STANDARD_BASE_URL=
MODAL_TURBO_BASE_URL=
MODAL_API_KEY=unused
MODAL_MODEL=

# DeepSeek / frontier model path
DEEPSEEK_API_KEY=<deepseek-api-key>
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash

# Agent transport
REDIS_URL=<upstash-or-redis-url>

# E2B sandbox runtime
E2B_API_KEY=
E2B_TEMPLATE_ID=
E2B_SANDBOX_TIMEOUT=

# Supabase auth, database, and storage
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_SECRET_KEY=
SUPABASE_BUCKET=

# Unstructured document parsing
UNSTRUCTURED_API_KEY=<unstructured-api-key>

# Agent memory and external research
MEM0_API_KEY=<mem0-api-key>
PARALLEL_API_KEY=<parallel-api-key>

# Langfuse LLM observability
LANGFUSE_PUBLIC_KEY=<langfuse-public-key>
LANGFUSE_SECRET_KEY=<langfuse-secret-key>
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com

# LangSmith tracing, kept in parallel with Langfuse
LANGSMITH_API_KEY=<langsmith-api-key>
LANGSMITH_BASE_URL=https://smith.langchain.com
LANGSMITH_TRACING=true

BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
```

Do not commit real API keys, Redis credentials, Supabase secret keys, or Langfuse
secret keys. The checked-in README intentionally uses placeholders for secrets.

Frontend variables belong in `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_SUPABASE_URL=
VITE_SUPABASE_PUBLISHABLE_KEY=
```

Langfuse is the primary LLM observability path for the sandboxed agent. When
`LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set, the backend forwards
them into each E2B worker session, and the agent records LLM traces through the
Langfuse LangChain callback and OpenAI wrapper. LangSmith tracing is still
available in parallel through the `LANGSMITH_*` variables.

## Backend

Install dependencies:

```powershell
uv sync --project backend --extra dev
```

Run the API:

```powershell
uv run --project backend python backend/main.py
```

The API defaults to `http://localhost:8000`.

Run backend tests:

```powershell
uv run --project backend pytest backend/tests
```

Smoke-test a provider:

```powershell
uv run --project backend python backend/tests/test_inference.py --provider deepseek
uv run --project backend python backend/tests/test_inference.py --provider modal-standard
uv run --project backend python backend/tests/test_inference.py --provider modal-turbo
```

## Frontend

Install dependencies:

```powershell
cd frontend
npm install
```

Run the Vite app:

```powershell
npm run dev
```

The frontend defaults to `http://127.0.0.1:5173`.

Build the frontend:

```powershell
npm run build
```

## E2B Agent Template

The E2B template preinstalls the agent runtime dependencies so sessions can
start quickly.

Build the template:

```powershell
uv run .\e2b-template\template.py
```

After a successful build, copy the printed template ID into:

```env
E2B_TEMPLATE_ID=
```

## Modal Model Serving

The Modal scripts serve Gemma 4 through vLLM with an OpenAI-compatible API.

Deploy standard Gemma:

```powershell
modal deploy infrastructure/modal/deploy_gemma_standard.py
```

Deploy the TurboQuant variant:

```powershell
modal deploy infrastructure/modal/deploy_gemma_turboquant.py
```

After deployment, set the resulting URLs in `.env`:

```env
MODAL_STANDARD_BASE_URL=
MODAL_TURBO_BASE_URL=
```

The inference smoke test appends `/v1` if it is not already present.

## Evaluations

The eval framework compares the assignment model paths on hallucination, bias,
and content safety. Reports are written to `evals/reports/`.

Build or refresh seed datasets:

```powershell
$env:PYTHONPATH = (Get-Location).Path
uv run --project backend python -m evals.datasets.build_seed_data
```

Run a no-API smoke test:

```powershell
$env:PYTHONPATH = (Get-Location).Path
uv run --project backend python -m evals.runners.all --harness direct --models mock
```

Run direct model evals:

```powershell
$env:PYTHONPATH = (Get-Location).Path
uv run --project backend python -m evals.runners.all --harness direct --models modal,deepseek --concurrency 10
```

Run the reportable E2B agent eval:

```powershell
$env:PYTHONPATH = (Get-Location).Path
uv run --project backend python -m evals.runners.all --harness e2b-agent --models modal,deepseek --concurrency 10
```
