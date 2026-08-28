"""Observation models — the result of executing a code artifact in the sandbox."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ArtifactRef(BaseModel):
    """Reference to an output artifact produced by sandbox execution."""

    filename: str
    uri: str
    size_bytes: int
    mime_type: str


class Observation(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    truncated: bool = False

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


__all__ = ["ArtifactRef", "Observation"]
