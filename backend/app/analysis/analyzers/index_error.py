"""
CodeTrace AI — IndexError Analyzer

Determines the root cause of IndexError exceptions:
- Which sequence was indexed
- The sequence's length
- The attempted index value
- The index variable name
- The valid index range
"""

import re
from typing import Any


class IndexErrorAnalyzer:
    def analyze(
        self,
        error_info: dict[str, Any],
        timeline: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze an IndexError and extract structured evidence."""
        failure_line = error_info.get("line", 0)
        failure_vars = self._get_failure_variables(timeline)

        evidence: dict[str, Any] = {
            "category": "index_out_of_range",
            "error_type": "IndexError",
        }

        # Find the sequence variable being indexed at the failure line
        sequence = self._find_sequence(failure_vars)
        if sequence:
            evidence["sequence_variable"] = sequence["name"]
            evidence["sequence_length"] = sequence["length"]
            evidence["valid_index_range"] = self._format_range(sequence["length"])
            evidence["sequence_value"] = sequence["value"]

        # Find the index variable
        index_info = self._find_index(failure_vars)
        if index_info:
            evidence["index_variable"] = index_info["name"]
            evidence["attempted_index"] = index_info["value"]

        # Build confidence based on what we found
        evidence["confidence"] = self._compute_confidence(evidence)

        # Add human-readable explanation
        evidence["explanation"] = self._build_explanation(evidence)

        return evidence

    def _get_failure_variables(
        self, timeline: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Get the variable state at the point of failure."""
        for step in reversed(timeline):
            if step.get("event") == "exception":
                return step.get("variables", {})
        # Fallback to last step with variables
        for step in reversed(timeline):
            if step.get("variables"):
                return step["variables"]
        return {}

    def _find_sequence(
        self, variables: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Find the sequence (list, tuple, str) most likely to be the one
        that was indexed. Returns the one with the smallest length that
        looks like user data (not a short string constant).
        """
        candidates = []
        for name, value in variables.items():
            if isinstance(value, list):
                candidates.append({
                    "name": name,
                    "length": len(value),
                    "value": value if len(value) <= 10 else f"<{len(value)} items>",
                    "type": "list",
                })
            elif isinstance(value, str) and len(value) > 3:
                candidates.append({
                    "name": name,
                    "length": len(value),
                    "value": value[:50],
                    "type": "str",
                })

        if not candidates:
            return None

        # Heuristic: the most recently created/updated sequence is the
        # most likely target. Since we can't determine recency from the
        # failure snapshot alone, return the one with the smallest length
        # (it's the most likely to cause an out-of-bounds error).
        candidates.sort(key=lambda c: c["length"])
        return candidates[0] if candidates else None

    def _find_index(
        self, variables: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Find the variable most likely used as the index.
        Usually it's an int variable with a value >= the sequence length.
        """
        for name, value in variables.items():
            if isinstance(value, int):
                return {"name": name, "value": value}
        return None

    def _format_range(self, length: int) -> str:
        """Format the valid index range for display."""
        if length == 0:
            return "empty (no valid indices)"
        if length == 1:
            return "0 only"
        return f"0 to {length - 1}"

    def _compute_confidence(self, evidence: dict[str, Any]) -> float:
        """Compute confidence based on how much evidence was found."""
        score = 0.0
        if evidence.get("sequence_variable"):
            score += 0.4
        if evidence.get("sequence_length") is not None:
            score += 0.2
        if evidence.get("attempted_index") is not None:
            score += 0.3
        if evidence.get("index_variable"):
            score += 0.1
        return min(score, 0.95)

    def _build_explanation(self, evidence: dict[str, Any]) -> str:
        """Build a deterministic explanation from the evidence."""
        seq_name = evidence.get("sequence_variable", "the sequence")
        seq_len = evidence.get("sequence_length")
        idx_val = evidence.get("attempted_index")
        valid_range = evidence.get("valid_index_range", "unknown")

        if seq_len is not None and idx_val is not None:
            return (
                f"'{seq_name}' has {seq_len} element(s) (valid indices: {valid_range}), "
                f"but you tried to access index {idx_val}, which is out of range."
            )
        elif seq_len is not None:
            return (
                f"'{seq_name}' has {seq_len} element(s) with valid indices {valid_range}. "
                f"The attempted index was outside this range."
            )
        return f"An index was used that is outside the valid range for '{seq_name}'."
