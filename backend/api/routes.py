"""API router — thin endpoint declarations.

Each route delegates immediately to its matching controller.
No business logic lives here.

History endpoints (fix #5):
  GET /api/agent/runs        — list past runs for a user
  GET /api/agent/runs/{id}   — load a specific run
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.controllers.agent_controller import handle_agent_run
from api.controllers.process_controller import handle_clear, handle_process
from api.controllers.upload_controller import handle_upload
from models.schemas import AgentRunRequest, UploadResponse

router = APIRouter()

# Shared in-memory processing context (populated by /process, consumed by /query and /agent/run)
_processing_context: Dict[str, Any] = {}


class ProcessRequest(BaseModel):
    """Request body for the /process endpoint."""

    files: List[str]


# ---------------------------------------------------------------------------
# Upload / Process / Query (unchanged)
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(...)) -> UploadResponse:
    """Validates and persists uploaded files."""
    return await handle_upload(files)


@router.post("/process")
async def process_batch(request: ProcessRequest) -> Dict[str, Any]:
    """Processes cached files into normalised in-memory context."""
    global _processing_context  # pylint: disable=global-statement
    result = handle_process(request.files)
    _processing_context = result.get("details", {})
    return result




# ---------------------------------------------------------------------------
# Agent run — SSE streaming
# ---------------------------------------------------------------------------

@router.post("/agent/run")
async def agent_run(request: AgentRunRequest) -> StreamingResponse:
    """Streams DS-STAR agent events as Server-Sent Events."""
    return StreamingResponse(
        handle_agent_run(
            query=request.query,
            context=_processing_context,
            session_id=request.session_id or "",
            max_rounds=request.max_rounds,
            model=request.model,
            coder_model=request.coder_model,
            temperature=request.temperature,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# History endpoints (fix #5)
# ---------------------------------------------------------------------------

@router.get("/agent/runs")
async def list_runs(
    user_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Lists past agent runs from Supabase.

    Args:
        user_id: Optional filter by user identifier.
        limit: Maximum number of runs to return (1–100, default 20).

    Returns:
        List of run summary dicts ordered by created_at descending.
    """
    try:
        from services.supabase_service import list_agent_runs  # pylint: disable=import-outside-toplevel
        return list_agent_runs(limit=limit)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/agent/runs/{run_id}")
async def get_run(run_id: str) -> Dict[str, Any]:
    """Retrieves a single agent run by its ID.

    Args:
        run_id: Unique run identifier (UUID hex).

    Returns:
        Full run record dict.

    Raises:
        HTTPException 404: If no run with that ID is found.
    """
    try:
        from services.supabase_service import get_agent_run  # pylint: disable=import-outside-toplevel
        run = get_agent_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
        return run
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

@router.delete("/clear")
async def clear_cache() -> Dict[str, Any]:
    """Wipes the internal global processing and byte contexts."""
    global _processing_context  # pylint: disable=global-statement
    _processing_context.clear()
    return handle_clear()
