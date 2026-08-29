"""CLI coverage for ``vera run`` against the scripted fake loop."""

from __future__ import annotations

from typer.testing import CliRunner
from vera_cli.main import app

runner = CliRunner()


def test_run_without_fake_llm_exits_1(tmp_path):
    r = runner.invoke(app, ["run", "--workspace", str(tmp_path), "--query", "q"])
    assert r.exit_code == 1
    assert "Phase 4" in r.output


def test_run_happy_scenario(tmp_path):
    r = runner.invoke(
        app,
        [
            "run",
            "--workspace",
            "fixtures/payments",
            "--query",
            "Total chargeback amount?",
            "--fake-llm",
            "--scenario",
            "happy",
        ],
    )
    assert r.exit_code == 0, r.output
    assert "Analyzed 3 files" in r.output
    assert "Plan: 2 steps" in r.output
    assert "1250" in r.output


def test_run_backtrack_scenario(tmp_path):
    r = runner.invoke(
        app,
        [
            "run",
            "--workspace",
            "fixtures/payments",
            "--query",
            "Total chargeback amount?",
            "--fake-llm",
            "--scenario",
            "backtrack",
        ],
    )
    assert r.exit_code == 0, r.output
    assert "backtrack" in r.output.lower()
    assert "(1 backtracked)" in r.output
    assert "Answer:" in r.output
    assert "1250" in r.output


def test_run_research_mode_prints_report(tmp_path):
    r = runner.invoke(
        app,
        [
            "run",
            "--workspace",
            "fixtures/payments",
            "--query",
            "Analyse chargeback exposure",
            "--fake-llm",
            "--mode",
            "research",
        ],
    )
    assert r.exit_code == 0, r.output
    assert "Sub-questions: 3" in r.output
    assert "Gap rounds: 1" in r.output
    assert "[SQ-" in r.output
