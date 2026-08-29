"""Sub-Question Generator agent (DS-STAR+) — decomposes a research query."""

from __future__ import annotations

from dataclasses import dataclass, field

from vera_core.agents._shared import run_structured_agent
from vera_core.agents._types import SubQuestionList
from vera_core.agents.base import AgentContext
from vera_core.models.agent_config import AgentTier
from vera_core.ports.llm import LLMResponse


@dataclass(frozen=True)
class SubQGenPayload:
    query: str
    descriptions: list[str]
    existing_questions: list[str] = field(default_factory=list)
    draft_report: str | None = None


class SubQuestionGeneratorAgent:
    name = "subquestion_generator"
    tier = AgentTier.REASONING

    async def run(
        self, ctx: AgentContext, payload: SubQGenPayload
    ) -> tuple[SubQuestionList, LLMResponse]:
        return await run_structured_agent(
            ctx,
            agent=self.name,
            tier=self.tier,
            template_vars={
                "query": payload.query,
                "descriptions": payload.descriptions,
                "existing_questions": payload.existing_questions,
                "draft_report": payload.draft_report,
            },
            schema=SubQuestionList,
        )


subquestion_generator = SubQuestionGeneratorAgent()
__all__ = ["SubQGenPayload", "SubQuestionGeneratorAgent", "subquestion_generator"]
