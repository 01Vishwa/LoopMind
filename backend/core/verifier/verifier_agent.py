"""VerifierAgent — LLM judge that decides if the plan is sufficient.

Uses NVIDIA NIM (meta/llama-3.1-70b-instruct) with ``.with_structured_output``
for hard schema-compliance.  No format-instruction strings are injected —
the model is constrained at the API function-calling level.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

logger = logging.getLogger("uvicorn.info")


# ---------------------------------------------------------------------------
# Pydantic output schema
# ---------------------------------------------------------------------------

class VerifierOutput(BaseModel):
    """Structured sufficiency verdict from the LLM judge."""

    is_sufficient: bool = Field(
        description="True if the output fully answers the user query, False otherwise."
    )
    reason: str = Field(
        description="Concise explanation of why the plan is or is not sufficient."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 (no confidence) and 1.0 (certain).",
    )


# ---------------------------------------------------------------------------
# Prompts (no {format_instructions} injection needed)
# ---------------------------------------------------------------------------

_VERIFIER_SYSTEM = """\
You are a rigorous data science quality judge.
Evaluate whether the current analysis plan and its code execution results
are sufficient to answer the user's original query.

HARD FAILURE RULES (any of these means is_sufficient = False, no exceptions):
1. The execution output contains the word "Traceback", "Error", "Exception", or "raise" — this is a crash and is NEVER sufficient.
2. The execution output contains a bare "nan" or "NaN" result for a requested calculation (e.g., correlation) WITHOUT a printed explanation of why it is NaN. A silent NaN is a failure.
3. The code produced no output at all (empty or only whitespace).

Evaluation criteria (only apply if no hard failures above):
1. Does the output actually answer the user's query with concrete values or plots?
2. Did the code execute without any errors or warnings that affect correctness?
3. Are the results meaningful and based on real data from the description?
4. Is the analysis complete, or are important steps missing?

IMPORTANT: Be strict. A partial or error-prone result does NOT qualify as sufficient.
Only mark is_sufficient = True if the output clearly and correctly answers the user query.
"""

_VERIFIER_HUMAN = """\
USER QUERY:
{query}

DATA DESCRIPTION:
{data_description}

CURRENT ANALYSIS PLAN:
{plan_steps}

GENERATED CODE:
{code}

EXECUTION OUTPUT:
{execution_output}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class VerifierAgent:
    """Evaluates whether the current plan and its output satisfy the query.

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
            structured_llm = llm.with_structured_output(VerifierOutput)
            self._chain = (
                ChatPromptTemplate.from_messages([
                    ("system", _VERIFIER_SYSTEM),
                    ("human", _VERIFIER_HUMAN),
                ])
                | structured_llm
            )
        return self._chain

    async def verify(
        self,
        query: str,
        data_description: str,
        plan_steps: List[Dict[str, Any]],
        code: str,
        execution_output: str,
    ) -> Dict[str, Any]:
        """Runs the LLM judge and returns a typed verification result dict.

        Args:
            query: Original user query.
            data_description: Output of FileAnalyzerAgent.
            plan_steps: Current plan steps.
            code: The generated Python script.
            execution_output: Combined stdout/stderr from the executor.

        Returns:
            Dict with keys ``is_sufficient`` (bool), ``reason`` (str),
            ``confidence`` (float).
        """
        formatted_steps = "\n".join(
            f"  Step {s['index'] + 1}: {s['description']}"
            for s in plan_steps
        )

        # Trim large inputs to avoid context limit exhaustion
        trimmed_output = execution_output[:3000]
        trimmed_code = code[:4000]

        result: VerifierOutput = await self._get_chain().ainvoke({
            "query": query,
            "data_description": data_description,
            "plan_steps": formatted_steps,
            "code": trimmed_code,
            "execution_output": trimmed_output or "(no output)",
        })

        logger.info(
            "[Verifier] is_sufficient=%s, confidence=%.2f, reason=%s",
            result.is_sufficient,
            result.confidence,
            result.reason[:80],
        )

        return result.model_dump()
