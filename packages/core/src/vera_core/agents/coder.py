"""Coder agent — writes a self-contained Python script for the current plan."""

from __future__ import annotations

from dataclasses import dataclass

from vera_core.agents._shared import run_structured_agent
from vera_core.agents._types import CoderOutput
from vera_core.agents.base import AgentContext
from vera_core.models.agent_config import AgentTier
from vera_core.ports.llm import LLMResponse


@dataclass(frozen=True)
class CoderPayload:
    query: str
    plan: list[str]
    last_stdout: str | None
    last_stderr: str | None
    prior_script: str | None = None


class CoderAgent:
    name = "coder"
    tier = AgentTier.REASONING

    async def run(
        self, ctx: AgentContext, payload: CoderPayload
    ) -> tuple[CoderOutput, LLMResponse]:
        return await run_structured_agent(
            ctx,
            agent=self.name,
            tier=self.tier,
            template_vars={
                "query": payload.query,
                "plan": payload.plan,
                "last_stdout": payload.last_stdout,
                "last_stderr": payload.last_stderr,
                "prior_script": payload.prior_script,
            },
            schema=CoderOutput,
        )


coder = CoderAgent()
__all__ = ["CoderAgent", "CoderPayload", "coder"]
