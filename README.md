# CodeTrace AI

> **"Why did my code fail?"** — answered with evidence, not guesswork.

## Problem

Developers waste hours debugging Python code by mentally simulating execution,
adding print statements, or copying errors into chatbots that hallucinate
variable states. Beginners especially struggle to understand *why* their loop
went out of bounds or *which* variable was `None` at the point of failure.

Existing tools either:
- Show raw stack traces with no execution history (CPython default)
- Require heavyweight IDE setup (PyCharm/VSCode debugger)
- Fabricate execution evidence (LLM-only debugging)

## Solution

CodeTrace AI is an **intelligent Python debugging and execution visualization
platform**. It actually runs your code in an isolated sandbox, traces every
line with `sys.settrace()`, captures real variable state at each step, performs
deterministic failure analysis, and uses AI only to *explain* the
evidence — never to invent it.

The standout feature is an **interactive visual execution timeline**:
click any step to see exactly what your code did, what variables changed,
and how it reached the failure point.

## Key Features

- **Real Runtime Tracing** — Uses Python's `sys.settrace()` to capture every
  line, function call, return, and exception with actual variable state.
- **Safe Sandbox Execution** — All user code runs inside an isolated Docker
  container with no network, CPU/memory limits, and a strict timeout.
- **Deterministic Failure Analysis** — Structured analyzers for IndexError,
  ZeroDivisionError, KeyError, NameError, and TypeError extract root-cause
  evidence with confidence scores. No LLM required for the diagnosis.
- **AI Explanation Layer** — Optional AI (OpenAI or Gemini) translates
  structured debugging evidence into beginner-friendly explanations.
  The app works fully without an API key.
- **Interactive Visual Timeline** — Click any step to highlight the
  corresponding source line in Monaco Editor and inspect variable state
  at that exact moment.
- **Dark-themed Debugging IDE** — Professional developer-tool interface
  with code editor, timeline, variable inspector, and output console.

## Architecture

```
User Browser
    ↓
React + Vite (Frontend)
    ↓  POST /api/execute
FastAPI (Backend)
    ↓
Execution Manager
    ↓  spawns container
Docker Sandbox (python:3.12-slim, no network)
    ↓  runs runner.py
Python Runtime Tracer (sys.settrace)
    ↓  captures events
Trace Processor + State Tracker
    ↓  structures & serializes
Failure Analyzer (deterministic)
    ↓  classifies error, extracts evidence
AI Explanation Engine (optional)
    ↓  generates human-readable explanation
Structured JSON Response
    ↓
Interactive React Timeline
```

### Layer Separation

| Layer | Responsibility | Depends On |
|-------|---------------|------------|
| **Execution** | Spawn Docker, run code, enforce limits | Docker |
| **Tracing** | `sys.settrace()` hooks, state snapshots, serialization | runner.py |
| **Analysis** | Classify errors, extract root-cause evidence | Trace data |
| **AI** | Translate evidence into explanations | Analysis result |
| **API** | Validate requests, orchestrate flow, return responses | All layers |
| **Presentation** | Monaco editor, timeline, variable inspector | API response |

## Execution Flow (Detailed)

1. User writes Python code in Monaco Editor, optionally provides stdin input.
2. Frontend sends `POST /api/execute` with `{code, input}`.
3. FastAPI validates payload, generates an execution ID.
4. Backend writes code + input to a temporary directory.
5. Docker container starts from `codetrace-sandbox:latest`:
   - `--network none` — no outbound connectivity
   - `--memory 128m --cpus 0.5` — resource limits
   - `--read-only` with a writable `/tmp`
   - Mounts the temp directory with user files
6. `runner.py` executes the user code under `sys.settrace()`.
7. The tracer captures: line events, function calls, returns, exceptions,
   local variable snapshots, and stdout/stderr output.
8. Trace processor deduplicates noise, attributes variable changes to the
   correct source lines, and serializes safe JSON representations.
9. If an exception occurred: the error classifier identifies the type,
   dispatches to the appropriate analyzer (e.g., IndexErrorAnalyzer),
   which inspects the trace to extract structured evidence.
10. If an AI provider is configured: the explanation service builds a strict
    prompt from the evidence and calls the LLM for a beginner-friendly
    explanation. Otherwise, a deterministic template is used.
11. The structured response (status, timeline, error, analysis, explanation)
    is returned to the frontend.
12. React renders the timeline. Clicking a step highlights the source line
    and updates the variable inspector.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Vite, Tailwind CSS, Monaco Editor, Axios |
| **Backend** | Python 3.12, FastAPI, Pydantic, Uvicorn |
| **Tracing** | `sys.settrace()`, Python frame objects, `traceback` |
| **Sandbox** | Docker, `python:3.12-slim`, network isolation |
| **AI** | Provider abstraction — OpenAI API or Gemini API |
| **No database** | MVP is stateless; execution history planned for later |

## Project Structure

```
codetrace/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── CodeEditor.jsx          # Monaco Editor wrapper
│   │   │   ├── InputPanel.jsx          # Stdin input field
│   │   │   ├── ExecutionTimeline.jsx   # Interactive step timeline
│   │   │   ├── VariableInspector.jsx   # Variable state at selected step
│   │   │   ├── OutputConsole.jsx       # Captured stdout/stderr
│   │   │   ├── ErrorCard.jsx           # Exception display
│   │   │   └── AIExplanation.jsx       # AI/deterministic explanation
│   │   ├── pages/
│   │   │   └── DebuggerPage.jsx        # Main debugger layout
│   │   ├── services/
│   │   │   └── api.js                  # Axios API client
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI app entry point
│   │   ├── config.py                   # Environment-based settings
│   │   ├── models/
│   │   │   ├── requests.py             # Pydantic request schemas
│   │   │   └── responses.py            # Pydantic response schemas
│   │   ├── api/
│   │   │   └── execute.py              # POST /api/execute, GET /api/health
│   │   ├── execution/
│   │   │   ├── executor.py             # Orchestrates a single execution
│   │   │   ├── sandbox.py              # Docker container management
│   │   │   └── execution_manager.py    # Temp files, limits, cleanup
│   │   ├── tracing/
│   │   │   ├── tracer.py               # sys.settrace() hook logic
│   │   │   ├── state_tracker.py        # Variable diff engine
│   │   │   ├── trace_processor.py      # Filter, deduplicate, attribute
│   │   │   └── serializer.py           # Safe JSON serialization
│   │   ├── analysis/
│   │   │   ├── analyzer.py             # Entry point — dispatches to analyzers
│   │   │   ├── error_classifier.py     # Maps exception types to analyzers
│   │   │   └── analyzers/
│   │   │       ├── index_error.py
│   │   │       ├── zero_division.py
│   │   │       ├── key_error.py
│   │   │       ├── name_error.py
│   │   │       └── type_error.py
│   │   └── ai/
│   │       ├── provider.py             # Abstract AI provider interface
│   │       ├── explanation_service.py  # Builds prompts, calls provider
│   │       └── prompts.py             # Prompt templates
│   ├── requirements.txt
│   └── tests/
│
├── sandbox/
│   ├── Dockerfile                      # python:3.12-slim, non-root user
│   └── runner.py                       # Entrypoint: loads & traces user code
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Local Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- (Optional) Docker Engine — for Docker sandbox mode (`EXECUTION_MODE=docker`)
- (Optional) OpenAI or Gemini API key for AI explanations

### Quick Start

```bash
# Clone the repository
git clone https://github.com/abhinanthkk/CodeTrace-AI.git
cd CodeTrace-AI

# Configure environment
cp .env.example .env
# Edit .env and add your API key (optional)

# Start the backend (subprocess mode — no Docker needed)
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server starts at `http://localhost:5173` and proxies
`/api` requests to the FastAPI backend at `http://localhost:8000`.

### Docker Setup (Optional)

```bash
# Build and start everything with Docker sandbox
docker-compose up --build
```

## Environment Variables

### Backend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EXECUTION_MODE` | Yes | `subprocess` | `subprocess` (default, all environments) or `docker` (local only) |
| `PORT` | No | `8000` | Server port (set by hosting platform) |
| `HOST` | No | `0.0.0.0` | Server host |
| `ALLOWED_ORIGINS` | Yes | `http://localhost:5173` | Comma-separated CORS origins |
| `AI_PROVIDER` | No | — | `openai` or `gemini` |
| `AI_API_KEY` | No | — | API key for the chosen provider |
| `AI_MODEL` | No | `gpt-4o` | Model name |
| `SANDBOX_IMAGE` | No | `codetrace-sandbox:latest` | Docker image (docker mode only) |
| `EXECUTION_TIMEOUT` | No | `5` | Max execution time in seconds |
| `EXECUTION_MEMORY` | No | `128m` | Memory limit (docker mode only) |
| `EXECUTION_CPU` | No | `0.5` | CPU limit (docker mode only) |
| `MAX_CODE_SIZE` | No | `65536` | Max code size in bytes |
| `MAX_INPUT_SIZE` | No | `65536` | Max stdin size in bytes |
| `MAX_OUTPUT_SIZE` | No | `262144` | Max output size in bytes |

### Frontend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | Yes | `http://localhost:8000/api` | Backend API base URL |

## Deployment

### Live Architecture

```
Cloudflare Pages                   Render (or Koyeb)
┌──────────────────┐              ┌─────────────────────────┐
│ React + Vite     │──HTTPS──────→│ FastAPI                  │
│ Monaco Editor    │              │ EXECUTION_MODE=subprocess│
│ Tailwind CSS     │              │                          │
│                  │              │ SubprocessExecutionBackend│
│ VITE_API_URL=    │              │  ↓ python3 subprocess    │
│  <backend-url>   │              │  ↓ sys.settrace()        │
└──────────────────┘              │  ↓ Analyzer → Explain    │
                                  └─────────────────────────┘
```

### Execution Modes

| Mode | Environment | How it works | Security |
|------|------------|-------------|----------|
| `docker` | Local dev | Docker container with `--network none`, `--read-only`, CPU/memory limits, non-root user | Container isolation |
| `subprocess` | Free cloud hosting | Separate Python process with `resource.setrlimit`, sanitized env, timeout | OS process boundary |

### Local Development (subprocess mode — recommended)

```bash
# 1. Start backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. Start frontend
cd frontend
npm install && npm run dev
```

The backend runs user code in isolated Python subprocesses. No Docker required.

### Local Development (Docker mode — optional)

```bash
# 1. Install docker Python package
pip install docker

# 2. Build sandbox image
docker build -f sandbox/Dockerfile -t codetrace-sandbox .

# 3. Start backend
cd backend
EXECUTION_MODE=docker uvicorn app.main:app --reload --port 8000

# 4. Start frontend
cd frontend
npm install && npm run dev
```

### Production Deployment (Free Tier)

#### Frontend → Cloudflare Pages

1. Push to GitHub
2. In Cloudflare Pages dashboard:
   - **Framework preset**: Vite
   - **Root directory**: `frontend`
   - **Build command**: `npm run build`
   - **Output directory**: `dist`
   - **Environment variable**: `VITE_API_URL` = your backend URL

#### Backend → Render

1. Push to GitHub
2. In Render dashboard, create a **New Web Service**:
   - **Repository**: your GitHub repo
   - **Root directory**: `backend`
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Set environment variables:
   - `EXECUTION_MODE=subprocess`
   - `ALLOWED_ORIGINS=https://codetrace-ai.pages.dev`
   - `PORT=8000` (Render sets `$PORT` automatically)
   - `AI_PROVIDER=gemini` (optional)
   - `AI_API_KEY=<your-key>` (optional)
4. Health check path: `/api/health`

Or deploy with Docker:
   - **Root directory**: (repo root)
   - **Dockerfile path**: `backend/Dockerfile`
   - Set same environment variables

### API Documentation

### `GET /api/health`

```json
{
  "status": "healthy",
  "sandbox_available": true,
  "ai_configured": false,
  "version": "0.1.0",
  "execution_mode": "subprocess"
}
```

### `POST /api/execute`

Execute Python code with runtime tracing.

**Request:**

```json
{
  "code": "arr = [10, 20, 30]\nfor i in range(4):\n    print(arr[i])",
  "input": ""
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `code` | string | Required, max 64 KB |
| `input` | string | Optional, max 64 KB |

**Response (success):**

```json
{
  "execution_id": "a1b2c3d4-...",
  "status": "success",
  "stdout": "10\n20\n30\n",
  "stderr": "",
  "timeline": [...],
  "error": null,
  "analysis": null,
  "explanation": null
}
```

**Response (runtime error):**

```json
{
  "execution_id": "a1b2c3d4-...",
  "status": "runtime_error",
  "stdout": "10\n20\n30\n",
  "stderr": "",
  "timeline": [
    {
      "step": 1,
      "event": "line",
      "line": 1,
      "function": "<module>",
      "changes": {
        "arr": {"type": "created", "value": [10, 20, 30]}
      },
      "variables": {"arr": [10, 20, 30]},
      "output": ""
    }
  ],
  "error": {
    "type": "IndexError",
    "message": "list index out of range",
    "line": 3,
    "function": "<module>"
  },
  "analysis": {
    "category": "index_out_of_range",
    "sequence_variable": "arr",
    "sequence_length": 3,
    "attempted_index": 3,
    "valid_index_range": "0 to 2",
    "confidence": 0.95
  },
  "explanation": {
    "summary": "Your loop tried to access arr[3] but arr only has 3 elements (indices 0-2).",
    "what_failed": "...",
    "why": "...",
    "execution_sequence": "...",
    "suggested_fix": "...",
    "corrected_code": "..."
  }
}
```

**Possible status values:**

| Status | Meaning |
|--------|---------|
| `success` | Code executed without errors |
| `runtime_error` | Exception raised during execution |
| `syntax_error` | Code failed to compile |
| `timeout` | Execution exceeded the time limit |
| `memory_limit` | Container hit the memory cap |
| `output_limit` | stdout/stderr exceeded size limits |
| `sandbox_error` | Docker or infrastructure failure |

## Security Limitations

### Docker Mode (`EXECUTION_MODE=docker`)

The Docker sandbox provides a meaningful security boundary, but is **not
a fully secure untrusted-code execution platform**.

- **Container escape**: Docker + non-root user + no network + resource limits
  make escape harder, but container escape vulnerabilities exist.
- **Resource exhaustion**: The Docker daemon can be overwhelmed by many
  concurrent executions. No queue or rate limiter in MVP.
- **Malicious output**: The serializer implements depth and size limits.

### Subprocess Mode (`EXECUTION_MODE=subprocess`)

The subprocess mode is a **portfolio demo fallback**. It runs user code
in a separate OS process — NOT in the FastAPI server process — but does
NOT provide the same isolation as Docker:

- **No network isolation**: Relies on platform network policies
- **No filesystem isolation**: Beyond the temp directory
- **No cgroup isolation**: Uses `resource.setrlimit` as best-effort on Linux
- **Environment sanitized**: API keys and secrets are stripped from the child
  process environment

**Subprocess mode is suitable for a controlled portfolio demonstration.**
It is not a hardened multi-tenant sandbox.

### Future Production Sandbox Architecture

For a production deployment supporting arbitrary user code:

- **gVisor (runsc)**: Drop-in Docker replacement with syscall filtering
- **Firecracker**: microVM per execution, true hardware-level isolation
- **Dedicated worker pool**: Per-execution VM/container with full teardown
- **Queue + rate limiting**: Prevent resource exhaustion
- **gRPC sandbox service**: Separate sandbox microservice on hardened hosts
- gVisor (runsc) as the container runtime
- A job queue with worker isolation (e.g., per-job VMs)
- Rate limiting and authentication
- Running the Docker daemon on a dedicated, hardened host

## Test Cases (Development)

These programs are used during development to validate each phase:

| # | Test | Expected |
|---|------|----------|
| 1 | `x=5; y=10; z=x+y; print(z)` | Success, output `15` |
| 2 | `arr=[10,20,30]; for i in range(4): print(arr[i])` | IndexError, i=3, len=3 |
| 3 | `x=10; y=0; result=x/y` | ZeroDivisionError, y=0 |
| 4 | `user={"name":"A"}; print(user["age"])` | KeyError, key="age" |
| 5 | `userName="A"; print(username)` | NameError, suggest `userName` |
| 6 | `age=20; message="Age:"+age` | TypeError, str+int |
| 7 | `name=input(); age=int(input()); ...` with stdin | Success with input |
| 8 | `if x>5\nprint(x)` (missing colon) | SyntaxError |
| 9 | `while True: pass` | Timeout |
| 10 | `nums=[1,2]; nums.append(3); nums.append(4)` | Mutable state tracked |

## Future Improvements

- **JavaScript and Java tracing** — extend the sandbox to other languages
- **Execution graph visualization** — D3/Canvas-based call graph and data flow
- **Function call stack visualization** — nested call hierarchy in the timeline
- **Time-travel debugging** — step backward through execution
- **Execution history** — store past runs (requires database)
- **Shareable debugging sessions** — permalink to a trace
- **GitHub integration** — trace code directly from PRs and issues
- **Automated test-case generation** — AI-suggested edge cases from your code
- **Multi-file project support** — trace modules, not just single scripts
