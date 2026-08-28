# Phase 3 — DS-STAR Loop with Fakes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete DS-STAR agent loop (analyze → retrieve → plan → code → execute → {verify | debug | finalize}, with verify → route → {plan | truncate → plan}) as a hand-rolled async state machine in `vera_core`, driven from `vera run --fake-llm`, with every path covered by deterministic tests.

**Architecture:** Pure node functions `async def node(state: RunState, deps: LoopDeps) -> RunState`, one file each, each emitting exactly one event and never branching. All control flow lives in `loop/runner.py`'s explicit `while` loop with pure edge predicates in `loop/edges.py`. Backtracking restores `state.script` / `state.observations` from index-keyed checkpoint dicts on `RunState` — no lineage walking. `langgraph` stays a declared dependency, unused until Phase 5.

**Tech Stack:** Python 3.13, Pydantic v2, Jinja2, Typer, pytest + pytest-asyncio + hypothesis, polyfactory. `uv` workspace. mypy --strict on `packages/core/src packages/testing/src apps/cli/src`.

**Spec:** `docs/superpowers/specs/2026-08-28-phase-3-dsstar-loop-design.md` — read it in full before starting.

## Global Constraints

- Python **3.13**; `ruff` (line length 100, rules `E,F,I,N,UP,B,SIM`); `mypy --strict` must pass on `packages/core/src packages/testing/src packages/db/src packages/llm/src apps/cli/src`.
- All domain types are Pydantic v2 models; new value objects are `model_config = {"frozen": True}`. Every new model gets a round-trip test in the nearest `test_models.py` / `test_*_types.py`.
- `.importlinter` contracts must stay green: `vera_core` imports no adapter/API/testing; `vera_testing` imports no adapter/API/cli. `vera_cli → vera_testing` is allowed.
- **No git available in this environment.** "Commit" steps mean: leave changes in the working tree, run the stated verification, and record progress in the task checkbox. Do not run `git`.
- Ports take **keyword-only** arguments (`test_every_port_method_is_keyword_only` enforces it).
- `datetime` uses `datetime.now(UTC)` / injected `ClockPort`, never `datetime.utcnow()` in new code (existing `events.py` use is pre-existing).
- Prompt template wording quality is **out of scope** — templates need only state the task, name their input vars, and require JSON-schema output. Phase 4 refines wording.
- Run the full check suite after every task:
  ```
  uv run pytest packages/ apps/ -q -m "not integration and not e2e and not live_llm"
  uv run ruff check packages/ apps/ && uv run ruff format --check packages/ apps/
  uv run mypy packages/core/src packages/testing/src packages/db/src packages/llm/src apps/cli/src
  uv run lint-imports
  ```

---

## File Structure

**Created:**
- `packages/core/src/vera_core/models/plan.py` — `PlanStep`
- `packages/core/src/vera_core/models/code.py` — `CodeArtifact`
- `packages/core/src/vera_core/models/observation.py` — `ArtifactRef`, `Observation`
- `packages/core/src/vera_core/models/verdict.py` — `Verdict`
- `packages/core/src/vera_core/models/routing.py` — `RouterAction`, `RouterDecision`
- `packages/core/src/vera_core/agents/base.py` — `AgentContext`, `Agent` Protocol
- `packages/core/src/vera_core/agents/_types.py` — `PlanStepDraft`, `PlannerOutput`, `CoderOutput`, `FinalizerOutput`
- `packages/core/src/vera_core/agents/_shared.py` — `run_structured_agent`
- `packages/core/src/vera_core/agents/{analyzer,planner,coder,verifier,router,debugger,finalizer}.py`
- `packages/core/src/vera_core/agents/__init__.py`
- `packages/core/src/vera_core/prompts/registry.py` — `PromptTemplate`, `PromptRegistry`
- `packages/core/src/vera_core/prompts/__init__.py`
- `packages/core/src/vera_core/loop/__init__.py`
- `packages/core/src/vera_core/loop/context.py` — `LoopDeps`
- `packages/core/src/vera_core/loop/edges.py` — 4 predicates
- `packages/core/src/vera_core/loop/runner.py` — `run_precise`
- `packages/core/src/vera_core/loop/nodes/__init__.py` — `max_active_index` helper
- `packages/core/src/vera_core/loop/nodes/{analyze,retrieve,plan,code,execute,debug,verify,route,truncate,finalize}.py`
- `packages/testing/src/vera_testing/fakes/retriever.py` — `FakeRetriever`
- `packages/testing/src/vera_testing/scenarios.py` — `happy_path`, `multi_round`, `backtrack`
- `apps/cli/src/vera_cli/commands/run.py` — `vera run`
- `fixtures/payments/{payments.csv,merchant_data.json,fees.json,manifest.yaml}`
- Test files per §10 of the spec.

**Modified:**
- `packages/core/src/vera_core/models/run.py` — remove moved types, add `AbandonedBranch` + 3 `RunState` fields, re-export moved names
- `packages/core/src/vera_core/policies/backtrack.py`, `ports/sandbox.py`, `ports/event_bus.py` (any `from vera_core.models.run import ...` → narrowest module)
- `packages/core/src/vera_core/prompts/templates/**/*.jinja` — fill (analyzer/v3, planner/v5, coder/v4, verifier/v6, router/v3, debugger/v2, finalizer/v2)
- `packages/testing/src/vera_testing/fakes/llm.py` — add `.on()`
- `packages/testing/src/vera_testing/fakes/sandbox.py` — add `.push_observation()`
- `packages/testing/src/vera_testing/fakes/__init__.py` — export `FakeRetriever`
- `packages/testing/src/vera_testing/factories/domain.py` — add `make_plan_step`, `make_code_artifact`, `make_observation`, `make_verdict`
- `packages/testing/tests/test_fakes_conform.py` — add `FakeRetriever` pair
- `apps/cli/src/vera_cli/main.py` — register `run`
- `Makefile` — add `loop` target + `.PHONY`
- `packages/core/tests/test_exports.py` — loop surface

---

## Task 1: Decompose `models/run.py` + add backtrack bookkeeping

**Files:**
- Create: `packages/core/src/vera_core/models/{plan,code,observation,verdict,routing}.py`
- Modify: `packages/core/src/vera_core/models/run.py`
- Modify: `packages/core/src/vera_core/policies/backtrack.py`, `packages/core/src/vera_core/ports/sandbox.py`, `packages/core/src/vera_core/ports/event_bus.py` (fix imports if they reference moved types)
- Test: `packages/core/tests/test_models.py` (extend)

**Interfaces:**
- Produces:
  - `vera_core.models.plan.PlanStep` (unchanged fields: `index:int, text:str, acceptance_criteria:list[str], created_at_round:int, superseded:bool`, frozen)
  - `vera_core.models.code.CodeArtifact` (`language:Literal["python","sql"], source:str, sha256:str, parent_sha256:str|None`, frozen)
  - `vera_core.models.observation.ArtifactRef`, `vera_core.models.observation.Observation` (`stdout,stderr:str; exit_code,duration_ms:int; artifacts:list[ArtifactRef]; truncated:bool; .succeeded` property)
  - `vera_core.models.verdict.Verdict` (`sufficient:bool, reason:str(min_length=10), missing_aspects:list[str]`, frozen)
  - `vera_core.models.routing.RouterAction` (StrEnum `ADD_STEP,BACKTRACK`), `vera_core.models.routing.RouterDecision` (`action:RouterAction, backtrack_index:int|None, rationale:str`, frozen)
  - `vera_core.models.run.AbandonedBranch` (`round:int, from_index:int, removed_step_texts:list[str], removed_script_sha:str|None=None, rationale:str`, frozen)
  - `vera_core.models.run.RunState` gains `abandoned_branches:list[AbandonedBranch]=[]`, `script_checkpoints:dict[int,CodeArtifact]={}`, `observation_checkpoints:dict[int,Observation]={}`
  - `vera_core.models.run.__all__` still exports every moved name (re-import them).
  - `vera_core.models.__init__` and `test_exports.py` unchanged and passing.

- [ ] **Step 1: Write the failing test** — append to `packages/core/tests/test_models.py`:

```python
def test_abandoned_branch_round_trips():
    from vera_core.models.run import AbandonedBranch
    b = AbandonedBranch(round=2, from_index=1, removed_step_texts=["compute fees"],
                        removed_script_sha="abc", rationale="wrong join key")
    assert AbandonedBranch.model_validate_json(b.model_dump_json()) == b


def test_run_state_round_trips_with_checkpoints():
    from vera_core.models.code import CodeArtifact
    from vera_core.models.observation import Observation
    from vera_testing.factories.domain import make_run_state
    st = make_run_state()
    st.script_checkpoints[0] = CodeArtifact(source="print(1)", sha256="s0")
    st.script_checkpoints[1] = CodeArtifact(source="print(2)", sha256="s1")
    st.observation_checkpoints[0] = Observation(stdout="1", stderr="", exit_code=0, duration_ms=1)
    round_tripped = type(st).model_validate_json(st.model_dump_json())
    assert round_tripped.script_checkpoints[1].sha256 == "s1"   # int key survives
    assert round_tripped.observation_checkpoints[0].stdout == "1"


def test_moved_types_importable_from_new_and_old_paths():
    from vera_core.models.observation import Observation as ONew
    from vera_core.models.run import Observation as OOld
    from vera_core.models.verdict import Verdict as VNew
    from vera_core.models.run import Verdict as VOld
    assert ONew is OOld and VNew is VOld
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest packages/core/tests/test_models.py -k "abandoned or checkpoints or moved" -q` → FAIL (import errors).

- [ ] **Step 3: Create the five new model files.** Move each type verbatim from `run.py` (keep field defs, `model_config`, docstrings). Each file: `from __future__ import annotations`, minimal imports, `__all__`. `observation.py` holds both `ArtifactRef` and `Observation` (Observation references ArtifactRef). Example `verdict.py`:

```python
"""Verifier verdict model."""
from __future__ import annotations
from pydantic import BaseModel, Field


class Verdict(BaseModel):
    sufficient: bool
    reason: str = Field(min_length=10)
    missing_aspects: list[str] = Field(default_factory=list)
    model_config = {"frozen": True}


__all__ = ["Verdict"]
```

- [ ] **Step 4: Rewrite `run.py`.** Remove the moved class bodies. Add at top:

```python
from vera_core.models.code import CodeArtifact
from vera_core.models.observation import ArtifactRef, Observation
from vera_core.models.plan import PlanStep
from vera_core.models.routing import RouterAction, RouterDecision
from vera_core.models.verdict import Verdict
```

Add `AbandonedBranch` (frozen) and the three `RunState` fields (see Interfaces). Keep `RunState.model_config = {"frozen": False}`. Keep `__all__` listing every name including the moved and re-imported ones plus `AbandonedBranch`.

- [ ] **Step 5: Fix downstream imports.** Grep `packages/core/src` for `from vera_core.models.run import`. For `policies/backtrack.py` (`PlanStep, RunState`), `policies/truncation.py` (`Observation`), `policies/cycle_detection.py` (`PlanStep`), `ports/sandbox.py` (`CodeArtifact, Observation`), `ports/event_bus.py` — point each at the narrowest new module (`RunState` stays from `run`). `vera_testing/fakes/sandbox.py` imports `ArtifactRef, CodeArtifact, Observation` from `vera_core.models.run` — leave it (re-export keeps it working) or update; either passes.

- [ ] **Step 6: Run the full suite** (Global Constraints block). All green, mypy clean, `lint-imports` 3 kept. `test_exports.py` unmodified and passing.

- [ ] **Step 7: Record progress** — check this task's box; leave changes in working tree.

---

## Task 2: `PromptRegistry` + fill the templates

**Files:**
- Create: `packages/core/src/vera_core/prompts/registry.py`, `packages/core/src/vera_core/prompts/__init__.py`
- Modify: `packages/core/src/vera_core/prompts/templates/{analyzer/v3,planner/v5,coder/v4,verifier/v6,router/v3,debugger/v2,finalizer/v2}.jinja`
- Test: `packages/core/tests/test_prompt_registry.py`

**Interfaces:**
- Produces:
  - `PromptTemplate` (frozen dataclass): `agent:str, version:str, source:str, sha256:str`, method `render(**vars: object) -> str`
  - `PromptRegistry`: `__init__(self, templates_dir: Path | None = None)` (defaults to `prompts/templates`), `get(self, agent: str, version: str | None = None) -> PromptTemplate` (highest `vN` when version None; raises `KeyError` if unknown agent), `list_versions(self, agent: str) -> list[str]`
  - importable as `from vera_core.prompts import PromptRegistry, PromptTemplate`
- Consumes: nothing from other tasks.

- [ ] **Step 1: Write failing test** `packages/core/tests/test_prompt_registry.py`:

```python
import pytest
from vera_core.prompts import PromptRegistry


def test_get_resolves_highest_version():
    reg = PromptRegistry()
    t = reg.get("planner")
    assert t.version == "v5"
    assert t.agent == "planner"
    assert len(t.sha256) == 64


def test_render_requires_all_vars():
    reg = PromptRegistry()
    with pytest.raises(Exception):
        reg.get("verifier").render()  # StrictUndefined -> missing vars raise


def test_sha256_changes_with_content(tmp_path):
    d = tmp_path / "coder"
    d.mkdir()
    (d / "v1.jinja").write_text("hello {{ x }}")
    a = PromptRegistry(tmp_path).get("coder").sha256
    (d / "v1.jinja").write_text("hello {{ x }}!")
    b = PromptRegistry(tmp_path).get("coder").sha256
    assert a != b


def test_unknown_agent_raises():
    with pytest.raises(KeyError):
        PromptRegistry().get("nonesuch")
```

- [ ] **Step 2: Run → FAIL** (`ModuleNotFoundError: vera_core.prompts`).

- [ ] **Step 3: Implement `registry.py`:**

```python
"""Versioned Jinja prompt templates resolved by agent name."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, StrictUndefined

_DEFAULT_DIR = Path(__file__).parent / "templates"
_VERSION_RE = re.compile(r"^v(\d+)\.jinja$")
_ENV = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True, autoescape=False)


@dataclass(frozen=True)
class PromptTemplate:
    agent: str
    version: str
    source: str
    sha256: str

    def render(self, **variables: object) -> str:
        return _ENV.from_string(self.source).render(**variables)


class PromptRegistry:
    def __init__(self, templates_dir: Path | None = None) -> None:
        self._dir = templates_dir or _DEFAULT_DIR

    def _versions(self, agent: str) -> dict[str, Path]:
        agent_dir = self._dir / agent
        out: dict[str, Path] = {}
        if agent_dir.is_dir():
            for p in agent_dir.iterdir():
                m = _VERSION_RE.match(p.name)
                if m and p.stat().st_size > 0:
                    out[f"v{int(m.group(1))}"] = p
        return out

    def list_versions(self, agent: str) -> list[str]:
        return sorted(self._versions(agent), key=lambda v: int(v[1:]))

    def get(self, agent: str, version: str | None = None) -> PromptTemplate:
        versions = self._versions(agent)
        if not versions:
            raise KeyError(f"No prompt templates for agent {agent!r}")
        chosen = version or self.list_versions(agent)[-1]
        path = versions[chosen]
        source = path.read_text(encoding="utf-8")
        return PromptTemplate(agent, chosen, source, hashlib.sha256(source.encode()).hexdigest())


__all__ = ["PromptRegistry", "PromptTemplate"]
```

`prompts/__init__.py`: `from vera_core.prompts.registry import PromptRegistry, PromptTemplate` + `__all__`.

- [ ] **Step 4: Fill the seven templates.** Each is plain text with `{{ var }}` placeholders matching spec §6.3. Example `verifier/v6.jinja`:

```jinja
You are the VERA verifier. Decide whether the analysis answers the user's question.

Question: {{ query }}

Plan:
{% for step in plan %}- {{ step }}
{% endfor %}
Code that was run:
{{ code }}

Program output:
{{ observation }}

Judge whether the output correctly and completely answers the question. Set
`sufficient` true only if the numbers are right and nothing is missing. When
insufficient, list every missing aspect.

Respond only with JSON matching the required schema:
{"sufficient": bool, "reason": str (>=10 chars), "missing_aspects": [str]}
```

`planner/v5.jinja` vars: `query`, `descriptions` (list str), `existing_steps` (list str), `abandoned` (list str). `coder/v4.jinja` & `debugger/v2.jinja` vars per §6.3. `router/v3.jinja` vars: `query, verdict_reason, missing_aspects, plan`. `finalizer/v2.jinja` vars: `query, plan, observation, degraded`. `analyzer/v3.jinja` vars: `filename, kind, sample`. Keep each under ~25 lines. Leave `analyzer/formats/*.jinja` empty (Phase 7).

- [ ] **Step 5: Run** `uv run pytest packages/core/tests/test_prompt_registry.py -q` → PASS, then full suite → green.

- [ ] **Step 6: Record progress.**

---

## Task 3: Fakes — `.on()`, `FakeRetriever`, `push_observation`, factories

**Files:**
- Modify: `packages/testing/src/vera_testing/fakes/llm.py`, `packages/testing/src/vera_testing/fakes/sandbox.py`, `packages/testing/src/vera_testing/fakes/__init__.py`, `packages/testing/src/vera_testing/factories/domain.py`
- Create: `packages/testing/src/vera_testing/fakes/retriever.py`
- Modify: `packages/testing/tests/test_fakes_conform.py`
- Test: `packages/testing/tests/test_fakes_extra.py` (new)

**Interfaces:**
- Produces:
  - `FakeLLM.on(self, agent: str, obj: BaseModel | str, *, cost_usd: Decimal = Decimal("0.001")) -> None` — per-agent FIFO; `complete()` prefers the queue for the incoming `agent=` kwarg, falls back to the global queue.
  - `FakeSandbox.push_observation(self, obs: Observation) -> None`
  - `FakeRetriever(descriptions: list[FileDescription] | None = None)`; `.set_results(list[FileDescription])`; `async search(*, query, workspace_id, top_k=12, pinned_file_ids=None) -> list[FileDescription]` returns `descriptions[:top_k]`
  - factories: `make_plan_step(*, index=0, text="step", acceptance_criteria=None, created_at_round=0, superseded=False)`, `make_code_artifact(*, source="print(1)", sha256="sha", parent_sha256=None)`, `make_observation(*, stdout="ok", stderr="", exit_code=0, duration_ms=1)`, `make_verdict(*, sufficient=True, reason="looks correct enough", missing_aspects=None)`
- Consumes: Task 1 model modules.

- [ ] **Step 1: Write failing tests** `packages/testing/tests/test_fakes_extra.py`:

```python
import pytest
from vera_core.models.verdict import Verdict
from vera_core.ports import RetrieverPort
from vera_testing.factories.domain import make_file_description
from vera_testing.fakes import FakeLLM, FakeRetriever, FakeSandbox


async def test_fake_llm_on_routes_by_agent():
    llm = FakeLLM()
    llm.push_response("global")
    llm.on("verifier", Verdict(sufficient=True, reason="all good here"))
    v = await llm.complete(provider_connection_id=None, model_id="m", messages=[],
                           response_schema=Verdict, agent="verifier")
    assert v.parsed.sufficient is True
    g = await llm.complete(provider_connection_id=None, model_id="m", messages=[], agent="coder")
    assert g.content == "global"


async def test_fake_retriever_returns_top_k():
    r = FakeRetriever([make_file_description() for _ in range(5)])
    out = await r.search(query="q", workspace_id=None, top_k=3)
    assert len(out) == 3
    assert isinstance(r, RetrieverPort)


async def test_fake_sandbox_push_observation():
    from vera_testing.factories.domain import make_observation
    sb = FakeSandbox()
    sb.push_observation(make_observation(stdout="hi"))
    obs = await sb.execute(script=make_code_artifact_stub(), mounts=[], limits=_limits(), run_id=None)
    assert obs.stdout == "hi"
```

(helper stubs: import `make_code_artifact` and build `ResourceLimits()` inline — adjust imports so the test is self-contained.)

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement.**
  - `FakeLLM.__init__`: add `self._agent_queues: dict[str, list] = {}`. Add `on()`. In `complete()`, before the `if not self._queue` check: `queue = self._agent_queues.get(agent) or self._queue`; pop from `queue`; keep the existing exception + parsed-fallback logic operating on the popped item.
  - `FakeSandbox.push_observation(obs)`: `self._queue.append(obs)`.
  - `retriever.py`: implement per Interfaces. Import `FileDescription`, `FileId`, `WorkspaceId` from `vera_core.models`.
  - `fakes/__init__.py`: import + add `FakeRetriever` to `__all__`.
  - `factories/domain.py`: add the four `make_*` helpers + names to `__all__`.
  - `test_fakes_conform.py`: `from vera_testing.fakes import FakeRetriever`; `from vera_core.ports import RetrieverPort`; add `(FakeRetriever, RetrieverPort)` to `PAIRS`.

- [ ] **Step 4: Run** `uv run pytest packages/testing -q` → PASS (conformance incl. FakeRetriever), then full suite → green, mypy clean.

- [ ] **Step 5: Record progress.**

---

## Task 4: Agents (`base`, `_types`, `_shared`, 7 agents)

**Files:**
- Create: `packages/core/src/vera_core/agents/{__init__,base,_types,_shared,analyzer,planner,coder,verifier,router,debugger,finalizer}.py` (the 7 agent files currently exist and are empty)
- Test: `packages/core/tests/test_agents.py`

**Interfaces:**
- Consumes: `PromptRegistry` (Task 2); `FakeLLM.on` (Task 3); `AgentTier` from `vera_core.models.agent_config`; `Verdict`, `RouterDecision` from `vera_core.models`.
- Produces:
  - `agents.base.AgentContext` (frozen dataclass): `llm: LLMPort`, `defaults: AgentDefaults`, `registry: PromptRegistry`, `run_id: RunId | None`
  - `agents.base.Agent[TIn, TOut]` Protocol: attrs `name: str`, `tier: AgentTier`; `async def run(self, ctx: AgentContext, payload: TIn) -> TOut`
  - `agents._types`: `PlanStepDraft(text:str, acceptance_criteria:list[str]=[])`, `PlannerOutput(steps:list[PlanStepDraft])`, `CoderOutput(source:str)`, `FinalizerOutput(answer:str)` — all frozen Pydantic
  - `agents._shared.run_structured_agent(ctx, *, agent: str, tier: AgentTier, template_vars: dict[str, object], schema: type[ModelT]) -> tuple[ModelT, LLMResponse]` — raises `AgentOutputError` when `response.parsed` is not a `schema` instance
  - Each agent module exposes an instance, e.g. `planner = PlannerAgent()`, with `.name`, `.tier`, and `async def run(ctx, payload) -> <output>`:
    - `AnalyzerAgent.run(ctx, payload: AnalyzePayload) -> FileDescription` where `AnalyzePayload(filename:str, kind:str, sample:str)` (define in `_types`)
    - `PlannerAgent.run(ctx, payload: PlannerPayload) -> PlannerOutput`, `PlannerPayload(query:str, descriptions:list[str], existing_steps:list[str], abandoned:list[str])`
    - `CoderAgent.run(ctx, payload: CoderPayload) -> CoderOutput`, `CoderPayload(query:str, plan:list[str], last_stdout:str|None, last_stderr:str|None)`
    - `VerifierAgent.run(ctx, payload: VerifierPayload) -> Verdict`, `VerifierPayload(query:str, plan:list[str], code:str, observation:str)`
    - `RouterAgent.run(ctx, payload: RouterPayload) -> RouterDecision`, `RouterPayload(query:str, verdict_reason:str, missing_aspects:list[str], plan:list[str])`
    - `DebuggerAgent.run(ctx, payload: DebuggerPayload) -> CoderOutput`, `DebuggerPayload(code:str, stderr:str)`
    - `FinalizerAgent.run(ctx, payload: FinalizerPayload) -> FinalizerOutput`, `FinalizerPayload(query:str, plan:list[str], observation:str, degraded:bool)`
  - `agents/__init__.py` re-exports the 7 agent instances + `AgentContext` + all payload/output types.

- [ ] **Step 1: Write failing test** `packages/core/tests/test_agents.py`:

```python
import pytest
from vera_core.agents import (
    AgentContext, VerifierPayload, verifier, planner, PlannerPayload,
)
from vera_core.errors import AgentOutputError
from vera_core.models.verdict import Verdict
from vera_testing.factories.domain import make_agent_defaults
from vera_testing.fakes import FakeLLM
from vera_core.prompts import PromptRegistry


def _ctx(llm):
    return AgentContext(llm=llm, defaults=make_agent_defaults(), registry=PromptRegistry(), run_id=None)


async def test_verifier_returns_verdict():
    llm = FakeLLM()
    llm.on("verifier", Verdict(sufficient=False, reason="missing fee deduction",
                               missing_aspects=["fees"]))
    out = await verifier.run(_ctx(llm), VerifierPayload(
        query="q", plan=["a"], code="print(1)", observation="1"))
    assert isinstance(out, Verdict) and out.sufficient is False


async def test_planner_returns_steps():
    from vera_core.agents._types import PlannerOutput, PlanStepDraft
    llm = FakeLLM()
    llm.on("planner", PlannerOutput(steps=[PlanStepDraft(text="load csv"),
                                           PlanStepDraft(text="sum col")]))
    out = await planner.run(_ctx(llm), PlannerPayload(
        query="q", descriptions=["a csv"], existing_steps=[], abandoned=[]))
    assert len(out.steps) == 2


async def test_agent_raises_on_junk():
    llm = FakeLLM()
    llm.push_response("not json at all")
    with pytest.raises(AgentOutputError):
        await verifier.run(_ctx(llm), VerifierPayload(query="q", plan=[], code="", observation=""))
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `base.py` + `_types.py` + `_shared.py`** per Interfaces and spec §6.1/6.2. `_shared` uses `ctx.defaults.get_assignment(tier)`, `ctx.registry.get(agent).render(**template_vars)`, `ctx.llm.complete(...)` with `response_schema=schema, agent=agent`.

- [ ] **Step 4: Implement the 7 agent modules.** Each ~15 lines:

```python
"""Verifier agent — judges whether the analysis answers the question."""
from __future__ import annotations
from dataclasses import dataclass
from vera_core.agents._shared import run_structured_agent
from vera_core.agents.base import AgentContext
from vera_core.models.agent_config import AgentTier
from vera_core.models.verdict import Verdict


@dataclass(frozen=True)
class VerifierPayload:
    query: str
    plan: list[str]
    code: str
    observation: str


class VerifierAgent:
    name = "verifier"
    tier = AgentTier.REASONING

    async def run(self, ctx: AgentContext, payload: VerifierPayload) -> Verdict:
        verdict, _ = await run_structured_agent(
            ctx, agent=self.name, tier=self.tier,
            template_vars={"query": payload.query, "plan": payload.plan,
                           "code": payload.code, "observation": payload.observation},
            schema=Verdict)
        return verdict


verifier = VerifierAgent()
__all__ = ["VerifierAgent", "VerifierPayload", "verifier"]
```

Analyzer returns `FileDescription` — its template must yield JSON matching `FileDescription` (the FakeLLM `.on()` supplies it directly in tests, so the schema just needs to validate). For analyzer set `file_id` from payload — add `file_id: str` to `AnalyzePayload` and pass through, or have the node attach it. **Decision:** `AnalyzePayload` carries `file_id: str`; analyzer injects it into `template_vars` and the node trusts `FakeLLM` to return a matching `FileDescription`; for real runs Phase 4's prompt handles it.

- [ ] **Step 5: `agents/__init__.py`** re-exports. Run `uv run pytest packages/core/tests/test_agents.py -q` → PASS; full suite green; mypy clean; `lint-imports` green (agents live in `vera_core`, import only `vera_core.*`).

- [ ] **Step 6: Record progress.**

---

## Task 5: The loop — `context`, `edges`, `nodes/*`, `runner`

**Files:**
- Create: `packages/core/src/vera_core/loop/{__init__,context,edges,runner}.py`, `packages/core/src/vera_core/loop/nodes/{__init__,analyze,retrieve,plan,code,execute,debug,verify,route,truncate,finalize}.py`
- Modify: `packages/core/tests/test_exports.py`
- Test: `packages/core/tests/test_loop_edges.py`, `packages/core/tests/test_truncate.py`, `packages/core/tests/test_loop_scenarios.py`, `packages/core/tests/test_cycle_detection.py`

**Interfaces:**
- Consumes: Tasks 1–4 (models, `PromptRegistry`, agents, fakes); `vera_core.policies` (`apply_backtrack`, `truncate_observation`, `check_budget`, `CycleDetector`); ports (`LLMPort, SandboxPort, RetrieverPort, EventBusPort, ClockPort`); `DataMount, ResourceLimits` from `vera_core.ports.sandbox`; event models from `vera_core.models.events`.
- Produces:
  - `loop.context.LoopDeps` (frozen dataclass) — fields per spec §5.1: `llm, sandbox, retriever, event_bus, clock, defaults, registry, file_refs: list[FileRef], mounts: list[DataMount], cycle_detector: CycleDetector`
  - `loop.edges`: `execution_outcome(state) -> Literal["ok","crash","budget"]`, `verify_outcome(state) -> Literal["sufficient","insufficient","max_rounds"]`, `route_outcome(state, detector) -> Literal["add_step","backtrack"]`, `debug_outcome(state) -> Literal["fixed","retry","max_retries"]`
  - `loop.nodes.max_active_index(state) -> int`
  - each node `async def <name>(state: RunState, deps: LoopDeps) -> RunState`
  - `loop.runner.run_precise(state: RunState, deps: LoopDeps) -> RunState`
  - `loop.__init__` re-exports `run_precise`, `LoopDeps`

- [ ] **Step 1: Write failing tests.**

`test_loop_edges.py` — table-drives each predicate across its outputs (build states with factories; e.g. budget-exhausted state → `execution_outcome == "budget"`; verdict sufficient → `verify_outcome == "sufficient"`; `round >= max_rounds` → `"max_rounds"`; router `BACKTRACK` w/ index → `route_outcome == "backtrack"`).

`test_truncate.py` — hypothesis:

```python
from hypothesis import given, strategies as st
from vera_core.loop.nodes.truncate import truncate
from vera_core.loop.context import LoopDeps
# build a RunState with N plan steps (indices 0..N-1), script_checkpoints[i] and
# observation_checkpoints[i] for each i, a RouterDecision(action=BACKTRACK, backtrack_index=j)
# assert post-truncate: active_plan indices == [0..j-1]; state.script == checkpoints[j-1]
# (or None if j==0); every observation_checkpoint key < j; len(state.observations) == j;
# len(state.abandoned_branches) == 1 and .from_index == j
```

`test_loop_scenarios.py` — uses `vera_testing.scenarios` (Task 6). **Depends on Task 6 for the scenario builders** — if Task 6 runs after, stub scenarios inline here first, then Task 6 replaces the import. Recommended: do Task 6's `scenarios.py` as Step 2 of *this* task (they are tightly coupled). Assertions per spec §10.

`test_cycle_detection.py` — planner `.on("planner", …)` the same 1-step plan 4×, verifier always insufficient, router always `add_step`; assert `run_precise` returns with `status in (SUCCEEDED, FAILED)` and `llm.call_count` bounded (< 30).

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `context.py` and `edges.py`** exactly per spec §5.1 / §5.4.

- [ ] **Step 4: Implement `nodes/__init__.py`** with `max_active_index` and re-exports.

- [ ] **Step 5: Implement the 10 nodes** per the spec §5.3 table. Key points:
  - Every LLM node builds `AgentContext(llm=deps.llm, defaults=deps.defaults, registry=deps.registry, run_id=state.run_id)` and calls the agent instance.
  - `analyze`: iterate `deps.file_refs`; emit `AnalysisStartedEvent(run_id=state.run_id, file_count=len(...))` then per file `FileAnalyzedEvent`. Append each `FileDescription`.
  - `plan`: render abandoned constraints (spec §6.3 string) from `state.abandoned_branches`; call planner; convert `PlannerOutput.steps` → `PlanStep`s appended after the current max active index with `created_at_round=state.round`; emit `PlanUpdatedEvent(steps=[s.text for s in state.active_plan])`.
  - `code`: compute `sha256 = hashlib.sha256(source.encode()).hexdigest()`; `parent = state.script.sha256 if state.script else None`; set `state.script`; `idx = max_active_index(state)`; `state.script_checkpoints[idx] = state.script`; emit `CodeGeneratedEvent`.
  - `execute`: `limits = ResourceLimits()`; try `deps.sandbox.execute(script=state.script, mounts=deps.mounts, limits=limits, run_id=state.run_id)`; `except SandboxTimeoutError:` build `Observation(stdout="", stderr="timeout", exit_code=124, duration_ms=limits.timeout_s*1000)`. Append `truncate_observation(obs)`; `state.observation_checkpoints[max_active_index(state)] = obs`; emit events.
  - `debug`: `state.debug_attempts += 1`; call debugger with `state.script.source` + last stderr; set new `state.script` (parent = broken sha); emit `DebugAttemptEvent(attempt=state.debug_attempts)`.
  - `verify`: call verifier; append `Verdict`; emit `VerifyVerdictEvent`.
  - `route`: call router; append `RouterDecision`; emit `RouteDecisionEvent`.
  - `truncate`: `j = state.routes[-1].backtrack_index`; capture pre sha (`state.script.sha256 if state.script else None`) and removed step texts (active steps with `index >= j`); `apply_backtrack(state, j)`; `state.script = state.script_checkpoints.get(j - 1)`; `state.observations = [state.observation_checkpoints[i] for i in sorted(state.observation_checkpoints) if i < j]`; delete checkpoint keys `>= j` from both dicts; `state.abandoned_branches.append(AbandonedBranch(round=state.round, from_index=j, removed_step_texts=..., removed_script_sha=pre_sha, rationale=state.routes[-1].rationale))`; `state.debug_attempts = 0`.
  - `finalize(state, deps, *, degraded=False)`: call finalizer; `state.answer = out.answer`; `state.status = RunStatus.FAILED if degraded and not state.observations else RunStatus.SUCCEEDED`; `state.finished_at = deps.clock.utcnow()`; emit `RunFinishedEvent` (or `RunFailedEvent(error="degraded")` when `state.status == FAILED`).
  - Each LLM node: `state.cost_usd += resp.cost_usd or Decimal("0")`; `state.total_tokens += resp.input_tokens + resp.output_tokens`. (Agents return only the model — extend the 7 agent `.run` signatures to also return the `LLMResponse`? No — keep agents clean. Instead nodes call `run_structured_agent` directly? Simplest: have each agent's `.run` return `tuple[Output, LLMResponse]`. **Decision:** agents return the tuple; update Task 4 tests accordingly — adjust `test_agents.py` to unpack. Update the Task 4 Interfaces note: `async def run(...) -> tuple[TOut, LLMResponse]`.)

  > **Cross-task correction:** Task 4 agents `.run()` returns `tuple[<Output>, LLMResponse]`. Update Task 4 Step 1 tests to `out, _ = await verifier.run(...)`.

  - `runner.run_precise`: the control flow in spec §5.2, including the `if deps.cycle_detector.is_cycling(): return await finalize(..., degraded=True)` guard right after `plan`, and `deps.cycle_detector.record(state.active_plan)` inside/after `plan`. Set `state.status = RunStatus.RUNNING` at entry.

- [ ] **Step 6: `loop/__init__.py`** re-exports; extend `test_exports.py` with a `test_loop_surface` asserting `from vera_core.loop import run_precise, LoopDeps`.

- [ ] **Step 7: Run** all new loop tests + full suite → green; mypy clean; `lint-imports` green.

- [ ] **Step 8: Record progress.**

---

## Task 6: Scenarios, fixtures, CLI `vera run`, Makefile

**Files:**
- Create: `packages/testing/src/vera_testing/scenarios.py`, `packages/testing/tests/test_scenarios.py`
- Create: `fixtures/payments/{payments.csv,merchant_data.json,fees.json,manifest.yaml}`
- Create: `apps/cli/src/vera_cli/commands/run.py`, `apps/cli/tests/test_run_command.py`
- Modify: `apps/cli/src/vera_cli/main.py`, `Makefile`

**Interfaces:**
- Consumes: `run_precise`, `LoopDeps` (Task 5); all fakes (Task 3); `PromptRegistry` (Task 2); `make_agent_defaults`, `make_file_description` (factories).
- Produces:
  - `vera_testing.scenarios`: `happy_path() -> Scenario`, `multi_round() -> Scenario`, `backtrack() -> Scenario` where `Scenario` is a frozen dataclass `(llm: FakeLLM, sandbox: FakeSandbox, retriever: FakeRetriever, expected_answer_substring: str, file_count: int)`
  - `vera_cli.commands.run.run` — a Typer command function; signature `run(workspace: Path, query: str, fake_llm: bool = False, scenario: str = "happy", max_rounds: int = 10)`

- [ ] **Step 1: Write failing tests.**

`packages/testing/tests/test_scenarios.py`:

```python
import pytest
from vera_testing.scenarios import happy_path, multi_round, backtrack
from vera_testing.factories.domain import make_agent_defaults, make_run_state
from vera_testing.fakes import FakeEventBus
from vera_core.ports.clock import FixedClock
from vera_core.prompts import PromptRegistry
from vera_core.policies import CycleDetector
from vera_core.loop import run_precise, LoopDeps
from datetime import UTC, datetime


@pytest.mark.parametrize("builder", [happy_path, multi_round, backtrack])
async def test_scenario_drains_cleanly(builder):
    sc = builder()
    st = make_run_state()
    deps = LoopDeps(llm=sc.llm, sandbox=sc.sandbox, retriever=sc.retriever,
                    event_bus=FakeEventBus(), clock=FixedClock(datetime.now(UTC)),
                    defaults=make_agent_defaults(), registry=PromptRegistry(),
                    file_refs=[], mounts=[], cycle_detector=CycleDetector(max_repeats=3))
    out = await run_precise(st, deps)
    assert out.answer and sc.expected_answer_substring in out.answer
    assert sc.llm.queue_length == 0        # no leftover global responses
```

`apps/cli/tests/test_run_command.py`:

```python
from typer.testing import CliRunner
from vera_cli.main import app

runner = CliRunner()


def test_run_without_fake_llm_exits_1(tmp_path):
    r = runner.invoke(app, ["run", "--workspace", str(tmp_path), "--query", "q"])
    assert r.exit_code == 1
    assert "Phase 4" in r.output


def test_run_backtrack_scenario(tmp_path):
    r = runner.invoke(app, ["run", "--workspace", "fixtures/payments",
                            "--query", "Total chargeback amount?",
                            "--fake-llm", "--scenario", "backtrack"])
    assert r.exit_code == 0
    assert "backtrack" in r.output.lower()
    assert "Answer:" in r.output
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Create fixtures** — hand-author the 3 data files (spec §9) and `manifest.yaml`. `payments.csv` ~20 rows; chargeback amounts must sum to a round number referenced in `manifest.yaml` and in the scenario `expected_answer_substring`.

- [ ] **Step 4: Implement `scenarios.py`.** Each builder creates `FakeLLM`, `FakeSandbox`, `FakeRetriever([make_file_description() x3])` and scripts them with `.on(agent, obj)`:
  - `happy_path`: `.on("analyzer", make_file_description())` ×3 (or set `file_refs=[]` in CLI and skip); `.on("planner", PlannerOutput(steps=[PlanStepDraft(text="load"), PlanStepDraft(text="sum chargebacks")]))`; `sandbox.push_success(stdout="chargeback_total=1250.00")`; `.on("verifier", Verdict(sufficient=True, reason="total is correct"))`; `.on("finalizer", FinalizerOutput(answer="Total chargeback amount is $1250.00"))`. `expected_answer_substring="1250"`.
  - `multi_round`: same start, but first `.on("verifier", Verdict(sufficient=False, reason="ignored refunds", missing_aspects=["refunds"]))`, `.on("router", RouterDecision(action=ADD_STEP, rationale="add refund netting"))`, second `.on("planner", PlannerOutput(steps=[PlanStepDraft(text="net refunds")]))`, `sandbox.push_success(stdout="chargeback_total=1250.00")` again, `.on("verifier", Verdict(sufficient=True, reason="now correct"))`, finalizer.
  - `backtrack`: after first insufficient verdict, `.on("router", RouterDecision(action=BACKTRACK, backtrack_index=1, rationale="wrong grouping key"))`; then `.on("planner", PlannerOutput(steps=[PlanStepDraft(text="group by merchant then sum")]))`, coder, `sandbox.push_success(stdout="chargeback_total=1250.00")`, `.on("verifier", Verdict(sufficient=True, reason="correct after regroup"))`, finalizer. Provide enough `.on("coder", CoderOutput(source="..."))` and `sandbox.push_success(...)` for every code/execute pass.
  - Count coder/execute passes carefully against the runner flow; add a comment per scenario tallying node calls.

- [ ] **Step 5: Implement `commands/run.py`.**

```python
"""`vera run` — execute the DS-STAR loop (fake-LLM only until Phase 4)."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import typer

SUPPORTED = {".csv", ".json", ".xlsx", ".parquet", ".md", ".txt", ".pdf", ".sqlite", ".zip"}


def run(
    workspace: Path = typer.Option(..., exists=True, file_okay=False),
    query: str = typer.Option(...),
    fake_llm: bool = typer.Option(False, "--fake-llm"),
    scenario: str = typer.Option("happy", help="happy | multiround | backtrack"),
    max_rounds: int = typer.Option(10),
) -> None:
    if not fake_llm:
        typer.echo("Real LLM execution lands in Phase 4. Re-run with --fake-llm.")
        raise typer.Exit(1)
    file_count = sum(1 for p in workspace.iterdir() if p.suffix.lower() in SUPPORTED)
    result = asyncio.run(_run_fake(scenario, query, max_rounds, file_count))
    typer.echo(f"Analyzed {file_count} files")
    backtracks = len(result.abandoned_branches)
    typer.echo(f"Plan: {len(result.active_plan)} steps"
               + (f" ({backtracks} backtracked)" if backtracks else ""))
    typer.echo(f"Rounds: {result.round}   Cost: ${result.cost_usd:.4f}   Tokens: {result.total_tokens}")
    typer.echo(f"Answer: {result.answer}")


async def _run_fake(scenario: str, query: str, max_rounds: int, file_count: int):
    from vera_core.loop import LoopDeps, run_precise
    from vera_core.policies import CycleDetector
    from vera_core.prompts import PromptRegistry
    from vera_core.ports.clock import FixedClock
    from vera_testing import scenarios
    from vera_testing.factories.domain import make_agent_defaults, make_run_state
    from vera_testing.fakes import FakeEventBus

    builder = {"happy": scenarios.happy_path, "multiround": scenarios.multi_round,
               "backtrack": scenarios.backtrack}[scenario]
    sc = builder()
    state = make_run_state(query=query)
    state.budget = state.budget.model_copy(update={"max_rounds": max_rounds})
    deps = LoopDeps(llm=sc.llm, sandbox=sc.sandbox, retriever=sc.retriever,
                    event_bus=FakeEventBus(), clock=FixedClock(datetime.now(UTC)),
                    defaults=make_agent_defaults(), registry=PromptRegistry(),
                    file_refs=[], mounts=[], cycle_detector=CycleDetector(max_repeats=3))
    return await run_precise(state, deps)
```

- [ ] **Step 6: Register in `main.py`** — `from vera_cli.commands.run import run` + `app.command()(run)`.

- [ ] **Step 7: `Makefile`** — add `loop` to `.PHONY` and:
```make
loop:
	uv run vera run --workspace ./fixtures/payments --query "Total chargeback amount?" --fake-llm --scenario backtrack
```

- [ ] **Step 8: Run** `uv run pytest packages/testing/tests/test_scenarios.py apps/cli/tests/test_run_command.py -q` → PASS; full suite green; mypy clean; `lint-imports` green. Then `uv run vera run --workspace ./fixtures/payments --query "Total chargeback amount?" --fake-llm --scenario backtrack` prints the 4 lines.

- [ ] **Step 9: Record progress.**

---

## Task 7: Integration pass — exit gate + completion notes

**Files:**
- Modify: any test/import fixups surfaced
- Create: `docs/superpowers/plans/completed/2026-08-28-phase-3-dsstar-loop-notes.md`

- [ ] **Step 1: Run the full exit gate** (spec §11) verbatim. Capture output.
- [ ] **Step 2: Fix any red.** Common: mypy strict on new dataclasses (annotate everything), ruff `SIM`/`B` nits, event `created_at` deprecation (leave — pre-existing pattern), int-key dict serialization.
- [ ] **Step 3: `make loop`** — confirm it prints `Analyzed 3 files / Plan: N steps (1 backtracked) / … / Answer: …`.
- [ ] **Step 4: Count tests** before/after; write completion notes in the Phase 2 notes format (what shipped per file group, gate output, "not verifiable here" items, follow-ups). No git.

---

## Self-Review (completed against the spec)

- **§2 D1–D6 decisions** → Tasks 1 (D4, D5), 2 (D3), 5 (D1), 6 (D6), scope D2 honored (no research agents). ✓
- **§3 model changes** → Task 1. ✓
- **§4 module layout** → Tasks 2, 4, 5. ✓
- **§5 loop (nodes, runner, edges)** → Task 5, node table transcribed into Step 5. ✓
- **§6 agents & prompts** → Tasks 2 (registry + templates), 4 (agents). ✓
- **§7 fakes & scenarios** → Task 3 (fakes), Task 6 (scenarios). ✓
- **§8 CLI** → Task 6. ✓
- **§9 fixtures** → Task 6 Step 3. ✓
- **§10 testing table** → every row mapped: `test_models` (T1), `test_agents` (T4), `test_prompt_registry` (T2), `test_loop_edges`/`test_loop_scenarios`/`test_truncate`/`test_cycle_detection` (T5), `test_fakes_conform`+`test_fakes_extra` (T3), `test_scenarios` (T6), `test_run_command` (T6), `test_exports` (T5). ✓
- **§11 exit gate** → Task 7. ✓
- **Type consistency fix applied:** agents `.run()` returns `tuple[Output, LLMResponse]` (noted in Task 5 Step 5 as a cross-task correction to Task 4). Executors must apply it when doing Task 4.
- **Placeholder scan:** no TBD/TODO; every code step has real code or an exact transcription target in the spec.
