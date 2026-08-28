"""``vera run`` — execute the DS-STAR loop (fake-LLM only until Phase 4)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from vera_core.models.run import RunState

SUPPORTED = {".csv", ".json", ".xlsx", ".parquet", ".md", ".txt", ".pdf", ".sqlite", ".zip"}

_SCENARIOS = {"happy": "happy_path", "multiround": "multi_round", "backtrack": "backtrack"}


def run(
    workspace: Annotated[
        Path, typer.Option(exists=True, file_okay=False, help="Workspace directory")
    ],
    query: Annotated[str, typer.Option(help="Natural-language question")],
    fake_llm: Annotated[
        bool, typer.Option("--fake-llm", help="Run against scripted fakes")
    ] = False,
    scenario: Annotated[str, typer.Option(help="happy | multiround | backtrack")] = "backtrack",
    max_rounds: Annotated[int, typer.Option(help="Round budget")] = 10,
) -> None:
    """Run the precise analysis loop over a workspace."""
    if not fake_llm:
        typer.echo("Real LLM execution requires Phase 4. Use --fake-llm.")
        raise typer.Exit(1)
    if scenario not in _SCENARIOS:
        typer.echo(f"Unknown scenario {scenario!r}. Choose one of: {', '.join(_SCENARIOS)}.")
        raise typer.Exit(2)

    file_count = sum(1 for p in workspace.iterdir() if p.suffix.lower() in SUPPORTED)
    result = asyncio.run(_run_fake(scenario, query, max_rounds))

    backtracks = len(result.abandoned_branches)
    suffix = f" ({backtracks} backtracked)" if backtracks else ""
    typer.echo(f"Analyzed {file_count} files")
    typer.echo(f"Plan: {len(result.active_plan)} steps{suffix}")
    typer.echo(f"Rounds: {result.round}")
    typer.echo(f"Backtracks: {backtracks}")
    typer.echo(f"Cost: ${result.cost_usd:.4f}   Tokens: {result.total_tokens}")
    typer.echo(f"Answer: {result.answer}")


async def _run_fake(scenario: str, query: str, max_rounds: int) -> RunState:
    import vera_testing.scenarios as scenarios
    from vera_core.loop import LoopDeps, run_precise
    from vera_core.policies import CycleDetector
    from vera_core.ports.clock import FixedClock
    from vera_core.prompts import PromptRegistry
    from vera_testing.factories.domain import make_agent_defaults
    from vera_testing.fakes import FakeEventBus

    sc = getattr(scenarios, _SCENARIOS[scenario])()
    state = sc.state
    state.query = query
    state.budget = state.budget.model_copy(update={"max_rounds": max_rounds})
    deps = LoopDeps(
        llm=sc.llm,
        sandbox=sc.sandbox,
        retriever=sc.retriever,
        event_bus=FakeEventBus(),
        clock=FixedClock(datetime.now(UTC)),
        defaults=make_agent_defaults(),
        registry=PromptRegistry(),
        file_refs=[],
        mounts=[],
        cycle_detector=CycleDetector(max_repeats=3),
    )
    return await run_precise(state, deps)


__all__ = ["run"]
