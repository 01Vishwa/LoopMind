"""VERA agents — one structured LLM call each, driven by the loop nodes."""

from __future__ import annotations

from vera_core.agents._types import (
    CoderOutput,
    FinalizerOutput,
    PlannerOutput,
    PlanStepDraft,
)
from vera_core.agents.analyzer import AnalyzePayload, AnalyzerAgent, analyzer
from vera_core.agents.base import Agent, AgentContext
from vera_core.agents.coder import CoderAgent, CoderPayload, coder
from vera_core.agents.debugger import DebuggerAgent, DebuggerPayload, debugger
from vera_core.agents.finalizer import FinalizerAgent, FinalizerPayload, finalizer
from vera_core.agents.planner import PlannerAgent, PlannerPayload, planner
from vera_core.agents.router import RouterAgent, RouterPayload, router
from vera_core.agents.verifier import VerifierAgent, VerifierPayload, verifier

__all__ = [
    "Agent",
    "AgentContext",
    "AnalyzePayload",
    "AnalyzerAgent",
    "CoderAgent",
    "CoderOutput",
    "CoderPayload",
    "DebuggerAgent",
    "DebuggerPayload",
    "FinalizerAgent",
    "FinalizerOutput",
    "FinalizerPayload",
    "PlanStepDraft",
    "PlannerAgent",
    "PlannerOutput",
    "PlannerPayload",
    "RouterAgent",
    "RouterPayload",
    "VerifierAgent",
    "VerifierPayload",
    "analyzer",
    "coder",
    "debugger",
    "finalizer",
    "planner",
    "router",
    "verifier",
]
