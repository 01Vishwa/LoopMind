"""Unit tests for ProviderService orchestration (fakes, no DB)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from conftest import FakeProviderRepo, FakeValidator, make_models
from vera_cli.services.provider_service import ProviderService
from vera_core.errors import ProviderAuthError
from vera_core.models.ids import TenantId, UserId
from vera_core.models.provider import ConnectionStatus, ProviderKind, ValidationResult
from vera_testing.fakes.vault import FakeKeyVault

TENANT = TenantId(uuid4())
USER = UserId(uuid4())


def _svc(result: ValidationResult) -> tuple[ProviderService, FakeProviderRepo, FakeKeyVault]:
    repo = FakeProviderRepo()
    vault = FakeKeyVault()
    svc = ProviderService(repo=repo, vault=vault, validator=FakeValidator(result))
    return svc, repo, vault


async def test_connect_writes_connection_vault_and_cache() -> None:
    svc, repo, vault = _svc(ValidationResult(valid=True, models=make_models(3)))

    conn = await svc.connect(
        tenant_id=TENANT,
        user_id=USER,
        kind=ProviderKind.OPENROUTER,
        api_key="sk-or-v1-secret",
        display_name="OR",
    )

    assert conn.status is ConnectionStatus.CONNECTED
    assert len(repo.connections()) == 1
    assert len(repo.cache()[conn.id]) == 3
    assert vault.entries()[(str(TENANT), f"provider:{conn.id}:api_key")] == "sk-or-v1-secret"
    assert conn.available_models is not None and len(conn.available_models) == 3


async def test_connect_invalid_key_writes_nothing() -> None:
    svc, repo, vault = _svc(ValidationResult(valid=False, error="Invalid API key"))

    with pytest.raises(ProviderAuthError, match="Invalid API key"):
        await svc.connect(
            tenant_id=TENANT,
            user_id=USER,
            kind=ProviderKind.OPENROUTER,
            api_key="bad",
            display_name="OR",
        )

    assert repo.connections() == {}
    assert len(vault) == 0


async def test_disconnect_removes_connection_and_secret() -> None:
    svc, repo, vault = _svc(ValidationResult(valid=True, models=make_models(1)))
    conn = await svc.connect(
        tenant_id=TENANT,
        user_id=USER,
        kind=ProviderKind.NVIDIA_NIM,
        api_key="k",
        display_name="NIM",
    )

    await svc.disconnect(tenant_id=TENANT, connection_id=conn.id)

    assert repo.connections() == {}
    assert len(vault) == 0


async def test_revalidate_marks_failed_on_invalid_key() -> None:
    svc, repo, vault = _svc(ValidationResult(valid=True, models=make_models(2)))
    conn = await svc.connect(
        tenant_id=TENANT,
        user_id=USER,
        kind=ProviderKind.OPENROUTER,
        api_key="k",
        display_name="OR",
    )

    svc._validator.result = ValidationResult(valid=False, error="key revoked")  # type: ignore[attr-defined]
    out = await svc.revalidate(tenant_id=TENANT, connection_id=conn.id)

    assert out.status is ConnectionStatus.FAILED
    assert out.last_error == "key revoked"
    # cache is retained on failure
    assert len(repo.cache()[conn.id]) == 2
