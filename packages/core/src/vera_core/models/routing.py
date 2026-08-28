"""Router models — the verify -> route decision that drives multi-round refinement."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RouterAction(StrEnum):
    ADD_STEP = "add_step"
    BACKTRACK = "backtrack"


class RouterDecision(BaseModel):
    """One verify -> route decision.

    ``backtrack_index`` is an **absolute** :attr:`~vera_core.models.plan.PlanStep.index`,
    never a position in ``RunState.active_plan``. After a backtrack the active plan
    develops gaps (indices ``[0, 2, 3]``), so the two are not interchangeable; the
    router prompts render each step as ``"<index>: <text>"`` for exactly this reason.
    Steps with ``index >= backtrack_index`` are superseded by ``apply_backtrack``.
    """

    action: RouterAction
    backtrack_index: int | None = Field(default=None, ge=0)
    rationale: str

    model_config = {"frozen": True}


__all__ = ["RouterAction", "RouterDecision"]
