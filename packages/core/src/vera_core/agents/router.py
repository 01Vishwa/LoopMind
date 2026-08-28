"""Router agent — decides add-step vs backtrack after an insufficient verdict."""

from __future__ import annotations

from dataclasses import dataclass

from vera_core.agents._shared import run_structured_agent
from vera_core.agents.base import AgentContext
from vera_core.models.agent_config import AgentTier
from vera_core.models.routing import RouterDecision
from vera_core.ports.llm import LLMResponse


@dataclass(frozen=True)
class RouterPayload:
    query: str
    verdict_reason: str
    missing_aspects: list[str]
    plan: list[str]


class RouterAgent:
    name = "router"
    tier = AgentTier.REASONING

    async def run(
        self, ctx: AgentContext, payload: RouterPayload
    ) -> tuple[RouterDecision, LLMResponse]:
        return await run_structured_agent(
            ctx,
            agent=self.name,
            tier=self.tier,
            template_vars={
                "query": payload.query,
                "verdict_reason": payload.verdict_reason,
                "missing_aspects": payload.missing_aspects,
                "plan": payload.plan,
            },
            schema=RouterDecision,
        )


router = RouterAgent()
__all__ = ["RouterAgent", "RouterPayload", "router"]
