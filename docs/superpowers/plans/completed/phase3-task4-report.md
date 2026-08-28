# Phase 3 — Task 4 (Agents) — Completion Report

**Status:** DONE

## Files touched

Created:
- `packages/core/src/vera_core/agents/base.py` — `AgentContext` (frozen dataclass, `run_id: RunId | None = None`), `Agent[TIn, TOut]` Protocol
- `packages/core/src/vera_core/agents/_types.py` — `PlanStepDraft`, `PlannerOutput`, `CoderOutput`, `FinalizerOutput` (frozen Pydantic)
- `packages/core/src/vera_core/agents/_shared.py` — `run_structured_agent(...) -> tuple[ModelT, LLMResponse]`, raises `AgentOutputError` on unparseable / wrong-type `response.parsed`
- `packages/core/src/vera_core/agents/{analyzer,planner,coder,verifier,router,debugger,finalizer}.py` — each defines its `*Payload` frozen dataclass, an `*Agent` class with `name` / `tier` and `async def run(self, ctx, payload) -> tuple[<Output>, LLMResponse]`, and a module-level singleton instance
- `packages/core/src/vera_core/agents/__init__.py` — re-exports 7 agent instances + `Agent` + `AgentContext` + every payload/output type
- `packages/core/tests/test_agents.py` — 8 tests

## Key decisions applied

- Preflight ruling honored: every `run` returns `tuple[<Output>, LLMResponse]`; agents pass the `_shared` tuple straight through. Test unpacks `out, resp = await ...` and asserts `resp` is an `LLMResponse` with `.input_tokens > 0` and `.cost_usd is not None`.
- `AnalyzePayload` carries `file_id: str`; analyzer injects it into `template_vars` (template's StrictUndefined only requires `filename`/`kind`/`sample`, extra key is harmless) and trusts FakeLLM to return a matching `FileDescription`.
- Tiers: planner/coder/verifier/router = REASONING; analyzer/debugger/finalizer = UTILITY.
- Templates (Task 2) and `PromptRegistry`, `FakeLLM.on`, factories were already in place; no changes needed.

## Test summary

`uv run pytest packages/ apps/ -q -m "not integration and not e2e and not live_llm"` → **119 passed, 10 deselected** (111 baseline + 8 new).

## Verification

- ruff check + ruff format --check: clean
- mypy (core, testing, db, llm, cli src): Success, no issues in 94 files
- lint-imports: 3 kept, 0 broken (agents import only `vera_core.*`)

## Concerns

- None blocking. Task 5 will extend each agent call site with cost/token accounting in the loop nodes; the tuple return is already in place for that.
