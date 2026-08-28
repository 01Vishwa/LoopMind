"""
Auth dependency — FastAPI Depends() for protected routes.

Usage:
    @router.get("/some-protected-resource")
    async def my_handler(principal: Principal = Depends(get_current_user)):
        ...
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Header

from vera_api.dependencies.db import get_supabase_client
from supabase._async.client import AsyncClient


@dataclass
class Principal:
    """The authenticated user context, injected into every protected route."""

    user_id: str      # auth.uid() — the Supabase Auth UUID
    tenant_id: str    # from public.profiles
    email: str
    role: str         # owner | admin | analyst | viewer


async def get_current_user(
    authorization: str = Header(..., description="Bearer <supabase_access_token>"),
    supabase: AsyncClient = Depends(get_supabase_client),
) -> Principal:
    """
    Verify the Supabase JWT and load the caller's profile.

    Steps:
    1. Strip "Bearer " prefix from the Authorization header.
    2. Call supabase.auth.get_user(token) — verifies signature + expiry.
    3. Load the matching row from public.profiles.
    4. Return a Principal with the user's identity and tenant.

    Raises HTTPException(401) on any auth failure.
    """
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="missing_token")

    # 1. Verify with Supabase Auth (checks signature + expiry).
    try:
        user_response = await supabase.auth.get_user(token)
    except Exception as exc:
        if "expired" in str(exc).lower():
            raise HTTPException(status_code=401, detail="session_expired")
        raise HTTPException(status_code=401, detail="invalid_token")

    if not user_response or not user_response.user:
        raise HTTPException(status_code=401, detail="invalid_token")

    user_id = user_response.user.id

    # 2. Load profile from public.profiles.
    try:
        profile_response = (
            await supabase.table("profiles")
            .select("id, tenant_id, email, full_name, role")
            .eq("id", user_id)
            .single()
            .execute()
        )
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_token")

    if not profile_response.data:
        raise HTTPException(status_code=401, detail="invalid_token")

    data = profile_response.data
    return Principal(
        user_id=data["id"],
        tenant_id=data["tenant_id"],
        email=data["email"],
        role=data["role"],
    )
