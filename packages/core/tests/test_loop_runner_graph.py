"""The StateGraph-based run_precise: shape, signature, and per-call isolation."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

from vera_core.loop import LoopDeps, run_precise
from vera_core.loop.runner import _build_graph, _recursion_limit
from vera_core.models.run import RunBudget, RunState, RunStatus
from vera_core.policies import CycleDetector
from vera_core.ports.clock import FixedClock
from vera_core.prompts import PromptRegistry
from vera_testing.factories.domain import make_agent_defaults
from vera_testing.fakes import FakeEventBus
from vera_testing.scenarios import Scenario, happy_path


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


def test_run_precise_signature_is_unchanged() -> None:
    sig = inspect.signature(run_precise)
    assert list(sig.parameters) == ["state", "deps"]
    assert sig.return_annotation in ("RunState", RunState)


def test_graph_has_the_expected_node_set() -> None:
    graph = _build_graph(_deps(happy_path()))
    nodes = set(graph.get_graph().nodes) - {"__start__", "__end__"}
    assert nodes == {
        "analyze",
        "retrieve",
        "plan",
        "code",
        "execute",
        "debug",
        "verify",
        "route",
        "truncate",
        "finalize_ok",
        "finalize_degraded",
    }


def test_recursion_limit_scales_with_budget() -> None:
    assert _recursion_limit(RunBudget(max_rounds=10, max_debug_attempts=3)) == 2 + 10 * 14 + 10
    assert _recursion_limit(RunBudget(max_rounds=1, max_debug_attempts=0)) == 2 + 1 * 8 + 10


async def test_run_precise_returns_a_runstate_instance() -> None:
    sc = happy_path()
    out = await run_precise(sc.state, _deps(sc))
    assert isinstance(out, RunState)
    assert out.status is RunStatus.SUCCEEDED


async def test_each_call_builds_a_fresh_graph_no_state_leak() -> None:
    sc1, sc2 = happy_path(), happy_path()
    out1 = await run_precise(sc1.state, _deps(sc1))
    out2 = await run_precise(sc2.state, _deps(sc2))
    assert out1.run_id != out2.run_id
    assert out1.round == out2.round
    assert "1250" in (out1.answer or "") and "1250" in (out2.answer or "")
