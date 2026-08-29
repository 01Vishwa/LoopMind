from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from supabase._async.client import AsyncClient
import uuid

from ...dependencies.auth import get_current_user
from ...dependencies.db import get_supabase_client, get_db_session
from ...dependencies.auth import Principal
from ...schemas.file import FileDescriptionResponse, SchemaFieldResponse
from vera_db.repositories.description_repository import DescriptionRepository

router = APIRouter(tags=["Descriptions"])

@router.get("/files/{file_id}/description", response_model=FileDescriptionResponse)
async def get_description(
    file_id: str,
    principal: Principal = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get a file's description.
    """
    desc_repo = DescriptionRepository(session=session)
    desc = await desc_repo.get_by_file(file_id=uuid.UUID(file_id), tenant_id=principal.tenant_id)
    
    if not desc:
        raise HTTPException(status_code=404, detail="Description not found")
        
    schema_fields = []
    if desc.schema_fields:
        schema_fields = [SchemaFieldResponse(**field) for field in desc.schema_fields]
        
    return FileDescriptionResponse(
        file_id=str(desc.file_id),
        summary_text=desc.summary_text,
        schema_fields=schema_fields,
        row_count=desc.row_count,
        sheet_names=desc.sheet_names,
        sample_rows=desc.sample_rows,
        analyzer_script=desc.analyzer_script,
        analyzer_model=desc.analyzer_model,
        prompt_version=desc.prompt_version,
        created_at=str(desc.created_at)
    )

@router.post("/files/{file_id}/reanalyze", status_code=202)
async def reanalyze_file(
    file_id: str,
    principal: Principal = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Delete the existing description and queue re-analysis (mock).
    """
    desc_repo = DescriptionRepository(session=session)
    await desc_repo.delete_by_file(file_id=uuid.UUID(file_id), tenant_id=principal.tenant_id)
    return {"status": "queued"}
