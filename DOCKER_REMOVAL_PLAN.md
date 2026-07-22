# Docker Removal Plan — Root Cause & Refactoring Report

---

## Root Cause

The deployed application on Render fails with:

```
Sandbox error:
Docker execution failed:
Docker is not available:
Error while fetching server API version:
FileNotFoundError(2, 'No such file or directory')
```

**Why it works locally but fails on Render:**

| Factor | Local Dev | Render (Free Tier) |
|--------|-----------|-------------------|
| Docker daemon | Available | Not available |
| `EXECUTION_MODE` default | `"docker"` | `"subprocess"` (user must set) |
| `docker` Python package | Installed via `requirements.txt` | Installed but can't connect |

The root cause is a chain of two issues:

1. **`backend/app/config.py:39`** — Default `EXECUTION_MODE` is `"docker"`. If the user forgets to set `EXECUTION_MODE=subprocess` on Render, the app tries to use Docker.
2. **`backend/app/execution/executor.py:20`** — `DockerExecutionBackend` is imported at module level. Even when the subprocess backend is selected, the `docker` Python package is still imported (via `docker_backend.py`).

The error message `"Docker is not available"` comes from `docker_backend.py:57`:
```python
raise RuntimeError(f"Docker is not available: {e}") from e
```

And `"Docker execution failed"` wraps it at `docker_backend.py:124`:
```python
raise RuntimeError(f"Docker execution failed: {e}") from e
```

This flows up through `executor.py:111-120` where `RuntimeError` is caught and returned as `"status": "sandbox_error"`, which then becomes a 500 response in `execute.py:56-60`.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/config.py` | Default `EXECUTION_MODE` changed from `"docker"` to `"subprocess"` |
| `backend/app/execution/executor.py` | `DockerExecutionBackend` import made lazy; graceful fallback with ImportError |
| `backend/app/execution/docker_backend.py` | `docker` import wrapped in try/except; `DOCKER_AVAILABLE` flag; type stubs for missing docker |
| `backend/app/execution/sandbox.py` | `docker` import wrapped in try/except (defensive, file is unused) |
| `backend/requirements.txt` | `docker` package removed from requirements (now optional) |
| `backend/app/api/execute.py` | Docstring updated to mention subprocess instead of Docker |
| `backend/app/execution/backend.py` | Docstring updated — subprocess is now primary |
| `.env.example` | Default changed to `EXECUTION_MODE=subprocess` |
| `docker-compose.yml` | Commented as optional; added `EXECUTION_MODE=docker` explicitly |
| `README.md` | Multiple sections updated to reflect subprocess as default |
| `deploy.sh` | Updated deployment instructions to use Python native runtime |
| `DOCKER_REMOVAL_PLAN.md` | This report |

---

## Code Changes

### 1. Default execution mode (`config.py`)

```python
# Before:
EXECUTION_MODE: str = os.getenv("EXECUTION_MODE", "docker")

# After:
EXECUTION_MODE: str = os.getenv("EXECUTION_MODE", "subprocess")
```

### 2. Lazy Docker import (`executor.py`)

```python
# Before:
from .docker_backend import DockerExecutionBackend  # module-level import

def _create_backend() -> ExecutionBackend:
    if mode == "docker":
        return DockerExecutionBackend()

# After:
# (no module-level import of DockerExecutionBackend)

def _create_backend() -> ExecutionBackend:
    if mode == "docker":
        try:
            from .docker_backend import DockerExecutionBackend
            return DockerExecutionBackend()
        except ImportError:
            logger.warning("Docker package not installed, falling back to subprocess")
            return SubprocessExecutionBackend()
```

### 3. Optional docker dependency (`docker_backend.py`)

```python
# Before:
import docker
from docker.errors import DockerException, ImageNotFound
from docker.models.containers import Container

# After:
try:
    import docker
    from docker.errors import DockerException, ImageNotFound
    from docker.models.containers import Container
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
```

### 4. Docker removed from requirements (`requirements.txt`)

```txt
# Removed:
docker>=7.0.0,<8.0.0

# Added as comment:
# Optional: Docker sandbox (local dev only)
# docker>=7.0.0,<8.0.0
```

---

## Security Considerations

The subprocess backend (`SubprocessExecutionBackend`) includes these security measures:

| Measure | Implementation |
|---------|---------------|
| **Separate process** | User code runs in a child Python process (`subprocess.run`) — never `exec()` or `eval()` in the server process |
| **Execution timeout** | `subprocess.run(timeout=...)` kills runaway code |
| **Resource limits** | `resource.setrlimit` on Linux: CPU time, virtual memory, file size, max child processes |
| **Sanitized environment** | Only `PATH`, `PYTHONPATH`, `PYTHONIOENCODING`, `HOME`, `USER`, `LANG` passed through — all secrets stripped |
| **Temp directory isolation** | Each execution gets a unique temp directory, cleaned up after completion |
| **Output size limit** | `MAX_OUTPUT_SIZE` (default 256KB) prevents memory exhaustion |

**Limitations vs Docker sandbox (accepted for free-tier deployment):**

- No network isolation (child process inherits host network)
- No filesystem isolation beyond temp directory
- No cgroup-based memory/CPU limits (uses best-effort `setrlimit`)
- Not hardened against a malicious attacker — suitable for portfolio demo

---

## Deployment Verification Steps

### 1. Verify locally (no Docker)

```bash
# Stop any running backend
# Ensure Docker is NOT running
cd backend && source .venv/bin/activate
python -c "from app.config import settings; print(settings.EXECUTION_MODE)"
# Should print: subprocess

# Start the backend
uvicorn app.main:app --reload --port 8000

# In another terminal, test execution
curl -s -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"code": "print(\"hello\")"}' | python3 -m json.tool
# Expected: status "success", stdout "hello\n"
```

### 2. Verify lint endpoint

```bash
curl -s -X POST http://localhost:8000/api/lint \
  -H "Content-Type: application/json" \
  -d '{"code": "x = 1\nprint(y)"}' | python3 -m json.tool
# Expected: status "success", diagnostics with F821, ruff_available true/false
```

### 3. Verify health endpoint

```bash
curl -s http://localhost:8000/api/health | python3 -m json.tool
# Expected: status "healthy", execution_mode "subprocess"
```

### 4. Verify Docker mode still works (if Docker is available)

```bash
EXECUTION_MODE=docker uvicorn app.main:app --reload --port 8001 &
curl -s http://localhost:8001/api/health | python3 -m json.tool
# Expected: execution_mode "docker", sandbox_available true/false
kill %1
```

### 5. Deploy to Render

```bash
# 1. Push to GitHub (triggers auto-deploy)
git push origin main

# 2. Verify in Render dashboard:
#    - Build logs show "pip install -r requirements.txt" (no docker package)
#    - Service starts successfully
#    - Health check passes at /api/health

# 3. Verify production endpoints:
curl https://codetrace-backend.onrender.com/api/health
curl -X POST https://codetrace-backend.onrender.com/api/execute \
  -H "Content-Type: application/json" \
  -d '{"code": "print(\"hello from Render\")"}'
```

---

## Future Improvements

| Improvement | Description | Priority |
|-------------|-------------|----------|
| **gVisor sandbox** | Replace Docker with `runsc` for stronger isolation on free-tier Linux hosts | Low |
| **Piston API** | Use [piston-api](https://github.com/engineer-man/piston) as an external execution service | Low |
| **Judge0** | Use [Judge0](https://judge0.com) as an external code execution API | Low |
| **Subprocess hardening** | Use `seccomp` or `landlock` for syscall filtering in subprocess | Medium |
