from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from supabase._async.client import AsyncClient
import uuid

from ...dependencies.auth import get_current_user
from ...dependencies.db import get_supabase_client, get_db_session, _get_sessionmaker
from ...dependencies.auth import Principal
from ...schemas.ingest import IngestResponse, IngestStatusResponse
from ...services import ingest_service

router = APIRouter(tags=["Ingestion"])

@router.post("/workspaces/{workspace_id}/ingest", response_model=IngestResponse, status_code=202)
async def trigger_ingestion(
    workspace_id: str,
    background_tasks: BackgroundTasks,
    principal: Principal = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase_client),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Trigger async analysis of pending files in the workspace.
    """
    res = await ingest_service.trigger_ingestion(workspace_id, principal, session)
    
    if res["pending"] > 0:
        # Pass a sessionmaker instead of an active session to the background task
        sm = _get_sessionmaker()
        background_tasks.add_task(
            ingest_service.run_ingestion,
            workspace_id,
            principal,
            supabase,
            sm
        )
        
    return IngestResponse(total=res["total"], pending=res["pending"])

@router.get("/workspaces/{workspace_id}/ingest/status", response_model=IngestStatusResponse)
async def get_ingestion_status(
    workspace_id: str,
    principal: Principal = Depends(get_current_user)
):
    """
    Get the current ingestion progress for a workspace.
    """
    return ingest_service.get_ingestion_status(workspace_id)
