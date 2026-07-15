"""
CodeTrace Live Fix — Diagnostic Scope Grouper

Groups related diagnostics into logical code blocks using Python AST.
For temporarily incomplete code, falls back to line-distance grouping.
"""

import ast
import logging
from typing import Any

logger = logging.getLogger(__name__)

LINE_PROXIMITY_THRESHOLD = 5  # lines


def group_diagnostics(
    diagnostics: list[dict[str, Any]],
    code: str,
) -> list[dict[str, Any]]:
    """
    Group related diagnostics by their containing scope.

    Each group:
    {
        "scope_type": "function" | "loop" | "conditional" | "module" | "proximity",
        "scope_name": "calculate_average" | "<module>" | ...,
        "start_line": 1,
        "end_line": 10,
        "diagnostic_ids": ["id1", "id2"],
        "diagnostics": [...],
        "confidence": 0.9
    }
    """
    if not diagnostics:
        return []

    # Try AST-based grouping
    try:
        tree = ast.parse(code)
        return _group_by_scope(diagnostics, tree)
    except SyntaxError:
        # Fallback: group by line proximity
        return _group_by_proximity(diagnostics)


def _group_by_scope(
    diagnostics: list[dict[str, Any]],
    tree: ast.AST,
) -> list[dict[str, Any]]:
    """Group diagnostics using AST scope information."""
    # Collect all scope nodes with their ranges
    scopes = _collect_scopes(tree)

    groups: dict[str, dict[str, Any]] = {}

    for diag in diagnostics:
        line = diag.get("line", 0)
        scope = _find_smallest_scope(line, scopes)

        key = f"{scope['type']}:{scope['name']}:{scope['start']}:{scope['end']}"
        if key not in groups:
            groups[key] = {
                "scope_type": scope["type"],
                "scope_name": scope["name"],
                "start_line": scope["start"],
                "end_line": scope["end"],
                "diagnostic_ids": [],
                "diagnostics": [],
                "confidence": 0.9,
            }

        groups[key]["diagnostic_ids"].append(diag.get("id", ""))
        groups[key]["diagnostics"].append(diag)

    return list(groups.values())


def _group_by_proximity(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Fallback: group diagnostics that are within LINE_PROXIMITY_THRESHOLD lines.
    Lower confidence than AST-based grouping.
    """
    if not diagnostics:
        return []

    sorted_diags = sorted(diagnostics, key=lambda d: d.get("line", 0))
    groups = []
    current_group = {
        "scope_type": "proximity",
        "scope_name": f"lines {sorted_diags[0].get('line', 0)}-{sorted_diags[0].get('line', 0)}",
        "start_line": sorted_diags[0].get("line", 0),
        "end_line": sorted_diags[0].get("line", 0),
        "diagnostic_ids": [],
        "diagnostics": [],
        "confidence": 0.5,
    }

    for diag in sorted_diags:
        line = diag.get("line", 0)
        if line - current_group["end_line"] <= LINE_PROXIMITY_THRESHOLD:
            # Same group
            current_group["end_line"] = max(current_group["end_line"], line)
            current_group["scope_name"] = f"lines {current_group['start_line']}-{current_group['end_line']}"
            current_group["diagnostic_ids"].append(diag.get("id", ""))
            current_group["diagnostics"].append(diag)
        else:
            # New group
            if current_group["diagnostics"]:
                groups.append(current_group)
            current_group = {
                "scope_type": "proximity",
                "scope_name": f"lines {line}-{line}",
                "start_line": line,
                "end_line": line,
                "diagnostic_ids": [diag.get("id", "")],
                "diagnostics": [diag],
                "confidence": 0.5,
            }

    if current_group["diagnostics"]:
        groups.append(current_group)

    return groups


def _collect_scopes(tree: ast.AST) -> list[dict[str, Any]]:
    """Walk the AST and collect all named scopes with line ranges."""
    scopes = []

    for node in ast.walk(tree):
        scope = None

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scope = {
                "type": "function",
                "name": node.name,
                "start": node.lineno,
                "end": node.end_lineno or node.lineno,
            }
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            scope = {
                "type": "loop",
                "name": f"for (line {node.lineno})",
                "start": node.lineno,
                "end": node.end_lineno or node.lineno,
            }
        elif isinstance(node, ast.While):
            scope = {
                "type": "loop",
                "name": f"while (line {node.lineno})",
                "start": node.lineno,
                "end": node.end_lineno or node.lineno,
            }
        elif isinstance(node, ast.If):
            scope = {
                "type": "conditional",
                "name": f"if (line {node.lineno})",
                "start": node.lineno,
                "end": node.end_lineno or node.lineno,
            }
        elif isinstance(node, ast.Try):
            scope = {
                "type": "try",
                "name": f"try (line {node.lineno})",
                "start": node.lineno,
                "end": node.end_lineno or node.lineno,
            }
        elif isinstance(node, ast.With):
            scope = {
                "type": "with",
                "name": f"with (line {node.lineno})",
                "start": node.lineno,
                "end": node.end_lineno or node.lineno,
            }
        elif isinstance(node, ast.ClassDef):
            scope = {
                "type": "class",
                "name": node.name,
                "start": node.lineno,
                "end": node.end_lineno or node.lineno,
            }

        if scope:
            scopes.append(scope)

    # Add module-level scope
    module_end = max((s["end"] for s in scopes), default=1)
    scopes.append({"type": "module", "name": "<module>", "start": 1, "end": module_end})

    return scopes


def _find_smallest_scope(line: int, scopes: list[dict[str, Any]]) -> dict[str, Any]:
    """Find the smallest scope that contains the given line."""
    containing = []
    for scope in scopes:
        if scope["start"] <= line <= scope["end"]:
            containing.append(scope)

    if not containing:
        return {"type": "module", "name": "<module>", "start": 1, "end": line}

    # Return the smallest (most specific) scope
    containing.sort(key=lambda s: s["end"] - s["start"])
    return containing[0]
