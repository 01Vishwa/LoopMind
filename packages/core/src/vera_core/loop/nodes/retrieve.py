"""retrieve node — narrow the file descriptions to the query-relevant top-K."""

from __future__ import annotations

from vera_core.loop.context import LoopDeps
from vera_core.models.run import RunState


async def retrieve(state: RunState, deps: LoopDeps) -> RunState:
    results = await deps.retriever.search(
        query=state.query,
        workspace_id=state.workspace_id,
        top_k=deps.defaults.retriever_top_k,
    )
    if results:
        state.descriptions = list(results)
    return state


__all__ = ["retrieve"]
