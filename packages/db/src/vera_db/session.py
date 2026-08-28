"""Session factory and the tenant-scoped session context manager."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build an ``async_sessionmaker`` with ``expire_on_commit=False``."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def tenant_session(
    sm: async_sessionmaker[AsyncSession], tenant_id: UUID
) -> AsyncIterator[AsyncSession]:
    """Open a transaction with ``app.tenant_id`` set for RLS-scoped access."""
    async with sm() as session, session.begin():
        await session.execute(
            text("select set_config('app.tenant_id', :tid, true)"),
            {"tid": str(tenant_id)},
        )
        yield session


__all__ = ["make_sessionmaker", "tenant_session"]
