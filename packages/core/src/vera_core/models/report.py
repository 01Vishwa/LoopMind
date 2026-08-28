"""Report domain models for DS-STAR+ research mode."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from vera_core.models.ids import RunId


class SubQuestionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class SubQuestion(BaseModel):
    idx: int
    text: str
    status: SubQuestionStatus = SubQuestionStatus.PENDING
    answer: str | None = None
    child_run_id: RunId | None = None

    model_config = {"frozen": False}


class Citation(BaseModel):
    file_id: str
    filename: str
    excerpt: str

    model_config = {"frozen": True}


class Report(BaseModel):
    """Final research report with citations."""

    markdown: str = Field(min_length=10)
    citations: list[Citation] = Field(default_factory=list)
    sub_question_count: int = 0
    gap_rounds: int = 0


__all__ = ["SubQuestionStatus", "SubQuestion", "Citation", "Report"]
