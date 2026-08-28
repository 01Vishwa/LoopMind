"""End-to-end loop paths (happy / add-step / backtrack) via the shared scenarios."""

from __future__ import annotations

from datetime import UTC, datetime

from vera_core.loop import LoopDeps, run_precise
from vera_core.models.routing import RouterAction
from vera_core.models.run import RunStatus
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


async def test_happy_path_succeeds_in_one_round() -> None:
    sc = happy_path()
    out = await run_precise(sc.state, _deps(sc))

    assert out.status is RunStatus.SUCCEEDED
    assert len(out.verdicts) == 1
    assert len(out.routes) == 0
    assert "1250" in (out.answer or "")


async def test_add_step_path_runs_two_rounds() -> None:
    sc = multi_round()
    out = await run_precise(sc.state, _deps(sc))

    assert out.status is RunStatus.SUCCEEDED
    assert len(out.verdicts) == 2
    assert len(out.routes) == 1
    assert out.routes[0].action is RouterAction.ADD_STEP
    assert len(out.active_plan) == 3
    assert not out.abandoned_branches


async def test_backtrack_path_records_one_abandoned_branch() -> None:
    sc = backtrack()
    out = await run_precise(sc.state, _deps(sc))

    assert out.status is RunStatus.SUCCEEDED
    assert len(out.abandoned_branches) == 1
    assert out.abandoned_branches[0].from_index == 1
    assert any(s.superseded for s in out.plan)
    assert "1250" in (out.answer or "")
