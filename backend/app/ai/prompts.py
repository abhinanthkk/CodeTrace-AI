"""
CodeTrace AI — Prompt Templates

Strict prompts that force the AI model to only use the provided
execution evidence. The model must not invent variable states or
execution events.
"""

EXPLANATION_PROMPT = """
You are analyzing a Python program that failed with an error.

## Source Code
```python
{source_code}
```

## Error
- Type: {error_type}
- Message: {error_message}
- Failed at line {error_line}

## Variable State at Failure
{variables_at_failure}

## Last Execution Steps Before Failure
{execution_steps}

## Deterministic Analysis
{analysis_summary}

## Instructions
Using ONLY the evidence above, generate a JSON object with these fields:

1. "summary": One sentence explaining what went wrong (beginner-friendly).
2. "what_failed": Which line and operation failed.
3. "why": Why the failure occurred, referencing the actual variable values from the evidence.
4. "execution_sequence": A step-by-step walkthrough of how execution led to the failure, citing actual values.
5. "suggested_fix": A concrete fix for the code (beginner-friendly language, no jargon).
6. "corrected_code": The corrected Python code.

CRITICAL RULES:
- ONLY use variable names and values present in the evidence above.
- DO NOT invent or assume any variable state not provided.
- If you are uncertain about something, say so instead of guessing.
- Use the exact variable values from the evidence.
- The "corrected_code" should be a complete, runnable version of the source code with the fix applied.

Return ONLY valid JSON. No markdown, no explanation outside the JSON.
"""


DETERMINISTIC_TEMPLATE = """
## What Failed
{what_failed}

## Why It Failed
{why}

## Execution Sequence
{execution_sequence}

## Suggested Fix
{suggested_fix}

## Corrected Code
```python
{corrected_code}
```
"""
