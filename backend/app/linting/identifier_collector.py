"""
CodeTrace Live Fix — Identifier Collector

Uses Python's AST to collect known identifiers from source code:
- Assigned variable names
- Function names and parameters
- Class names
- Imported names

Never executes code — AST parsing only.
"""

import ast
import logging
from typing import Any

logger = logging.getLogger(__name__)


def collect_identifiers(code: str) -> dict[str, set[str]]:
    """
    Parse Python source with AST and collect known identifiers.

    Returns:
        {
            "variables": {"name", "age", ...},
            "functions": {"calculate", ...},
            "parameters": {"numbers", ...},
            "classes": {"MyClass", ...},
            "imports": {"os", "json", ...},
            "all": {"name", "age", "calculate", ...}
        }
    """
    result: dict[str, set[str]] = {
        "variables": set(),
        "functions": set(),
        "parameters": set(),
        "classes": set(),
        "imports": set(),
        "all": set(),
    }

    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Incomplete code — return what we have (empty)
        return result

    for node in ast.walk(tree):
        # Variable assignments: x = 5, arr = [1,2,3]
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            result["variables"].add(node.id)

        # Augmented assignment: x += 1
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            result["variables"].add(node.target.id)

        # Function definitions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["functions"].add(node.name)
            for arg in node.args.args:
                result["parameters"].add(arg.arg)
            # Also add function name as a variable (it's assignable)
            result["variables"].add(node.name)

        # Class definitions
        if isinstance(node, ast.ClassDef):
            result["classes"].add(node.name)
            result["variables"].add(node.name)

        # Imports: import os, from os import path
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                result["imports"].add(name)
                result["variables"].add(name)
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    name = alias.asname or alias.name
                    result["imports"].add(name)
                    result["variables"].add(name)

    # Build the "all" set
    result["all"] = (
        result["variables"]
        | result["functions"]
        | result["parameters"]
        | result["classes"]
    )

    return result
