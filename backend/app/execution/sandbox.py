"""
CodeTrace AI — Docker Sandbox Manager (OPTIONAL)

Manages Docker containers for isolated code execution.
This module is NOT imported by the main execution flow.
It is kept as a reference for optional Docker-based execution.

Each execution gets a fresh container with:
- No network access
- CPU and memory limits
- Read-only filesystem (writable /tmp only)
- Non-root user
- Execution timeout
"""

import json
import logging
from pathlib import Path
from typing import Any

try:
    import docker
    from docker.errors import DockerException, ImageNotFound, NotFound
    from docker.models.containers import Container
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

from ..config import settings

logger = logging.getLogger(__name__)


class SandboxError(Exception):
    """Raised when the sandbox encounters an infrastructure error."""


class SandboxManager:
    """
    Manages Docker-based sandbox execution.

    Usage:
        manager = SandboxManager()
        result = manager.run(temp_dir)
    """

    def __init__(self):
        self.image = settings.SANDBOX_IMAGE
        self.timeout = settings.EXECUTION_TIMEOUT
        self.memory = settings.EXECUTION_MEMORY
        self.cpu = settings.EXECUTION_CPU
        self._client: docker.DockerClient | None = None

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            try:
                self._client = docker.from_env()
            except DockerException as e:
                raise SandboxError(f"Docker is not available: {e}") from e
        return self._client

    def is_available(self) -> bool:
        """Check if Docker and the sandbox image are available."""
        try:
            self.client.images.get(self.image)
            return True
        except (DockerException, ImageNotFound):
            return False

    def run(self, exec_dir: Path) -> dict[str, Any]:
        """
        Execute user code in a Docker sandbox.

        Args:
            exec_dir: Directory containing user_code.py and stdin.txt

        Returns:
            Parsed JSON trace result from the sandbox runner.

        Raises:
            SandboxError: On Docker/infrastructure failures.
        """
        code_file = exec_dir / "user_code.py"
        stdin_file = exec_dir / "stdin.txt"

        if not code_file.exists():
            raise SandboxError(f"Code file not found: {code_file}")

        # Build the docker run command
        container: Container | None = None
        try:
            container = self.client.containers.run(
                image=self.image,
                # ENTRYPOINT is "python /runner.py", so command is just the args
                command=["/exec/user_code.py", "/exec/stdin.txt"],
                volumes={
                    str(exec_dir.resolve()): {
                        "bind": "/exec",
                        "mode": "ro",
                    },
                },
                network_mode="none",
                mem_limit=self.memory,
                nano_cpus=int(float(self.cpu) * 1_000_000_000),
                read_only=True,
                tmpfs={"/tmp": "size=16m,mode=1777"},
                working_dir="/workspace",
                user="sandbox",
                detach=True,
                stdout=True,
                stderr=True,
            )

            # Wait for the container to finish or timeout
            try:
                exit_info = container.wait(timeout=self.timeout + 2)
                exit_code = exit_info.get("StatusCode", -1)
            except Exception:
                # Timeout
                self._kill_container(container)
                return {
                    "status": "timeout",
                    "stdout": "",
                    "stderr": f"Execution timed out after {self.timeout}s",
                    "timeline": [],
                }

            logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")

            if exit_code == 0:
                return self._parse_output(logs)
            else:
                # Try to parse output even on non-zero exit
                try:
                    return self._parse_output(logs)
                except Exception:
                    return {
                        "status": "sandbox_error",
                        "stdout": "",
                        "stderr": logs[:1000],
                        "timeline": [],
                    }

        except docker.errors.ContainerError as e:
            logger.error(f"Container error: {e}")
            return {
                "status": "sandbox_error",
                "stdout": "",
                "stderr": str(e)[:1000],
                "timeline": [],
            }
        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            raise SandboxError(f"Execution failed: {e}") from e
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

    def _parse_output(self, logs: str) -> dict[str, Any]:
        """Parse the JSON output from the sandbox runner."""
        # The runner prints JSON to stdout; find the last complete JSON object
        # in case there are warnings or other output before it.
        logs = logs.strip()

        # Try parsing the entire output first
        try:
            return json.loads(logs)
        except json.JSONDecodeError:
            pass

        # Try to find a JSON object in the output
        # Look for the last '{' and try to parse from there
        try:
            start = logs.rindex("{")
            return json.loads(logs[start:])
        except (ValueError, json.JSONDecodeError):
            return {
                "status": "sandbox_error",
                "stdout": "",
                "stderr": logs[:1000],
                "timeline": [],
            }

    def _kill_container(self, container: Container) -> None:
        """Force-kill a container that has timed out."""
        try:
            container.kill()
        except Exception:
            pass

    def check_image(self) -> bool:
        """Verify the sandbox image exists, return False if not."""
        try:
            self.client.images.get(self.image)
            return True
        except (DockerException, ImageNotFound):
            return False
