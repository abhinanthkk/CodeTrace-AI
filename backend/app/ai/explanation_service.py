"""
CodeTrace AI — Explanation Service

Builds prompts from structured execution evidence, calls the AI
provider, and parses the response. Falls back to deterministic
templates when no AI provider is configured.
"""

import json
import logging
import re
from typing import Any

from .prompts import EXPLANATION_PROMPT
from .provider import AIProvider, create_provider

logger = logging.getLogger(__name__)


class ExplanationService:
    """
    Generates explanations for code failures.

    Uses AI when available, falls back to deterministic templates.
    """

    def __init__(self, provider: AIProvider | None = None):
        self.provider = provider or create_provider()

    def explain(
        self,
        source_code: str,
        error_info: dict[str, Any] | None,
        timeline: list[dict[str, Any]],
        analysis: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Generate an explanation for a code failure.

        Args:
            source_code: The user's Python source code
            error_info: Exception info from the tracer
            timeline: Processed execution timeline
            analysis: Deterministic analyzer results

        Returns:
            Explanation dict with summary, what_failed, why, etc.
        """
        if error_info is None:
            return self._empty_explanation()

        if self.provider:
            return self._ai_explain(source_code, error_info, timeline, analysis)
        else:
            return self._deterministic_explain(error_info, analysis)

    def _ai_explain(
        self,
        source_code: str,
        error_info: dict[str, Any],
        timeline: list[dict[str, Any]],
        analysis: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Generate explanation using the configured AI provider."""
        # Build the last execution steps summary
        steps_summary = self._format_last_steps(timeline, count=10)

        # Build variables at failure summary
        variables_at_failure = self._format_failure_variables(timeline)

        # Analysis summary
        analysis_summary = json.dumps(analysis, indent=2) if analysis else "No analysis available."

        # Build the prompt
        prompt = EXPLANATION_PROMPT.format(
            source_code=source_code,
            error_type=error_info.get("type", "Exception"),
            error_message=error_info.get("message", ""),
            error_line=error_info.get("line", "?"),
            variables_at_failure=variables_at_failure,
            execution_steps=steps_summary,
            analysis_summary=analysis_summary,
        )

        try:
            raw_response = self.provider.generate(prompt)
            return self._parse_ai_response(raw_response)
        except Exception as e:
            logger.error(f"AI explanation failed: {e}")
            return self._deterministic_explain(error_info, analysis)

    def _deterministic_explain(
        self,
        error_info: dict[str, Any],
        analysis: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Generate a deterministic explanation from analyzer evidence."""
        error_type = error_info.get("type", "Exception")
        error_message = error_info.get("message", "")
        error_line = error_info.get("line", "?")

        analysis_explanation = ""
        if analysis:
            analysis_explanation = analysis.get("explanation", "")

        # Build a simple explanation from evidence
        what_failed = f"Line {error_line} raised {error_type}: {error_message}"
        why = analysis_explanation or f"A {error_type} occurred at line {error_line}."
        execution_sequence = self._build_deterministic_sequence(error_info, analysis)

        suggested_fix = ""
        if analysis:
            if analysis.get("category") == "index_out_of_range":
                valid = analysis.get("valid_index_range", "valid range")
                suggested_fix = f"Make sure the loop index stays within {valid}."
            elif analysis.get("category") == "division_by_zero":
                suggested_fix = "Check that the divisor is not zero before dividing."
            elif analysis.get("category") == "key_not_found":
                key = analysis.get("requested_key", "the key")
                suggested_fix = f"Verify that {key!r} exists in the dictionary before accessing it."
            elif analysis.get("category") == "name_not_defined":
                name = analysis.get("missing_name", "the variable")
                similar = analysis.get("similar_variables", [])
                if similar:
                    suggested_fix = f"Rename '{similar[0]}' to '{name}', or use the correct variable name."
                else:
                    suggested_fix = f"Define '{name}' before using it, or check for typos."
            elif analysis.get("category") == "type_mismatch":
                suggested_fix = "Convert the values to compatible types before the operation."

        corrected_code = analysis.get("corrected_code", "")

        return {
            "summary": f"Your code raised {error_type} at line {error_line}.",
            "what_failed": what_failed,
            "why": why,
            "execution_sequence": execution_sequence,
            "suggested_fix": suggested_fix,
            "corrected_code": corrected_code,
        }

    def _format_last_steps(
        self, timeline: list[dict[str, Any]], count: int = 10
    ) -> str:
        """Format the last N execution steps for the prompt."""
        if not timeline:
            return "No execution steps recorded."

        last_steps = timeline[-count:]
        lines = []
        for step in last_steps:
            parts = [f"Step {step['step']}: {step['event']} at line {step['line']}"]
            for name, info in step.get("changes", {}).items():
                if info["type"] == "created":
                    parts.append(f"  {name} = {self._format_val(info.get('value'))}")
                elif info["type"] == "updated":
                    parts.append(
                        f"  {name}: {self._format_val(info.get('old_value'))} → "
                        f"{self._format_val(info.get('new_value'))}"
                    )
            if step.get("output", "").strip():
                parts.append(f"  output: {step['output'].strip()}")
            if step.get("exception"):
                parts.append(f"  EXCEPTION: {step['exception']['type']}: {step['exception']['message']}")
            lines.append(" ".join(parts))
        return "\n".join(lines)

    def _format_failure_variables(self, timeline: list[dict[str, Any]]) -> str:
        """Format the variable state at failure for the prompt."""
        for step in reversed(timeline):
            if step.get("event") == "exception" and step.get("variables"):
                return json.dumps(step["variables"], default=str, indent=2)
        for step in reversed(timeline):
            if step.get("variables"):
                return json.dumps(step["variables"], default=str, indent=2)
        return "No variables captured."

    def _build_deterministic_sequence(
        self,
        error_info: dict[str, Any],
        analysis: dict[str, Any] | None,
    ) -> str:
        """Build a deterministic execution sequence description."""
        error_type = error_info.get("type", "Exception")
        error_line = error_info.get("line", "?")

        if not analysis:
            return f"Execution reached line {error_line} where {error_type} occurred."

        category = analysis.get("category", "")
        if category == "index_out_of_range":
            seq = analysis.get("sequence_variable", "sequence")
            length = analysis.get("sequence_length", "?")
            idx_var = analysis.get("index_variable", "index")
            idx_val = analysis.get("attempted_index", "?")
            valid = analysis.get("valid_index_range", "?")
            return (
                f"The loop iterates, incrementing {idx_var}. When {idx_var} reaches {idx_val}, "
                f"the code tries {seq}[{idx_val}]. But {seq} has only {length} element(s), "
                f"with valid indices {valid}."
            )
        elif category == "division_by_zero":
            divisor = analysis.get("divisor_variable", "divisor")
            return f"The code attempts division with {divisor} = 0, which is mathematically undefined."
        elif category == "key_not_found":
            key = analysis.get("requested_key", "key")
            return f"The code tries to access key {key!r} which does not exist in the dictionary."

        return f"Execution reached line {error_line} where {error_type} occurred."

    def _parse_ai_response(self, raw: str) -> dict[str, Any]:
        """Parse the AI's JSON response, with error recovery."""
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse AI response as JSON, using raw text")
            # Try to salvage partial JSON
            try:
                start = cleaned.index("{")
                end = cleaned.rindex("}") + 1
                return json.loads(cleaned[start:end])
            except (ValueError, json.JSONDecodeError):
                return {
                    "summary": "AI explanation unavailable.",
                    "what_failed": raw[:200],
                    "why": "",
                    "execution_sequence": "",
                    "suggested_fix": "",
                    "corrected_code": "",
                }

    @staticmethod
    def _format_val(val: Any) -> str:
        """Format a value for display in the prompt."""
        if val is None:
            return "None"
        s = str(val)
        if len(s) > 50:
            return s[:50] + "..."
        return s

    def _empty_explanation(self) -> dict[str, Any]:
        return {
            "summary": "",
            "what_failed": "",
            "why": "",
            "execution_sequence": "",
            "suggested_fix": "",
            "corrected_code": "",
        }
