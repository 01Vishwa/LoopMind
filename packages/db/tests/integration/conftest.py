"""Fixtures for vera_db integration tests (require a live Supabase Postgres)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from vera_db.engine import build_direct_engine
from vera_db.session import make_sessionmaker

_DIRECT_URL = os.environ.get("VERA_DATABASE_URL_DIRECT")

pytestmark = pytest.mark.skipif(
    not _DIRECT_URL,
    reason="VERA_DATABASE_URL_DIRECT not set — integration tests need a live Supabase DB",
)


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[object]:
    assert _DIRECT_URL is not None
    eng = build_direct_engine(_DIRECT_URL)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def session(engine: object) -> AsyncIterator[AsyncSession]:
    sm = make_sessionmaker(engine)  # type: ignore[arg-type]
    async with sm() as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture
async def make_tenant_user(
    session: AsyncSession,
) -> AsyncIterator[Callable[[], tuple[UUID, UUID]]]:
    created: list[UUID] = []

    async def _make() -> tuple[UUID, UUID]:
        tenant_id = uuid4()
        user_id = uuid4()
        await session.execute(
            text("insert into public.tenants (id, name) values (:id, :name)"),
            {"id": tenant_id, "name": f"itest-{tenant_id}"},
        )
        await session.execute(
            text("insert into public.users (id, tenant_id, email) values (:id, :tid, :email)"),
            {"id": user_id, "tid": tenant_id, "email": f"{user_id}@itest.vera"},
        )
        await session.flush()
        created.append(tenant_id)
        return tenant_id, user_id

    yield _make

    for tenant_id in created:
        await session.execute(text("delete from public.tenants where id = :id"), {"id": tenant_id})
    await session.commit()


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)
