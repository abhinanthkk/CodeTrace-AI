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
