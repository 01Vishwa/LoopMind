# Phase 3 — Task 1 completion report

**Task:** Decompose `models/run.py` + add backtrack bookkeeping.
**Status:** DONE

## Files created

- `packages/core/src/vera_core/models/plan.py` — `PlanStep` (verbatim body, frozen)
- `packages/core/src/vera_core/models/code.py` — `CodeArtifact` (verbatim body, frozen)
- `packages/core/src/vera_core/models/observation.py` — `ArtifactRef`, `Observation` (verbatim bodies, incl. `.succeeded`)
- `packages/core/src/vera_core/models/verdict.py` — `Verdict` (verbatim body, frozen)
- `packages/core/src/vera_core/models/routing.py` — `RouterAction`, `RouterDecision` (verbatim bodies)

## Files modified

- `packages/core/src/vera_core/models/run.py`
  - Removed the six moved class bodies; re-imports them from the new narrow modules.
  - Added `AbandonedBranch` (frozen): `round`, `from_index`, `removed_step_texts` (default_factory list), `removed_script_sha: str | None = None`, `rationale`.
  - Added three `RunState` fields, all `default_factory`: `abandoned_branches: list[AbandonedBranch]`, `script_checkpoints: dict[int, CodeArtifact]`, `observation_checkpoints: dict[int, Observation]`.
  - `__all__` still exports every moved/re-imported name plus `AbandonedBranch` (re-sorted alphabetically; no functional change).
  - `RunState.model_config = {"frozen": False}` unchanged.
- `packages/core/src/vera_core/policies/backtrack.py` — `PlanStep` from `models.plan`, `RunState` stays from `models.run`.
- `packages/core/src/vera_core/policies/truncation.py` — `Observation` from `models.observation`.
- `packages/core/src/vera_core/policies/cycle_detection.py` — `PlanStep` from `models.plan`.
- `packages/core/src/vera_core/ports/sandbox.py` — `CodeArtifact` from `models.code`, `Observation` from `models.observation`.
- `packages/testing/src/vera_testing/fakes/sandbox.py` — `CodeArtifact` from `models.code`, `ArtifactRef`/`Observation` from `models.observation`.
- `packages/core/tests/test_models.py` — appended the three Task 1 Step 1 tests:
  `test_abandoned_branch_round_trips`, `test_run_state_round_trips_with_checkpoints`,
  `test_moved_types_importable_from_new_and_old_paths` (import order adjusted for ruff I001; assertions verbatim).

## Files deliberately NOT changed

- `packages/core/src/vera_core/models/__init__.py` — byte-identical; all names it imports from `models.run` are still re-exported there.
- `packages/core/tests/test_exports.py` — unmodified, passes.
- `ports/event_bus.py` — does not import from `models.run` (plan mention was precautionary).
- Test files `test_policies.py` (`from vera_core.models.run import Observation, PlanStep, ...`) left as-is — the re-export keeps them working; task scope was `src/` only. They pass.

## Verification output (run from E:\Vera)

```
uv run pytest packages/ apps/ -q -m "not integration and not e2e and not live_llm"
  99 passed, 10 deselected in 1.31s          (was 96; +3 new tests)

uv run ruff check packages/ apps/ && uv run ruff format --check packages/ apps/
  All checks passed!
  159 files already formatted

uv run mypy packages/core/src packages/testing/src packages/db/src packages/llm/src apps/cli/src
  Success: no issues found in 89 source files

uv run lint-imports
  Contracts: 3 kept, 0 broken.
```

## Concerns

- None. `run.py` `__all__` was re-sorted alphabetically (ruff/style consistency); it still contains the full set of names, so no downstream import breaks.
