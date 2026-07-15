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
