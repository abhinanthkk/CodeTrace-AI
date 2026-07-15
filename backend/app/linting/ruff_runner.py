"""
CodeTrace Live Fix — Ruff Runner

Runs Ruff as a subprocess against user-provided Python source code.
Never writes code into a shell command. Uses stdin for safety.

Ruff rule selection (pyproject.toml or CLI flags):
- F: Pyflakes (undefined names, unused imports, etc.)
- E/W: pycodestyle errors/warnings
- B: flake8-bugbear (likely bugs)
- UP: pyupgrade (modern Python idioms)
- SIM: flake8-simplify (simplification suggestions)

We prioritize F, B, E over W, UP, SIM for the live editor.
"""

import json
import logging
import shutil
import subprocess
import sys
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# Rules enabled for live linting — prioritize bugs and mistakes over style
RUFF_RULES = ["F", "E", "B", "W", "UP", "SIM"]

# Ruff timeout (seconds)
RUFF_TIMEOUT = 2


class RuffError(Exception):
    """Raised when Ruff itself fails (not when diagnostics are found)."""


def _find_ruff_binary() -> str:
    """
    Locate the ruff binary.
    Checks: venv bin next to python, then system PATH.
    """
    # Try ruff next to the current Python interpreter (works in venv)
    venv_ruff = (sys.executable).replace("python3", "ruff").replace("python", "ruff")
    if shutil.which(venv_ruff):
        return venv_ruff

    # Try system PATH
    system_ruff = shutil.which("ruff")
    if system_ruff:
        return system_ruff

    # Fallback: hope ruff is on PATH
    return "ruff"


def run_ruff(code: str, timeout: int = RUFF_TIMEOUT) -> list[dict[str, Any]]:
    """
    Run Ruff against Python source code via stdin.

    Args:
        code: Python source code to lint.
        timeout: Maximum seconds to wait for Ruff.

    Returns:
        List of raw Ruff diagnostic dicts (JSON format).

    Raises:
        RuffError: If Ruff crashes, times out, or produces invalid output.
    """
    if not code.strip():
        return []

    try:
        proc = subprocess.run(
            [
                _find_ruff_binary(), "check",
                "--output-format", "json",
                "--stdin-filename", "main.py",
                "--select", ",".join(RUFF_RULES),
                "-",
            ],
            input=code,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise RuffError("Ruff is not installed. Run: pip install ruff")
    except subprocess.TimeoutExpired:
        raise RuffError(f"Ruff timed out after {timeout}s")

    # Ruff exit code 0 = no issues, 1 = issues found, 2 = error
    if proc.returncode == 2:
        stderr = proc.stderr.strip()
        # Ruff returns exit code 2 for invalid Python syntax too —
        # we still get diagnostics in that case, so try to parse
        logger.warning(f"Ruff exited with code 2: {stderr[:200]}")

    stdout = proc.stdout.strip()
    if not stdout:
        return []

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise RuffError(f"Invalid Ruff JSON output: {e}")


def run_ruff_safe(code: str) -> list[dict[str, Any]]:
    """
    Run Ruff but never raise — returns empty list on any failure.
    Use this for the API endpoint so Ruff never crashes FastAPI.
    """
    try:
        return run_ruff(code)
    except RuffError as e:
        logger.error(f"Ruff execution failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected Ruff error: {e}")
        return []


def check_ruff_available() -> bool:
    """Check if Ruff is installed and runnable."""
    try:
        subprocess.run(
            [_find_ruff_binary(), "--version"],
            capture_output=True,
            timeout=5,
        )
        return True
    except Exception:
        return False
