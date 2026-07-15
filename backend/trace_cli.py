#!/usr/bin/env python3
"""
CodeTrace AI — Standalone CLI Tracer

Usage:
    python trace_cli.py <python_file> [--stdin <text>] [--pretty]

Example:
    python trace_cli.py test_programs/success.py
    python trace_cli.py test_programs/index_error.py --pretty

This is the Phase 2 testing tool. It runs a Python file through the
sys.settrace() tracer and prints structured JSON to stdout. In later
phases this logic moves into the sandbox runner.py.
"""

import argparse
import sys
from pathlib import Path

# Add the backend to the path so we can import the tracer
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.tracing.tracer import PythonTracer


def main():
    parser = argparse.ArgumentParser(
        description="CodeTrace AI — Trace a Python program and print execution JSON.",
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Path to a Python file to trace",
    )
    parser.add_argument(
        "--stdin",
        type=str,
        default="",
        help="Standard input text to provide to the program",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output (default: compact)",
    )
    args = parser.parse_args()

    source_path = args.file.resolve()
    if not source_path.exists():
        print(f'{{"error": "File not found: {args.file}"}}')
        sys.exit(1)

    if not source_path.suffix == ".py":
        print(f'{{"error": "Not a Python file: {args.file}"}}')
        sys.exit(1)

    # Run the tracer
    tracer = PythonTracer(source_path, stdin_data=args.stdin)
    tracer.run()

    # Output the result
    indent = 2 if args.pretty else None
    import json
    print(json.dumps(tracer.to_dict(), indent=indent, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
