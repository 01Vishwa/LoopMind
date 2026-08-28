"""vera_core policies — pure decision functions with no I/O."""

from __future__ import annotations

from vera_core.policies.backtrack import active_steps, apply_backtrack
from vera_core.policies.context_budget import ContextBudget
from vera_core.policies.cycle_detection import CycleDetector, plan_fingerprint
from vera_core.policies.termination import check_budget, is_terminal_status, should_terminate
from vera_core.policies.truncation import (
    DEFAULT_STDERR_CAP,
    DEFAULT_STDOUT_CAP,
    truncate_observation,
)

__all__ = [
    "DEFAULT_STDERR_CAP",
    "DEFAULT_STDOUT_CAP",
    "ContextBudget",
    "CycleDetector",
    "active_steps",
    "apply_backtrack",
    "check_budget",
    "is_terminal_status",
    "plan_fingerprint",
    "should_terminate",
    "truncate_observation",
]
