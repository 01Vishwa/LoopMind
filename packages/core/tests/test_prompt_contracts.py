"""Load-bearing instructional content + StrictUndefined render-smoke for every
non-analyzer agent template."""

from __future__ import annotations

import pytest
from vera_core.prompts import PromptRegistry

REG = PromptRegistry()

_SMOKE_VARS: dict[str, dict[str, object]] = {
    "planner": {
        "query": "q",
        "descriptions": ["payments.csv: merchant_id, amount"],
        "existing_steps": ["Load payments.csv"],
        "abandoned": ["Step 0 attempted X, rejected because Y"],
        "last_observation": "TOTAL: 1250.00",
    },
    "coder": {
        "query": "q",
        "plan": ["Load payments.csv", "Sum amount"],
        "last_stdout": "prev output",
        "last_stderr": None,
        "prior_script": "import pandas as pd\ndf = pd.read_csv('payments.csv')",
    },
    "verifier": {"query": "q", "plan": ["0: load"], "code": "print(1)", "observation": "1"},
    "router": {
        "query": "q",
        "verdict_reason": "wrong join",
        "missing_aspects": ["join key"],
        "plan": ["0: load", "2: join"],
    },
    "debugger": {"code": "print(x)", "stderr": "NameError: name 'x' is not defined"},
    "finalizer": {
        "query": "q",
        "plan": ["0: load"],
        "observation": "TOTAL 1250",
        "degraded": False,
    },
}


def _src(agent: str) -> str:
    return REG.get(agent).source


# ── planner ──────────────────────────────────────────────────────────────────


def test_planner_renders_with_all_vars() -> None:
    out = REG.get("planner").render(**_SMOKE_VARS["planner"])
    assert "Load payments.csv" in out
    assert "TOTAL: 1250.00" in out


def test_planner_renders_with_empty_lists_and_no_observation() -> None:
    REG.get("planner").render(
        query="q", descriptions=[], existing_steps=[], abandoned=[], last_observation=None
    )


def test_planner_demands_verbatim_cumulative_restatement() -> None:
    src = _src("planner")
    assert "verbatim" in src
    assert "rather than restating" not in src  # the old bug: contradicted _is_prefix


def test_planner_asks_for_only_the_next_step() -> None:
    src = _src("planner").lower()
    assert "next" in src and "step" in src


# ── coder ────────────────────────────────────────────────────────────────────


def test_coder_renders_with_all_vars() -> None:
    out = REG.get("coder").render(**_SMOKE_VARS["coder"])
    assert "pd.read_csv('payments.csv')" in out


def test_coder_renders_without_prior_script() -> None:
    REG.get("coder").render(
        query="q", plan=[], last_stdout=None, last_stderr=None, prior_script=None
    )


def test_coder_forbids_try_except_and_asks_to_build_on_base() -> None:
    src = _src("coder")
    assert "try/except" in src
    assert "BUILD ON THIS" in src
    assert 'open("payments.csv")' in src or "current working directory" in src


# ── verifier / router / debugger / finalizer ─────────────────────────────────


@pytest.mark.parametrize("agent", ["verifier", "router", "debugger", "finalizer"])
def test_template_renders_under_strict_undefined(agent: str) -> None:
    REG.get(agent).render(**_SMOKE_VARS[agent])


def test_verifier_is_deterministic_and_judges_the_output() -> None:
    src = _src("verifier")
    assert "temperature 0" in src
    assert "OUTPUT" in src  # judge the output, not just the code


def test_router_uses_lowercase_enum_values_and_worked_examples() -> None:
    src = _src("router")
    assert '"add_step"' in src and '"backtrack"' in src
    assert "ADD_STEP" not in src and "BACKTRACK" not in src  # the old bug
    assert "merchant_id" in src  # a concrete worked example (agent-spec §7.7)


def test_debugger_returns_complete_script_and_names_keyerror_fix() -> None:
    src = _src("debugger")
    assert "COMPLETE" in src
    assert "KeyError" in src


def test_finalizer_specifies_number_formatting() -> None:
    src = _src("finalizer").lower()
    assert "two decimal" in src or "2 decimal" in src
    assert "%" in src


# ── DS-STAR+ research templates ──────────────────────────────────────────────


def test_subquestion_generator_template_renders_both_modes() -> None:
    initial = REG.get("subquestion_generator").render(
        query="q", descriptions=["f.csv"], existing_questions=[], draft_report=None
    )
    gap = REG.get("subquestion_generator").render(
        query="q", descriptions=["f.csv"], existing_questions=["Q1"], draft_report="# Draft"
    )
    assert "data-grounded" in initial.lower()
    assert "GAP" in gap.upper()


def test_report_writer_template_renders_both_modes() -> None:
    class _A:
        def __init__(self, i: int, s: str) -> None:
            self.index, self.text, self.status, self.answer = i, "Q", s, "A"

    draft = REG.get("report_writer").render(query="q", answers=[_A(1, "done")], prior_report=None)
    refine = REG.get("report_writer").render(
        query="q", answers=[_A(2, "failed")], prior_report="# Prior"
    )
    assert "[SQ-" in draft
    assert "UNRESOLVED" in draft
    assert "Prior" in refine
