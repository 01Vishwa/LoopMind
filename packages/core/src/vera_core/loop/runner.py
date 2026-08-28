"""run_precise — the explicit DS-STAR control loop over the pure nodes."""

from __future__ import annotations

from vera_core.loop.context import LoopDeps
from vera_core.loop.edges import (
    debug_outcome,
    execution_outcome,
    route_outcome,
    verify_outcome,
)
from vera_core.loop.nodes import (
    analyze,
    code,
    debug,
    execute,
    finalize,
    plan,
    retrieve,
    route,
    truncate,
    verify,
)
from vera_core.models.run import RunState, RunStatus


async def run_precise(state: RunState, deps: LoopDeps) -> RunState:
    state.status = RunStatus.RUNNING

    state = await analyze(state, deps)
    state = await retrieve(state, deps)

    while True:
        # The debug budget is per round, not per run: a fresh script deserves a
        # fresh allowance even if an earlier round used all of its attempts.
        state.debug_attempts = 0
        state = await plan(state, deps)
        deps.cycle_detector.record(state.active_plan)
        if deps.cycle_detector.is_cycling():
            return await finalize(state, deps, degraded=True)

        state = await code(state, deps)
        state = await execute(state, deps)

        outcome = execution_outcome(state)
        if outcome == "crash":
            while execution_outcome(state) == "crash":
                if debug_outcome(state) == "max_retries":
                    return await finalize(state, deps, degraded=True)
                state = await debug(state, deps)
                state = await execute(state, deps)
            if execution_outcome(state) == "budget":
                return await finalize(state, deps, degraded=True)
        elif outcome == "budget":
            return await finalize(state, deps, degraded=True)

        state.round += 1
        state = await verify(state, deps)
        vo = verify_outcome(state)
        if vo in ("sufficient", "max_rounds"):
            return await finalize(state, deps, degraded=(vo == "max_rounds"))

        state = await route(state, deps)
        ro = route_outcome(state, deps.cycle_detector)
        if ro == "backtrack":
            state = await truncate(state, deps)


__all__ = ["run_precise"]
