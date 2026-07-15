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
- Docker Engine
- (Optional) OpenAI or Gemini API key for AI explanations

### Quick Start

```bash
# Clone the repository
git clone https://github.com/abhinanthkk/CodeTrace-AI.git
cd CodeTrace-AI

# Configure environment
cp .env.example .env
# Edit .env and add your API key (optional)

# Build the sandbox image
cd sandbox
docker build -t codetrace-sandbox:latest .
cd ..

# Start the backend
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

### Docker Setup

```bash
# Build and start everything
docker-compose up --build
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_PROVIDER` | No | `openai` | AI provider: `openai` or `gemini` |
| `AI_API_KEY` | No | — | API key for the chosen provider |
| `AI_MODEL` | No | `gpt-4o` | Model name for the provider |
| `SANDBOX_IMAGE` | No | `codetrace-sandbox:latest` | Docker image for execution |
| `EXECUTION_TIMEOUT` | No | `5` | Max execution time in seconds |
| `EXECUTION_MEMORY` | No | `128m` | Memory limit per execution |
| `EXECUTION_CPU` | No | `0.5` | CPU limit per execution |
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `8000` | Server port |
| `CORS_ORIGIN` | No | `http://localhost:5173` | Allowed frontend origin |

## API Documentation

### `GET /api/health`

Returns backend and sandbox readiness.

```json
{
  "status": "healthy",
  "sandbox_available": true,
  "ai_configured": false
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

## Security Limitations (MVP)

The Docker sandbox provides a meaningful security boundary over running
user code directly in the server process, but it is **not a fully secure
untrusted-code execution platform**.

- **Container escape**: While Docker + non-root user + no network + resource
  limits make escape significantly harder, container escape vulnerabilities
  exist. Do not expose this service to untrusted users on a shared host
  without additional hardening (gVisor, Firecracker, or a VM boundary).
- **Resource exhaustion**: The Docker daemon itself can be overwhelmed by
  many concurrent executions. The MVP does not include a queue or rate limiter.
- **Malicious output**: The tracing system serializes variable state to JSON.
  Extremely large or deeply nested objects could consume memory during
  serialization. The serializer implements depth and size limits to mitigate
  this.
- **Side channels**: `sys.settrace()` runs inside the sandbox container.
  Malicious code that patches the tracer or abuses `ctypes` could theoretically
  interfere with tracing, but cannot escape the container.

For a production deployment, consider:
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
