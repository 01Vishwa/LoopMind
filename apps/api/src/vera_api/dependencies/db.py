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
from vera_api.settings import settings
from .supabase import get_supabase_client
from .auth import get_current_user
from fastapi import Depends

# _client has been moved to supabase.py
_engine = None
_sessionmaker = None

def _get_sessionmaker():
    global _engine, _sessionmaker
    if _sessionmaker is None:
        db_url = settings.database_url.get_secret_value()
        _engine = build_pooled_engine(db_url)
        _sessionmaker = make_sessionmaker(_engine)
    return _sessionmaker

async def get_db_session(principal = Depends(get_current_user)) -> AsyncIterator[AsyncSession]:
    sm = _get_sessionmaker()
    async with tenant_session(sm, principal.tenant_id) as session:
        yield session
