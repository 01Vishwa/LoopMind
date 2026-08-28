from typing import Optional
from supabase._async.client import AsyncClient
from ..schemas.settings import (
    AgentDefaultsResponse,
    ModelAssignmentResponse,
    UpdateAgentDefaultsRequest
)
from ..schemas.auth import Principal

DEFAULT_DEFAULTS = {
    "max_rounds": 7,
    "max_cost_usd": 2.50,
    "max_debug_attempts": 3,
    "retriever_top_k": 12
}

async def get_agent_defaults(
    principal: Principal,
    supabase: AsyncClient
) -> AgentDefaultsResponse:
    # Fetch run limits and file processing defaults
    res = await supabase.table("agent_defaults").select("*").eq("user_id", str(principal.user_id)).execute()
    
    if not res.data:
        # Initialize defaults if they don't exist
        defaults = DEFAULT_DEFAULTS.copy()
        defaults["tenant_id"] = str(principal.tenant_id)
        defaults["user_id"] = str(principal.user_id)
        res = await supabase.table("agent_defaults").insert(defaults).select("*").execute()
        row = res.data[0]
    else:
        row = res.data[0]
        
    # Fetch assignments
    # We join with provider_connections to get provider_display_name
    # Since supabase JS client does joins nicely, we can do it via python too:
    # .select("*, provider_connections(display_name)")
    assign_res = await supabase.table("agent_model_assignments") \
        .select("tier, provider_connection_id, model_id, provider_connections(display_name)") \
        .eq("user_id", str(principal.user_id)).execute()
        
    assignments = []
    # Guarantee we return all 3 tiers even if not set
    tiers_found = set()
    for a in assign_res.data:
        tiers_found.add(a["tier"])
        provider = a.get("provider_connections") or {}
        assignments.append(ModelAssignmentResponse(
            tier=a["tier"],
            provider_connection_id=a["provider_connection_id"],
            model_id=a["model_id"],
            provider_display_name=provider.get("display_name"),
            model_display_name=a["model_id"]  # In a real app we might fetch display name from a cache
        ))
        
    for t in ["reasoning", "utility", "embedding"]:
        if t not in tiers_found:
            assignments.append(ModelAssignmentResponse(tier=t))

    return AgentDefaultsResponse(
        assignments=assignments,
        max_rounds=row["max_rounds"],
        max_cost_usd=float(row["max_cost_usd"]),
        max_debug_attempts=row["max_debug_attempts"],
        retriever_top_k=row["retriever_top_k"]
    )

async def update_agent_defaults(
    principal: Principal,
    body: UpdateAgentDefaultsRequest,
    supabase: AsyncClient
) -> AgentDefaultsResponse:
    update_data = {}
    if body.max_rounds is not None: update_data["max_rounds"] = body.max_rounds
    if body.max_cost_usd is not None: update_data["max_cost_usd"] = body.max_cost_usd
    if body.max_debug_attempts is not None: update_data["max_debug_attempts"] = body.max_debug_attempts
    if body.retriever_top_k is not None: update_data["retriever_top_k"] = body.retriever_top_k
    
    if update_data:
        # Upsert just in case it doesn't exist
        update_data["tenant_id"] = str(principal.tenant_id)
        update_data["user_id"] = str(principal.user_id)
        await supabase.table("agent_defaults").upsert(update_data, on_conflict="user_id").execute()
        
    if body.assignments is not None:
        for assignment in body.assignments:
            await supabase.table("agent_model_assignments").upsert({
                "tenant_id": str(principal.tenant_id),
                "user_id": str(principal.user_id),
                "tier": assignment.tier,
                "provider_connection_id": assignment.provider_connection_id,
                "model_id": assignment.model_id
            }, on_conflict="user_id, tier").execute()
            
    return await get_agent_defaults(principal, supabase)

async def reset_agent_defaults(
    principal: Principal,
    supabase: AsyncClient
) -> AgentDefaultsResponse:
    defaults = DEFAULT_DEFAULTS.copy()
    defaults["tenant_id"] = str(principal.tenant_id)
    defaults["user_id"] = str(principal.user_id)
    
    await supabase.table("agent_defaults").upsert(defaults, on_conflict="user_id").execute()
    await supabase.table("agent_model_assignments").delete().eq("user_id", str(principal.user_id)).execute()
    
    return await get_agent_defaults(principal, supabase)
