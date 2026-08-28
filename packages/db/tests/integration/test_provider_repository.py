"""Integration tests for ProviderRepository against a live Supabase Postgres."""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from vera_core.errors import ConflictError
from vera_core.models.ids import ProviderConnectionId, TenantId, UserId
from vera_core.models.provider import (
    ConnectionStatus,
    ModelInfo,
    ProviderConnection,
    ProviderKind,
)
from vera_db.repositories.provider_repository import ProviderRepository

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("VERA_DATABASE_URL_DIRECT"),
        reason="VERA_DATABASE_URL_DIRECT not set",
    ),
]


def _conn(tenant_id: UUID, user_id: UUID, *, name: str = "OpenRouter") -> ProviderConnection:
    return ProviderConnection(
        id=ProviderConnectionId(uuid4()),
        tenant_id=TenantId(tenant_id),
        user_id=UserId(user_id),
        kind=ProviderKind.OPENROUTER,
        display_name=name,
        base_url="https://openrouter.ai/api/v1",
        api_key_ref=f"provider:{uuid4()}:api_key",
        status=ConnectionStatus.CONNECTED,
        created_at=datetime.now(UTC),
        last_validated_at=datetime.now(UTC),
    )


def _model(model_id: str) -> ModelInfo:
    return ModelInfo(model_id=model_id, display_name=model_id, context_window=8192)


async def test_crud_round_trip(
    session: AsyncSession, make_tenant_user: Callable[[], tuple[UUID, UUID]]
) -> None:
    tenant_id, user_id = await make_tenant_user()
    repo = ProviderRepository(session=session)

    created = await repo.create_connection(conn=_conn(tenant_id, user_id))
    fetched = await repo.get_connection(id=created.id, tenant_id=TenantId(tenant_id))
    assert fetched is not None
    assert fetched.display_name == "OpenRouter"

    updated = await repo.update_connection(
        conn=created.model_copy(update={"status": ConnectionStatus.FAILED, "last_error": "boom"})
    )
    assert updated.status is ConnectionStatus.FAILED

    await repo.delete_connection(id=created.id, tenant_id=TenantId(tenant_id))
    assert await repo.get_connection(id=created.id, tenant_id=TenantId(tenant_id)) is None


async def test_list_connections_returns_cached_models(
    session: AsyncSession, make_tenant_user: Callable[[], tuple[UUID, UUID]]
) -> None:
    tenant_id, user_id = await make_tenant_user()
    repo = ProviderRepository(session=session)
    created = await repo.create_connection(conn=_conn(tenant_id, user_id))
    await repo.replace_model_cache(
        provider_connection_id=created.id, models=[_model("a/x"), _model("a/y")]
    )

    listed = await repo.list_connections(user_id=UserId(user_id))
    assert len(listed) == 1
    assert listed[0].available_models is not None
    assert {m.model_id for m in listed[0].available_models} == {"a/x", "a/y"}


async def test_replace_model_cache_swaps_rows(
    session: AsyncSession, make_tenant_user: Callable[[], tuple[UUID, UUID]]
) -> None:
    tenant_id, user_id = await make_tenant_user()
    repo = ProviderRepository(session=session)
    created = await repo.create_connection(conn=_conn(tenant_id, user_id))
    await repo.replace_model_cache(provider_connection_id=created.id, models=[_model("old/m")])
    await repo.replace_model_cache(provider_connection_id=created.id, models=[_model("new/m")])

    listed = await repo.list_connections(user_id=UserId(user_id))
    assert listed[0].available_models is not None
    assert {m.model_id for m in listed[0].available_models} == {"new/m"}


async def test_duplicate_display_name_raises_conflict(
    session: AsyncSession, make_tenant_user: Callable[[], tuple[UUID, UUID]]
) -> None:
    tenant_id, user_id = await make_tenant_user()
    repo = ProviderRepository(session=session)
    await repo.create_connection(conn=_conn(tenant_id, user_id, name="dup"))
    with pytest.raises(ConflictError):
        await repo.create_connection(conn=_conn(tenant_id, user_id, name="dup"))
