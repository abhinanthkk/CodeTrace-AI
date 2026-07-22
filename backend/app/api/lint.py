"""
CodeTrace Live Fix — Lint API

POST /api/lint — Run Ruff diagnostics on Python code.
"""

import logging

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..linting.ruff_runner import check_ruff_available, run_ruff_safe
from ..linting.diagnostic_processor import process_diagnostics
from ..models.requests import LintRequest
from ..models.responses import LintResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/lint", response_model=LintResponse)
async def lint_code(request: LintRequest):
    """
    Run Ruff static analysis on Python source code.

    Code is sent via stdin to Ruff. No execution occurs.
    Returns normalized diagnostics ready for the frontend.
    """
    if request.code is None:
        raise HTTPException(status_code=400, detail="Code field is required")

    code = request.code

    if len(code) > settings.MAX_CODE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Code exceeds maximum size of {settings.MAX_CODE_SIZE} bytes",
        )

    # Empty code → no diagnostics
    if not code.strip():
        return LintResponse(
            status="success",
            diagnostics=[],
            ruff_available=check_ruff_available(),
        )

    # Run Ruff
    raw = run_ruff_safe(code)
    diagnostics = process_diagnostics(raw)

    return LintResponse(
        status="success",
        diagnostics=diagnostics,
        ruff_available=check_ruff_available(),
    )
