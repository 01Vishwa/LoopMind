"""plan node — extend the active plan with the planner's next steps."""

from __future__ import annotations

from vera_core.agents import PlannerPayload, planner
from vera_core.loop.context import LoopDeps, account, build_context
from vera_core.models.events import PlanUpdatedEvent
from vera_core.models.plan import PlanStep
from vera_core.models.run import AbandonedBranch, RunState


def _constraint(branch: AbandonedBranch) -> str:
    attempted = branch.removed_step_texts[0] if branch.removed_step_texts else ""
    return (
        f'Step {branch.from_index} previously attempted "{attempted}" and was '
        f'rejected because: "{branch.rationale}". Propose a different approach.'
    )


def _norm(text: str) -> str:
    return " ".join(text.split())


def _is_prefix(prefix: list[str], drafts: list[str]) -> bool:
    """Whitespace-insensitive prefix match on the planner's cumulative restatement.

    LEDGER: this is a fake-era bridge. It only holds while the planner faithfully
    restates the whole active plan verbatim; a single reworded step makes the match
    fail and appends every draft, duplicating the plan (and defeating the cycle
    detector, whose fingerprint then changes every round). Phase 4 must make the
    contract explicit in the planner prompt — either "restate the cumulative plan
    exactly" or "return only the new steps" — and this heuristic goes away.
    """
    normalised = [_norm(t) for t in prefix]
    return [_norm(d) for d in drafts[: len(prefix)]] == normalised


async def plan(state: RunState, deps: LoopDeps) -> RunState:
    abandoned = [_constraint(b) for b in state.abandoned_branches]
    last = state.last_observation
    output, response = await planner.run(
        build_context(state, deps),
        PlannerPayload(
            query=state.query,
            descriptions=[d.summary_text for d in state.descriptions],
            existing_steps=[s.text for s in state.active_plan],
            abandoned=abandoned,
            last_observation=last.stdout if last else None,
        ),
    )
    account(state, response)

    active_texts = [s.text for s in state.active_plan]
    draft_texts = [d.text for d in output.steps]
    new_drafts = (
        list(output.steps)[len(active_texts) :]
        if _is_prefix(active_texts, draft_texts)
        else list(output.steps)
    )
    max_index = max((s.index for s in state.plan), default=-1)
    new_steps = [
        PlanStep(
            index=max_index + 1 + offset,
            text=draft.text,
            acceptance_criteria=list(draft.acceptance_criteria),
            created_at_round=state.round,
        )
        for offset, draft in enumerate(new_drafts)
    ]
    state.plan = state.plan + new_steps

    await deps.event_bus.emit(
        run_id=state.run_id,
        event=PlanUpdatedEvent(
            run_id=state.run_id,
            round=state.round,
            steps=[s.text for s in state.active_plan],
        ),
    )
    return state


__all__ = ["plan"]
