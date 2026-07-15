"""
CodeTrace AI — Execution Backend Abstraction

Defines the interface for code execution backends.
The executor selects a backend based on EXECUTION_MODE:
- "docker":     DockerExecutionBackend (local dev, full sandbox)
- "subprocess": SubprocessExecutionBackend (free cloud hosting)
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ExecutionBackend(ABC):
    """Abstract interface for code execution backends."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether this backend can execute code right now."""
        ...

    @abstractmethod
    def execute(self, exec_dir: Path, code: str, stdin_data: str) -> dict[str, Any]:
        """
        Execute user code and return a trace result dict.

        Args:
            exec_dir: Directory containing user_code.py and stdin.txt
            code: The user's Python source code
            stdin_data: Standard input text for the program

        Returns:
            Dict with status, stdout, stderr, timeline, optional error.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name for health checks."""
        ...
