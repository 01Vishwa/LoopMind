"""API router — thin endpoint declarations.

Each route delegates immediately to its matching controller.
No business logic lives here.
"""

from typing import List, Dict, Any

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from models.schemas import UploadResponse, QueryRequest, QueryResponse
from api.controllers.upload_controller import handle_upload
from api.controllers.process_controller import handle_process, handle_clear
from api.controllers.query_controller import handle_query

router = APIRouter()

# Shared in-memory processing context (populated by /process, consumed by /query)
_processing_context: Dict[str, Any] = {}


class ProcessRequest(BaseModel):
    """Request body for the /process endpoint."""

    files: List[str]


@router.post("/upload", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(...)) -> UploadResponse:
    """Validates and persists uploaded files."""
    return await handle_upload(files)


@router.post("/process")
async def process_batch(request: ProcessRequest) -> Dict[str, Any]:
    """Processes cached files into normalised in-memory context."""
    global _processing_context
    result = handle_process(request.files)
    _processing_context = result.get("details", {})
    return result


@router.post("/query", response_model=QueryResponse)
async def query_context(request: QueryRequest) -> QueryResponse:
    """Executes a natural language query against the processing context."""
    return handle_query(request.query, _processing_context)


@router.delete("/clear")
async def clear_cache() -> Dict[str, Any]:
    """Wipes the internal global processing and byte contexts."""
    global _processing_context
    _processing_context.clear()
    return handle_clear()
