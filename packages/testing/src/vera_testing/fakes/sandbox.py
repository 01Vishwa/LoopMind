"""FakeSandbox — scripted sandbox implementation for unit tests."""

from __future__ import annotations

from typing import Any

from vera_core.models.code import CodeArtifact
from vera_core.models.ids import RunId
from vera_core.models.observation import ArtifactRef, Observation
from vera_core.ports.sandbox import DataMount, ResourceLimits


class FakeSandbox:
    """Returns scripted Observation objects. Records all calls for assertion."""

    def __init__(self) -> None:
        self._queue: list[Observation] = []
        self.calls: list[dict[str, Any]] = []

    def push_success(
        self,
        stdout: str = "",
        stderr: str = "",
        artifacts: list[ArtifactRef] | None = None,
    ) -> None:
        """Queue a successful execution observation."""
        self._queue.append(
            Observation(
                stdout=stdout,
                stderr=stderr,
                exit_code=0,
                duration_ms=50,
                artifacts=artifacts or [],
            )
        )

    def push_failure(
        self,
        stderr: str = "Traceback (most recent call last):\n  RuntimeError: something failed",
        stdout: str = "",
    ) -> None:
        """Queue a failed execution observation (non-zero exit code)."""
        self._queue.append(
            Observation(
                stdout=stdout,
                stderr=stderr,
                exit_code=1,
                duration_ms=50,
                artifacts=[],
            )
        )

    def push_observation(self, obs: Observation) -> None:
        """Queue a caller-built observation verbatim."""
        self._queue.append(obs)

    def push_timeout(self) -> None:
        """Queue a timeout observation."""
        from vera_core.errors import SandboxTimeoutError

        self._queue.append(SandboxTimeoutError("Execution timed out"))  # type: ignore[arg-type]

    async def execute(
        self,
        *,
        script: CodeArtifact,
        mounts: list[DataMount],
        limits: ResourceLimits,
        run_id: RunId,
    ) -> Observation:
        self.calls.append(
            {
                "script_sha": script.sha256,
                "mounts": mounts,
                "limits": limits,
                "run_id": run_id,
            }
        )

        if not self._queue:
            raise RuntimeError(
                "FakeSandbox has no queued observations. "
                "Call push_success() or push_failure() first."
            )

        item = self._queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    @property
    def call_count(self) -> int:
        return len(self.calls)

    @property
    def queue_length(self) -> int:
        """Number of scripted observations still queued (mirrors FakeLLM)."""
        return len(self._queue)

    @property
    def last_call(self) -> dict[str, Any]:
        if not self.calls:
            raise IndexError("No calls recorded")
        return self.calls[-1]


__all__ = ["FakeSandbox"]
