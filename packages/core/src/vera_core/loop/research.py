"""run_research — the DS-STAR+ orchestrator (plain async, not a StateGraph).

Linear pipeline: prime shared descriptions -> generate sub-questions -> answer
each with a child ``run_precise`` -> write a cited report -> up to
``budget.max_gap_rounds`` refinement rounds. All hard control flow lives inside
the per-sub-question ``run_precise`` graph, which this module never modifies.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from vera_core.agents import (
    ReportAnswer,
    ReportWriterPayload,
    SubQGenPayload,
    report_writer,
    subquestion_generator,
)
from vera_core.agents._types import SubQuestionList
from vera_core.loop.context import LoopDeps, account, build_context
from vera_core.loop.nodes import analyze, retrieve
from vera_core.loop.runner import run_precise
from vera_core.models.events import (
    ReportGeneratedEvent,
    RunFinishedEvent,
    SubQuestionResolvedEvent,
    SubQuestionsGeneratedEvent,
)
from vera_core.models.ids import RunId
from vera_core.models.report import Report, SubQuestion, SubQuestionStatus
from vera_core.models.run import RunMode, RunState, RunStatus
from vera_core.policies import CycleDetector


def _append_questions(state: RunState, sq_list: SubQuestionList) -> int:
    """Append drafts as SubQuestion rows up to the budget cap. Returns the count added."""
    added = 0
    for draft in sq_list.questions:
        if len(state.sub_questions) >= state.budget.max_sub_questions:
            break
        state.sub_questions.append(SubQuestion(idx=len(state.sub_questions) + 1, text=draft.text))
        added += 1
    return added


def _report_answers(state: RunState) -> list[ReportAnswer]:
    return [
        ReportAnswer(index=sq.idx, text=sq.text, status=sq.status.value, answer=sq.answer)
        for sq in state.sub_questions
    ]


def _child_state(state: RunState, sq: SubQuestion, deps: LoopDeps) -> RunState:
    return RunState(
        run_id=RunId(uuid4()),
        tenant_id=state.tenant_id,
        user_id=state.user_id,
        workspace_id=state.workspace_id,
        query=sq.text,
        mode=RunMode.PRECISE,
        status=RunStatus.QUEUED,
        budget=state.budget,
        started_at=deps.clock.utcnow(),
    )


async def _answer_pending(state: RunState, deps: LoopDeps) -> None:
    for sq in state.sub_questions:
        if sq.status is not SubQuestionStatus.PENDING:
            continue
        sq.status = SubQuestionStatus.RUNNING
        child_deps = replace(deps, cycle_detector=CycleDetector())
        child = await run_precise(_child_state(state, sq, deps), child_deps)
        state.cost_usd += child.cost_usd
        state.total_tokens += child.total_tokens
        sq.answer = child.answer
        sq.child_run_id = child.run_id
        sq.status = (
            SubQuestionStatus.DONE
            if child.status is RunStatus.SUCCEEDED
            else SubQuestionStatus.FAILED
        )
        await deps.event_bus.emit(
            run_id=state.run_id,
            event=SubQuestionResolvedEvent(
                run_id=state.run_id,
                idx=sq.idx,
                status=sq.status.value,
                child_run_id=str(sq.child_run_id),
            ),
        )


async def _write_report(state: RunState, deps: LoopDeps, gap_round: int) -> None:
    prior = state.report.markdown if state.report else None
    out, resp = await report_writer.run(
        build_context(state, deps),
        ReportWriterPayload(query=state.query, answers=_report_answers(state), prior_report=prior),
    )
    account(state, resp)
    state.report = Report(
        markdown=out.markdown,
        sub_question_count=len(state.sub_questions),
        gap_rounds=gap_round,
    )
    await deps.event_bus.emit(
        run_id=state.run_id,
        event=ReportGeneratedEvent(
            run_id=state.run_id,
            sub_question_count=len(state.sub_questions),
            gap_rounds=gap_round,
        ),
    )


async def run_research(state: RunState, deps: LoopDeps) -> RunState:
    state.status = RunStatus.RUNNING
    state = await analyze(state, deps)
    state = await retrieve(state, deps)
    descriptions = [d.summary_text for d in state.descriptions]
    ctx = build_context(state, deps)

    sq_list, resp = await subquestion_generator.run(
        ctx, SubQGenPayload(query=state.query, descriptions=descriptions)
    )
    account(state, resp)
    added = _append_questions(state, sq_list)
    await deps.event_bus.emit(
        run_id=state.run_id,
        event=SubQuestionsGeneratedEvent(run_id=state.run_id, count=added, gap_round=0),
    )
    await _answer_pending(state, deps)
    await _write_report(state, deps, gap_round=0)

    for gap_round in range(1, state.budget.max_gap_rounds + 1):
        if len(state.sub_questions) >= state.budget.max_sub_questions:
            break
        gap_list, resp = await subquestion_generator.run(
            ctx,
            SubQGenPayload(
                query=state.query,
                descriptions=descriptions,
                existing_questions=[sq.text for sq in state.sub_questions],
                draft_report=state.report.markdown if state.report else None,
            ),
        )
        account(state, resp)
        if not gap_list.questions:
            break
        added = _append_questions(state, gap_list)
        await deps.event_bus.emit(
            run_id=state.run_id,
            event=SubQuestionsGeneratedEvent(run_id=state.run_id, count=added, gap_round=gap_round),
        )
        await _answer_pending(state, deps)
        await _write_report(state, deps, gap_round=gap_round)

    state.answer = state.report.markdown if state.report else ""
    state.status = RunStatus.SUCCEEDED
    state.finished_at = deps.clock.utcnow()
    await deps.event_bus.emit(
        run_id=state.run_id,
        event=RunFinishedEvent(
            run_id=state.run_id,
            answer=state.answer,
            cost_usd=state.cost_usd,
            total_tokens=state.total_tokens,
            total_rounds=0,
        ),
    )
    return state


__all__ = ["run_research"]
