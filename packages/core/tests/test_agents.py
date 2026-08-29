"""Agent unit tests — scripted FakeLLM in, typed structured output out."""

from __future__ import annotations

from uuid import uuid4

import pytest
from vera_core.agents import (
    AgentContext,
    AnalyzePayload,
    CoderPayload,
    DebuggerPayload,
    FinalizerPayload,
    PlannerPayload,
    RouterPayload,
    VerifierPayload,
    analyzer,
    coder,
    debugger,
    finalizer,
    planner,
    router,
    verifier,
)
from vera_core.agents._types import (
    CoderOutput,
    FinalizerOutput,
    PlannerOutput,
    PlanStepDraft,
)
from vera_core.errors import AgentOutputError
from vera_core.models.agent_config import AgentTier
from vera_core.models.ids import RunId
from vera_core.models.routing import RouterAction, RouterDecision
from vera_core.models.verdict import Verdict
from vera_core.ports.llm import LLMResponse
from vera_core.prompts import PromptRegistry
from vera_testing.factories.domain import make_agent_defaults
from vera_testing.fakes import FakeLLM


def _ctx(llm: FakeLLM) -> AgentContext:
    return AgentContext(
        llm=llm,
        defaults=make_agent_defaults(),
        registry=PromptRegistry(),
        run_id=RunId(uuid4()),
    )


async def test_verifier_returns_verdict_and_llm_response() -> None:
    llm = FakeLLM()
    llm.on(
        "verifier",
        Verdict(sufficient=False, reason="missing fee deduction", missing_aspects=["fees"]),
    )
    out, resp = await verifier.run(
        _ctx(llm),
        VerifierPayload(query="q", plan=["a"], code="print(1)", observation="1"),
    )
    assert isinstance(out, Verdict)
    assert out.sufficient is False
    assert isinstance(resp, LLMResponse)
    assert resp.input_tokens > 0
    assert resp.cost_usd is not None


async def test_planner_returns_steps() -> None:
    llm = FakeLLM()
    llm.on(
        "planner",
        PlannerOutput(steps=[PlanStepDraft(text="load csv"), PlanStepDraft(text="sum col")]),
    )
    out, _ = await planner.run(
        _ctx(llm),
        PlannerPayload(query="q", descriptions=["a csv"], existing_steps=[], abandoned=[]),
    )
    assert len(out.steps) == 2


async def test_analyzer_returns_a_parser_script() -> None:
    from vera_core.agents import AnalyzerScriptOutput

    llm = FakeLLM()
    llm.on("analyzer", AnalyzerScriptOutput(source="import pandas as pd\nprint(pd.__version__)"))
    out, _ = await analyzer.run(
        _ctx(llm),
        AnalyzePayload(file_id="f1", filename="x.csv", kind="csv", sample="a,b\n1,2"),
    )
    assert out.source.startswith("import pandas")


async def test_coder_and_debugger_return_source() -> None:
    llm = FakeLLM()
    llm.on("coder", CoderOutput(source="print(1)"))
    llm.on("debugger", CoderOutput(source="print(2)"))
    c, _ = await coder.run(
        _ctx(llm),
        CoderPayload(query="q", plan=["a"], last_stdout=None, last_stderr=None),
    )
    d, _ = await debugger.run(_ctx(llm), DebuggerPayload(code="print(1)", stderr="boom"))
    assert c.source == "print(1)"
    assert d.source == "print(2)"
    assert isinstance(d, CoderOutput)


async def test_router_returns_decision() -> None:
    llm = FakeLLM()
    llm.on(
        "router",
        RouterDecision(action=RouterAction.BACKTRACK, backtrack_index=1, rationale="wrong join"),
    )
    out, _ = await router.run(
        _ctx(llm),
        RouterPayload(query="q", verdict_reason="bad", missing_aspects=[], plan=["a"]),
    )
    assert out.action is RouterAction.BACKTRACK
    assert out.backtrack_index == 1


async def test_finalizer_returns_answer() -> None:
    llm = FakeLLM()
    llm.on("finalizer", FinalizerOutput(answer="The total is 1250."))
    out, _ = await finalizer.run(
        _ctx(llm),
        FinalizerPayload(query="q", plan=["a"], observation="1250", degraded=False),
    )
    assert isinstance(out, FinalizerOutput)
    assert "1250" in out.answer


async def test_agent_raises_on_junk() -> None:
    llm = FakeLLM()
    llm.push_response("not json at all")
    with pytest.raises(AgentOutputError):
        await verifier.run(
            _ctx(llm),
            VerifierPayload(query="q", plan=[], code="", observation=""),
        )


def test_agent_tiers_match_spec() -> None:
    assert verifier.tier is AgentTier.REASONING
    assert planner.tier is AgentTier.REASONING
    assert coder.tier is AgentTier.REASONING
    assert router.tier is AgentTier.REASONING
    assert analyzer.tier is AgentTier.UTILITY
    assert debugger.tier is AgentTier.UTILITY
    assert finalizer.tier is AgentTier.UTILITY
