import httpx
import re
from typing import Optional
from fastapi import HTTPException
from supabase._async.client import AsyncClient
from ..schemas.providers import (
    TestProviderKeyRequest,
    TestKeyResponse,
    ModelsResponse,
    ModelInfoResponse,
    RegisterProviderRequest,
    ProviderConnectionResponse
)
from ..dependencies.auth import Principal

# Regex for key validation on server
KEY_PATTERNS = {
    "openrouter": re.compile(r"^sk-or-v1-[A-Za-z0-9]{16,}$"),
    "nvidia_nim": re.compile(r"^nvapi-[A-Za-z0-9-]{16,}$")
}

PROVIDER_URLS = {
    "openrouter": "https://openrouter.ai/api/v1/models",
    "nvidia_nim": "https://integrate.api.nvidia.com/v1/models"
}

MAX_PROVIDER_CONNECTIONS_PER_USER = 10

async def test_provider_key(body: TestProviderKeyRequest) -> TestKeyResponse:
    if not KEY_PATTERNS[body.kind].match(body.api_key.strip()):
        return TestKeyResponse(status="invalid_format")
        
    url = body.base_url or PROVIDER_URLS[body.kind]
    headers = {"Authorization": f"Bearer {body.api_key.strip()}"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            
        if response.status_code in (401, 403):
            return TestKeyResponse(status="invalid_key")
        
        response.raise_for_status()
        
        data = response.json()
        models = data.get("data", [])
        return TestKeyResponse(status="valid", model_count=len(models))
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code >= 500:
            return TestKeyResponse(status="provider_unreachable")
        return TestKeyResponse(status="provider_unreachable")
    except (httpx.RequestError, httpx.TimeoutException):
        return TestKeyResponse(status="provider_unreachable")

async def fetch_provider_models(body: TestProviderKeyRequest) -> ModelsResponse:
    if not KEY_PATTERNS[body.kind].match(body.api_key.strip()):
        raise HTTPException(status_code=400, detail="invalid_format")
        
    url = body.base_url or PROVIDER_URLS[body.kind]
    headers = {"Authorization": f"Bearer {body.api_key.strip()}"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            
        if response.status_code in (401, 403):
            raise HTTPException(status_code=401, detail="invalid_key")
        
        response.raise_for_status()
        data = response.json()
        raw_models = data.get("data", [])
        
        models = []
        for m in raw_models:
            # Basic parsing; provider schemas for models vary
            model_id = m.get("id", "")
            display_name = m.get("name") or model_id
            context_window = m.get("context_length") or m.get("max_position_embeddings") or None
            
            pricing = m.get("pricing", {})
            input_price = float(pricing.get("prompt", 0)) if "prompt" in pricing else None
            output_price = float(pricing.get("completion", 0)) if "completion" in pricing else None
            
            models.append(ModelInfoResponse(
                model_id=model_id,
                display_name=display_name,
                context_window=context_window,
                input_price_per_m=input_price * 1000000 if input_price is not None else None,
                output_price_per_m=output_price * 1000000 if output_price is not None else None,
                supports_json_mode=True, # Fallback true for demo
                supports_vision=False # Fallback false
            ))
            
        return ModelsResponse(models=models)
        
    except Exception as e:
        raise HTTPException(status_code=502, detail="provider_unreachable")

async def register_provider_connection(
    principal: Principal,
    body: RegisterProviderRequest,
    supabase: AsyncClient
) -> ProviderConnectionResponse:
    # Check limit
    res = await supabase.table("provider_connections").select("id", count="exact").eq("user_id", str(principal.user_id)).execute()
    count = res.count if res.count is not None else len(res.data)
    if count >= MAX_PROVIDER_CONNECTIONS_PER_USER:
        raise HTTPException(status_code=409, detail="connection_limit_reached")
        
    res = await supabase.table("provider_connections").insert({
        "tenant_id": str(principal.tenant_id),
        "user_id": str(principal.user_id),
        "kind": body.kind,
        "display_name": body.display_name
    }).execute()
    
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create connection")
        
    row = res.data[0]
    return ProviderConnectionResponse(**row)

async def delete_provider_connection(
    principal: Principal,
    connection_id: str,
    supabase: AsyncClient
):
    # Cascades will nullify the provider_connection_id in agent_model_assignments
    await supabase.table("provider_connections").delete().eq("id", connection_id).eq("user_id", str(principal.user_id)).execute()

async def list_provider_connections(
    principal: Principal,
    supabase: AsyncClient
) -> list[ProviderConnectionResponse]:
    res = await supabase.table("provider_connections").select("*").eq("user_id", str(principal.user_id)).execute()
    return [ProviderConnectionResponse(**row) for row in res.data]
