"""Report Writer agent (DS-STAR+) — compiles sub-question answers into a cited report."""

from __future__ import annotations

from dataclasses import dataclass

from vera_core.agents._shared import run_structured_agent
from vera_core.agents._types import ReportOutput
from vera_core.agents.base import AgentContext
from vera_core.models.agent_config import AgentTier
from vera_core.ports.llm import LLMResponse


@dataclass(frozen=True)
class ReportAnswer:
    index: int
    text: str
    status: str
    answer: str | None = None


@dataclass(frozen=True)
class ReportWriterPayload:
    query: str
    answers: list[ReportAnswer]
    prior_report: str | None = None


class ReportWriterAgent:
    name = "report_writer"
    tier = AgentTier.REASONING

    async def run(
        self, ctx: AgentContext, payload: ReportWriterPayload
    ) -> tuple[ReportOutput, LLMResponse]:
        return await run_structured_agent(
            ctx,
            agent=self.name,
            tier=self.tier,
            template_vars={
                "query": payload.query,
                "answers": payload.answers,
                "prior_report": payload.prior_report,
            },
            schema=ReportOutput,
        )


report_writer = ReportWriterAgent()
__all__ = ["ReportAnswer", "ReportWriterAgent", "ReportWriterPayload", "report_writer"]
