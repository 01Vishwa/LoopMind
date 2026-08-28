"""Edge predicates return the right label across their full output range."""

from __future__ import annotations

from vera_core.loop.edges import (
    debug_outcome,
    execution_outcome,
    route_outcome,
    verify_outcome,
)
from vera_core.models.routing import RouterAction, RouterDecision
from vera_core.policies import CycleDetector
from vera_testing.factories.domain import (
    make_observation,
    make_run_state,
    make_verdict,
)


def _state(**over: object):
    st = make_run_state()
    for key, value in over.items():
        setattr(st, key, value)
    return st


def test_execution_outcome_ok() -> None:
    st = _state()
    st.observations.append(make_observation(exit_code=0))
    assert execution_outcome(st) == "ok"


def test_execution_outcome_crash() -> None:
    st = _state()
    st.observations.append(make_observation(exit_code=1, stderr="boom"))
    assert execution_outcome(st) == "crash"


def test_execution_outcome_budget() -> None:
    st = _state()
    st.round = st.budget.max_rounds
    st.observations.append(make_observation(exit_code=0))
    assert execution_outcome(st) == "budget"


def test_verify_outcome_sufficient() -> None:
    st = _state()
    st.verdicts.append(make_verdict(sufficient=True))
    assert verify_outcome(st) == "sufficient"


def test_verify_outcome_insufficient() -> None:
    st = _state()
    st.round = 1
    st.verdicts.append(make_verdict(sufficient=False, reason="missing something here"))
    assert verify_outcome(st) == "insufficient"


def test_verify_outcome_max_rounds() -> None:
    st = _state()
    st.round = st.budget.max_rounds
    st.verdicts.append(make_verdict(sufficient=False, reason="still not enough here"))
    assert verify_outcome(st) == "max_rounds"


def test_route_outcome_backtrack() -> None:
    st = _state()
    st.routes.append(
        RouterDecision(action=RouterAction.BACKTRACK, backtrack_index=1, rationale="wrong")
    )
    assert route_outcome(st, CycleDetector()) == "backtrack"


def test_route_outcome_add_step() -> None:
    st = _state()
    st.routes.append(RouterDecision(action=RouterAction.ADD_STEP, rationale="more"))
    assert route_outcome(st, CycleDetector()) == "add_step"


def test_route_outcome_backtrack_without_index_is_add_step() -> None:
    st = _state()
    st.routes.append(
        RouterDecision(action=RouterAction.BACKTRACK, backtrack_index=None, rationale="x")
    )
    assert route_outcome(st, CycleDetector()) == "add_step"


def test_debug_outcome_max_retries() -> None:
    st = _state()
    st.debug_attempts = st.budget.max_debug_attempts
    assert debug_outcome(st) == "max_retries"


def test_debug_outcome_fixed() -> None:
    st = _state()
    st.observations.append(make_observation(exit_code=0))
    assert debug_outcome(st) == "fixed"


def test_debug_outcome_retry() -> None:
    st = _state()
    st.observations.append(make_observation(exit_code=1, stderr="still broken"))
    assert debug_outcome(st) == "retry"
