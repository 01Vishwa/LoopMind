"""Fully-scripted fake stacks for the three DS-STAR loop paths.

Each builder returns a :class:`Scenario` whose ``llm`` / ``sandbox`` queues drain
*exactly* when driven through ``run_precise`` with ``file_refs=[]`` (so the
analyzer is never called) and three ``FakeRetriever`` descriptions.

The plan node uses prefix-append semantics: it appends only the tail of the
planner's draft list when the drafts start with the current active-plan texts.
So every planner response below returns the CUMULATIVE plan (all prior active
step texts in order, then the new step).
"""

from __future__ import annotations

from dataclasses import dataclass

from vera_core.agents._types import (
    CoderOutput,
    FinalizerOutput,
    PlannerOutput,
    PlanStepDraft,
    ReportOutput,
    SubQuestionDraft,
    SubQuestionList,
)
from vera_core.models.routing import RouterAction, RouterDecision
from vera_core.models.run import RunMode, RunState, RunStatus
from vera_core.models.verdict import Verdict

from vera_testing.factories.domain import make_file_description, make_run_state
from vera_testing.fakes import FakeLLM, FakeRetriever, FakeSandbox

_STDOUT = "chargeback_total=1250.00"


@dataclass
class Scenario:
    """A fully-scripted fake stack plus the run state and expected outcome."""

    llm: FakeLLM
    sandbox: FakeSandbox
    retriever: FakeRetriever
    state: RunState
    expected_status: RunStatus
    expected_answer_substring: str
    file_count: int


def _retriever() -> FakeRetriever:
    return FakeRetriever([make_file_description() for _ in range(3)])


def happy_path() -> Scenario:
    """Verifier is satisfied on round 1.

    Node calls: plan x1, code x1, execute x1, verify x1 (sufficient), finalize x1.
    """
    llm = FakeLLM()
    sandbox = FakeSandbox()

    llm.on(
        "planner",
        PlannerOutput(
            steps=[
                PlanStepDraft(text="Load payments.csv"),
                PlanStepDraft(text="Sum the chargeback amounts"),
            ]
        ),
    )
    llm.on("coder", CoderOutput(source="import pandas as pd  # sum chargebacks"))
    sandbox.push_success(stdout=_STDOUT)
    llm.on("verifier", Verdict(sufficient=True, reason="chargeback total is correct"))
    llm.on("finalizer", FinalizerOutput(answer="Total chargeback amount is $1250.00."))

    return Scenario(llm, sandbox, _retriever(), make_run_state(), RunStatus.SUCCEEDED, "1250", 3)


def multi_round() -> Scenario:
    """Insufficient -> router ADD_STEP -> replan -> sufficient.

    Node calls: plan x2, code x2, execute x2, verify x2 (insufficient, sufficient),
    route x1 (add_step), finalize x1.
    """
    llm = FakeLLM()
    sandbox = FakeSandbox()

    llm.on(
        "planner",
        PlannerOutput(
            steps=[
                PlanStepDraft(text="Load payments.csv"),
                PlanStepDraft(text="Sum the chargeback amounts"),
            ]
        ),
    )
    llm.on("coder", CoderOutput(source="import pandas as pd  # v1"))
    sandbox.push_success(stdout=_STDOUT)
    llm.on(
        "verifier",
        Verdict(
            sufficient=False,
            reason="refund reversals were not netted out",
            missing_aspects=["refunds"],
        ),
    )
    llm.on(
        "router",
        RouterDecision(action=RouterAction.ADD_STEP, rationale="net refunds against chargebacks"),
    )
    llm.on(
        "planner",
        PlannerOutput(
            steps=[
                PlanStepDraft(text="Load payments.csv"),
                PlanStepDraft(text="Sum the chargeback amounts"),
                PlanStepDraft(text="Net refund reversals against the chargeback total"),
            ]
        ),
    )
    llm.on("coder", CoderOutput(source="import pandas as pd  # v2"))
    sandbox.push_success(stdout=_STDOUT)
    llm.on("verifier", Verdict(sufficient=True, reason="chargeback total is now correct"))
    llm.on(
        "finalizer",
        FinalizerOutput(answer="Total chargeback amount, net of refunds, is $1250.00."),
    )

    return Scenario(llm, sandbox, _retriever(), make_run_state(), RunStatus.SUCCEEDED, "1250", 3)


def backtrack() -> Scenario:
    """Insufficient -> router BACKTRACK index=1 -> truncate -> replan -> sufficient.

    Node calls: plan x2, code x2, execute x2, verify x2 (insufficient, sufficient),
    route x1 (backtrack index=1), truncate x1, finalize x1.
    """
    llm = FakeLLM()
    sandbox = FakeSandbox()

    llm.on(
        "planner",
        PlannerOutput(
            steps=[
                PlanStepDraft(text="Load payments.csv"),
                PlanStepDraft(text="Sum chargebacks grouped by capture day"),
            ]
        ),
    )
    llm.on("coder", CoderOutput(source="import pandas as pd  # group by day"))
    sandbox.push_success(stdout=_STDOUT)
    llm.on(
        "verifier",
        Verdict(
            sufficient=False,
            reason="grouped by the wrong key so the total is wrong",
            missing_aspects=["grouping"],
        ),
    )
    llm.on(
        "router",
        RouterDecision(
            action=RouterAction.BACKTRACK,
            backtrack_index=1,
            rationale="wrong grouping key",
        ),
    )
    llm.on(
        "planner",
        PlannerOutput(
            steps=[
                PlanStepDraft(text="Load payments.csv"),
                PlanStepDraft(text="Sum chargebacks grouped by merchant"),
            ]
        ),
    )
    llm.on("coder", CoderOutput(source="import pandas as pd  # group by merchant"))
    sandbox.push_success(stdout=_STDOUT)
    llm.on("verifier", Verdict(sufficient=True, reason="correct after regrouping by merchant"))
    llm.on(
        "finalizer",
        FinalizerOutput(
            answer=(
                "After a backtrack to regroup by merchant, the total chargeback amount is $1250.00."
            )
        ),
    )

    return Scenario(llm, sandbox, _retriever(), make_run_state(), RunStatus.SUCCEEDED, "1250", 3)


def _research_child_turn(llm: FakeLLM, sandbox: FakeSandbox, answer: str) -> None:
    llm.on("planner", PlannerOutput(steps=[PlanStepDraft(text="Load and compute")]))
    llm.on("coder", CoderOutput(source="print('x')"))
    sandbox.push_success(stdout=_STDOUT)
    llm.on("verifier", Verdict(sufficient=True, reason="the number is correct here"))
    llm.on("finalizer", FinalizerOutput(answer=answer))


def research_scenario() -> Scenario:
    """DS-STAR+: 2 initial sub-questions + 1 gap round -> a cited report."""
    llm, sandbox = FakeLLM(), FakeSandbox()
    llm.on(
        "subquestion_generator",
        SubQuestionList(
            questions=[
                SubQuestionDraft(index=1, text="Total volume by merchant?"),
                SubQuestionDraft(index=2, text="Chargeback rate by month?"),
            ]
        ),
    )
    _research_child_turn(llm, sandbox, "Volume is 1,000.")
    _research_child_turn(llm, sandbox, "Rate is 2.5%.")
    llm.on(
        "report_writer",
        ReportOutput(markdown="# Draft report\nVolume 1,000 [SQ-1]; rate 2.5% [SQ-2]."),
    )
    llm.on(
        "subquestion_generator",
        SubQuestionList(questions=[SubQuestionDraft(index=3, text="Top merchant by loss?")]),
    )
    _research_child_turn(llm, sandbox, "Merchant Acme, 300 in losses.")
    llm.on(
        "report_writer",
        ReportOutput(
            markdown="# Final report\n\n## Executive Summary\nVolume 1,000 [SQ-1]; "
            "rate 2.5% [SQ-2]; top merchant Acme [SQ-3]."
        ),
    )

    state = make_run_state()
    state.mode = RunMode.RESEARCH
    return Scenario(llm, sandbox, _retriever(), state, RunStatus.SUCCEEDED, "[SQ-", 3)


__all__ = ["Scenario", "backtrack", "happy_path", "multi_round", "research_scenario"]
