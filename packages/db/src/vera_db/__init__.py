"""vera_db — VERA persistence adapter (SQLAlchemy 2.0 + Supabase Postgres)."""

from __future__ import annotations

from vera_db.config import DbConfig
from vera_db.engine import build_direct_engine, build_pooled_engine
from vera_db.models.base import Base
from vera_db.repositories.provider_repository import ProviderRepository
from vera_db.repositories.vault_repository import VaultRepository
from vera_db.session import make_sessionmaker, tenant_session

__all__ = [
    "DbConfig",
    "build_pooled_engine",
    "build_direct_engine",
    "make_sessionmaker",
    "tenant_session",
    "Base",
    "ProviderRepository",
    "VaultRepository",
]
