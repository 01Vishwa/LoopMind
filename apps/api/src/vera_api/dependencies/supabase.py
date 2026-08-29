from supabase._async.client import AsyncClient, create_client
from vera_api.settings import settings

_client: AsyncClient | None = None

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
