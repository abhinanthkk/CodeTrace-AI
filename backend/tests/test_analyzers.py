"""Tests for deterministic error analyzers."""

import pytest
from app.analysis.analyzers.index_error import IndexErrorAnalyzer
from app.analysis.analyzers.zero_division import ZeroDivisionErrorAnalyzer
from app.analysis.analyzers.key_error import KeyErrorAnalyzer
from app.analysis.analyzers.name_error import NameErrorAnalyzer
from app.analysis.analyzers.type_error import TypeErrorAnalyzer
from app.analysis.analyzer import GenericAnalyzer, analyze_failure


class TestIndexErrorAnalyzer:
    def setup_method(self):
        self.analyzer = IndexErrorAnalyzer()

    def test_basic_index_error(self):
        error_info = {"type": "IndexError", "message": "list index out of range", "line": 4}
        timeline = [
            {"step": 1, "event": "line", "line": 1, "variables": {"arr": [10, 20, 30]}},
            {"step": 2, "event": "line", "line": 3, "variables": {"arr": [10, 20, 30], "i": 0}},
            {"step": 3, "event": "exception", "line": 4, "variables": {"arr": [10, 20, 30], "i": 3}},
        ]
        result = self.analyzer.analyze(error_info, timeline)
        assert result["category"] == "index_out_of_range"
        assert result["sequence_variable"] == "arr"
        assert result["sequence_length"] == 3
        assert result["attempted_index"] == 3
        assert result["confidence"] >= 0.8

    def test_partial_evidence(self):
        """Should handle missing variables gracefully."""
        error_info = {"type": "IndexError", "message": "list index out of range", "line": 1}
        timeline = [
            {"step": 1, "event": "exception", "line": 1, "variables": {}},
        ]
        result = self.analyzer.analyze(error_info, timeline)
        assert result["category"] == "index_out_of_range"
        assert result["confidence"] < 0.5


class TestZeroDivisionErrorAnalyzer:
    def setup_method(self):
        self.analyzer = ZeroDivisionErrorAnalyzer()

    def test_basic_zero_division(self):
        error_info = {"type": "ZeroDivisionError", "message": "division by zero", "line": 3}
        timeline = [
            {"step": 1, "event": "line", "line": 1, "variables": {"x": 10, "y": 0}},
            {"step": 2, "event": "exception", "line": 3, "variables": {"x": 10, "y": 0}},
        ]
        result = self.analyzer.analyze(error_info, timeline)
        assert result["category"] == "division_by_zero"
        assert result["divisor_variable"] == "y"
        assert result["divisor_value"] == 0
        assert result["confidence"] >= 0.8


class TestKeyErrorAnalyzer:
    def setup_method(self):
        self.analyzer = KeyErrorAnalyzer()

    def test_basic_key_error(self):
        error_info = {"type": "KeyError", "message": "'age'", "line": 4}
        timeline = [
            {"step": 1, "event": "line", "line": 1, "variables": {"user": {"name": "A"}}},
            {"step": 2, "event": "exception", "line": 4, "variables": {"user": {"name": "A"}}},
        ]
        result = self.analyzer.analyze(error_info, timeline)
        assert result["category"] == "key_not_found"
        assert result["requested_key"] == "age"
        assert result["dictionary_variable"] == "user"
        assert "name" in result["available_keys"]
        assert result["confidence"] >= 0.7


class TestNameErrorAnalyzer:
    def setup_method(self):
        self.analyzer = NameErrorAnalyzer()

    def test_name_error_with_similar(self):
        error_info = {
            "type": "NameError",
            "message": "name 'username' is not defined",
            "line": 3,
        }
        timeline = [
            {"step": 1, "event": "line", "line": 1, "variables": {"userName": "A"}},
            {"step": 2, "event": "exception", "line": 3, "variables": {"userName": "A"}},
        ]
        result = self.analyzer.analyze(error_info, timeline)
        assert result["category"] == "name_not_defined"
        assert result["missing_name"] == "username"
        assert "userName" in result.get("similar_variables", [])
        assert result["confidence"] >= 0.8

    def test_name_error_no_similar(self):
        error_info = {
            "type": "NameError",
            "message": "name 'foo' is not defined",
            "line": 1,
        }
        timeline = [
            {"step": 1, "event": "exception", "line": 1, "variables": {"x": 5}},
        ]
        result = self.analyzer.analyze(error_info, timeline)
        assert result["missing_name"] == "foo"
        # Should not match "x" as similar to "foo"
        assert "foo" not in str(result.get("similar_variables", []))


class TestTypeErrorAnalyzer:
    def setup_method(self):
        self.analyzer = TypeErrorAnalyzer()

    def test_concatenation_type_error(self):
        error_info = {
            "type": "TypeError",
            "message": 'can only concatenate str (not "int") to str',
            "line": 2,
        }
        timeline = [
            {"step": 1, "event": "line", "line": 1, "variables": {"age": 20}},
            {"step": 2, "event": "exception", "line": 2, "variables": {"age": 20}},
        ]
        result = self.analyzer.analyze(error_info, timeline)
        assert result["category"] == "type_mismatch"
        assert "int" in result.get("involved_types", [])
        assert result.get("variable_types", {}).get("age") == "int"
        assert result["confidence"] >= 0.7


class TestGenericAnalyzer:
    def test_unknown_exception(self):
        analyzer = GenericAnalyzer()
        error_info = {"type": "RecursionError", "message": "maximum recursion depth exceeded", "line": 1}
        result = analyzer.analyze(error_info, [])
        assert result["category"] == "unknown"
        assert result["confidence"] == 0.0


class TestAnalyzeFailure:
    def test_no_error(self):
        result = analyze_failure(None, [])
        assert result is None

    def test_with_error(self):
        error_info = {"type": "IndexError", "message": "list index out of range", "line": 4}
        timeline = [
            {"step": 1, "event": "exception", "line": 4, "variables": {"arr": [1], "i": 5}},
        ]
        result = analyze_failure(error_info, timeline)
        assert result is not None
        assert result["category"] == "index_out_of_range"
