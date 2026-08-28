"""CliRunner tests for `vera provider` — fakes injected, no DB, no real HTTP."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from conftest import FakeProviderRepo, FakeValidator, make_models
from typer.testing import CliRunner
from vera_cli.commands import provider as provider_cmd
from vera_cli.main import app
from vera_cli.services.provider_service import ProviderService
from vera_core.models.ids import TenantId, UserId
from vera_core.models.provider import ProviderKind, ValidationResult
from vera_testing.fakes.vault import FakeKeyVault

runner = CliRunner()
TENANT = uuid4()
USER = uuid4()
RAW_KEY = "sk-or-v1-supersecretvalue"


def _wire(monkeypatch: pytest.MonkeyPatch, result: ValidationResult) -> ProviderService:
    repo = FakeProviderRepo()
    vault = FakeKeyVault()
    svc = ProviderService(repo=repo, vault=vault, validator=FakeValidator(result))

    @asynccontextmanager
    async def _fake_service() -> AsyncIterator[ProviderService]:
        yield svc

    monkeypatch.setattr(provider_cmd, "_provider_service", _fake_service)
    return svc


def test_provider_add_masks_key_and_reports_model_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _wire(monkeypatch, ValidationResult(valid=True, models=make_models(5)))

    result = runner.invoke(
        app,
        [
            "provider",
            "add",
            "--kind",
            "openrouter",
            "--key",
            RAW_KEY,
            "--tenant",
            str(TENANT),
            "--user",
            str(USER),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "supersecretvalue" not in result.output
    assert "sk-or-v1****" in result.output
    assert "models=5" in result.output
    assert len(svc._repo.connections()) == 1  # type: ignore[attr-defined]
    assert len(svc._vault) == 1  # type: ignore[attr-defined]


def test_provider_add_invalid_key_exits_nonzero_and_hides_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _wire(monkeypatch, ValidationResult(valid=False, error="Invalid API key"))

    result = runner.invoke(
        app,
        [
            "provider",
            "add",
            "--kind",
            "openrouter",
            "--key",
            RAW_KEY,
            "--tenant",
            str(TENANT),
            "--user",
            str(USER),
        ],
    )

    assert result.exit_code != 0
    assert "supersecretvalue" not in result.output
    assert "Invalid API key" in result.output
    assert svc._repo.connections() == {}  # type: ignore[attr-defined]


def test_provider_list_renders_table(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = _wire(monkeypatch, ValidationResult(valid=True, models=make_models(2)))
    import asyncio

    asyncio.run(
        svc.connect(
            tenant_id=TenantId(TENANT),
            user_id=UserId(USER),
            kind=ProviderKind.OPENROUTER,
            api_key=RAW_KEY,
            display_name="My OR",
        )
    )

    result = runner.invoke(app, ["provider", "list", "--user", str(USER)])

    assert result.exit_code == 0, result.output
    assert "My OR" in result.output
    assert "openrouter" in result.output
    assert "event=provider.listed count=1" in result.output
