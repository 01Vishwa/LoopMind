# Phase 3 — DS-STAR loop — final code review

**Date:** 2026-08-28
**Reviewer:** whole-branch review against
`docs/superpowers/specs/2026-08-28-phase-3-dsstar-loop-design.md` (§3, §5, §6).
**Scope:** quality + correctness. The exit gate already passes (146 tests, ruff /
mypy / lint-imports green, `vera run --fake-llm --scenario backtrack` prints a
correct result), so nothing below is a "does it run" finding.

**Verdict:** the state machine matches the spec's control flow closely and
`account()` is correct everywhere, but the backtrack machinery — the phase's
stated "money" feature — is structurally broken in a way the tests are shaped
not to catch.

Counts: **3 Critical, 8 Important, 14 Minor.**

---

## Critical

### C1. `backtrack_index` is produced positionally but consumed as an absolute plan index

`loop/nodes/route.py:19` (and `verify.py:17`, `finalize.py:18`, `code.py:21`)
pass the plan to the LLM as `plan=[s.text for s in state.active_plan]` — a bare
list of strings with no index numbers. The router therefore can only answer with
a **position in that list**. `loop/nodes/truncate.py:12-19` and
`policies/backtrack.py:38` then treat that number as an **absolute
`PlanStep.index`** (`step.index >= backtrack_to_index`).

Position and index agree only until the first backtrack. `loop/nodes/plan.py:44`
computes `max_index = max((s.index for s in state.plan), default=-1)` over the
**whole** plan including superseded steps, so new step indices continue past the
abandoned ones and the active plan develops gaps. Verified empirically on the
shipped `backtrack()` scenario — the final plan is:

```
(0, superseded=False, 'Load payments.csv')
(1, superseded=True,  'Sum chargebacks grouped by capture day')
(2, superseded=False, 'Sum chargebacks grouped by merchant')
```

`active_plan` is `[index 0, index 2]`, so position 1 is index 2.

Failure scenario: after one backtrack the plan grows to active indices
`[0, 2, 3]`. The verifier/router are shown three step texts; the router decides
the third one (position 2) is wrong and returns `backtrack_index=2`.
`apply_backtrack(state, 2)` supersedes every step with `index >= 2` — killing
both the third *and* the second active step. The run silently discards correct
work, replans from the wrong point, and the `AbandonedBranch.removed_step_texts`
recorded for the planner names a step the router never objected to.

Fix direction: either render the plan to the router as `f"{s.index}: {s.text}"`
and document `backtrack_index` as the absolute index, or map
position → `active_plan[pos].index` in the `route`/`truncate` node. Pick one and
assert it in a test.

### C2. Checkpoint keys are sparse, so `script_checkpoints.get(j - 1)` almost always misses

Spec §5.3 keys the checkpoints by `max_active_index`:
`code.py:31` writes `state.script_checkpoints[max_active_index(state)]` and
`execute.py:41` writes `state.observation_checkpoints[max_active_index(state)]`.
That produces **one key per round — the highest index only** — never a key per
step. `truncate.py:21` then restores with an exact lookup,
`state.script_checkpoints.get(j - 1)`, and `truncate.py:22-24` rebuilds
observations from keys strictly `< j`.

`j - 1` is a checkpoint key only in the degenerate case where an earlier round's
max active index happened to be exactly `j - 1`. Instrumented run of the shipped
`backtrack()` scenario:

```
PRE  script_ckpts: [1]  obs_ckpts: [1]  obs: 1  plan idx: [0, 1]
POST script: None       obs: 0          ckpts: []
```

So in the phase's flagship test the script restore silently yields `None` and the
entire observation history is erased. The subsequent `plan`→`code` regenerates
from scratch, which is why the scenario still "passes" — the checkpoint machinery
(D5, the whole reason `script_checkpoints` / `observation_checkpoints` exist) is
a no-op in every realistic case.

Failure scenario: a 6-step plan backtracked at `j = 4` should resume from the
script that produced steps 0–3. It resumes from `None`, discards all six
observations, and re-derives everything — every backtrack costs a full replay and
the run loses the intermediate observations the product promises to ship with the
answer.

Fix direction: restore from the greatest key strictly less than `j`
(`max((k for k in state.script_checkpoints if k < j), default=None)`), or write a
checkpoint per step index rather than per round. Then fix C5 (test masks this).

### C3. A degraded finalize reports `SUCCEEDED` whenever *any* observation exists — including only-failed ones

`loop/nodes/finalize.py:25`:

```python
state.status = RunStatus.FAILED if degraded and not state.observations else RunStatus.SUCCEEDED
```

Spec §5.3 says `FAILED if degraded and no **usable** observation`. The check tests
mere presence, not `Observation.succeeded`.

Failure scenario: the coder emits a script that raises. The debug inner loop
(`runner.py:39-43`) runs 3 attempts, all crash, `debug_attempts >= 3` →
`finalize(degraded=True)`. `state.observations` holds three `exit_code != 0`
observations, so the run is reported `SUCCEEDED`, `state.error` is left `None`,
and `RunFinishedEvent` is emitted instead of `RunFailedEvent`. The finalizer is
handed `observation=last.stdout` which is `""`, so the "successful" answer is
whatever the LLM invents from an empty observation. Once Phase 6 wires SSE, the
UI will show a green run for a total failure.

Fix: `not any(o.succeeded for o in state.observations)`.

---

## Important

### I1. `debug_attempts` is never reset per round, only on truncate

`debug.py:15` increments and `truncate.py:39` resets. Nothing resets it when the
loop takes the `add_step` path, so the debug budget is per-run, not per-round.

Failure scenario: round 1 needs all 3 debug attempts and succeeds on the third.
Verifier says insufficient → router `add_step` → round 2's new script has a
trivial typo. `runner.py:40` sees `debug_attempts (3) >= max_debug_attempts (3)`
and finalizes degraded **without a single debug attempt in round 2**. The run
dies on a one-line fix. Reset `debug_attempts = 0` at the top of each outer
iteration (or after a successful execute).

### I2. The script checkpoint is stale after a debug fix

`code.py:30-31` checkpoints the coder's script. `debug.py:29-33` replaces
`state.script` with the corrected artifact but never updates
`state.script_checkpoints`.

Failure scenario: round 1 — coder emits A (broken), checkpoint`[k] = A`, debugger
emits B (works), execute succeeds. Round 2 adds a step and later backtracks past
`k`. Once C2 is fixed and the restore actually resolves, the loop restores **A —
the known-broken script** — as the resumption point, and immediately burns the
debug budget re-fixing a bug it already fixed. `debug.py` must refresh the
checkpoint at the same key `code.py` wrote.

### I3. An out-of-range `backtrack_index` escapes `run_precise` as an uncaught `ValueError`

`truncate.py:19` calls `apply_backtrack(state, j)` with no validation.
`policies/backtrack.py:26-35` raises `ValueError` when the plan is empty or `j` is
not a plan index. `RouterDecision.backtrack_index` (`models/routing.py:17`) is a
bare `int | None` with no `ge=0` bound, and `runner.py` has no `try/except`
anywhere.

Failure scenario: a real (Phase 4) router hallucinates `backtrack_index=7` on a
3-step plan. `ValueError("Backtrack index 7 is not in plan…")` propagates out of
`run_precise`, past the API layer, as a 500 with no `RunFailedEvent`, no
`finished_at`, and a run stuck in `RUNNING` forever. Clamp `j` to the active plan
(or treat an invalid index as `add_step`) and, at minimum, make the runner
degrade rather than raise.

### I4. `plan`'s prefix-append is exact string equality — a reworded restatement duplicates the whole plan

`plan.py:20-43`: `_is_prefix` compares `active_texts` to the draft texts with
`==`. If the match fails, **every** draft is appended.

Failure scenario (the common one — this fails *toward* corruption, not toward
safety): round 1 plan is `["Load payments.csv", "Sum the chargeback amounts"]`.
Round 2 the planner restates it with one word changed —
`["Load the payments.csv", "Sum the chargeback amounts", "Group by merchant"]`.
`_is_prefix` is False, so all three drafts are appended and the active plan
becomes five steps containing two near-duplicate "load" steps and a duplicate
"sum" step. The coder is then handed a self-contradictory plan. Worse, because
the fingerprint changes every round, `CycleDetector` never fires
(`runner.py:31`) and the run burns all `max_rounds`.

The docstring in `scenarios.py:7-11` acknowledges the contract ("every planner
response below returns the CUMULATIVE plan") — that contract is enforced nowhere
except in the fakes, and no prompt in `templates/planner/` can guarantee it.
Consider matching on normalised text, or having the planner return only new steps
and dropping the prefix heuristic entirely.

### I5. `test_truncate.py` sets up a checkpoint shape the loop never produces — which is precisely what hides C2

`test_truncate.py:45-51` populates `script_checkpoints[i]` and
`observation_checkpoints[i]` for **every** `i in range(n)`. The loop only ever
writes one key per round (C2). Under that dense precondition
`script_checkpoints.get(j - 1)` always hits and `len(observations) == j` always
holds, so the hypothesis property at lines 58-66 is vacuously true of a function
that is broken for the real input distribution.

The property test should be driven by the loop's own writer (`code`/`execute`) or
should draw a *sparse* key set. As written it is the most misleading test in the
branch: it looks like the strongest test and validates the least.

### I6. The debug / crash / timeout path has zero coverage through `run_precise`, and `debug_outcome` is dead

No test in `packages/core/tests`, `packages/testing/tests`, or `apps/cli/tests`
pushes a failing or timing-out observation through the loop —
`FakeSandbox.push_failure` and `push_timeout` are never called. Consequently:

- the inner `while` at `runner.py:39-43` is never executed,
- the `max_debug_attempts` exit at `runner.py:40-41` is never executed,
- `debug.py` in its entirety is never executed,
- the `SandboxTimeoutError` branch at `execute.py:31-37` is never executed,
- `edges.py:34 debug_outcome` is exported and unit-tested in isolation but is
  **called by nothing** — the runner reimplements its `max_retries` arm inline at
  `runner.py:40`. Dead code duplicating a live inline check.

I1 and I2 both live in exactly this untested region. Add a fourth scenario
(`crash_then_fix()`) and a fifth (`crash_exhausts_debug_budget()`).

### I7. `test_cycle_detection.py` asserts almost nothing

Lines 47-49:

```python
assert out.status in (RunStatus.SUCCEEDED, RunStatus.FAILED)
assert out.answer is not None
assert llm.call_count < 30
```

`status in (SUCCEEDED, FAILED)` is a tautology — those are the only two statuses
`finalize` can set. The test never asserts the cycle detector was the reason the
loop stopped (a `max_rounds` exit would satisfy it identically), never asserts
`degraded=True` was the finalize path, never asserts the plan stayed at one step,
and `< 30` is loose against an actual count of ~11. The spec's requirement
("runner finalizes `degraded=True` … assert bounded call count") is only half met.

Assert `len(out.verdicts) == 2`, `len(out.active_plan) == 1`, an exact
`llm.call_count`, and — once C3 is fixed and degraded is observable — the
degraded outcome itself.

### I8. The budget arm of `execution_outcome` is half-unreachable and half-untested, and discards good results

`edges.py:12-16` returns `"budget"` from `check_budget`, which fires on
`round >= max_rounds` **or** `cost_usd >= max_cost_usd`
(`policies/termination.py:17-21`).

- The **round** arm is unreachable from `runner.py`: `state.round += 1`
  (line 49) is immediately followed by `verify_outcome`, which returns
  `"max_rounds"` and finalizes (lines 51-53). Control never re-enters
  `execution_outcome` with `round == max_rounds`.
  `test_loop_edges.py:39-43` tests it by hand-setting `st.round`, so the dead arm
  looks covered.
- The **cost** arm is live but never exercised end-to-end (`FakeLLM` charges
  $0.001/call against a $5.00 default; the whole backtrack scenario costs $0.008).
- Semantically, `execution_outcome` returns `"budget"` even when the observation
  **succeeded** (`edges.py:13` short-circuits before reading `obs.succeeded`). A
  run whose cost crosses the limit on the very call that produced the right
  answer is finalized `degraded=True` without ever being verified — and, per C3,
  is then reported `SUCCEEDED` anyway.

---

## Minor

1. **`agents/base.py:24` — the `Agent` Protocol is a lying, unused contract.** It
   declares `async def run(self, ctx, payload) -> TOut`, but every agent returns
   `tuple[TOut, LLMResponse]` (`planner.py:28`, `verifier.py:26`, …). No agent
   satisfies it, nothing is annotated as `Agent[...]`, and mypy never checks it.
   Either fix the return type to `tuple[TOut, LLMResponse]` and annotate the
   module-level singletons, or delete it.
2. **`edges.py:27` — `route_outcome`'s `detector` parameter is unused.** It
   matches the spec's own §5.4 snippet, but the cycle guard actually lives at
   `runner.py:30-32`, so the parameter is pure ceremony that every caller and
   test must supply.
3. **`agents/base.py:21` — `run_id: RunId | None = None`** where spec §6.1 says
   `run_id: RunId` (required). A default of `None` silently drops run attribution
   from `llm_calls` in Phase 5. `build_context` (`context.py:43`) always passes
   one, so nothing is gained by the default.
4. **`prompts/registry.py:47-54` re-reads the template from disk and
   `registry.py:27` recompiles the Jinja source on *every* LLM call.** Seven
   agents × N rounds of `stat` + `read_text` + `Environment.from_string`. Also
   means a template edited mid-run changes the recorded sha256 between calls.
   Cache `PromptTemplate` per `(agent, version)`.
5. **`registry.py:40` silently skips zero-byte templates** (`p.stat().st_size > 0`).
   A truncated `verifier/v6.jinja` falls back to `v5` with no warning, and an
   explicit `get("verifier", "v6")` raises a bare `KeyError('v6')` from
   `versions[chosen]` rather than the informative message on line 50.
6. **`execute.py:16` raises a bare `RuntimeError`**, violating the repo
   convention that errors subclass `VeraError` with `status` / `type_uri`
   (CLAUDE.md, `errors.py`). It maps to an untyped 500 rather than
   `application/problem+json`.
7. **Duplicated policy surfaces, both unused by the loop.**
   `RunState.budget_exhausted()` (`models/run.py:100`) reimplements
   `termination.check_budget`; `policies/backtrack.py:46 active_steps()`
   reimplements `RunState.active_plan` — and *sorts by index* while the property
   does not, so the two disagree the moment plan order and index order diverge
   (which C1 shows they do). Pick one of each.
8. **`retrieve.py:15` silently no-ops on an empty retriever result**
   (`if results:`), so a retriever that legitimately finds nothing is
   indistinguishable from one that is unwired — the loop proceeds on the full
   unfiltered analyze output. It also never passes `pinned_file_ids`, which the
   port accepts.
9. **`packages/testing/tests/test_scenarios.py:40` asserts on a private
   attribute** (`sc.sandbox._queue`). Expose a `queue_length` property on
   `FakeSandbox` mirroring `FakeLLM.queue_length` (`fakes/llm.py:209`). The test
   functions in that file are also the only unannotated ones in the branch
   (lines 33, 43, 52) — they escape mypy only because `packages/testing/tests`
   is outside the checked paths.
10. **`scenarios.py:43 Scenario.file_count`** is set to `3` by all three builders
    and asserted by nothing anywhere. Either assert it in the CLI test or drop
    the field (YAGNI).
11. **`test_loop_scenarios.py:55-63` omits two of spec §10's Scenario C
    assertions** — "`script_checkpoints` pruned" and the superseded-step content.
    (`any(s.superseded ...)` at line 62 is weaker than "superseded steps
    present" — it does not check *which*.) Nothing anywhere asserts
    `cost_usd` / `total_tokens` after a run, so the accounting in §5.3 is
    unverified by any test even though it is implemented correctly.
12. **Event round numbers are off by one relative to verdicts.**
    `runner.py:49` increments `round` *after* execute, so `PlanUpdatedEvent`
    (`plan.py:59`), `CodeGeneratedEvent` (`code.py:36`) and
    `ExecutionStartedEvent`/`ExecutionFinishedEvent` (`execute.py:20`, `:47`) for
    the first pass all carry `round=0`, while `VerifyVerdictEvent`
    (`verify.py:29`) and `RouteDecisionEvent` (`route.py:29`) for the same pass
    carry `round=1`. The Phase 6 SSE UI will group them into different rounds.
13. **`truncate.py:22-24` destroys the observation audit trail.** Rebuilding
    `state.observations` from the (sparse — see C2) checkpoint dict is faithful to
    spec §5.3, but it conflicts with the product promise that every answer ships
    with its intermediate observations, and `AbandonedBranch` retains only step
    texts and a sha. Consider keeping a full `observations` log and tracking the
    active window separately.
14. **`registry.py:14-16` builds a module-level `Environment(autoescape=False)`.**
    Correct for prompts, but it will trip `ruff` S701 the moment the `S` ruleset
    is enabled; a one-line comment now saves the argument later.

---

## What is correct (checked, no action)

- **Cost/token accounting is exactly right.** `account()` (`context.py:47`) is
  called **exactly once** in all seven LLM-calling nodes and nowhere else:
  `analyze.py:26`, `plan.py:35`, `code.py:25`, `debug.py:26`, `verify.py:22`,
  `route.py:22`, `finalize.py:22`. `retrieve` and `truncate` make no LLM call and
  correctly do not account. Verified end-to-end: 8 calls → `cost 0.008`,
  `tokens 1200`.
- Control flow in `runner.py:28-58` is a faithful transcription of spec §5.2,
  including the cycle guard placement (§5.2's "add that check at the top of the
  `while` after `plan`") and the `degraded=(vo == "max_rounds")` finalize.
- The §3.3 model decomposition is complete and `models/run.py:104-117` keeps the
  full re-export `__all__`, so no downstream import broke.
- `run_structured_agent` (`_shared.py:13-36`) matches §6.2 exactly, including the
  `isinstance` guard that makes `AgentOutputError` reachable.
- `FakeLLM.on` (`fakes/llm.py:83-116`) is genuinely additive: `complete` falls
  back to the global queue when the per-agent queue is empty
  (`llm.py:145-146`), and the port signature is unchanged, so the conformance
  test still holds.
