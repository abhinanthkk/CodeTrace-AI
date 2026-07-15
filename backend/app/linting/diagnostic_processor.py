"""
CodeTrace Live Fix — Diagnostic Processor

Normalizes raw Ruff diagnostics into CodeTrace's internal format.
The frontend consumes ONLY CodeTrace's schema, never raw Ruff JSON.

Filters out low-value style/formatting diagnostics — CodeTrace is an
error detection and debugging tool, not a style checker.
"""

from typing import Any

# ── Ignored diagnostics ────────────────────────────────────────────────
# These Ruff codes represent formatting preferences, not bugs.
# CodeTrace focuses on actual coding mistakes.
IGNORED_DIAGNOSTICS: set[str] = {
    # pycodestyle warnings (style, not bugs)
    "W292",  # No newline at end of file
    "W291",  # Trailing whitespace
    "W293",  # Blank line contains whitespace
    "W391",  # Blank line at end of file
    # Line length and whitespace
    "E501",  # Line too long
    "E302",  # Expected 2 blank lines
    "E305",  # Expected 2 blank lines after class/function
    "E303",  # Too many blank lines
    "E231",  # Missing whitespace after ','
    "E225",  # Missing whitespace around operator
    "E261",  # At least two spaces before inline comment
    "E262",  # Inline comment should start with '# '
    "E265",  # Block comment should start with '# '
    "E266",  # Too many leading '#' for block comment
    "E271",  # Multiple spaces after keyword
    "E272",  # Multiple spaces before keyword
    "E275",  # Missing whitespace after keyword
    # Import ordering (style)
    "E401",  # Multiple imports on one line
    "E402",  # Module level import not at top of file
    "I001",  # Import block is un-sorted or un-formatted
    # Quote style (style)
    "Q000",  # Single quotes found but double quotes preferred
    "Q001",  # Single quote found but double quote preferred
    "Q002",  # Double quote found but single quote preferred
    "Q003",  # Avoid escaping inner quotes
    # Blank lines (style)
    "D100",  # Missing docstring in public module
    "D101",  # Missing docstring in public class
    "D102",  # Missing docstring in public method
    "D103",  # Missing docstring in public function
    "D104",  # Missing docstring in public package
    # Naming conventions (style, not bugs)
    "N801",  # Class name should use CapWords
    "N802",  # Function name should be lowercase
    "N803",  # Argument name should be lowercase
    "N806",  # Variable in function should be lowercase
    # Pyupgrade suggestions (optional upgrades)
    "UP004",  # Class inherits from object
    "UP006",  # Use `list` instead of `List` for type annotation
    "UP007",  # Use `X | Y` for type annotations
    "UP008",  # Use `super()` instead of `super(__class__, self)`
    "UP009",  # UTF-8 encoding declaration is unnecessary
    "UP010",  # Unnecessary __future__ import
    "UP012",  # Unnecessary call to `encode` as UTF-8
    "UP013",  # Convert `type(x)` to `isinstance(x, int)`
    "UP015",  # Unnecessary open mode parameters
    "UP018",  # Unnecessary `str` call
    "UP019",  # Unnecessary `typing.Tuple` instead of `tuple`
    "UP020",  # Unnecessary call around `open()`
    "UP021",  # Replace `Universal Newlines` with `text=`
    "UP022",  # Replace `stdout` argument with `capsys`
    "UP024",  # Replace `os.error` aliases with `OSError`
    "UP025",  # Remove unicode escapes and use the actual character
    "UP026",  # Replace `mock` with `unittest.mock`
    "UP027",  # Replace unpacked list comprehensions
    "UP028",  # Replace `yield` with `yield from`
    "UP029",  # Unnecessary `os.getcwd` instead of `Path.cwd()`
    "UP030",  # Use `pathlib.Path` methods instead of `os` functions
    "UP031",  # Use `format` specifiers instead of `%` formatting
    "UP032",  # Use f-string instead of `.format()` call
    "UP033",  # Use `max`/`min` builtins instead of `sorted()[-1]`
    "UP034",  # Remove unnecessary parentheses
    "UP035",  # Remove deprecated `typing` imports
    "UP036",  # Remove outdated `__future__` import
    "UP037",  # Remove quotes from type annotations
    "UP038",  # Use `isinstance` instead of `type` comparisons
    "UP039",  # Remove unnecessary `str`/`bytes` calls from class definitions
    "UP040",  # Use explicit `Optional` instead of `X | None` shorthand
    "UP041",  # Use `yield from` instead of `yield` in a loop
    "UP042",  # Replace `typing.Text` with `str`
    "UP043",  # Replace `typing.DefaultDict` with `collections.defaultdict`
    "UP044",  # Replace `typing.Counter` with `collections.Counter`
    "UP045",  # Remove quotes from annotations
    # flake8-simplify (code style preferences)
    "SIM102",  # Use a single `if` instead of nested `if`
    "SIM103",  # Return the condition directly instead of if-else
    "SIM105",  # Use `contextlib.suppress` instead of try-except-pass
    "SIM107",  # Don't use `return` in try/except and finally
    "SIM108",  # Use ternary operator instead of if-else
    "SIM109",  # Use `a == b` instead of `not (a != b)`
    "SIM110",  # Use `any()` instead of for loop
    "SIM111",  # Use `all()` instead of for loop
    "SIM112",  # Use `os.environ.get()` instead of `os.getenv()`
    "SIM113",  # Use `enumerate()` to index loop variable
    "SIM114",  # Combine `if` branches with same body
    "SIM115",  # Use context manager for file operations
    "SIM116",  # Use dictionary comprehension instead of `dict()`
    "SIM117",  # Use `with` statement for multiple context managers
    "SIM118",  # Use `in` instead of `key in dict.keys()`
    "SIM201",  # Use `a != b` instead of `not a == b`
    "SIM202",  # Use `not a > b` instead of `a <= b`
    "SIM208",  # Use `is` instead of `==` for True/False/None
    "SIM210",  # Use `bool(...)` instead of `True if ... else False`
    "SIM211",  # Use `not ...` instead of `False if ... else True`
    "SIM212",  # Use `a if a else b` instead of `b if not a else a`
    "SIM220",  # Use `a and not b` instead of `not a and b`
    "SIM221",  # Use `a or not b` instead of `not a or b`
    "SIM222",  # Use `a or not b` instead of `not a or b`
    "SIM223",  # Use `not a` instead of `a == False`
    "SIM300",  # Use `age == 42` instead of `42 == age` (Yoda)
    "SIM401",  # Use `d.get(key, default)` instead of if-else
    "SIM910",  # Use `dict.get(key)` instead of `None if key in dict else dict[key]`
}


def process_diagnostics(raw_diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert raw Ruff diagnostics into CodeTrace's normalized format,
    filtering out low-value style/formatting diagnostics.

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
        "raw_fix": { ... } | null
    }
    """
    processed = []
    for diag in raw_diagnostics:
        # Skip style/formatting diagnostics
        code = diag.get("code", "")
        if code in IGNORED_DIAGNOSTICS:
            continue
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
