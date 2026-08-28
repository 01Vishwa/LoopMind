# Phase 2 (Supabase edition) — Key Vault & BYOK Provider Management — Design

**Date:** 2026-08-28
**Status:** Approved (design), pending spec review
**Supersedes:** `VERA_BACKEND_PHASES.md` Phase 2 as originally written (Neon + Fernet)
**Companion ADR:** `docs/adr/0002-supabase-platform.md` (to be created in this phase)

---

## 1. Context and decision

VERA's backend will run entirely on **Supabase** — no other external service.
Supabase is Postgres, so the relational model, RLS, and pgvector are unchanged
from the Neon plan. Supabase additionally provides managed **Vault** (encrypted
secrets), **Auth**, **Storage**, and **Realtime**.

**Chosen approach — Option A:** keep FastAPI + SQLAlchemy 2.0 as the API/data
layer, connect to Supabase Postgres directly over the connection string, and use
Supabase's managed features as add-ons behind the existing `vera_core` ports.
Option B (PostgREST + Edge Functions replacing FastAPI) is rejected: it discards
the ORM and migration tooling and couples orchestration to Deno.

**Per-feature phase mapping:**

| Supabase feature | VERA port / concern | Lands in |
| --- | --- | --- |
| Postgres + Supavisor pooling | `vera_db` engine/session | **Phase 2** |
| Vault (`supabase_vault`) | `KeyVaultPort` | **Phase 2** |
| RLS | tenancy isolation | **Phase 2** (policies authored) / Phase 5 (load-bearing test) |
| Auth | `Principal`, request auth | Phase 6 |
| Storage | `ObjectStorePort` | Phase 5 |
| Realtime | `EventBusPort` / SSE | Phase 6 |

`packages/core` is **not modified in this phase**. Every port protocol
(`KeyVaultPort`, `ProviderRepositoryPort`, `AgentDefaultsRepositoryPort`,
`LLMPort`) and every domain model (`ProviderConnection`, `ModelInfo`,
`ValidationResult`, `AgentDefaults`) already exists and is frozen by Phase 1.

## 2. Goal and exit gate

**Goal:** from a CLI, a user connects an OpenRouter or NVIDIA NIM key; VERA
validates it against the provider, stores it in Supabase Vault (never in an
app-owned table, never logged, never returned), caches the available models, and
lists connected providers with their model counts.

**Exit gate:**

```bash
supabase db push                                                       # schema + RLS + grants
uv run pytest packages/ apps/ -q -m "not integration and not live_llm" # unit + contract
uv run pytest -q -m integration                                        # against Supabase
uv run vera doctor                                                     # all green
uv run vera dev seed
uv run vera provider add --kind openrouter --key $OPENROUTER_API_KEY
uv run vera provider list                                              # connected + model count
make lint                                                              # ruff + mypy + import-linter
```

Manual verification after `provider add`:
- the raw key is **absent** from `provider_connections` (only `api_key_ref`);
- `select decrypted_secret from vault.decrypted_secrets where name = <ref>` returns it;
- `select secret from vault.secrets where name = <ref>` is ciphertext only.

## 3. Repository layout (approved)

Packages stay **flat** — no `packages/adapters/` rename (CLAUDE.md forbids it).

```
supabase/                                   # NEW — Supabase CLI project
  config.toml
  migrations/
    0001_extensions.sql
    0002_tenancy.sql
    0003_providers.sql
    0004_rls.sql
    0005_grants.sql
  seed.sql                                  # optional local seed

packages/db/                                # was a stub; filled in this phase
  pyproject.toml                            # drop alembic; keep sqlalchemy/asyncpg/pgvector
  src/vera_db/
    config.py                               # NEW — reads VERA_DATABASE_URL* from env
    engine.py                               # NEW — async engines (pooled + direct)
    session.py                              # NEW — sessionmaker + tenant_session helper
    models/
      base.py                               # NEW — DeclarativeBase, timestamp mixin
      tenancy.py                            # NEW — Tenant, User ORM
      provider.py                           # NEW — ProviderConnection, ProviderModelCache ORM
    repositories/
      provider_repository.py                # NEW — implements ProviderRepositoryPort
      vault_repository.py                   # NEW — implements KeyVaultPort (Supabase Vault)
    __init__.py                             # re-export public surface
    migrations/                             # DELETE (empty Alembic stub tree)

packages/llm/                               # was a stub; validation slice filled in this phase
  src/vera_llm/
    providers.py                            # NEW — PROVIDER_CONFIGS
    validation.py                           # NEW — validate_connection
    model_parsing.py                        # NEW — per-provider /models response -> list[ModelInfo]
    client.py                               # NEW — LLMClient (list_models + validate; complete -> NotImplementedError)
    __init__.py                             # re-export
  tests/
    fixtures/openrouter_models.json         # NEW — recorded
    fixtures/nvidia_models.json             # NEW — recorded
    test_providers.py                       # NEW
    test_validation.py                      # NEW

apps/cli/                                   # NEW app
  pyproject.toml
  src/vera_cli/
    main.py                                 # typer app
    deps.py                                 # build engine/repos/llm client from env
    services/provider_service.py            # connect / revalidate / disconnect orchestration
    commands/
      doctor.py
      db.py                                 # `vera db migrate` -> supabase db push
      dev.py                                # `vera dev seed`
      provider.py                           # add / list / validate / rm
  tests/
    test_provider_commands.py               # CliRunner + fakes

docs/adr/0002-supabase-platform.md          # NEW
```

**Config / workspace / lint changes:**

- `pyproject.toml` `[tool.uv.workspace].members` — add `apps/cli`.
- `.importlinter` — add `vera_cli` to `root_packages`; extend the
  `core-is-independent` and `testing-depends-only-on-core` forbidden contracts
  with `vera_cli`.
- `mypy.ini` / `make lint` — extend the mypy invocation to
  `packages/core/src packages/testing/src packages/db/src packages/llm/src apps/cli/src`.
  Add `[mypy-*]` `ignore_missing_imports` sections only where a third-party lib
  ships no stubs (e.g. `pgvector.*`, `typer` ships types).
- `Makefile` — replace `migrate` / `migrate-new` targets with
  `db-migrate` (`supabase db push`), `db-new` (`supabase migration new $(MSG)`),
  `db-reset` (`supabase db reset`). Remove the `apps/api/alembic.ini` reference.
- `.env.example` — see §8.

## 4. Database schema (`supabase/migrations/`)

### 0001_extensions.sql
```sql
create extension if not exists supabase_vault cascade;   -- Vault (pgsodium + vault schema)
create extension if not exists vector;
create extension if not exists pgcrypto;
```

### 0002_tenancy.sql
Minimal tenancy — full Auth wiring is Phase 6. `users.id` is a plain uuid now;
Phase 6 aligns it with `auth.users.id`.
```sql
create table public.tenants (
    id          uuid primary key default gen_random_uuid(),
    name        text not null,
    plan        text not null default 'free',
    created_at  timestamptz not null default now()
);

create table public.users (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid not null references public.tenants(id) on delete cascade,
    email       text not null unique,
    full_name   text not null default '',
    role        text not null default 'analyst',      -- owner|admin|analyst|viewer
    created_at  timestamptz not null default now()
);
create index idx_users_tenant on public.users(tenant_id);
```

### 0003_providers.sql
```sql
create table public.provider_connections (
    id                 uuid primary key default gen_random_uuid(),
    tenant_id          uuid not null references public.tenants(id) on delete cascade,
    user_id            uuid not null references public.users(id) on delete cascade,
    kind               text not null check (kind in ('openrouter','nvidia_nim')),
    display_name       text not null,
    base_url           text not null,
    api_key_ref        text not null,                 -- Vault secret name; NEVER the key
    status             text not null default 'validating'
                       check (status in ('connected','validating','failed','revoked')),
    last_validated_at  timestamptz,
    last_error         text,
    created_at         timestamptz not null default now(),
    unique (user_id, display_name)
);
create index idx_prov_conn_user on public.provider_connections(user_id);
create index idx_prov_conn_tenant on public.provider_connections(tenant_id);

create table public.provider_models_cache (
    provider_connection_id     uuid not null references public.provider_connections(id) on delete cascade,
    model_id                   text not null,
    display_name               text not null,
    context_window             integer not null default 0,
    input_price_per_m          numeric(12,6),
    output_price_per_m         numeric(12,6),
    supports_json_mode         boolean not null default false,
    supports_function_calling  boolean not null default false,
    supports_vision            boolean not null default false,
    cached_at                  timestamptz not null default now(),
    primary key (provider_connection_id, model_id)
);
```

### 0004_rls.sql
```sql
create or replace function public.current_tenant_id() returns uuid
language sql stable as $$
    select coalesce(
        nullif(current_setting('request.jwt.claims', true)::jsonb ->> 'tenant_id', ''),
        nullif(current_setting('app.tenant_id', true), '')
    )::uuid
$$;

alter table public.provider_connections enable row level security;
alter table public.provider_connections force row level security;
create policy prov_conn_tenant on public.provider_connections
    using (tenant_id = public.current_tenant_id())
    with check (tenant_id = public.current_tenant_id());

alter table public.provider_models_cache enable row level security;
alter table public.provider_models_cache force row level security;
create policy prov_models_tenant on public.provider_models_cache
    using (exists (
        select 1 from public.provider_connections pc
        where pc.id = provider_connection_id
          and pc.tenant_id = public.current_tenant_id()
    ));

alter table public.tenants enable row level security;   -- no policy: service-role only for now
alter table public.users   enable row level security;
```

### 0005_grants.sql
```sql
grant usage on schema public to authenticated;
grant select, insert, update, delete on
    public.provider_connections, public.provider_models_cache to authenticated;
-- vault.decrypted_secrets is NOT granted to authenticated — server/service-role only.
```

## 5. Tenancy model for Phase 2

- The **CLI and (later) the API connect as the `postgres` / service-role
  Postgres user**, which bypasses RLS by design. Every repository method takes an
  explicit `tenant_id` and filters on it in SQL — RLS is defence in depth, not
  the primary guard on the server path.
- RLS policies are authored now against `public.current_tenant_id()` so the
  future authenticated (browser) path is already covered. Phase 6 only changes
  whether the tenant id comes from the JWT claim or the GUC.
- **RLS smoke test (this phase):** open a second connection as the `authenticated`
  role, `set local request.jwt.claims = '{"tenant_id":"<A>"}'`, insert a row for
  tenant B via the service-role connection, assert the authenticated connection
  sees 0 rows. Marked `integration`.

## 6. `vera_db` adapter

### config.py
Reads `VERA_DATABASE_URL` (transaction pooler) and `VERA_DATABASE_URL_DIRECT`
(session mode) from the environment. A small frozen dataclass; raises
`vera_core.errors.ValidationError` with a clear message if unset. Adapters may
read env; `vera_core` may not.

### engine.py
- `build_pooled_engine()` — `create_async_engine(url, poolclass=NullPool,
  connect_args={"statement_cache_size": 0})` (pgbouncer transaction mode cannot
  use prepared-statement cache).
- `build_direct_engine()` — normal pool; used by migrations tooling and the RLS
  test.
- Both `echo=False`, `pool_pre_ping=True` on the direct engine.

### session.py
- `sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)`.
- `@asynccontextmanager tenant_session(sm, tenant_id)` — begins a transaction and
  issues `select set_config('app.tenant_id', :tid, true)` before yielding. Used
  by the authenticated path and the RLS test; the CLI uses a plain session.

### models/
SQLAlchemy 2.0 declarative, `Mapped[...]` / `mapped_column`. `Base(DeclarativeBase)`
in `base.py` with a `TimestampMixin`. ORM classes: `Tenant`, `User`,
`ProviderConnectionRow`, `ProviderModelCacheRow`. Enums stored as `text` with a
CHECK (mirrors the SQL); mapping to/from `vera_core` `StrEnum` is explicit in the
repository.

### repositories/provider_repository.py
Implements `ProviderRepositoryPort` exactly (keyword-only, same names):
- `create_connection(conn)` — insert; returns the domain model with DB defaults applied.
- `get_connection(id, tenant_id)` — select with `tenant_id` filter; `None` if absent.
- `list_connections(user_id)` — ordered by `created_at desc`; eager-loads the
  model cache to populate `available_models` without N+1 (`selectinload`).
- `update_connection(conn)` — update mutable fields (`status`, `last_error`,
  `last_validated_at`, `display_name`).
- `delete_connection(id, tenant_id)` — delete; cascade removes the cache rows.
- `replace_model_cache(*, provider_connection_id, models)` — delete + bulk insert
  in one transaction.

Row ↔ domain mapping lives in a private `_to_domain` / `_to_row` pair. `ModelInfo`
prices are `Decimal | None`.

### repositories/vault_repository.py
Implements `KeyVaultPort`. Secret name = `t:{tenant_id}:{ref}` (the `ref` passed
in already contains the connection id, e.g. `provider:<conn_id>:api_key`).
- `store(tenant_id, ref, plaintext)` — `select id from vault.secrets where name = :name`;
  if found → `select vault.update_secret(:id, :secret)`, else
  `select vault.create_secret(:secret, :name, :description)`. One statement path,
  parameterised — never string-interpolated.
- `retrieve(tenant_id, ref)` — `select decrypted_secret from vault.decrypted_secrets
  where name = :name`; raise `vera_core.errors.NotFoundError` if no row.
- `delete(tenant_id, ref)` — `delete from vault.secrets where name = :name`.

The vault repo takes an `AsyncSession` (or sessionmaker) — it does not open its
own engine, so `provider_service` can run the connection insert and the secret
write in **one transaction**.

### __init__.py
Re-export `build_pooled_engine`, `build_direct_engine`, `make_sessionmaker`,
`tenant_session`, `ProviderRepository`, `VaultRepository`, and the ORM `Base`.

## 7. `vera_llm` — provider validation slice

### providers.py
```python
@dataclass(frozen=True)
class ProviderConfig:
    default_base_url: str
    auth_header: str
    auth_prefix: str
    extra_headers: dict[str, str]
    models_path: str
    cost_source: Literal["header", "compute"]

PROVIDER_CONFIGS: dict[ProviderKind, ProviderConfig] = {
    ProviderKind.OPENROUTER: ProviderConfig(
        default_base_url="https://openrouter.ai/api/v1",
        auth_header="Authorization", auth_prefix="Bearer ",
        extra_headers={"HTTP-Referer": "https://vera.app", "X-Title": "VERA Analytics"},
        models_path="/models", cost_source="header",
    ),
    ProviderKind.NVIDIA_NIM: ProviderConfig(
        default_base_url="https://integrate.api.nvidia.com/v1",
        auth_header="Authorization", auth_prefix="Bearer ",
        extra_headers={}, models_path="/models", cost_source="compute",
    ),
}
```

### model_parsing.py
`parse_models(kind, payload) -> list[ModelInfo]`. OpenRouter: `data[]` with
`id`, `name`, `context_length`, `pricing.prompt` / `pricing.completion` (string
USD per token → `Decimal` per million), `architecture.modality` for vision,
`supported_parameters` contains `response_format` / `tools`. NIM: `data[]` with
`id`; sparse metadata → sensible defaults.

### validation.py
```python
async def validate_connection(*, kind, base_url, api_key, http) -> ValidationResult:
    cfg = PROVIDER_CONFIGS[kind]
    headers = {cfg.auth_header: f"{cfg.auth_prefix}{api_key}", **cfg.extra_headers}
    r = await http.get(f"{base_url}{cfg.models_path}", headers=headers, timeout=10)
    if r.status_code in (401, 403):
        return ValidationResult(valid=False, error="Invalid API key")
    if r.status_code >= 400:
        return ValidationResult(valid=False, error=f"Provider returned {r.status_code}")
    models = parse_models(kind, r.json())
    if not models:
        return ValidationResult(valid=False, error="Provider returned no models")
    # cheapest-model completion smoke test
    test = _cheapest(models)
    cr = await http.post(f"{base_url}/chat/completions", headers=headers, timeout=15,
                         json={"model": test.model_id,
                               "messages": [{"role": "user", "content": "Say ok"}],
                               "max_tokens": 5})
    if cr.status_code >= 400:
        return ValidationResult(valid=False,
                                error=f"Completion test failed ({cr.status_code})")
    return ValidationResult(valid=True, models=models)
```
The API key is never placed in an exception message, a log line, or the
`ValidationResult`.

### client.py
`LLMClient(key_vault: KeyVaultPort, provider_repo: ProviderRepositoryPort,
http: httpx.AsyncClient)` implementing `LLMPort`:
- `validate_connection(...)` → delegates to `validation.validate_connection`.
- `list_models(provider_connection_id)` → loads the connection (needs a
  `tenant_id`; for Phase 2 the CLI passes it, so `list_models` gains no new
  params — it resolves via `provider_repo` using a stored tenant on the client or
  is only called through `provider_service`). **Simplest:** `list_models` on the
  client is implemented by re-reading the model cache through `provider_repo`;
  live refresh happens in `provider_service.revalidate`. Document this.
- `complete(...)` → `raise NotImplementedError("LLM completion lands in Phase 4")`.

`vera_llm` imports only `vera_core` + `httpx` + stdlib — **never `vera_db`**.

### Tests
`httpx.MockTransport` backed by the recorded fixtures. Cases: valid key → models
parsed; 401 → `valid=False`; empty list → `valid=False`; completion 500 →
`valid=False`; request-shape assertion that OpenRouter and NIM bodies are
identical for the same logical call (the BYOK abstraction test from PLAN §15).
Live tests (`@pytest.mark.live_llm`) hit the real providers, skipped unless
`OPENROUTER_API_KEY` / `NVIDIA_API_KEY` are set.

## 8. `apps/cli`

### deps.py
Builds, from env: the direct async engine + sessionmaker, an `httpx.AsyncClient`,
`VaultRepository`, `ProviderRepository`, `LLMClient`. Exposes a `Deps` dataclass
and a `build_deps()` factory; tests substitute a `Deps` with fakes.

### services/provider_service.py
```python
class ProviderService:
    def __init__(self, *, repo, vault, llm): ...

    async def connect(self, *, tenant_id, user_id, kind, api_key,
                      display_name, base_url=None) -> ProviderConnection:
        base_url = base_url or PROVIDER_CONFIGS[kind].default_base_url
        result = await self.llm.validate_connection(kind=kind, base_url=base_url, api_key=api_key)
        if not result.valid:
            raise ProviderAuthError(result.error or "Validation failed")
        conn_id = ProviderConnectionId(uuid4())
        ref = f"provider:{conn_id}:api_key"
        async with self.repo.transaction():           # single tx across all three writes
            conn = await self.repo.create_connection(conn=ProviderConnection(
                id=conn_id, tenant_id=tenant_id, user_id=user_id, kind=kind,
                display_name=display_name, base_url=base_url, api_key_ref=ref,
                status=ConnectionStatus.CONNECTED, created_at=now_utc(),
                last_validated_at=now_utc()))
            await self.vault.store(tenant_id=tenant_id, ref=ref, plaintext=api_key)
            await self.repo.replace_model_cache(provider_connection_id=conn_id,
                                                models=result.models)
        return conn

    async def revalidate(self, *, tenant_id, connection_id): ...   # re-run, update status + cache
    async def disconnect(self, *, tenant_id, connection_id): ...    # delete row + vault.delete
```
Idempotency / concurrency: `connect` relies on the `unique (user_id,
display_name)` constraint — a duplicate raises `ConflictError`. A failed Vault
write rolls the whole transaction back, so there is never a connection row
without a secret.

*(This service lives in the CLI for Phase 2. Phase 6 promotes it verbatim to a
location the API can import — either `apps/api/services/` with the logic copied,
or a new `packages/services` package. Deferred to keep this phase small.)*

### commands/
- `vera doctor` — env vars present; `select 1`; `supabase_vault` extension
  installed; `public.current_tenant_id()` exists; optional
  `--check-providers` pings provider `/models` if keys are in env. Exit 1 on any
  failure, human-readable checklist output.
- `vera db migrate` — runs `supabase db push` (subprocess), streams output,
  propagates exit code. `vera db status` → `supabase migration list`.
- `vera dev seed` — upsert a demo tenant + user with fixed UUIDs; prints them so
  later commands can pass `--tenant/--user` (or reads them from a `.vera-dev.json`).
- `vera provider add --kind {openrouter,nvidia_nim} --key <k> [--name <n>]
  [--tenant <uuid>] [--user <uuid>] [--base-url <u>]` — resolves tenant/user from
  flags or the dev seed file, calls `ProviderService.connect`, prints the masked
  key + model count. The key is read from `--key`, `--key-stdin`, or the
  `OPENROUTER_API_KEY` / `NVIDIA_API_KEY` env var; never echoed.
- `vera provider list [--user <uuid>]` — Rich table: display name, kind, status,
  model count, last validated, last error.
- `vera provider validate <connection_id>` — `ProviderService.revalidate`.
- `vera provider rm <connection_id>` — `ProviderService.disconnect`, with a
  confirmation prompt unless `--yes`.

### Tests
`typer.testing.CliRunner`, `Deps` built with `FakeLLM` (pre-loaded
`ValidationResult`), `FakeKeyVault`, and an in-memory fake provider repo (new, in
`apps/cli/tests/` or reuse a `vera_testing` fake if one is added). Assert:
`provider add` writes a connection + a vault entry + cache rows; a `valid=False`
result raises `ProviderAuthError` and writes nothing; `provider list` renders the
table; the raw key never appears in stdout.

## 9. Environment (`.env.example` changes)

```bash
# ── Supabase ─────────────────────────────────────────────────────────────────
SUPABASE_URL=https://YOUR-PROJECT-REF.supabase.co
SUPABASE_ANON_KEY=replace-me
SUPABASE_SERVICE_ROLE_KEY=replace-me            # server-side only; bypasses RLS

# Postgres — transaction pooler (Supavisor :6543), used by the API at runtime
VERA_DATABASE_URL=postgresql+asyncpg://postgres.YOUR-REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
# Postgres — session mode (:5432), used by migrations, LISTEN/NOTIFY, and tests
VERA_DATABASE_URL_DIRECT=postgresql+asyncpg://postgres.YOUR-REF:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres

VERA_KEYVAULT_BACKEND=supabase_vault           # supabase_vault | fake
```

Removed: `VERA_VAULT_MASTER_KEY` (Supabase Vault manages its own encryption key).
Kept but unused until later phases: `VERA_JWT_*`, `VERA_STORAGE_*`,
`VERA_EVENT_BUS_BACKEND`.

## 10. Failure-mode analysis

| Scenario | Behaviour |
| --- | --- |
| DB unreachable during `provider add` | `ProviderService.connect` fails before any write; CLI prints a connection error, exit 1. |
| Provider `/models` times out | `validate_connection` → `ValidationResult(valid=False, error="...")`; no row written. |
| Vault write fails after the connection insert | Whole transaction rolls back (single tx); no orphan row. |
| `provider add` run twice with same name | `unique (user_id, display_name)` → `ConflictError` (409-class); first connection intact. |
| Two concurrent `provider add`, same name | One commits, the other hits the unique constraint and rolls back. |
| `provider validate` when the key was revoked upstream | status → `failed`, `last_error` set, cache left as-is; `list` shows it. |
| Retry of a failed `provider add` | Safe — nothing was committed, so a clean retry creates the connection. |
| pgbouncer transaction mode + prepared statements | `statement_cache_size=0` on the pooled engine avoids the "prepared statement already exists" error. |
| Secret name collision across tenants | Prevented by the `t:{tenant_id}:` prefix on every Vault secret name. |

## 11. Observability

- `vera_db` and `vera_llm` use `logging.getLogger(__name__)`; **no secret, key,
  or full request body is ever logged.** `validate_connection` logs
  `kind`, `base_url`, `status_code`, `model_count` only.
- The CLI prints a one-line structured summary per command
  (`event=provider.connected kind=openrouter models=486`).
- `apps/cli` sets a `request_id` (uuid4) per invocation and includes it in log
  records — consistent with the API's future `X-Request-Id`.

## 12. Out of scope (explicit)

Supabase Auth / `Principal` / real JWT verification; Storage adapter; Realtime;
`LLMClient.complete`; `AgentDefaultsRepositoryPort` implementation and the
agent-defaults endpoints; any FastAPI route; the DS-STAR loop; UUIDv7 (plain
`gen_random_uuid()` for now).

## 13. Test inventory

| File | Marker | Asserts |
| --- | --- | --- |
| `packages/llm/tests/test_providers.py` | unit | `PROVIDER_CONFIGS` shape; `parse_models` for both providers from fixtures |
| `packages/llm/tests/test_validation.py` | unit | valid / 401 / empty / completion-failure paths; identical request shape across providers |
| `packages/db/tests/integration/test_provider_repository.py` | integration | CRUD round-trip; `list_connections` has no N+1; cache replace |
| `packages/db/tests/integration/test_vault_repository.py` | integration | store→retrieve round-trip; rotate (store twice) keeps latest; delete; `vault.secrets` is ciphertext |
| `packages/db/tests/integration/test_rls_providers.py` | integration | authenticated role with tenant-A claim cannot see a tenant-B row |
| `apps/cli/tests/test_provider_commands.py` | unit | `add` writes all three; invalid key writes nothing; `list` output; key never in stdout |
| `packages/testing/tests/test_fakes_conform.py` | unit | unchanged — `FakeKeyVault` still conforms to `KeyVaultPort` |

Integration tests require `VERA_DATABASE_URL_DIRECT` pointing at a Supabase
project (or `supabase start`); they `create`/`truncate` their own rows and clean
up. They are skipped when the env var is unset.

## 14. Task breakdown (for the implementation plan)

1. **Docs & config** — ADR 0002; `PLAN.md` / `PHASES.md` edits; `.env.example`;
   `pyproject` workspace; `.importlinter`; `mypy.ini`; `Makefile`.
2. **Supabase project** — `supabase/config.toml` + the five migrations; verify
   `supabase db push` applies clean; `supabase db reset` idempotent.
3. **`vera_db` core** — `config.py`, `engine.py`, `session.py`, `models/*`.
4. **`vera_db` repositories** — `provider_repository.py`, `vault_repository.py`,
   `__init__.py`; integration tests.
5. **`vera_llm` validation** — `providers.py`, `model_parsing.py`,
   `validation.py`, `client.py`, fixtures, unit tests.
6. **`apps/cli`** — `pyproject`, `deps.py`, `services/provider_service.py`,
   `commands/*`, `main.py`, tests.
7. **Gate** — `make lint`, full `pytest`, the manual CLI flow; write completion
   notes to `docs/superpowers/plans/completed/`.

Tasks 3–5 are independent once Task 1–2 land and can run in parallel; Task 6
depends on 3–5.
