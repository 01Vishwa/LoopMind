"""run_precise — the DS-STAR control loop compiled as a LangGraph StateGraph.

The graph is the single source of control flow; every node body in
``loop/nodes/*.py`` and every predicate in ``loop/edges.py`` is reused
unchanged. Round bookkeeping the old hand-rolled ``while`` loop did inline
(``round += 1``, ``debug_attempts = 0``, ``cycle_detector.record``) lives in
three thin wrappers here so the nodes stay pure.
"""

from __future__ import annotations

from functools import partial
from typing import Literal

from langgraph.graph import END, START, StateGraph

from vera_core.loop.context import LoopDeps
from vera_core.loop.edges import after_execute, route_outcome, verify_outcome
from vera_core.loop.nodes import (
    analyze,
    code,
    debug,
    execute,
    finalize,
    plan,
    retrieve,
    route,
    truncate,
    verify,
)
from vera_core.models.run import RunBudget, RunState, RunStatus


def _recursion_limit(budget: RunBudget) -> int:
    """Super-step ceiling generous enough for the worst-case multi-round + backtrack run.

    langgraph 1.x defaults to 25, which a real multi-round run exceeds.
    """
    return 2 + budget.max_rounds * (8 + 2 * budget.max_debug_attempts) + 10


def _build_graph(deps: LoopDeps):  # type: ignore[no-untyped-def]  # CompiledStateGraph generic is unstable across 1.x
    async def _plan_step(state: RunState) -> RunState:
        state.debug_attempts = 0
        state = await plan(state, deps)
        deps.cycle_detector.record(state.active_plan)
        return state

    async def _verify_step(state: RunState) -> RunState:
        # Only reachable via ``after_execute == "verify"`` — the exact point the
        # old loop did ``round += 1`` (execution ultimately succeeded).
        state.round += 1
        return await verify(state, deps)

    def _after_plan(state: RunState) -> Literal["cycle", "ok"]:
        return "cycle" if deps.cycle_detector.is_cycling() else "ok"

    def _after_route(state: RunState) -> Literal["backtrack", "add_step"]:
        return route_outcome(state, deps.cycle_detector)

    g = StateGraph(RunState)
    g.add_node("analyze", partial(analyze, deps=deps))
    g.add_node("retrieve", partial(retrieve, deps=deps))
    g.add_node("plan", _plan_step)
    g.add_node("code", partial(code, deps=deps))
    g.add_node("execute", partial(execute, deps=deps))
    g.add_node("debug", partial(debug, deps=deps))
    g.add_node("verify", _verify_step)
    g.add_node("route", partial(route, deps=deps))
    g.add_node("truncate", partial(truncate, deps=deps))
    g.add_node("finalize_ok", partial(finalize, deps=deps, degraded=False))
    g.add_node("finalize_degraded", partial(finalize, deps=deps, degraded=True))

    g.add_edge(START, "analyze")
    g.add_edge("analyze", "retrieve")
    g.add_edge("retrieve", "plan")
    g.add_conditional_edges("plan", _after_plan, {"cycle": "finalize_degraded", "ok": "code"})
    g.add_edge("code", "execute")
    g.add_conditional_edges(
        "execute",
        after_execute,
        {"verify": "verify", "debug": "debug", "degraded": "finalize_degraded"},
    )
    g.add_edge("debug", "execute")
    g.add_conditional_edges(
        "verify",
        verify_outcome,
        {"sufficient": "finalize_ok", "max_rounds": "finalize_degraded", "insufficient": "route"},
    )
    g.add_conditional_edges("route", _after_route, {"backtrack": "truncate", "add_step": "plan"})
    g.add_edge("truncate", "plan")
    g.add_edge("finalize_ok", END)
    g.add_edge("finalize_degraded", END)
    return g.compile()


async def run_precise(state: RunState, deps: LoopDeps) -> RunState:
    state.status = RunStatus.RUNNING
    graph = _build_graph(deps)
    result = await graph.ainvoke(state, config={"recursion_limit": _recursion_limit(state.budget)})
    return RunState.model_validate(result)


__all__ = ["run_precise"]
