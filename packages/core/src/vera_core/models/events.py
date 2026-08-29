"""SSE event types emitted during a run.

Every event is a tagged union. The `type` field is the SSE event name.
All events are JSON-serialisable for storage in run_events table.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from vera_core.models.ids import RunId


class BaseEvent(BaseModel):
    run_id: RunId
    round: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": True}


class RunStartedEvent(BaseEvent):
    type: Literal["run.started"] = "run.started"
    query: str
    mode: str


class AnalysisStartedEvent(BaseEvent):
    type: Literal["analysis.started"] = "analysis.started"
    file_count: int


class FileAnalyzedEvent(BaseEvent):
    type: Literal["file.analyzed"] = "file.analyzed"
    file_id: str
    filename: str
    row_count: int | None = None
    partial: bool = False


class PlanUpdatedEvent(BaseEvent):
    type: Literal["plan.updated"] = "plan.updated"
    steps: list[str]  # step texts


class CodeGeneratedEvent(BaseEvent):
    type: Literal["code.generated"] = "code.generated"
    sha256: str
    language: str


class ExecutionStartedEvent(BaseEvent):
    type: Literal["execution.started"] = "execution.started"


class ExecutionFinishedEvent(BaseEvent):
    type: Literal["execution.finished"] = "execution.finished"
    exit_code: int
    duration_ms: int
    truncated: bool


class DebugAttemptEvent(BaseEvent):
    type: Literal["debug.attempt"] = "debug.attempt"
    attempt: int


class VerifyVerdictEvent(BaseEvent):
    type: Literal["verify.verdict"] = "verify.verdict"
    sufficient: bool
    reason: str
    missing_aspects: list[str]


class RouteDecisionEvent(BaseEvent):
    type: Literal["route.decision"] = "route.decision"
    action: str
    backtrack_index: int | None = None
    rationale: str


class RunFinishedEvent(BaseEvent):
    type: Literal["run.finished"] = "run.finished"
    answer: str
    cost_usd: Decimal
    total_tokens: int
    total_rounds: int


class RunFailedEvent(BaseEvent):
    type: Literal["run.failed"] = "run.failed"
    error: str


class RunCancelledEvent(BaseEvent):
    type: Literal["run.cancelled"] = "run.cancelled"


# ── DS-STAR+ research events ──────────────────────────────────────────────────


class SubQuestionsGeneratedEvent(BaseEvent):
    type: Literal["research.subquestions"] = "research.subquestions"
    count: int
    gap_round: int


class SubQuestionResolvedEvent(BaseEvent):
    type: Literal["research.subquestion_resolved"] = "research.subquestion_resolved"
    idx: int
    status: str
    child_run_id: str | None = None


class ReportGeneratedEvent(BaseEvent):
    type: Literal["research.report"] = "research.report"
    sub_question_count: int
    gap_rounds: int


# Discriminated union — used for type-safe deserialization
RunEvent = Annotated[
    RunStartedEvent
    | AnalysisStartedEvent
    | FileAnalyzedEvent
    | PlanUpdatedEvent
    | CodeGeneratedEvent
    | ExecutionStartedEvent
    | ExecutionFinishedEvent
    | DebugAttemptEvent
    | VerifyVerdictEvent
    | RouteDecisionEvent
    | RunFinishedEvent
    | RunFailedEvent
    | RunCancelledEvent
    | SubQuestionsGeneratedEvent
    | SubQuestionResolvedEvent
    | ReportGeneratedEvent,
    Field(discriminator="type"),
]

__all__ = [
    "RunEvent",
    "BaseEvent",
    "RunStartedEvent",
    "AnalysisStartedEvent",
    "FileAnalyzedEvent",
    "PlanUpdatedEvent",
    "CodeGeneratedEvent",
    "ExecutionStartedEvent",
    "ExecutionFinishedEvent",
    "DebugAttemptEvent",
    "VerifyVerdictEvent",
    "RouteDecisionEvent",
    "RunFinishedEvent",
    "RunFailedEvent",
    "RunCancelledEvent",
    "SubQuestionsGeneratedEvent",
    "SubQuestionResolvedEvent",
    "ReportGeneratedEvent",
]
