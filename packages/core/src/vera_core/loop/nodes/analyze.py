"""analyze node — generate a parser script per file, execute it, parse the stdout.

Two-step DS-STAR mechanism (agent-spec §3.3): the Analyzer never describes a file
directly — it writes a Python script, the sandbox runs it, and its stdout is the
ground-truth structural profile. A crash gets at most two Debugger fixes
(agent-spec §3.8); after that we fall back to a columns-only partial description
built from the raw sample.
"""

from __future__ import annotations

import hashlib

from vera_core.agents import AnalyzePayload, analyzer
from vera_core.agents.debugger import DebuggerPayload, debugger
from vera_core.loop.context import (
    LoopDeps,
    account,
    build_context,
    execute_analyzer_script,
    mount_for,
    read_sample,
)
from vera_core.models.code import CodeArtifact
from vera_core.models.events import AnalysisStartedEvent, FileAnalyzedEvent
from vera_core.models.run import RunState
from vera_core.policies import build_partial_description, parse_analyzer_stdout

ANALYZER_MAX_DEBUG_ATTEMPTS = 2


def _artifact(source: str, parent: str | None = None) -> CodeArtifact:
    return CodeArtifact(
        source=source,
        sha256=hashlib.sha256(source.encode()).hexdigest(),
        parent_sha256=parent,
    )


async def analyze(state: RunState, deps: LoopDeps) -> RunState:
    await deps.event_bus.emit(
        run_id=state.run_id,
        event=AnalysisStartedEvent(run_id=state.run_id, file_count=len(deps.file_refs)),
    )
    ctx = build_context(state, deps)

    for ref in deps.file_refs:
        sample = read_sample(ref, deps.mounts)
        mount = mount_for(ref, deps.mounts)

        script_out, resp = await analyzer.run(
            ctx,
            AnalyzePayload(
                file_id=str(ref.file_id),
                filename=ref.filename,
                kind=ref.kind.value,
                sample=sample,
            ),
        )
        account(state, resp)
        script = _artifact(script_out.source)

        observation = (
            await execute_analyzer_script(deps.sandbox, script, mount, state.run_id)
            if mount is not None
            else None
        )

        attempts = 0
        while (
            mount is not None
            and observation is not None
            and not observation.succeeded
            and attempts < ANALYZER_MAX_DEBUG_ATTEMPTS
        ):
            attempts += 1
            fix_out, resp = await debugger.run(
                ctx, DebuggerPayload(code=script.source, stderr=observation.stderr)
            )
            account(state, resp)
            script = _artifact(fix_out.source, parent=script.sha256)
            observation = await execute_analyzer_script(deps.sandbox, script, mount, state.run_id)

        if observation is not None and observation.succeeded:
            description = parse_analyzer_stdout(ref.file_id, observation.stdout)
        else:
            description = build_partial_description(ref.file_id, sample)

        state.descriptions.append(description)
        await deps.event_bus.emit(
            run_id=state.run_id,
            event=FileAnalyzedEvent(
                run_id=state.run_id,
                file_id=str(ref.file_id),
                filename=ref.filename,
                row_count=description.row_count,
                partial=description.partial,
            ),
        )

    return state


__all__ = ["ANALYZER_MAX_DEBUG_ATTEMPTS", "analyze"]
