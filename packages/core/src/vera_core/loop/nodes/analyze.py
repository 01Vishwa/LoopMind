"""analyze node — summarise each workspace file into a FileDescription."""

from __future__ import annotations

from vera_core.agents import AnalyzePayload, analyzer
from vera_core.loop.context import LoopDeps, account, build_context
from vera_core.models.events import AnalysisStartedEvent, FileAnalyzedEvent
from vera_core.models.run import RunState


async def analyze(state: RunState, deps: LoopDeps) -> RunState:
    await deps.event_bus.emit(
        run_id=state.run_id,
        event=AnalysisStartedEvent(run_id=state.run_id, file_count=len(deps.file_refs)),
    )
    for ref in deps.file_refs:
        description, response = await analyzer.run(
            build_context(state, deps),
            AnalyzePayload(
                file_id=str(ref.file_id),
                filename=ref.filename,
                kind=ref.kind.value,
                sample="",
            ),
        )
        account(state, response)
        state.descriptions.append(description)
        await deps.event_bus.emit(
            run_id=state.run_id,
            event=FileAnalyzedEvent(
                run_id=state.run_id,
                file_id=str(description.file_id),
                filename=ref.filename,
                row_count=description.row_count,
            ),
        )
    return state


__all__ = ["analyze"]
