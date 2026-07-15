"""
CodeTrace AI — NameError Analyzer

Determines the root cause of NameError exceptions:
- The missing variable name
- Similar variable names (basic string similarity)
- Suggests possible intended variable
"""

import re
from difflib import get_close_matches
from typing import Any


class NameErrorAnalyzer:
    def analyze(
        self,
        error_info: dict[str, Any],
        timeline: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze a NameError and extract structured evidence."""
        failure_vars = self._get_failure_variables(timeline)
        error_message = error_info.get("message", "")

        evidence: dict[str, Any] = {
            "category": "name_not_defined",
            "error_type": "NameError",
        }

        # Extract the missing variable name from the error message
        missing_name = self._extract_missing_name(error_message)
        if missing_name:
            evidence["missing_name"] = missing_name

        # Find similar variable names in the available variables
        if missing_name and failure_vars:
            similar = self._find_similar_names(missing_name, list(failure_vars.keys()))
            if similar:
                evidence["similar_variables"] = similar
                evidence["suggestion"] = f"Did you mean '{similar[0]}'?"

        # Also check variable names from earlier in the timeline
        all_names = self._collect_all_variable_names(timeline)
        if missing_name and not evidence.get("similar_variables"):
            similar = self._find_similar_names(missing_name, all_names)
            if similar:
                evidence["similar_variables"] = similar
                evidence["suggestion"] = f"Did you mean '{similar[0]}'?"

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

    def _collect_all_variable_names(
        self, timeline: list[dict[str, Any]]
    ) -> list[str]:
        """Collect all variable names that appeared across the timeline."""
        seen = set()
        for step in timeline:
            for name in step.get("variables", {}):
                seen.add(name)
        return list(seen)

    def _extract_missing_name(self, message: str) -> str | None:
        """
        Extract the undefined name from Python's NameError message.

        Examples:
        - "name 'username' is not defined"
        - "name 'x' is not defined. Did you mean: 'y'?"
        """
        # Try quoted name extraction
        match = re.search(r"name '([^']+)' is not defined", message)
        if match:
            return match.group(1)
        # Try without quotes (rare)
        match = re.search(r"name (\w+) is not defined", message)
        if match:
            return match.group(1)
        return None

    def _find_similar_names(
        self, target: str, candidates: list[str], cutoff: float = 0.6
    ) -> list[str]:
        """
        Find candidate names that are similar to the target using
        difflib's get_close_matches (based on sequence matching).
        """
        # Filter out names that are exact matches (case-sensitive)
        # Keep names that differ only in case (userName vs username)
        filtered = [
            c for c in candidates
            if c != target
            and abs(len(c) - len(target)) <= len(target) // 2 + 3
        ]
        if not filtered:
            return []
        return get_close_matches(target, filtered, n=3, cutoff=cutoff)

    def _compute_confidence(self, evidence: dict[str, Any]) -> float:
        score = 0.0
        if evidence.get("missing_name"):
            score += 0.5
        if evidence.get("similar_variables"):
            score += 0.45
        return min(score, 0.95)

    def _build_explanation(self, evidence: dict[str, Any]) -> str:
        missing = evidence.get("missing_name", "the variable")
        similar = evidence.get("similar_variables", [])

        if similar:
            candidates = ", ".join(f"'{s}'" for s in similar)
            return (
                f"'{missing}' is not defined. "
                f"Did you mean {candidates}?"
            )

        return (
            f"'{missing}' is not defined. Check for typos or make sure "
            f"the variable is assigned before it is used."
        )
