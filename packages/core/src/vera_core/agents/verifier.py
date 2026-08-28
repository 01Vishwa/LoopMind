"""Verifier agent — judges whether the analysis answers the question."""

from __future__ import annotations

from dataclasses import dataclass

from vera_core.agents._shared import run_structured_agent
from vera_core.agents.base import AgentContext
from vera_core.models.agent_config import AgentTier
from vera_core.models.verdict import Verdict
from vera_core.ports.llm import LLMResponse


@dataclass(frozen=True)
class VerifierPayload:
    query: str
    plan: list[str]
    code: str
    observation: str


class VerifierAgent:
    name = "verifier"
    tier = AgentTier.REASONING

    async def run(self, ctx: AgentContext, payload: VerifierPayload) -> tuple[Verdict, LLMResponse]:
        return await run_structured_agent(
            ctx,
            agent=self.name,
            tier=self.tier,
            template_vars={
                "query": payload.query,
                "plan": payload.plan,
                "code": payload.code,
                "observation": payload.observation,
            },
            schema=Verdict,
        )


verifier = VerifierAgent()
__all__ = ["VerifierAgent", "VerifierPayload", "verifier"]
