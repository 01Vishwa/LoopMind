"""code node — generate the script for the current active plan."""

from __future__ import annotations

import hashlib

from vera_core.agents import CoderPayload, coder
from vera_core.loop.context import LoopDeps, account, build_context, max_active_index
from vera_core.models.code import CodeArtifact
from vera_core.models.events import CodeGeneratedEvent
from vera_core.models.run import RunState


async def code(state: RunState, deps: LoopDeps) -> RunState:
    last = state.last_observation
    output, response = await coder.run(
        build_context(state, deps),
        CoderPayload(
            query=state.query,
            plan=[s.text for s in state.active_plan],
            last_stdout=last.stdout if last else None,
            last_stderr=last.stderr if last else None,
        ),
    )
    account(state, response)

    source = output.source
    sha256 = hashlib.sha256(source.encode()).hexdigest()
    parent_sha256 = state.script.sha256 if state.script else None
    state.script = CodeArtifact(source=source, sha256=sha256, parent_sha256=parent_sha256)
    state.script_checkpoints[max_active_index(state)] = state.script

    await deps.event_bus.emit(
        run_id=state.run_id,
        event=CodeGeneratedEvent(
            run_id=state.run_id, round=state.round, sha256=sha256, language="python"
        ),
    )
    return state


__all__ = ["code"]
