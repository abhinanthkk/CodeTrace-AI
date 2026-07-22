"""
CodeTrace AI — Executor

Orchestrates the full execution pipeline:
1. Select backend based on EXECUTION_MODE
2. Create temporary files
3. Run code through the selected backend
4. Parse trace results
5. Run deterministic analysis on errors
6. Generate AI/deterministic explanation
7. Return structured response
"""

import logging
from typing import Any

from ..analysis.analyzer import analyze_failure
from ..config import settings
from .backend import ExecutionBackend
from .execution_manager import ExecutionManager
from .subprocess_backend import SubprocessExecutionBackend

logger = logging.getLogger(__name__)


def _create_backend() -> ExecutionBackend:
    """
    Factory: select the execution backend based on EXECUTION_MODE.

    "subprocess" → SubprocessExecutionBackend (always available, default)
    "docker"     → DockerExecutionBackend (requires Docker daemon)
    """
    mode = settings.EXECUTION_MODE.lower().strip()

    if mode == "docker":
        logger.info("Using Docker execution backend")
        try:
            from .docker_backend import DockerExecutionBackend
            return DockerExecutionBackend()
        except ImportError:
            logger.warning("Docker package not installed, falling back to subprocess")
            return SubprocessExecutionBackend()
    elif mode == "subprocess":
        logger.info("Using subprocess execution backend")
        return SubprocessExecutionBackend()
    else:
        logger.warning(f"Unknown EXECUTION_MODE '{mode}', falling back to subprocess")
        return SubprocessExecutionBackend()


class Executor:
    """
    Orchestrates a single code execution from start to finish.
    """

    def __init__(self):
        self.backend = _create_backend()
        self.exec_mgr = ExecutionManager()

    def execute(self, code: str, stdin_data: str = "") -> dict[str, Any]:
        """
        Execute user code and return the full trace result.
        """
        exec_id = self.exec_mgr.create_execution()

        try:
            self.exec_mgr.write_files(exec_id, code, stdin_data)
            exec_dir = self.exec_mgr._executions[exec_id]

            # Run through the selected backend
            result = self.backend.execute(exec_dir, code, stdin_data)
            result["execution_id"] = exec_id

            # Run deterministic analysis if there was a runtime error
            if result.get("error") and result.get("status") == "runtime_error":
                try:
                    analysis = analyze_failure(
                        result["error"],
                        result.get("timeline", []),
                    )
                    result["analysis"] = analysis
                except Exception as e:
                    logger.error(f"Analysis failed: {e}")
                    result["analysis"] = {
                        "category": "analysis_error",
                        "confidence": 0.0,
                        "explanation": f"Analysis engine error: {e}",
                    }

            # Generate AI/deterministic explanation if there's an error
            if result.get("error") and result["status"] not in ("sandbox_error",):
                try:
                    from ..ai.explanation_service import ExplanationService
                    svc = ExplanationService()
                    result["explanation"] = svc.explain(
                        source_code=code,
                        error_info=result.get("error"),
                        timeline=result.get("timeline", []),
                        analysis=result.get("analysis"),
                    )
                except Exception as e:
                    logger.error(f"Explanation failed: {e}")

            # Ensure stdout/stderr are within limits
            max_out = settings.MAX_OUTPUT_SIZE
            if len(result.get("stdout", "")) > max_out:
                result["stdout"] = result["stdout"][:max_out] + "\n...<output truncated>"
                if result.get("status") == "success":
                    result["status"] = "output_limit"
            if len(result.get("stderr", "")) > max_out:
                result["stderr"] = result["stderr"][:max_out] + "\n...<output truncated>"

            return result

        except RuntimeError as e:
            # Backend infrastructure error (e.g., Docker unavailable)
            logger.error(f"Backend error: {e}")
            return {
                "execution_id": exec_id,
                "status": "sandbox_error",
                "stdout": "",
                "stderr": str(e),
                "timeline": [],
            }
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {
                "execution_id": exec_id,
                "status": "sandbox_error",
                "stdout": "",
                "stderr": f"Execution error: {type(e).__name__}: {e}",
                "timeline": [],
            }
        finally:
            self.exec_mgr.cleanup(exec_id)

    def health_check(self) -> dict[str, Any]:
        """Check backend availability."""
        return {
            "execution_mode": self.backend.name,
            "execution_available": self.backend.is_available(),
        }
