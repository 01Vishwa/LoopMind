"""Finalizer agent — writes the final natural-language answer."""

from __future__ import annotations

from dataclasses import dataclass

from vera_core.agents._shared import run_structured_agent
from vera_core.agents._types import FinalizerOutput
from vera_core.agents.base import AgentContext
from vera_core.models.agent_config import AgentTier
from vera_core.ports.llm import LLMResponse


@dataclass(frozen=True)
class FinalizerPayload:
    query: str
    plan: list[str]
    observation: str
    degraded: bool


class FinalizerAgent:
    name = "finalizer"
    tier = AgentTier.UTILITY

    async def run(
        self, ctx: AgentContext, payload: FinalizerPayload
    ) -> tuple[FinalizerOutput, LLMResponse]:
        return await run_structured_agent(
            ctx,
            agent=self.name,
            tier=self.tier,
            template_vars={
                "query": payload.query,
                "plan": payload.plan,
                "observation": payload.observation,
                "degraded": payload.degraded,
            },
            schema=FinalizerOutput,
        )


finalizer = FinalizerAgent()
__all__ = ["FinalizerAgent", "FinalizerPayload", "finalizer"]
