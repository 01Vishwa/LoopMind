"""finalize node — write the final answer and close out the run."""

from __future__ import annotations

from vera_core.agents import FinalizerPayload, finalizer
from vera_core.loop.context import LoopDeps, account, build_context, numbered
from vera_core.models.events import RunFailedEvent, RunFinishedEvent
from vera_core.models.run import RunState, RunStatus


async def finalize(state: RunState, deps: LoopDeps, *, degraded: bool = False) -> RunState:
    last = state.last_observation
    output, response = await finalizer.run(
        build_context(state, deps),
        FinalizerPayload(
            query=state.query,
            plan=numbered(state.active_plan),
            observation=last.stdout if last else "",
            degraded=degraded,
        ),
    )
    account(state, response)

    state.answer = output.answer
    # Degraded with no *usable* observation is a failure: a run whose every
    # execution crashed must not be reported green (spec §5.3).
    usable = any(o.succeeded for o in state.observations)
    state.status = RunStatus.FAILED if degraded and not usable else RunStatus.SUCCEEDED
    state.finished_at = deps.clock.utcnow()

    if state.status is RunStatus.FAILED:
        state.error = "run degraded: no successful execution"
        await deps.event_bus.emit(
            run_id=state.run_id,
            event=RunFailedEvent(run_id=state.run_id, round=state.round, error=state.error),
        )
    else:
        await deps.event_bus.emit(
            run_id=state.run_id,
            event=RunFinishedEvent(
                run_id=state.run_id,
                round=state.round,
                answer=output.answer,
                cost_usd=state.cost_usd,
                total_tokens=state.total_tokens,
                total_rounds=state.round,
            ),
        )
    return state


__all__ = ["finalize"]
