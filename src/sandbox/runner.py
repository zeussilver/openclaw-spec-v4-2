"""sandbox/runner.py - Docker container runner for skill verification.

Security flags per spec/security.md §4.1:
- --network none: Disable network access
- --read-only: Read-only root filesystem
- --cap-drop ALL: Remove all capabilities
- --memory 512m: Limit memory
- --pids-limit 128: Limit processes
- --security-opt no-new-privileges:true: Prevent privilege escalation
"""
import time
from pathlib import Path
from typing import Any

import docker
from docker.errors import APIError, ImageNotFound


class SandboxRunner:
    """Docker-based sandbox runner for skill verification."""

    def __init__(
        self,
        image: str = "openclaw-sandbox:latest",
        timeout: int = 30,
        network_mode: str = "none",
        allow_network: bool = False,
    ):
        """Initialize sandbox runner.

        Args:
            image: Docker image name for sandbox
            timeout: Maximum execution time in seconds
            network_mode: Docker network mode (default: "none")
            allow_network: Require explicit opt-in for non-"none" network modes
        """
        if network_mode != "none" and not allow_network:
            raise ValueError("network_mode requires allow_network=True")
        self.image = image
        self.timeout = timeout
        self.network_mode = network_mode
        self._client: docker.DockerClient | None = None

    @property
    def client(self) -> docker.DockerClient:
        """Lazy-load Docker client."""
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def is_available(self) -> bool:
        """Check if Docker daemon is available and image exists.

        Returns:
            True if Docker is ready to run sandboxes
        """
        try:
            self.client.ping()
            self.client.images.get(self.image)
            return True
        except (APIError, ImageNotFound, Exception):
            return False

    def run(
        self, skill_path: Path, output_path: Path | None = None
    ) -> tuple[bool, str, dict[str, Any]]:
        """Run skill verification in Docker sandbox.

        Args:
            skill_path: Path to skill directory containing skill.py
            output_path: Optional path for output (mounted as /output)

        Returns:
            Tuple of (passed, logs, metrics)
            - passed: True only if exit_code == 0 AND "VERIFICATION_SUCCESS" in logs
            - logs: Container stdout/stderr
            - metrics: Dict with exit_code, duration_ms, etc.
        """
        container = None
        logs = ""
        start_time = time.time()
        metrics: dict[str, Any] = {}

        # Prepare volumes
        volumes = {
            str(skill_path.absolute()): {"bind": "/skill", "mode": "ro"},
        }
        if output_path is not None:
            output_path.mkdir(parents=True, exist_ok=True)
            volumes[str(output_path.absolute())] = {"bind": "/output", "mode": "rw"}

        try:
            container = self.client.containers.run(
                self.image,
                command=["python", "/sandbox/harness.py", "/skill"],
                volumes=volumes,
                # Security: Network isolation (default: none)
                network_mode=self.network_mode,
                # Security: Read-only filesystem
                read_only=True,
                # Security: Resource limits
                mem_limit="512m",
                memswap_limit="512m",
                cpu_period=100000,
                cpu_quota=100000,  # 1 CPU
                pids_limit=128,
                # Security: Drop all capabilities
                cap_drop=["ALL"],
                # Security: Prevent privilege escalation
                security_opt=["no-new-privileges:true"],
                # Security: Limited /tmp
                tmpfs={"/tmp": "size=64m,noexec"},
                # Run detached so we can wait with timeout
                detach=True,
            )

            # Wait for completion with timeout
            try:
                result = container.wait(timeout=self.timeout)
                exit_code = result.get("StatusCode", 1)
            except Exception:
                # Timeout or other error during wait
                exit_code = -1
                metrics["timeout"] = True

            # Get logs before cleanup
            try:
                logs = container.logs().decode("utf-8", errors="replace")
            except Exception:
                logs = ""

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            metrics["exit_code"] = exit_code
            metrics["duration_ms"] = duration_ms

            # CRITICAL: Both conditions must be true
            # 1. Exit code must be 0
            # 2. Logs must contain VERIFICATION_SUCCESS
            passed = exit_code == 0 and "VERIFICATION_SUCCESS" in logs

            return passed, logs, metrics

        except ImageNotFound:
            return False, f"Docker image not found: {self.image}", {"error": "image_not_found"}

        except APIError as e:
            return False, f"Docker API error: {e}", {"error": "api_error"}

        except Exception as e:
            # Try to get logs if container was created
            if container:
                try:
                    logs = container.logs().decode("utf-8", errors="replace")
                except Exception:
                    pass
            return False, f"{logs}\nRunner error: {e}", {"error": str(e)}

        finally:
            # ALWAYS cleanup container
            if container:
                try:
                    container.kill()
                except Exception:
                    pass
                try:
                    container.remove(force=True)
                except Exception:
                    pass
