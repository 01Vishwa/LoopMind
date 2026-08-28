"""Plan step model — a single step in a run's analysis plan."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    index: int
    text: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    created_at_round: int = 0
    superseded: bool = False

    model_config = {"frozen": True}


__all__ = ["PlanStep"]
