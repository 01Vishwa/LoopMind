"""The DS-STAR agent loop — hand-rolled async state machine over RunState."""

from __future__ import annotations

from vera_core.loop.context import LoopDeps
from vera_core.loop.runner import run_precise

__all__ = ["LoopDeps", "run_precise"]
