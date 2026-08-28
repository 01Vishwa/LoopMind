"""Pure edge predicates — no I/O, no deps beyond the state and the detector."""

from __future__ import annotations

from typing import Literal

from vera_core.models.routing import RouterAction
from vera_core.models.run import RunState
from vera_core.policies import CycleDetector, check_budget


def execution_outcome(state: RunState) -> Literal["ok", "crash", "budget"]:
    obs = state.last_observation
    if obs is not None and obs.succeeded:
        # A good result is never thrown away for budget: let verify run once on
        # the observation the run already paid for.
        return "ok"
    # `check_budget`'s round arm is belt-and-braces here — it is unreachable from
    # `run_precise`, where `verify_outcome` is the real max-rounds exit. The live
    # arm is cost.
    if check_budget(state) is not None:
        return "budget"
    return "crash"


def verify_outcome(state: RunState) -> Literal["sufficient", "insufficient", "max_rounds"]:
    if state.verdicts and state.verdicts[-1].sufficient:
        return "sufficient"
    if state.round >= state.budget.max_rounds:
        return "max_rounds"
    return "insufficient"


def route_outcome(state: RunState, detector: CycleDetector) -> Literal["add_step", "backtrack"]:
    decision = state.routes[-1]
    if decision.action is RouterAction.BACKTRACK and decision.backtrack_index is not None:
        return "backtrack"
    return "add_step"


def debug_outcome(state: RunState) -> Literal["fixed", "retry", "max_retries"]:
    if state.debug_attempts >= state.budget.max_debug_attempts:
        return "max_retries"
    obs = state.last_observation
    return "fixed" if obs is not None and obs.succeeded else "retry"


__all__ = ["debug_outcome", "execution_outcome", "route_outcome", "verify_outcome"]
