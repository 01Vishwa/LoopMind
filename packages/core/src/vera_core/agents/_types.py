"""Small structured-output models produced by agents."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlanStepDraft(BaseModel):
    text: str
    acceptance_criteria: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}


class PlannerOutput(BaseModel):
    steps: list[PlanStepDraft] = Field(default_factory=list)

    model_config = {"frozen": True}


class CoderOutput(BaseModel):
    source: str

    model_config = {"frozen": True}


class FinalizerOutput(BaseModel):
    answer: str

    model_config = {"frozen": True}


__all__ = ["CoderOutput", "FinalizerOutput", "PlanStepDraft", "PlannerOutput"]
