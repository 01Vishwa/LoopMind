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


def _deps_for(llm: object, sandbox: object, retriever: object) -> LoopDeps:
    return LoopDeps(
        llm=llm,  # type: ignore[arg-type]
        sandbox=sandbox,  # type: ignore[arg-type]
        retriever=retriever,  # type: ignore[arg-type]
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


async def test_multi_debug_retry_recovers_within_budget() -> None:
    """Two consecutive crashes, each fixed by the debugger, then success — the
    flattened debug->execute self-loop must match the old nested while loop."""
    from vera_core.agents._types import (
        CoderOutput,
        FinalizerOutput,
        PlannerOutput,
        PlanStepDraft,
    )
    from vera_core.models.verdict import Verdict
    from vera_testing.factories.domain import make_run_state
    from vera_testing.fakes import FakeLLM, FakeRetriever, FakeSandbox

    llm = FakeLLM()
    llm.on("planner", PlannerOutput(steps=[PlanStepDraft(text="Load and sum payments.csv")]))
    llm.on("coder", CoderOutput(source="import pandas as pd  # v1 (broken)"))
    llm.on("debugger", CoderOutput(source="import pandas as pd  # v2 (still broken)"))
    llm.on("debugger", CoderOutput(source="import pandas as pd  # v3 (fixed)"))
    llm.on("verifier", Verdict(sufficient=True, reason="total is correct after two fixes"))
    llm.on("finalizer", FinalizerOutput(answer="Total is $1250.00."))

    sandbox = FakeSandbox()
    sandbox.push_failure(stderr="KeyError: 'amt'")
    sandbox.push_failure(stderr="KeyError: 'amount_'")
    sandbox.push_success(stdout="TOTAL: 1250.00")

    state = make_run_state(query="total payments?")
    out = await run_precise(state, _deps_for(llm, sandbox, FakeRetriever()))

    assert out.status is RunStatus.SUCCEEDED
    assert "1250" in (out.answer or "")
    assert sandbox.call_count == 3  # initial + 2 debug retries
    assert out.round == 1  # exactly one verify
    assert len(out.verdicts) == 1
