"""Unit tests for domain models — Pydantic validation and invariants."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from vera_core.models.agent_config import AgentDefaults, AgentTier, ModelAssignment
from vera_core.models.ids import ProviderConnectionId, UserId
from vera_core.models.provider import ConnectionStatus, ModelInfo, ProviderConnection, ProviderKind
from vera_core.models.run import (
    Observation,
    PlanStep,
    RunBudget,
    RunMode,
    RunState,
    RunStatus,
)


def test_file_description_partial_defaults_false_and_round_trips() -> None:
    from vera_core.models.file import FileDescription
    from vera_core.models.ids import FileId

    d = FileDescription(file_id=FileId(uuid.uuid4()), summary_text="x")
    assert d.partial is False

    d2 = FileDescription(file_id=FileId(uuid.uuid4()), summary_text="x", partial=True)
    assert FileDescription.model_validate_json(d2.model_dump_json()).partial is True


def test_file_analyzed_event_partial_round_trips() -> None:
    from vera_core.models.events import FileAnalyzedEvent
    from vera_core.models.ids import RunId

    e = FileAnalyzedEvent(run_id=RunId(uuid.uuid4()), file_id="f1", filename="x.csv", partial=True)
    assert FileAnalyzedEvent.model_validate_json(e.model_dump_json()).partial is True


def uid() -> UserId:
    return UserId(uuid.uuid4())


def pcid() -> ProviderConnectionId:
    return ProviderConnectionId(uuid.uuid4())


# ── AgentDefaults ─────────────────────────────────────────────────────────────


class TestAgentDefaults:
    def test_has_all_tiers_true(self):
        conn_id = pcid()
        defaults = AgentDefaults(
            user_id=uid(),
            assignments=[
                ModelAssignment(
                    tier=AgentTier.REASONING, provider_connection_id=conn_id, model_id="a"
                ),
                ModelAssignment(
                    tier=AgentTier.UTILITY, provider_connection_id=conn_id, model_id="b"
                ),
            ],
        )
        assert defaults.has_all_tiers() is True

    def test_has_all_tiers_false_missing_utility(self):
        defaults = AgentDefaults(
            user_id=uid(),
            assignments=[
                ModelAssignment(
                    tier=AgentTier.REASONING, provider_connection_id=pcid(), model_id="a"
                ),
            ],
        )
        assert defaults.has_all_tiers() is False

    def test_has_all_tiers_false_empty(self):
        defaults = AgentDefaults(user_id=uid())
        assert defaults.has_all_tiers() is False

    def test_get_assignment_found(self):
        conn_id = pcid()
        assignment = ModelAssignment(
            tier=AgentTier.REASONING, provider_connection_id=conn_id, model_id="gpt-4o"
        )
        defaults = AgentDefaults(user_id=uid(), assignments=[assignment])
        result = defaults.get_assignment(AgentTier.REASONING)
        assert result.model_id == "gpt-4o"

    def test_get_assignment_missing_raises(self):
        defaults = AgentDefaults(user_id=uid())
        with pytest.raises(ValueError, match="No model assignment"):
            defaults.get_assignment(AgentTier.REASONING)

    def test_temperature_bounds(self):
        with pytest.raises(ValidationError, match="less_than_equal"):
            ModelAssignment(
                tier=AgentTier.REASONING,
                provider_connection_id=pcid(),
                model_id="m",
                temperature=3.0,
            )

    def test_max_tokens_minimum(self):
        with pytest.raises(ValidationError, match="greater_than_equal"):
            ModelAssignment(
                tier=AgentTier.REASONING, provider_connection_id=pcid(), model_id="m", max_tokens=0
            )


# ── RunState ──────────────────────────────────────────────────────────────────


class TestRunState:
    def _make_state(self, **kwargs) -> RunState:
        return RunState(
            run_id=uuid.uuid4(),  # type: ignore[arg-type]
            tenant_id=uuid.uuid4(),  # type: ignore[arg-type]
            user_id=uuid.uuid4(),  # type: ignore[arg-type]
            workspace_id=uuid.uuid4(),  # type: ignore[arg-type]
            query="test query",
            mode=RunMode.PRECISE,
            status=RunStatus.RUNNING,
            started_at=datetime.now(UTC),
            **kwargs,
        )

    def test_active_plan_excludes_superseded(self):
        state = self._make_state(
            plan=[
                PlanStep(index=0, text="step 0", superseded=True),
                PlanStep(index=1, text="step 1", superseded=False),
                PlanStep(index=2, text="step 2", superseded=False),
            ]
        )
        assert len(state.active_plan) == 2
        assert all(s.index > 0 for s in state.active_plan)

    def test_budget_exhausted_by_rounds(self):
        state = self._make_state(budget=RunBudget(max_rounds=5), round=5)
        assert state.budget_exhausted() is True

    def test_budget_not_exhausted(self):
        state = self._make_state(budget=RunBudget(max_rounds=10), round=3)
        assert state.budget_exhausted() is False

    def test_budget_exhausted_by_cost(self):
        state = self._make_state(
            budget=RunBudget(max_cost_usd=Decimal("1.00")),
            cost_usd=Decimal("1.00"),
        )
        assert state.budget_exhausted() is True

    def test_last_observation_none_when_empty(self):
        state = self._make_state()
        assert state.last_observation is None

    def test_last_observation_returns_last(self):
        obs1 = Observation(stdout="first", stderr="", exit_code=0, duration_ms=10)
        obs2 = Observation(stdout="last", stderr="", exit_code=0, duration_ms=20)
        state = self._make_state(observations=[obs1, obs2])
        assert state.last_observation.stdout == "last"


# ── ProviderConnection ────────────────────────────────────────────────────────


class TestProviderConnection:
    def test_provider_connection_frozen(self):
        conn = ProviderConnection(
            id=pcid(),
            tenant_id=uuid.uuid4(),  # type: ignore[arg-type]
            user_id=uid(),
            kind=ProviderKind.OPENROUTER,
            display_name="Test",
            base_url="https://openrouter.ai/api/v1",
            api_key_ref="ref:123",
            status=ConnectionStatus.CONNECTED,
            created_at=datetime.now(UTC),
        )
        with pytest.raises(ValidationError, match="frozen"):
            conn.display_name = "Modified"  # type: ignore[misc]

    def test_model_info_frozen(self):
        info = ModelInfo(model_id="a/b", display_name="A B", context_window=4096)
        with pytest.raises(ValidationError, match="frozen"):
            info.model_id = "c/d"  # type: ignore[misc]


# ── Observation ───────────────────────────────────────────────────────────────


class TestObservation:
    def test_succeeded_true_on_zero_exit(self):
        obs = Observation(stdout="ok", stderr="", exit_code=0, duration_ms=5)
        assert obs.succeeded is True

    def test_succeeded_false_on_nonzero_exit(self):
        obs = Observation(stdout="", stderr="error", exit_code=1, duration_ms=5)
        assert obs.succeeded is False


# ── Backtrack bookkeeping (Phase 3) ───────────────────────────────────────────


def test_abandoned_branch_round_trips():
    from vera_core.models.run import AbandonedBranch

    b = AbandonedBranch(
        round=2,
        from_index=1,
        removed_step_texts=["compute fees"],
        removed_script_sha="abc",
        rationale="wrong join key",
    )
    assert AbandonedBranch.model_validate_json(b.model_dump_json()) == b


def test_run_state_round_trips_with_checkpoints():
    from vera_core.models.code import CodeArtifact
    from vera_core.models.observation import Observation
    from vera_testing.factories.domain import make_run_state

    st = make_run_state()
    st.script_checkpoints[0] = CodeArtifact(source="print(1)", sha256="s0")
    st.script_checkpoints[1] = CodeArtifact(source="print(2)", sha256="s1")
    st.observation_checkpoints[0] = Observation(stdout="1", stderr="", exit_code=0, duration_ms=1)
    round_tripped = type(st).model_validate_json(st.model_dump_json())
    assert round_tripped.script_checkpoints[1].sha256 == "s1"  # int key survives
    assert round_tripped.observation_checkpoints[0].stdout == "1"


def test_moved_types_importable_from_new_and_old_paths():
    from vera_core.models.observation import Observation as ONew
    from vera_core.models.run import Observation as OOld
    from vera_core.models.run import Verdict as VOld
    from vera_core.models.verdict import Verdict as VNew

    assert ONew is OOld and VNew is VOld


def test_run_state_research_fields_default_and_round_trip() -> None:
    from vera_core.models.report import Report, SubQuestion
    from vera_testing.factories.domain import make_run_state

    st = make_run_state()
    assert st.sub_questions == []
    assert st.report is None

    st.sub_questions.append(SubQuestion(idx=1, text="what is X?"))
    st.report = Report(markdown="# Report\nX is 5 [SQ-1].", sub_question_count=1)
    rt = RunState.model_validate_json(st.model_dump_json())
    assert rt.sub_questions[0].text == "what is X?"
    assert rt.report is not None and "SQ-1" in rt.report.markdown


def test_run_budget_research_bounds() -> None:
    b = RunBudget()
    assert b.max_sub_questions == 8
    assert b.max_gap_rounds == 1
    b2 = RunBudget(max_sub_questions=3, max_gap_rounds=0)
    assert RunBudget.model_validate_json(b2.model_dump_json()).max_sub_questions == 3
    with pytest.raises(ValidationError):
        RunBudget(max_gap_rounds=99)


def test_research_events_round_trip() -> None:
    from vera_core.models.events import (
        ReportGeneratedEvent,
        SubQuestionResolvedEvent,
        SubQuestionsGeneratedEvent,
    )
    from vera_core.models.ids import RunId

    rid = RunId(uuid.uuid4())
    for ev in (
        SubQuestionsGeneratedEvent(run_id=rid, count=3, gap_round=0),
        SubQuestionResolvedEvent(run_id=rid, idx=1, status="done", child_run_id="c1"),
        ReportGeneratedEvent(run_id=rid, sub_question_count=3, gap_rounds=1),
    ):
        rt = type(ev).model_validate_json(ev.model_dump_json())
        assert rt == ev
