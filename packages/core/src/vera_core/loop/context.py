"""Loop dependencies and small helpers shared by the nodes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from vera_core.agents.base import AgentContext
from vera_core.errors import SandboxTimeoutError
from vera_core.models.agent_config import AgentDefaults
from vera_core.models.code import CodeArtifact
from vera_core.models.file import FileKind, FileRef
from vera_core.models.ids import RunId
from vera_core.models.observation import Observation
from vera_core.models.plan import PlanStep
from vera_core.models.run import RunState
from vera_core.policies import CycleDetector
from vera_core.ports.clock import ClockPort
from vera_core.ports.event_bus import EventBusPort
from vera_core.ports.llm import LLMPort, LLMResponse
from vera_core.ports.retriever import RetrieverPort
from vera_core.ports.sandbox import DataMount, ResourceLimits, SandboxPort
from vera_core.prompts import PromptRegistry

_BINARY_KINDS = frozenset(
    {FileKind.XLSX, FileKind.PARQUET, FileKind.SQLITE, FileKind.ZIP, FileKind.PDF}
)
_ANALYZER_TIMEOUT_S = 30


@dataclass(frozen=True)
class LoopDeps:
    """Everything the DS-STAR loop needs from the outside world."""

    llm: LLMPort
    sandbox: SandboxPort
    retriever: RetrieverPort
    event_bus: EventBusPort
    clock: ClockPort
    defaults: AgentDefaults
    registry: PromptRegistry
    file_refs: list[FileRef]
    mounts: list[DataMount]
    cycle_detector: CycleDetector


def build_context(state: RunState, deps: LoopDeps) -> AgentContext:
    """Construct the per-call agent context from loop state and deps."""
    return AgentContext(
        llm=deps.llm,
        defaults=deps.defaults,
        registry=deps.registry,
        run_id=state.run_id,
    )


def account(state: RunState, response: LLMResponse) -> None:
    """Fold one LLM response's cost and token usage into the run state."""
    state.cost_usd += response.cost_usd or Decimal("0")
    state.total_tokens += response.input_tokens + response.output_tokens


def max_active_index(state: RunState) -> int:
    """Highest index among non-superseded plan steps (0 when the plan is empty)."""
    return max((s.index for s in state.active_plan), default=0)


def mount_for(ref: FileRef, mounts: list[DataMount]) -> DataMount | None:
    """The mount whose basename matches ``ref.filename`` (container or host side)."""
    for m in mounts:
        if Path(m.container_path).name == ref.filename or Path(m.host_path).name == ref.filename:
            return m
    return None


def read_sample(ref: FileRef, mounts: list[DataMount], max_bytes: int = 8192) -> str:
    """First ``max_bytes`` of the file as text; ``''`` for binary kinds or an unmatched ref."""
    if ref.kind in _BINARY_KINDS:
        return ""
    mount = mount_for(ref, mounts)
    if mount is None:
        return ""
    try:
        with open(mount.host_path, "rb") as fh:
            raw = fh.read(max_bytes)
    except OSError:
        return ""
    return raw.decode("utf-8", errors="replace")


async def execute_analyzer_script(
    sandbox: SandboxPort, script: CodeArtifact, mount: DataMount, run_id: RunId
) -> Observation:
    """Run one analyzer parser script against one file's mount, 30s cap.

    A :class:`SandboxTimeoutError` becomes a synthetic failed observation so the
    caller's retry/fallback logic treats a timeout like any other crash.
    """
    try:
        return await sandbox.execute(
            script=script,
            mounts=[mount],
            limits=ResourceLimits(timeout_s=_ANALYZER_TIMEOUT_S),
            run_id=run_id,
        )
    except SandboxTimeoutError:
        return Observation(
            stdout="", stderr="timeout", exit_code=124, duration_ms=_ANALYZER_TIMEOUT_S * 1000
        )


def numbered(steps: Sequence[PlanStep]) -> list[str]:
    """Render plan steps as ``"<absolute index>: <text>"`` for prompt injection.

    The router answers with an absolute :attr:`PlanStep.index`, not a position in
    the active plan. After a backtrack the active plan has gaps (e.g. indices
    ``[0, 2, 3]``), so the two diverge — every prompt that can influence
    ``RouterDecision.backtrack_index`` must show the absolute index.
    """
    return [f"{s.index}: {s.text}" for s in steps]


__all__ = [
    "LoopDeps",
    "account",
    "build_context",
    "execute_analyzer_script",
    "max_active_index",
    "mount_for",
    "numbered",
    "read_sample",
]
