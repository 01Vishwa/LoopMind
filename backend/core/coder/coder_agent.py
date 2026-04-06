"""CoderAgent — translates the current plan into executable Python.

Uses NVIDIA NIM (meta/codellama-70b-instruct) with ``.with_structured_output``
for hard schema-compliance.  No format-instruction strings are injected —
the model is constrained at the API function-calling level.

Artifact-output instructions are baked into the system prompt.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

logger = logging.getLogger("uvicorn.info")


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
# Prompts (no {format_instructions} needed)
# ---------------------------------------------------------------------------

_CODER_SYSTEM = """\
You are an expert Python data scientist.
Your task is to generate a single, self-contained Python script that implements the analysis plan below.

Rules for the Python script:
- Use pandas, json, matplotlib, and standard library only.
- The script must print a clear, human-readable final answer or result summary.
- Handle missing values and errors gracefully.
- Use only the data described in the DATA DESCRIPTION.
- Simulate file reading using the data content from the description if actual files are unavailable.
- Do NOT use external APIs or network calls.
- Include comments explaining each major section.
- The script must be fully runnable without any arguments.

CRITICAL — NEVER try to open or read raw files from disk:
- Do NOT call open(), pd.read_csv('filename.csv'), pd.read_excel('filename.xlsx'),
  json.load(open(...)), or ANY function that reads a file by its original name.
- The DATA DESCRIPTION above already contains all the data you need (columns, sample rows,
  full text content). Use that content directly in your script.
- For CSV/XLSX documents: reconstruct the DataFrame using pd.DataFrame with the sample rows
  from the description, or use io.StringIO with the content preview.
- For PDF/TXT/MD documents: use the "Full Text Content" from the description as a Python string.
- The execution sandbox is a temp directory that does NOT contain any of the original files.

IMPORTANT — NumPy compatibility (MANDATORY):
- NEVER use deprecated NumPy type aliases: np.object, np.int, np.float, np.bool, np.complex, np.str.
- Instead use built-in Python types (object, int, float, bool) or explicit NumPy dtypes: np.object_, np.int64, np.float64, np.bool_, np.complex128.

IMPORTANT — Robust data handling (MANDATORY):
- Before any numeric calculation, coerce columns: pd.to_numeric(df['col'], errors='coerce').
- Before correlation or statistical operations, always drop NaN rows: df.dropna(subset=['col1', 'col2']).
- Before computing correlation, ALWAYS check for zero variance:
    if df['col1'].std() == 0 or df['col2'].std() == 0:
        print("Cannot compute correlation: one or more columns have zero variance (all values identical).")
    else:
        print(df[['col1', 'col2']].corr())
- If a calculation produces NaN, print an explicit explanation of WHY (e.g., zero variance, all-null column, insufficient non-null pairs).
- NEVER silently output NaN as the final result — always explain it.

IMPORTANT — Artifact output:
- Save ALL plots using: plt.savefig('./outputs/<descriptive_name>.png', dpi=100, bbox_inches='tight')
- Save ALL DataFrames using: df.to_csv('./outputs/<descriptive_name>.csv', index=False)
- NEVER call plt.show().
- The ./outputs/ directory is pre-created; write directly into it.
"""

_CODER_HUMAN = """\
USER QUERY:
{query}

DATA DESCRIPTION:
{data_description}

ANALYSIS PLAN:
{plan_steps}

PREVIOUS CODE (if any):
{previous_code}

LAST EXECUTION OUTPUT (if any):
{execution_output}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class CoderAgent:
    """Translates plan steps into a runnable Python script via NIM CodeLlama.

    Uses ``.with_structured_output`` to enforce schema compliance at the
    function-calling protocol level — no JSON format instructions injected.
    """

    def __init__(self, model: Optional[str] = None, temperature: Optional[float] = None) -> None:
        """Initialises the agent.  The LLM chain is built lazily on first use.

        Args:
            model: NIM model identifier; defaults to ``NIM_MODEL_CODER``.
            temperature: Sampling temperature; defaults to 0.1.
        """
        self._model = model
        self._temperature = temperature if temperature is not None else 0.1
        self._chain = None  # lazily built by _get_chain()

    def _get_chain(self):
        """Builds and caches the structured-output LangChain pipeline using the coder LLM."""
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
    ) -> str:
        """Generates a Python script implementing the analysis plan.

        Args:
            query: The user's natural language question.
            data_description: Output of FileAnalyzerAgent.
            plan_steps: Current plan steps.
            previous_code: Code from the previous round (if any).
            execution_output: stdout/stderr from the previous execution.

        Returns:
            A self-contained Python script as a string.
        """
        formatted_steps = "\n".join(
            f"  Step {s['index'] + 1}: {s['description']}"
            for s in plan_steps
        )

        result: CodeOutput = await self._get_chain().ainvoke({
            "query": query,
            "data_description": data_description,
            "plan_steps": formatted_steps,
            "previous_code": previous_code or "(none)",
            "execution_output": execution_output or "(none)",
        })
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
