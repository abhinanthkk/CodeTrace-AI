"""
CodeTrace AI — Executor

Orchestrates the full execution pipeline:
1. Create temporary files
2. Run code in Docker sandbox
3. Parse trace results
4. Run deterministic analysis on errors
5. Return structured response
"""

import logging
from typing import Any

from ..analysis.analyzer import analyze_failure
from .execution_manager import ExecutionManager
from .sandbox import SandboxError, SandboxManager

logger = logging.getLogger(__name__)


class Executor:
    """
    Orchestrates a single code execution from start to finish.

    Usage:
        executor = Executor()
        result = await executor.execute(code="...", input="...")
    """

    def __init__(self):
        self.sandbox = SandboxManager()
        self.exec_mgr = ExecutionManager()

    def execute(self, code: str, stdin_data: str = "") -> dict[str, Any]:
        """
        Execute user code and return the full trace result.

        Args:
            code: Python source code to trace
            stdin_data: Optional standard input for the program

        Returns:
            Dict with execution_id, status, stdout, stderr, timeline,
            error, analysis (ready for the API response).
        """
        exec_id = self.exec_mgr.create_execution()

        try:
            # Write user files
            self.exec_mgr.write_files(exec_id, code, stdin_data)
            exec_dir = self.exec_mgr._executions[exec_id]

            # Run in sandbox
            result = self.sandbox.run(exec_dir)
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

            # Ensure stdout/stderr are within limits
            max_out = 256 * 1024  # 256 KB
            if len(result.get("stdout", "")) > max_out:
                result["stdout"] = result["stdout"][:max_out] + "\n...<output truncated>"
                if result.get("status") == "success":
                    result["status"] = "output_limit"
            if len(result.get("stderr", "")) > max_out:
                result["stderr"] = result["stderr"][:max_out] + "\n...<output truncated>"

            return result

        except SandboxError as e:
            logger.error(f"Sandbox error: {e}")
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
        """Check if the sandbox is available."""
        return {
            "docker_available": self.sandbox.is_available(),
            "sandbox_image": self.sandbox.image,
        }
