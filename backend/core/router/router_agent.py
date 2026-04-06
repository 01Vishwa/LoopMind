"""RouterAgent — decides how to refine an insufficient plan.

Uses NVIDIA NIM (meta/llama-3.1-70b-instruct) with ``.with_structured_output``
for hard schema-compliance.  No format-instruction strings are injected —
the model is constrained at the API function-calling level.
"""

import logging
from typing import Any, Dict, List, Literal, Optional

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

logger = logging.getLogger("uvicorn.info")


# ---------------------------------------------------------------------------
# Pydantic output schema
# ---------------------------------------------------------------------------

class StepDetail(BaseModel):
    """A single plan step payload (index/status added by the orchestrator)."""

    description: str = Field(
        description="Clear, specific description of what this step should do."
    )


class RouterOutput(BaseModel):
    """Routing decision from the LLM optimizer."""

    action: Literal["ADD_STEP", "FIX_STEP"] = Field(
        description=(
            "ADD_STEP to append a new step at the end, "
            "FIX_STEP to replace an existing broken step."
        )
    )
    step_index: Optional[int] = Field(
        default=None,
        description=(
            "Zero-based index of the step to fix "
            "(required for FIX_STEP, null for ADD_STEP)."
        ),
    )
    new_step: StepDetail = Field(description="The new or replacement step content.")


# ---------------------------------------------------------------------------
# Prompts (no {format_instructions} injection needed)
# ---------------------------------------------------------------------------

_ROUTER_SYSTEM = """\
You are a data science plan optimizer.
The current analysis plan was judged as INSUFFICIENT.
Your job is to decide the best way to fix it.

Choose ONE of the following actions:
- "ADD_STEP": Add a new step at the end of the plan.
- "FIX_STEP": Replace an existing step that is incorrect or incomplete.
"""

_ROUTER_HUMAN = """\
USER QUERY:
{query}

DATA DESCRIPTION:
{data_description}

CURRENT PLAN STEPS:
{plan_steps}

VERIFIER FEEDBACK:
{verifier_reason}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class RouterAgent:
    """Decides and produces the plan mutation needed after a failed verification.

    Uses ``.with_structured_output`` to enforce schema compliance at the
    function-calling protocol level — no JSON format instructions injected.
    """

    def __init__(self, model: Optional[str] = None, temperature: Optional[float] = None) -> None:
        """Initialises the agent.  The LLM chain is built lazily on first use.

        Args:
            model: NIM model identifier; defaults to ``NIM_MODEL_DEFAULT``.
            temperature: Sampling temperature; defaults to 0.1.
        """
        self._model = model
        self._temperature = temperature if temperature is not None else 0.1
        self._chain = None  # lazily built by _get_chain()

    def _get_chain(self):
        """Builds and caches the structured-output LangChain pipeline on first call."""
        if self._chain is None:
            from core.llm_client import get_nim_llm  # pylint: disable=import-outside-toplevel
            llm = get_nim_llm(model=self._model, temperature=self._temperature)
            structured_llm = llm.with_structured_output(RouterOutput)
            self._chain = (
                ChatPromptTemplate.from_messages([
                    ("system", _ROUTER_SYSTEM),
                    ("human", _ROUTER_HUMAN),
                ])
                | structured_llm
            )
        return self._chain

    async def route(
        self,
        query: str,
        data_description: str,
        plan_steps: List[Dict[str, Any]],
        verifier_reason: str,
    ) -> Dict[str, Any]:
        """Generates a routing decision to refine the plan.

        Args:
            query: Original user query.
            data_description: Output of FileAnalyzerAgent.
            plan_steps: Current plan steps.
            verifier_reason: Explanation from VerifierAgent.

        Returns:
            Dict with keys ``action`` (str), ``step_index`` (int|None),
            ``new_step`` (Dict).
        """
        formatted_steps = "\n".join(
            f"  Step {s['index'] + 1}: {s['description']}"
            for s in plan_steps
        )

        result: RouterOutput = await self._get_chain().ainvoke({
            "query": query,
            "data_description": data_description,
            "plan_steps": formatted_steps,
            "verifier_reason": verifier_reason,
        })

        logger.info(
            "[Router] Decision: action=%s, step_index=%s, new_step=%s",
            result.action,
            result.step_index,
            result.new_step.description[:60],
        )

        return {
            "action": result.action,
            "step_index": result.step_index,
            "new_step": result.new_step.model_dump(),
        }
