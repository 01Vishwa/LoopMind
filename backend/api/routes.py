"""API router — thin endpoint declarations.

Each route delegates immediately to its matching controller.
No business logic lives here.

Gap fixes applied:
- _session_contexts is now session-keyed (Dict[session_id, context]) to
  prevent multi-tenancy corruptions where two concurrent users overwrite each other.
- /process now merges files into an existing session context instead of overwriting.
- /upload now accepts a session_id query param so files are scoped per session.
- /clear now passes session_id to the file cache so only one session is wiped.
- /agent/run now receives the FastAPI Request object so handle_agent_run can detect
  client disconnection and stop the server-side loop (Gap 5 fix).

ARCH-02 fix:
- _session_contexts is bounded by TTL eviction (SESSION_TTL_SECONDS, default 3600 s)
  and a MAX_SESSIONS size cap (default 500). Both are env-configurable via config.py.
  Eviction runs lazily on every session write to avoid background threads.
- _set_session() is the single write path; it calls _evict_stale_sessions() first.

ARCH-03 fix:
- /agent/runs and /agent/runs/{run_id} now await the async Supabase service functions.
"""

import time as _time
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.controllers.agent_controller import handle_agent_run
from api.controllers.process_controller import handle_clear, handle_process
from api.controllers.upload_controller import handle_upload
from api.controllers.research_controller import handle_research_run
from eval.eval_routes import eval_router
from core.deep_research_orchestrator import is_open_ended
from core.config import SESSION_TTL_SECONDS, MAX_SESSIONS
from models.schemas import AgentRunRequest, UploadResponse

logger = logging.getLogger("uvicorn.error")

router = APIRouter()
router.include_router(eval_router, prefix="/eval")

# ---------------------------------------------------------------------------
# ARCH-02: Session context store with TTL eviction and size cap
# ---------------------------------------------------------------------------

# Primary store: session_id → context dict
_session_contexts: Dict[str, Dict[str, Any]] = {}
# Companion timestamps: session_id → monotonic time of last write
_session_timestamps: Dict[str, float] = {}

# Fallback anonymous session key for clients that don't send a session_id
_ANON_SESSION = "__anon__"


def _evict_stale_sessions() -> None:
    """Removes sessions older than SESSION_TTL_SECONDS and enforces MAX_SESSIONS cap.

    Called lazily on every session write. TTL eviction runs first, then the
    size cap so freshly-written sessions are never immediately evicted.
    """
    now = _time.monotonic()

    # TTL pass: remove entries that haven't been touched within the window
    stale = [
        k for k, ts in _session_timestamps.items()
        if now - ts > SESSION_TTL_SECONDS
    ]
    for k in stale:
        _session_contexts.pop(k, None)
        _session_timestamps.pop(k, None)
    if stale:
        logger.info("[Router] Evicted %d stale session(s) (TTL=%ds)", len(stale), SESSION_TTL_SECONDS)

    # Size cap: evict oldest entries when over MAX_SESSIONS
    while len(_session_contexts) >= MAX_SESSIONS:
        oldest_key = min(_session_timestamps, key=lambda k: _session_timestamps[k])
        _session_contexts.pop(oldest_key, None)
        _session_timestamps.pop(oldest_key, None)
        logger.warning(
            "[Router] Session cap (%d) reached — evicted oldest session: %s",
            MAX_SESSIONS, oldest_key,
        )


def _set_session(key: str, data: Dict[str, Any]) -> None:
    """Writes ``data`` into the session store with eviction and timestamp tracking.

    Args:
        key: Session identifier.
        data: Context dict to store.
    """
    _evict_stale_sessions()
    _session_contexts[key] = data
    _session_timestamps[key] = _time.monotonic()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ProcessRequest(BaseModel):
    """Request body for the /process endpoint."""

    files: List[str]
    session_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Upload / Process / Query
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Query(default=None),
) -> UploadResponse:
    """Validates and persists uploaded files into the session-scoped cache."""
    return await handle_upload(files, session_id=session_id or _ANON_SESSION)


@router.post("/process")
async def process_batch(request: ProcessRequest) -> Dict[str, Any]:
    """Processes cached files into normalised in-memory context.

    Merges results into the session's existing context rather than replacing
    it wholesale, so multiple /process calls accumulate files correctly.
    """
    session_key = request.session_id or _ANON_SESSION
    result = handle_process(request.files, session_id=session_key)

    existing = _session_contexts.get(session_key, {})
    new_details = result.get("details", {})

    # Deep merge: combine combined_extractions from old and new
    merged_extractions = {
        **existing.get("combined_extractions", {}),
        **new_details.get("combined_extractions", {}),
    }
    merged = {
        **new_details,
        "combined_extractions": merged_extractions,
        "files_processed": len(merged_extractions),
    }
    _set_session(session_key, merged)  # ARCH-02: write through eviction helper

    return result


# ---------------------------------------------------------------------------
# Agent run — SSE streaming
# ---------------------------------------------------------------------------

@router.post("/agent/run")
async def agent_run(
    request: AgentRunRequest,
    http_request: Request,
) -> StreamingResponse:
    """Streams DS-STAR or DS-STAR+ agent events as Server-Sent Events.

    Automatically routes open-ended queries to the DS-STAR+ deep research loop.
    ``http_request`` is passed to the controller so it can detect client
    disconnection and abort the server-side loop early (Gap 5).
    """
    session_key = request.session_id or _ANON_SESSION
    context = _session_contexts.get(session_key, {})

    if is_open_ended(request.query):
        logger.info("[Router] Open-ended query detected — dispatching to DS-STAR+")
        stream_handler = handle_research_run(
            query=request.query,
            context=context,
            session_id=session_key,
            max_rounds=request.max_rounds,
            model=request.model,
            coder_model=request.coder_model,
            temperature=request.temperature,
        )
    else:
        logger.info("[Router] Specific query detected — dispatching to regular DS-STAR")
        stream_handler = handle_agent_run(
            query=request.query,
            context=context,
            session_id=session_key,
            max_rounds=request.max_rounds,
            model=request.model,
            coder_model=request.coder_model,
            temperature=request.temperature,
            http_request=http_request,
        )

    return StreamingResponse(
        stream_handler,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# History endpoints
# ---------------------------------------------------------------------------

@router.get("/agent/runs")
async def list_runs(
    user_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Lists past agent runs from Supabase."""
    try:
        from services.supabase_service import list_agent_runs  # pylint: disable=import-outside-toplevel
        return await list_agent_runs(limit=limit)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/agent/runs/{run_id}")
async def get_run(run_id: str) -> Dict[str, Any]:
    """Retrieves a single agent run by its ID."""
    try:
        from services.supabase_service import get_agent_run  # pylint: disable=import-outside-toplevel
        run = await get_agent_run(run_id)
        if not run:
            raise HTTPException(
                status_code=404, detail=f"Run '{run_id}' not found."
            )
        return run
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

@router.delete("/clear")
async def clear_cache(session_id: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    """Wipes the internal session processing context and byte caches."""
    session_key = session_id or _ANON_SESSION
    _session_contexts.pop(session_key, None)
    _session_timestamps.pop(session_key, None)
    return handle_clear(session_id=session_key)
