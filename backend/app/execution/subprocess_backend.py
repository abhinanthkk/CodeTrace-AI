"""
CodeTrace AI — Subprocess Execution Backend

Runs user code in a separate Python process with resource limits.
This is the deployment fallback when Docker is unavailable.

SECURITY: This mode runs user code in a separate OS process, NOT inside
the FastAPI server process. However, it does NOT provide the same
isolation as Docker:
- No network isolation (relies on platform network policies)
- No filesystem isolation beyond the temp directory
- No memory/cpu cgroup isolation (uses rlimit as best-effort on Linux)

This mode is suitable for a CONTROLLED PORTFOLIO DEMONSTRATION.
It is NOT a hardened multi-tenant sandbox.
"""

import json
import logging
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from ..config import settings
from .backend import ExecutionBackend

logger = logging.getLogger(__name__)


class SubprocessExecutionBackend(ExecutionBackend):
    """
    Executes user code in a separate Python subprocess.

    Safety measures:
    - Runs under a separate Python process (sys.executable)
    - Execution timeout enforced via subprocess.run(timeout=...)
    - Environment sanitized (no API keys, no backend secrets)
    - Temp directory cleaned after execution
    - Output size limited
    - Resource limits applied where supported (Linux rlimit)

    Does NOT use exec() or eval() in the FastAPI process.
    """

    def __init__(self):
        self.timeout = settings.EXECUTION_TIMEOUT
        # Use the same Python interpreter that runs the backend
        self.python_bin = sys.executable

    @property
    def name(self) -> str:
        return "subprocess"

    def is_available(self) -> bool:
        """Subprocess backend is always available."""
        return True

    def execute(self, exec_dir: Path, code: str, stdin_data: str) -> dict[str, Any]:
        code_file = exec_dir / "user_code.py"
        stdin_file = exec_dir / "stdin.txt"

        if not code_file.exists():
            return self._error_result("Code file not found")

        # Build the trace runner command.
        # We run a small inline Python script that imports the tracer,
        # runs it against the user's code file, and prints JSON to stdout.
        runner_script = self._build_runner_script()

        # Sanitized environment — only pass what's needed for Python execution
        safe_env = self._build_safe_env()

        try:
            proc = subprocess.run(
                [self.python_bin, "-c", runner_script, str(code_file), str(stdin_file)],
                capture_output=True,
                text=True,
                timeout=self.timeout + 2,
                cwd=str(exec_dir),
                env=safe_env,
                # Apply resource limits before exec (Linux only)
                preexec_fn=self._apply_limits if platform.system() == "Linux" else None,
            )

            stdout = proc.stdout or ""
            stderr = proc.stderr or ""

            # Truncate output
            max_out = settings.MAX_OUTPUT_SIZE
            if len(stdout) > max_out:
                stdout = stdout[:max_out] + "\n...<output truncated>"
            if len(stderr) > max_out:
                stderr = stderr[:max_out] + "\n...<output truncated>"

            if proc.returncode == 0:
                return self._parse_output(stdout, stderr)
            else:
                # Try to parse even on non-zero exit (trace may have error info)
                result = self._parse_output(stdout, stderr)
                if result.get("status") == "sandbox_error":
                    result["stderr"] = stderr
                return result

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "stdout": "",
                "stderr": f"Execution timed out after {self.timeout}s",
                "timeline": [],
            }
        except Exception as e:
            logger.error(f"Subprocess backend failed: {e}")
            return self._error_result(f"Execution error: {e}")

    def _build_runner_script(self) -> str:
        """
        Build a self-contained Python script that runs the tracer.

        This script is passed to `python -c`. It imports PythonTracer
        from the backend's tracing package, runs the user's code, and
        prints the JSON result to stdout.
        """
        # We need to add the backend app directory to sys.path so the
        # subprocess can import the tracing package.
        backend_app = str(Path(__file__).resolve().parent.parent)

        return f'''
import json, sys
sys.path.insert(0, {backend_app!r})
from tracing.tracer import PythonTracer
from pathlib import Path

source = Path(sys.argv[1])
stdin_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
stdin_data = stdin_path.read_text(encoding="utf-8") if stdin_path and stdin_path.exists() else ""

try:
    tracer = PythonTracer(source, stdin_data=stdin_data)
    tracer.run()
    result = tracer.to_dict()
except Exception as e:
    result = {{
        "status": "sandbox_error",
        "stdout": "",
        "stderr": f"Tracer error: {{type(e).__name__}}: {{e}}",
        "timeline": [],
    }}

print(json.dumps(result, default=str, ensure_ascii=False))
'''

    def _build_safe_env(self) -> dict[str, str]:
        """
        Build a sanitized environment for the subprocess.

        ONLY passes through:
        - PATH (needed to find Python and system libs)
        - PYTHONPATH (needed for imports)
        - PYTHONIOENCODING (avoids encoding issues)
        - HOME, USER, LANG (basic runtime)

        Strips ALL application secrets:
        - GEMINI_API_KEY, OPENAI_API_KEY, AI_API_KEY
        - DATABASE_URL, SECRET_KEY, etc.
        """
        safe_keys = {
            "PATH", "PYTHONPATH", "PYTHONIOENCODING",
            "HOME", "USER", "LANG", "LC_ALL", "LC_CTYPE",
            "TMPDIR", "TEMP", "TMP",
        }

        safe_env = {}
        for key in safe_keys:
            val = os.environ.get(key)
            if val is not None:
                safe_env[key] = val

        # Ensure basic encoding is set
        safe_env.setdefault("PYTHONIOENCODING", "utf-8")

        return safe_env

    def _apply_limits(self) -> None:
        """
        Apply resource limits to the child process (Linux only).

        Uses resource.setrlimit as a best-effort defense:
        - RLIMIT_CPU:  soft limit on CPU seconds
        - RLIMIT_AS:   address space (virtual memory) limit
        - RLIMIT_FSIZE: max file size written
        - RLIMIT_NPROC: max child processes

        These are SOFT limits — the process can raise them if it has
        permission, but they provide a first line of defense against
        accidental resource exhaustion.
        """
        try:
            import resource

            cpu_limit = max(self.timeout * 2, 10)
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit + 5))

            mem_bytes = 128 * 1024 * 1024  # 128 MB
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes * 2))

            # Limit file creation size
            resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 16 * 1024 * 1024))

            # Limit child processes
            resource.setrlimit(resource.RLIMIT_NPROC, (16, 32))

        except (ImportError, ValueError, OSError) as e:
            # rlimit not available or setting failed — non-fatal
            logger.debug(f"rlimit not applied: {e}")

    def _parse_output(self, stdout: str, stderr: str) -> dict[str, Any]:
        """Parse JSON output from the tracer subprocess."""
        stdout = stdout.strip()

        # Try whole output as JSON
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in output
        try:
            start = stdout.rindex("{")
            return json.loads(stdout[start:])
        except (ValueError, json.JSONDecodeError):
            pass

        # Could not parse — return error
        return {
            "status": "sandbox_error",
            "stdout": "",
            "stderr": stderr or stdout[:1000] or "No output from tracer",
            "timeline": [],
        }

    def _error_result(self, message: str) -> dict[str, Any]:
        return {
            "status": "sandbox_error",
            "stdout": "",
            "stderr": message,
            "timeline": [],
        }
