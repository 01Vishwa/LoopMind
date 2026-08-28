"""Sandbox port — untrusted code execution interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from vera_core.models.ids import RunId
from vera_core.models.run import CodeArtifact, Observation


class DataMount(BaseModel):
    """A file/directory to mount read-only into the sandbox container."""

    host_path: str
    container_path: str

    model_config = {"frozen": True}


class ResourceLimits(BaseModel):
    memory_mb: int = Field(default=512, ge=64, le=4096)
    cpu_quota: int = Field(default=50000, ge=1000)  # Docker cpu_quota (100000 = 1 CPU)
    timeout_s: int = Field(default=60, ge=5, le=300)
    max_output_bytes: int = Field(default=1_048_576, ge=1024)  # 1 MB

    model_config = {"frozen": True}


@runtime_checkable
class SandboxPort(Protocol):
    """Execute untrusted Python code in an isolated container.

    Each call must create a fresh container. Containers are destroyed after
    execution regardless of outcome.
    """

    async def execute(
        self,
        *,
        script: CodeArtifact,
        mounts: list[DataMount],
        limits: ResourceLimits,
        run_id: RunId,
    ) -> Observation: ...


__all__ = ["DataMount", "ResourceLimits", "SandboxPort"]
