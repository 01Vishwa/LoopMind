"""Unit tests for policies — truncation, backtrack, context budget, termination, cycle detection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from vera_core.models.run import Observation, PlanStep, RunBudget, RunMode, RunState, RunStatus
from vera_core.policies.backtrack import active_steps, apply_backtrack
from vera_core.policies.context_budget import ContextBudget
from vera_core.policies.cycle_detection import CycleDetector, plan_fingerprint
from vera_core.policies.termination import check_budget, should_terminate
from vera_core.policies.truncation import truncate_observation

# ── Truncation ────────────────────────────────────────────────────────────────


class TestTruncation:
    def _obs(self, stdout="", stderr=""):
        return Observation(stdout=stdout, stderr=stderr, exit_code=0, duration_ms=5)

    def test_short_output_unchanged(self):
        obs = self._obs(stdout="hello", stderr="world")
        result = truncate_observation(obs, stdout_cap=100, stderr_cap=100)
        assert result.stdout == "hello"
        assert result.stderr == "world"
        assert result.truncated is False

    def test_long_stdout_capped(self):
        obs = self._obs(stdout="x" * 10_000)
        result = truncate_observation(obs, stdout_cap=100)
        assert len(result.stdout) < 10_000
        assert "[TRUNCATED" in result.stdout
        assert result.truncated is True

    def test_long_stderr_capped(self):
        obs = self._obs(stderr="e" * 5_000)
        result = truncate_observation(obs, stderr_cap=200)
        assert result.truncated is True

    def test_already_truncated_stays_truncated(self):
        obs = Observation(stdout="short", stderr="", exit_code=0, duration_ms=1, truncated=True)
        result = truncate_observation(obs, stdout_cap=1000)
        assert result.truncated is True

    def test_head_and_tail_preserved(self):
        # Content: AAAA...BBBB — head and tail should both appear
        content = "A" * 500 + "B" * 500
        obs = self._obs(stdout=content)
        result = truncate_observation(obs, stdout_cap=200)
        assert result.stdout.startswith("A")
        assert result.stdout.endswith("B")


# ── Backtrack ─────────────────────────────────────────────────────────────────


def _make_state(plan: list[PlanStep]) -> RunState:
    return RunState(
        run_id=uuid.uuid4(),  # type: ignore[arg-type]
        tenant_id=uuid.uuid4(),  # type: ignore[arg-type]
        user_id=uuid.uuid4(),  # type: ignore[arg-type]
        workspace_id=uuid.uuid4(),  # type: ignore[arg-type]
        query="q",
        mode=RunMode.PRECISE,
        status=RunStatus.RUNNING,
        plan=plan,
        started_at=datetime.now(UTC),
    )


class TestBacktrack:
    def test_backtrack_supersedes_from_index(self):
        steps = [PlanStep(index=i, text=f"step {i}") for i in range(4)]
        state = _make_state(steps)
        updated = apply_backtrack(state, backtrack_to_index=2)
        active = active_steps(updated)
        assert [s.index for s in active] == [0, 1]

    def test_backtrack_to_zero_supersedes_all(self):
        steps = [PlanStep(index=i, text=f"step {i}") for i in range(3)]
        state = _make_state(steps)
        updated = apply_backtrack(state, backtrack_to_index=0)
        assert active_steps(updated) == []

    def test_backtrack_empty_plan_raises(self):
        state = _make_state([])
        with pytest.raises(ValueError, match="empty"):
            apply_backtrack(state, backtrack_to_index=0)

    def test_active_steps_sorted_by_index(self):
        steps = [
            PlanStep(index=2, text="c"),
            PlanStep(index=0, text="a"),
            PlanStep(index=1, text="b"),
        ]
        state = _make_state(steps)
        result = active_steps(state)
        assert [s.index for s in result] == [0, 1, 2]

    def test_backtrack_preserves_history(self):
        steps = [PlanStep(index=i, text=f"step {i}") for i in range(3)]
        state = _make_state(steps)
        updated = apply_backtrack(state, backtrack_to_index=1)
        assert len(updated.plan) == 3  # history preserved
        superseded = [s for s in updated.plan if s.superseded]
        assert len(superseded) == 2


# ── ContextBudget ─────────────────────────────────────────────────────────────


class TestContextBudget:
    def test_consume_tracks_usage(self):
        budget = ContextBudget(max_tokens=1000)
        budget.consume(300)
        budget.consume(200)
        assert budget.used == 500

    def test_remaining_computed(self):
        budget = ContextBudget(max_tokens=1000)
        budget.consume(600)
        assert budget.remaining == 400

    def test_not_exceeded_initially(self):
        budget = ContextBudget(max_tokens=100)
        assert not budget.is_exceeded()

    def test_exceeded_at_limit(self):
        budget = ContextBudget(max_tokens=100)
        budget.consume(100)
        assert budget.is_exceeded()

    def test_negative_tokens_raise(self):
        budget = ContextBudget(max_tokens=100)
        with pytest.raises(ValueError):
            budget.consume(-1)

    def test_remaining_floored_at_zero(self):
        budget = ContextBudget(max_tokens=10)
        budget.consume(50)
        assert budget.remaining == 0


# ── Termination ───────────────────────────────────────────────────────────────


class TestTermination:
    def _state(self, round=0, cost="0", max_rounds=10, max_cost="5.00") -> RunState:
        return RunState(
            run_id=uuid.uuid4(),  # type: ignore[arg-type]
            tenant_id=uuid.uuid4(),  # type: ignore[arg-type]
            user_id=uuid.uuid4(),  # type: ignore[arg-type]
            workspace_id=uuid.uuid4(),  # type: ignore[arg-type]
            query="q",
            mode=RunMode.PRECISE,
            status=RunStatus.RUNNING,
            round=round,
            cost_usd=Decimal(cost),
            budget=RunBudget(max_rounds=max_rounds, max_cost_usd=Decimal(max_cost)),
            started_at=datetime.now(UTC),
        )

    def test_no_termination_under_limits(self):
        state = self._state(round=3, cost="1.00")
        assert check_budget(state) is None
        assert not should_terminate(state)

    def test_terminates_at_max_rounds(self):
        state = self._state(round=10, max_rounds=10)
        assert should_terminate(state) is True
        assert "rounds" in check_budget(state).lower()

    def test_terminates_at_cost_limit(self):
        state = self._state(cost="5.00", max_cost="5.00")
        assert should_terminate(state) is True
        assert "Cost" in check_budget(state)


# ── CycleDetection ────────────────────────────────────────────────────────────


class TestCycleDetection:
    def test_no_cycle_initially(self):
        detector = CycleDetector()
        steps = [PlanStep(index=0, text="step")]
        detector.record(steps)
        assert not detector.is_cycling()

    def test_cycle_detected_after_repeat(self):
        detector = CycleDetector(max_repeats=2)
        steps = [PlanStep(index=0, text="same plan")]
        detector.record(steps)
        detector.record(steps)
        assert detector.is_cycling() is True

    def test_no_cycle_with_different_plans(self):
        detector = CycleDetector(max_repeats=2)
        detector.record([PlanStep(index=0, text="plan A")])
        detector.record([PlanStep(index=0, text="plan B")])
        assert not detector.is_cycling()

    def test_fingerprint_ignores_superseded(self):
        active = [PlanStep(index=0, text="step", superseded=False)]
        with_superseded = [
            PlanStep(index=0, text="step", superseded=False),
            PlanStep(index=1, text="old step", superseded=True),
        ]
        # Active plan is the same, so fingerprints should match
        # (superseded steps are excluded from fingerprint)
        fp1 = plan_fingerprint(active)
        fp2 = plan_fingerprint(with_superseded)
        assert fp1 == fp2
