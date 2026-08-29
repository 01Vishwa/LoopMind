from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from supabase._async.client import AsyncClient
from typing import List

from ...dependencies.auth import get_current_user
from ...dependencies.db import get_supabase_client, get_db_session
from ...dependencies.auth import Principal
from ...schemas.workspace import (
    WorkspaceResponse,
    WorkspaceDetailResponse,
    CreateWorkspaceRequest,
    UpdateWorkspaceRequest
)
from ...services import workspace_service

router = APIRouter(tags=["Workspaces"])

@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    body: CreateWorkspaceRequest,
    principal: Principal = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Create a new workspace.
    """
    return await workspace_service.create_workspace(body, principal, session)

@router.get("/workspaces", response_model=List[WorkspaceResponse])
async def list_workspaces(
    principal: Principal = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    List user workspaces.
    """
    return await workspace_service.list_workspaces(principal, session)

@router.get("/workspaces/{workspace_id}", response_model=WorkspaceDetailResponse)
async def get_workspace(
    workspace_id: str,
    principal: Principal = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get a workspace by ID.
    """
    return await workspace_service.get_workspace(workspace_id, principal, session)

@router.put("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    body: UpdateWorkspaceRequest,
    principal: Principal = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Update a workspace.
    """
    return await workspace_service.update_workspace(workspace_id, body, principal, session)

@router.delete("/workspaces/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: str,
    principal: Principal = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase_client),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Delete a workspace, cascading to files.
    """
    await workspace_service.delete_workspace(workspace_id, principal, supabase, session)
