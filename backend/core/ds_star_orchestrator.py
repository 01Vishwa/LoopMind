"""DsStarOrchestrator — the main DS-STAR agent loop controller.

Implements the full Plan → Code → Execute → Verify → Route iterative cycle.
Yields AgentEvent objects at each stage for SSE streaming to the frontend.

Changes vs. original:
- All LLM agent calls are now ``await``-ed (async NIM chains).
- Per-agent tenacity retry with exponential back-off.
- ``retrying`` SSE event emitted before each retry attempt.
- On final agent failure: terminal ``error`` SSE event + Supabase status → "failed".
- Artifact SSE event emitted for every file written to outputs/.
- Per-round timing metrics collected via RoundTimingCollector and emitted
  as a ``metrics`` SSE event on completion (mirrors DABStep ablation tables).
"""

import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import tenacity

from core.analyzer.file_analyzer import FileAnalyzerAgent
from core.coder.coder_agent import CoderAgent
from core.executor.code_executor import CodeExecutor, ExecutionResult
from core.planner.planner_agent import PlannerAgent
from core.router.router_agent import RouterAgent
from core.verifier.verifier_agent import VerifierAgent
from core.config import MAX_AGENT_ROUNDS
from models.metrics_schema import RoundMetric, RoundTimingCollector, RunMetrics

logger = logging.getLogger("uvicorn.info")


# ---------------------------------------------------------------------------
# SSE event helper
# ---------------------------------------------------------------------------

def _event(event_type: str, **payload: Any) -> Dict[str, Any]:
    """Constructs a typed agent event dict.

    Args:
        event_type: Event name (e.g. "analyzing", "planning", "completed").
        **payload: Arbitrary keyword arguments included in the event payload.

    Returns:
        Serialisable event dict.
    """
    return {"event": event_type, "payload": payload}


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

def _make_retry_before_sleep(event_type: str, events_sink: List[Dict]) -> Any:
    """Builds a tenacity ``before_sleep`` callback that appends a retrying event.

    Args:
        event_type: Name of the agent being retried.
        events_sink: Mutable list; the callback appends events here so the
            generator can yield them on the next iteration.

    Returns:
        Callable accepted by ``tenacity.retry(before_sleep=...)``.
    """
    def _callback(retry_state: tenacity.RetryCallState) -> None:
        events_sink.append(_event(
            "retrying",
            agent=event_type,
            attempt=retry_state.attempt_number,
            message=(
                f"{event_type}: attempt {retry_state.attempt_number} failed — retrying…"
            ),
        ))
    return _callback


async def _with_retry(
    coro_factory,
    agent_name: str,
    pending_events: List[Dict],
    max_attempts: int = 3,
):
    """Runs ``coro_factory()`` with exponential-backoff retry.

    Args:
        coro_factory: Zero-arg callable returning a coroutine.
        agent_name: Human-readable agent label for retry SSE events.
        pending_events: Mutable list; retry events are appended here.
        max_attempts: Maximum number of attempts before re-raising.

    Returns:
        Result of the coroutine on success.

    Raises:
        Exception: If all attempts fail.
    """
    retryer = tenacity.AsyncRetrying(
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        stop=tenacity.stop_after_attempt(max_attempts),
        retry=tenacity.retry_if_exception_type(Exception),
        before_sleep=_make_retry_before_sleep(agent_name, pending_events),
        reraise=True,
    )
    async for attempt in retryer:
        with attempt:
            return await coro_factory()


# ---------------------------------------------------------------------------
# Timing helper
# ---------------------------------------------------------------------------

def _ms_since(t0: float) -> int:
    """Returns elapsed milliseconds since ``t0`` (from ``time.monotonic()``)."""
    return int((time.monotonic() - t0) * 1000)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class DsStarOrchestrator:
    """Runs the full DS-STAR iterative loop and streams progress events.

    Attributes:
        analyzer: FileAnalyzerAgent for building data descriptions.
        planner: PlannerAgent for creating and mutating plans.
        coder: CoderAgent for generating Python scripts.
        executor: CodeExecutor for sandboxed code execution.
        verifier: VerifierAgent for judging plan sufficiency.
        router: RouterAgent for deciding plan mutations.
    """

    def __init__(
        self,
        max_rounds: Optional[int] = None,
        model: Optional[str] = None,
        coder_model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> None:
        self._max_rounds = max_rounds or MAX_AGENT_ROUNDS
        self.analyzer = FileAnalyzerAgent()
        self.planner = PlannerAgent(model=model, temperature=temperature)
        self.coder = CoderAgent(model=coder_model, temperature=temperature)
        self.executor = CodeExecutor()
        self.verifier = VerifierAgent(model=model, temperature=temperature)
        self.router = RouterAgent(model=model, temperature=temperature)

    async def run(
        self,
        query: str,
        context: Dict[str, Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Executes the DS-STAR loop and yields SSE events.

        Args:
            query: The user's natural language query.
            context: Processing context from /process endpoint,
                including ``combined_extractions`` and ``files_processed``.

        Yields:
            AgentEvent dicts for SSE streaming.
        """
        run_t0 = time.monotonic()
        execution_logs: List[str] = []
        combined = context.get("combined_extractions", {})
        pending_retry_events: List[Dict] = []
        round_metrics: List[RoundMetric] = []

        # Determine task complexity (easy = 1 file, hard = 2+ files — per paper)
        file_count = len(combined)
        complexity = "hard" if file_count >= 2 else "easy"

        # ── Stage 1: File Analysis ────────────────────────────────────────────
        yield _event("analyzing", message="Analyzing data files…")
        analyzer_t0 = time.monotonic()
        try:
            data_description = self.analyzer.analyze(combined)
            yield _event(
                "analysis_complete",
                message="Data analysis complete.",
                data_description=data_description,
            )
        except Exception as exc:  # pylint: disable=broad-except
            data_description = f"Data description unavailable: {exc}"
            yield _event("warning", message=f"File analysis error: {exc}")
        analyzer_ms = _ms_since(analyzer_t0)

        execution_logs.append(
            f"[FileAnalyzer] {len(data_description)} chars of data description generated."
        )

        # ── Stage 2: Initial Plan ─────────────────────────────────────────────
        yield _event("planning", message="Creating initial analysis plan…")
        planner_t0 = time.monotonic()
        try:
            plan_steps = await _with_retry(
                lambda: self.planner.create_plan(query, data_description),
                "PlannerAgent",
                pending_retry_events,
            )
            for ev in pending_retry_events:
                yield ev
            pending_retry_events.clear()
        except Exception as exc:  # pylint: disable=broad-except
            for ev in pending_retry_events:
                yield ev
            pending_retry_events.clear()
            plan_steps = [
                {"index": 0, "description": "Load and inspect available data.", "status": "pending"},
                {"index": 1, "description": f"Answer the query: {query}", "status": "pending"},
            ]
            yield _event("warning", message=f"Planner error (using fallback): {exc}")
        planner_ms = _ms_since(planner_t0)

        yield _event("plan_ready", message="Plan created.", steps=plan_steps)
        execution_logs.append(f"[Planner] Initial plan: {len(plan_steps)} steps.")

        # ── Stage 3: Iterative Loop ───────────────────────────────────────────
        current_code = ""
        last_exec_result: ExecutionResult = ExecutionResult("", "", 0)
        verification: Dict[str, Any] = {"is_sufficient": False, "reason": "", "confidence": 0.0}
        rounds_completed = 0
        rounds_until_sufficient = 0

        for round_num in range(1, self._max_rounds + 1):
            rounds_completed = round_num
            timing = RoundTimingCollector(round_num=round_num)
            # Charge planner and analyzer time to round 1 only
            if round_num == 1:
                timing.record("planner", planner_ms + analyzer_ms)

            yield _event(
                "round_start",
                message=f"Round {round_num}/{self._max_rounds}",
                round=round_num,
                max_rounds=self._max_rounds,
            )

            # ── 3a. Code Generation ───────────────────────────────────────────
            yield _event("coding", message=f"Round {round_num}: Generating Python code…", round=round_num)
            coder_t0 = time.monotonic()
            try:
                current_code = await _with_retry(
                    lambda: self.coder.generate_code(
                        query=query,
                        data_description=data_description,
                        plan_steps=plan_steps,
                        previous_code=current_code,
                        execution_output=last_exec_result.combined_output(),
                    ),
                    "CoderAgent",
                    pending_retry_events,
                )
                for ev in pending_retry_events:
                    yield ev
                pending_retry_events.clear()
                timing.record("coder", _ms_since(coder_t0))
                yield _event("code_ready", message="Code generated.", code=current_code, round=round_num)
            except Exception as exc:  # pylint: disable=broad-except
                for ev in pending_retry_events:
                    yield ev
                pending_retry_events.clear()
                timing.record("coder", _ms_since(coder_t0))
                execution_logs.append(f"[Round {round_num}] Coder exhausted retries: {exc}")
                yield _event("error", message=f"CoderAgent failed after 3 attempts: {exc}")
                return

            # ── 3b. Code Execution ────────────────────────────────────────────
            yield _event("executing", message=f"Round {round_num}: Executing generated code…", round=round_num)
            exec_t0 = time.monotonic()
            try:
                last_exec_result = self.executor.run(current_code)
                timing.record("executor", _ms_since(exec_t0))
                exec_summary = (
                    f"[Round {round_num}] Execution "
                    f"{'succeeded' if last_exec_result.success else 'failed'}."
                    f" stdout={len(last_exec_result.stdout)} chars,"
                    f" stderr={len(last_exec_result.stderr)} chars."
                )
                execution_logs.append(exec_summary)
                yield _event(
                    "execution_result",
                    message=f"Round {round_num}: Execution {'succeeded' if last_exec_result.success else 'failed'}.",
                    stdout=last_exec_result.stdout[:2000],
                    stderr=last_exec_result.stderr[:500],
                    success=last_exec_result.success,
                    round=round_num,
                    executor_ms=timing._timings.get("executor", 0),
                )

                # ── Emit artifact events ────────────────────────────────────
                for fname, b64data in last_exec_result.artifacts.items():
                    mime = "image/png" if fname.endswith(".png") else (
                        "text/csv" if fname.endswith(".csv") else "application/octet-stream"
                    )
                    yield _event(
                        "artifact",
                        name=fname,
                        data=b64data,
                        mime_type=mime,
                        round=round_num,
                    )

            except Exception as exc:  # pylint: disable=broad-except
                timing.record("executor", _ms_since(exec_t0))
                last_exec_result = ExecutionResult("", str(exc), 1)
                execution_logs.append(f"[Round {round_num}] Executor crash: {exc}")
                yield _event("warning", message=f"Executor crash: {exc}")

            # ── 3c. Verification ──────────────────────────────────────────────
            yield _event("verifying", message=f"Round {round_num}: Verifying plan sufficiency…", round=round_num)
            verifier_t0 = time.monotonic()
            try:
                verification = await _with_retry(
                    lambda: self.verifier.verify(
                        query=query,
                        data_description=data_description,
                        plan_steps=plan_steps,
                        code=current_code,
                        execution_output=last_exec_result.combined_output(),
                    ),
                    "VerifierAgent",
                    pending_retry_events,
                )
                for ev in pending_retry_events:
                    yield ev
                pending_retry_events.clear()
                timing.record("verifier", _ms_since(verifier_t0))
                execution_logs.append(
                    f"[Round {round_num}] Verifier: sufficient={verification['is_sufficient']}, "
                    f"reason={verification['reason'][:80]}"
                )
                yield _event(
                    "verification_result",
                    message=f"Round {round_num}: {'Sufficient ✓' if verification['is_sufficient'] else 'Insufficient — refining…'}",
                    is_sufficient=verification["is_sufficient"],
                    reason=verification["reason"],
                    confidence=verification.get("confidence", 0.5),
                    round=round_num,
                    verifier_ms=timing._timings.get("verifier", 0),
                )
            except Exception as exc:  # pylint: disable=broad-except
                for ev in pending_retry_events:
                    yield ev
                pending_retry_events.clear()
                timing.record("verifier", _ms_since(verifier_t0))
                verification = {"is_sufficient": False, "reason": str(exc), "confidence": 0.0}
                execution_logs.append(f"[Round {round_num}] Verifier exhausted retries: {exc}")
                yield _event("warning", message=f"Verifier error: {exc}")

            # Build and store round metric
            round_metrics.append(timing.build(
                is_sufficient=verification["is_sufficient"],
                verifier_confidence=verification.get("confidence", 0.0),
                exec_success=last_exec_result.success,
            ))

            if verification["is_sufficient"]:
                rounds_until_sufficient = round_num
                break  # ✓ Done

            # ── 3d. Routing (only if insufficient) ────────────────────────────
            if round_num < self._max_rounds:
                yield _event("routing", message=f"Round {round_num}: Deciding how to refine the plan…", round=round_num)
                router_t0 = time.monotonic()
                try:
                    decision = await _with_retry(
                        lambda: self.router.route(
                            query=query,
                            data_description=data_description,
                            plan_steps=plan_steps,
                            verifier_reason=verification["reason"],
                        ),
                        "RouterAgent",
                        pending_retry_events,
                    )
                    for ev in pending_retry_events:
                        yield ev
                    pending_retry_events.clear()
                    timing.record("router", _ms_since(router_t0))

                    action = decision.get("action", "ADD_STEP")
                    step_index = decision.get("step_index")
                    new_step = decision.get("new_step", {})

                    if action == "FIX_STEP" and step_index is not None:
                        plan_steps = self.planner.fix_step(plan_steps, step_index, new_step)
                    else:
                        plan_steps = self.planner.add_step(plan_steps, new_step)

                    execution_logs.append(
                        f"[Round {round_num}] Router: {action}, new plan has {len(plan_steps)} steps."
                    )
                    yield _event(
                        "plan_updated",
                        message=f"Round {round_num}: Plan updated ({action}).",
                        steps=plan_steps,
                        action=action,
                        round=round_num,
                        router_ms=timing._timings.get("router", 0),
                    )
                except Exception as exc:  # pylint: disable=broad-except
                    for ev in pending_retry_events:
                        yield ev
                    pending_retry_events.clear()
                    timing.record("router", _ms_since(router_t0))
                    execution_logs.append(f"[Round {round_num}] Router error: {exc}")
                    yield _event("warning", message=f"Router error: {exc}")

        # ── Stage 4: Evaluation Metrics ───────────────────────────────────────
        total_run_ms = _ms_since(run_t0)
        final_status = (
            "completed" if verification.get("is_sufficient") else "max_rounds_reached"
        )
        run_metrics = RunMetrics(
            run_id="",  # filled in by agent_controller with the real run_id
            query=query,
            complexity=complexity,
            file_count=file_count,
            rounds_completed=rounds_completed,
            rounds_until_sufficient=rounds_until_sufficient or rounds_completed,
            total_run_ms=total_run_ms,
            final_status=final_status,
            rounds=round_metrics,
        )

        # ── Stage 5: Final Output ─────────────────────────────────────────────
        insights = _build_insights(
            query=query,
            plan_steps=plan_steps,
            execution_output=last_exec_result.stdout or last_exec_result.stderr,
            rounds=rounds_completed,
            verified=verification.get("is_sufficient", False),
        )

        final_result = {
            "insights": insights,
            "code": {"Python": current_code},
            "plan_steps": plan_steps,
            "rounds": rounds_completed,
            "execution_logs": execution_logs,
        }

        yield _event(
            "completed",
            message=f"DS-STAR analysis complete in {rounds_completed} round(s).",
            **final_result,
        )

        # Emit metrics as a dedicated event for the controller to persist
        yield _event(
            "metrics",
            message="Run evaluation metrics captured.",
            metrics=run_metrics.summary(),
            total_run_ms=total_run_ms,
            complexity=complexity,
        )

        logger.info(
            "[Orchestrator] Completed — rounds=%d, steps=%d, code=%d chars, complexity=%s, total_ms=%d",
            rounds_completed,
            len(plan_steps),
            len(current_code),
            complexity,
            total_run_ms,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_insights(
    query: str,
    plan_steps: List[Dict[str, Any]],
    execution_output: str,
    rounds: int,
    verified: bool,
) -> Dict[str, Any]:
    """Builds a narrative insights dict from the agent run result.

    Args:
        query: Original user query.
        plan_steps: Final plan steps.
        execution_output: The stdout from the last execution.
        rounds: Number of rounds completed.
        verified: Whether the verifier approved the final plan.

    Returns:
        Insights dict with ``summary`` (str) and ``bullets`` (List[str]).
    """
    if execution_output and len(execution_output.strip()) > 10:
        summary = execution_output.strip()[:800]
    else:
        summary = (
            f"DS-STAR completed the analysis for your query: \"{query}\". "
            f"The agent ran {rounds} refinement round(s) and produced the code above."
        )

    bullets = [
        f"Agent completed in {rounds} round(s)",
        f"Plan steps executed: {len(plan_steps)}",
        f"Verification status: {'✓ Approved' if verified else '⚠ Max rounds reached'}",
    ]
    for step in plan_steps:
        bullets.append(f"• Step {step['index'] + 1}: {step['description']}")

    return {"summary": summary, "bullets": bullets}
