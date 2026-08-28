from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from supabase._async.client import AsyncClient
import uuid

from vera_db.repositories.workspace_repository import WorkspaceRepository
from vera_db.repositories.file_repository import FileRepository
from vera_api.schemas.auth import Principal
from vera_api.schemas.workspace import (
    WorkspaceResponse,
    WorkspaceDetailResponse,
    CreateWorkspaceRequest,
    UpdateWorkspaceRequest
)
from vera_api.schemas.file import FileResponse

# --- Helpers ---

def map_workspace_response(workspace_record, file_count: int = 0, described_count: int = 0) -> WorkspaceResponse:
    if file_count == 0:
        status = "empty"
    elif file_count == described_count:
        status = "ready"
    else:
        status = "partial"
        
    return WorkspaceResponse(
        id=str(workspace_record.id),
        name=workspace_record.name,
        description=workspace_record.description,
        file_count=file_count,
        described_count=described_count,
        status=status,
        created_at=str(workspace_record.created_at),
        updated_at=str(workspace_record.updated_at)
    )

# --- Service ---

async def create_workspace(
    body: CreateWorkspaceRequest,
    principal: Principal,
    session: AsyncSession
) -> WorkspaceResponse:
    repo = WorkspaceRepository(session=session)
    w = await repo.create(
        id=uuid.uuid7() if hasattr(uuid, 'uuid7') else uuid.uuid4(),
        tenant_id=principal.tenant_id,
        created_by=principal.user_id,
        name=body.name,
        description=body.description
    )
    return map_workspace_response(w, 0, 0)

async def list_workspaces(
    principal: Principal,
    session: AsyncSession
) -> list[WorkspaceResponse]:
    repo = WorkspaceRepository(session=session)
    workspaces = await repo.list_for_tenant(tenant_id=principal.tenant_id)
    
    # In a real scenario, you'd fetch counts efficiently for all.
    # We use get_with_counts in a loop here for simplicity of implementation.
    res = []
    for w in workspaces:
        counts = await repo.get_with_counts(workspace_id=w.id, tenant_id=principal.tenant_id)
        if counts:
            res.append(map_workspace_response(counts["workspace"], counts["file_count"], counts["described_count"]))
    return res

async def get_workspace(
    workspace_id: str,
    principal: Principal,
    session: AsyncSession
) -> WorkspaceDetailResponse:
    repo = WorkspaceRepository(session=session)
    counts = await repo.get_with_counts(workspace_id=uuid.UUID(workspace_id), tenant_id=principal.tenant_id)
    if not counts:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    w_res = map_workspace_response(counts["workspace"], counts["file_count"], counts["described_count"])
    
    file_repo = FileRepository(session=session)
    files = await file_repo.list_by_workspace(workspace_id=uuid.UUID(workspace_id), tenant_id=principal.tenant_id)
    
    from vera_db.repositories.description_repository import DescriptionRepository
    desc_repo = DescriptionRepository(session=session)
    descriptions = await desc_repo.list_by_workspace(workspace_id=uuid.UUID(workspace_id), tenant_id=principal.tenant_id)
    described_file_ids = {desc.file_id for desc in descriptions}
    
    file_responses = []
    for f in files:
        file_responses.append(FileResponse(
            id=str(f.id),
            filename=f.filename,
            kind=f.kind,
            size_bytes=f.size_bytes,
            content_sha256=f.content_sha256,
            has_description=(f.id in described_file_ids),
            created_at=str(f.created_at)
        ))
        
    return WorkspaceDetailResponse(
        **w_res.model_dump(),
        files=file_responses
    )

async def update_workspace(
    workspace_id: str,
    body: UpdateWorkspaceRequest,
    principal: Principal,
    session: AsyncSession
) -> WorkspaceResponse:
    repo = WorkspaceRepository(session=session)
    w = await repo.update(
        workspace_id=uuid.UUID(workspace_id),
        tenant_id=principal.tenant_id,
        name=body.name,
        description=body.description
    )
    if not w:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    counts = await repo.get_with_counts(workspace_id=uuid.UUID(workspace_id), tenant_id=principal.tenant_id)
    return map_workspace_response(counts["workspace"], counts["file_count"], counts["described_count"])

async def delete_workspace(
    workspace_id: str,
    principal: Principal,
    supabase: AsyncClient,
    session: AsyncSession
):
    # Cascade delete logic
    file_repo = FileRepository(session=session)
    files = await file_repo.list_by_workspace(workspace_id=uuid.UUID(workspace_id), tenant_id=principal.tenant_id)
    
    if files:
        storage = supabase.storage.from_("workspace-files")
        paths = [f.storage_path for f in files]
        try:
            await storage.remove(paths)
        except Exception as e:
            # Log error, but proceed with DB deletion
            print(f"Failed to delete some files from storage: {e}")
            
    workspace_repo = WorkspaceRepository(session=session)
    await workspace_repo.delete(workspace_id=uuid.UUID(workspace_id), tenant_id=principal.tenant_id)
