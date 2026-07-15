"""
CodeTrace Live Fix — AI Block Fix Service

Uses the existing AI provider to generate contextual fixes for
groups of related diagnostics.

STRICT PROMPT DESIGN: The AI receives ONLY static diagnostics and
source code. It must NOT invent runtime data.
"""

import json
import logging
import re
from typing import Any

from .provider import create_provider

logger = logging.getLogger(__name__)

BLOCK_FIX_PROMPT = """You are CodeTrace's contextual Python repair engine.

You receive a Python code block and VERIFIED Ruff static diagnostics.
Your job is to propose the smallest logically consistent correction.

## Rules
- Use ONLY the supplied source code and diagnostics.
- Do NOT invent runtime variable values or claim code was executed.
- Preserve the developer's apparent intent.
- Modify only code necessary to resolve the related diagnostics.
- Do NOT refactor unrelated code.
- Do NOT add external dependencies unless absolutely necessary.
- Return structured JSON ONLY — no markdown, no explanation outside the JSON.

## Scope
Type: {scope_type}
Name: {scope_name}
Lines: {start_line}–{end_line}

## Diagnostics
{diagnostics_json}

## Code Block
```python
{code_block}
```

## Output Format
Return exactly this JSON structure:
{{
  "title": "Brief description of the fix",
  "explanation": "Detailed explanation of what was wrong and how it is fixed",
  "fixed_code": "The corrected code block",
  "changes": [
    {{"description": "What changed 1"}},
    {{"description": "What changed 2"}}
  ],
  "confidence": 0.88
}}
"""


class BlockFixService:
    """Generates AI-powered block fixes using the existing AI provider."""

    def __init__(self):
        self.provider = create_provider()

    def generate_block_fix(
        self,
        full_code: str,
        group: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate an AI block fix for a group of related diagnostics.

        Args:
            full_code: Complete source code
            group: Diagnostic group from scope_grouper

        Returns:
            FixResponse-compatible dict
        """
        if not self.provider:
            return self._ai_unavailable()

        # Extract the relevant code block
        start_line = group.get("start_line", 1)
        end_line = group.get("end_line", start_line)
        code_lines = full_code.split("\n")
        code_block = "\n".join(code_lines[start_line - 1 : end_line])

        # Format diagnostics
        diags_json = json.dumps(
            [
                {
                    "code": d.get("code"),
                    "message": d.get("message"),
                    "line": d.get("line"),
                }
                for d in group.get("diagnostics", [])
            ],
            indent=2,
        )

        prompt = BLOCK_FIX_PROMPT.format(
            scope_type=group.get("scope_type", "unknown"),
            scope_name=group.get("scope_name", "unknown"),
            start_line=start_line,
            end_line=end_line,
            diagnostics_json=diags_json,
            code_block=code_block,
        )

        try:
            raw = self.provider.generate(prompt)
            parsed = self._parse_and_validate(raw, code_block)

            # Build the fixed full code
            fixed_full_code = self._replace_block(
                full_code, start_line, end_line, parsed.get("fixed_code", code_block)
            )

            return {
                "status": "success",
                "fix_type": "block",
                "title": parsed.get("title", "AI Block Fix"),
                "explanation": parsed.get("explanation", ""),
                "confidence": parsed.get("confidence", 0.7),
                "original_code": code_block,
                "fixed_code": fixed_full_code,
                "edits": [],
                "affected_lines": {"start": start_line, "end": end_line},
                "requires_ai": True,
                "changes": parsed.get("changes", []),
            }

        except Exception as e:
            logger.error(f"Block fix generation failed: {e}")
            return {
                "status": "ai_error",
                "fix_type": "block",
                "title": "AI fix generation failed",
                "explanation": f"Error: {e}",
                "confidence": 0.0,
                "requires_ai": True,
            }

    def _parse_and_validate(self, raw: str, original_code: str) -> dict[str, Any]:
        """Parse AI JSON response and validate the fixed code."""
        # Strip markdown fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            try:
                start = cleaned.index("{")
                end = cleaned.rindex("}") + 1
                result = json.loads(cleaned[start:end])
            except (ValueError, json.JSONDecodeError):
                raise ValueError("AI returned invalid JSON")

        # Validate required fields
        if not result.get("title"):
            raise ValueError("AI response missing 'title'")

        # Validate fixed_code parses as Python
        fixed_code = result.get("fixed_code", "")
        if fixed_code:
            try:
                import ast
                ast.parse(fixed_code)
            except SyntaxError as e:
                logger.warning(f"AI generated invalid Python: {e}")
                # Don't reject — the code might be incomplete
                # Lower confidence instead
                result["confidence"] = min(result.get("confidence", 0.5), 0.4)
                result["_validation_note"] = f"Fixed code has syntax issues: {e}"

        return result

    def _replace_block(
        self, full_code: str, start: int, end: int, replacement: str
    ) -> str:
        """Replace a line range in the full source with new code."""
        lines = full_code.split("\n")
        before = lines[: start - 1]
        after = lines[end:]
        result = before + replacement.split("\n") + after
        return "\n".join(result)

    def _ai_unavailable(self) -> dict[str, Any]:
        return {
            "status": "ai_unavailable",
            "fix_type": "block",
            "title": "AI not configured",
            "explanation": "Add an AI API key to enable contextual block fixes.",
            "confidence": 0.0,
            "requires_ai": True,
        }
