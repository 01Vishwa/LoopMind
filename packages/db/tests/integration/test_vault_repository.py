"""Integration tests for VaultRepository against Supabase Vault."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from vera_core.errors import NotFoundError
from vera_core.models.ids import TenantId
from vera_db.repositories.vault_repository import VaultRepository

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("VERA_DATABASE_URL_DIRECT"),
        reason="VERA_DATABASE_URL_DIRECT not set",
    ),
]


async def test_store_retrieve_round_trip(session: AsyncSession) -> None:
    vault = VaultRepository(session=session)
    tenant_id = TenantId(uuid4())
    ref = f"provider:{uuid4()}:api_key"
    try:
        await vault.store(tenant_id=tenant_id, ref=ref, plaintext="sk-secret-1")
        assert await vault.retrieve(tenant_id=tenant_id, ref=ref) == "sk-secret-1"
    finally:
        await vault.delete(tenant_id=tenant_id, ref=ref)


async def test_store_twice_keeps_latest(session: AsyncSession) -> None:
    vault = VaultRepository(session=session)
    tenant_id = TenantId(uuid4())
    ref = f"provider:{uuid4()}:api_key"
    try:
        await vault.store(tenant_id=tenant_id, ref=ref, plaintext="sk-old")
        await vault.store(tenant_id=tenant_id, ref=ref, plaintext="sk-new")
        assert await vault.retrieve(tenant_id=tenant_id, ref=ref) == "sk-new"
    finally:
        await vault.delete(tenant_id=tenant_id, ref=ref)


async def test_delete_then_retrieve_raises(session: AsyncSession) -> None:
    vault = VaultRepository(session=session)
    tenant_id = TenantId(uuid4())
    ref = f"provider:{uuid4()}:api_key"
    await vault.store(tenant_id=tenant_id, ref=ref, plaintext="sk-secret")
    await vault.delete(tenant_id=tenant_id, ref=ref)
    with pytest.raises(NotFoundError):
        await vault.retrieve(tenant_id=tenant_id, ref=ref)


async def test_stored_secret_is_ciphertext(session: AsyncSession) -> None:
    vault = VaultRepository(session=session)
    tenant_id = TenantId(uuid4())
    ref = f"provider:{uuid4()}:api_key"
    name = f"t:{tenant_id}:{ref}"
    try:
        await vault.store(tenant_id=tenant_id, ref=ref, plaintext="sk-plaintext-value")
        raw = (
            await session.execute(
                text("select secret from vault.secrets where name = :name"), {"name": name}
            )
        ).scalar_one()
        assert raw != "sk-plaintext-value"
    finally:
        await vault.delete(tenant_id=tenant_id, ref=ref)
