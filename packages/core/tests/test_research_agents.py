"""Sub-Question Generator and Report Writer agent unit tests."""

from __future__ import annotations

from uuid import uuid4

from vera_core.agents import (
    ReportAnswer,
    ReportWriterPayload,
    SubQGenPayload,
    report_writer,
    subquestion_generator,
)
from vera_core.agents._types import ReportOutput, SubQuestionDraft, SubQuestionList
from vera_core.agents.base import AgentContext
from vera_core.models.ids import RunId
from vera_core.prompts import PromptRegistry
from vera_testing.factories.domain import make_agent_defaults
from vera_testing.fakes import FakeLLM


def _ctx(llm: FakeLLM) -> AgentContext:
    return AgentContext(
        llm=llm, defaults=make_agent_defaults(), registry=PromptRegistry(), run_id=RunId(uuid4())
    )


async def test_subquestion_generator_initial_mode() -> None:
    llm = FakeLLM()
    llm.on(
        "subquestion_generator",
        SubQuestionList(
            questions=[
                SubQuestionDraft(
                    index=1, text="Total volume by merchant?", rationale="core metric"
                ),
                SubQuestionDraft(index=2, text="Chargeback rate by month?", rationale="trend"),
            ]
        ),
    )
    out, _ = await subquestion_generator.run(
        _ctx(llm),
        SubQGenPayload(query="Analyse chargebacks", descriptions=["payments.csv: merchant_id"]),
    )
    assert [q.index for q in out.questions] == [1, 2]
    assert llm.calls[-1]["agent"] == "subquestion_generator"


async def test_subquestion_generator_gap_mode_includes_draft_report() -> None:
    llm = FakeLLM()
    llm.on("subquestion_generator", SubQuestionList(questions=[]))
    await subquestion_generator.run(
        _ctx(llm),
        SubQGenPayload(
            query="q",
            descriptions=["f.csv"],
            existing_questions=["Total volume?"],
            draft_report="# Draft\nVolume is 100 [SQ-1].",
        ),
    )
    prompt = llm.calls[-1]["messages"][0]["content"]
    assert "Draft" in prompt and "Total volume?" in prompt


async def test_report_writer_draft_mode() -> None:
    llm = FakeLLM()
    llm.on("report_writer", ReportOutput(markdown="# Findings\nVolume is 100 [SQ-1]."))
    out, _ = await report_writer.run(
        _ctx(llm),
        ReportWriterPayload(
            query="q",
            answers=[ReportAnswer(index=1, text="Volume?", status="done", answer="100")],
        ),
    )
    assert "[SQ-1]" in out.markdown


async def test_report_writer_refine_mode_includes_prior_report() -> None:
    llm = FakeLLM()
    llm.on("report_writer", ReportOutput(markdown="# Findings v2\n... [SQ-1][SQ-2]."))
    await report_writer.run(
        _ctx(llm),
        ReportWriterPayload(
            query="q",
            answers=[ReportAnswer(index=2, text="Rate?", status="failed", answer=None)],
            prior_report="# Findings v1\nVolume is 100 [SQ-1].",
        ),
    )
    prompt = llm.calls[-1]["messages"][0]["content"]
    assert "Findings v1" in prompt
    assert "UNRESOLVED" in prompt
