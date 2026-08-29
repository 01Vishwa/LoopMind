from fastapi import APIRouter, Depends
from typing import List
from supabase._async.client import AsyncClient

from ...dependencies.auth import get_current_user
from ...dependencies.db import get_supabase_client
from ...dependencies.auth import Principal
from ...schemas.providers import (
    TestProviderKeyRequest,
    TestKeyResponse,
    ModelsResponse,
    RegisterProviderRequest,
    ProviderConnectionResponse
)
from ...services import provider_service

router = APIRouter(prefix="/providers", tags=["Providers"])

@router.post("/test", response_model=TestKeyResponse)
async def test_provider_key(
    body: TestProviderKeyRequest,
    principal: Principal = Depends(get_current_user)
):
    """
    Stateless key validation. The key is never persisted.
    """
    return await provider_service.test_provider_key(body)

@router.post("/models", response_model=ModelsResponse)
async def fetch_provider_models(
    body: TestProviderKeyRequest,
    principal: Principal = Depends(get_current_user)
):
    """
    Stateless model fetching. The key is never persisted.
    """
    return await provider_service.fetch_provider_models(body)

@router.post("", response_model=ProviderConnectionResponse)
async def register_provider_connection(
    body: RegisterProviderRequest,
    principal: Principal = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase_client)
):
    """
    Registers a connection metadata record (without the key).
    """
    return await provider_service.register_provider_connection(principal, body, supabase)

@router.get("", response_model=List[ProviderConnectionResponse])
async def list_provider_connections(
    principal: Principal = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase_client)
):
    """
    List user's provider connection records.
    """
    return await provider_service.list_provider_connections(principal, supabase)

@router.delete("/{connection_id}", status_code=204)
async def delete_provider_connection(
    connection_id: str,
    principal: Principal = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase_client)
):
    """
    Deletes a connection record and cascades to agent defaults.
    """
    await provider_service.delete_provider_connection(principal, connection_id, supabase)
