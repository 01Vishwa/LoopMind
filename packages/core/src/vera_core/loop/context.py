"""Loop dependencies and small helpers shared by the nodes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from vera_core.agents.base import AgentContext
from vera_core.models.agent_config import AgentDefaults
from vera_core.models.file import FileRef
from vera_core.models.plan import PlanStep
from vera_core.models.run import RunState
from vera_core.policies import CycleDetector
from vera_core.ports.clock import ClockPort
from vera_core.ports.event_bus import EventBusPort
from vera_core.ports.llm import LLMPort, LLMResponse
from vera_core.ports.retriever import RetrieverPort
from vera_core.ports.sandbox import DataMount, SandboxPort
from vera_core.prompts import PromptRegistry


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


def numbered(steps: Sequence[PlanStep]) -> list[str]:
    """Render plan steps as ``"<absolute index>: <text>"`` for prompt injection.

    The router answers with an absolute :attr:`PlanStep.index`, not a position in
    the active plan. After a backtrack the active plan has gaps (e.g. indices
    ``[0, 2, 3]``), so the two diverge — every prompt that can influence
    ``RouterDecision.backtrack_index`` must show the absolute index.
    """
    return [f"{s.index}: {s.text}" for s in steps]


__all__ = ["LoopDeps", "account", "build_context", "max_active_index", "numbered"]
