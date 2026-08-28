"""truncate rolls plan, script, and observations back together, by index."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from hypothesis import given, settings
from hypothesis import strategies as st
from vera_core.loop.context import LoopDeps
from vera_core.loop.nodes.truncate import truncate
from vera_core.models.code import CodeArtifact
from vera_core.models.observation import Observation
from vera_core.models.plan import PlanStep
from vera_core.models.routing import RouterAction, RouterDecision
from vera_core.policies import CycleDetector
from vera_core.ports.clock import FixedClock
from vera_core.prompts import PromptRegistry
from vera_testing.factories.domain import make_agent_defaults, make_run_state
from vera_testing.fakes import FakeEventBus, FakeLLM, FakeRetriever, FakeSandbox


def _deps() -> LoopDeps:
    return LoopDeps(
        llm=FakeLLM(),
        sandbox=FakeSandbox(),
        retriever=FakeRetriever(),
        event_bus=FakeEventBus(),
        clock=FixedClock(datetime.now(UTC)),
        defaults=make_agent_defaults(),
        registry=PromptRegistry(),
        file_refs=[],
        mounts=[],
        cycle_detector=CycleDetector(),
    )


@settings(max_examples=60, deadline=None)
@given(n=st.integers(min_value=2, max_value=8), data=st.data())
def test_truncate_restores_by_index(n: int, data: st.DataObject) -> None:
    j = data.draw(st.integers(min_value=1, max_value=n - 1))

    state = make_run_state()
    state.plan = [PlanStep(index=i, text=f"step {i}", created_at_round=0) for i in range(n)]
    for i in range(n):
        state.script_checkpoints[i] = CodeArtifact(source=f"s{i}", sha256=f"sha{i}")
        state.observation_checkpoints[i] = Observation(
            stdout=f"out{i}", stderr="", exit_code=0, duration_ms=1
        )
    state.script = state.script_checkpoints[n - 1]
    state.observations = [state.observation_checkpoints[i] for i in range(n)]
    state.routes = [
        RouterDecision(action=RouterAction.BACKTRACK, backtrack_index=j, rationale="wrong join")
    ]

    out = asyncio.run(truncate(state, _deps()))

    assert [s.index for s in out.active_plan] == list(range(j))
    assert out.script == CodeArtifact(source=f"s{j - 1}", sha256=f"sha{j - 1}")
    assert len(out.observations) == j
    assert all(k < j for k in out.script_checkpoints)
    assert all(k < j for k in out.observation_checkpoints)
    assert len(out.abandoned_branches) == 1
    assert out.abandoned_branches[0].from_index == j
    assert out.abandoned_branches[0].removed_script_sha == f"sha{n - 1}"
    assert out.debug_attempts == 0


def test_truncate_index_zero_clears_script() -> None:
    state = make_run_state()
    state.plan = [PlanStep(index=0, text="only", created_at_round=0)]
    state.script_checkpoints[0] = CodeArtifact(source="s0", sha256="sha0")
    state.observation_checkpoints[0] = Observation(
        stdout="o0", stderr="", exit_code=0, duration_ms=1
    )
    state.script = state.script_checkpoints[0]
    state.routes = [
        RouterDecision(action=RouterAction.BACKTRACK, backtrack_index=0, rationale="redo")
    ]

    out = asyncio.run(truncate(state, _deps()))
    assert out.script is None
    assert out.observations == []
    assert out.active_plan == []
