"""Unit tests asserting ORM metadata mirrors the Supabase schema (no database)."""

from __future__ import annotations

from vera_db.models.base import Base


def test_expected_tables_present() -> None:
    assert set(Base.metadata.tables) == {
        "tenants",
        "users",
        "provider_connections",
        "provider_models_cache",
    }


def test_tenants_columns() -> None:
    cols = set(Base.metadata.tables["tenants"].columns.keys())
    assert cols == {"id", "name", "plan", "created_at"}


def test_users_columns() -> None:
    cols = set(Base.metadata.tables["users"].columns.keys())
    assert cols == {"id", "tenant_id", "email", "full_name", "role", "created_at"}


def test_provider_connections_columns() -> None:
    cols = set(Base.metadata.tables["provider_connections"].columns.keys())
    assert cols == {
        "id",
        "tenant_id",
        "user_id",
        "kind",
        "display_name",
        "base_url",
        "api_key_ref",
        "status",
        "last_validated_at",
        "last_error",
        "created_at",
    }


def test_provider_models_cache_columns_and_pk() -> None:
    table = Base.metadata.tables["provider_models_cache"]
    assert set(table.columns.keys()) == {
        "provider_connection_id",
        "model_id",
        "display_name",
        "context_window",
        "input_price_per_m",
        "output_price_per_m",
        "supports_json_mode",
        "supports_function_calling",
        "supports_vision",
        "cached_at",
    }
    assert {c.name for c in table.primary_key.columns} == {
        "provider_connection_id",
        "model_id",
    }


def test_provider_connections_unique_user_display_name() -> None:
    from sqlalchemy import UniqueConstraint

    table = Base.metadata.tables["provider_connections"]
    uniques = [
        {c.name for c in con.columns}
        for con in table.constraints
        if isinstance(con, UniqueConstraint)
    ]
    assert {"user_id", "display_name"} in uniques
