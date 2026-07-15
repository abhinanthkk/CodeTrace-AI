"""
CodeTrace AI — Execution Manager

Manages temporary directories and execution lifecycle.
Each execution gets a unique ID and an isolated temp directory
that is cleaned up after the execution completes.
"""

import logging
import tempfile
import uuid
from pathlib import Path

from ..config import settings

logger = logging.getLogger(__name__)


class ExecutionManager:
    """
    Creates temporary execution environments and cleans them up.

    Usage:
        manager = ExecutionManager()
        exec_id = manager.create_execution()
        manager.write_files(exec_id, code="...", stdin="...")
        # ... run sandbox ...
        manager.cleanup(exec_id)
    """

    def __init__(self):
        self._executions: dict[str, Path] = {}
        self._base_dir = Path(tempfile.gettempdir()) / "codetrace_executions"

    def create_execution(self) -> str:
        """Create a new execution directory and return its ID."""
        exec_id = str(uuid.uuid4())
        exec_dir = self._base_dir / exec_id
        exec_dir.mkdir(parents=True, exist_ok=True)
        self._executions[exec_id] = exec_dir
        return exec_id

    def write_files(self, exec_id: str, code: str, stdin_data: str = "") -> Path:
        """
        Write the user's code and stdin data to the execution directory.

        Returns the path to the execution directory.
        """
        exec_dir = self._executions.get(exec_id)
        if not exec_dir:
            raise ValueError(f"Unknown execution ID: {exec_id}")

        # Validate size limits
        if len(code) > settings.MAX_CODE_SIZE:
            raise ValueError(f"Code exceeds maximum size of {settings.MAX_CODE_SIZE} bytes")
        if len(stdin_data) > settings.MAX_INPUT_SIZE:
            raise ValueError(f"Input exceeds maximum size of {settings.MAX_INPUT_SIZE} bytes")

        code_file = exec_dir / "user_code.py"
        stdin_file = exec_dir / "stdin.txt"

        code_file.write_text(code, encoding="utf-8")
        stdin_file.write_text(stdin_data, encoding="utf-8")

        return exec_dir

    def cleanup(self, exec_id: str) -> None:
        """Remove the execution directory and all its files."""
        exec_dir = self._executions.pop(exec_id, None)
        if exec_dir and exec_dir.exists():
            import shutil
            try:
                shutil.rmtree(exec_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup {exec_id}: {e}")

    def cleanup_all(self) -> None:
        """Remove all execution directories."""
        for exec_id in list(self._executions.keys()):
            self.cleanup(exec_id)
