"""route node — decide add-step vs backtrack after an insufficient verdict."""

from __future__ import annotations

from vera_core.agents import RouterPayload, router
from vera_core.loop.context import LoopDeps, account, build_context, numbered
from vera_core.models.events import RouteDecisionEvent
from vera_core.models.run import RunState


async def route(state: RunState, deps: LoopDeps) -> RunState:
    verdict = state.verdicts[-1]
    decision, response = await router.run(
        build_context(state, deps),
        RouterPayload(
            query=state.query,
            verdict_reason=verdict.reason,
            missing_aspects=list(verdict.missing_aspects),
            plan=numbered(state.active_plan),
        ),
    )
    account(state, response)
    state.routes.append(decision)

    await deps.event_bus.emit(
        run_id=state.run_id,
        event=RouteDecisionEvent(
            run_id=state.run_id,
            round=state.round,
            action=decision.action.value,
            backtrack_index=decision.backtrack_index,
            rationale=decision.rationale,
        ),
    )
    return state


__all__ = ["route"]
