"""debug node — ask the debugger for a corrected replacement script."""

from __future__ import annotations

import hashlib

from vera_core.agents import DebuggerPayload, debugger
from vera_core.loop.context import LoopDeps, account, build_context, max_active_index
from vera_core.models.code import CodeArtifact
from vera_core.models.events import DebugAttemptEvent
from vera_core.models.run import RunState


async def debug(state: RunState, deps: LoopDeps) -> RunState:
    state.debug_attempts += 1
    broken = state.script
    last = state.last_observation
    output, response = await debugger.run(
        build_context(state, deps),
        DebuggerPayload(
            code=broken.source if broken else "",
            stderr=last.stderr if last else "",
        ),
    )
    account(state, response)

    source = output.source
    sha256 = hashlib.sha256(source.encode()).hexdigest()
    state.script = CodeArtifact(
        source=source,
        sha256=sha256,
        parent_sha256=broken.sha256 if broken else None,
    )
    # Refresh the checkpoint the `code` node wrote for this round, so a later
    # backtrack resumes from the *fixed* script rather than the broken original.
    state.script_checkpoints[max_active_index(state)] = state.script

    await deps.event_bus.emit(
        run_id=state.run_id,
        event=DebugAttemptEvent(
            run_id=state.run_id, round=state.round, attempt=state.debug_attempts
        ),
    )
    return state


__all__ = ["debug"]
