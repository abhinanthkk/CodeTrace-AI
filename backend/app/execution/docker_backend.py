"""
CodeTrace AI — Docker Execution Backend

Runs user code inside an isolated Docker container.
This is the recommended execution mode for local development.

Requires:
- Docker daemon with accessible socket
- codetrace-sandbox Docker image (pre-built)
"""

import json
import logging
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException, ImageNotFound
from docker.models.containers import Container

from ..config import settings
from .backend import ExecutionBackend

logger = logging.getLogger(__name__)


class DockerExecutionBackend(ExecutionBackend):
    """
    Executes user code in an isolated Docker container.

    Security properties:
    - Container has no network access (--network none)
    - Read-only filesystem with writable /tmp only
    - Non-root user (sandbox)
    - CPU and memory limits enforced by Docker
    - Execution timeout enforced by the host
    - Container auto-removed after execution
    """

    def __init__(self):
        self.image = settings.SANDBOX_IMAGE
        self.timeout = settings.EXECUTION_TIMEOUT
        self.memory = settings.EXECUTION_MEMORY
        self.cpu = settings.EXECUTION_CPU
        self._client: docker.DockerClient | None = None

    @property
    def name(self) -> str:
        return "docker"

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            try:
                self._client = docker.from_env()
            except DockerException as e:
                raise RuntimeError(f"Docker is not available: {e}") from e
        return self._client

    def is_available(self) -> bool:
        try:
            self.client.images.get(self.image)
            return True
        except (DockerException, ImageNotFound):
            return False

    def execute(self, exec_dir: Path, code: str, stdin_data: str) -> dict[str, Any]:
        code_file = exec_dir / "user_code.py"
        stdin_file = exec_dir / "stdin.txt"

        if not code_file.exists():
            return self._error_result("Code file not found")

        container: Container | None = None
        try:
            container = self.client.containers.run(
                image=self.image,
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

            try:
                exit_info = container.wait(timeout=self.timeout + 2)
                exit_code = exit_info.get("StatusCode", -1)
            except Exception:
                self._kill(container)
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
                try:
                    return self._parse_output(logs)
                except Exception:
                    return self._error_result(logs[:1000])

        except docker.errors.ContainerError as e:
            logger.error(f"Container error: {e}")
            return self._error_result(str(e)[:1000])
        except Exception as e:
            logger.error(f"Docker backend failed: {e}")
            raise RuntimeError(f"Docker execution failed: {e}") from e
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

    def _parse_output(self, logs: str) -> dict[str, Any]:
        logs = logs.strip()
        try:
            return json.loads(logs)
        except json.JSONDecodeError:
            pass
        try:
            start = logs.rindex("{")
            return json.loads(logs[start:])
        except (ValueError, json.JSONDecodeError):
            return self._error_result(logs[:1000])

    def _kill(self, container: Container) -> None:
        try:
            container.kill()
        except Exception:
            pass

    def _error_result(self, message: str) -> dict[str, Any]:
        return {
            "status": "sandbox_error",
            "stdout": "",
            "stderr": message,
            "timeline": [],
        }
