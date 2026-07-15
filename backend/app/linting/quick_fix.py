"""
CodeTrace Live Fix — Quick Fix Engine

Generates deterministic fixes for safe, obvious diagnostics.
No LLM required for these fixes.

Supported:
- Undefined name typo (F821): find similar known identifier
- Ruff safe fixes: pass through Ruff's own fix data
"""

import logging
from difflib import get_close_matches
from typing import Any

from .ruff_runner import run_ruff_safe
from .identifier_collector import collect_identifiers

logger = logging.getLogger(__name__)

TYPO_CONFIDENCE_THRESHOLD = 0.70


def generate_quick_fix(
    diagnostic: dict[str, Any],
    code: str,
) -> dict[str, Any] | None:
    """
    Generate a deterministic quick fix for a single diagnostic.

    Returns None if no deterministic fix can be generated.
    """
    diag_code = diagnostic.get("code", "")

    # F821 — Undefined name: try to find a similar known identifier
    if diag_code == "F821":
        return _fix_undefined_name(diagnostic, code)

    # Ruff safe fixes — pass through if available
    if diagnostic.get("fix_type") == "quick" and diagnostic.get("raw_fix"):
        return _fix_from_ruff(diagnostic)

    return None


def _fix_undefined_name(diagnostic: dict[str, Any], code: str) -> dict[str, Any] | None:
    """
    For F821 (undefined name), find a similar known identifier.

    Uses difflib.get_close_matches for string similarity.
    Only suggests a fix when confidence is high.
    """
    message = diagnostic.get("message", "")
    # Extract the undefined name from the message: "Undefined name `nam`"
    undefined_name = _extract_undefined_name(message)
    if not undefined_name:
        return None

    # Collect known identifiers from the source
    identifiers = collect_identifiers(code)
    candidates = list(identifiers["all"])

    if not candidates:
        return None

    # Find similar names
    matches = get_close_matches(undefined_name, candidates, n=3, cutoff=0.6)
    if not matches:
        return None

    best_match = matches[0]
    # Compute approximate confidence based on similarity
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, undefined_name, best_match).ratio()

    if similarity < TYPO_CONFIDENCE_THRESHOLD:
        return None

    line = diagnostic.get("line", 0)
    col = diagnostic.get("column", 0)
    end_col = diagnostic.get("end_column", col + len(undefined_name))

    return {
        "fix_type": "quick",
        "title": f"Replace `{undefined_name}` with `{best_match}`",
        "explanation": (
            f"`{undefined_name}` is undefined. `{best_match}` is defined nearby "
            f"and appears to be the intended variable."
        ),
        "edits": [
            {
                "start_line": line,
                "start_column": col,
                "end_line": line,
                "end_column": end_col,
                "replacement": best_match,
            }
        ],
        "confidence": round(similarity, 3),
        "requires_ai": False,
        "affected_lines": {"start": line, "end": line},
    }


def _fix_from_ruff(diagnostic: dict[str, Any]) -> dict[str, Any] | None:
    """
    Pass through a Ruff-provided safe fix.
    """
    raw_fix = diagnostic.get("raw_fix", {})
    edits = raw_fix.get("edits", [])
    if not edits:
        return None

    msg = raw_fix.get("message", "Apply fix")
    code = diagnostic.get("code", "")
    line = diagnostic.get("line", 0)

    return {
        "fix_type": "quick",
        "title": msg,
        "explanation": f"Ruff can safely fix {code}: {msg}",
        "edits": edits,
        "confidence": 0.99,
        "requires_ai": False,
        "affected_lines": {"start": line, "end": line},
    }


def _extract_undefined_name(message: str) -> str | None:
    """
    Extract the undefined variable name from Ruff's F821 message.

    Examples:
    - "Undefined name `nam`" → "nam"
    - "Undefined name `username`" → "username"
    """
    import re
    match = re.search(r"`([^`]+)`", message)
    if match:
        return match.group(1)
    return None


def classify_fix_type(diagnostics: list[dict[str, Any]], code: str) -> str:
    """
    Classify whether the selected diagnostics can be handled by Quick Fix
    or require AI Block Fix.

    Returns: "quick_fix" | "block_fix"
    """
    if len(diagnostics) == 0:
        return "quick_fix"

    # Single diagnostic with a quick fix available → quick
    if len(diagnostics) == 1:
        diag = diagnostics[0]
        quick = generate_quick_fix(diag, code)
        if quick and quick.get("confidence", 0) >= TYPO_CONFIDENCE_THRESHOLD:
            return "quick_fix"

    # Multiple related diagnostics → block fix
    return "block_fix"
