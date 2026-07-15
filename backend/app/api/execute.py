"""
CodeTrace AI — Execute API

POST /api/execute  — Run Python code with tracing
GET  /api/health   — Application health check
"""

import logging

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..execution.executor import Executor
from ..models.requests import ExecuteRequest
from ..models.responses import ExecuteResponse, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Single executor instance (stateless, safe to reuse)
executor = Executor()


@router.post("/execute", response_model=ExecuteResponse)
async def execute_code(request: ExecuteRequest):
    """
    Execute Python code with runtime tracing.

    The code runs inside an isolated Docker sandbox with:
    - No network access
    - CPU and memory limits
    - Execution timeout

    Returns a structured trace timeline, error information,
    deterministic failure analysis, and (optionally) AI explanation.
    """
    # Validate
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")

    if len(request.code) > settings.MAX_CODE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Code exceeds maximum size of {settings.MAX_CODE_SIZE} bytes",
        )

    # Execute
    try:
        result = executor.execute(request.code, request.input)
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}")

    # Check for sandbox infrastructure errors
    if result["status"] == "sandbox_error":
        raise HTTPException(
            status_code=500,
            detail=f"Sandbox error: {result.get('stderr', 'Unknown error')}",
        )

    return ExecuteResponse(
        execution_id=result["execution_id"],
        status=result["status"],
        stdout=result.get("stdout", ""),
        stderr=result.get("stderr", ""),
        timeline=result.get("timeline", []),
        error=result.get("error"),
        analysis=result.get("analysis"),
        explanation=result.get("explanation"),
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Return application and sandbox health status."""
    sandbox_available = False
    try:
        sandbox_available = executor.sandbox.is_available()
    except Exception:
        pass

    return HealthResponse(
        status="healthy",
        sandbox_available=sandbox_available,
        ai_configured=settings.ai_configured,
    )
