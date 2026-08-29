"""run_research end to end via scripted fakes."""

from __future__ import annotations

from datetime import UTC, datetime

from vera_core.agents._types import (
    CoderOutput,
    FinalizerOutput,
    PlannerOutput,
    PlanStepDraft,
    ReportOutput,
    SubQuestionDraft,
    SubQuestionList,
)
from vera_core.loop import LoopDeps, run, run_research
from vera_core.models.report import SubQuestionStatus
from vera_core.models.run import RunMode, RunStatus
from vera_core.models.verdict import Verdict
from vera_core.policies import CycleDetector
from vera_core.ports.clock import FixedClock
from vera_core.prompts import PromptRegistry
from vera_testing.factories.domain import make_agent_defaults, make_run_state
from vera_testing.fakes import FakeEventBus, FakeLLM, FakeRetriever, FakeSandbox


def _child_turn(llm: FakeLLM, sandbox: FakeSandbox, answer: str) -> None:
    """Queue one happy-path precise round for one sub-question."""
    llm.on("planner", PlannerOutput(steps=[PlanStepDraft(text="Load and compute")]))
    llm.on("coder", CoderOutput(source="print('x')"))
    sandbox.push_success(stdout="RESULT")
    llm.on("verifier", Verdict(sufficient=True, reason="the number is correct here"))
    llm.on("finalizer", FinalizerOutput(answer=answer))


def _deps(llm: FakeLLM, sandbox: FakeSandbox) -> LoopDeps:
    return LoopDeps(
        llm=llm,
        sandbox=sandbox,
        retriever=FakeRetriever(),
        event_bus=FakeEventBus(),
        clock=FixedClock(datetime.now(UTC)),
        defaults=make_agent_defaults(),
        registry=PromptRegistry(),
        file_refs=[],
        mounts=[],
        cycle_detector=CycleDetector(),
    )


def _scripted() -> tuple[FakeLLM, FakeSandbox]:
    llm, sandbox = FakeLLM(), FakeSandbox()
    llm.on(
        "subquestion_generator",
        SubQuestionList(
            questions=[
                SubQuestionDraft(index=1, text="Volume by merchant?"),
                SubQuestionDraft(index=2, text="Chargeback rate?"),
            ]
        ),
    )
    _child_turn(llm, sandbox, "Volume is 1,000.")
    _child_turn(llm, sandbox, "Rate is 2.5%.")
    llm.on(
        "report_writer",
        ReportOutput(markdown="# Draft\nVolume 1,000 [SQ-1]; rate 2.5% [SQ-2]."),
    )
    llm.on(
        "subquestion_generator",
        SubQuestionList(questions=[SubQuestionDraft(index=3, text="Top merchant by loss?")]),
    )
    _child_turn(llm, sandbox, "Merchant Acme.")
    llm.on("report_writer", ReportOutput(markdown="# Final\n... [SQ-1][SQ-2][SQ-3]."))
    return llm, sandbox


async def test_run_research_two_rounds_and_report() -> None:
    llm, sandbox = _scripted()
    state = make_run_state(query="Analyse chargebacks", mode=RunMode.RESEARCH)

    out = await run_research(state, _deps(llm, sandbox))

    assert out.status is RunStatus.SUCCEEDED
    assert [sq.idx for sq in out.sub_questions] == [1, 2, 3]
    assert all(sq.status is SubQuestionStatus.DONE for sq in out.sub_questions)
    assert out.report is not None
    assert out.report.gap_rounds == 1
    assert out.report.sub_question_count == 3
    assert out.answer == out.report.markdown
    assert "[SQ-3]" in out.answer
    assert out.cost_usd > 0


async def test_run_dispatcher_routes_by_mode() -> None:
    llm, sandbox = _scripted()
    state = make_run_state(query="q", mode=RunMode.RESEARCH)
    out = await run(state, _deps(llm, sandbox))
    assert out.report is not None


async def test_gap_round_stops_when_generator_returns_empty() -> None:
    llm, sandbox = FakeLLM(), FakeSandbox()
    llm.on(
        "subquestion_generator",
        SubQuestionList(questions=[SubQuestionDraft(index=1, text="Only question?")]),
    )
    _child_turn(llm, sandbox, "Answer.")
    llm.on("report_writer", ReportOutput(markdown="# Draft\nAnswer [SQ-1]."))
    llm.on("subquestion_generator", SubQuestionList(questions=[]))

    state = make_run_state(query="q", mode=RunMode.RESEARCH)
    out = await run_research(state, _deps(llm, sandbox))

    assert len(out.sub_questions) == 1
    assert out.report is not None
    assert out.report.gap_rounds == 0
    assert out.status is RunStatus.SUCCEEDED
