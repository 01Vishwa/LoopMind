"""Supabase service layer.

Encapsulates all interactions with Supabase Storage and the
``uploaded_files`` PostgreSQL table. Exposes a thin, typed API so that
controllers never import the supabase client directly.
"""

import datetime
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from core.config import SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, SUPABASE_BUCKET

logger = logging.getLogger("uvicorn.info")

# ---------------------------------------------------------------------------
# Singleton client
# ---------------------------------------------------------------------------

_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Returns a cached Supabase client, initialising it on first call.

    Returns:
        Client: Authenticated Supabase client instance.

    Raises:
        RuntimeError: If SUPABASE_URL or SUPABASE_PUBLISHABLE_KEY are missing.
    """
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY must be set in .env"
            )
        _client = create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)
        logger.info("Supabase client initialised (url=%s)", SUPABASE_URL)
    return _client


# ---------------------------------------------------------------------------
# Storage operations
# ---------------------------------------------------------------------------

def upload_to_storage(
    filename: str,
    content_bytes: bytes,
    extension: str,
) -> str:
    """Uploads raw file bytes to Supabase Storage.

    Files are stored under a UUID-prefixed path to avoid collisions.

    Args:
        filename (str): Original filename (used for Content-Type hint).
        content_bytes (bytes): Raw file content.
        extension (str): Lowercase file extension (csv | xlsx | json).

    Returns:
        str: Public URL of the uploaded object.

    Raises:
        RuntimeError: If the Supabase Storage upload fails.
    """
    client = get_supabase_client()

    mime_map = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
    }

    storage_path = f"{uuid.uuid4().hex}/{filename}"

    response = client.storage.from_(SUPABASE_BUCKET).upload(
        path=storage_path,
        file=content_bytes,
        file_options={"content-type": mime_map.get(extension, "application/octet-stream")},
    )

    if hasattr(response, "error") and response.error:
        raise RuntimeError(f"Storage upload failed: {response.error}")

    # Build public URL
    public_url = (
        client.storage.from_(SUPABASE_BUCKET).get_public_url(storage_path)
    )

    logger.info(
        "Uploaded to Supabase Storage — path=%s, url=%s", storage_path, public_url
    )
    return public_url, storage_path


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

def insert_file_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Inserts a file metadata row into the ``uploaded_files`` table.

    Args:
        record (Dict[str, Any]): Row data matching the table schema.

    Returns:
        Dict[str, Any]: The inserted row returned by Supabase.

    Raises:
        RuntimeError: If the insert fails.
    """
    client = get_supabase_client()

    response = (
        client.table("uploaded_files")
        .insert(record)
        .execute()
    )

    if not response.data:
        raise RuntimeError(f"DB insert failed for record: {record}")

    logger.info("Inserted file record — id=%s", response.data[0].get("id"))
    return response.data[0]


def list_uploaded_files() -> List[Dict[str, Any]]:
    """Fetches all rows from the ``uploaded_files`` table.

    Returns:
        List[Dict[str, Any]]: List of dataset metadata rows.
    """
    client = get_supabase_client()

    response = (
        client.table("uploaded_files")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    return response.data or []


# ---------------------------------------------------------------------------
# Agent run operations  (DS-STAR)
# ---------------------------------------------------------------------------

def create_agent_run(
    run_id: str,
    query: str,
    file_names: List[str],
    session_id: str = "",
) -> Dict[str, Any]:
    """Creates a new row in the ``agent_runs`` table with status=running.

    Args:
        run_id (str): Unique identifier for this agent run.
        query (str): The user query that triggered the run.
        file_names (List[str]): Names of files in the processing context.
        session_id (str): Optional client session identifier.

    Returns:
        Dict[str, Any]: The inserted row.

    Raises:
        RuntimeError: If the DB insert fails.
    """
    client = get_supabase_client()

    record = {
        "id": run_id,
        "session_id": session_id or None,
        "query": query,
        "file_names": file_names,
        "status": "running",
        "plan_steps": [],
        "execution_logs": [],
    }

    try:
        response = client.table("agent_runs").insert(record).execute()
        if not response.data:
            raise RuntimeError(f"Failed to create agent_run record: {run_id}")
        logger.info("Created agent_run — id=%s", run_id)
        return response.data[0]
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Could not create agent_run (schema missing?): %s", exc)
        return record


def update_agent_run(
    run_id: str,
    plan_steps: List[Dict[str, Any]],
    final_code: str,
    rounds: int,
    insights: Dict[str, Any],
    execution_logs: List[str],
    status: str = "completed",
) -> Dict[str, Any]:
    """Updates an existing agent_run row with the final result.

    Args:
        run_id (str): Unique run identifier.
        plan_steps (List[Dict[str, Any]]): Final plan step list.
        final_code (str): The generated Python script.
        rounds (int): Number of rounds completed.
        insights (Dict[str, Any]): Final insights dict.
        execution_logs (List[str]): Log entries from each round.
        status (str): Terminal status — "completed" or "failed".

    Returns:
        Dict[str, Any]: The updated row.
    """
    client = get_supabase_client()

    updates = {
        "plan_steps": plan_steps,
        "final_code": final_code,
        "rounds": rounds,
        "insights": insights,
        "execution_logs": execution_logs,
        "status": status,
        "completed_at": datetime.datetime.utcnow().isoformat(),
    }

    try:
        response = (
            client.table("agent_runs")
            .update(updates)
            .eq("id", run_id)
            .execute()
        )
        logger.info("Updated agent_run — id=%s, status=%s", run_id, status)
        return response.data[0] if response.data else {}
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Could not update agent_run (schema missing?): %s", exc)
        return {}


def get_agent_run(run_id: str) -> Dict[str, Any]:
    """Fetches a single agent_run row by its ID.

    Args:
        run_id (str): Unique run identifier.

    Returns:
        Dict[str, Any]: The run row, or an empty dict if not found.
    """
    client = get_supabase_client()

    try:
        response = (
            client.table("agent_runs")
            .select("*")
            .eq("id", run_id)
            .maybe_single()
            .execute()
        )
        return response.data or {}
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Could not get agent_run (schema missing?): %s", exc)
        return {}


def list_agent_runs(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetches the most recent agent_run rows.

    Args:
        limit (int): Maximum number of rows to return.

    Returns:
        List[Dict[str, Any]]: Agent run rows ordered newest first.
    """
    client = get_supabase_client()

    try:
        response = (
            client.table("agent_runs")
            .select("id, query, file_names, rounds, status, created_at, completed_at, eval_metrics")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Could not list agent_runs (schema missing?): %s", exc)
        return []


def update_agent_run_metrics(
    run_id: str,
    metrics: Dict[str, Any],
    total_run_ms: int,
    complexity: str,
) -> Dict[str, Any]:
    """Persists evaluation metrics onto an existing agent_run row.

    Stores the RunMetrics summary (per-round timing, complexity tag, convergence
    data) into the ``eval_metrics`` jsonb column.  Gracefully no-ops if the
    column is not yet present in the Supabase schema.

    Args:
        run_id (str): Unique run identifier matching an existing agent_runs row.
        metrics (Dict[str, Any]): RunMetrics.summary() output.
        total_run_ms (int): Total wall-clock duration of the run in milliseconds.
        complexity (str): Task complexity tag — ``"easy"`` or ``"hard"``.

    Returns:
        Dict[str, Any]: The updated row, or empty dict on failure.
    """
    client = get_supabase_client()

    updates = {
        "eval_metrics": {
            **metrics,
            "total_run_ms": total_run_ms,
            "complexity": complexity,
        }
    }

    try:
        response = (
            client.table("agent_runs")
            .update(updates)
            .eq("id", run_id)
            .execute()
        )
        logger.info(
            "Persisted eval_metrics for run_id=%s — complexity=%s, total_ms=%d",
            run_id,
            complexity,
            total_run_ms,
        )
        return response.data[0] if response.data else {}
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(
            "Could not persist eval_metrics for run_id=%s (column may not exist yet): %s",
            run_id,
            exc,
        )
        return {}


# ---------------------------------------------------------------------------
# Deep Research (DS-STAR+) tracking
# ---------------------------------------------------------------------------

def create_report_run(
    report_id: str,
    query: str,
    file_names: List[str],
    session_id: str = "",
) -> Dict[str, Any]:
    """Creates a new tracking row in the reports table.

    Args:
        report_id: Unique identifier for the research run.
        query: Full natural language query.
        file_names: List of files included in the context.
        session_id: Optional client session ID.

    Returns:
        The inserted row as a dictionary.
    """
    client = get_supabase_client()
    record = {
        "id": report_id,
        "query": query,
        "session_id": session_id or None,
        "file_names": file_names,
        "status": "running",
        "key_findings": [],
        "caveats": [],
        "sub_questions": [],
        "sub_run_ids": [],
    }

    try:
        response = client.table("reports").insert(record).execute()
        logger.info("[Supabase] Created research report: %s", report_id)
        return response.data[0] if response.data else record
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[Supabase] Could not create report %s: %s", report_id, exc)
        return record


def create_subquestions(
    report_id: str,
    sub_questions: List[str],
) -> None:
    """Inserts a batch of sub_questions associated with a report.

    Args:
        report_id: The parent report ID.
        sub_questions: Ordered list of sub-questions to track.
    """
    client = get_supabase_client()

    # Update parent report to track the sub-questions array
    try:
        client.table("reports").update({
            "sub_questions": sub_questions,
            "sub_run_ids": [None] * len(sub_questions)
        }).eq("id", report_id).execute()
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[Supabase] Could not update report array: %s", exc)

    # Insert individual sub-question tracker rows
    records = [
        {
            "id": f"{report_id}-q{i}",
            "report_id": report_id,
            "question": sq,
            "question_index": i,
            "status": "pending"
        }
        for i, sq in enumerate(sub_questions)
    ]

    try:
        client.table("sub_questions").insert(records).execute()
        logger.info("[Supabase] Inserted %d sub-questions for %s", len(records), report_id)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[Supabase] Could not create sub-questions: %s", exc)


def link_subquestion_run(
    report_id: str,
    question_index: int,
    status: str,
    result_run_id: str,
) -> None:
    """Updates a sub-question with its final execution status and linked agent_run ID.

    Args:
        report_id: Parent report ID.
        question_index: The zero-based index of the sub-question.
        status: The final status (e.g. 'completed' or 'failed').
        result_run_id: The run ID of the DS-STAR execution that answered this question.
    """
    client = get_supabase_client()
    sq_id = f"{report_id}-q{question_index}"

    try:
        client.table("sub_questions").update({
            "status": status,
            "result_run_id": result_run_id,
            "completed_at": datetime.datetime.utcnow().isoformat()
        }).eq("id", sq_id).execute()
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[Supabase] Could not link sub-question %s: %s", sq_id, exc)


def update_report_status(
    report_id: str,
    status: str,
    title: str = "",
    executive_summary: str = "",
    report_body: str = "",
    key_findings: Optional[List[str]] = None,
    caveats: Optional[List[str]] = None,
    total_ms: int = 0,
) -> None:
    """Marks a research report as finished and populates the synthesized final output.

    Args:
        report_id: Unique research run identifier.
        status: 'completed' or 'failed'.
        title: Synthesized title.
        executive_summary: High-level summary of findings.
        report_body: Full markdown document body.
        key_findings: Discovered insights.
        caveats: Any warnings or errors encountered during the sub-runs.
        total_ms: Wall-clock duration of the entire DeepResearch workflow.
    """
    client = get_supabase_client()
    updates = {
        "status": status,
        "title": title or None,
        "executive_summary": executive_summary or None,
        "report_body": report_body or None,
        "key_findings": key_findings or [],
        "caveats": caveats or [],
        "total_ms": total_ms,
        "completed_at": datetime.datetime.utcnow().isoformat()
    }

    try:
        client.table("reports").update(updates).eq("id", report_id).execute()
        logger.info("[Supabase] Finalised report %s with status=%s", report_id, status)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[Supabase] Could not finalise report %s: %s", report_id, exc)
