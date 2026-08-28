"""LLM port — the interface every agent uses to call a language model."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from vera_core.models.ids import ProviderConnectionId, RunId
from vera_core.models.provider import ModelInfo, ProviderKind, ValidationResult


class LLMResponse(BaseModel):
    content: str
    parsed: BaseModel | None = None  # populated when response_schema was provided
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: Decimal | None = None  # from provider header or computed
    model_id: str = ""
    latency_ms: int = 0
    provider_kind: ProviderKind = ProviderKind.OPENROUTER

    model_config = {"frozen": True, "arbitrary_types_allowed": True}


@runtime_checkable
class LLMPort(Protocol):
    """Provider-agnostic LLM interface. Implemented by vera_llm.LLMClient."""

    async def complete(
        self,
        *,
        provider_connection_id: ProviderConnectionId,
        model_id: str,
        messages: list[dict[str, Any]],
        response_schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        run_id: RunId | None = None,
        agent: str = "unknown",
    ) -> LLMResponse: ...

    async def list_models(
        self,
        *,
        provider_connection_id: ProviderConnectionId,
    ) -> list[ModelInfo]: ...

    async def validate_connection(
        self,
        *,
        kind: ProviderKind,
        base_url: str,
        api_key: str,
    ) -> ValidationResult: ...


__all__ = ["LLMPort", "LLMResponse"]
