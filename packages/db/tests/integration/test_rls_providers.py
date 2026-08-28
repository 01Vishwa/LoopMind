"""RLS smoke test — the authenticated role cannot see another tenant's rows.

Needs a second DSN that connects as the Supabase ``authenticated`` role, provided
via ``VERA_TEST_AUTHENTICATED_URL``. Skipped when it is unset.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from vera_db.engine import build_direct_engine
from vera_db.session import make_sessionmaker

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("VERA_DATABASE_URL_DIRECT"),
        reason="VERA_DATABASE_URL_DIRECT not set",
    ),
]

_AUTHED_URL = os.environ.get("VERA_TEST_AUTHENTICATED_URL")

_skip_authed = pytest.mark.skipif(
    not _AUTHED_URL,
    reason="VERA_TEST_AUTHENTICATED_URL not set — needs a DSN for the authenticated role",
)


@_skip_authed
async def test_authenticated_role_cannot_see_other_tenant(
    session: AsyncSession, make_tenant_user: Callable[[], tuple[UUID, UUID]]
) -> None:
    tenant_b, user_b = await make_tenant_user()
    # service-role session inserts a tenant-B provider connection
    conn_id = uuid4()
    await session.execute(
        text(
            "insert into public.provider_connections "
            "(id, tenant_id, user_id, kind, display_name, base_url, api_key_ref, status) "
            "values (:id, :tid, :uid, 'openrouter', 'b-conn', 'https://x', 'ref', 'connected')"
        ),
        {"id": conn_id, "tid": tenant_b, "uid": user_b},
    )
    await session.commit()

    tenant_a = uuid4()
    assert _AUTHED_URL is not None
    authed_engine = build_direct_engine(_AUTHED_URL)
    try:
        sm = make_sessionmaker(authed_engine)
        async with sm() as authed, authed.begin():
            await authed.execute(
                text("select set_config('request.jwt.claims', :claims, true)"),
                {"claims": f'{{"tenant_id":"{tenant_a}"}}'},
            )
            visible = (
                await authed.execute(
                    text("select count(*) from public.provider_connections where id = :id"),
                    {"id": conn_id},
                )
            ).scalar_one()
            assert visible == 0
    finally:
        await authed_engine.dispose()
        await session.execute(
            text("delete from public.provider_connections where id = :id"), {"id": conn_id}
        )
        await session.commit()
