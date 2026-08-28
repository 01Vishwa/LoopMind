"""A planner that never diverges is stopped by the cycle detector, not an infinite loop."""

from __future__ import annotations

from datetime import UTC, datetime

from vera_core.agents._types import CoderOutput, FinalizerOutput, PlannerOutput, PlanStepDraft
from vera_core.loop import LoopDeps, run_precise
from vera_core.models.routing import RouterAction, RouterDecision
from vera_core.models.run import RunStatus
from vera_core.models.verdict import Verdict
from vera_core.policies import CycleDetector
from vera_core.ports.clock import FixedClock
from vera_core.prompts import PromptRegistry
from vera_testing.factories.domain import make_agent_defaults, make_run_state
from vera_testing.fakes import FakeEventBus, FakeLLM, FakeRetriever, FakeSandbox


async def test_identical_plan_forces_degraded_finalize() -> None:
    llm, sandbox = FakeLLM(), FakeSandbox()
    for _ in range(4):
        llm.on("planner", PlannerOutput(steps=[PlanStepDraft(text="the one step")]))
        llm.on("coder", CoderOutput(source="print('x')"))
        llm.on(
            "verifier",
            Verdict(sufficient=False, reason="still not sufficient here", missing_aspects=["x"]),
        )
        llm.on("router", RouterDecision(action=RouterAction.ADD_STEP, rationale="keep going"))
        sandbox.push_success(stdout="x")
    llm.on("finalizer", FinalizerOutput(answer="Could not converge on an answer."))

    deps = LoopDeps(
        llm=llm,
        sandbox=sandbox,
        retriever=FakeRetriever(),
        event_bus=FakeEventBus(),
        clock=FixedClock(datetime.now(UTC)),
        defaults=make_agent_defaults(),
        registry=PromptRegistry(),
        file_refs=[],
        mounts=[],
        cycle_detector=CycleDetector(max_repeats=3),
    )

    out = await run_precise(make_run_state(), deps)

    assert out.status in (RunStatus.SUCCEEDED, RunStatus.FAILED)
    assert out.answer is not None
    assert llm.call_count < 30
