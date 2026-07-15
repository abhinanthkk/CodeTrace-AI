"""
CodeTrace AI — Explanation Service

Builds prompts from structured execution evidence, calls the AI
provider, and parses the response. Falls back to deterministic
templates when no AI provider is configured.

The deterministic path now generates actual corrected code for
every supported error type — not just one-line suggestions.
"""

import json
import logging
import re
from typing import Any

from .prompts import EXPLANATION_PROMPT
from .provider import AIProvider, create_provider

logger = logging.getLogger(__name__)


class CodeFixer:
    """
    Generates corrected Python code for supported error types
    using the source code and analyzer evidence.
    """

    @staticmethod
    def fix_index_error(source_code: str, analysis: dict[str, Any]) -> str:
        """Fix IndexError by correcting loop bounds or index access."""
        seq_var = analysis.get("sequence_variable", "")
        seq_len = analysis.get("sequence_length", 0)
        idx_var = analysis.get("index_variable", "")
        lines = source_code.split("\n")

        fixed_lines = []
        for line in lines:
            stripped = line.strip()
            # Fix `for i in range(N):` → `for i in range(len(seq)):`
            if idx_var and f"for {idx_var} in range(" in stripped:
                fixed_lines.append(
                    line.replace(
                        f"range({stripped.split('range(')[1].split(')')[0]})",
                        f"range(len({seq_var}))" if seq_var else f"range({seq_len})",
                    )
                )
            # Fix `print(arr[i])` → `if i < len(arr): print(arr[i])`
            elif seq_var and f"{seq_var}[" in stripped and idx_var and idx_var in stripped:
                indent = line[:len(line) - len(line.lstrip())]
                fixed_lines.append(f"{indent}if {idx_var} < len({seq_var}):")
                fixed_lines.append(f"{indent}    {stripped}")
            # Fix `print(empty[0])` → `if empty: print(empty[0])`
            elif seq_var and f"{seq_var}[0]" in stripped:
                indent = line[:len(line) - len(line.lstrip())]
                fixed_lines.append(f"{indent}if {seq_var}:")
                fixed_lines.append(f"{indent}    {stripped}")
            # Fix `s[5]` on strings → safe access
            elif seq_var and f"{seq_var}[" in stripped and seq_len:
                indent = line[:len(line) - len(line.lstrip())]
                idx_expr = stripped.split(f"{seq_var}[")[1].split("]")[0]
                fixed_lines.append(f"{indent}if {idx_expr} < len({seq_var}):")
                fixed_lines.append(f"{indent}    {stripped}")
            else:
                fixed_lines.append(line)

        return "\n".join(fixed_lines)

    @staticmethod
    def fix_zero_division(source_code: str, analysis: dict[str, Any]) -> str:
        """Fix ZeroDivisionError by adding a guard clause."""
        divisor_var = analysis.get("divisor_variable", "")
        lines = source_code.split("\n")

        fixed_lines = []
        for line in lines:
            stripped = line.strip()
            if divisor_var and f"/ {divisor_var}" in stripped:
                indent = line[:len(line) - len(line.lstrip())]
                fixed_lines.append(f"{indent}if {divisor_var} != 0:")
                fixed_lines.append(f"{indent}    {stripped}")
                fixed_lines.append(f"{indent}else:")
                fixed_lines.append(f'{indent}    print("Error: cannot divide by zero")')
            elif divisor_var and f"% {divisor_var}" in stripped:
                indent = line[:len(line) - len(line.lstrip())]
                fixed_lines.append(f"{indent}if {divisor_var} != 0:")
                fixed_lines.append(f"{indent}    {stripped}")
            else:
                fixed_lines.append(line)

        return "\n".join(fixed_lines)

    @staticmethod
    def fix_key_error(source_code: str, analysis: dict[str, Any]) -> str:
        """Fix KeyError by using .get() or checking key existence."""
        dict_var = analysis.get("dictionary_variable", "")
        req_key = analysis.get("requested_key", "")
        lines = source_code.split("\n")

        fixed_lines = []
        for line in lines:
            stripped = line.strip()
            if dict_var and req_key and f"{dict_var}[{req_key!r}]" in stripped:
                fixed_lines.append(
                    stripped.replace(
                        f"{dict_var}[{req_key!r}]",
                        f"{dict_var}.get({req_key!r}, 'default value')",
                    )
                )
            elif dict_var and req_key and f'{dict_var}["{req_key}"]' in stripped:
                fixed_lines.append(
                    stripped.replace(
                        f'{dict_var}["{req_key}"]',
                        f'{dict_var}.get("{req_key}", "default value")',
                    )
                )
            elif dict_var and f"{dict_var}[{req_key}]" in stripped:
                fixed_lines.append(
                    stripped.replace(
                        f"{dict_var}[{req_key}]",
                        f"{dict_var}.get({req_key}, 'default value')",
                    )
                )
            elif dict_var and f"{dict_var}[" in stripped:
                # Generic dict access — use .get()
                indent = line[:len(line) - len(line.lstrip())]
                key_expr = stripped.split(f"{dict_var}[")[1].split("]")[0]
                fixed_lines.append(
                    f"{indent}{stripped.replace(f'{dict_var}[{key_expr}]', f'{dict_var}.get({key_expr})')}"
                )
            else:
                fixed_lines.append(line)

        return "\n".join(fixed_lines)

    @staticmethod
    def fix_name_error(source_code: str, analysis: dict[str, Any]) -> str:
        """Fix NameError by correcting the variable name."""
        missing = analysis.get("missing_name", "")
        similar = analysis.get("similar_variables", [])
        lines = source_code.split("\n")

        if not similar:
            return source_code  # Can't fix without knowing the intended name

        correct_name = similar[0]
        fixed_lines = []
        for line in lines:
            # Replace the misspelled name with the correct one
            # Only replace whole-word occurrences
            fixed_line = re.sub(rf'\b{re.escape(missing)}\b', correct_name, line)
            fixed_lines.append(fixed_line)

        return "\n".join(fixed_lines)

    @staticmethod
    def fix_type_error(source_code: str, analysis: dict[str, Any]) -> str:
        """Fix TypeError by adding type conversion."""
        var_types = analysis.get("variable_types", {})
        lines = source_code.split("\n")

        fixed_lines = []
        for line in lines:
            stripped = line.strip()
            fixed = stripped
            # Fix str + int → str + str(int)
            if "+" in stripped and "int" in str(var_types.values()):
                for var, vtype in var_types.items():
                    if vtype == "int" and f"+ {var}" in stripped:
                        fixed = stripped.replace(f"+ {var}", f"+ str({var})")
                    elif vtype == "int" and f"{var} +" in stripped:
                        fixed = stripped.replace(f"{var} +", f"str({var}) +")
            elif "None" in str(var_types.values()):
                for var, vtype in var_types.items():
                    if vtype == "NoneType" and f"{var} +" in stripped:
                        fixed = stripped.replace(f"{var} +", f"({var} or 0) +")
            fixed_lines.append(fixed)

        return "\n".join(fixed_lines)

    @classmethod
    def generate(cls, source_code: str, analysis: dict[str, Any] | None) -> str:
        """Generate corrected code for any supported error type."""
        if not analysis or not source_code:
            return ""

        category = analysis.get("category", "")
        fixers = {
            "index_out_of_range": cls.fix_index_error,
            "division_by_zero": cls.fix_zero_division,
            "key_not_found": cls.fix_key_error,
            "name_not_defined": cls.fix_name_error,
            "type_mismatch": cls.fix_type_error,
        }

        fixer = fixers.get(category)
        if fixer:
            try:
                return fixer(source_code, analysis)
            except Exception as e:
                logger.warning(f"Code fixer failed for {category}: {e}")
                return ""

        return ""


class ExplanationService:
    """
    Generates explanations for code failures.

    Uses AI when available, falls back to deterministic templates
    that now include actual corrected code.
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
        """Generate an explanation for a code failure."""
        if error_info is None:
            return self._empty_explanation()

        if self.provider:
            return self._ai_explain(source_code, error_info, timeline, analysis)
        else:
            return self._deterministic_explain(source_code, error_info, analysis)

    def _ai_explain(
        self,
        source_code: str,
        error_info: dict[str, Any],
        timeline: list[dict[str, Any]],
        analysis: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Generate explanation using the configured AI provider."""
        steps_summary = self._format_last_steps(timeline, count=10)
        variables_at_failure = self._format_failure_variables(timeline)
        analysis_summary = json.dumps(analysis, indent=2) if analysis else "No analysis available."

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
            return self._deterministic_explain(source_code, error_info, analysis)

    def _deterministic_explain(
        self,
        source_code: str,
        error_info: dict[str, Any],
        analysis: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Generate a rich deterministic explanation with corrected code."""
        error_type = error_info.get("type", "Exception")
        error_message = error_info.get("message", "")
        error_line = error_info.get("line", "?")

        analysis_explanation = analysis.get("explanation", "") if analysis else ""

        # Build rich explanation
        what_failed = f"Line {error_line} raised {error_type}: {error_message}"
        why = self._build_why(error_info, analysis)
        execution_sequence = self._build_execution_sequence(error_info, analysis)
        suggested_fix = self._build_suggested_fix(error_info, analysis)
        corrected_code = CodeFixer.generate(source_code, analysis) if analysis else ""

        summary = self._build_summary(error_info, analysis)

        return {
            "summary": summary,
            "what_failed": what_failed,
            "why": why,
            "execution_sequence": execution_sequence,
            "suggested_fix": suggested_fix,
            "corrected_code": corrected_code,
        }

    def _build_summary(self, error_info: dict[str, Any], analysis: dict[str, Any] | None) -> str:
        """Build a beginner-friendly one-sentence summary."""
        error_type = error_info.get("type", "Exception")
        if not analysis:
            return f"Your code raised {error_type} at line {error_info.get('line', '?')}."

        category = analysis.get("category", "")
        summaries = {
            "index_out_of_range": (
                f"Your loop went past the end of "
                f"'{analysis.get('sequence_variable', 'a list')}'. "
                f"It has {analysis.get('sequence_length', '?')} element(s) "
                f"(valid indices {analysis.get('valid_index_range', '?')}), "
                f"but you tried to access index {analysis.get('attempted_index', '?')}."
            ),
            "division_by_zero": (
                f"'{analysis.get('divisor_variable', 'a variable')}' is 0. "
                f"Division by zero is undefined — add a check before dividing."
            ),
            "key_not_found": (
                f"The key {analysis.get('requested_key', '?')!r} doesn't exist in "
                f"'{analysis.get('dictionary_variable', 'the dictionary')}'. "
                f"Use .get() to safely access dictionary keys."
            ),
            "name_not_defined": self._name_error_summary(analysis),
            "type_mismatch": (
                f"You tried to combine incompatible types. "
                f"One value is a {', '.join(analysis.get('involved_types', ['?']))}. "
                f"Convert values to matching types before the operation."
            ),
        }
        return summaries.get(category, f"Your code raised {error_type}.")

    def _name_error_summary(self, analysis: dict[str, Any]) -> str:
        similar = analysis.get("similar_variables", [])
        missing = analysis.get("missing_name", "the variable")
        if similar:
            return (
                f"'{missing}' is not defined. "
                f"Did you mean '{similar[0]}'? The names are very similar."
            )
        return f"'{missing}' is used before being assigned. Define it first."

    def _build_why(self, error_info: dict[str, Any], analysis: dict[str, Any] | None) -> str:
        """Build a detailed 'why it failed' explanation."""
        error_type = error_info.get("type", "Exception")
        error_line = error_info.get("line", "?")

        if not analysis:
            return f"Python raised {error_type} at line {error_line}."

        category = analysis.get("category", "")
        whys = {
            "index_out_of_range": (
                f"'{analysis.get('sequence_variable', 'the sequence')}' has "
                f"{analysis.get('sequence_length', '?')} element(s) (indices "
                f"{analysis.get('valid_index_range', '?')}). When your code tried "
                f"index {analysis.get('attempted_index', '?')}, Python couldn't find "
                f"that position and raised IndexError."
            ),
            "division_by_zero": (
                f"Mathematically, division by zero is undefined. In your code, "
                f"'{analysis.get('divisor_variable', '?')}' has value 0 at line "
                f"{error_line}, so Python raised ZeroDivisionError."
            ),
            "key_not_found": (
                f"The dictionary '{analysis.get('dictionary_variable', '?')}' "
                f"doesn't contain the key {analysis.get('requested_key', '?')!r}. "
                f"Available keys: {analysis.get('available_keys', [])}. "
                f"Accessing a missing key directly with [] raises KeyError."
            ),
            "name_not_defined": self._name_error_why(analysis),
            "type_mismatch": (
                f"Python can't automatically convert between these types. "
                f"The operation at line {error_line} expects compatible types, "
                f"but found: {analysis.get('involved_types', [])}."
            ),
        }
        return whys.get(category, analysis.get("explanation", f"A {error_type} occurred."))

    def _name_error_why(self, analysis: dict[str, Any]) -> str:
        similar = analysis.get("similar_variables", [])
        missing = analysis.get("missing_name", "?")
        if similar:
            return (
                f"Python is case-sensitive. '{similar[0]}' and '{missing}' are "
                f"different variables. You defined '{similar[0]}' but tried to use "
                f"'{missing}', which doesn't exist."
            )
        return f"'{missing}' was never assigned a value before being used."

    def _build_execution_sequence(
        self, error_info: dict[str, Any], analysis: dict[str, Any] | None
    ) -> str:
        """Build a step-by-step execution sequence leading to the failure."""
        if not analysis:
            return f"Execution reached line {error_info.get('line', '?')} and raised {error_info.get('type', 'Exception')}."

        category = analysis.get("category", "")
        sequences = {
            "index_out_of_range": self._index_error_sequence(analysis),
            "division_by_zero": (
                f"1. {analysis.get('divisor_variable', '?')} was set to 0.\n"
                f"2. The code attempted division with this zero value.\n"
                f"3. Python raised ZeroDivisionError — can't divide by zero."
            ),
            "key_not_found": (
                f"1. Dictionary '{analysis.get('dictionary_variable', '?')}' was created.\n"
                f"2. Code tried to access key {analysis.get('requested_key', '?')!r}.\n"
                f"3. Key not found → Python raised KeyError."
            ),
            "name_not_defined": self._name_error_sequence(analysis),
            "type_mismatch": (
                f"1. A variable with a value of an incompatible type was created.\n"
                f"2. The operation expected a different type.\n"
                f"3. Python raised TypeError — types don't match."
            ),
        }
        return sequences.get(category, f"Execution reached the failure point at line {error_info.get('line', '?')}.")

    def _index_error_sequence(self, analysis: dict[str, Any]) -> str:
        seq_var = analysis.get("sequence_variable", "sequence")
        idx_var = analysis.get("index_variable", "index")
        seq_len = analysis.get("sequence_length", "?")
        idx_val = analysis.get("attempted_index", "?")
        return (
            f"1. '{seq_var}' was created with {seq_len} element(s).\n"
            f"2. The loop started, setting {idx_var} = 0.\n"
            f"3. Each iteration: {seq_var}[{idx_var}] is accessed, then {idx_var} increments.\n"
            f"4. When {idx_var} reached {idx_val}, it was outside the valid range.\n"
            f"5. Python raised IndexError — index {idx_val} doesn't exist."
        )

    def _name_error_sequence(self, analysis: dict[str, Any]) -> str:
        similar = analysis.get("similar_variables", [])
        missing = analysis.get("missing_name", "?")
        if similar:
            return (
                f"1. Variable '{similar[0]}' was correctly defined.\n"
                f"2. Code tried to use '{missing}' instead of '{similar[0]}'.\n"
                f"3. Python is case-sensitive: '{similar[0]}' ≠ '{missing}'.\n"
                f"4. Python raised NameError — '{missing}' doesn't exist."
            )
        return f"1. Code tried to use '{missing}'.\n2. '{missing}' was never defined.\n3. Python raised NameError."

    def _build_suggested_fix(self, error_info: dict[str, Any], analysis: dict[str, Any] | None) -> str:
        """Build a concrete, actionable suggested fix."""
        if not analysis:
            return "Check the error line for issues."

        category = analysis.get("category", "")
        fixes = {
            "index_out_of_range": (
                f"Change the loop to use len({analysis.get('sequence_variable', 'the list')}) "
                f"instead of a hardcoded number, or add a bounds check before accessing "
                f"the element. The valid range is {analysis.get('valid_index_range', '?')}."
            ),
            "division_by_zero": (
                f"Add a check: if {analysis.get('divisor_variable', 'divisor')} != 0 "
                f"before the division. Or handle the zero case with a default value."
            ),
            "key_not_found": (
                f"Use {analysis.get('dictionary_variable', 'dict')}.get("
                f"{analysis.get('requested_key', 'key')!r}, default_value) instead of "
                f"square brackets. This returns a default instead of crashing."
            ),
            "name_not_defined": self._name_error_fix(analysis),
            "type_mismatch": (
                f"Convert the value to the correct type before the operation. "
                f"For example, use str() to convert a number to a string, "
                f"or int() to convert a string to an integer."
            ),
        }
        return fixes.get(category, "Review the error line and check the variable values at failure.")

    def _name_error_fix(self, analysis: dict[str, Any]) -> str:
        similar = analysis.get("similar_variables", [])
        missing = analysis.get("missing_name", "?")
        if similar:
            return (
                f"Rename '{missing}' to '{similar[0]}' (the variable you defined). "
                f"Python is case-sensitive, so 'myVar' and 'myvar' are different."
            )
        return f"Define '{missing}' before using it, or check if the variable name has a typo."

    def _format_last_steps(self, timeline: list[dict[str, Any]], count: int = 10) -> str:
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
                parts.append(
                    f"  EXCEPTION: {step['exception']['type']}: {step['exception']['message']}"
                )
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

    def _parse_ai_response(self, raw: str) -> dict[str, Any]:
        """Parse the AI's JSON response, with error recovery."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse AI response as JSON, using raw text")
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
