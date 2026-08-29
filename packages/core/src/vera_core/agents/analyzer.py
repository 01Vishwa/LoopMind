"""Analyzer agent — summarizes one uploaded file into a FileDescription."""

from __future__ import annotations

from dataclasses import dataclass

from vera_core.agents._shared import run_structured_agent
from vera_core.agents._types import AnalyzerScriptOutput
from vera_core.agents.base import AgentContext
from vera_core.models.agent_config import AgentTier
from vera_core.ports.llm import LLMResponse


@dataclass(frozen=True)
class AnalyzePayload:
    file_id: str
    filename: str
    kind: str
    sample: str


class AnalyzerAgent:
    name = "analyzer"
    tier = AgentTier.UTILITY

    async def run(
        self, ctx: AgentContext, payload: AnalyzePayload
    ) -> tuple[AnalyzerScriptOutput, LLMResponse]:
        return await run_structured_agent(
            ctx,
            agent=self.name,
            tier=self.tier,
            template_vars={
                "file_id": payload.file_id,
                "filename": payload.filename,
                "kind": payload.kind,
                "sample": payload.sample,
            },
            schema=AnalyzerScriptOutput,
        )


analyzer = AnalyzerAgent()
__all__ = ["AnalyzePayload", "AnalyzerAgent", "analyzer"]
