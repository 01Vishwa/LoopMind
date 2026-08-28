from fastapi import APIRouter, Depends
from supabase._async.client import AsyncClient

from ...dependencies.auth import require_authenticated_user
from ...dependencies.db import get_supabase_client
from ...schemas.auth import Principal
from ...schemas.settings import (
    AgentDefaultsResponse,
    UpdateAgentDefaultsRequest
)
from ...services import settings_service

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/agent-defaults", response_model=AgentDefaultsResponse)
async def get_agent_defaults(
    principal: Principal = Depends(require_authenticated_user),
    supabase: AsyncClient = Depends(get_supabase_client)
):
    """
    Gets model assignments + run config.
    """
    return await settings_service.get_agent_defaults(principal, supabase)

@router.put("/agent-defaults", response_model=AgentDefaultsResponse)
async def update_agent_defaults(
    body: UpdateAgentDefaultsRequest,
    principal: Principal = Depends(require_authenticated_user),
    supabase: AsyncClient = Depends(get_supabase_client)
):
    """
    Updates model assignments + run config.
    """
    return await settings_service.update_agent_defaults(principal, body, supabase)

@router.post("/agent-defaults/reset", response_model=AgentDefaultsResponse)
async def reset_agent_defaults(
    principal: Principal = Depends(require_authenticated_user),
    supabase: AsyncClient = Depends(get_supabase_client)
):
    """
    Resets to recommended defaults.
    """
    return await settings_service.reset_agent_defaults(principal, supabase)
