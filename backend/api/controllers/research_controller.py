"""Research API controller — DS-STAR+ deep research endpoint handler.

Handles streaming responses for the /api/research endpoint.
Delegates to DeepResearchOrchestrator and serialises each AgentEvent as SSE.

Also persists:
- A new ``reports`` row before the loop starts.
- ``sub_questions`` rows for each generated sub-question.
- Final report content when research_complete is emitted.
- Status update to ``failed`` if an error event terminates the stream.
"""

import json
import logging
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from core.deep_research_orchestrator import DeepResearchOrchestrator

logger = logging.getLogger("uvicorn.info")


async def handle_research_run(
    query: str,
    context: Dict[str, Any],
    session_id: str = "",
    max_rounds: Optional[int] = None,
    model: Optional[str] = None,
    coder_model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_workers: Optional[int] = None,
) -> AsyncGenerator[str, None]:
    """Streams DS-STAR+ research events as Server-Sent Events.

    Args:
        query: The user's open-ended research query.
        context: Processing context from /process endpoint.
        session_id: Optional client-provided session identifier.
        max_rounds: Override for MAX_AGENT_ROUNDS per sub-question.
        model: Override for the reasoning LLM model.
        coder_model: Override for the code-generation LLM model.
        temperature: Override for the LLM sampling temperature (0.0–1.0).
        max_workers: Override for max parallel DS-STAR sub-runs.

    Yields:
        SSE-formatted ``data: <json>\\n\\n`` lines.
    """
    report_id = uuid.uuid4().hex

    orchestrator = DeepResearchOrchestrator(
        max_rounds=max_rounds,
        model=model,
        coder_model=coder_model,
        temperature=temperature,
        max_workers=max_workers,
    )

    # Persist report row before streaming starts
    _try_create_report(report_id, session_id, query, context)

    # Emit report_id to frontend immediately
    yield f"data: {json.dumps({'event': 'report_started', 'payload': {'report_id': report_id}})}\n\n"

    sub_questions_created = False

    try:
        async for event in orchestrator.run(query, context, report_id=report_id):
            payload = json.dumps(event, default=str)
            yield f"data: {payload}\n\n"

            event_type = event.get("event")
            event_payload = event.get("payload", {})

            # Create sub_question rows the moment they are generated
            if event_type == "subquestions_ready" and not sub_questions_created:
                sub_questions = event_payload.get("sub_questions", [])
                _try_create_subquestions(report_id, sub_questions)
                sub_questions_created = True

            # Update sub_question rows as each completes
            elif event_type == "subquestion_complete":
                _try_update_subquestion(
                    report_id=report_id,
                    index=event_payload.get("index", 0),
                    status=event_payload.get("status", "completed"),
                    result_run_id=event_payload.get("sub_run_id", ""),
                )

            # Persist final report content
            elif event_type == "research_complete":
                _try_update_report(
                    report_id=report_id,
                    event_payload=event_payload,
                    status="completed",
                )

            # Mark report as failed on terminal error
            elif event_type == "error":
                _try_fail_report(report_id)

    except Exception as exc:  # pylint: disable=broad-except
        error_event = json.dumps({
            "event": "error",
            "payload": {"message": str(exc)},
        })
        yield f"data: {error_event}\n\n"
        _try_fail_report(report_id)
        logger.error(
            "[ResearchController] Stream error for report_id=%s: %s",
            report_id,
            exc,
        )

    finally:
        yield "data: {\"event\": \"stream_end\", \"payload\": {}}\n\n"


# ---------------------------------------------------------------------------
# Supabase persistence helpers (all non-blocking, warn on failure)
# ---------------------------------------------------------------------------

def _try_create_report(
    report_id: str,
    session_id: str,
    query: str,
    context: Dict[str, Any],
) -> None:
    """Creates a new reports row with status=running.

    Args:
        report_id: Unique report identifier.
        session_id: Client session identifier.
        query: Original research query.
        context: Processing context (used to extract file names).
    """
    try:
        from services.supabase_service import create_report_run  # pylint: disable=import-outside-toplevel
        file_names = list(context.get("combined_extractions", {}).keys())
        create_report_run(
            report_id=report_id,
            query=query,
            file_names=file_names,
            session_id=session_id,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(
            "[ResearchController] Could not persist report start: %s", exc
        )


def _try_create_subquestions(
    report_id: str,
    sub_questions: List[str],
) -> None:
    """Creates sub_questions rows for each generated question.

    Args:
        report_id: Parent report identifier.
        sub_questions: Ordered list of atomic sub-question strings.
    """
    try:
        from services.supabase_service import create_subquestions  # pylint: disable=import-outside-toplevel
        create_subquestions(report_id=report_id, sub_questions=sub_questions)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(
            "[ResearchController] Could not persist sub_questions: %s", exc
        )


def _try_update_subquestion(
    report_id: str,
    index: int,
    status: str,
    result_run_id: str,
) -> None:
    """Updates a single sub_question row with its DS-STAR result.

    Args:
        report_id: Parent report identifier.
        index: Zero-based position of this sub-question.
        status: Final status string from the DS-STAR run.
        result_run_id: The agent_run ID for this sub-question run.
    """
    try:
        from services.supabase_service import link_subquestion_run  # pylint: disable=import-outside-toplevel
        link_subquestion_run(
            report_id=report_id,
            question_index=index,
            status=status,
            result_run_id=result_run_id,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(
            "[ResearchController] Could not update sub_question idx=%d: %s",
            index,
            exc,
        )


def _try_update_report(
    report_id: str,
    event_payload: Dict[str, Any],
    status: str = "completed",
) -> None:
    """Persists the final report content to the reports table.

    Args:
        report_id: Unique report identifier.
        event_payload: The ``research_complete`` SSE event payload dict.
        status: Terminal status (``"completed"`` or ``"failed"``).
    """
    try:
        from services.supabase_service import update_report_status  # pylint: disable=import-outside-toplevel
        update_report_status(
            report_id=report_id,
            status=status,
            title=event_payload.get("title", ""),
            executive_summary=event_payload.get("executive_summary", ""),
            report_body=event_payload.get("report_body", ""),
            key_findings=event_payload.get("key_findings", []),
            caveats=event_payload.get("caveats", []),
            total_ms=event_payload.get("total_ms", 0),
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(
            "[ResearchController] Could not persist report result: %s", exc
        )


def _try_fail_report(report_id: str) -> None:
    """Marks a report as failed in Supabase.

    Args:
        report_id: Unique report identifier.
    """
    try:
        from services.supabase_service import update_report_status  # pylint: disable=import-outside-toplevel
        update_report_status(report_id=report_id, status="failed")
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(
            "[ResearchController] Could not mark report as failed: %s", exc
        )
