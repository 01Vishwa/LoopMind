import asyncio
import logging
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict

from supabase._async.client import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from vera_db.repositories.file_repository import FileRepository
from vera_db.repositories.description_repository import DescriptionRepository
from vera_api.dependencies.auth import Principal
from vera_api.schemas.ingest import IngestStatusResponse

logger = logging.getLogger(__name__)

# --- In-memory progress tracking ---

@dataclass
class IngestionProgress:
    workspace_id: str
    total: int
    analyzed: int = 0
    failed: int = 0
    current_file: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def pending(self) -> int:
        return self.total - self.analyzed - self.failed

    @property
    def status(self) -> str:
        if self.pending > 0:
            return "running"
        return "complete"

_active_ingestions: Dict[str, IngestionProgress] = {}

# --- Analysis Mock (Replace with real Agent in the future) ---

async def analyze_file_mock(file_record, local_path: Path, tenant_id: uuid.UUID):
    """
    Mock analyzer. In reality, this would use LLMPort and SandboxPort to
    profile the file contents, extract schemas, and generate a summary.
    """
    await asyncio.sleep(2) # Simulate work
    
    # Generate mock description
    return {
        "summary_text": f"This is an automated description for {file_record.filename}.",
        "schema_fields": [{"name": "id", "dtype": "integer", "samples": ["1", "2"], "warning": None}],
        "row_count": 100,
        "sheet_names": None,
        "sample_rows": [{"id": 1}, {"id": 2}],
        "analyzer_script": "import pandas as pd\n\ndf = pd.read_csv('/data/file.csv')\nprint(df.head())",
        "analyzer_model": "mock-model-v1",
        "prompt_version": "v1",
        "embedding": None # Mock embedding
    }

# --- Service ---

async def trigger_ingestion(workspace_id: str, principal: Principal, session: AsyncSession) -> dict:
    if workspace_id in _active_ingestions and _active_ingestions[workspace_id].status == "running":
        return {"total": _active_ingestions[workspace_id].total, "pending": _active_ingestions[workspace_id].pending}
        
    file_repo = FileRepository(session=session)
    pending_files = await file_repo.list_without_description(
        workspace_id=uuid.UUID(workspace_id), 
        tenant_id=principal.tenant_id
    )
    
    if not pending_files:
        return {"total": 0, "pending": 0}
        
    progress = IngestionProgress(workspace_id=workspace_id, total=len(pending_files))
    _active_ingestions[workspace_id] = progress
    
    return {"total": progress.total, "pending": progress.pending}

async def run_ingestion(workspace_id: str, principal: Principal, supabase: AsyncClient, sessionmaker):
    """
    Background task that processes pending files.
    Requires a sessionmaker to spawn new sessions per file to avoid holding long transactions.
    """
    if workspace_id not in _active_ingestions:
        return
        
    progress = _active_ingestions[workspace_id]
    
    async with sessionmaker() as db_session:
        file_repo = FileRepository(session=db_session)
        pending_files = await file_repo.list_without_description(
            workspace_id=uuid.UUID(workspace_id), 
            tenant_id=principal.tenant_id
        )
        
    try:
        for file in pending_files:
            progress.current_file = file.filename
            
            # Using a new session for each file processing
            async with sessionmaker() as db_session:
                desc_repo = DescriptionRepository(session=db_session)
                
                try:
                    # Download from storage
                    storage = supabase.storage.from_("workspace-files")
                    file_bytes = await storage.download(file.storage_path)
                    
                    with tempfile.TemporaryDirectory() as tmpdir:
                        local_path = Path(tmpdir) / file.filename
                        local_path.write_bytes(file_bytes)
                        
                        # Run the Analyzer agent (Mocked for now)
                        desc_data = await analyze_file_mock(file, local_path, principal.tenant_id)
                        
                        # Store
                        await desc_repo.create(
                            file_id=file.id,
                            tenant_id=principal.tenant_id,
                            summary_text=desc_data["summary_text"],
                            schema_fields=desc_data["schema_fields"],
                            row_count=desc_data["row_count"],
                            sheet_names=desc_data["sheet_names"],
                            sample_rows=desc_data["sample_rows"],
                            analyzer_script=desc_data["analyzer_script"],
                            analyzer_model=desc_data["analyzer_model"],
                            prompt_version=desc_data["prompt_version"],
                            embedding=desc_data["embedding"],
                        )
                        
                    progress.analyzed += 1
                except Exception as e:
                    logger.error(f"Failed to analyze {file.filename}: {e}")
                    progress.failed += 1
                    
    finally:
        # Keep progress around for a short time for polling, then clean up
        await asyncio.sleep(60)
        _active_ingestions.pop(workspace_id, None)

def get_ingestion_status(workspace_id: str) -> IngestStatusResponse:
    if workspace_id in _active_ingestions:
        progress = _active_ingestions[workspace_id]
        return IngestStatusResponse(
            total=progress.total,
            analyzed=progress.analyzed,
            pending=progress.pending,
            failed=progress.failed,
            current_file=progress.current_file,
            status=progress.status
        )
    return IngestStatusResponse(
        total=0,
        analyzed=0,
        pending=0,
        failed=0,
        current_file=None,
        status="idle"
    )
