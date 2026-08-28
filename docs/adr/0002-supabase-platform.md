# 2. Supabase as the sole backend platform

Date: 2026-08-28

## Status

Accepted

## Context

VERA's backend is a greenfield rewrite. The original plan (`VERA_BACKEND_PLAN.md`)
targeted Neon Postgres for data, a Fernet-based application vault
(`VERA_VAULT_MASTER_KEY`) for BYOK provider keys, custom JWT auth with a
per-request `app.tenant_id` GUC, local-filesystem object storage, and a
Postgres `LISTEN/NOTIFY` + SSE-polling event stream.

That is five moving parts to build, secure, and operate. We want one managed
platform that covers all of them without discarding the parts of the plan that
are sound — the relational domain model, RLS-based multi-tenancy, pgvector
retrieval, SQLAlchemy 2.0, and the hexagonal `vera_core` port boundary.

Two options were considered.

### Option A — FastAPI + SQLAlchemy retained, Supabase as managed add-ons

Keep FastAPI + SQLAlchemy 2.0 + Pydantic v2 as the API and data layer. Connect
to Supabase Postgres directly over the connection string (transaction pooler at
:6543 for runtime, session mode at :5432 for migrations and `LISTEN/NOTIFY`).
Use Supabase's managed features behind the **existing `vera_core` ports**:

- **Vault** (`supabase_vault` extension: `vault.create_secret`,
  `vault.update_secret`, `vault.decrypted_secrets`) behind `KeyVaultPort`.
- **Auth** behind `Principal` / request-auth (Phase 6).
- **Storage** behind `ObjectStorePort` (Phase 5).
- **Realtime** behind `EventBusPort` (Phase 6).
- **RLS** unchanged — Postgres is Postgres.

### Option B — PostgREST + Edge Functions replace FastAPI

Drop FastAPI. Expose tables through PostgREST, move orchestration into Supabase
Edge Functions (Deno/TypeScript).

## Decision

**We choose Option A.** Supabase is the **sole external service** for the VERA
backend. It is a managed Postgres with Vault, Auth, Storage, and Realtime as
add-ons, each consumed through an existing `vera_core` port. FastAPI +
SQLAlchemy + Alembic-free migrations (`supabase/migrations/`) remain the API and
data layer.

`packages/core` is **not modified** by this decision. Every port
(`KeyVaultPort`, `ProviderRepositoryPort`, `AgentDefaultsRepositoryPort`,
`LLMPort`) and every domain model (`ProviderConnection`, `ModelInfo`,
`ValidationResult`, `AgentDefaults`) is already frozen by Phase 1.

### Per-feature phase mapping

| Supabase feature | VERA port / concern | Lands in |
| --- | --- | --- |
| Postgres + Supavisor pooling | `vera_db` engine / session | **Phase 2** |
| Vault (`supabase_vault`) | `KeyVaultPort` | **Phase 2** |
| RLS | tenancy isolation | **Phase 2** (policies authored) / Phase 5 (load-bearing isolation test) |
| Auth | `Principal`, request auth | Phase 6 |
| Storage | `ObjectStorePort` | Phase 5 |
| Realtime | `EventBusPort` / SSE | Phase 6 |

## Consequences

### Positive

- One vendor, one dashboard, one bill. Local development via `supabase start`
  gives the same Postgres + Vault + Auth + Storage + Realtime stack.
- `VERA_VAULT_MASTER_KEY` and the `FernetKeyVault` design are deleted. Supabase
  Vault manages its own encryption key (`pgsodium`); the app never holds key
  material at rest.
- Auth, Storage, and Realtime are managed — less code to write and secure in
  Phases 5–6.
- The hexagonal boundary means Supabase is swappable later: each feature sits
  behind a port with a fake.

### Negative / risks

- Transaction-mode pooling (:6543) forbids prepared-statement caching — the
  pooled async engine must set `statement_cache_size=0` / `NullPool`. Migrations,
  `LISTEN/NOTIFY`, and the RLS integration test use the :5432 direct connection.
- `vault.decrypted_secrets` must never be granted to the `authenticated` role —
  server / service-role only.
- Vendor concentration: an outage takes down data, secrets, auth, and events at
  once. Accepted for a pre-product rewrite.

### Rejected — Option B

Rejected. It discards SQLAlchemy, the migration tooling, and the typed
repository layer, and couples the DS-STAR orchestration loop to the Deno
runtime. The port boundary in `vera_core` assumes an in-process Python
composition root; PostgREST + Edge Functions would fork the architecture for no
gain over Option A.
