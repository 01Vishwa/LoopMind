# Phase 2 (Supabase edition) — Key Vault & BYOK — Completion Notes

Date: 2026-08-28
Branch: `issue-fix`
Spec: `docs/superpowers/specs/2026-08-28-phase-2-supabase-byok-design.md`
ADR: `docs/adr/0002-supabase-platform.md`

## What shipped

Implemented by four background subagents (foundation, `vera_llm`, `vera_db`,
`apps/cli`) plus orchestrator fixups. No git operations performed — all changes
left in the working tree.

### Foundation (config + migrations)
- `docs/adr/0002-supabase-platform.md` — Supabase as sole external service, Option A.
- `docs/VERA_BACKEND_PLAN.md` §4/§6/§10/§12/§17 and `docs/VERA_BACKEND_PHASES.md`
  Phase 2 rewritten for Supabase (Vault replaces Fernet; Storage/Auth/Realtime
  mapped to Phases 5–6).
- `.env.example` — Supabase block; `VERA_DATABASE_URL` (:6543 pooler) +
  `VERA_DATABASE_URL_DIRECT` (:5432 session); `VERA_VAULT_MASTER_KEY` removed.
- `pyproject.toml` workspace + `[tool.pytest.ini_options]` (asyncio auto, markers).
- `.importlinter` — `vera_cli` added to root packages + both forbidden contracts.
- `mypy.ini` — `[mypy-pgvector.*]`; `Makefile` — mypy paths extended, Alembic
  targets replaced with `db-migrate`/`db-new`/`db-reset` (Supabase CLI).
- `supabase/` — `config.toml`, `migrations/0001_extensions.sql` … `0005_grants.sql`
  (extensions incl. `supabase_vault`; `tenants`/`users`; `provider_connections`
  + `provider_models_cache`; RLS via `public.current_tenant_id()`; grants keeping
  `vault.decrypted_secrets` service-role-only), `seed.sql`.

### `packages/llm` — provider validation slice
- `providers.py` (`PROVIDER_CONFIGS`), `model_parsing.py` (`parse_models`),
  `validation.py` (`validate_connection` + `_cheapest`), `client.py` (`LLMClient`;
  `complete` → `NotImplementedError` Phase 4; `list_models` → defers to
  `provider_service`).
- Recorded fixtures + `test_providers.py` / `test_validation.py` (18 tests,
  incl. OpenRouter/NIM request-shape parity), `test_validation_live.py`
  (`live_llm`, skipped without `OPENROUTER_API_KEY`).
- `alembic` dependency removed from `packages/db/pyproject.toml`.

### `packages/db` — Supabase adapter
- `config.py`, `engine.py` (pooled = `NullPool` + `statement_cache_size=0`;
  direct), `session.py` (`make_sessionmaker`, `tenant_session`).
- `models/` — `Base`, `TimestampMixin`, `Tenant`, `User`, `ProviderConnectionRow`,
  `ProviderModelCacheRow`.
- `repositories/provider_repository.py` (`ProviderRepository` implements
  `ProviderRepositoryPort` + `replace_model_cache`; `selectinload`;
  `IntegrityError` → `ConflictError`).
- `repositories/vault_repository.py` (`VaultRepository` implements `KeyVaultPort`
  over `vault.create_secret` / `vault.update_secret` / `vault.decrypted_secrets`;
  secret name `t:{tenant_id}:{ref}`; parameterised `text()` only).
- Deleted the empty Alembic stub tree and 0-byte repository stubs.
- `tests/test_config.py`, `tests/test_models.py` (10 unit); `tests/integration/`
  `test_provider_repository.py` / `test_vault_repository.py` / `test_rls_providers.py`
  (9, `integration` marker, skip without `VERA_DATABASE_URL_DIRECT`).

### `apps/cli` — the `vera` CLI
- `deps.py`, `masking.py`, `constants.py`, `services/provider_service.py`
  (`ProviderService.connect/revalidate/disconnect`, single-transaction
  orchestration with rollback), `commands/{doctor,db,dev,provider}.py`, `main.py`.
- `[project.scripts] vera = "vera_cli.main:app"`.
- `tests/test_provider_service.py` (4) + `tests/test_provider_commands.py` (3),
  fakes in `conftest.py`.

## Orchestrator fixups (not by a subagent)

- Removed `packages/llm/tests/__init__.py` — collided with
  `packages/core/tests/__init__.py` (pytest package-name clash).
- Added root `[tool.pytest.ini_options]` — repo-wide `pytest` had no config, so
  `asyncio_mode` defaulted to `strict` and every async test failed to run.
- Fixed the dev-seed identifiers: `…-00000000dev1` / `…dev2` contain a non-hex
  `v` and are rejected by `uuid.UUID()` and Postgres. Replaced with
  `0000000d-0000-4000-8000-000000000001` / `…002` in `supabase/seed.sql` and
  `apps/cli/src/vera_cli/constants.py`.

## Gate output (local, 2026-08-28)

```
$ uv run pytest packages/ apps/ -q -m "not integration and not e2e and not live_llm"
96 passed, 10 deselected

$ uv run ruff check packages/ apps/            → All checks passed!
$ uv run ruff format --check packages/ apps/   → 159 files already formatted
$ uv run mypy packages/core/src packages/testing/src packages/db/src packages/llm/src apps/cli/src
Success: no issues found in 89 source files

$ uv run lint-imports                          → Contracts: 3 kept, 0 broken.
$ uv run vera --help                           → renders (doctor / provider / db / dev)
```

Test count: 61 → 96 (+18 llm, +10 db, +7 cli).

## Not verifiable in this environment (needs the human / a live project)

- `supabase` CLI is not installed here — migrations are authored but never
  applied. Run `supabase link` + `supabase db push` against the cloud project.
- Integration tests (`-m integration`) and the live CLI flow
  (`vera doctor`, `vera dev seed`, `vera provider add --kind openrouter --key …`,
  `vera provider list`) require `VERA_DATABASE_URL*` pointed at the Supabase
  project with Phase 2 migrations applied, plus a real `OPENROUTER_API_KEY`.
- `make` is unavailable on the dev box; gate commands were run individually.

## Follow-ups for later phases

- `LLMClient.list_models` is `NotImplementedError` — Phase 6 gives it a
  tenant-aware read path via the API composition layer.
- `ProviderService` lives in `apps/cli`; Phase 6 promotes it to a location the
  API can import (or a `packages/services`).
- `users.id` is a standalone uuid; Phase 6 aligns it with `auth.users.id`.
- UUIDv7 helper deferred — `gen_random_uuid()` for now.
- `AgentDefaultsRepositoryPort` implementation + agent-defaults endpoints:
  original Build-Order slice 3, still open.
