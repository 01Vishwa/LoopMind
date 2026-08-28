"""Shared fixtures and in-memory fakes for the vera_cli test-suite."""

from __future__ import annotations

import pytest
from vera_core.errors import ConflictError
from vera_core.models.ids import ProviderConnectionId, TenantId, UserId
from vera_core.models.provider import (
    ModelInfo,
    ProviderConnection,
    ProviderKind,
    ValidationResult,
)
from vera_testing.fakes.vault import FakeKeyVault


def make_models(n: int = 2) -> list[ModelInfo]:
    """Build ``n`` throwaway ``ModelInfo`` entries."""
    return [ModelInfo(model_id=f"m{i}", display_name=f"Model {i}") for i in range(n)]


class FakeProviderRepo:
    """In-memory ``ProviderRepositoryPort`` (+ ``replace_model_cache``) over dicts."""

    def __init__(self) -> None:
        self._conns: dict[ProviderConnectionId, ProviderConnection] = {}
        self._cache: dict[ProviderConnectionId, list[ModelInfo]] = {}

    async def create_connection(self, *, conn: ProviderConnection) -> ProviderConnection:
        for existing in self._conns.values():
            if existing.user_id == conn.user_id and existing.display_name == conn.display_name:
                raise ConflictError(f"{conn.display_name!r} already exists")
        stored = conn.model_copy(update={"available_models": None})
        self._conns[conn.id] = stored
        return stored

    async def get_connection(
        self, *, id: ProviderConnectionId, tenant_id: TenantId
    ) -> ProviderConnection | None:
        conn = self._conns.get(id)
        if conn is None or conn.tenant_id != tenant_id:
            return None
        return conn.model_copy(update={"available_models": self._cache.get(id)})

    async def list_connections(self, *, user_id: UserId) -> list[ProviderConnection]:
        return [
            c.model_copy(update={"available_models": self._cache.get(c.id)})
            for c in self._conns.values()
            if c.user_id == user_id
        ]

    async def update_connection(self, *, conn: ProviderConnection) -> ProviderConnection:
        if conn.id not in self._conns:
            raise ConflictError(f"{conn.id} not found")
        stored = conn.model_copy(update={"available_models": None})
        self._conns[conn.id] = stored
        return stored

    async def delete_connection(self, *, id: ProviderConnectionId, tenant_id: TenantId) -> None:
        conn = self._conns.get(id)
        if conn is not None and conn.tenant_id == tenant_id:
            del self._conns[id]
            self._cache.pop(id, None)

    async def replace_model_cache(
        self, *, provider_connection_id: ProviderConnectionId, models: list[ModelInfo]
    ) -> None:
        self._cache[provider_connection_id] = list(models)

    # ── test helpers ────────────────────────────────────────────────────────
    def connections(self) -> dict[ProviderConnectionId, ProviderConnection]:
        return dict(self._conns)

    def cache(self) -> dict[ProviderConnectionId, list[ModelInfo]]:
        return dict(self._cache)


class FakeValidator:
    """Returns a preloaded ``ValidationResult`` and records call args."""

    def __init__(self, result: ValidationResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def validate_connection(
        self, *, kind: ProviderKind, base_url: str, api_key: str
    ) -> ValidationResult:
        self.calls.append({"kind": kind, "base_url": base_url, "api_key": api_key})
        return self.result


@pytest.fixture
def fake_vault() -> FakeKeyVault:
    return FakeKeyVault()


@pytest.fixture
def fake_repo() -> FakeProviderRepo:
    return FakeProviderRepo()
