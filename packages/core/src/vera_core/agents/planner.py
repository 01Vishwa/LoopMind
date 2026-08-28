"""Planner agent — produces an ordered list of concrete analysis steps."""

from __future__ import annotations

from dataclasses import dataclass

from vera_core.agents._shared import run_structured_agent
from vera_core.agents._types import PlannerOutput
from vera_core.agents.base import AgentContext
from vera_core.models.agent_config import AgentTier
from vera_core.ports.llm import LLMResponse


@dataclass(frozen=True)
class PlannerPayload:
    query: str
    descriptions: list[str]
    existing_steps: list[str]
    abandoned: list[str]


class PlannerAgent:
    name = "planner"
    tier = AgentTier.REASONING

    async def run(
        self, ctx: AgentContext, payload: PlannerPayload
    ) -> tuple[PlannerOutput, LLMResponse]:
        return await run_structured_agent(
            ctx,
            agent=self.name,
            tier=self.tier,
            template_vars={
                "query": payload.query,
                "descriptions": payload.descriptions,
                "existing_steps": payload.existing_steps,
                "abandoned": payload.abandoned,
            },
            schema=PlannerOutput,
        )


planner = PlannerAgent()
__all__ = ["PlannerAgent", "PlannerPayload", "planner"]
