"""ProviderService — connect / revalidate / disconnect orchestration for BYOK providers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from vera_core.errors import NotFoundError, ProviderAuthError
from vera_core.models.ids import ProviderConnectionId, TenantId, UserId
from vera_core.models.provider import (
    ConnectionStatus,
    ModelInfo,
    ProviderConnection,
    ProviderKind,
    ValidationResult,
)
from vera_core.ports.key_vault import KeyVaultPort
from vera_core.ports.repository import ProviderRepositoryPort
from vera_llm import PROVIDER_CONFIGS


class _ProviderRepo(ProviderRepositoryPort, Protocol):
    """``ProviderRepositoryPort`` plus the model-cache write the service needs."""

    async def replace_model_cache(
        self, *, provider_connection_id: ProviderConnectionId, models: list[ModelInfo]
    ) -> None: ...


class _Validator(Protocol):
    """Minimal validation surface (``vera_llm.LLMClient`` satisfies it)."""

    async def validate_connection(
        self, *, kind: ProviderKind, base_url: str, api_key: str
    ) -> ValidationResult: ...


def _now() -> datetime:
    return datetime.now(UTC)


def _ref(conn_id: ProviderConnectionId) -> str:
    return f"provider:{conn_id}:api_key"


class ProviderService:
    """Orchestrates the three-way write (connection row, Vault secret, model cache).

    ``session`` is optional so tests can drive the service with in-memory fakes.
    When present, every mutating method commits on success and rolls back on any
    error, so a failed Vault write can never leave an orphan connection row.
    """

    def __init__(
        self,
        *,
        repo: _ProviderRepo,
        vault: KeyVaultPort,
        validator: _Validator,
        session: AsyncSession | None = None,
    ) -> None:
        self._repo = repo
        self._vault = vault
        self._validator = validator
        self._session = session

    @asynccontextmanager
    async def _tx(self) -> AsyncIterator[None]:
        if self._session is None:
            yield
            return
        try:
            yield
            await self._session.commit()
        except BaseException:
            await self._session.rollback()
            raise

    async def connect(
        self,
        *,
        tenant_id: TenantId,
        user_id: UserId,
        kind: ProviderKind,
        api_key: str,
        display_name: str,
        base_url: str | None = None,
    ) -> ProviderConnection:
        """Validate the key, then persist connection + secret + model cache atomically."""
        resolved_base_url = base_url or PROVIDER_CONFIGS[kind].default_base_url
        result = await self._validator.validate_connection(
            kind=kind, base_url=resolved_base_url, api_key=api_key
        )
        if not result.valid:
            raise ProviderAuthError(result.error or "Validation failed")

        conn_id = ProviderConnectionId(uuid4())
        ref = _ref(conn_id)
        now = _now()
        # Concurrency / idempotency: the repo's unique (user_id, display_name)
        # constraint raises ConflictError on a duplicate name; two racing adds
        # let exactly one commit. A retry after any failure is safe because the
        # whole transaction (row + secret + cache) rolls back together.
        async with self._tx():
            conn = await self._repo.create_connection(
                conn=ProviderConnection(
                    id=conn_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    kind=kind,
                    display_name=display_name,
                    base_url=resolved_base_url,
                    api_key_ref=ref,
                    status=ConnectionStatus.CONNECTED,
                    available_models=result.models,
                    created_at=now,
                    last_validated_at=now,
                )
            )
            await self._vault.store(tenant_id=tenant_id, ref=ref, plaintext=api_key)
            await self._repo.replace_model_cache(
                provider_connection_id=conn_id, models=result.models
            )
        return conn.model_copy(update={"available_models": result.models})

    async def revalidate(
        self, *, tenant_id: TenantId, connection_id: ProviderConnectionId
    ) -> ProviderConnection:
        """Re-run validation with the stored key; update status and (on success) the cache."""
        conn = await self._repo.get_connection(id=connection_id, tenant_id=tenant_id)
        if conn is None:
            raise NotFoundError(f"Provider connection {connection_id} not found")

        api_key = await self._vault.retrieve(tenant_id=tenant_id, ref=conn.api_key_ref)
        result = await self._validator.validate_connection(
            kind=conn.kind, base_url=conn.base_url, api_key=api_key
        )
        now = _now()

        if result.valid:
            updated = conn.model_copy(
                update={
                    "status": ConnectionStatus.CONNECTED,
                    "last_error": None,
                    "last_validated_at": now,
                }
            )
            async with self._tx():
                out = await self._repo.update_connection(conn=updated)
                await self._repo.replace_model_cache(
                    provider_connection_id=connection_id, models=result.models
                )
            return out.model_copy(update={"available_models": result.models})

        # Validation failed upstream (e.g. key revoked): mark FAILED, keep the cache.
        failed = conn.model_copy(
            update={
                "status": ConnectionStatus.FAILED,
                "last_error": result.error or "Validation failed",
                "last_validated_at": now,
            }
        )
        async with self._tx():
            out = await self._repo.update_connection(conn=failed)
        return out

    async def disconnect(self, *, tenant_id: TenantId, connection_id: ProviderConnectionId) -> None:
        """Delete the connection row and its Vault secret in one transaction."""
        conn = await self._repo.get_connection(id=connection_id, tenant_id=tenant_id)
        if conn is None:
            raise NotFoundError(f"Provider connection {connection_id} not found")
        async with self._tx():
            await self._repo.delete_connection(id=connection_id, tenant_id=tenant_id)
            await self._vault.delete(tenant_id=tenant_id, ref=conn.api_key_ref)

    async def list_connections(self, *, user_id: UserId) -> list[ProviderConnection]:
        """Return the user's connections with their cached model lists populated."""
        return await self._repo.list_connections(user_id=user_id)


__all__ = ["ProviderService"]
