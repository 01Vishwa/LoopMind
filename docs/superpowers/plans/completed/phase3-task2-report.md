# Phase 3 — Task 2: PromptRegistry + templates — completion report

**Status:** DONE

## What shipped

- `packages/core/src/vera_core/prompts/registry.py` — `PromptTemplate` (frozen
  dataclass: agent/version/source/sha256, `render(**vars)` via jinja2
  `StrictUndefined`, trim_blocks/lstrip_blocks, autoescape off) and
  `PromptRegistry(templates_dir=None)` with `get(agent, version=None)`
  (highest `vN` when None, `KeyError` on unknown agent), `list_versions(agent)`.
  Transcribed from plan Task 2 Step 3; only whitespace touched by `ruff format`.
- `packages/core/src/vera_core/prompts/__init__.py` — re-exports
  `PromptRegistry`, `PromptTemplate`.
- Filled 7 versioned templates (2–4 sentence task statement, named input vars,
  closing JSON-schema requirement, each < 25 lines):
  - `analyzer/v3.jinja` — vars `filename`, `kind`, `sample` → FileDescription
  - `planner/v5.jinja` — vars `query`, `descriptions`, `existing_steps`, `abandoned`
  - `coder/v4.jinja` — vars `query`, `plan`, `last_stdout`, `last_stderr`
  - `verifier/v6.jinja` — vars `query`, `plan`, `code`, `observation`
  - `router/v3.jinja` — vars `query`, `verdict_reason`, `missing_aspects`, `plan`
  - `debugger/v2.jinja` — vars `code`, `stderr`
  - `finalizer/v2.jinja` — vars `query`, `plan`, `observation`, `degraded`
- `packages/core/tests/test_prompt_registry.py` — highest-version resolution,
  `StrictUndefined` raises on missing var (asserts `jinja2.UndefinedError` to
  satisfy ruff B017), sha256 stability/change, unknown-agent `KeyError`,
  `list_versions` sorted.

## Out of scope / untouched (per instructions)

- `analyzer/formats/*.jinja`, `report_writer/v3.jinja`,
  `subquestion_generator/v2.jinja` left empty (Phase 7 / Phase 8).
- No agents, loop, fakes, CLI, or model changes.

## Verification (run from E:\Vera, all green)

- `uv run pytest packages/ apps/ -q -m "not integration and not e2e and not live_llm"` → 104 passed, 10 deselected
- `uv run ruff check packages/ apps/` → All checks passed
- `uv run ruff format --check packages/ apps/` → 161 files already formatted
- `uv run mypy packages/core/src packages/testing/src packages/db/src packages/llm/src apps/cli/src` → Success, no issues in 90 files
- `uv run lint-imports` → 3 kept, 0 broken

## Concerns

None. Note `render()` with no args only raises because every template references
a variable on its first executed line; this is intentional and covered by the
`StrictUndefined` test.
