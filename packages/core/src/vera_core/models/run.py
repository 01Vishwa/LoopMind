"""Run domain models — the core state that flows through the DS-STAR loop."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

from vera_core.models.code import CodeArtifact
from vera_core.models.file import FileDescription
from vera_core.models.ids import RunId, TenantId, UserId, WorkspaceId
from vera_core.models.observation import ArtifactRef, Observation
from vera_core.models.plan import PlanStep
from vera_core.models.report import Report, SubQuestion
from vera_core.models.routing import RouterAction, RouterDecision
from vera_core.models.verdict import Verdict


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


class RunBudget(BaseModel):
    max_rounds: int = Field(default=10, ge=1, le=50)
    max_debug_attempts: int = Field(default=3, ge=0, le=10)
    max_wall_clock_s: int = Field(default=900, ge=30)
    max_cost_usd: Decimal = Field(default=Decimal("5.00"))
    max_sub_questions: int = Field(default=8, ge=1, le=20)  # DS-STAR+ research fan-out cap
    max_gap_rounds: int = Field(default=1, ge=0, le=3)  # DS-STAR+ report refinement rounds

    model_config = {"frozen": True}


class AbandonedBranch(BaseModel):
    """Records why a plan branch was abandoned so the planner can diverge."""

    round: int
    from_index: int
    removed_step_texts: list[str] = Field(default_factory=list)
    removed_script_sha: str | None = None
    rationale: str

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
    abandoned_branches: list[AbandonedBranch] = Field(default_factory=list)
    script_checkpoints: dict[int, CodeArtifact] = Field(default_factory=dict)
    observation_checkpoints: dict[int, Observation] = Field(default_factory=dict)
    # DS-STAR+ research mode only
    sub_questions: list[SubQuestion] = Field(default_factory=list)
    report: Report | None = None

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
    "AbandonedBranch",
    "ArtifactRef",
    "CodeArtifact",
    "Observation",
    "PlanStep",
    "RouterAction",
    "RouterDecision",
    "RunBudget",
    "RunMode",
    "RunState",
    "RunStatus",
    "Verdict",
]
