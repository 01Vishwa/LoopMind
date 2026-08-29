# Phase 4 (pulled forward) — Analyzer Rearchitecture, Prompt Hardening, LangGraph Conversion — Design

**Date:** 2026-08-29
**Branch:** `issue-fix`
**Companion:** `docs/VERA_BACKEND_PHASES.md` (Phase 3 §3.8, Phase 4), `docs/superpowers/specs/2026-08-28-phase-3-dsstar-loop-design.md`
**Supersedes:** Phase 3 design decision **D1** ("hand-rolled loop, not `StateGraph`, until Phase 5"). D1's own text says the deferral is "until Phase 5 checkpointing," but the original `PHASES.md` Step 3.8 always specified the `StateGraph` conversion inside Phase 3. Pulling it forward now is catching up to the master plan, not a new deviation, and it unblocks giving each precise-loop node the `langgraph` retry/streaming primitives before Phase 4's real-LLM work needs them.
**Entry gate:** Phase 3 unit-test suite is green (`uv run pytest packages/ apps/ -q -m "not integration and not e2e and not live_llm"`) — verify before starting.

---

## 1. Goal

Three changes to `packages/core/src/vera_core`, none touching `apps/api`, `packages/llm`, or `packages/db`:

1. **Analyzer rearchitecture** — replace the current direct-describe call with the spec's generate-script → execute-in-sandbox → parse-stdout mechanism (the single highest-leverage fix per the agent-spec doc's own ablation: 45.24% → 26.98% accuracy without it), including a Scenario-A debug-retry path and a partial-description fallback.
2. **Prompt hardening** — fill out the still-skeletal `analyzer/v3`, `planner/v5`, `coder/v4`, `verifier/v6`, `router/v3`, `debugger/v2`, `finalizer/v2` templates to match the full contracts in the agent-spec reference doc (few-shot framing, explicit caps, calibration language), **in place** — these are first-fill stubs per Phase 3 D3, not yet "merged" content, so no version bump is needed. The analyzer template additionally gains the `{% include "analyzer/formats/" + kind + ".jinja" %}` wiring to the six already-populated format sub-templates.
3. **LangGraph conversion** — replace `loop/runner.py`'s hand-rolled `while` loop with a real `langgraph.graph.StateGraph`, keeping every `loop/nodes/*.py` function's logic unchanged (only their call signature adapts) and every `loop/edges.py` predicate reused verbatim as a conditional-edge selector.

A new minimal, dev-only `SubprocessSandbox` backend is added to `packages/sandbox` so the Analyzer fix is real end-to-end, not just parsing-logic-in-isolation.

## 2. Decisions (locked for this spec)

| # | Decision | Rationale |
|---|----------|-----------|
| E1 | Analyzer output changes from `FileDescription` to a generated script (`CoderOutput`, reused — identical `source: str` shape, no new type). | Matches the agent-spec's §3.3 two-step mechanism; avoids a needless duplicate schema. |
| E2 | `FileDescription` gains one additive field: `partial: bool = False`. | Marks fallback descriptions per agent-spec §3.8 without breaking existing serialization. |
| E3 | Sandbox: one new backend, `SubprocessSandbox`, gated behind `VERA_SANDBOX_ALLOW_SUBPROCESS=1`; `SandboxClient` refuses to construct a subprocess backend without it. Docker/gVisor backends stay `NotImplementedError` stubs. | Honors the CLAUDE.md hazard ("fail closed when Docker/gVisor is absent") while still making the Analyzer loop runnable in dev/CI. |
| E4 | AST deny-list scanner (`guards/ast_scanner.py`) is implemented as defense-in-depth and documented as **not** a security boundary. | Matches the CLAUDE.md hazard note verbatim; the container/microVM (Phase 4 proper, Docker) remains the real boundary. |
| E5 | LangGraph state schema is `RunState` itself (already a mutable, JSON-serializable Pydantic `BaseModel` per Phase 3 D-decisions) — no `TypedDict` translation layer. | `langgraph>=0.2` supports Pydantic `BaseModel` state directly; a parallel `TypedDict` would be a second source of truth for the same fields. |
| E6 | Each node function keeps its `(state: RunState, deps: LoopDeps) -> RunState` signature; the graph binds `deps` per run via `functools.partial` when `run_precise` constructs the graph, rather than smuggling `deps` through LangGraph's `config`. | `deps` carries run-specific `file_refs`/`mounts`/`cycle_detector` — it cannot be a module-level singleton, so the graph must be built fresh per invocation regardless. `functools.partial` keeps `loop/nodes/*.py` untouched. |
| E7 | Conditional routing after `execute`, `verify`, `route`, and `debug` is expressed via `StateGraph.add_conditional_edges` calling the existing `edges.py` predicates unchanged — no predicate logic moves or is rewritten. | Phase 3's edge predicates are already pure and unit-tested; only their *wiring* changes. |
| E8 | The `truncate → plan` back-edge and the cycle-detector short-circuit (checked immediately after `plan`) are preserved exactly as in the current `while` loop, expressed as a conditional edge out of `plan` before `code`. | Cycle detection must run before any further LLM spend, same as today. |
| E9 | `run_precise` keeps its existing public signature `async def run_precise(state: RunState, deps: LoopDeps) -> RunState`; callers (CLI, tests) are unaffected. Internally it now compiles and invokes a `StateGraph` instead of running the `while` loop. | No churn to `apps/cli` or existing scenario tests that call `run_precise` end-to-end. |

## 3. Analyzer rearchitecture

### 3.1 Agent change (`agents/analyzer.py`)

`AnalyzerAgent.run()` now targets `schema=CoderOutput` instead of `schema=FileDescription`, and its prompt template vars gain nothing new (`filename`, `kind`, `sample` stay the same — `sample` just stops being hardcoded to `""` upstream).

```python
class AnalyzerAgent:
    name = "analyzer"
    tier = AgentTier.UTILITY

    async def run(self, ctx: AgentContext, payload: AnalyzePayload) -> tuple[CoderOutput, LLMResponse]:
        return await run_structured_agent(
            ctx, agent=self.name, tier=self.tier,
            template_vars={"file_id": payload.file_id, "filename": payload.filename,
                           "kind": payload.kind, "sample": payload.sample},
            schema=CoderOutput,
        )
```

### 3.2 New pure functions — `policies/analyzer_output.py`

```python
def parse_analyzer_stdout(file_id: FileId, stdout: str) -> FileDescription:
    """Parse the analyzer script's `--- Essential Information ---` stdout block
    into a FileDescription. Best-effort key: value and column-list parsing;
    unparseable sections are folded into summary_text verbatim."""

def build_partial_description(file_id: FileId, sample: str) -> FileDescription:
    """Fallback when the analyzer script fails twice: columns-only best-effort
    from the first line of `sample` (header row for csv/tsv-shaped samples,
    top-level keys for JSON-shaped samples), partial=True, no row_count."""
```

Both are pure (no I/O, no LLM, no sandbox) and unit-tested directly with fixture stdout strings — one fixture per `FileKind`.

### 3.3 `FileDescription` model change (`models/file.py`)

Add `partial: bool = False` to the existing frozen model. Additive, no migration concerns (nothing persists it yet — `packages/db` is still a stub).

### 3.4 `loop/nodes/analyze.py` rewrite

```
for ref in deps.file_refs:
    sample = read_sample(mount_for(ref, deps.mounts), max_bytes=8192)   # new helper
    script_out, resp = await analyzer.run(ctx, AnalyzePayload(file_id=str(ref.file_id),
                                            filename=ref.filename, kind=ref.kind.value, sample=sample))
    account(state, resp)
    script = CodeArtifact(source=script_out.source, sha256=sha256(script_out.source))
    observation = await execute_analyzer_script(deps.sandbox, script, mount_for(ref, deps.mounts), state.run_id)

    attempts = 0
    while not observation.succeeded and attempts < ANALYZER_MAX_DEBUG_ATTEMPTS:  # = 2
        attempts += 1
        debug_out, resp = await debugger.run(ctx, DebuggerPayload(code=script.source, stderr=observation.stderr))
        account(state, resp)
        script = CodeArtifact(source=debug_out.source, sha256=sha256(debug_out.source), parent_sha256=script.sha256)
        observation = await execute_analyzer_script(deps.sandbox, script, mount_for(ref, deps.mounts), state.run_id)

    description = (parse_analyzer_stdout(ref.file_id, observation.stdout) if observation.succeeded
                   else build_partial_description(ref.file_id, sample))
    state.descriptions.append(description)
    await deps.event_bus.emit(..., FileAnalyzedEvent(..., row_count=description.row_count))
```

`read_sample` and `execute_analyzer_script` are both new helpers in `loop/context.py`, alongside the existing `account`/`build_context`/`max_active_index`/`numbered` shared node helpers. `read_sample(ref, mounts)` matches a `FileRef` to its `DataMount` by filename and reads up to 8 KB from `host_path`. `execute_analyzer_script(sandbox, script, mount, run_id)` wraps `sandbox.execute(...)` with a 30s `ResourceLimits`, catching `SandboxTimeoutError` into a synthetic failed `Observation` exactly like the existing `execute` node does — same pattern, smaller timeout, scoped to one file's mount.

`ANALYZER_MAX_DEBUG_ATTEMPTS = 2` is a module constant in `analyze.py` (agent-spec §3.8 item 3), independent of `state.budget.max_debug_attempts` (that budget governs the main coder/debugger cycle, not the pre-loop analyzer step).

## 4. Prompt template hardening (in place, no version bump)

Each of the 7 templates is rewritten to match its agent-spec §N.6 "Prompt contract" section. No new files — Phase 3 D3 already established these are first-fill stubs. Content additions per template:

- **`analyzer/v3.jinja`**: full script-generation contract — self-contained, no try/except, stable `--- Essential Information ---` header, per-`kind` include of `analyzer/formats/{kind}.jinja` (already-populated files, currently dead code), explicit 8 KB stdout cap.
- **`planner/v5.jinja`**: "restate the full cumulative plan verbatim" instruction (load-bearing — `loop/nodes/plan.py`'s `_is_prefix` heuristic depends on this exact behavior; the LEDGER comment there stays valid, not touched), simplicity instruction ("propose only the next simple step"), negative-constraint rendering.
- **`coder/v4.jinja`**: "preserve all working logic, add only the new step" instruction, incremental-build framing, no try/except.
- **`verifier/v6.jinja`**: explicit "you are deterministic, temperature 0" framing, "judge the OUTPUT, not just whether the code looks plausible" instruction.
- **`router/v3.jinja`**: concrete backtrack-vs-add_step worked examples from agent-spec §7.7.
- **`debugger/v2.jinja`**: traceback-summarization framing, explicit column-name-correction guidance when `descriptions` are non-empty (Scenario B) vs absent (Scenario A).
- **`finalizer/v2.jinja`**: number-formatting instructions (commas, 2dp currency, % sign), degraded-mode caveat framing.

## 5. Minimal subprocess sandbox

New implementations for currently-0-byte files in `packages/sandbox/src/vera_sandbox/`:

- **`guards/resource_limits.py`** — `asyncio.wait_for` timeout wrapper; POSIX-only best-effort `resource.setrlimit(RLIMIT_AS, ...)` via `preexec_fn`, skipped entirely (no `resource` import) when `sys.platform == "win32"`.
- **`guards/ast_scanner.py`** — `ast.walk` deny-list blocking `socket`, `subprocess`, `ctypes`, `os.system`/`os.popen`, `eval`/`exec`, `__import__`, `urllib`/`requests`/`http`. A blocked script short-circuits to `Observation(exit_code=1, stderr="Blocked: <reason>", ...)` without ever spawning a subprocess — the Debugger sees this like any other crash and can react to the message.
- **`mounts.py`** — materializes each `DataMount` into a fresh `tempfile.mkdtemp()` by copying (not symlinking — Windows dev environments often lack symlink privilege) `host_path` to `<tempdir>/<container_path basename>`.
- **`capture.py`** — reads subprocess stdout/stderr incrementally, truncating at `limits.max_output_bytes` and setting `Observation.truncated=True`.
- **`backends/subprocess_backend.py`** — `SubprocessSandbox` implementing `SandboxPort.execute()`: runs the AST guard, then `asyncio.create_subprocess_exec(sys.executable, script_path, cwd=tempdir)` under the timeout guard, returns `Observation`; raises the existing `SandboxTimeoutError` on timeout (already the exact exception type both `loop/nodes/execute.py` and the new analyzer helper catch).
- **`client.py`** — `SandboxClient(backend: Literal["subprocess", "docker", "gvisor"])`: constructing with `backend="subprocess"` raises `RuntimeError` unless `os.environ.get("VERA_SANDBOX_ALLOW_SUBPROCESS") == "1"`; `"docker"`/`"gvisor"` raise `NotImplementedError`. This is where Phase 4-proper's real fail-closed composition-root logic will plug in later — `apps/api` doesn't construct this yet (no `container.py` exists), so the gate lives here for now.

## 6. LangGraph conversion (`loop/runner.py`)

### 6.1 Graph shape

```python
from langgraph.graph import StateGraph, START, END

def _build_graph(deps: LoopDeps) -> "CompiledStateGraph":
    g = StateGraph(RunState)
    g.add_node("analyze", partial(analyze, deps=deps))
    g.add_node("retrieve", partial(retrieve, deps=deps))
    g.add_node("plan", partial(plan, deps=deps))
    g.add_node("code", partial(code, deps=deps))
    g.add_node("execute", partial(execute, deps=deps))
    g.add_node("debug", partial(debug, deps=deps))
    g.add_node("verify", partial(verify, deps=deps))
    g.add_node("route", partial(route, deps=deps))
    g.add_node("truncate", partial(truncate, deps=deps))
    g.add_node("finalize_ok", partial(finalize, deps=deps, degraded=False))
    g.add_node("finalize_degraded", partial(finalize, deps=deps, degraded=True))

    g.add_edge(START, "analyze")
    g.add_edge("analyze", "retrieve")
    g.add_edge("retrieve", "plan")

    g.add_conditional_edges("plan", _after_plan(deps.cycle_detector),
        {"cycle": "finalize_degraded", "continue": "code"})
    g.add_edge("code", "execute")
    g.add_conditional_edges("execute", execution_outcome,
        {"ok": "verify", "crash": "debug", "budget": "finalize_degraded"})
    g.add_conditional_edges("debug", _after_debug,  # wraps debug_outcome + re-execute
        {"retry": "execute", "max_retries": "finalize_degraded"})
    g.add_conditional_edges("verify", verify_outcome,
        {"sufficient": "finalize_ok", "max_rounds": "finalize_degraded", "insufficient": "route"})
    g.add_conditional_edges("route", route_outcome,
        {"backtrack": "truncate", "add_step": "plan"})
    g.add_edge("truncate", "plan")

    g.add_edge("finalize_ok", END)
    g.add_edge("finalize_degraded", END)
    return g.compile()

async def run_precise(state: RunState, deps: LoopDeps) -> RunState:
    state.status = RunStatus.RUNNING
    graph = _build_graph(deps)
    return await graph.ainvoke(state)
```

### 6.2 Two edge-shape mismatches to resolve (both pure wiring, no policy change)

- **`debug` isn't a conditional-edge source in the old code** — the `while execution_outcome(state) == "crash"` inner loop is really "debug, then go straight back to `execute` (not through a decision node), checking `debug_outcome` only for the `max_retries` exit." Model this as: `debug` node itself calls `execute` internally is wrong (nodes must stay side-effect-boundaries only calling their own agent/port) — instead add `debug`'s conditional edge target `execute` directly (`{"retry": "execute", ...}` above), and have `execution_outcome`'s "crash" branch route back to `debug` again automatically via the `execute → debug` conditional edge. This reproduces the original `while` exactly: `execute -[crash]-> debug -[retry]-> execute -[crash]-> debug -> ...-> [ok]-> verify` or `[max_retries]-> finalize_degraded`, with no `_after_debug` synthetic wrapper needed after all — drop it from §6.1 and use `debug_outcome` directly as the conditional-edge selector on `debug` with targets `{"fixed": "verify", "retry": "execute", "max_retries": "finalize_degraded"}` (checking `debug_outcome` right after `debug` runs, before re-executing, matches the original code's check order exactly — re-derive `debug_outcome` to inspect `state.debug_attempts` vs budget only, not `last_observation`, since at that point the *replacement* script hasn't executed yet). **Verify against the existing `test_loop_edges.py`/`test_loop_scenarios.py` behavior during implementation** — this is the one place where flattening the `while` into edges needs care; write a new scenario test (`multi_debug_retry`) that exercises 2 consecutive crashes before a fix, asserting node visit order, before trusting the graph shape.
- **The `plan`-then-cycle-check ordering**: the old code checks `cycle_detector.is_cycling()` *after* `plan` runs but *before* `code`. `_after_plan(detector)` is a closure (not a bare function) because it needs the same `CycleDetector` instance `deps.cycle_detector` that `plan.py` already records into — no new state, just a routing function reading `deps.cycle_detector.is_cycling()`.

### 6.3 What does NOT change

`loop/nodes/*.py` function bodies, `loop/edges.py` predicate bodies, `loop/context.py` (`LoopDeps`, `account`, `build_context`, `max_active_index`, `numbered`) — all reused as-is. `loop/runner.py` is the only file whose *implementation* changes; its public `run_precise` signature does not.

## 7. Testing

All in `packages/core/tests/` unless noted.

| File | Tests |
|---|---|
| `test_analyzer_output.py` (new) | `parse_analyzer_stdout` against one fixture stdout per `FileKind`; `build_partial_description` against csv-shaped and JSON-shaped raw samples |
| `test_loop_nodes_analyze.py` (extend/new) | happy path (script succeeds first try); crash-then-fixed-by-debugger (1 retry); crash-exhausts-2-retries → `partial=True` fallback — all via `FakeLLM` + `FakeSandbox` |
| `packages/sandbox/tests/test_subprocess_backend.py` (new) | trivial `print("hello")` script succeeds; infinite-loop script raises `SandboxTimeoutError` within the configured timeout; `import socket` script is blocked pre-execution with a clear stderr message and never spawns a process (assert via a monkeypatched `create_subprocess_exec` call-count of 0) |
| `packages/sandbox/tests/test_client_gating.py` (new) | `SandboxClient("subprocess")` without the env var raises `RuntimeError`; with it, returns a working `SubprocessSandbox`; `SandboxClient("docker")` raises `NotImplementedError` regardless |
| `test_prompt_registry.py` (extend) | render-smoke test per agent: `registry.get(agent).render(**minimal_vars)` doesn't raise `StrictUndefined` for the hardened templates; analyzer template's format-include renders for each `FileKind` |
| `test_loop_scenarios.py` (extend) | existing `happy_path`/`multi_round`/`backtrack` scenarios still pass unchanged through the new `StateGraph`-based `run_precise` (this is the regression guard that the conversion preserved behavior); **new** `multi_debug_retry` scenario per §6.2 |
| `test_loop_runner_graph.py` (new) | asserts the compiled graph's node set and that `run_precise` is still `async def run_precise(state, deps) -> RunState` (signature-preservation guard for `apps/cli`) |

## 8. Exit gate

```bash
uv run pytest packages/ apps/ -q -m "not integration and not e2e and not live_llm"
uv run ruff check packages/ apps/
uv run ruff format --check packages/ apps/
uv run mypy packages/core/src packages/testing/src packages/sandbox/src
uv run lint-imports
uv run vera run --workspace ./fixtures/payments --query "Total chargeback amount?" --fake-llm --scenario backtrack
VERA_SANDBOX_ALLOW_SUBPROCESS=1 uv run pytest packages/sandbox/tests -q
```

## 9. Out of scope

DS-STAR+ (`subquestion_generator`, `report_writer`, `loop/research.py` — Phase 8 per D2, unchanged). Real Docker/gVisor sandbox backends. `packages/llm` real provider implementation. `apps/api` composition root / container.py. Persistence of `FileDescription.partial` or any checkpointing (Phase 5). Changes to `loop/nodes/plan.py`'s `_is_prefix` LEDGER heuristic itself (only the prompt is hardened to keep satisfying it).

## 10. Risks

- **LangGraph conditional-edge flattening of the debug retry loop** (§6.2) is the one place where behavior could subtly diverge from the hand-rolled `while`. Mitigated by keeping all three existing scenario tests green through the conversion plus one new `multi_debug_retry` scenario.
- **`functools.partial` binding `deps` per graph build** means `_build_graph` must be called fresh every `run_precise` invocation (never cached/module-level) — a stale `deps` (wrong `file_refs`/`mounts` for a different run) would silently cross-contaminate runs. `test_loop_runner_graph.py` should build two graphs with different `deps.file_refs` and assert no leakage.
- **Windows dev environment**: `guards/resource_limits.py`'s memory cap is inert here (no `resource` module) — timeout is the only real guard on this platform. Documented, not silently hidden.
