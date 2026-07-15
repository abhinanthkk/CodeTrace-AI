# CodeTrace AI — Sandbox Runner
#
# This script is the ENTRYPOINT inside the Docker sandbox.
# It receives a path to user code and optional stdin data,
# executes the code under sys.settrace() tracing,
# and emits structured JSON trace output to stdout.
#
# Security: this runs inside an isolated container with:
#   - No network access
#   - CPU and memory limits
#   - Non-root user

import sys
import json


def main():
    """Run user code with tracing and emit JSON results."""
    # Stub — will be implemented in Phase 2 (tracer) + Phase 5 (sandbox)
    result = {"status": "ok", "message": "Sandbox runner placeholder"}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
