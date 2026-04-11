"""CoderAgent — translates the current plan into executable Python.

Uses NVIDIA NIM with ``.with_structured_output`` for hard schema-compliance.

Gap fixes applied:
- Coder prompt reframed as accumulative/sequential (DS-STAR "Colab notebook"
  model): the agent EXTENDS the previous script, not rewrites it from scratch.
- Task-type routing added: coder adapts output mode to ML / Wrangling /
  Visualization / Insight.
- execution_output capped at 3 000 chars before being sent to the LLM.
- Defensive strip of markdown fences retained.
"""

import logging
import threading
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from core.token_tracker import TokenTracker, tracker_callback_config

logger = logging.getLogger("uvicorn.info")

# Maximum chars of execution output passed to the coder
_MAX_EXEC_OUTPUT_CHARS = 3_000


# ---------------------------------------------------------------------------
# Pydantic output schema
# ---------------------------------------------------------------------------

class CodeOutput(BaseModel):
    """Generated Python script output."""

    code: str = Field(
        description=(
            "Complete, self-contained Python script. "
            "No markdown fences, no explanations — raw Python only."
        )
    )


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_CODER_SYSTEM = """\
You are an expert Python data scientist working like a Jupyter/Colab notebook.

Your task is to generate a single, self-contained Python script that implements
the CURRENT analysis plan.

EXECUTION MODEL — Read this carefully:
- If PREVIOUS CODE is provided, you are in a refinement round.
- You must EXTEND the previous script by adding NEW sections at the end,
  OR correct a broken section.  Do NOT discard working code.
- The script runs from top to bottom each round, so all imports and data-loading
  stay at the top; new analysis blocks go at the end.

TASK TYPE OUTPUT MODES:
- Insight / Data Analysis: print() final numeric answers clearly.
- Visualization: save plots with plt.savefig('./outputs/<name>.png', dpi=100, bbox_inches='tight')
- Data Wrangling: save cleaned data with df.to_csv('./outputs/<name>.csv', index=False)
- Machine Learning: save the model with joblib.dump(model, './outputs/model.joblib')
  AND print metrics (accuracy, RMSE, etc.)

GENERAL RULES:
- Use pandas, json, matplotlib, sklearn, joblib, and standard library only.
- Read files by filename — files are pre-injected into the working directory.
- NEVER call plt.show(). The ./outputs/ directory is pre-created.
- Handle missing values gracefully with pd.to_numeric(..., errors='coerce').
- NEVER use deprecated NumPy aliases: np.object, np.int, np.float, np.bool.
  Use built-in types or np.object_, np.int64, np.float64, np.bool_.
- Before correlation/statistics, check for zero variance:
    if df['col'].std() == 0: print("Zero variance — cannot compute correlation")
- If a result is NaN, always print WHY (zero variance, all-null, etc.).
- The script must print a clear final answer or summary as the last action.

IMPORTANT — Robust data handling:
- Coerce numerics: pd.to_numeric(df['col'], errors='coerce')
- Drop NaN before stats: df.dropna(subset=['col1', 'col2'])
- NEVER silently output NaN as the final result.
"""

_CODER_HUMAN = """\
USER QUERY:
{query}

DATA DESCRIPTION:
{data_description}

CURRENT ANALYSIS PLAN:
{plan_steps}

PREVIOUS CODE (extend this — do not discard working sections):
{previous_code}

LAST EXECUTION OUTPUT (errors to fix are highlighted here):
{execution_output}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class CoderAgent:
    """Translates plan steps into a runnable Python script via NIM.

    Uses ``.with_structured_output`` to enforce schema compliance at the
    function-calling protocol level.
    """

    def __init__(
        self, model: Optional[str] = None, temperature: Optional[float] = None
    ) -> None:
        """Initialises the agent.

        Args:
            model: NIM model identifier; defaults to ``NIM_MODEL_CODER``.
            temperature: Sampling temperature; defaults to 0.1.
        """
        self._model = model
        self._temperature = temperature if temperature is not None else 0.1
        self._chain = None  # lazily built
        self._lock = threading.Lock()  # thread-safe lazy init

    def _get_chain(self):
        """Builds and caches the structured-output LangChain pipeline."""
        with self._lock:
            if self._chain is None:
                from core.llm_client import get_nim_llm  # pylint: disable=import-outside-toplevel
                from core.config import NIM_MODEL_CODER  # pylint: disable=import-outside-toplevel
                resolved = self._model or NIM_MODEL_CODER
                llm = get_nim_llm(model=resolved, temperature=self._temperature)
                structured_llm = llm.with_structured_output(CodeOutput)
                self._chain = (
                    ChatPromptTemplate.from_messages([
                        ("system", _CODER_SYSTEM),
                        ("human", _CODER_HUMAN),
                    ])
                    | structured_llm
                )
        return self._chain

    async def generate_code(
        self,
        query: str,
        data_description: str,
        plan_steps: List[Dict[str, Any]],
        previous_code: str = "",
        execution_output: str = "",
        token_tracker: Optional[TokenTracker] = None,
    ) -> str:
        """Generates a Python script implementing the analysis plan.

        Args:
            query: The user's natural language question.
            data_description: Output of FileAnalyzerAgent.
            plan_steps: Current plan steps.
            previous_code: Code from the previous round (if any).
            execution_output: stdout/stderr from the previous execution.
            token_tracker: Optional run-level tracker.  When provided, token
                usage from this LLM call is recorded automatically via a
                LangChain callback.

        Returns:
            A self-contained Python script as a string.
        """
        formatted_steps = "\n".join(
            f"  Step {s['index'] + 1}: {s['description']}"
            for s in plan_steps
        )

        # Cap execution output passed to coder to avoid context window exhaustion
        trimmed_exec = execution_output[:_MAX_EXEC_OUTPUT_CHARS] if execution_output else "(none)"

        result: CodeOutput = await self._get_chain().ainvoke(
            {
                "query": query,
                "data_description": data_description,
                "plan_steps": formatted_steps,
                "previous_code": previous_code or "(none — this is round 1, write from scratch)",
                "execution_output": trimmed_exec,
            },
            config=tracker_callback_config(token_tracker),
        )
        code = result.code

        # Strip accidental markdown fences (defensive)
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )

        logger.info("[Coder] Generated code (%d chars).", len(code))
        return code.strip()
