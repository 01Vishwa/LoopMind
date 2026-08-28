"""truncate node — roll plan, script, and observations back to a backtrack index."""

from __future__ import annotations

from vera_core.loop.context import LoopDeps
from vera_core.models.run import AbandonedBranch, RunState
from vera_core.policies import apply_backtrack


async def truncate(state: RunState, deps: LoopDeps) -> RunState:
    decision = state.routes[-1]
    j = decision.backtrack_index
    if j is None:
        return state

    active_indices = [s.index for s in state.active_plan]
    if not active_indices:
        return state
    if j not in active_indices:
        # A hallucinated / stale index must never escape as an uncaught ValueError
        # from apply_backtrack. Clamp to the earliest active step: discarding more
        # than the router asked for is recoverable, crashing the run is not.
        j = min(active_indices)

    pre_sha = state.script.sha256 if state.script else None
    removed_step_texts = [s.text for s in state.active_plan if s.index >= j]

    apply_backtrack(state, j)

    # Checkpoints are written once per round, keyed by that round's max active
    # index, so the keys are sparse and `j - 1` is a key only by luck. Resume from
    # the newest checkpoint that predates the discarded branch.
    prev_key = max((k for k in state.script_checkpoints if k < j), default=None)
    state.script = state.script_checkpoints.get(prev_key) if prev_key is not None else None
    state.observations = [
        state.observation_checkpoints[i] for i in sorted(state.observation_checkpoints) if i < j
    ]
    for key in [k for k in state.script_checkpoints if k >= j]:
        del state.script_checkpoints[key]
    for key in [k for k in state.observation_checkpoints if k >= j]:
        del state.observation_checkpoints[key]

    state.abandoned_branches.append(
        AbandonedBranch(
            round=state.round,
            from_index=j,
            removed_step_texts=removed_step_texts,
            removed_script_sha=pre_sha,
            rationale=decision.rationale,
        )
    )
    state.debug_attempts = 0
    return state


__all__ = ["truncate"]
