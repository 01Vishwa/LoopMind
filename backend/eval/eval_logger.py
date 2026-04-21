"""EvalLogger — the passive SSE-event sidecar.

Consumes the exact same event dicts that agent_controller.py already
yields as SSE.  Zero changes to agents or orchestrator required.

Usage (inside agent_controller.handle_agent_run)::

    eval_logger = EvalLogger(run_id=run_id, query=query)

    async for event in orchestrator.run(...):
        eval_logger.ingest(event)          # ← passive observation
        yield f"data: {json.dumps(event)}\\n\\n"

    await eval_logger.finalize()           # ← flush to Supabase

Mapping of SSE event-types to EvalStep captures:

    analysis_complete  → Analyzer  step
    plan_ready         → Planner   step  (captures initial plan length)
    code_ready         → Coder     step
    execution_result   → Executor  step  (error_type set on failure)
    debug_applied      → Debugger  step  (increments retry_count)
    verification_result→ Verifier  step
    plan_updated       → Router    step
    finalized          → Finalizer step
    metrics            → triggers finalize() automatically

All other event types (round_start, retrying, warning, etc.) are observed
but do not produce new steps — they update state on the *current* open step.
"""

import datetime
import logging
import uuid
from typing import Any, Dict, List, Optional

from eval.schemas import EvalRunMetrics, EvalStep
from eval.eval_engine import compute_run_metrics

logger = logging.getLogger("uvicorn.info")

# ---------------------------------------------------------------------------
# Agents that produce an EvalStep row
# ---------------------------------------------------------------------------

_STEP_EVENTS = {
    "analysis_complete": "Analyzer",
    "plan_ready":        "Planner",
    "code_ready":        "Coder",
    "execution_result":  "Executor",
    "debug_applied":     "Debugger",
    "verification_result": "Verifier",
    "plan_updated":      "Router",
    "finalized":         "Finalizer",
}


def _trunc(text: Any, limit: int = 512) -> str:
    """Truncates any value to a safely storable string."""
    s = str(text) if text is not None else ""
    return s[:limit]


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


# ---------------------------------------------------------------------------
# EvalLogger
# ---------------------------------------------------------------------------

class EvalLogger:
    """Stateful accumulator for one DS-STAR agent run.

    Thread-safety: single-threaded SSE generator — no locks needed.

    Attributes:
        run_id:   Matches the agent_runs PK.
        query:    Original user query (for query_length metric).
    """

    def __init__(self, run_id: str, query: str = "") -> None:
        self.run_id = run_id
        self.query = query
        self._steps: List[EvalStep] = []
        self._step_seq = 0
        self._current_round = 1

        # Retry tracking — counts retrying events before a step closes
        self._current_retry_count = 0

        # Debug depth tracking per round
        self._debug_depths: List[int] = []
        self._current_debug_depth = 0

        # Final plan size (captured from plan_updated or plan_ready)
        self._initial_plan_count = 0
        self._final_plan_count = 0

        # Run-level metadata captured from the "metrics" event
        self._run_meta: Dict[str, Any] = {}

        # Mode — overridden to "batch" only by external callers
        self.mode: str = "live"

        logger.debug("[EvalLogger] Initialized for run_id=%s", run_id)

    # -----------------------------------------------------------------------
    # Public: ingest one event
    # -----------------------------------------------------------------------

    def ingest(self, event: Dict[str, Any]) -> None:
        """Observes one SSE event emitted by the orchestrator.

        Builds EvalStep rows at deterministic boundaries and tracks
        state needed for loop-level metrics.

        Args:
            event: The raw event dict ``{event: str, payload: dict}``.
        """
        event_type: str = event.get("event", "")
        payload: Dict[str, Any] = event.get("payload", {})

        # ── Track current round ────────────────────────────────────────────
        if event_type == "round_start":
            self._current_round = payload.get("round", self._current_round)
            self._current_debug_depth = 0
            self._current_retry_count = 0
            return

        # ── Accumulate retries for the next step ───────────────────────────
        if event_type == "retrying":
            self._current_retry_count += 1
            return

        # ── Debug depth tracking ───────────────────────────────────────────
        if event_type == "debug_applied":
            self._current_debug_depth += 1

        # ── Finalise debug depth when we leave the debug sub-loop ─────────
        if event_type == "verification_result":
            self._debug_depths.append(self._current_debug_depth)
            self._current_debug_depth = 0

        # ── Capture plan sizes ─────────────────────────────────────────────
        if event_type == "plan_ready":
            self._initial_plan_count = len(payload.get("steps", []))
            self._final_plan_count = self._initial_plan_count

        if event_type == "plan_updated":
            self._final_plan_count = len(payload.get("steps", []))

        # ── Capture run-level metadata from metrics event ──────────────────
        if event_type == "metrics":
            self._run_meta = payload
            return  # no step row for the metrics event itself

        # ── Build EvalStep at each deterministic boundary ─────────────────
        agent_name = _STEP_EVENTS.get(event_type)
        if agent_name is None:
            return  # not a step-producing event

        step = self._build_step(agent_name, event_type, payload)
        self._steps.append(step)
        self._step_seq += 1

        # Reset retry counter after consuming it
        self._current_retry_count = 0

    # -----------------------------------------------------------------------
    # Public: flush to Supabase
    # -----------------------------------------------------------------------

    async def finalize(self) -> None:
        """Flushes accumulated steps and computed run metrics to Supabase.

        Called once, after the SSE stream ends (in the finally block of
        handle_agent_run).  Failures are logged as warnings — never raised.
        """
        if not self.run_id:
            return

        try:
            from eval.eval_store import upsert_steps, upsert_run_metrics  # pylint: disable=import-outside-toplevel

            # ── Persist step traces ────────────────────────────────────────
            await upsert_steps(self._steps)

            # ── Compute and persist aggregated run metrics ─────────────────
            run_metrics = compute_run_metrics(
                steps=self._steps,
                run_meta=self._run_meta,
                debug_depths=self._debug_depths,
                initial_plan_count=self._initial_plan_count,
                final_plan_count=self._final_plan_count,
                query_length=len(self.query),
                mode=self.mode,
            )
            await upsert_run_metrics(run_metrics)

            logger.info(
                "[EvalLogger] Flushed %d steps + metrics for run_id=%s",
                len(self._steps),
                self.run_id,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "[EvalLogger] Could not flush eval data for run_id=%s: %s",
                self.run_id,
                exc,
            )

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _build_step(
        self,
        agent_name: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> EvalStep:
        """Constructs an EvalStep from a payload dict.

        Each event type exposes slightly different payload keys — this
        method normalises them into the common EvalStep schema.
        """
        latency_ms = self._extract_latency(event_type, payload)
        error_type = self._extract_error(event_type, payload)
        input_summary = self._extract_input(event_type, payload)
        output_summary = self._extract_output(event_type, payload)
        validation_passed = self._extract_validation(event_type, payload)

        return EvalStep(
            step_id=uuid.uuid4().hex,
            run_id=self.run_id,
            step_seq=self._step_seq,
            round_num=self._current_round,
            agent_name=agent_name,
            input_summary=input_summary,
            output_summary=output_summary,
            latency_ms=latency_ms,
            retry_count=self._current_retry_count,
            error_type=error_type,
            validation_passed=validation_passed,
            timestamp_iso=_now_iso(),
        )

    @staticmethod
    def _extract_latency(event_type: str, payload: Dict[str, Any]) -> int:
        """Pulls the most specific latency key from the payload."""
        keys = {
            "code_ready":          "coder_ms",
            "execution_result":    "executor_ms",
            "verification_result": "verifier_ms",
            "plan_updated":        "router_ms",
            "debug_applied":       "debug_ms",
        }
        key = keys.get(event_type)
        if key:
            return int(payload.get(key, 0))
        return 0

    @staticmethod
    def _extract_error(event_type: str, payload: Dict[str, Any]) -> Optional[str]:
        """Returns an error classification string or None on success."""
        if event_type == "execution_result":
            if not payload.get("success", True):
                stderr: str = payload.get("stderr", "")
                # Classify by first token of error line
                for line in stderr.splitlines():
                    line = line.strip()
                    if line and ("Error" in line or "Exception" in line):
                        return line.split(":")[0].strip()[:80]
                return "ExecutionError"
        if event_type == "debug_applied":
            return payload.get("error_type") or None
        return None

    @staticmethod
    def _extract_input(event_type: str, payload: Dict[str, Any]) -> str:
        if event_type == "plan_ready":
            steps = payload.get("steps", [])
            return _trunc(f"{len(steps)} plan steps")
        if event_type == "code_ready":
            code = payload.get("code", "")
            return _trunc(f"round={payload.get('round',1)} prev_code={len(code)} chars")
        if event_type == "execution_result":
            return _trunc(f"round={payload.get('round',1)}")
        if event_type == "debug_applied":
            return _trunc(payload.get("error_type", ""))
        if event_type == "verification_result":
            return _trunc(payload.get("reason", ""))
        if event_type == "plan_updated":
            return _trunc(f"action={payload.get('action','')}")
        return ""

    @staticmethod
    def _extract_output(event_type: str, payload: Dict[str, Any]) -> str:
        if event_type == "analysis_complete":
            desc = payload.get("data_description", "")
            return _trunc(desc)
        if event_type == "plan_ready":
            steps = payload.get("steps", [])
            return _trunc(", ".join(
                s.get("description", "")[:60] for s in steps[:5]
            ))
        if event_type == "code_ready":
            return _trunc(payload.get("code", "")[:512])
        if event_type == "execution_result":
            stdout = payload.get("stdout", "")
            stderr = payload.get("stderr", "")
            return _trunc(stdout or stderr)
        if event_type == "debug_applied":
            return _trunc(payload.get("fix_summary", ""))
        if event_type == "verification_result":
            conf = payload.get("confidence", 0)
            suf = payload.get("is_sufficient", False)
            return _trunc(f"sufficient={suf} confidence={conf:.2f}")
        if event_type == "plan_updated":
            steps = payload.get("steps", [])
            return _trunc(f"{len(steps)} updated steps")
        if event_type == "finalized":
            return _trunc(payload.get("headline", "") or payload.get("formatted_output", ""))
        return ""

    @staticmethod
    def _extract_validation(event_type: str, payload: Dict[str, Any]) -> bool:
        if event_type == "execution_result":
            return bool(payload.get("success", True))
        if event_type == "verification_result":
            return bool(payload.get("is_sufficient", False))
        return True
