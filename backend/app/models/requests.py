"""
CodeTrace AI — Pydantic Request Models
"""

from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    """POST /api/execute request body."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=64 * 1024,
        description="Python source code to execute and trace",
    )
    input: str = Field(
        default="",
        max_length=64 * 1024,
        description="Optional standard input for the program",
    )


class LintRequest(BaseModel):
    """POST /api/lint request body."""

    code: str = Field(
        ...,
        min_length=0,
        max_length=64 * 1024,
        description="Python source code to lint (can be empty)",
    )


class FixRequest(BaseModel):
    """POST /api/fix request body."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=64 * 1024,
        description="Full Python source code",
    )
    diagnostic_ids: list[str] = Field(
        default_factory=list,
        description="IDs of diagnostics to fix",
    )
