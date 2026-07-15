"""
CodeTrace Live Fix — Fix API

POST /api/fix — Generate fix proposals for selected diagnostics.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..linting.ruff_runner import run_ruff_safe
from ..linting.diagnostic_processor import process_diagnostics
from ..linting.quick_fix import generate_quick_fix, classify_fix_type
from ..linting.scope_grouper import group_diagnostics
from ..models.requests import FixRequest
from ..models.responses import FixResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/fix", response_model=FixResponse)
async def propose_fix(request: FixRequest):
    """
    Generate a fix proposal for selected diagnostics.

    Classifies as quick_fix (deterministic) or block_fix (AI-assisted),
    generates the appropriate fix, and returns it for user approval.
    Fixes are NEVER applied server-side.
    """
    code = request.code
    diagnostic_ids = set(request.diagnostic_ids)

    if not code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")

    if len(code) > settings.MAX_CODE_SIZE:
        raise HTTPException(status_code=400, detail="Code exceeds maximum size")

    # Re-run Ruff to get current diagnostics (code may have changed)
    raw = run_ruff_safe(code)
    current_diags = process_diagnostics(raw)

    # Find the requested diagnostics in current results
    selected = [d for d in current_diags if d.get("id") in diagnostic_ids]

    if not selected:
        return FixResponse(
            status="no_diagnostics",
            fix_type="quick",
            title="No matching diagnostics found",
            explanation="The code may have changed since linting. Re-run lint and try again.",
            confidence=0.0,
            requires_ai=False,
        )

    # Classify: quick or block
    fix_type = classify_fix_type(selected, code)

    if fix_type == "quick_fix":
        # Try deterministic quick fix for the first diagnostic
        quick = generate_quick_fix(selected[0], code)
        if quick:
            return FixResponse(
                status="success",
                fix_type=quick["fix_type"],
                title=quick["title"],
                explanation=quick["explanation"],
                confidence=quick["confidence"],
                edits=quick.get("edits", []),
                fixed_code=apply_edits(code, quick.get("edits", [])),
                affected_lines=quick.get("affected_lines", {}),
                requires_ai=quick.get("requires_ai", False),
            )
        else:
            return FixResponse(
                status="no_fix_available",
                fix_type="quick",
                title="No deterministic fix available",
                explanation="Could not generate a quick fix for this diagnostic. Try AI Block Fix.",
                confidence=0.0,
                requires_ai=True,
            )

    # Block fix — requires AI
    if not settings.ai_configured:
        return FixResponse(
            status="ai_unavailable",
            fix_type="block",
            title="AI not configured",
            explanation="Add an AI API key to enable contextual block fixes.",
            confidence=0.0,
            requires_ai=True,
        )

    # Group related diagnostics
    groups = group_diagnostics(selected, code)
    if not groups:
        return FixResponse(
            status="no_fix_available",
            fix_type="block",
            title="Could not group diagnostics",
            explanation="No logical grouping found for the selected diagnostics.",
            confidence=0.0,
            requires_ai=True,
        )

    # Use the first group
    group = groups[0]

    # Call AI block fix
    try:
        from ..ai.block_fix_service import BlockFixService
        svc = BlockFixService()
        result = svc.generate_block_fix(code, group)
        return result
    except Exception as e:
        logger.error(f"Block fix failed: {e}")
        return FixResponse(
            status="ai_error",
            fix_type="block",
            title="AI fix generation failed",
            explanation=f"Error: {e}",
            confidence=0.0,
            requires_ai=True,
        )


def apply_edits(code: str, edits: list[dict[str, Any]]) -> str:
    """
    Apply a list of edits to source code.

    Edits are applied from end to start to preserve line/column positions.
    Each edit: {start_line, start_column, end_line, end_column, replacement}
    """
    lines = code.split("\n")
    # Sort edits from end to start
    sorted_edits = sorted(edits, key=lambda e: (e["start_line"], e["start_column"]), reverse=True)

    for edit in sorted_edits:
        sl = edit["start_line"] - 1  # 0-indexed
        el = edit["end_line"] - 1
        sc = edit["start_column"] - 1
        ec = edit["end_column"] - 1
        repl = edit.get("replacement", "")

        if sl == el:
            # Single-line edit
            if sl < len(lines):
                line = lines[sl]
                lines[sl] = line[:sc] + repl + line[ec:]
        else:
            # Multi-line edit: replace the range
            if sl < len(lines):
                lines[sl] = lines[sl][:sc] + repl
                # Remove lines between sl+1 and el
                for i in range(el, sl, -1):
                    if i < len(lines):
                        lines.pop(i)

    return "\n".join(lines)
