"""Pydantic schemas for DS-STAR evaluation metrics.

Captures per-round timing, token usage, and task complexity tagging to
mirror the ablation study methodology in the DS-STAR paper (easy vs. hard
task convergence: 3.0 vs 5.6 average rounds on DABStep).
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class RoundMetric(BaseModel):
    """Timing and status data captured for a single agent loop round.

    Attributes:
        round_num: 1-based round number within the run.
        planner_ms: Milliseconds spent in the PlannerAgent call (round 1 only).
        coder_ms: Milliseconds spent in the CoderAgent call.
        executor_ms: Milliseconds spent in subprocess code execution.
        verifier_ms: Milliseconds spent in the VerifierAgent call.
        router_ms: Milliseconds spent in the RouterAgent call (0 if not triggered).
        total_ms: Total wall-clock milliseconds for this round.
        is_sufficient: Whether VerifierAgent approved this round's output.
        verifier_confidence: Confidence score emitted by the verifier (0.0–1.0).
        exec_success: Whether the executor subprocess exited with code 0.
    """

    round_num: int = Field(ge=1, description="1-based round index.")
    planner_ms: int = Field(default=0, ge=0, description="Planner latency (ms).")
    coder_ms: int = Field(default=0, ge=0, description="Coder latency (ms).")
    executor_ms: int = Field(default=0, ge=0, description="Executor latency (ms).")
    verifier_ms: int = Field(default=0, ge=0, description="Verifier latency (ms).")
    router_ms: int = Field(default=0, ge=0, description="Router latency (ms).")
    total_ms: int = Field(default=0, ge=0, description="Total round wall-clock (ms).")
    prompt_tokens: int = Field(default=0, ge=0, description="Total prompt tokens in this round.")
    completion_tokens: int = Field(default=0, ge=0, description="Total completion tokens in this round.")
    is_sufficient: bool = Field(default=False)
    verifier_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    exec_success: bool = Field(default=False)


class RunMetrics(BaseModel):
    """Full evaluation-quality metrics for a single DS-STAR agent run.

    These metrics enable tracking the convergence patterns described in the
    DS-STAR paper (Section 4.2 ablations), differentiating easy vs. hard tasks.

    Attributes:
        run_id: UUID matching the agent_runs Supabase row.
        query: Original user query text.
        complexity: Task complexity tag — 'easy' (single file) or 'hard' (multi-file).
        file_count: Number of distinct files in the processing context.
        rounds_completed: Total refinement rounds consumed.
        rounds_until_sufficient: Round index at which Verifier first approved output
            (equals rounds_completed if max rounds hit without approval).
        total_run_ms: Total wall-clock duration of the entire agent run (ms).
        final_status: "completed" | "failed" | "max_rounds_reached".
        rounds: Ordered per-round metric breakdown.
    """

    run_id: str
    query: str
    complexity: Literal["easy", "hard"] = Field(
        description="'easy' = single file, 'hard' = 2+ files (per DABStep taxonomy)."
    )
    file_count: int = Field(default=1, ge=0)
    rounds_completed: int = Field(default=0, ge=0)
    rounds_until_sufficient: int = Field(default=0, ge=0)
    total_run_ms: int = Field(default=0, ge=0)
    final_status: Literal["completed", "failed", "max_rounds_reached"] = "completed"
    rounds: List[RoundMetric] = Field(default_factory=list)

    def summary(self) -> Dict:
        """Returns a flat serialisable dict suitable for Supabase jsonb column.

        Returns:
            Dict with top-level metrics and per-round breakdown.
        """
        return {
            "complexity": self.complexity,
            "file_count": self.file_count,
            "rounds_completed": self.rounds_completed,
            "rounds_until_sufficient": self.rounds_until_sufficient,
            "total_run_ms": self.total_run_ms,
            "final_status": self.final_status,
            "per_round": [r.model_dump() for r in self.rounds],
        }


class RoundTimingCollector:
    """Context-manager-style helper for recording per-stage timing within a round.

    Usage::

        collector = RoundTimingCollector(round_num=1)
        with collector.time("coder"):
            result = await coder.generate_code(...)
        metric = collector.build()
    """

    import time as _time

    def __init__(self, round_num: int) -> None:
        self._round_num = round_num
        self._timings: Dict[str, int] = {}
        self._prompt_tokens = 0
        self._completion_tokens = 0

    def record(self, stage: str, elapsed_ms: int) -> None:
        """Manually records a timing entry."""
        self._timings[stage] = elapsed_ms

    def record_tokens(self, prompt: int, completion: int) -> None:
        """Aggregates token usage for the round."""
        self._prompt_tokens += prompt
        self._completion_tokens += completion

    def build(
        self,
        is_sufficient: bool = False,
        verifier_confidence: float = 0.0,
        exec_success: bool = False,
    ) -> RoundMetric:
        """Assembles a ``RoundMetric`` from recorded timings and tokens."""
        total = sum(self._timings.values())
        return RoundMetric(
            round_num=self._round_num,
            planner_ms=self._timings.get("planner", 0),
            coder_ms=self._timings.get("coder", 0),
            executor_ms=self._timings.get("executor", 0),
            verifier_ms=self._timings.get("verifier", 0),
            router_ms=self._timings.get("router", 0),
            total_ms=total,
            prompt_tokens=self._prompt_tokens,
            completion_tokens=self._completion_tokens,
            is_sufficient=is_sufficient,
            verifier_confidence=verifier_confidence,
            exec_success=exec_success,
        )
