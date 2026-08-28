"""Verifier verdict model."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Verdict(BaseModel):
    sufficient: bool
    reason: str = Field(min_length=10)
    missing_aspects: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}


__all__ = ["Verdict"]
