"""Shared helper — render a prompt, call the LLM, validate the structured output."""

from __future__ import annotations

from pydantic import BaseModel

from vera_core.agents.base import AgentContext
from vera_core.errors import AgentOutputError
from vera_core.models.agent_config import AgentTier
from vera_core.ports.llm import LLMResponse


async def run_structured_agent[ModelT: BaseModel](
    ctx: AgentContext,
    *,
    agent: str,
    tier: AgentTier,
    template_vars: dict[str, object],
    schema: type[ModelT],
) -> tuple[ModelT, LLMResponse]:
    assignment = ctx.defaults.get_assignment(tier)
    template = ctx.registry.get(agent)
    rendered = template.render(**template_vars)
    response = await ctx.llm.complete(
        provider_connection_id=assignment.provider_connection_id,
        model_id=assignment.model_id,
        messages=[{"role": "system", "content": rendered}],
        response_schema=schema,
        temperature=assignment.temperature,
        max_tokens=assignment.max_tokens,
        run_id=ctx.run_id,
        agent=agent,
    )
    if response.parsed is None or not isinstance(response.parsed, schema):
        raise AgentOutputError(f"{agent} returned unparseable output: {response.content[:200]}")
    return response.parsed, response


__all__ = ["run_structured_agent"]
