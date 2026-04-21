"""Pydantic schemas for the DS-STAR evaluation sidecar.

These models mirror the ``eval_steps`` and ``eval_metrics`` Supabase tables
defined in migrations/create_eval_schema.sql.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Step-level capture
# ---------------------------------------------------------------------------

class EvalStep(BaseModel):
    """One captured boundary event inside the DS-STAR orchestrator loop.

    Attributes:
        step_id:          UUID4 primary key for the eval_steps row.
        run_id:           Matches agent_runs.id.
        step_seq:         0-based ordering within the run.
        round_num:        1-based orchestrator round this step belongs to.
        agent_name:       One of Analyzer | Planner | Coder | Executor |
                          Debugger | Verifier | Router | Finalizer.
        input_summary:    Truncated input context (≤ 512 chars).
        output_summary:   Truncated output / result (≤ 512 chars).
        latency_ms:       Wall-clock ms spent in this step.
        retry_count:      Number of tenacity retries consumed.
        error_type:       Populated only on failure (e.g. ``"SyntaxError"``).
        validation_passed: Whether the step output passed schema validation.
        timestamp_iso:    ISO-8601 wall-clock timestamp at step start.
    """

    step_id: str
    run_id: str
    step_seq: int = Field(ge=0)
    round_num: int = Field(default=1, ge=1)
    agent_name: str
    input_summary: str = ""
    output_summary: str = ""
    latency_ms: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    error_type: Optional[str] = None
    validation_passed: bool = True
    timestamp_iso: str


# ---------------------------------------------------------------------------
# Run-level computed metrics
# ---------------------------------------------------------------------------

class EvalRunMetrics(BaseModel):
    """Aggregated evaluation metrics for a single DS-STAR run.

    Computed by EvalEngine from the collected EvalStep list after the run
    completes.  Persisted to the ``eval_metrics`` Supabase table.

    Attributes:
        run_id:             Matches agent_runs.id.
        success_rate:       1.0 if Verifier approved; 0.0 if max rounds hit.
        exec_success_rate:  Fraction of rounds where execution succeeded.
        validation_pass_rate: Fraction of steps that passed schema checks.
        total_retries:      Sum of retry_count across all steps.
        avg_debug_depth:    Average Debugger invocations per failed exec round.
        plan_step_count:    Steps in the initial plan.
        final_step_count:   Steps in the final plan.
        analyzer_ms:        Latency for the Analyzer stage.
        planner_ms:         Latency for the Planner stage (round 1).
        coder_ms:           Cumulative Coder latency across all rounds.
        executor_ms:        Cumulative Executor latency across all rounds.
        debugger_ms:        Cumulative Debugger latency across all rounds.
        verifier_ms:        Cumulative Verifier latency across all rounds.
        router_ms:          Cumulative Router latency across all rounds.
        finalizer_ms:       Latency for the Finalizer stage.
        difficulty:         Task difficulty tag — ``"easy"`` or ``"hard"``.
        mode:               ``"live"`` (production) or ``"batch"`` (offline eval).
        query_length:       Character length of the original query.
    """

    run_id: str
    # Correctness
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    exec_success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    validation_pass_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    # Efficiency
    total_retries: int = Field(default=0, ge=0)
    avg_debug_depth: float = Field(default=0.0, ge=0.0)
    plan_step_count: int = Field(default=0, ge=0)
    final_step_count: int = Field(default=0, ge=0)
    # Per-agent latency (ms)
    analyzer_ms: int = Field(default=0, ge=0)
    planner_ms: int = Field(default=0, ge=0)
    coder_ms: int = Field(default=0, ge=0)
    executor_ms: int = Field(default=0, ge=0)
    debugger_ms: int = Field(default=0, ge=0)
    verifier_ms: int = Field(default=0, ge=0)
    router_ms: int = Field(default=0, ge=0)
    finalizer_ms: int = Field(default=0, ge=0)
    # Classification
    difficulty: str = "easy"
    mode: str = "live"
    query_length: int = Field(default=0, ge=0)
