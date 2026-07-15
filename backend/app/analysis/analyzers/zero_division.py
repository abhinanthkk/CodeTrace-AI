"""
CodeTrace AI — ZeroDivisionError Analyzer

Determines the root cause of ZeroDivisionError:
- Which variable was the divisor
- The divisor's value (should be 0)
- The expression context
"""

from typing import Any


class ZeroDivisionErrorAnalyzer:
    def analyze(
        self,
        error_info: dict[str, Any],
        timeline: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze a ZeroDivisionError and extract structured evidence."""
        failure_vars = self._get_failure_variables(timeline)
        error_message = error_info.get("message", "")

        evidence: dict[str, Any] = {
            "category": "division_by_zero",
            "error_type": "ZeroDivisionError",
        }

        # Find the divisor variable — look for a variable with value 0
        divisor = self._find_divisor(failure_vars)
        if divisor:
            evidence["divisor_variable"] = divisor["name"]
            evidence["divisor_value"] = divisor["value"]

        # Check for other zero-valued variables that might be involved
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

    def _find_divisor(
        self, variables: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Find the variable most likely to be the zero divisor.

        Strategy: look for variables with value 0. If there are multiple,
        prefer the most recently appearing one (variables at the end of
        the dict, approximating creation order).
        """
        zero_vars = []
        for name, value in variables.items():
            if isinstance(value, (int, float)) and value == 0:
                zero_vars.append({"name": name, "value": value})

        if not zero_vars:
            return None

        # Return the last zero-valued variable found (likely most relevant)
        return zero_vars[-1] if len(zero_vars) > 0 else zero_vars[0] if zero_vars else None

    def _compute_confidence(self, evidence: dict[str, Any]) -> float:
        score = 0.0
        if evidence.get("divisor_variable"):
            score += 0.7
        if evidence.get("divisor_value") == 0:
            score += 0.25
        return min(score, 0.95)

    def _build_explanation(self, evidence: dict[str, Any]) -> str:
        var = evidence.get("divisor_variable")
        if var:
            return (
                f"'{var}' has a value of 0. Division by zero is mathematically "
                f"undefined, which causes ZeroDivisionError in Python."
            )
        return (
            "A division operation has a divisor equal to zero. "
            "Check the right-hand operand of /, //, or %."
        )
