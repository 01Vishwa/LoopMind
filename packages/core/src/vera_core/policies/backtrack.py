"""Backtrack policy — supersede plan steps and restore an earlier state."""

from __future__ import annotations

from vera_core.models.run import PlanStep, RunState


def apply_backtrack(state: RunState, backtrack_to_index: int) -> RunState:
    """Mark all plan steps from backtrack_to_index onward as superseded.

    The loop then re-enters the plan node and generates new steps from
    backtrack_to_index forward, keeping the history for audit.

    Args:
        state: Current run state.
        backtrack_to_index: The plan step index to revert to. Steps at this
            index and later are marked superseded.

    Returns:
        Updated RunState with superseded steps.

    Raises:
        ValueError: If backtrack_to_index is out of range.
    """
    if not state.plan:
        raise ValueError("Cannot backtrack: plan is empty")

    valid_indices = [s.index for s in state.plan if not s.superseded]
    if backtrack_to_index not in valid_indices and backtrack_to_index not in [
        s.index for s in state.plan
    ]:
        raise ValueError(
            f"Backtrack index {backtrack_to_index} is not in plan. Valid indices: {valid_indices}"
        )

    updated_plan = [
        step.model_copy(update={"superseded": True}) if step.index >= backtrack_to_index else step
        for step in state.plan
    ]

    state.plan = updated_plan
    return state


def active_steps(state: RunState) -> list[PlanStep]:
    """Return only non-superseded plan steps in order."""
    return sorted(
        [s for s in state.plan if not s.superseded],
        key=lambda s: s.index,
    )


__all__ = ["apply_backtrack", "active_steps"]
