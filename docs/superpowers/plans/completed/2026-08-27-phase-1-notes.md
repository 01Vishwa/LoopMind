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
........................................                                 [100%]
40 passed in 0.60s
```

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

- **Task 5 conformance tests / assertions.py** — not present as untracked files and
  not added in this session; test count stayed at 40. The mypy/import/ruff gate is
  green regardless. Flagged for follow-up if the phase-1 exit gate item "every fake
  passes `assert_conforms`" is to be literally satisfied.

- `.env.example` already existed (committed in `ef8a38f`) with the full forward-
  looking variable list from the plan. No code currently reads any env var
  (`vera_core.config` only loads bundled YAML), so the list is complete by
  definition. Left as-is.
