"""The plan / code nodes forward the context their hardened prompts need."""

from __future__ import annotations

from datetime import UTC, datetime

from vera_core.agents._types import CoderOutput, PlannerOutput, PlanStepDraft
from vera_core.loop.context import LoopDeps
from vera_core.loop.nodes.code import code
from vera_core.loop.nodes.plan import plan
from vera_core.models.code import CodeArtifact
from vera_core.models.observation import Observation
from vera_core.policies import CycleDetector
from vera_core.ports.clock import FixedClock
from vera_core.prompts import PromptRegistry
from vera_testing.factories.domain import make_agent_defaults, make_run_state
from vera_testing.fakes import FakeEventBus, FakeLLM, FakeRetriever, FakeSandbox


def _deps(llm: FakeLLM) -> LoopDeps:
    return LoopDeps(
        llm=llm,
        sandbox=FakeSandbox(),
        retriever=FakeRetriever(),
        event_bus=FakeEventBus(),
        clock=FixedClock(datetime.now(UTC)),
        defaults=make_agent_defaults(),
        registry=PromptRegistry(),
        file_refs=[],
        mounts=[],
        cycle_detector=CycleDetector(max_repeats=3),
    )


async def test_plan_node_passes_last_observation_stdout() -> None:
    llm = FakeLLM()
    llm.on("planner", PlannerOutput(steps=[PlanStepDraft(text="next step")]))
    state = make_run_state()
    state.observations.append(Observation(stdout="OBS-123", stderr="", exit_code=0, duration_ms=1))

    await plan(state, _deps(llm))

    assert "OBS-123" in llm.calls[-1]["messages"][0]["content"]


async def test_code_node_passes_prior_script_source() -> None:
    llm = FakeLLM()
    llm.on("coder", CoderOutput(source="print('v2')"))
    state = make_run_state()
    state.script = CodeArtifact(source="print('v1 PRIOR')", sha256="abc")

    await code(state, _deps(llm))

    assert "v1 PRIOR" in llm.calls[-1]["messages"][0]["content"]
