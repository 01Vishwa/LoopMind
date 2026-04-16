"""DeepResearchOrchestrator — DS-STAR+ hierarchical research loop.

Implements the DS-STAR+ extension that handles open-ended research queries
by decomposing them into atomic sub-questions, running a full DS-STAR loop
for each sub-question in parallel, then aggregating the results into a
structured research report.

Flow:
    1. Detect open-ended query (or always run in research mode when called).
    2. FileAnalyzerAgent: build data description.
    3. SubQuestionGeneratorAgent: decompose query into atomic sub-questions.
    4. Parallel DS-STAR runs (max_workers=3, concurrency-controlled).
    5. ReportWriterAgent: aggregate into structured markdown report.
    6. Emit SSE events throughout for frontend streaming.
    7. Persist report + sub-question links to Supabase.
"""

import asyncio
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from core.analyzer.file_analyzer import FileAnalyzerAgent
from core.ds_star_orchestrator import DsStarOrchestrator, _event, _ms_since
from core.ds_star_plus.subquestion_agent import SubQuestionGeneratorAgent
from core.ds_star_plus.report_writer_agent import ReportWriterAgent
from core.retrieval.retriever import Retriever
from core.config import DS_STAR_PLUS_MAX_WORKERS, MAX_AGENT_ROUNDS

logger = logging.getLogger("uvicorn.info")


# ---------------------------------------------------------------------------
# Open-ended query classifier
# ---------------------------------------------------------------------------

_RESEARCH_KEYWORDS = frozenset({
    "report", "research", "summarise", "summarize", "overview", "analyse",
    "analyze", "explore", "investigate", "comprehensive", "deep dive",
    "findings", "insights", "trends", "patterns", "compare", "contrast",
    "relationship", "correlation", "across", "between", "profile",
})


def is_open_ended(query: str) -> bool:
    """Returns True if the query is open-ended and suited for DS-STAR+.

    Uses keyword heuristics only. The word-count heuristic has been removed
    because it incorrectly routed ordinary analytical questions (>15 words)
    into the expensive parallel DS-STAR+ pipeline. Research mode can be
    forced explicitly by calling the research endpoint directly, or via the
    UI research-mode toggle (AgentSettings).

    Args:
        query: The user's natural language query.

    Returns:
        True if the query contains research-oriented keywords.
    """
    lower = query.lower()
    words = set(lower.split())
    return bool(words & _RESEARCH_KEYWORDS)


# ---------------------------------------------------------------------------
# Sub-question DS-STAR runner helper
# ---------------------------------------------------------------------------

async def _run_single_ds_star(
    question: str,
    context: Dict[str, Any],
    model: Optional[str],
    coder_model: Optional[str],
    temperature: Optional[float],
    max_rounds: int,
    sub_run_id: str,
    session_id: str = "__anon__",
) -> Dict[str, Any]:
    """Runs a complete DS-STAR loop for one sub-question and returns its result.

    Args:
        question: The atomic sub-question to answer.
        context: Processing context passed from the research endpoint.
        model: LLM model override (Pro tier).
        coder_model: LLM model override for code generation.
        temperature: Sampling temperature override.
        max_rounds: Maximum orchestrator rounds per sub-question.
        sub_run_id: Unique run ID for this sub-question run.
        session_id: Client session identifier — scopes executor file access so
            sub-runs see only this session's uploaded files, not __anon__ bucket.

    Returns:
        Dict containing status, execution_output, insights, code, rounds, run_id.
    """
    orchestrator = DsStarOrchestrator(
        max_rounds=max_rounds,
        model=model,
        coder_model=coder_model,
        temperature=temperature,
    )

    result: Dict[str, Any] = {
        "status": "failed",
        "execution_output": "",
        "insights": {},
        "code": "",
        "rounds": 0,
        "run_id": sub_run_id,
    }

    try:
        async for event in orchestrator.run(
            question, context, run_id=sub_run_id, session_id=session_id
        ):
            event_type = event.get("event")
            payload = event.get("payload", {})
            if event_type == "completed":
                result["status"] = "completed"
                result["insights"] = payload.get("insights", {})
                result["code"] = payload.get("code", {}).get("Python", "")
                result["rounds"] = payload.get("rounds", 0)
                exec_out = payload.get("insights", {}).get("summary", "")
                result["execution_output"] = exec_out
            elif event_type == "execution_result":
                # Capture raw stdout from the last successful execution
                if payload.get("success"):
                    result["execution_output"] = payload.get("stdout", "")
            elif event_type == "metrics":
                final_status = payload.get("metrics", {}).get("final_status", "")
                if final_status == "max_rounds_reached":
                    result["status"] = "max_rounds_reached"
            elif event_type == "error":
                result["status"] = "failed"
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(
            "[DeepResearch] Sub-question DS-STAR failed | run_id=%s: %s",
            sub_run_id,
            exc,
        )
        result["status"] = "failed"
        result["execution_output"] = str(exc)

    return result


# ---------------------------------------------------------------------------
# Deep Research Orchestrator
# ---------------------------------------------------------------------------

class DeepResearchOrchestrator:
    """Runs the DS-STAR+ deep research loop and streams progress events.

    Decomposes an open-ended research query into atomic sub-questions,
    executes a DS-STAR loop per sub-question (concurrently, up to
    ``max_workers``), then synthesises results via ReportWriterAgent.

    Attributes:
        analyzer: FileAnalyzerAgent for building data descriptions.
        subq_agent: SubQuestionGeneratorAgent for query decomposition.
        report_writer: ReportWriterAgent for report synthesis.
        retriever: Retriever for top-K file selection on large corpora.
        _max_rounds: Max orchestrator rounds for each sub-question DS-STAR run.
        _max_workers: Max parallel DS-STAR runs.
    """

    def __init__(
        self,
        max_rounds: Optional[int] = None,
        model: Optional[str] = None,
        coder_model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_workers: Optional[int] = None,
    ) -> None:
        """Initialises the deep research orchestrator.

        Args:
            max_rounds: Maximum DS-STAR rounds per sub-question.
            model: LLM model identifier for Pro-tier agents.
            coder_model: LLM model identifier for code generation.
            temperature: LLM sampling temperature.
            max_workers: Maximum parallel DS-STAR sub-executions.
        """
        self._max_rounds = max_rounds or MAX_AGENT_ROUNDS
        self._model = model
        self._coder_model = coder_model
        self._temperature = temperature
        self._max_workers = max_workers or DS_STAR_PLUS_MAX_WORKERS
        self.analyzer = FileAnalyzerAgent()
        self.subq_agent = SubQuestionGeneratorAgent()
        self.report_writer = ReportWriterAgent()
        self.retriever = Retriever()

    async def run(
        self,
        query: str,
        context: Dict[str, Any],
        report_id: str = "",
        session_id: str = "__anon__",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Executes the DS-STAR+ research loop and yields SSE events.

        Args:
            query: The user's open-ended research query.
            context: Processing context from /process endpoint,
                including ``combined_extractions`` and ``files_processed``.
            report_id: Unique report identifier for Supabase persistence.
            session_id: Client session identifier — forwarded to all
                sub-question DS-STAR runs so their executors access the
                correct session file bucket instead of ``__anon__``.

        Yields:
            AgentEvent dicts for SSE streaming.
        """
        run_t0 = time.monotonic()
        report_id = report_id or uuid.uuid4().hex
        combined = context.get("combined_extractions", {})

        yield _event(
            "research_started",
            message="DS-STAR+ deep research mode initiated.",
            report_id=report_id,
        )

        # ── Stage 1: File Analysis ────────────────────────────────────────────
        yield _event("analyzing", message="Analyzing data files for research context…")
        try:
            data_description = self.analyzer.analyze(combined)
            yield _event(
                "analysis_complete",
                message="Data analysis complete.",
                data_description=data_description,
            )
        except Exception as exc:  # pylint: disable=broad-except
            data_description = f"Data description unavailable: {exc}"
            yield _event("warning", message=f"File analysis error: {exc}")

        # Retrieval: filter to top-K relevant files for large corpora
        filtered_combined = self.retriever.retrieve_combined_extractions(
            query=query,
            combined_extractions=combined,
        )
        filtered_count = len(filtered_combined)
        if filtered_count < len(combined):
            yield _event(
                "retrieval_complete",
                message=(
                    f"Retrieval filtered {len(combined)} → {filtered_count} "
                    f"most relevant files."
                ),
                selected_files=list(filtered_combined.keys()),
            )
            # Use filtered context for sub-question runs
            context = {**context, "combined_extractions": filtered_combined}

        # ── Stage 2: Sub-Question Generation ─────────────────────────────────
        yield _event(
            "generating_subquestions",
            message="Decomposing query into atomic sub-questions…",
        )
        try:
            sub_questions: List[str] = await self.subq_agent.generate(
                query=query,
                data_summary=data_description,
            )
            yield _event(
                "subquestions_ready",
                message=f"Generated {len(sub_questions)} sub-questions.",
                sub_questions=sub_questions,
                count=len(sub_questions),
            )
            logger.info(
                "[DeepResearch] report_id=%s | %d sub-questions generated",
                report_id,
                len(sub_questions),
            )
        except Exception as exc:  # pylint: disable=broad-except
            yield _event("error", message=f"SubQuestion generation failed: {exc}")
            return

        # ── Stage 3: Parallel DS-STAR Runs ────────────────────────────────────
        yield _event(
            "running_subquestions",
            message=(
                f"Running {len(sub_questions)} DS-STAR analyses "
                f"(max_workers={self._max_workers})…"
            ),
            total=len(sub_questions),
        )

        sub_run_ids = [uuid.uuid4().hex for _ in sub_questions]

        # Semaphore-controlled concurrency
        semaphore = asyncio.Semaphore(self._max_workers)

        async def _run_with_semaphore(i: int, question: str) -> Dict[str, Any]:
            async with semaphore:
                yield_event = _event(
                    "subquestion_started",
                    message=f"[Q{i + 1}] Running: {question[:80]}",
                    index=i,
                    question=question,
                    sub_run_id=sub_run_ids[i],
                )
                logger.info(
                    "[DeepResearch] Q%d started | run_id=%s", i + 1, sub_run_ids[i]
                )
                result = await _run_single_ds_star(
                    question=question,
                    context=context,
                    model=self._model,
                    coder_model=self._coder_model,
                    temperature=self._temperature,
                    max_rounds=self._max_rounds,
                    sub_run_id=sub_run_ids[i],
                    session_id=session_id,
                )
                logger.info(
                    "[DeepResearch] Q%d done | status=%s | run_id=%s",
                    i + 1,
                    result["status"],
                    sub_run_ids[i],
                )
                return yield_event, result

        # Run all sub-questions concurrently under semaphore
        tasks = [
            asyncio.create_task(_run_with_semaphore(i, q))
            for i, q in enumerate(sub_questions)
        ]

        results: List[Dict[str, Any]] = [None] * len(sub_questions)  # type: ignore[assignment]
        for coro in asyncio.as_completed(tasks):
            start_event, sub_result = await coro
            idx = sub_run_ids.index(sub_result["run_id"])
            results[idx] = sub_result

            # Emit start event (may be slightly delayed but ordering is acceptable)
            yield start_event
            yield _event(
                "subquestion_complete",
                message=(
                    f"Sub-question '{sub_questions[idx][:60]}…' — "
                    f"status: {sub_result['status']}"
                ),
                index=idx,
                status=sub_result["status"],
                sub_run_id=sub_result["run_id"],
            )

        yield _event(
            "all_subquestions_complete",
            message=f"All {len(sub_questions)} sub-questions completed.",
            statuses=[r["status"] for r in results],
        )

        # ── Stage 4: Report Writing ───────────────────────────────────────────
        yield _event("writing_report", message="Synthesising research report…")
        try:
            report = await self.report_writer.write(
                query=query,
                sub_questions=sub_questions,
                results=results,
            )
            total_ms = int((time.monotonic() - run_t0) * 1000)
            yield _event(
                "research_complete",
                message="DS-STAR+ research report ready.",
                report_id=report_id,
                title=report.get("title", ""),
                executive_summary=report.get("executive_summary", ""),
                report_body=report.get("report_body", ""),
                key_findings=report.get("key_findings", []),
                caveats=report.get("caveats", []),
                sub_questions=sub_questions,
                sub_run_ids=sub_run_ids,
                total_ms=total_ms,
            )
            logger.info(
                "[DeepResearch] report_id=%s complete | %d findings | %d caveats | %dms",
                report_id,
                len(report.get("key_findings", [])),
                len(report.get("caveats", [])),
                total_ms,
            )
        except Exception as exc:  # pylint: disable=broad-except
            yield _event("error", message=f"ReportWriter failed: {exc}")
            logger.error(
                "[DeepResearch] report_id=%s | ReportWriter error: %s",
                report_id,
                exc,
            )
