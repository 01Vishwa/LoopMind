"""VERA agents — one structured LLM call each, driven by the loop nodes."""

from __future__ import annotations

from vera_core.agents._types import (
    AnalyzerScriptOutput,
    CoderOutput,
    FinalizerOutput,
    PlannerOutput,
    PlanStepDraft,
    ReportOutput,
    SubQuestionList,
)
from vera_core.agents.analyzer import AnalyzePayload, AnalyzerAgent, analyzer
from vera_core.agents.base import Agent, AgentContext
from vera_core.agents.coder import CoderAgent, CoderPayload, coder
from vera_core.agents.debugger import DebuggerAgent, DebuggerPayload, debugger
from vera_core.agents.finalizer import FinalizerAgent, FinalizerPayload, finalizer
from vera_core.agents.planner import PlannerAgent, PlannerPayload, planner
from vera_core.agents.report_writer import (
    ReportAnswer,
    ReportWriterAgent,
    ReportWriterPayload,
    report_writer,
)
from vera_core.agents.router import RouterAgent, RouterPayload, router
from vera_core.agents.subquestion_generator import (
    SubQGenPayload,
    SubQuestionGeneratorAgent,
    subquestion_generator,
)
from vera_core.agents.verifier import VerifierAgent, VerifierPayload, verifier

__all__ = [
    "Agent",
    "AgentContext",
    "AnalyzePayload",
    "AnalyzerAgent",
    "AnalyzerScriptOutput",
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
    "ReportAnswer",
    "ReportOutput",
    "ReportWriterAgent",
    "ReportWriterPayload",
    "RouterAgent",
    "RouterPayload",
    "SubQGenPayload",
    "SubQuestionGeneratorAgent",
    "SubQuestionList",
    "VerifierAgent",
    "VerifierPayload",
    "analyzer",
    "coder",
    "debugger",
    "finalizer",
    "planner",
    "report_writer",
    "router",
    "subquestion_generator",
    "verifier",
]
