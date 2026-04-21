"""EvalEngine — derives aggregated metrics from raw EvalStep traces.

All computation is pure Python with no I/O so it is synchronous and
easily unit-testable.
"""

from typing import Any, Dict, List

from eval.schemas import EvalRunMetrics, EvalStep


# ---------------------------------------------------------------------------
# Per-run metric computation
# ---------------------------------------------------------------------------

def compute_run_metrics(
    steps: List[EvalStep],
    run_meta: Dict[str, Any],
    debug_depths: List[int],
    initial_plan_count: int,
    final_plan_count: int,
    query_length: int = 0,
    mode: str = "live",
) -> EvalRunMetrics:
    """Derives an EvalRunMetrics from the captured steps and loop metadata.

    Args:
        steps:              All EvalStep objects captured for this run.
        run_meta:           The ``payload`` dict from the ``"metrics"`` SSE event.
        debug_depths:       List of debug loop depths per orchestrator round.
        initial_plan_count: Steps in the initial plan (from ``plan_ready``).
        final_plan_count:   Steps in the final plan (from last ``plan_updated``
                            or ``plan_ready`` if router never fired).
        query_length:       Character length of the original query.
        mode:               ``"live"`` or ``"batch"``.

    Returns:
        Fully populated EvalRunMetrics instance.
    """
    # Pull run_id from run_meta (the metrics SSE payload carries metrics sub-dict)
    metrics_sub = run_meta.get("metrics", {})
    run_id: str = metrics_sub.get("run_id", run_meta.get("run_id", ""))

    # ── Correctness ───────────────────────────────────────────────────────
    final_status: str = metrics_sub.get("final_status", "max_rounds_reached")
    success_rate = 1.0 if final_status == "completed" else 0.0

    exec_steps = [s for s in steps if s.agent_name == "Executor"]
    exec_success_rate = (
        sum(1 for s in exec_steps if s.validation_passed) / len(exec_steps)
        if exec_steps else 0.0
    )

    total_steps = len(steps)
    validation_pass_rate = (
        sum(1 for s in steps if s.validation_passed) / total_steps
        if total_steps else 1.0
    )

    # ── Efficiency ────────────────────────────────────────────────────────
    total_retries = sum(s.retry_count for s in steps)

    avg_debug_depth = (
        sum(debug_depths) / len(debug_depths) if debug_depths else 0.0
    )

    # ── Per-agent latency sums ─────────────────────────────────────────────
    def _sum_ms(agent: str) -> int:
        return sum(s.latency_ms for s in steps if s.agent_name == agent)

    # Pull per-round timings from the RoundMetric breakdown when available
    per_round: List[Dict[str, Any]] = metrics_sub.get("per_round", [])
    if per_round:
        planner_ms  = sum(r.get("planner_ms", 0)  for r in per_round)
        coder_ms    = sum(r.get("coder_ms", 0)    for r in per_round)
        executor_ms = sum(r.get("executor_ms", 0) for r in per_round)
        verifier_ms = sum(r.get("verifier_ms", 0) for r in per_round)
        router_ms   = sum(r.get("router_ms", 0)   for r in per_round)
    else:
        # Fallback: derive from step-level captures
        planner_ms  = _sum_ms("Planner")
        coder_ms    = _sum_ms("Coder")
        executor_ms = _sum_ms("Executor")
        verifier_ms = _sum_ms("Verifier")
        router_ms   = _sum_ms("Router")

    analyzer_ms  = _sum_ms("Analyzer")
    debugger_ms  = _sum_ms("Debugger")
    finalizer_ms = _sum_ms("Finalizer")

    # ── Difficulty ─────────────────────────────────────────────────────────
    difficulty = run_meta.get("complexity", metrics_sub.get("complexity", "easy"))

    return EvalRunMetrics(
        run_id=run_id,
        success_rate=round(success_rate, 4),
        exec_success_rate=round(exec_success_rate, 4),
        validation_pass_rate=round(validation_pass_rate, 4),
        total_retries=total_retries,
        avg_debug_depth=round(avg_debug_depth, 2),
        plan_step_count=initial_plan_count,
        final_step_count=final_plan_count,
        analyzer_ms=analyzer_ms,
        planner_ms=planner_ms,
        coder_ms=coder_ms,
        executor_ms=executor_ms,
        debugger_ms=debugger_ms,
        verifier_ms=verifier_ms,
        router_ms=router_ms,
        finalizer_ms=finalizer_ms,
        difficulty=difficulty,
        mode=mode,
        query_length=query_length,
    )


# ---------------------------------------------------------------------------
# Cross-run agent summary (for dashboard /agents endpoint)
# ---------------------------------------------------------------------------

def compute_agent_summary(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Aggregates per-agent statistics across multiple eval_metrics rows.

    Args:
        rows: Rows from the ``eval_metrics`` table (list of dicts).

    Returns:
        Dict keyed by agent_name with keys:
            ``avg_latency_ms``, ``total_calls``, ``failure_rate``,
            ``avg_retry_rate``.
    """
    agents = [
        "Analyzer", "Planner", "Coder", "Executor",
        "Debugger", "Verifier", "Router", "Finalizer",
    ]
    latency_col = {
        "Analyzer":  "analyzer_ms",
        "Planner":   "planner_ms",
        "Coder":     "coder_ms",
        "Executor":  "executor_ms",
        "Debugger":  "debugger_ms",
        "Verifier":  "verifier_ms",
        "Router":    "router_ms",
        "Finalizer": "finalizer_ms",
    }
    summary: Dict[str, Dict[str, Any]] = {}
    n = len(rows) or 1

    for agent in agents:
        col = latency_col[agent]
        latencies = [r.get(col, 0) for r in rows if r.get(col, 0) > 0]
        avg_lat = round(sum(latencies) / len(latencies), 1) if latencies else 0

        # Executor failure rate = 1 - exec_success_rate
        if agent == "Executor":
            if len(rows) == 0:
                failure_rate = 0.0
            else:
                failure_rate = round(
                    1.0 - (sum(r.get("exec_success_rate", 0) for r in rows) / n), 4
                )
        elif agent in ("Verifier", "Analyzer", "Planner", "Coder", "Finalizer"):
            # Proxy: fraction of runs the agent had retries
            failure_rate = 0.0  # refined below via step data if available
        else:
            failure_rate = 0.0

        summary[agent] = {
            "avg_latency_ms": avg_lat,
            "failure_rate": failure_rate,
            "total_calls": len(latencies),
        }
    return summary
