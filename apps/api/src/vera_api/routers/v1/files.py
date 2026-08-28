from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from supabase._async.client import AsyncClient
import uuid
from typing import List

from ...dependencies.auth import require_authenticated_user
from ...dependencies.db import get_supabase_client, get_db_session
from ...schemas.auth import Principal
from ...schemas.file import FileResponse
from ...services.upload_service import upload_file as upload_file_service
from vera_db.repositories.file_repository import FileRepository
from vera_db.repositories.description_repository import DescriptionRepository

router = APIRouter(tags=["Files"])

@router.post("/workspaces/{workspace_id}/files/upload", response_model=FileResponse, status_code=201)
async def upload_file(
    workspace_id: str,
    file: UploadFile = File(...),
    principal: Principal = Depends(require_authenticated_user),
    supabase: AsyncClient = Depends(get_supabase_client),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Upload a file to a workspace.
    """
    return await upload_file_service(workspace_id, file, principal, supabase, session)

@router.get("/workspaces/{workspace_id}/files", response_model=List[FileResponse])
async def list_files(
    workspace_id: str,
    principal: Principal = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    List files in a workspace.
    """
    file_repo = FileRepository(session=session)
    files = await file_repo.list_by_workspace(workspace_id=uuid.UUID(workspace_id), tenant_id=principal.tenant_id)
    
    # Needs has_description. We can fetch descriptions or use a joined query.
    # The current FileResponse requires has_description.
    desc_repo = DescriptionRepository(session=session)
    descriptions = await desc_repo.list_by_workspace(workspace_id=uuid.UUID(workspace_id), tenant_id=principal.tenant_id)
    described_file_ids = {desc.file_id for desc in descriptions}
    
    response = []
    for f in files:
        response.append(FileResponse(
            id=str(f.id),
            filename=f.filename,
            kind=f.kind,
            size_bytes=f.size_bytes,
            content_sha256=f.content_sha256,
            has_description=(f.id in described_file_ids),
            created_at=str(f.created_at)
        ))
    return response

@router.get("/files/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str,
    principal: Principal = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get a file by ID.
    """
    file_repo = FileRepository(session=session)
    f = await file_repo.get(file_id=uuid.UUID(file_id), tenant_id=principal.tenant_id)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
        
    desc_repo = DescriptionRepository(session=session)
    desc = await desc_repo.get_by_file(file_id=uuid.UUID(file_id), tenant_id=principal.tenant_id)
    
    return FileResponse(
        id=str(f.id),
        filename=f.filename,
        kind=f.kind,
        size_bytes=f.size_bytes,
        content_sha256=f.content_sha256,
        has_description=(desc is not None),
        created_at=str(f.created_at)
    )

@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    principal: Principal = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db_session),
    supabase: AsyncClient = Depends(get_supabase_client)
):
    """
    Get a signed URL for a file and redirect to it.
    """
    file_repo = FileRepository(session=session)
    f = await file_repo.get(file_id=uuid.UUID(file_id), tenant_id=principal.tenant_id)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
        
    storage = supabase.storage.from_("workspace-files")
    # Generate signed URL
    signed_url = await storage.create_signed_url(f.storage_path, expires_in=60)
    if "signedURL" not in signed_url:
        raise HTTPException(status_code=500, detail="Could not generate download link")
        
    return RedirectResponse(url=signed_url["signedURL"], status_code=302)

@router.delete("/files/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    principal: Principal = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db_session),
    supabase: AsyncClient = Depends(get_supabase_client)
):
    """
    Delete a file from DB and Storage.
    """
    file_repo = FileRepository(session=session)
    f = await file_repo.get(file_id=uuid.UUID(file_id), tenant_id=principal.tenant_id)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
        
    storage = supabase.storage.from_("workspace-files")
    try:
        await storage.remove([f.storage_path])
    except Exception as e:
        # Proceed to DB deletion even if storage deletion fails
        print(f"Error removing file from storage: {e}")
        
    await file_repo.delete(file_id=uuid.UUID(file_id), tenant_id=principal.tenant_id)
