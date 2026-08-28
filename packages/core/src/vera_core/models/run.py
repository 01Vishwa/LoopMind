"""Run domain models — the core state that flows through the DS-STAR loop."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from vera_core.models.file import FileDescription
from vera_core.models.ids import RunId, TenantId, UserId, WorkspaceId


class RunMode(StrEnum):
    PRECISE = "precise"
    RESEARCH = "research"


class RunStatus(StrEnum):
    QUEUED = "queued"
    ANALYZING = "analyzing"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlanStep(BaseModel):
    index: int
    text: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    created_at_round: int = 0
    superseded: bool = False

    model_config = {"frozen": True}


class CodeArtifact(BaseModel):
    language: Literal["python", "sql"] = "python"
    source: str
    sha256: str
    parent_sha256: str | None = None

    model_config = {"frozen": True}


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


class Verdict(BaseModel):
    sufficient: bool
    reason: str = Field(min_length=10)
    missing_aspects: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}


class RouterAction(StrEnum):
    ADD_STEP = "add_step"
    BACKTRACK = "backtrack"


class RouterDecision(BaseModel):
    action: RouterAction
    backtrack_index: int | None = None
    rationale: str

    model_config = {"frozen": True}


class RunBudget(BaseModel):
    max_rounds: int = Field(default=10, ge=1, le=50)
    max_debug_attempts: int = Field(default=3, ge=0, le=10)
    max_wall_clock_s: int = Field(default=900, ge=30)
    max_cost_usd: Decimal = Field(default=Decimal("5.00"))

    model_config = {"frozen": True}


class RunState(BaseModel):
    """Full mutable state carried through the LangGraph DS-STAR loop.

    This is the single source of truth for a run. All agents read from and
    write to this state. It must remain JSON-serialisable for checkpointing.
    """

    run_id: RunId
    tenant_id: TenantId
    user_id: UserId
    workspace_id: WorkspaceId
    query: str
    mode: RunMode
    status: RunStatus
    descriptions: list[FileDescription] = Field(default_factory=list)
    plan: list[PlanStep] = Field(default_factory=list)
    script: CodeArtifact | None = None
    observations: list[Observation] = Field(default_factory=list)
    verdicts: list[Verdict] = Field(default_factory=list)
    routes: list[RouterDecision] = Field(default_factory=list)
    round: int = 0
    debug_attempts: int = 0
    budget: RunBudget = Field(default_factory=RunBudget)
    cost_usd: Decimal = Field(default=Decimal("0"))
    total_tokens: int = 0
    answer: str | None = None
    error: str | None = None
    started_at: datetime
    finished_at: datetime | None = None

    # Mutable model_config — RunState changes during the loop
    model_config = {"frozen": False}

    @property
    def active_plan(self) -> list[PlanStep]:
        """Steps that are not superseded, in order."""
        return [s for s in self.plan if not s.superseded]

    @property
    def last_observation(self) -> Observation | None:
        return self.observations[-1] if self.observations else None

    def budget_exhausted(self) -> bool:
        return self.round >= self.budget.max_rounds or self.cost_usd >= self.budget.max_cost_usd


__all__ = [
    "RunMode",
    "RunStatus",
    "PlanStep",
    "CodeArtifact",
    "ArtifactRef",
    "Observation",
    "Verdict",
    "RouterAction",
    "RouterDecision",
    "RunBudget",
    "RunState",
]
