"""execute node — run the current script in the sandbox and record the observation."""

from __future__ import annotations

from vera_core.errors import AgentOutputError, SandboxTimeoutError
from vera_core.loop.context import LoopDeps, max_active_index
from vera_core.models.events import ExecutionFinishedEvent, ExecutionStartedEvent
from vera_core.models.observation import Observation
from vera_core.models.run import RunState
from vera_core.policies import truncate_observation
from vera_core.ports.sandbox import ResourceLimits


async def execute(state: RunState, deps: LoopDeps) -> RunState:
    if state.script is None:
        raise AgentOutputError("execute node reached with no script on the state")

    await deps.event_bus.emit(
        run_id=state.run_id,
        event=ExecutionStartedEvent(run_id=state.run_id, round=state.round),
    )

    limits = ResourceLimits()
    try:
        observation = await deps.sandbox.execute(
            script=state.script,
            mounts=deps.mounts,
            limits=limits,
            run_id=state.run_id,
        )
    except SandboxTimeoutError:
        observation = Observation(
            stdout="",
            stderr="timeout",
            exit_code=124,
            duration_ms=limits.timeout_s * 1000,
        )

    capped = truncate_observation(observation)
    state.observations.append(capped)
    state.observation_checkpoints[max_active_index(state)] = capped

    await deps.event_bus.emit(
        run_id=state.run_id,
        event=ExecutionFinishedEvent(
            run_id=state.run_id,
            round=state.round,
            exit_code=capped.exit_code,
            duration_ms=capped.duration_ms,
            truncated=capped.truncated,
        ),
    )
    return state


__all__ = ["execute"]
