#!/usr/bin/env python3
"""
CodeTrace AI — Sandbox Runner

This is the ENTRYPOINT inside the Docker sandbox container.
It receives user code, executes it under sys.settrace() tracing,
and emits structured JSON trace data to stdout.

Usage (inside container):
    python /runner.py /tmp/exec/user_code.py /tmp/exec/stdin.txt

Arguments:
    1. Path to user's Python source file
    2. Path to stdin data file (optional)

Output (stdout):
    JSON trace result

Security context:
    - Runs as non-root 'sandbox' user
    - Container has no network access
    - CPU and memory limits enforced by Docker
    - Timeout enforced by the host process
"""

import json
import sys
from pathlib import Path

# Add app code to path (Dockerfile ENV also sets PYTHONPATH=/app)
sys.path.insert(0, "/app")

from tracing.tracer import PythonTracer


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "sandbox_error",
            "error": "Usage: runner.py <source_file> [stdin_file]",
        }))
        sys.exit(1)

    source_path = Path(sys.argv[1])
    stdin_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    if not source_path.exists():
        print(json.dumps({
            "status": "sandbox_error",
            "error": f"Source file not found: {source_path}",
        }))
        sys.exit(1)

    # Read stdin data if provided
    stdin_data = ""
    if stdin_path and stdin_path.exists():
        try:
            stdin_data = stdin_path.read_text(encoding="utf-8")
        except Exception as e:
            print(json.dumps({
                "status": "sandbox_error",
                "error": f"Failed to read stdin file: {e}",
            }))
            sys.exit(1)

    # Run the tracer
    try:
        tracer = PythonTracer(source_path, stdin_data=stdin_data)
        tracer.run()

        # Output the result as JSON to stdout
        result = tracer.to_dict()

        # Add analysis if there was an error
        if result.get("error") and result["status"] not in ("syntax_error",):
            # We import the analyzer here to avoid the dependency in the
            # tracing module itself. The analyzer modules are available
            # because the full /tracing directory is in PYTHONPATH...
            # actually, the analyzer is in backend/app/analysis/, not tracing/.
            # Skip analysis inside the sandbox for now; the backend will
            # run analysis after receiving the trace.
            pass

        print(json.dumps(result, default=str, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({
            "status": "sandbox_error",
            "error": f"Runner failed: {type(e).__name__}: {e}",
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
