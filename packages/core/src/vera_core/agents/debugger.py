"""Debugger agent — returns a corrected replacement script after a crash."""

from __future__ import annotations

from dataclasses import dataclass

from vera_core.agents._shared import run_structured_agent
from vera_core.agents._types import CoderOutput
from vera_core.agents.base import AgentContext
from vera_core.models.agent_config import AgentTier
from vera_core.ports.llm import LLMResponse


@dataclass(frozen=True)
class DebuggerPayload:
    code: str
    stderr: str


class DebuggerAgent:
    name = "debugger"
    tier = AgentTier.UTILITY

    async def run(
        self, ctx: AgentContext, payload: DebuggerPayload
    ) -> tuple[CoderOutput, LLMResponse]:
        return await run_structured_agent(
            ctx,
            agent=self.name,
            tier=self.tier,
            template_vars={"code": payload.code, "stderr": payload.stderr},
            schema=CoderOutput,
        )


debugger = DebuggerAgent()
__all__ = ["DebuggerAgent", "DebuggerPayload", "debugger"]
