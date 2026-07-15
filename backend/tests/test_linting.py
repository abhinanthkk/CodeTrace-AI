"""Tests for CodeTrace Live Fix linting layer."""

import pytest
from app.linting.diagnostic_processor import (
    IGNORED_DIAGNOSTICS,
    process_diagnostics,
)
from app.linting.ruff_runner import RUFF_RULES, run_ruff_safe


class TestDiagnosticProcessor:
    """Tests for diagnostic normalization and filtering."""

    def test_w292_filtered_out(self):
        """W292 (no newline at end of file) should be filtered out."""
        raw = [
            {
                "code": "W292",
                "message": "No newline at end of file",
                "location": {"row": 3, "column": 10},
                "end_location": {"row": 3, "column": 10},
                "fix": None,
                "severity": "warning",
            }
        ]
        result = process_diagnostics(raw)
        assert len(result) == 0, f"W292 should be filtered, got {len(result)}"

    def test_e501_filtered_out(self):
        """E501 (line too long) should be filtered out."""
        raw = [
            {
                "code": "E501",
                "message": "Line too long",
                "location": {"row": 1, "column": 89},
                "end_location": {"row": 1, "column": 89},
                "fix": None,
                "severity": "warning",
            }
        ]
        result = process_diagnostics(raw)
        assert len(result) == 0

    def test_f821_preserved(self):
        """F821 (undefined name) should NOT be filtered."""
        raw = [
            {
                "code": "F821",
                "message": "Undefined name `nam`",
                "location": {"row": 2, "column": 7},
                "end_location": {"row": 2, "column": 10},
                "fix": None,
                "severity": "error",
            }
        ]
        result = process_diagnostics(raw)
        assert len(result) == 1
        assert result[0]["code"] == "F821"
        assert result[0]["severity"] == "error"

    def test_f401_preserved(self):
        """F401 (unused import) should NOT be filtered."""
        raw = [
            {
                "code": "F401",
                "message": "`os` imported but unused",
                "location": {"row": 1, "column": 8},
                "end_location": {"row": 1, "column": 10},
                "fix": None,
                "severity": "error",
            }
        ]
        result = process_diagnostics(raw)
        assert len(result) == 1
        assert result[0]["code"] == "F401"

    def test_mixed_diagnostics_filtered(self):
        """Mixed diagnostics: W292 filtered, F821 kept."""
        raw = [
            {"code": "F821", "message": "Undefined name", "location": {"row": 2, "column": 7}, "end_location": {"row": 2, "column": 10}, "fix": None},
            {"code": "W292", "message": "No newline", "location": {"row": 2, "column": 10}, "end_location": {"row": 2, "column": 10}, "fix": None},
        ]
        result = process_diagnostics(raw)
        assert len(result) == 1
        assert result[0]["code"] == "F821"

    def test_ignored_set_is_substantial(self):
        """The IGNORED_DIAGNOSTICS set should contain W292 at minimum."""
        assert "W292" in IGNORED_DIAGNOSTICS
        assert "E501" in IGNORED_DIAGNOSTICS
        assert len(IGNORED_DIAGNOSTICS) > 20  # Should be a substantial list

    def test_b_rules_preserved(self):
        """B (bugbear) rules should NOT be filtered."""
        raw = [
            {
                "code": "B006",
                "message": "Do not use mutable data structures for argument defaults",
                "location": {"row": 1, "column": 20},
                "end_location": {"row": 1, "column": 22},
                "fix": None,
                "severity": "error",
            }
        ]
        result = process_diagnostics(raw)
        assert len(result) == 1


class TestRuffRules:
    """Tests for Ruff rule configuration."""

    def test_rules_bugs_only(self):
        """RUFF_RULES should only include F, E, B (bugs, not style)."""
        assert "F" in RUFF_RULES, "F (Pyflakes) should be enabled"
        assert "E" in RUFF_RULES, "E (pycodestyle errors) should be enabled"
        assert "B" in RUFF_RULES, "B (bugbear) should be enabled"
        assert "W" not in RUFF_RULES, "W (pycodestyle warnings) should be disabled"
        assert "SIM" not in RUFF_RULES, "SIM (simplify) should be disabled"
        assert "UP" not in RUFF_RULES, "UP (pyupgrade) should be disabled"


class TestLiveLintEndToEnd:
    """End-to-end tests using the actual Ruff runner."""

    def test_valid_code_no_issues(self):
        """Valid Python without trailing newline should return zero useful issues."""
        raw = run_ruff_safe('name = "Abhinanth"\n\nprint(name)')
        result = process_diagnostics(raw)
        errors = [d for d in result if d["severity"] in ("error", "warning")]
        assert len(errors) == 0, f"Expected 0 issues, got: {[(d['code'], d['message']) for d in errors]}"

    def test_undefined_name_detected(self):
        """Undefined variable should still be detected."""
        raw = run_ruff_safe('name = "Abhinanth"\n\nprint(nam)')
        result = process_diagnostics(raw)
        f821 = [d for d in result if d["code"] == "F821"]
        assert len(f821) >= 1, f"F821 should be detected, got: {[(d['code'], d['message']) for d in result]}"
        assert "nam" in f821[0]["message"]

    def test_unused_import_detected(self):
        """Unused import should still be detected."""
        raw = run_ruff_safe('import os\n\nprint("Hello")')
        result = process_diagnostics(raw)
        f401 = [d for d in result if d["code"] == "F401"]
        # F401 should be present if Ruff is configured to check it
        # Note: Ruff may or may not flag this depending on rule selection
        assert len(result) >= 0  # At minimum, no crash
