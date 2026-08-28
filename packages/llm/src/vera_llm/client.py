"""``LLMClient`` — the ``LLMPort`` implementation for BYOK providers.

Phase 2 only wires the ``validate_connection`` path. ``complete`` lands in
Phase 4; ``list_models`` is intentionally not served here — see its docstring.
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel
from vera_core.models.ids import ProviderConnectionId, RunId
from vera_core.models.provider import ModelInfo, ProviderKind, ValidationResult
from vera_core.ports.key_vault import KeyVaultPort
from vera_core.ports.llm import LLMResponse
from vera_core.ports.repository import ProviderRepositoryPort

from vera_llm.validation import validate_connection as _validate_connection


class LLMClient:
    """Provider-agnostic LLM client. Satisfies ``vera_core.ports.llm.LLMPort``."""

    def __init__(
        self,
        *,
        key_vault: KeyVaultPort,
        provider_repo: ProviderRepositoryPort,
        http: httpx.AsyncClient,
    ) -> None:
        self._key_vault = key_vault
        self._provider_repo = provider_repo
        self._http = http

    async def validate_connection(
        self,
        *,
        kind: ProviderKind,
        base_url: str,
        api_key: str,
    ) -> ValidationResult:
        """Delegate to :func:`vera_llm.validation.validate_connection`."""
        return await _validate_connection(
            kind=kind, base_url=base_url, api_key=api_key, http=self._http
        )

    async def list_models(
        self,
        *,
        provider_connection_id: ProviderConnectionId,
    ) -> list[ModelInfo]:
        """Not served by the client in Phase 2.

        The cached model list is tenant-scoped, and ``ProviderRepositoryPort``
        exposes no lookup keyed by ``provider_connection_id`` alone
        (``get_connection`` needs ``tenant_id``, ``list_connections`` needs
        ``user_id``). Reading or refreshing models therefore happens in the
        CLI's ``provider_service``, which holds that context. This method is
        promoted to a real implementation once the API composition layer
        (Phase 6) supplies a tenant-aware read path.
        """
        raise NotImplementedError(
            "list_models is served by apps/cli provider_service in Phase 2; "
            "see docs/superpowers/specs/2026-08-28-phase-2-supabase-byok-design.md §7"
        )

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
        raise NotImplementedError("LLM completion lands in Phase 4")


__all__ = ["LLMClient"]
