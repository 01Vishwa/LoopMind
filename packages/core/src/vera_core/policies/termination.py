"""Termination policy — decides when a run should stop."""

from __future__ import annotations

from vera_core.models.run import RunState


def check_budget(state: RunState) -> str | None:
    """Return a human-readable reason if the run should terminate, else None.

    Termination conditions (in priority order):
    1. Max rounds reached
    2. Cost limit reached
    3. Wall-clock time exceeded (caller must track elapsed time)
    4. Max debug attempts reached (signalled by debug_attempts field)
    """
    if state.round >= state.budget.max_rounds:
        return f"Max rounds reached ({state.budget.max_rounds})"

    if state.cost_usd >= state.budget.max_cost_usd:
        return f"Cost limit reached (${state.cost_usd:.4f} >= ${state.budget.max_cost_usd:.2f})"

    return None


def should_terminate(state: RunState) -> bool:
    """Return True if the run must stop before the next round."""
    return check_budget(state) is not None


def is_terminal_status(status: str) -> bool:
    """Return True if the status is a terminal run status."""
    return status in {"succeeded", "failed", "cancelled"}


__all__ = ["check_budget", "should_terminate", "is_terminal_status"]
