"""
CodeTrace AI — Pydantic Response Models
"""

from typing import Any
from pydantic import BaseModel, Field


class VariableChange(BaseModel):
    type: str  # "created" | "updated" | "deleted"
    value: Any | None = None
    old_value: Any | None = None
    new_value: Any | None = None


class TimelineStep(BaseModel):
    step: int
    event: str  # "line" | "call" | "return" | "exception" | "system"
    line: int
    function: str
    changes: dict[str, dict[str, Any]] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    output: str = ""
    exception: dict[str, Any] | None = None
    return_value: Any | None = None


class ErrorInfo(BaseModel):
    type: str
    message: str
    line: int
    function: str = ""
    traceback_frames: list[dict[str, Any]] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    category: str
    error_type: str = ""
    confidence: float = 0.0
    explanation: str = ""
    # Additional evidence fields vary by analyzer
    model_config = {"extra": "allow"}


class ExplanationResult(BaseModel):
    summary: str = ""
    what_failed: str = ""
    why: str = ""
    execution_sequence: str = ""
    suggested_fix: str = ""
    corrected_code: str = ""


class ExecuteResponse(BaseModel):
    execution_id: str
    status: str  # success | runtime_error | syntax_error | timeout | ...
    stdout: str = ""
    stderr: str = ""
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    error: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    explanation: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: str
    sandbox_available: bool
    ai_configured: bool
    version: str = "0.1.0"
    execution_mode: str = ""


# ── Live Fix / Linting Models ─────────────────────────────────────────────

class DiagnosticFix(BaseModel):
    message: str = ""
    applicability: str = ""
    edits: list[dict[str, Any]] = Field(default_factory=list)


class DiagnosticInfo(BaseModel):
    id: str
    code: str
    message: str
    severity: str  # "error" | "warning" | "info"
    line: int
    column: int
    end_line: int = 0
    end_column: int = 0
    source: str = "ruff"
    fix_available: bool = False
    fix_type: str | None = None
    raw_fix: dict[str, Any] | None = None


class LintResponse(BaseModel):
    status: str
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    ruff_available: bool = True


class FixEdit(BaseModel):
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    replacement: str = ""


class FixResponse(BaseModel):
    status: str  # "success" | "no_diagnostics" | "no_fix_available" | "ai_unavailable" | "ai_error"
    fix_type: str = "quick"  # "quick" | "block"
    title: str = ""
    explanation: str = ""
    confidence: float = 0.0
    original_code: str | None = None
    fixed_code: str | None = None
    edits: list[dict[str, Any]] = Field(default_factory=list)
    affected_lines: dict[str, int] = Field(default_factory=dict)
    requires_ai: bool = False
    changes: list[dict[str, Any]] | None = None
