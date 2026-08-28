# Phase 3 — Task 3 completion report

**Scope:** Fakes — `.on()`, `FakeRetriever`, `push_observation`, four factory helpers.
No agents, loop, scenarios, or CLI touched.

## Files touched

Modified:
- `packages/testing/src/vera_testing/fakes/llm.py` — added `self._agent_queues`,
  `FakeLLM.on(agent, obj, *, cost_usd=Decimal("0.001"))` (accepts `BaseModel | str`),
  and per-agent queue preference in `complete()` (falls back to global `_queue`
  when the agent queue is empty/absent). `complete()` signature unchanged.
- `packages/testing/src/vera_testing/fakes/sandbox.py` — added
  `FakeSandbox.push_observation(obs: Observation)` (appends verbatim to `_queue`).
- `packages/testing/src/vera_testing/fakes/__init__.py` — export `FakeRetriever`.
- `packages/testing/src/vera_testing/factories/domain.py` — added `make_plan_step`,
  `make_code_artifact`, `make_observation`, `make_verdict` (+ `__all__`, imports).
- `packages/testing/src/vera_testing/factories/__init__.py` — re-export the four new helpers.
- `packages/testing/tests/test_fakes_conform.py` — added `(FakeRetriever, RetrieverPort)`
  to `PAIRS` (+ imports).

Created:
- `packages/testing/src/vera_testing/fakes/retriever.py` — `FakeRetriever(descriptions=None)`,
  `.set_results(...)`, `async search(*, query, workspace_id, top_k=12, pinned_file_ids=None)`
  returning `descriptions[:top_k]`. Matches `RetrieverPort` verbatim.
- `packages/testing/tests/test_fakes_extra.py` — 5 tests: `.on()` agent routing,
  `.on()` fallback-to-global after agent queue drains, retriever top-k, retriever
  `set_results`, sandbox `push_observation`. Self-contained (uses
  `make_code_artifact` + `vera_core.ports.sandbox.ResourceLimits()` directly).

## Test summary

`uv run pytest packages/ apps/ -q -m "not integration and not e2e and not live_llm"` →
**111 passed, 10 deselected** (was 104; +7 new: 5 in `test_fakes_extra.py`, +2 conformance
params for `FakeRetriever`). ruff check + format, mypy (91 files), and `lint-imports`
(3 kept, 0 broken) all green.

## Concerns

- `FakeLLM.queue_length` still reports only the global queue length; Task 6's
  `test_scenarios.py` sketch asserts `sc.llm.queue_length == 0`. If scenarios script
  via `.on()`, that property may need to sum agent queues too — flag for Task 6.
- `test_fakes_extra.py` passes `workspace_id=None` / `run_id=None` / `provider_connection_id=None`;
  fakes are permissive so this is fine at runtime, but real adapters will want real IDs.
