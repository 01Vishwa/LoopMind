"""
Supabase client dependency.

Uses the SERVICE_ROLE key for server-side admin operations (verifying JWTs,
reading profiles). Never expose this key to clients.
"""

from collections.abc import AsyncIterator
from supabase._async.client import AsyncClient, create_client
from sqlalchemy.ext.asyncio import AsyncSession
from vera_db.engine import build_pooled_engine
from vera_db.session import make_sessionmaker, tenant_session
from .settings import settings
from .auth import require_authenticated_user
from fastapi import Depends

_client: AsyncClient | None = None
_engine = None
_sessionmaker = None


async def get_supabase_client() -> AsyncClient:
    """
    Returns a module-level singleton Supabase async client.

    FastAPI dependencies can call this directly. The client is created once on
    first use and reused for the lifetime of the process.
    """
    global _client
    if _client is None:
        _client = await create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_service_role_key.get_secret_value(),
        )
    return _client

def _get_sessionmaker():
    global _engine, _sessionmaker
    if _sessionmaker is None:
        db_url = settings.database_url.get_secret_value()
        _engine = build_pooled_engine(db_url)
        _sessionmaker = make_sessionmaker(_engine)
    return _sessionmaker

async def get_db_session(principal = Depends(require_authenticated_user)) -> AsyncIterator[AsyncSession]:
    sm = _get_sessionmaker()
    async with tenant_session(sm, principal.tenant_id) as session:
        yield session
