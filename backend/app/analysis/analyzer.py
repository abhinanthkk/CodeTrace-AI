"""
CodeTrace AI — Failure Analyzer

Entry point for deterministic failure analysis.
Dispatches to the appropriate per-exception analyzer.

Each analyzer extracts structured evidence from the trace data:
- Variable state at failure
- Timeline leading to failure
- Exception details

Analyzers return evidence with confidence scores. If confidence is low,
the application falls back to generic analysis — we never fabricate.
"""

from typing import Any

from .error_classifier import get_analyzer


class GenericAnalyzer:
    """
    Fallback analyzer for unsupported exception types.
    Returns basic exception information without speculative analysis.
    """

    def analyze(
        self,
        error_info: dict[str, Any],
        timeline: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "category": "unknown",
            "error_type": error_info.get("type", "unknown"),
            "message": error_info.get("message", ""),
            "confidence": 0.0,
            "note": "No specialized analyzer available for this exception type.",
        }


def analyze_failure(
    error_info: dict[str, Any] | None,
    timeline: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Analyze an execution failure and return structured evidence.

    Args:
        error_info: Exception dict from the tracer (type, message, line, ...)
        timeline: Processed execution timeline

    Returns:
        Structured analysis dict, or None if there is no error to analyze.
    """
    if error_info is None:
        return None

    exception_type = error_info.get("type", "Exception")
    analyzer = get_analyzer(exception_type)
    return analyzer.analyze(error_info, timeline)
