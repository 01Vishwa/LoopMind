# Phase 3 — The DS-STAR Loop with Fakes — Design

**Date:** 2026-08-28
**Branch:** `issue-fix`
**Companion:** `docs/VERA_BACKEND_PHASES.md` (Phase 3), `docs/VERA_BACKEND_PLAN.md` §7
**Entry gate:** Phase 2 exit gate passed (see
`docs/superpowers/plans/completed/2026-08-28-phase-2-supabase-byok-notes.md`).

---

## 1. Goal

The complete agent loop — analyze → retrieve → plan → code → execute →
{verify | debug | finalize}, with `verify → route → {plan | truncate → plan}`
for multi-round refinement and backtracking — runs end-to-end against `FakeLLM`,
`FakeSandbox`, and `FakeRetriever`, driven from the CLI, with every path covered
by deterministic unit tests.

No real LLM, no real sandbox, no database. This phase debugs the **state
machine** in isolation so Phase 4 can debug **prompts** in isolation.

## 2. Decisions (locked)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **Hand-rolled async loop**, not a LangGraph `StateGraph`. `langgraph` stays a declared dependency, unused until Phase 5 checkpointing. | `RunState` is one mutable Pydantic object; every path is deterministic. An explicit `while` loop over pure node functions is trivially unit-testable and has no reducer/checkpointer ceremony. |
| D2 | **Scope: precise loop only.** 7 agents (analyzer, planner, coder, verifier, router, debugger, finalizer). `subquestion_generator`, `report_writer`, `loop/research.py` are deferred to Phase 8. | Matches `PHASES.md`. Research mode has its own gate. |
| D3 | **Fill the existing versioned `.jinja` files** (`verifier/v6.jinja`, `planner/v5.jinja`, …). `PromptRegistry` resolves a name to its highest version. | No file churn; the odd version numbers are pre-existing stubs. |
| D4 | **Decompose `models/run.py`.** Move `PlanStep`, `CodeArtifact`, `ArtifactRef`, `Observation`, `Verdict`, `RouterAction`, `RouterDecision` into the existing empty `models/{plan,code,observation,verdict,routing}.py`. `run.py` keeps `RunMode`, `RunStatus`, `RunBudget`, `RunState`, `AbandonedBranch`. `models/__init__.py` re-exports stay byte-identical so no downstream import breaks. | Phase 3 is the first multi-consumer use of these types; a 160-line `run.py` holding six models plus `RunState` is the monolith the file-per-concept layout exists to prevent. |
| D5 | **Typed backtrack bookkeeping on `RunState`** — `abandoned_branches: list[AbandonedBranch]`, `script_checkpoints: dict[int, CodeArtifact]`, `observation_checkpoints: dict[int, Observation]`. Truncate restores from checkpoints by index; it never walks `parent_sha256` lineage. | Lineage-walking is O(n) and breaks when the debugger emits a script with a different parent. A dict lookup has no edge cases. |
| D6 | **`--fake-llm` is the only working `vera run` path.** Without it the command exits with a "Phase 4 required" message. | Real LLM/sandbox wiring is Phase 4. |

## 3. Domain-model changes

### 3.1 New model — `models/routing.py` gains `AbandonedBranch`? No — it lives in `run.py`

`AbandonedBranch` records *why* a plan branch was abandoned so the planner can
render a negative constraint:

```python
# vera_core/models/run.py
class AbandonedBranch(BaseModel):
    round: int
    from_index: int
    removed_step_texts: list[str]
    removed_script_sha: str | None = None
    rationale: str

    model_config = {"frozen": True}
```

### 3.2 `RunState` — three additive fields

```python
class RunState(BaseModel):
    # ... all existing fields unchanged ...
    abandoned_branches: list[AbandonedBranch] = Field(default_factory=list)
    script_checkpoints: dict[int, CodeArtifact] = Field(default_factory=dict)
    observation_checkpoints: dict[int, Observation] = Field(default_factory=dict)
```

All three must round-trip through `model_dump_json` / `model_validate_json`
(dict keys serialise as strings and re-parse to `int` — the round-trip test
asserts this).

### 3.3 Model decomposition — exact moves

| Type | From | To |
|------|------|----|
| `PlanStep` | `run.py` | `models/plan.py` |
| `CodeArtifact` | `run.py` | `models/code.py` |
| `ArtifactRef` | `run.py` | `models/observation.py` |
| `Observation` | `run.py` | `models/observation.py` |
| `Verdict` | `run.py` | `models/verdict.py` |
| `RouterAction`, `RouterDecision` | `run.py` | `models/routing.py` |

`run.py` then imports them back:
`from vera_core.models.plan import PlanStep` etc. `run.py` keeps `RunMode`,
`RunStatus`, `RunBudget`, `RunState`, `AbandonedBranch`, and its `__all__` stays
the full list (re-exporting the moved names) so
`from vera_core.models.run import Observation` still works. `models/__init__.py`
is unchanged. `test_exports.py` still passes unmodified.

`policies/*` and `ports/*` that do `from vera_core.models.run import ...`:
update those imports to the new modules (backtrack.py, sandbox.py, event
imports). Grep for `models.run import` and fix each to import from the narrowest
module.

## 4. Module layout

```
packages/core/src/vera_core/
  agents/
    base.py            # Agent[TIn, TOut] Protocol; AgentContext dataclass
    _shared.py         # run_structured_agent(ctx, template_vars, schema) -> BaseModel
    analyzer.py planner.py coder.py verifier.py router.py debugger.py finalizer.py
  prompts/
    registry.py        # PromptRegistry, PromptTemplate
    templates/<agent>/vN.jinja   # existing empty files, filled
  loop/
    __init__.py        # re-exports run_precise, LoopDeps
    context.py         # LoopDeps dataclass
    edges.py           # execution_outcome, verify_outcome, route_outcome, debug_outcome
    runner.py          # run_precise(state, deps) -> RunState
    nodes/
      __init__.py
      analyze.py retrieve.py plan.py code.py execute.py
      debug.py verify.py route.py truncate.py finalize.py

packages/testing/src/vera_testing/
  fakes/llm.py         # + .on(agent, obj) per-agent scripting
  fakes/sandbox.py     # + .push_observation(obs)
  fakes/retriever.py   # NEW FakeRetriever
  fakes/__init__.py    # + FakeRetriever
  factories/domain.py  # + make_plan_step, make_code_artifact, make_observation, make_verdict
  scenarios.py         # NEW — scripts the fakes for happy / multiround / backtrack

apps/cli/src/vera_cli/
  commands/run.py      # NEW  `vera run`
  main.py              # + app.add_typer / app.command for run
  scenarios.py         # re-uses vera_testing.scenarios (dev-dep already present? see §9)

fixtures/payments/
  payments.csv merchant_data.json fees.json manifest.yaml
```

## 5. The loop

### 5.1 `LoopDeps` (`loop/context.py`)

```python
@dataclass(frozen=True)
class LoopDeps:
    llm: LLMPort
    sandbox: SandboxPort
    retriever: RetrieverPort
    event_bus: EventBusPort
    clock: ClockPort
    defaults: AgentDefaults
    registry: PromptRegistry
    file_refs: list[FileRef]          # workspace files to analyze
    mounts: list[DataMount]           # sandbox mounts for execute
    cycle_detector: CycleDetector     # fresh per run
```

### 5.2 Control flow (`loop/runner.py`)

```
run_precise(state, deps):
    state = await analyze(state, deps)
    state = await retrieve(state, deps)
    while True:
        state = await plan(state, deps)              # cycle_detector.record(active plan)
        state = await code(state, deps)              # checkpoint script+obs by max active index
        state = await execute(state, deps)

        outcome = execution_outcome(state)           # "ok" | "crash" | "budget"
        if outcome == "crash":
            while execution_outcome(state) == "crash":
                if state.debug_attempts >= state.budget.max_debug_attempts:
                    return await finalize(state, deps, degraded=True)
                state = await debug(state, deps)
                state = await execute(state, deps)
            if execution_outcome(state) == "budget":
                return await finalize(state, deps, degraded=True)
        elif outcome == "budget":
            return await finalize(state, deps, degraded=True)

        state.round += 1
        state = await verify(state, deps)
        vo = verify_outcome(state)                   # "sufficient" | "insufficient" | "max_rounds"
        if vo in ("sufficient", "max_rounds"):
            return await finalize(state, deps, degraded=(vo == "max_rounds"))

        state = await route(state, deps)
        ro = route_outcome(state, deps.cycle_detector)  # "add_step" | "backtrack"
        if ro == "backtrack":
            state = await truncate(state, deps)
        # loop back to plan
```

`route_outcome`: if the router said `backtrack` **and** `cycle_detector.is_cycling()`
is False → `"backtrack"`. If the router said `add_step` but the detector reports a
cycle → still `"add_step"` (planner is told to diverge via the abandoned-branch
constraint) and if the same cycle repeats twice more, `verify_outcome` short-circuits
to `max_rounds` on the next pass. (Simplest correct guard: `CycleDetector(max_repeats=3)`;
on `is_cycling()` the runner forces `finalize(degraded=True)` right after `plan`.)

Add that check at the top of the `while` after `plan`:
```
if deps.cycle_detector.is_cycling():
    return await finalize(state, deps, degraded=True)
```

### 5.3 Nodes — one file each, signature `async def NODE(state: RunState, deps: LoopDeps) -> RunState`

| Node | Agent / port | Reads | Writes | Event(s) |
|------|--------------|-------|--------|----------|
| `analyze` | analyzer (utility) per `deps.file_refs` | file refs | `state.descriptions` | `AnalysisStartedEvent`, `FileAnalyzedEvent` per file |
| `retrieve` | `deps.retriever.search` | `state.query`, `deps.defaults.retriever_top_k` | `state.descriptions` (filtered/ordered to top-K) | — |
| `plan` | planner (reasoning) | query, descriptions, `state.active_plan`, `state.abandoned_branches` | appends/repopulates `state.plan` from the first non-superseded gap; `created_at_round=state.round` | `PlanUpdatedEvent` |
| `code` | coder (reasoning) | query, active plan, last observation | `state.script` (sha256 = `sha256(source)`, `parent_sha256` = prior script sha); then `state.script_checkpoints[max_active_index] = state.script` | `CodeGeneratedEvent` |
| `execute` | `deps.sandbox.execute` | `state.script`, `deps.mounts`, `ResourceLimits()` | appends `truncate_observation(obs)` to `state.observations`; `state.observation_checkpoints[max_active_index] = that obs`; on `SandboxTimeoutError` append a synthetic `Observation(exit_code=124, stderr="timeout")` | `ExecutionStartedEvent`, `ExecutionFinishedEvent` |
| `debug` | debugger (utility) | `state.script.source`, last observation stderr | replaces `state.script` (new sha, parent = broken sha); `state.debug_attempts += 1` | `DebugAttemptEvent` |
| `verify` | verifier (reasoning) | query, active plan, `state.script.source`, last observation stdout | appends `Verdict` to `state.verdicts` | `VerifyVerdictEvent` |
| `route` | router (reasoning) | last verdict, active plan | appends `RouterDecision` to `state.routes` | `RouteDecisionEvent` |
| `truncate` | pure (policy) | last `RouterDecision.backtrack_index` = `j` | `apply_backtrack(state, j)`; `state.script = state.script_checkpoints.get(j - 1)`; `state.observations = [state.observation_checkpoints[i] for i in sorted(state.observation_checkpoints) if i < j]`; drop checkpoint keys `>= j`; append `AbandonedBranch(round=state.round, from_index=j, removed_step_texts=[…], removed_script_sha=<pre-truncate sha>, rationale=<router rationale>)`; `state.debug_attempts = 0` | — (the subsequent `plan` emits `PlanUpdatedEvent`) |
| `finalize` | finalizer (utility); `degraded: bool` kwarg | query, active plan, last observation | `state.answer`, `state.status` (`SUCCEEDED`, or `FAILED` if degraded and no usable observation), `state.finished_at = deps.clock.utcnow()` | `RunFinishedEvent` or `RunFailedEvent` |

**Cost/token accounting:** every node that calls `llm.complete` does
`state.cost_usd += response.cost_usd or Decimal("0")` and
`state.total_tokens += response.input_tokens + response.output_tokens`.

**`max_active_index`** helper (in `nodes/__init__.py` or `policies/backtrack.py`):
`max((s.index for s in state.active_plan), default=0)`.

### 5.4 Edge predicates (`loop/edges.py`) — pure, no deps

```python
def execution_outcome(state: RunState) -> Literal["ok", "crash", "budget"]:
    if termination.check_budget(state) is not None:
        return "budget"
    obs = state.last_observation
    return "ok" if obs is not None and obs.succeeded else "crash"

def verify_outcome(state: RunState) -> Literal["sufficient", "insufficient", "max_rounds"]:
    if state.verdicts and state.verdicts[-1].sufficient:
        return "sufficient"
    if state.round >= state.budget.max_rounds:
        return "max_rounds"
    return "insufficient"

def route_outcome(state: RunState, detector: CycleDetector) -> Literal["add_step", "backtrack"]:
    decision = state.routes[-1]
    if decision.action is RouterAction.BACKTRACK and decision.backtrack_index is not None:
        return "backtrack"
    return "add_step"

def debug_outcome(state: RunState) -> Literal["fixed", "retry", "max_retries"]:
    if state.debug_attempts >= state.budget.max_debug_attempts:
        return "max_retries"
    obs = state.last_observation
    return "fixed" if obs is not None and obs.succeeded else "retry"
```

## 6. Agents & prompts

### 6.1 `agents/base.py`

```python
@dataclass(frozen=True)
class AgentContext:
    llm: LLMPort
    defaults: AgentDefaults
    registry: PromptRegistry
    run_id: RunId

class Agent[TIn, TOut](Protocol):
    name: str
    tier: AgentTier
    async def run(self, ctx: AgentContext, payload: TIn) -> TOut: ...
```

### 6.2 `agents/_shared.py`

```python
async def run_structured_agent(
    ctx: AgentContext, *, agent: str, tier: AgentTier,
    template_vars: dict[str, object], schema: type[ModelT],
) -> tuple[ModelT, LLMResponse]:
    assignment = ctx.defaults.get_assignment(tier)
    template = ctx.registry.get(agent)
    rendered = template.render(**template_vars)
    response = await ctx.llm.complete(
        provider_connection_id=assignment.provider_connection_id,
        model_id=assignment.model_id,
        messages=[{"role": "system", "content": rendered}],
        response_schema=schema,
        temperature=assignment.temperature,
        max_tokens=assignment.max_tokens,
        run_id=ctx.run_id,
        agent=agent,
    )
    if response.parsed is None or not isinstance(response.parsed, schema):
        raise AgentOutputError(f"{agent} returned unparseable output: {response.content[:200]}")
    return response.parsed, response
```

`AgentOutputError` already exists in `errors.py`? — verify; if not, add it
(`status = 500`, `type_uri = "urn:vera:error:agent-output"`).

### 6.3 Per-agent I/O contracts

| Agent | tier | input template vars | output schema |
|-------|------|---------------------|---------------|
| analyzer | UTILITY | `filename`, `kind`, `sample` (str) | `FileDescription` |
| planner | REASONING | `query`, `descriptions` (list of summary str), `existing_steps` (list str), `abandoned` (list of rendered constraint str) | `PlannerOutput(steps: list[PlanStepDraft])` where `PlanStepDraft(text: str, acceptance_criteria: list[str] = [])` |
| coder | REASONING | `query`, `plan` (list str), `last_stdout` (str \| None), `last_stderr` (str \| None) | `CoderOutput(source: str)` |
| verifier | REASONING | `query`, `plan` (list str), `code` (str), `observation` (str) | `Verdict` |
| router | REASONING | `query`, `verdict_reason`, `missing_aspects` (list str), `plan` (list str) | `RouterDecision` |
| debugger | UTILITY | `code` (str), `stderr` (str) | `CoderOutput(source: str)` |
| finalizer | UTILITY | `query`, `plan` (list str), `observation` (str), `degraded` (bool) | `FinalizerOutput(answer: str)` |

New tiny output models live in `agents/_types.py` (`PlannerOutput`,
`PlanStepDraft`, `CoderOutput`, `FinalizerOutput`) — Pydantic, `frozen`, with a
round-trip test. `Verdict` and `RouterDecision` are reused from `models/`.

The planner's abandoned-branch constraint string (rendered by the `plan` node
before calling the agent, one per `AbandonedBranch`):

> `Step {from_index} previously attempted "{removed_step_texts[0]}" and was rejected because: "{rationale}". Propose a different approach.`

### 6.4 `prompts/registry.py`

```python
@dataclass(frozen=True)
class PromptTemplate:
    agent: str
    version: str            # "v6"
    source: str
    sha256: str
    def render(self, **vars: object) -> str: ...   # jinja2 Environment, StrictUndefined

class PromptRegistry:
    def __init__(self, templates_dir: Path | None = None) -> None: ...
    def get(self, agent: str, version: str | None = None) -> PromptTemplate:
        """Highest version for `agent` when `version` is None."""
    def list_versions(self, agent: str) -> list[str]: ...
```

Templates are discovered from `templates/<agent>/v<N>.jinja`. `analyzer` also has
`templates/analyzer/formats/<kind>.jinja` — Phase 3 fills only `analyzer/v3.jinja`
(a generic template); the per-format files stay empty (Phase 7). `render` uses
`jinja2.Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)`.

Draft prompt content: each template states the task in 2–4 sentences, lists the
input variables it receives, and ends with *"Respond only with JSON matching the
required schema."* Wording quality is explicitly out of scope (Phase 4 refines).

## 7. Fakes & scenarios

### 7.1 `FakeLLM.on(agent, obj)` (additive)

```python
def on(self, agent: str, obj: BaseModel | str, *, cost_usd: Decimal = Decimal("0.001")) -> None:
    """Queue a response addressed to a specific agent name."""
    self._agent_queues.setdefault(agent, []).append(_wrap(obj, cost_usd))
```

`complete()` change: if `self._agent_queues.get(agent)` is non-empty, pop from
there; else fall back to the existing global `_queue`. Existing behaviour and the
conformance test (signature unchanged) are unaffected.

### 7.2 `FakeSandbox.push_observation(obs: Observation)` (additive) — appends a caller-built observation.

### 7.3 `FakeRetriever` (`fakes/retriever.py`)

```python
class FakeRetriever:
    def __init__(self, descriptions: list[FileDescription] | None = None) -> None: ...
    def set_results(self, descriptions: list[FileDescription]) -> None: ...
    async def search(self, *, query: str, workspace_id: WorkspaceId,
                     top_k: int = 12, pinned_file_ids: list[FileId] | None = None
                     ) -> list[FileDescription]:
        return list(self._descriptions)[:top_k]
```

Add to `fakes/__init__.py` `__all__` and to `test_fakes_conform.py::PAIRS` as
`(FakeRetriever, RetrieverPort)`.

### 7.4 `vera_testing/scenarios.py`

Three builders, each returns `(FakeLLM, FakeSandbox, FakeRetriever)` fully
scripted plus an `expected_answer_substring: str`:

- `happy_path()` — analyzer×N, planner (2 steps), coder, verifier `sufficient=True`, finalizer.
- `multi_round()` — … verifier `sufficient=False` → router `add_step` → planner (3 steps) → coder → verifier `sufficient=True` → finalizer.
- `backtrack()` — … verifier `sufficient=False` → router `BACKTRACK backtrack_index=1` → truncate → planner → coder → verifier `sufficient=True` → finalizer. (This is the money test.)

Deterministic ordering: scenarios use `.on("planner", …)` etc. so the queue can't
desync if node call order shifts.

## 8. CLI

`apps/cli/src/vera_cli/commands/run.py`:

```
vera run --workspace PATH --query TEXT
         [--fake-llm] [--scenario happy|multiround|backtrack] [--max-rounds N]
```

- Without `--fake-llm`: `typer.echo("Real LLM execution lands in Phase 4. Re-run with --fake-llm.")`, `raise typer.Exit(1)`.
- With `--fake-llm`: read the workspace dir for supported files → build `FileRef`s
  (fake ids), build `LoopDeps` from `vera_testing.scenarios.<scenario>()` +
  `FakeEventBus` + `FixedClock` + a `make_agent_defaults()` + `PromptRegistry()`,
  call `run_precise`, then print:

  ```
  Analyzed 3 files
  Plan: 3 steps (1 backtracked at index 1)
  Rounds: 2   Cost: $0.0090   Tokens: 900
  Answer: <state.answer>
  ```

Wire into `main.py`: `app.command()(run)` (single command, not a sub-typer).

`apps/cli` gains a **dev dependency** on `vera-testing` (it's test/demo-only
scaffolding; acceptable for the `--fake-llm` path and mirrors how Phase 2's CLI
tests use fakes). Add `vera-testing` to `apps/cli/pyproject.toml`
`[dependency-groups].dev` **and** as a runtime dep is *not* wanted — instead put
the scenario wiring behind a lazy import inside the `--fake-llm` branch and add
`vera-testing` to `apps/cli` `[project.optional-dependencies].fake`. Simpler:
add it to `dependencies` with a comment; the CLI is not shipped to users yet.
**Chosen:** add `"vera-testing"` to `apps/cli/pyproject.toml [project] dependencies`
with `{ workspace = true }` in `[tool.uv.sources]`, matching the other members.

`.importlinter`: `vera_cli` importing `vera_testing` — the existing contract
`testing-depends-only-on-core` forbids `vera_testing → vera_cli`, not the reverse,
so no contract change is needed. Confirm `lint-imports` stays green.

## 9. Fixtures

`fixtures/payments/`:
- `payments.csv` — ~20 rows: `txn_id,merchant_id,amount,method,captured_at,capture_delay_manual,chargeback`
- `merchant_data.json` — 4 merchants: `{merchant_id, name, category}`
- `fees.json` — `{method: {percent, fixed}}` for `card`, `ach`, `wallet`
- `manifest.yaml` — one smoke query + expected answer substring, e.g.
  `queries: [{query: "Total chargeback amount?", expect: "1250"}]`

Fixtures are static, hand-authored, committed. The fake scenarios don't actually
read them (the sandbox is faked) — they exist for Phase 4 to point a real sandbox
at, and for the CLI's "Analyzed N files" count to be real.

## 10. Testing

All in `packages/core/tests/` unless noted. Markers: none (all unit).

| File | Tests |
|------|-------|
| `test_models.py` (extend) | round-trip `AbandonedBranch`; round-trip `RunState` with all three new fields populated (int-keyed dicts survive JSON) |
| `test_agents.py` (new) | each of the 7 agents: scripted `FakeLLM` → agent returns the right schema; `FakeLLM` returning junk → `AgentOutputError` |
| `test_prompt_registry.py` (new) | highest-version resolution; `StrictUndefined` raises on missing var; sha256 stable & changes with content |
| `test_loop_edges.py` (new) | each predicate across its full output range |
| `test_loop_scenarios.py` (new) | **Scenario A** happy: `status==SUCCEEDED`, 1 verdict, 0 routes. **Scenario B** multiround: 2 verdicts, 1 route `add_step`, plan grew. **Scenario C** backtrack: `len(state.abandoned_branches)==1`, superseded steps present, `script_checkpoints` pruned, final `status==SUCCEEDED` |
| `test_truncate.py` (new) | hypothesis: for a random plan of N steps with checkpoints, `truncate` at random `j` leaves `active_plan` = steps `< j`, `script == script_checkpoints[j-1]`, `len(observations)` == count of checkpoint keys `< j`, and no checkpoint key `>= j` remains |
| `test_cycle_detection.py` (new) | planner scripted to emit an identical plan 3× → runner finalizes `degraded=True` without infinite loop (assert bounded call count) |
| `packages/testing/tests/test_fakes_conform.py` (extend) | `FakeRetriever` conforms to `RetrieverPort` |
| `packages/testing/tests/test_scenarios.py` (new) | each scenario builder produces queues that drain exactly (no leftover, no underflow) when run through `run_precise` |
| `apps/cli/tests/test_run_command.py` (new) | `CliRunner`: `vera run … --fake-llm --scenario backtrack` exits 0 and prints "backtracked"; without `--fake-llm` exits 1 |
| `packages/core/tests/test_exports.py` (extend) | new loop surface (`run_precise`, `LoopDeps`) importable from `vera_core.loop` |

## 11. Exit gate

```bash
uv run pytest packages/ apps/ -q -m "not integration and not e2e and not live_llm"   # all green, ~+40 tests
uv run ruff check packages/ apps/
uv run ruff format --check packages/ apps/
uv run mypy packages/core/src packages/testing/src packages/db/src packages/llm/src apps/cli/src
uv run lint-imports                                                                  # 3 kept, 0 broken
uv run vera run --workspace ./fixtures/payments --query "Total chargeback amount?" --fake-llm --scenario backtrack
#  → Analyzed 3 files / Plan: N steps (1 backtracked …) / Answer: …
make loop                                                                            # same, via Makefile
```

`Makefile` gains:
```make
loop:
	uv run vera run --workspace ./fixtures/payments --query "Total chargeback amount?" --fake-llm --scenario backtrack
```
(add `loop` to `.PHONY`).

## 12. Out of scope (later phases)

Real LLM gateway, Docker sandbox, AST scanner (Phase 4); persistence,
checkpointer, RLS (Phase 5); API routers, SSE endpoint (Phase 6); per-format
analyzer prompts, pgvector retriever (Phase 7); research mode, evals (Phase 8).

## 13. Risks

- **Node call order vs FakeLLM queue** — mitigated by per-agent `.on()` queues (D7 in §7.1).
- **int-keyed dict JSON round-trip** — Pydantic coerces string keys back to `int` for `dict[int, X]`; the model test pins this.
- **`truncate` + debugger interaction** — `truncate` resets `debug_attempts = 0`; a backtrack after a debug spiral starts clean.
- **mypy strict on `langgraph`** — unused; no new import of it. If mypy complains about the existing dep, it's pre-existing.
