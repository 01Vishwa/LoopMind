# Phase 3 — Task 5 (the DS-STAR loop) — completion report

**Status:** DONE. All verification commands green.

## What shipped

### `packages/core/src/vera_core/loop/`
- `context.py` — `LoopDeps` frozen dataclass (fields exactly per spec §5.1:
  llm, sandbox, retriever, event_bus, clock, defaults, registry, file_refs,
  mounts, cycle_detector). Also holds the shared helpers `build_context`,
  `account` (folds `resp.cost_usd` + tokens into state), and `max_active_index`.
- `edges.py` — pure predicates `execution_outcome`, `verify_outcome`,
  `route_outcome`, `debug_outcome` transcribed from spec §5.4.
- `runner.py` — `run_precise(state, deps)`; control flow transcribed verbatim
  from spec §5.2 including `state.status = RUNNING` at entry,
  `cycle_detector.record(state.active_plan)` after `plan`, and the
  `is_cycling() -> finalize(degraded=True)` guard immediately after `plan`.
- `nodes/__init__.py` — re-exports the 10 node fns + `max_active_index`.
- `nodes/{analyze,retrieve,plan,code,execute,debug,verify,route,truncate,finalize}.py`
  — one `async def NODE(state, deps) -> RunState` each, one event each, no
  branching (per spec §5.3 node table).
- `__init__.py` — re-exports `run_precise`, `LoopDeps`.

### Key implementation decisions
- **plan node** appends the planner's draft steps that extend past the current
  active plan (prefix-match against `[s.text for s in active_plan]`; when the
  draft is a prefix-or-equal of the active plan, nothing new is appended). This
  is what makes `cycle_detector.record(state.active_plan)` actually detect a
  non-diverging planner: an identical 1-step draft leaves `active_plan`
  unchanged, so the fingerprint repeats and `is_cycling()` fires. New steps get
  indices `max(existing plan index) + 1 …` and `created_at_round=state.round`.
- **truncate**: captures `pre_sha` + removed active-step texts (`index >= j`)
  before `apply_backtrack(state, j)`; then `state.script =
  script_checkpoints.get(j-1)` (None when j==0 or that index was never
  checkpointed), rebuilds `state.observations` from `observation_checkpoints`
  with key `< j`, deletes both checkpoint dicts' keys `>= j`, appends one
  `AbandonedBranch`, resets `debug_attempts = 0`. No event (the following `plan`
  emits `PlanUpdatedEvent`).
- **execute**: `ResourceLimits()` defaults; `SandboxTimeoutError` -> synthetic
  `Observation(exit_code=124, stderr="timeout", duration_ms=timeout_s*1000)`;
  `truncate_observation` applied before append + checkpoint at
  `max_active_index`. Raises if `state.script is None` (mypy narrowing + guard).
- **finalize**: `status = FAILED if degraded and not state.observations else
  SUCCEEDED`; sets `finished_at = deps.clock.utcnow()`, `error="degraded"` and
  emits `RunFailedEvent(error="degraded")` on FAILED, else `RunFinishedEvent`.
- Every LLM node unpacks `out, resp = await agent.run(ctx, payload)` and calls
  `account(state, resp)`.

### Tests (all in `packages/core/tests/`)
- `test_loop_edges.py` — 12 cases, every predicate across its full output range.
- `test_truncate.py` — hypothesis property test (random N steps / random j) for
  the truncate invariants + an explicit j==0 case. Body is sync and drives the
  async node via `asyncio.run` (hypothesis does not await coroutines).
- `test_loop_scenarios.py` — inline scripted-fake builders (`_happy`,
  `_add_step`, `_backtrack`) + 3 tests:
  - happy -> `SUCCEEDED`, 1 verdict, 0 routes, answer contains "1250".
  - add-step -> `SUCCEEDED`, 2 verdicts, 1 `ADD_STEP` route, `active_plan` grew
    to 3.
  - backtrack -> `SUCCEEDED`, exactly 1 `AbandonedBranch` (`from_index == 1`),
    superseded steps present, answer contains "1250".
- `test_cycle_detection.py` — planner scripted to emit the same 1-step plan 4×,
  verifier always insufficient, router always add_step; asserts terminal status
  and `llm.call_count < 30` (cycle detector fires on the 3rd identical plan).
- `test_exports.py` — added `test_loop_surface` (imports `run_precise`,
  `LoopDeps` from `vera_core.loop`).

## Verification (from E:\Vera)

- `uv run pytest packages/ apps/ -q -m "not integration and not e2e and not live_llm"`
  -> **138 passed, 10 deselected** (was 119; +19 new).
- `uv run ruff check packages/ apps/` -> All checks passed.
- `uv run ruff format --check packages/ apps/` -> 186 files already formatted.
- `uv run mypy packages/core/src packages/testing/src packages/db/src packages/llm/src apps/cli/src`
  -> Success, no issues found in 109 source files.
- `uv run lint-imports` -> **3 kept, 0 broken.**

## Out of scope for this task (Task 6)

- `vera_testing/scenarios.py`, `fixtures/payments/*`, `apps/cli` `vera run`
  command, `Makefile` `loop` target. The scenario tests here use small inline
  scripted-fake helpers instead of the shared `scenarios.py`.

## Concerns / notes

- The `plan` node semantics (prefix-append) is a deliberate reconciliation of
  two spec statements that are otherwise inconsistent: literally recording
  `state.active_plan` for cycle detection only detects a stuck planner if the
  plan node does not blindly append. If Task 6's `scenarios.py` scripts the
  planner to return only *new* delta steps every round (not the full active
  plan), the add-step path will still work, but a planner that returns a full
  restated plan each round will not grow the plan — scenario authors should
  return the cumulative plan text, as the inline builders here do.
- Pre-existing `DeprecationWarning: datetime.utcnow()` from `models/events.py`
  `BaseEvent.created_at` default — untouched per Global Constraints.
- `debug_outcome` is implemented and exported but `run_precise` uses an inline
  `execution_outcome`-based debug loop per spec §5.2; `debug_outcome` is kept
  for the edge-predicate test surface / future use.
