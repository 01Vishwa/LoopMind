"""Code artifact model — a versioned script produced by the coder agent."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CodeArtifact(BaseModel):
    language: Literal["python", "sql"] = "python"
    source: str
    sha256: str
    parent_sha256: str | None = None

    model_config = {"frozen": True}


__all__ = ["CodeArtifact"]
