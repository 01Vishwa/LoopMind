"""Agent SSE controller.

Handles streaming responses for the /api/agent/run endpoint. Delegates
to the DsStarOrchestrator and serialises each AgentEvent as an SSE JSON line.
Also persists run metadata to Supabase before and after the loop, including:
- Marking the run as "failed" when the orchestrator emits a terminal error event.
- Persisting evaluation metrics (complexity, per-round timing) when the
  "metrics" event is emitted by the orchestrator.
"""

import json
import logging
import uuid
from typing import Any, AsyncGenerator, Dict, Optional

from core.ds_star_orchestrator import DsStarOrchestrator

logger = logging.getLogger("uvicorn.info")


async def handle_agent_run(
    query: str,
    context: Dict[str, Any],
    session_id: str = "",
    max_rounds: Optional[int] = None,
    model: Optional[str] = None,
    coder_model: Optional[str] = None,
    temperature: Optional[float] = None,
) -> AsyncGenerator[str, None]:
    """Streams DS-STAR agent events as Server-Sent Events.

    Args:
        query: The user's natural language query.
        context: The processing context from /process.
        session_id: Optional client-provided session identifier.
        max_rounds: Override for MAX_AGENT_ROUNDS (1–10).
        model: Override for the reasoning LLM model.
        coder_model: Override for the code-generation LLM model.
        temperature: Override for the LLM sampling temperature (0.0–1.0).

    Yields:
        SSE-formatted ``data: <json>\\n\\n`` lines.
    """
    run_id = session_id or uuid.uuid4().hex
    orchestrator = DsStarOrchestrator(
        max_rounds=max_rounds,
        model=model,
        coder_model=coder_model,
        temperature=temperature,
    )

    _try_create_run(run_id, query, context)

    try:
        async for event in orchestrator.run(query, context):
            payload = json.dumps(event, default=str)
            yield f"data: {payload}\n\n"

            event_type = event.get("event")

            # Persist final completed result
            if event_type == "completed":
                _try_update_run(run_id, event.get("payload", {}), status="completed")

            # Persist failure state so history UI shows correct badge
            elif event_type == "error":
                _try_update_run(
                    run_id,
                    event.get("payload", {}),
                    status="failed",
                )

            # Persist evaluation metrics emitted by the orchestrator
            elif event_type == "metrics":
                metrics_payload = event.get("payload", {})
                _try_persist_metrics(run_id, metrics_payload)

    except Exception as exc:  # pylint: disable=broad-except
        error_event = json.dumps({
            "event": "error",
            "payload": {"message": str(exc)},
        })
        yield f"data: {error_event}\n\n"
        _try_update_run(run_id, {"message": str(exc)}, status="failed")
        logger.error("[AgentController] Stream error for run_id=%s: %s", run_id, exc)

    finally:
        yield "data: {\"event\": \"stream_end\", \"payload\": {}}\n\n"


def _try_create_run(run_id: str, query: str, context: Dict[str, Any]) -> None:
    """Attempts to create an agent_runs row in Supabase.

    Args:
        run_id: Unique run identifier.
        query: User query.
        context: Processing context.
    """
    try:
        from services.supabase_service import create_agent_run  # pylint: disable=import-outside-toplevel
        file_names = list(context.get("combined_extractions", {}).keys())
        create_agent_run(run_id=run_id, query=query, file_names=file_names)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[AgentController] Could not persist run start: %s", exc)


def _try_update_run(
    run_id: str,
    payload: Dict[str, Any],
    status: str = "completed",
) -> None:
    """Attempts to update the agent_runs row with the final result.

    Args:
        run_id: Unique run identifier.
        payload: Completed or error event payload.
        status: Final run status — ``"completed"`` or ``"failed"``.
    """
    try:
        from services.supabase_service import update_agent_run  # pylint: disable=import-outside-toplevel
        update_agent_run(
            run_id=run_id,
            plan_steps=payload.get("plan_steps", []),
            final_code=payload.get("code", {}).get("Python", ""),
            rounds=payload.get("rounds", 0),
            insights=payload.get("insights", {}),
            execution_logs=payload.get("execution_logs", []),
            status=status,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[AgentController] Could not persist run result: %s", exc)


def _try_persist_metrics(run_id: str, metrics_payload: Dict[str, Any]) -> None:
    """Attempts to persist run evaluation metrics to Supabase.

    Stores the RunMetrics summary (complexity, round timing breakdown, etc.)
    into the ``agent_run_metrics`` jsonb column of the agent_runs table.

    Args:
        run_id: Unique run identifier.
        metrics_payload: The ``payload`` dict from the ``metrics`` SSE event,
            containing ``metrics`` (RunMetrics.summary()), ``total_run_ms``,
            and ``complexity``.
    """
    try:
        from services.supabase_service import update_agent_run_metrics  # pylint: disable=import-outside-toplevel
        update_agent_run_metrics(
            run_id=run_id,
            metrics=metrics_payload.get("metrics", {}),
            total_run_ms=metrics_payload.get("total_run_ms", 0),
            complexity=metrics_payload.get("complexity", "easy"),
        )
        logger.info(
            "[AgentController] Metrics persisted for run_id=%s, complexity=%s, total_ms=%d",
            run_id,
            metrics_payload.get("complexity", "easy"),
            metrics_payload.get("total_run_ms", 0),
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[AgentController] Could not persist run metrics: %s", exc)
