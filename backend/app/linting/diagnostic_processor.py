"""
CodeTrace Live Fix — Diagnostic Processor

Normalizes raw Ruff diagnostics into CodeTrace's internal format.
The frontend consumes ONLY CodeTrace's schema, never raw Ruff JSON.
"""

from typing import Any

# Severity mapping: Ruff severity → CodeTrace severity
_SEVERITY_MAP = {
    "error": "error",
    "warning": "warning",
    "info": "info",
}


def process_diagnostics(raw_diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert raw Ruff diagnostics into CodeTrace's normalized format.

    Each diagnostic:
    {
        "id": "unique-id",
        "code": "F821",
        "message": "Undefined name `nam`",
        "severity": "error",
        "line": 3,
        "column": 7,
        "end_line": 3,
        "end_column": 10,
        "source": "ruff",
        "fix_available": true,
        "fix_type": "quick" | null,
        "raw_fix": { ... } | null   # Ruff's fix data, if available
    }
    """
    processed = []
    for diag in raw_diagnostics:
        processed.append(_normalize_one(diag))
    return processed


def _normalize_one(diag: dict[str, Any]) -> dict[str, Any]:
    """Normalize a single Ruff diagnostic."""
    code = diag.get("code", "unknown")
    message = diag.get("message", "")
    location = diag.get("location", {})
    end_location = diag.get("end_location", {})
    fix_data = diag.get("fix")
    fix_applicability = diag.get("applicability")  # Ruff's fix safety label

    # Determine fix availability
    fix_available = fix_data is not None
    fix_type = None
    if fix_available and fix_applicability == "safe":
        fix_type = "quick"
    elif fix_available:
        fix_type = "manual"  # Ruff has a fix but it's not marked safe

    # Determine severity
    severity = "info"
    if code.startswith("F"):  # Pyflakes — likely bugs
        severity = "error"
    elif code.startswith("E"):  # pycodestyle errors
        severity = "error"
    elif code.startswith("B"):  # flake8-bugbear
        severity = "error"
    elif code.startswith("W"):  # pycodestyle warnings
        severity = "warning"
    elif code.startswith("UP"):  # pyupgrade
        severity = "info"
    elif code.startswith("SIM"):  # flake8-simplify
        severity = "info"

    # Generate a stable diagnostic ID
    diagnostic_id = f"{code}-{location.get('row', 0)}-{location.get('column', 0)}"

    processed = {
        "id": diagnostic_id,
        "code": code,
        "message": message,
        "severity": severity,
        "line": location.get("row", 0),
        "column": location.get("column", 0),
        "end_line": end_location.get("row", location.get("row", 0)),
        "end_column": end_location.get("column", location.get("column", 0)),
        "source": "ruff",
        "fix_available": fix_available,
        "fix_type": fix_type,
    }

    # Include Ruff's fix data if available (normalized)
    if fix_data:
        processed["raw_fix"] = {
            "message": fix_data.get("message", ""),
            "applicability": fix_applicability,
            "edits": _normalize_fix_edits(fix_data.get("edits", [])),
        }

    return processed


def _normalize_fix_edits(edits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize Ruff fix edits into CodeTrace's edit format."""
    normalized = []
    for edit in edits:
        location = edit.get("location", {})
        end_location = edit.get("end_location", {})
        normalized.append({
            "start_line": location.get("row", 0),
            "start_column": location.get("column", 0),
            "end_line": end_location.get("row", location.get("row", 0)),
            "end_column": end_location.get("column", 255),
            "replacement": edit.get("content", ""),
        })
    return normalized


def filter_by_severity(
    diagnostics: list[dict[str, Any]],
    min_severity: str = "info",
) -> list[dict[str, Any]]:
    """Filter diagnostics to a minimum severity level."""
    levels = {"error": 0, "warning": 1, "info": 2}
    min_level = levels.get(min_severity, 2)
    return [d for d in diagnostics if levels.get(d.get("severity", "info"), 2) <= min_level]
