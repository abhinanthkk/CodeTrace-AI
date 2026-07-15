"""
CodeTrace AI — TypeError Analyzer

Determines the root cause of TypeError exceptions:
- The types of operands involved
- The likely incompatible operation
- Relevant variable names and values
"""

import re
from typing import Any


class TypeErrorAnalyzer:
    def analyze(
        self,
        error_info: dict[str, Any],
        timeline: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze a TypeError and extract structured evidence."""
        failure_vars = self._get_failure_variables(timeline)
        error_message = error_info.get("message", "")
        failure_line = error_info.get("line", 0)

        evidence: dict[str, Any] = {
            "category": "type_mismatch",
            "error_type": "TypeError",
            "error_message": error_message,
        }

        # Extract type information from the error message
        types_found = self._extract_types(error_message)
        if types_found:
            evidence["involved_types"] = types_found

        # Find variables at the failure line with their runtime types
        if failure_vars:
            type_summary = {
                name: type(value).__name__
                for name, value in failure_vars.items()
            }
            if type_summary:
                evidence["variable_types"] = type_summary

        evidence["confidence"] = self._compute_confidence(evidence)
        evidence["explanation"] = self._build_explanation(evidence)

        return evidence

    def _get_failure_variables(
        self, timeline: list[dict[str, Any]]
    ) -> dict[str, Any]:
        for step in reversed(timeline):
            if step.get("event") == "exception":
                return step.get("variables", {})
        for step in reversed(timeline):
            if step.get("variables"):
                return step["variables"]
        return {}

    def _extract_types(self, message: str) -> list[str] | None:
        """
        Extract type names from common TypeError message patterns.

        Examples:
        - "can only concatenate str (not "int") to str"
        - "unsupported operand type(s) for +: 'int' and 'str'"
        - "'int' object is not callable"
        """
        types = []

        # Pattern: "str (not "int")"
        match = re.findall(r'"(\w+)"', message)
        if match:
            types = match

        # Pattern: "'int' and 'str'"
        if not types:
            match = re.findall(r"'(\w+)'", message)
            types = match

        # Pattern: "int and float" (without quotes)
        if not types:
            match = re.findall(r'\b(int|str|float|list|dict|tuple|set|bool|NoneType)\b', message)
            types = list(set(match))

        return types if types else None

    def _compute_confidence(self, evidence: dict[str, Any]) -> float:
        score = 0.0
        if evidence.get("error_message"):
            score += 0.3
        if evidence.get("involved_types"):
            score += 0.4
        if evidence.get("variable_types"):
            score += 0.25
        return min(score, 0.95)

    def _build_explanation(self, evidence: dict[str, Any]) -> str:
        types = evidence.get("involved_types", [])
        var_types = evidence.get("variable_types", {})

        if types:
            types_str = " and ".join(types)
            return (
                f"This operation is not supported between {types_str}. "
                f"Check that the values at the failure line have compatible types."
            )

        if var_types:
            vars_str = ", ".join(f"'{k}': {v}" for k, v in list(var_types.items())[:5])
            return (
                f"Type mismatch detected. Variable types at failure: {vars_str}. "
                f"Check that operations are used with compatible types."
            )

        return "A type mismatch occurred. Check the types of values in the failing expression."
