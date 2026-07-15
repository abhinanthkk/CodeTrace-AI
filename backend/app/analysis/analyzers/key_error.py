"""
CodeTrace AI — KeyError Analyzer

Determines the root cause of KeyError exceptions:
- Which dictionary was accessed
- The requested (missing) key
- Available keys (when safe to display)
"""

import re
from typing import Any


class KeyErrorAnalyzer:
    def analyze(
        self,
        error_info: dict[str, Any],
        timeline: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze a KeyError and extract structured evidence."""
        failure_vars = self._get_failure_variables(timeline)
        error_message = error_info.get("message", "")

        evidence: dict[str, Any] = {
            "category": "key_not_found",
            "error_type": "KeyError",
        }

        # Extract the requested key from the error message
        requested_key = self._extract_requested_key(error_message)
        if requested_key is not None:
            evidence["requested_key"] = requested_key

        # Find the dictionary variable
        target_dict = self._find_dict(failure_vars, requested_key)
        if target_dict:
            evidence["dictionary_variable"] = target_dict["name"]
            if len(target_dict.get("keys", [])) <= 20:
                evidence["available_keys"] = target_dict["keys"]

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

    def _extract_requested_key(self, message: str) -> Any:
        """
        Extract the missing key from the KeyError message.

        Python formats KeyError messages like:
        - 'age' (single key as string)
        - 42 (integer key)
        - ('a', 'b') (tuple key)
        """
        # The message IS the key repr for simple keys
        stripped = message.strip().strip("'\"")
        if stripped:
            # Try as int
            try:
                return int(stripped)
            except ValueError:
                pass
            return stripped
        return None

    def _find_dict(
        self, variables: dict[str, Any], requested_key: Any
    ) -> dict[str, Any] | None:
        """
        Find the dictionary most likely to have been accessed.

        Strategy: look for dict variables. If we know the requested key,
        find the dict that is missing that key. Otherwise return the
        first dict found.
        """
        candidates = []
        for name, value in variables.items():
            if isinstance(value, dict):
                keys = list(value.keys())
                candidates.append({
                    "name": name,
                    "keys": keys,
                    "has_key": requested_key in value if requested_key is not None else None,
                })

        if not candidates:
            return None

        if requested_key is not None:
            # Prefer the dict that doesn't have the requested key
            for c in candidates:
                if c["has_key"] is False:
                    return c
            # If all dicts have the key (unlikely for KeyError), return first
            return candidates[0]

        return candidates[0] if candidates else None

    def _compute_confidence(self, evidence: dict[str, Any]) -> float:
        score = 0.0
        if evidence.get("requested_key") is not None:
            score += 0.4
        if evidence.get("dictionary_variable"):
            score += 0.35
        if evidence.get("available_keys"):
            score += 0.2
        return min(score, 0.95)

    def _build_explanation(self, evidence: dict[str, Any]) -> str:
        req_key = evidence.get("requested_key", "the key")
        dict_var = evidence.get("dictionary_variable", "the dictionary")
        available = evidence.get("available_keys")

        if available:
            keys_str = ", ".join(repr(k)[:20] for k in available[:10])
            if len(available) > 10:
                keys_str += f", ... ({len(available)} total)"
            return (
                f"'{dict_var}' does not contain key {req_key!r}. "
                f"Available keys: [{keys_str}]."
            )

        return f"'{dict_var}' does not contain the key {req_key!r}."
