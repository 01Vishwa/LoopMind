"""Every scenario builder drains its fake queues exactly through run_precise."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from vera_core.loop import LoopDeps, run_precise
from vera_core.policies import CycleDetector
from vera_core.ports.clock import FixedClock
from vera_core.prompts import PromptRegistry
from vera_testing.factories.domain import make_agent_defaults
from vera_testing.fakes import FakeEventBus
from vera_testing.scenarios import Scenario, backtrack, happy_path, multi_round


def _deps(sc: Scenario) -> LoopDeps:
    return LoopDeps(
        llm=sc.llm,
        sandbox=sc.sandbox,
        retriever=sc.retriever,
        event_bus=FakeEventBus(),
        clock=FixedClock(datetime.now(UTC)),
        defaults=make_agent_defaults(),
        registry=PromptRegistry(),
        file_refs=[],
        mounts=[],
        cycle_detector=CycleDetector(max_repeats=3),
    )


@pytest.mark.parametrize("builder", [happy_path, multi_round, backtrack])
async def test_scenario_drains_cleanly(builder):
    sc = builder()
    state = await run_precise(sc.state, _deps(sc))

    assert state.answer and sc.expected_answer_substring in state.answer
    assert state.status is sc.expected_status
    assert sc.llm.queue_length == 0
    assert not sc.sandbox._queue


async def test_multi_round_grows_the_plan():
    sc = multi_round()
    state = await run_precise(sc.state, _deps(sc))
    assert len(state.active_plan) == 3
    assert len(state.verdicts) == 2
    assert len(state.routes) == 1
    assert state.abandoned_branches == []


async def test_backtrack_records_one_abandoned_branch():
    sc = backtrack()
    state = await run_precise(sc.state, _deps(sc))
    assert len(state.abandoned_branches) == 1
    assert state.abandoned_branches[0].from_index == 1
    assert "backtrack" in state.answer.lower()
    assert any(s.superseded for s in state.plan)
