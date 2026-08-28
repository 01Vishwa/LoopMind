# Phase 3 — Task 6 completion report

**Scope:** shared scenario builders, payments fixtures + Phase 4 gate manifest,
`vera run` CLI command, `make loop` target. Loop / agents / models untouched.

## Files touched

Created / present:
- `packages/testing/src/vera_testing/scenarios.py` — `Scenario` dataclass
  (`llm`, `sandbox`, `retriever`, `state: RunState`, `expected_status:
  RunStatus`, `expected_answer_substring`, `file_count`) + `happy_path()`,
  `multi_round()`, `backtrack()`. Each scripts `FakeLLM.on(...)` /
  `FakeSandbox.push_success(...)` to drain exactly through `run_precise` with
  `file_refs=[]`. Planner responses return the cumulative plan (prefix-append
  semantics); node-call tally in each builder's docstring.
- `packages/testing/tests/test_scenarios.py` — parametrised "drains cleanly"
  (`queue_length == 0`, sandbox queue empty, `status is sc.expected_status`),
  plus multi_round plan-growth and backtrack abandoned-branch assertions. Drives
  each run from `sc.state`.
- `fixtures/payments/{payments.csv,merchant_data.json,fees.json,manifest.yaml}` —
  20 hand-authored rows; chargeback amounts sum to 1250 (t003 150 + t006 250 +
  t012 200 + t016 150 + t018 500). `manifest.yaml` now carries a `files:` block
  plus **10 gate queries** of increasing difficulty in the Phase 4 format
  (`query` + `contains` substring + optional `tolerance`), each answer computed
  from `payments.csv` (20 txns, 60% card, total 3662.73, avg 183.14, retail
  volume 2085.74, card fees 89.09, top-chargeback merchant "Adventure Works
  Gear" 750).
- `apps/cli/src/vera_cli/commands/run.py` — `run` Typer command. Without
  `--fake-llm`: `"Real LLM execution requires Phase 4. Use --fake-llm."`, exit 1.
  With it: counts supported files in the workspace, loads `sc.state` from the
  chosen scenario (default `backtrack`), runs it through `run_precise`, prints
  `Analyzed N files` / `Plan: N steps (K backtracked)` / `Rounds:` /
  `Backtracks:` / `Cost: … Tokens:` / `Answer:`.
- `apps/cli/tests/test_run_command.py` — exit-1 path, happy path, backtrack path.

Modified this session:
- `scenarios.py` — added `state` / `expected_status` fields; builders updated.
- `apps/cli/.../run.py` — default `--scenario backtrack`; Phase-4 message
  wording; explicit `Backtracks:` line; runs from `sc.state`.
- `packages/core/tests/test_loop_scenarios.py` — replaced inline scripted-fake
  helpers with imports from `vera_testing.scenarios`.
- `fixtures/payments/manifest.yaml` — replaced the single smoke query with the
  10-query gate set.
- `Makefile` — `loop` target repointed at the Q3-chargebacks gate query.
- `apps/cli/.../main.py` — `app.command()(run)` (already present).

## Test summary

`uv run pytest packages/ apps/ -q -m "not integration and not e2e and not live_llm"`
→ **146 passed, 10 deselected**. `ruff check` + `ruff format --check` clean;
`mypy` clean on all 5 gate paths (111 files); `lint-imports` 3 kept / 0 broken.

`uv run vera run --workspace ./fixtures/payments --query "What share of Q3
chargebacks came from merchants with manual capture delay?" --fake-llm
--scenario backtrack` exits 0 and prints:
```
Analyzed 3 files
Plan: 2 steps (1 backtracked)
Rounds: 2
Backtracks: 1
Cost: $0.0080   Tokens: 1200
Answer: After a backtrack to regroup by merchant, the total chargeback amount is $1250.00.
```

## Concerns

- `make loop` not runnable here (`make` absent from PATH); the underlying
  `uv run vera run …` command was verified directly and the target is a verbatim
  wrapper.
- `manifest.yaml` gate answers were computed by hand from `payments.csv`; Phase 4
  should re-verify each against a real sandbox run before trusting the gate.
- `Scenario` is a plain (non-frozen) `@dataclass` per the Task 6 spec; `run.py`
  mutates `sc.state.query`. Fine for the fake path; the real path (Phase 4) will
  build its own `RunState`.
