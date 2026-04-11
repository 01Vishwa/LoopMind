"""PlannerAgent — creates and mutates the DS-STAR analysis plan.

Uses NVIDIA NIM with ``.with_structured_output`` for hard schema-compliance.

Gap fixes applied:
- Step cap raised from 8 → 12.
- Added ``remove_steps_from(index)`` mutation to support the Router's new
  REMOVE_STEPS action (matching the paper's plan-pruning diagram).
- Thread-safe chain caching via a simple instance lock.
- Task-type hint added to system prompt.
"""

import logging
import threading
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from core.token_tracker import TokenTracker, tracker_callback_config

logger = logging.getLogger("uvicorn.info")


# ---------------------------------------------------------------------------
# Pydantic output schemas
# ---------------------------------------------------------------------------

class PlanStep(BaseModel):
    """A single step in the analysis plan."""

    index: int = Field(description="Zero-based sequential index of this step.")
    description: str = Field(
        description="Clear, concrete description of the action."
    )
    status: str = Field(
        default="pending",
        description="Execution status: pending | done | failed.",
    )


class PlanOutput(BaseModel):
    """Full plan produced by the planner."""

    steps: List[PlanStep] = Field(
        description="Ordered list of analysis steps, max 12."
    )


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_INITIAL_PLAN_SYSTEM = (
    "You are an expert data science planner. "
    "Given a user query and a description of available data files, "
    "produce a concise step-by-step analysis plan.\n"
    "Rules:\n"
    "- Each step must be a single, concrete, executable action "
    "  (e.g. 'Load CSV into DataFrame', 'Filter rows where column > value').\n"
    "- Limit to at most 12 steps.\n"
    "- Steps must be ordered logically.\n"
    "- Do not include steps that cannot be performed on the available data.\n"
    "- Identify the task type first: "
    "  ML (train/predict), Wrangling (clean/transform), "
    "  Visualization (plot/chart), or Insight (answer a question).\n"
    "- Tailor steps to the task type: e.g., include train/test split for ML, "
    "  plt.savefig for Visualization, print() for Insight.\n"
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
    function-calling protocol level.
    """

    def __init__(
        self, model: Optional[str] = None, temperature: Optional[float] = None
    ) -> None:
        """Initialises the agent.

        Args:
            model: NIM model identifier; defaults to ``NIM_MODEL_DEFAULT``.
            temperature: Sampling temperature; defaults to 0.1 (deterministic).
        """
        self._model = model
        self._temperature = temperature if temperature is not None else 0.1
        self._chain = None
        self._lock = threading.Lock()   # thread-safe lazy init (matches PlannerAgent)

    def _get_chain(self):
        """Builds and caches the structured-output LangChain pipeline."""
        with self._lock:
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

    async def create_plan(
        self, query: str, data_description: str,
        token_tracker: Optional[TokenTracker] = None,
    ) -> List[Dict[str, Any]]:
        """Generates the initial plan from the query and data description.

        Args:
            query: The user's natural language question.
            data_description: Output of FileAnalyzerAgent.
            token_tracker: Optional run-level tracker.  When provided, token
                usage from this LLM call is recorded automatically via a
                LangChain callback.

        Returns:
            Ordered list of plan step dicts.

        Raises:
            Exception: Propagated to the orchestrator so ``_with_retry`` can
                retry on transient LLM failures. Do NOT catch here.
        """
        result: PlanOutput = await self._get_chain().ainvoke(
            {
                "query": query,
                "data_description": data_description,
            },
            config=tracker_callback_config(token_tracker),
        )
        steps = [s.model_dump() for s in result.steps]
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
        new_step = dict(new_step)
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
            replacement = dict(replacement)
            replacement["index"] = step_index
            replacement["status"] = "pending"
            updated[step_index] = replacement
            logger.info("[Planner] Fixed step %d.", step_index)
        return updated

    def remove_steps_from(
        self,
        steps: List[Dict[str, Any]],
        from_index: int,
        new_step: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Prunes all steps from ``from_index`` onward and appends a replacement.

        This implements the DS-STAR paper's plan-pruning operation (Router action
        REMOVE_STEPS).

        Args:
            steps: Existing plan steps.
            from_index: Zero-based index at which to start removing (inclusive).
            new_step: A replacement step to append after pruning.

        Returns:
            Pruned and reindexed steps with the replacement appended.
        """
        if from_index < 0 or from_index >= len(steps):
            # Invalid index — fall back to appending
            logger.warning(
                "[Planner] remove_steps_from: invalid index %d (plan has %d steps).",
                from_index,
                len(steps),
            )
            return self.add_step(steps, new_step)

        updated = list(steps[:from_index])
        new_step = dict(new_step)
        new_step.setdefault("status", "pending")
        updated.append(new_step)
        logger.info(
            "[Planner] Pruned steps from index %d; plan now has %d steps.",
            from_index,
            len(updated),
        )
        return self._reindex(updated)

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
