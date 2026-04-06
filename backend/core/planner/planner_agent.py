"""PlannerAgent — creates and mutates the DS-STAR analysis plan.

Uses NVIDIA NIM (meta/llama-3.1-70b-instruct) with ``.with_structured_output``
for hard schema-compliance via function-calling.  No format-instruction strings
are injected into the prompt — the model is constrained at the API level.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

logger = logging.getLogger("uvicorn.info")


# ---------------------------------------------------------------------------
# Pydantic output schemas
# ---------------------------------------------------------------------------

class PlanStep(BaseModel):
    """A single step in the analysis plan."""

    index: int = Field(description="Zero-based sequential index of this step.")
    description: str = Field(description="Clear, concrete description of the action.")
    status: str = Field(default="pending", description="Execution status: pending | done | failed.")


class PlanOutput(BaseModel):
    """Full plan produced by the planner."""

    steps: List[PlanStep] = Field(description="Ordered list of analysis steps, max 8.")


# ---------------------------------------------------------------------------
# Prompts (no {format_instructions} injection needed)
# ---------------------------------------------------------------------------

_INITIAL_PLAN_SYSTEM = (
    "You are an expert data science planner. "
    "Given a user query and a description of available data files, "
    "produce a concise step-by-step analysis plan.\n"
    "Rules:\n"
    "- Each step must be a single, concrete, executable action "
    "  (e.g. 'Load CSV into DataFrame', 'Filter rows where column > value').\n"
    "- Limit to at most 8 steps.\n"
    "- Steps must be ordered logically.\n"
    "- Do not include steps that cannot be performed on the available data.\n"
)

_INITIAL_PLAN_HUMAN = (
    "USER QUERY:\n{query}\n\n"
    "DATA DESCRIPTION:\n{data_description}"
)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class PlannerAgent:
    """Creates and mutates a Pydantic-validated analysis plan via NIM.

    Uses ``.with_structured_output`` to enforce schema compliance at the
    function-calling protocol level — no JSON format instructions injected.
    """

    def __init__(self, model: Optional[str] = None, temperature: Optional[float] = None) -> None:
        """Initialises the agent.  The LLM chain is built lazily on first use.

        Args:
            model: NIM model identifier; defaults to ``NIM_MODEL_DEFAULT``.
            temperature: Sampling temperature; defaults to 0.1 (deterministic).
        """
        self._model = model
        self._temperature = temperature if temperature is not None else 0.1
        self._chain = None  # lazily built by _get_chain()

    def _get_chain(self):
        """Builds and caches the structured-output LangChain pipeline on first call."""
        if self._chain is None:
            from core.llm_client import get_nim_llm  # pylint: disable=import-outside-toplevel
            llm = get_nim_llm(model=self._model, temperature=self._temperature)
            structured_llm = llm.with_structured_output(PlanOutput)
            self._chain = (
                ChatPromptTemplate.from_messages([
                    ("system", _INITIAL_PLAN_SYSTEM),
                    ("human", _INITIAL_PLAN_HUMAN),
                ])
                | structured_llm
            )
        return self._chain

    async def create_plan(self, query: str, data_description: str) -> List[Dict[str, Any]]:
        """Generates the initial plan from the query and data description.

        Args:
            query: The user's natural language question.
            data_description: Output of FileAnalyzerAgent.

        Returns:
            Ordered list of plan step dicts.
        """
        try:
            result: PlanOutput = await self._get_chain().ainvoke({
                "query": query,
                "data_description": data_description,
            })
            steps = [s.model_dump() for s in result.steps]
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("[Planner] LLM/parse error (%s); using fallback plan.", exc)
            steps = [
                {"index": 0, "description": "Load and inspect all data files.", "status": "pending"},
                {"index": 1, "description": "Perform analysis relevant to the query.", "status": "pending"},
                {"index": 2, "description": "Summarize and format the final answer.", "status": "pending"},
            ]

        logger.info("[Planner] Created plan with %d steps.", len(steps))
        return steps

    def add_step(
        self, steps: List[Dict[str, Any]], new_step: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Appends a new step to the plan and reindexes all steps.

        Args:
            steps: Existing plan steps.
            new_step: The new step dict to append.

        Returns:
            Updated steps with consistent indices.
        """
        updated = list(steps)
        new_step["index"] = len(updated)
        new_step.setdefault("status", "pending")
        updated.append(new_step)
        return self._reindex(updated)

    def fix_step(
        self,
        steps: List[Dict[str, Any]],
        step_index: int,
        replacement: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Replaces a specific step with a corrected version.

        Args:
            steps: Existing plan steps.
            step_index: Zero-based index of the step to replace.
            replacement: The replacement step dict.

        Returns:
            Updated steps.
        """
        updated = list(steps)
        if 0 <= step_index < len(updated):
            replacement["index"] = step_index
            replacement["status"] = "pending"
            updated[step_index] = replacement
            logger.info("[Planner] Fixed step %d.", step_index)
        return updated

    def _reindex(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Reassigns sequential indices to all steps.

        Args:
            steps: Steps to reindex.

        Returns:
            Steps with corrected indices.
        """
        for i, step in enumerate(steps):
            step["index"] = i
        return steps
