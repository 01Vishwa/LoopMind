"""Agent protocol and the context every agent receives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from vera_core.models.agent_config import AgentDefaults, AgentTier
from vera_core.models.ids import RunId
from vera_core.ports.llm import LLMPort, LLMResponse
from vera_core.prompts import PromptRegistry


@dataclass(frozen=True)
class AgentContext:
    """Everything an agent needs to make one structured LLM call."""

    llm: LLMPort
    defaults: AgentDefaults
    registry: PromptRegistry
    run_id: RunId


class Agent[TIn, TOut](Protocol):
    name: str
    tier: AgentTier

    async def run(self, ctx: AgentContext, payload: TIn) -> tuple[TOut, LLMResponse]: ...


__all__ = ["Agent", "AgentContext"]
