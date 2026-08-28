"""Unit tests for DbConfig.from_env (no database required)."""

from __future__ import annotations

import pytest
from vera_core.errors import ValidationError
from vera_db.config import DbConfig


def test_from_env_raises_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VERA_DATABASE_URL", raising=False)
    monkeypatch.delenv("VERA_DATABASE_URL_DIRECT", raising=False)
    with pytest.raises(ValidationError, match="VERA_DATABASE_URL"):
        DbConfig.from_env()


def test_from_env_raises_when_direct_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERA_DATABASE_URL", "postgresql+asyncpg://x/postgres")
    monkeypatch.delenv("VERA_DATABASE_URL_DIRECT", raising=False)
    with pytest.raises(ValidationError, match="VERA_DATABASE_URL_DIRECT"):
        DbConfig.from_env()


def test_from_env_parses_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERA_DATABASE_URL", "postgresql+asyncpg://pooled/postgres")
    monkeypatch.setenv("VERA_DATABASE_URL_DIRECT", "postgresql+asyncpg://direct/postgres")
    cfg = DbConfig.from_env()
    assert cfg.url == "postgresql+asyncpg://pooled/postgres"
    assert cfg.direct_url == "postgresql+asyncpg://direct/postgres"


def test_config_is_frozen() -> None:
    cfg = DbConfig(url="a", direct_url="b")
    with pytest.raises(Exception):  # noqa: B017 - FrozenInstanceError
        cfg.url = "c"  # type: ignore[misc]
