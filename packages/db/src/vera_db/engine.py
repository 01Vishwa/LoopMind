"""Async SQLAlchemy engine factories for pooled and direct Supabase connections."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool


def build_pooled_engine(url: str) -> AsyncEngine:
    """Engine for the Supavisor transaction pooler.

    pgbouncer transaction mode cannot reuse prepared statements, so the asyncpg
    statement caches are disabled and SQLAlchemy pooling is turned off.
    """
    return create_async_engine(
        url,
        poolclass=NullPool,
        echo=False,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )


def build_direct_engine(url: str) -> AsyncEngine:
    """Engine for a direct session-mode connection (migrations, RLS tests, NOTIFY)."""
    return create_async_engine(url, echo=False, pool_pre_ping=True)


__all__ = ["build_pooled_engine", "build_direct_engine"]
