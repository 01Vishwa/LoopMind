# Phase 3 — The DS-STAR Loop with Fakes — Completion Notes

Date: 2026-08-28
Branch: `issue-fix`
Spec: `docs/superpowers/specs/2026-08-28-phase-3-dsstar-loop-design.md`
Plan: `docs/superpowers/plans/2026-08-28-phase-3-dsstar-loop.md`

## What shipped

Implemented by six background subagents (one per plan task) plus orchestrator
review between tasks. **No git operations** — all changes left in the working
tree, per the Phase 2 precedent and the environment constraint.

The complete precise-mode DS-STAR loop now runs end-to-end against fakes, driven
from `vera run --fake-llm`, with every path (happy / multi-round / backtrack /
cycle / debug) covered by deterministic unit tests. No real LLM, no real
sandbox, no database.

### Task 1 — domain-model decomposition (`packages/core/src/vera_core/models/`)
- Split `run.py`: `PlanStep → plan.py`, `CodeArtifact → code.py`,
  `ArtifactRef`+`Observation → observation.py`, `Verdict → verdict.py`,
  `RouterAction`+`RouterDecision → routing.py`. `run.py` re-imports and
  re-exports all of them (old import paths still work); `models/__init__.py`
  unchanged; `test_exports.py` passes unmodified.
- New `AbandonedBranch` model (`round`, `from_index`, `removed_step_texts`,
  `removed_script_sha`, `rationale`; frozen).
- `RunState` gained `abandoned_branches: list[AbandonedBranch]`,
  `script_checkpoints: dict[int, CodeArtifact]`,
  `observation_checkpoints: dict[int, Observation]` — int-keyed dicts verified
  to round-trip through JSON.
- Import fixups in `policies/{backtrack,truncation,cycle_detection}.py`,
  `ports/sandbox.py`, `vera_testing/fakes/sandbox.py`.

### Task 2 — prompt registry (`packages/core/src/vera_core/prompts/`)
- `registry.py` — `PromptRegistry` (discovers `templates/<agent>/vN.jinja`,
  resolves highest version, records sha256) + `PromptTemplate` (Jinja2
  `StrictUndefined`, `trim_blocks`/`lstrip_blocks`).
- Filled the 7 versioned templates: `analyzer/v3`, `planner/v5`, `coder/v4`,
  `verifier/v6`, `router/v3`, `debugger/v2`, `finalizer/v2`. Draft quality —
  each states the task, names its input vars, requires JSON output. Wording
  refinement is Phase 4. `analyzer/formats/*`, `report_writer`,
  `subquestion_generator` templates left empty (Phases 7 / 8).

### Task 3 — fakes & factories (`packages/testing/`)
- `FakeLLM.on(agent, obj)` — per-agent scripted queue; `complete()` prefers the
  queue for the incoming `agent=` kwarg, falls back to the global FIFO. Existing
  `push_response`/`push_parsed` untouched. `queue_length` now counts both.
- `FakeSandbox.push_observation(obs)`.
- New `FakeRetriever` (`fakes/retriever.py`) — conforms to `RetrieverPort`,
  added to `test_fakes_conform.py::PAIRS`.
- Factories: `make_plan_step`, `make_code_artifact`, `make_observation`,
  `make_verdict`.

### Task 4 — agents (`packages/core/src/vera_core/agents/`)
- `base.py` — `AgentContext` (frozen: `llm`, `defaults`, `registry`, `run_id`),
  `Agent[TIn, TOut]` Protocol.
- `_types.py` — `PlanStepDraft`, `PlannerOutput`, `CoderOutput`,
  `FinalizerOutput` (frozen Pydantic).
- `_shared.py` — `run_structured_agent(ctx, *, agent, tier, template_vars,
  schema) -> tuple[ModelT, LLMResponse]`; raises `AgentOutputError` on
  unparseable output.
- 7 agents (`analyzer, planner, coder, verifier, router, debugger, finalizer`),
  each a payload dataclass + agent class + module-level singleton. **Every
  `.run(ctx, payload)` returns `tuple[<Output>, LLMResponse]`** (preflight
  ruling — nodes need the response for cost/token accounting).

### Task 5 — the loop (`packages/core/src/vera_core/loop/`)
- `context.py` — `LoopDeps` frozen dataclass (all ports + `defaults`,
  `registry`, `file_refs`, `mounts`, `cycle_detector`) plus `build_context` /
  `account` helpers.
- `edges.py` — pure predicates `execution_outcome`, `verify_outcome`,
  `route_outcome`, `debug_outcome`.
- `nodes/` — 10 nodes, each `async def node(state, deps) -> RunState`, one event
  emitted, no branching. `nodes/__init__.py` exposes `max_active_index`.
  `plan` uses **prefix-append**: when the planner's drafts start with the
  current active-plan texts, only the tail is appended; otherwise all drafts
  become new steps. `truncate` restores `state.script` from
  `script_checkpoints[j-1]` and `state.observations` from
  `observation_checkpoints` keys `< j` (no lineage walking), records an
  `AbandonedBranch`, resets `debug_attempts`.
- `runner.py` — `run_precise(state, deps) -> RunState`: explicit `while` loop
  per spec §5.2, with the `cycle_detector.is_cycling()` guard right after
  `plan` and a bounded inner debug loop.

### Task 6 — scenarios, fixtures, CLI
- `vera_testing/scenarios.py` — `Scenario` dataclass (`llm`, `sandbox`,
  `retriever`, `state: RunState`, `expected_status: RunStatus`,
  `expected_answer_substring`, `file_count`) + `happy_path()`, `multi_round()`,
  `backtrack()`; queues drain exactly through `run_precise` with `file_refs=[]`.
  `packages/core/tests/test_loop_scenarios.py` now imports these builders instead
  of inline helpers.
- `fixtures/payments/{payments.csv,merchant_data.json,fees.json,manifest.yaml}`
  — hand-authored; chargeback amounts sum to 1250. `manifest.yaml` carries **10
  gate queries** of increasing difficulty (`contains` substring + optional
  `tolerance`) for the Phase 4 loop-vs-single-shot comparison.
- `apps/cli/commands/run.py` — `vera run --workspace … --query … [--fake-llm]
  [--scenario happy|multiround|backtrack] [--max-rounds N]` (default scenario
  `backtrack`). Without `--fake-llm`: "Real LLM execution requires Phase 4. Use
  --fake-llm." exit 1. With it: prints `Analyzed N files` / `Plan: N steps
  (K backtracked)` / `Rounds:` / `Backtracks:` / `Cost: … Tokens: …` / `Answer:`.
  Registered in `main.py`.
- `Makefile` — `loop` target (+ `.PHONY`), pointed at the backtrack scenario with
  the Q3-chargebacks gate query.

## Gate output (local, 2026-08-28)

```
$ uv run pytest packages/ apps/ -q -m "not integration and not e2e and not live_llm"
146 passed, 10 deselected

$ uv run ruff check packages/ apps/            → All checks passed!
$ uv run ruff format --check packages/ apps/   → 190 files already formatted
$ uv run mypy packages/core/src packages/testing/src packages/db/src packages/llm/src apps/cli/src
Success: no issues found in 111 source files
$ uv run lint-imports                          → Contracts: 3 kept, 0 broken.

$ uv run vera run --workspace ./fixtures/payments \
    --query "What share of Q3 chargebacks came from merchants with manual capture delay?" \
    --fake-llm --scenario backtrack
Analyzed 3 files
Plan: 2 steps (1 backtracked)
Rounds: 2
Backtracks: 1
Cost: $0.0080   Tokens: 1200
Answer: After a backtrack to regroup by merchant, the total chargeback amount is $1250.00.
```

`make loop` wraps exactly this command (`make` is not on PATH on the dev box;
the wrapped `uv run vera run …` was verified directly).

Test count: 96 → 146 (+50: +3 models, +5 prompt registry, +7 fakes, +8 agents,
+19 loop/edges/truncate/scenarios/cycle, +8 scenarios/CLI).

The three graph scenarios (happy → `SUCCEEDED` in 1 round; add-step → 2 verdicts,
1 route; backtrack → 1 `AbandonedBranch`, checkpoints pruned, `SUCCEEDED`) and the
`truncate` hypothesis property test all pass. Cycle detection terminates a stuck
planner within a bounded call count.

## Preflight ruling

- **Agents `.run()` return `tuple[<Output>, LLMResponse]`** (not bare output).
  Reason: loop nodes need `input_tokens` / `cost_usd` from the response and
  `_shared.run_structured_agent` is the single LLM call site. Cost if wrong: a
  one-line unpack change in agent tests. Applied cleanly in Tasks 4–6.

## Decisions locked in the spec (recap)

D1 hand-rolled async loop (langgraph stays a dep, unused until Phase 5) ·
D2 precise loop only (no research agents) · D3 fill existing versioned templates ·
D4 decompose `run.py` · D5 checkpoint-dict rollback in `truncate` ·
D6 `--fake-llm` is the only working `vera run` path.

## Not verifiable in this environment

- `make loop` — `make` is not on PATH on the dev box; the wrapped
  `uv run vera run …` command was verified directly and the target is a verbatim
  copy of the spec.
- Nothing else deferred — the whole phase runs on fakes, so the full gate is
  reproducible locally.

## Follow-ups for later phases

- **Phase 4** builds the real `LLMClient.complete` and `DockerSandboxClient` in
  `packages/llm` (`cost.py`, `resilience.py`, `routing.py`, `structured.py`,
  `fakes.py` are still 0 bytes) and `packages/sandbox` (`guards/ast_scanner.py`,
  `backends/local_docker.py`, `client.py` need real implementations). A
  composition root (`container.py` or CLI wiring) builds a real `LoopDeps` so
  `vera run` works without `--fake-llm`. Prompt wording refinement (v-bump the
  templates) and the go/no-go gate ("loop beats single-shot ≥ 7/10") land here.
- Add `packages/sandbox/src` to the mypy strict target list and an import-linter
  contract that `vera_llm` / `vera_sandbox` import only `vera_core`.
- `plan` node prefix-append semantics assume the planner restates the cumulative
  plan each round. Phase 4's real planner prompt must enforce this, or the node
  needs a smarter merge.
- `RunState.docstring` still says "LangGraph" — harmless, update when Phase 5
  wires the real checkpointer.
- Per-subagent task reports: `docs/superpowers/plans/completed/phase3-task{1..6}-report.md`.
```
