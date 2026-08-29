"""The DS-STAR agent loop — precise (StateGraph) and research (orchestrator) modes."""

from __future__ import annotations

from vera_core.loop.context import LoopDeps
from vera_core.loop.research import run_research
from vera_core.loop.runner import run_precise
from vera_core.models.run import RunMode, RunState


async def run(state: RunState, deps: LoopDeps) -> RunState:
    """Dispatch a run to the loop that matches its mode."""
    if state.mode is RunMode.RESEARCH:
        return await run_research(state, deps)
    return await run_precise(state, deps)


__all__ = ["LoopDeps", "run", "run_precise", "run_research"]
