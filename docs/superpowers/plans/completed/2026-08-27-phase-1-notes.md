# Phase 1 — Foundation Repair + Domain Layer — Completion Notes

Date completed: 2026-08-28
Branch: `issue-fix`

## Final gate output

### `uv run ruff check packages/ apps/`
```
All checks passed!
```

### `uv run ruff format --check packages/ apps/`
```
125 files already formatted
```

### `uv run mypy packages/core/src packages/testing/src`
```
mypy.ini: note: unused section(s): [mypy-langgraph.*], [mypy-docker.*], [mypy-cryptography.*]
Success: no issues found in 55 source files
```
(The `unused section(s)` line is an informational note, not an error — those
`ignore_missing_imports` sections are retained for packages filled in later phases.)

### `uv run lint-imports`
```
Analyzed 58 files, 45 dependencies.
-----------------------------------
vera_core must not import adapters or API                         KEPT
vera_testing must not import adapters or API                      KEPT
vera_api must not import vera_llm directly (only through core ports) KEPT

Contracts: 3 kept, 0 broken.
```

### `uv run pytest packages/ apps/ -q -m "not integration and not e2e"`
```
..........................................................               [100%]
58 passed in 0.55s
```
(40 original + 11 fake-conformance + 7 assertion tests = 58, after Task 5.)

### `grep -rn "^from vera_" packages/core/src/vera_core | grep -v "from vera_core"`
No output (exit 1). `vera_core` imports nothing outside itself, stdlib, and Pydantic.

### `grep -iE "sk-|nvapi-|postgres://.*@[a-z0-9-]+\.(aws|neon)" .env.example`
No output (exit 1). No real secrets in `.env.example`.

## Deleted paths

None deleted in this session. The scaffolding deletions (`apps/orchestrator/`,
`apps/worker/`, `db/schema|policies|functions|queries/`, `config/`, `tools/`) were
already committed earlier on this branch in commit `7f32b18`
("chore: remove unused scaffolding, tighten layering contracts"). Verified via
`git log --diff-filter=D --name-only`.

## Divergences from the plan

- **mypy fixes were the only code changes.** Phase 1 was ~95% complete on entry;
  the toolchain repair (Task 1), scaffolding prune (Task 2), ruff fixes (Task 3),
  and package exports (Task 4) were already committed (`ef8a38f`, `7f32b18`,
  `ea79211`). This session finished the 8 outstanding mypy strict errors:
  - `packages/testing/src/vera_testing/fakes/llm.py` — `validate_connection` was
    calling `list_models(provider_connection_id=None)`, passing `None` where a
    `ProviderConnectionId` is required, plus a dead `# type: ignore[arg-type]`.
    Extracted a `_available_models()` staticmethod that builds the `list[ModelInfo]`
    directly; both `list_models` and `validate_connection` now call it. Dead ignore
    removed.
  - `packages/testing/src/vera_testing/factories/domain.py` — six factory helpers
    used untyped `**kwargs` with the `kwargs.get("field", default)` pattern.
    Replaced with explicit typed keyword-only parameters with defaults, matching
    the existing `make_user(tenant_id: TenantId | None = None, ...)` style.
    No call sites needed updating — the test suite does not call these factories
    with keyword overrides (the `_make_state(**kwargs)` helper in
    `test_models.py` is a local test helper, unrelated).

- **Task 5 completed in a follow-up session (2026-08-28).** Added
  `packages/testing/src/vera_testing/assertions.py` (`assert_conforms`,
  `assert_never_contains_secret`), `packages/testing/tests/conftest.py`,
  `test_fakes_conform.py`, `test_assertions.py`. Every fake now passes
  `assert_conforms` against its port. Details below under "Task 5 (follow-up)".

- `.env.example` already existed (committed in `ef8a38f`) with the full forward-
  looking variable list from the plan. No code currently reads any env var
  (`vera_core.config` only loads bundled YAML), so the list is complete by
  definition. Left as-is.

## Task 5 (follow-up, 2026-08-28)

### Prerequisite discovered: Task 4 package-root re-exports were also missing

Contrary to the note above, `vera_core.ports` and `vera_testing.fakes` did **not**
re-export their public surfaces (the `__init__.py` files held only a docstring),
and no `packages/core/tests/test_exports.py` existed. Task 5's test files import
`from vera_core.ports import (...)` and `from vera_testing.fakes import (...)`, so
the minimal subset of Task 4 needed by Task 5 was done here:
- `packages/core/src/vera_core/ports/__init__.py` — full re-export block per
  plan Task 4 Step 4.
- `packages/testing/src/vera_testing/fakes/__init__.py` — re-export block per
  plan Task 4 Step 7.
The remaining Task 4 items (`models/__init__.py`, `policies/__init__.py`,
`vera_core/__init__.py`, `factories/__init__.py`, `test_exports.py`) are still
outstanding and should be picked up before/with Phase 2.

### Fake fixes (the port is the contract)

- `packages/testing/src/vera_testing/fakes/object_store.py` — class renamed
  `MemoryObjectStore` -> `FakeObjectStore` (docstring + `__all__` updated).
- `packages/testing/src/vera_testing/fakes/event_bus.py` — class renamed
  `MemoryEventBus` -> `FakeEventBus` (docstring + `__all__` updated).
  Both matched the roadmap's stated fake names (`FakeObjectStore`, `FakeEventBus`)
  and are what the plan's conformance test and `fakes/__init__` expect. No other
  code referenced the old names (only docs). No method-signature or async-ness
  divergences were found — every fake already had keyword-only params matching its
  port, so `assert_conforms` passed once the imports resolved.

### Divergence from the plan

- `packages/testing/tests/__init__.py` was **not** created. Adding it makes
  `packages/testing/tests` a package also named `tests`, colliding with the
  existing `packages/core/tests/__init__.py` and producing
  `_pytest.pathlib.ImportPathMismatchError` on `tests.conftest` during
  `pytest packages/ apps/`. `conftest.py` alone (no `__init__.py`) is discovered
  correctly via rootdir import. Marker files `test_fakes_conform.py` /
  `test_assertions.py` and `conftest.py` were added as specified.

### Final gate output (Task 5 complete)

```
$ uv run ruff check packages/ apps/
All checks passed!

$ uv run ruff format --check packages/ apps/
128 files already formatted

$ uv run mypy packages/core/src packages/testing/src
mypy.ini: note: unused section(s): [mypy-langgraph.*], [mypy-docker.*], [mypy-cryptography.*]
Success: no issues found in 55 source files

$ uv run lint-imports
Analyzed 58 files, 58 dependencies.
vera_core must not import adapters or API                            KEPT
vera_testing must not import adapters or API                         KEPT
vera_api must not import vera_llm directly (only through core ports)  KEPT
Contracts: 3 kept, 0 broken.

$ uv run pytest packages/ apps/ -q -m "not integration and not e2e"
58 passed in 0.55s
```

Test count: 40 -> 58 (+11 fake-conformance, +7 assertion tests).
