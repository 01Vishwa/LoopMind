"""FakeLLM — deterministic LLM implementation for unit tests.

Usage:
    llm = FakeLLM()
    llm.push_response("The answer is 42")          # next call returns this
    llm.push_parsed(MySchema(field="value"))        # next call returns parsed object
    response = await llm.complete(...)
    assert llm.call_count == 1
    assert llm.last_call["model_id"] == "gpt-4o"
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from vera_core.models.ids import ProviderConnectionId, RunId
from vera_core.models.provider import ModelInfo, ProviderKind, ValidationResult
from vera_core.ports.llm import LLMResponse


class FakeLLM:
    """Scripted LLM that returns pre-loaded responses in order.

    Thread-safe for asyncio usage (single-event-loop assumption).
    """

    def __init__(self) -> None:
        self._queue: list[LLMResponse] = []
        self._agent_queues: dict[str, list[LLMResponse]] = {}
        self.calls: list[dict[str, Any]] = []

    # ── Response scripting ────────────────────────────────────────────────────

    def push_response(
        self,
        content: str,
        *,
        cost_usd: Decimal = Decimal("0.001"),
        input_tokens: int = 100,
        output_tokens: int = 50,
    ) -> None:
        """Queue a plain-text response."""
        self._queue.append(
            LLMResponse(
                content=content,
                cost_usd=cost_usd,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model_id="fake/model",
                latency_ms=10,
                provider_kind=ProviderKind.OPENROUTER,
            )
        )

    def push_parsed(
        self,
        parsed: BaseModel,
        *,
        cost_usd: Decimal = Decimal("0.001"),
    ) -> None:
        """Queue a response that includes a parsed Pydantic object."""
        content = parsed.model_dump_json()
        self._queue.append(
            LLMResponse(
                content=content,
                parsed=parsed,
                cost_usd=cost_usd,
                input_tokens=100,
                output_tokens=50,
                model_id="fake/model",
                latency_ms=10,
                provider_kind=ProviderKind.OPENROUTER,
            )
        )

    def push_error(self, exc: Exception) -> None:
        """Queue an exception to be raised on the next call."""
        # Store as a sentinel
        self._queue.append(exc)  # type: ignore[arg-type]

    def on(
        self,
        agent: str,
        obj: BaseModel | str,
        *,
        cost_usd: Decimal = Decimal("0.001"),
    ) -> None:
        """Queue a response addressed to a specific agent name.

        ``complete()`` prefers the per-agent queue matching its ``agent=`` kwarg
        and falls back to the global queue when that queue is empty.
        """
        if isinstance(obj, str):
            response = LLMResponse(
                content=obj,
                cost_usd=cost_usd,
                input_tokens=100,
                output_tokens=50,
                model_id="fake/model",
                latency_ms=10,
                provider_kind=ProviderKind.OPENROUTER,
            )
        else:
            response = LLMResponse(
                content=obj.model_dump_json(),
                parsed=obj,
                cost_usd=cost_usd,
                input_tokens=100,
                output_tokens=50,
                model_id="fake/model",
                latency_ms=10,
                provider_kind=ProviderKind.OPENROUTER,
            )
        self._agent_queues.setdefault(agent, []).append(response)

    # ── Port implementation ───────────────────────────────────────────────────

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
    ) -> LLMResponse:
        self.calls.append(
            {
                "provider_connection_id": provider_connection_id,
                "model_id": model_id,
                "messages": messages,
                "response_schema": response_schema,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "run_id": run_id,
                "agent": agent,
            }
        )

        agent_queue = self._agent_queues.get(agent)
        queue = agent_queue if agent_queue else self._queue

        if not queue:
            raise RuntimeError(
                f"FakeLLM has no queued responses. "
                f"Call push_response(), push_parsed(), or on() before completing. "
                f"Call #{len(self.calls)} was for agent={agent!r}"
            )

        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item

        # If caller asked for parsed output but we only have content, attempt parse
        if response_schema is not None and item.parsed is None:
            try:
                parsed = response_schema.model_validate_json(item.content)
                return item.model_copy(update={"parsed": parsed})
            except Exception:
                pass

        return item

    @staticmethod
    def _available_models() -> list[ModelInfo]:
        return [
            ModelInfo(
                model_id="fake/model",
                display_name="Fake Model",
                context_window=128000,
                supports_json_mode=True,
                supports_function_calling=True,
            )
        ]

    async def list_models(
        self,
        *,
        provider_connection_id: ProviderConnectionId,
    ) -> list[ModelInfo]:
        return self._available_models()

    async def validate_connection(
        self,
        *,
        kind: ProviderKind,
        base_url: str,
        api_key: str,
    ) -> ValidationResult:
        return ValidationResult(valid=True, models=self._available_models())

    # ── Inspection helpers ────────────────────────────────────────────────────

    @property
    def call_count(self) -> int:
        return len(self.calls)

    @property
    def last_call(self) -> dict[str, Any]:
        if not self.calls:
            raise IndexError("No calls recorded")
        return self.calls[-1]

    @property
    def queue_length(self) -> int:
        return len(self._queue) + sum(len(q) for q in self._agent_queues.values())


__all__ = ["FakeLLM"]
