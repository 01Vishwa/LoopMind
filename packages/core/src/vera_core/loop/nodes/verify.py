"""verify node — judge whether the latest observation answers the question."""

from __future__ import annotations

from vera_core.agents import VerifierPayload, verifier
from vera_core.loop.context import LoopDeps, account, build_context, numbered
from vera_core.models.events import VerifyVerdictEvent
from vera_core.models.run import RunState


async def verify(state: RunState, deps: LoopDeps) -> RunState:
    last = state.last_observation
    verdict, response = await verifier.run(
        build_context(state, deps),
        VerifierPayload(
            query=state.query,
            plan=numbered(state.active_plan),
            code=state.script.source if state.script else "",
            observation=last.stdout if last else "",
        ),
    )
    account(state, response)
    state.verdicts.append(verdict)

    await deps.event_bus.emit(
        run_id=state.run_id,
        event=VerifyVerdictEvent(
            run_id=state.run_id,
            round=state.round,
            sufficient=verdict.sufficient,
            reason=verdict.reason,
            missing_aspects=list(verdict.missing_aspects),
        ),
    )
    return state


__all__ = ["verify"]
