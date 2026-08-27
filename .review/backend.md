# VERA Backend Code Review

**Scope:** `apps/api/**`, `packages/core/**`, `packages/db/**`, `packages/observability/**`, root config
(`pyproject.toml`, `ruff.toml`, `.importlinter`, `.pre-commit-config.yaml`, `Makefile`, `config/*.yaml`, `mypy.ini`).
**Reference:** `docs/VERA_BACKEND_PLAN.md` (v1.0, implementation-ready).
**Date:** 2026-08-27
**Branch:** `issue-fix`

---

## Headline finding

**Every file in review scope is a zero-byte placeholder.** There is no backend code to review — no
imports, no functions, no models, no SQL. The scope is a directory tree of empty files staged for commit.

Verified: all 64 `*.py` files under `apps/api`, `packages/core`, `packages/db`, `packages/observability`
are 0 bytes; all root config files (`pyproject.toml`, `ruff.toml`, `.importlinter`,
`.pre-commit-config.yaml`, `Makefile`, `mypy.ini`, `config/budgets.yaml`, `config/feature_flags.yaml`,
`config/model_routing.yaml`, `config/retention.yaml`) are 0 bytes. All 16 prompt `*.jinja` templates
are 0 bytes.

The only content in the staged changeset is the frontend (`apps/web/**`, ~5k lines of TS/TSX),
lock files (`pnpm-lock.yaml`, `uv.lock`, `apps/web/package-lock.json`), and docs
(`docs/UI.md`, `docs/api/openapi.yaml` — also 0 bytes, `docs/architecture/*`).

Consequently, categories 1–4 of the review brief (correctness bugs, plan consistency at code level,
security issues in code, API-design details) **cannot be assessed** — there is no implementation.
What follows is an assessment of the scaffold itself, plan-level risks to carry forward, and
what slice-1/slice-2 of the build order still needs.

---

## 1. Scaffold / process issues

### 1.1 Commit messages claim implementations that do not exist  — **design/process concern**

Recent history:

```
a690001 feat: implement multi-file workspace upload system with schema parsing and centralized state management
4ce1943 feat: implement file upload service and UI components for managing session-based file processing
2d3d2f8 feat: implement secure code execution engine with sandboxed subprocess and optional Docker isolation
71bcece implement DS-STAR agent framework and full-stack backend service architecture with file management and authentication support
```

None of these are true for the backend. `71bcece` deleted the entire previous `backend/` implementation
(controllers, agents, parsers, db SQL, tests) and replaced it with empty files. The "secure code
execution engine" (`2d3d2f8`) does not exist in scope — `packages/sandbox/**` is also empty.
Impact: history is not a reliable record of what works; a reader (or CI gate) trusting these messages
will be misled. Fix: use accurate messages (`chore: scaffold monorepo package layout`) and squash/annotate
the misleading ones before they reach `main`.

### 1.2 The previous working backend was deleted wholesale  — **design concern**

`git status` shows ~60 `backend/**` files deleted: `backend/core/ds_star_orchestrator.py`,
`backend/core/llm_client.py`, all nine agent files, seven parsers, `backend/db/migrations/*.sql`,
and 11 test files (`test_orchestrator_integration.py`, `test_code_executor.py`, `test_schema_merger.py`,
…). These held real logic and tests. Replacing them with empty files in the same changeset means the
repo has **regressed from "partially working" to "nothing"** with no migration path. At minimum the old
code should be kept on a branch/tag and ported slice by slice, not deleted before the replacement exists.
This directly violates the plan's Build Order gate philosophy ("Debug the state machine and the prompts
separately").

### 1.3 `.importlinter` created by renaming an empty test file  — **bug (scaffold)**

Git detected `R backend/tests/__init__.py -> .importlinter` (100% similarity — both empty). The plan's
Build Order slice 1 ships `.importlinter` as a deliverable that "proves the type system holds" (the
hexagonal-architecture import contract: `apps` → `packages/core` allowed, `core` → `adapters` forbidden,
etc.). An empty file means `lint-imports` is a no-op and the layering the whole design depends on is
unenforced. Fix: write real contracts, e.g.:

```ini
[importlinter]
root_packages = vera_core, vera_api, vera_db, vera_llm, vera_sandbox

[importlinter:contract:core-is-pure]
name = core depends on nothing internal
type = forbidden
source_modules = vera_core
forbidden_modules = vera_api, vera_db, vera_llm, vera_sandbox, vera_obs
```

### 1.4 Empty root build/tooling config  — **bug (scaffold)**

- `pyproject.toml` (root) — 0 bytes, yet `uv.lock` is committed. A lock file with no manifest is
  stale by definition and `uv sync` has nothing to resolve. Workspace member declaration
  (`[tool.uv.workspace] members = ["apps/*", "packages/*"]`) is absent.
- `apps/api/pyproject.toml`, `packages/core/pyproject.toml`, `packages/db/pyproject.toml`,
  `packages/observability/pyproject.toml` — all 0 bytes. No package is installable, so none of the
  cross-package imports the plan specifies can resolve.
- `ruff.toml` — 0 bytes. `.pre-commit-config.yaml` references (per plan) ruff/mypy hooks; with both
  empty, `pre-commit` and `make lint` do nothing.
- `mypy.ini` — 0 bytes. Plan mandates strict typing (Protocols, `NewType` IDs); unconfigured.
- `Makefile` — 0 bytes. Plan's workflow (`make lint`, `make test`, `make migrate`) is undefined.
- `config/*.yaml` (budgets, feature_flags, model_routing, retention) — all 0 bytes. `model_routing.yaml`
  is referenced by the plan (§16, `packages/core/config/`) for tier→model defaults and by
  `AgentDefaults.reset` ("reset to recommended"); nothing to load.

### 1.5 Missing `__init__.py` throughout  — **bug (scaffold), if not using namespace packages**

Only 1 `__init__.py` exists in the entire Python scope (`vera_api/__init__.py`, itself empty).
Sub-packages `vera_api/dependencies/`, `vera_api/middleware/`, `vera_api/routers/`, `vera_api/routers/v1/`,
`vera_api/schemas/`, `vera_api/services/`, and every `vera_core/*`, `vera_db/*` dir have none. This works
only under PEP-420 namespace packages with correct `[tool.setuptools.packages.find]` / hatch config —
which is absent (see 1.4). As-is, imports would fail. Decide explicitly: namespace packages (configure
the build backend) or regular packages (add `__init__.py`).

### 1.6 Test scaffolding is empty  — **missing tests (expected at this stage, but total)**

`apps/api/tests/conftest.py` — 0 bytes. `apps/api/tests/contract/.gitkeep`, `tests/unit/.gitkeep`,
`packages/core/tests/unit/.gitkeep`, `packages/db/tests/integration/.gitkeep`,
`packages/observability/tests/.gitkeep` — placeholders only. The plan's Testing Strategy (§15) names
specific must-have suites: `FakeLLM`/`FakeSandbox`/`FakeVault` unit tests, repository+RLS integration
tests on a Neon branch, schemathesis contract tests against `docs/api/openapi.yaml` (also empty), and
"the BYOK-specific test" (identical request shapes for OpenRouter vs NIM). None are stubbed even as
skipped tests. The previous changeset *deleted* 11 working test files (1.2).

---

## 2. Package-layout divergence from the plan  — **design concern (likely intentional evolution)**

| Plan (§16) | Actual tree | Note |
| --- | --- | --- |
| `packages/adapters/llm/src/vera_llm/` | `packages/llm/src/vera_llm/` | adapters/ grouping dropped; flat `packages/*`. Update `.importlinter` roots and docs accordingly. |
| `packages/adapters/keyvault/` | *absent* | No keyvault package at all. Plan §6 (Fernet vault, `KeyVaultPort`) is Build Order slice 2 — the first functional slice — and has no home. `packages/core/src/vera_core/ports/key_vault.py` is also **missing** (only `llm.py`, `repository.py`, `retriever.py`, `sandbox.py` port files exist; `object_store.py`, `event_bus.py`, `clock.py`, `key_vault.py` from §3.2/§16 are absent). |
| `packages/adapters/db/` | `packages/db/` | fine, but `checkpointer` module (plan §16, §7.1 `PostgresCheckpointer`) is under `apps/orchestrator/src/vera_orch/graph/checkpointer.py` instead — reasonable given the orchestrator split. |
| `packages/adapters/storage/`, `packages/adapters/events/` | *absent* | `ObjectStorePort` / `EventBusPort` implementations have no package. SSE (§10) depends on the event bus. |
| in-process orchestrator via `asyncio.create_task` (§11) | separate `apps/orchestrator` (Temporal-style: `workflows/`, `activities/`) | Significant architecture change from the plan. Not in review scope, but it means `apps/api/services/run_service.py` (§11 sample) will dispatch to Temporal, not spawn a task. The plan text should be reconciled. |

The domain-model files that *do* exist as (empty) stubs are also renamed/split vs the plan:
plan `models/provider.py` + `models/agent_config.py` + `models/workspace.py` →
actual `models/{code,file,observation,plan,report,routing,run,tenancy,verdict}.py`. There is **no
`provider.py` and no `agent_config.py`** — the `ProviderConnection`, `ProviderKind`, `ModelInfo`,
`AgentTier`, `ModelAssignment`, `AgentDefaults` types central to BYOK (§2, §3.1) have no file. Given
BYOK is "the core design decision", the absence of any provider/agent-config model stub is the single
biggest structural gap.

---

## 3. Plan-level risks to carry forward (apply when these files get implemented)

These are in the plan's own sample code and will become real issues in the empty files that will hold
them. Flagging now so the scaffold is filled correctly.

### 3.1 SQL injection via string-interpolated tenant id  — **security (high, latent)**

Plan §12, destined for `apps/api/src/vera_api/dependencies/tenancy.py`:

```python
await db.execute(text(f"SET LOCAL app.tenant_id = '{principal.tenant_id}'"))
```

`SET LOCAL` does not accept bind parameters, so this pattern is tempting, but f-string interpolation
into raw SQL is the exact anti-pattern the brief calls out. Mitigations, in order of preference:
1. Use `set_config`: `await db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(principal.tenant_id)})` — fully parameterized.
2. If keeping `SET LOCAL`, coerce and validate first: `tid = str(uuid.UUID(str(principal.tenant_id)))` then interpolate — a parsed `UUID` round-tripped to `str` cannot carry an injection payload.

`principal.tenant_id` comes from a JWT claim (§9.1). If the JWT is HS256-verified the value is trusted,
but defense-in-depth demands (1). Note also the RLS policies (`db/policies/rls_tenancy.sql`) are empty,
so even a correct `set_config` protects nothing yet.

### 3.2 JWT handling is unsafe as written  — **security (high, latent)**

Plan §12, destined for `dependencies/auth.py`:

```python
async def auth(authorization: str = Header(...)) -> Principal:
    token = authorization.removeprefix("Bearer ").strip()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    return Principal(**payload)
```

Issues to fix on implementation:
- No `exp` / `nbf` / `iat` verification options shown, no `aud`/`iss` checks. PyJWT verifies `exp` by
  default but `require=["exp","sub","tenant_id"]` should be explicit.
- No handling of `jwt.InvalidTokenError` / `ExpiredSignatureError` → these must map to `401`
  (a `UnauthorizedError` is missing from the error taxonomy §13 entirely — see 3.4).
- `Principal(**payload)` blindly trusts claim names; extra claims will raise or, worse, if `Principal`
  had `model_config extra="allow"`, be silently attached. Map claims explicitly.
- Algorithm confusion: `algorithms=["HS256"]` is hard-coded — good — but ensure the same secret is
  never also used to verify RS256 tokens elsewhere.
- Plan §9.1 also says "OIDC provider (prod)" — HS256 with a shared secret is incompatible with OIDC
  (which is RS256/JWKS). The auth dependency needs a strategy switch.

### 3.3 `require_role` is an `async def` returning a sync closure  — **bug (latent)**

Plan §12:

```python
async def require_role(*allowed: Role):
    def checker(principal: Principal = Depends(auth)):
        ...
    return checker
```

Used as `Depends(require_role(Role.ADMIN))`, FastAPI would receive a coroutine, not a dependency
callable. This must be a plain `def` (a dependency factory), not `async def`. Minor, but it is
copy-paste-ready code in the plan and will be wrong in every router that uses it.

### 3.4 Error taxonomy gaps  — **API design**

Plan §13:
- No `UnauthorizedError` (401) class — every auth failure path needs it.
- `class NotFoundError(VeraError): status = 404` uses class-body assignment `status = 404` with a
  trailing statement on the same line as the `class` — as literally written (`class NotFoundError(VeraError):          status = 404`) it is valid Python but unusual; ensure the real file uses normal bodies.
- `BudgetExhaustedError` with `status = 200` is a category error — a 200 "error" that flows through
  `vera_error_handler` would emit `application/problem+json` with `status: 200`, which violates RFC 9457
  (§3.1 of the RFC: `status` conveys the HTTP status; problem+json is for 4xx/5xx). Budget exhaustion
  is a normal terminal run state, not an error — model it as `RunStatus` + a normal `200` run payload,
  not a `VeraError`.
- The handler reads `request.state.trace_id`; `middleware/request_id.py` (empty) must set it before the
  exception handler runs, and must also set it on the error path (exception handlers run outside the
  middleware stack in Starlette for some failure modes). Also the field is `trace_id` but §9.4 /
  §9.2 and the `X-Request-Id` header use "request id" — reconcile `trace_id` (OTel) vs `request_id`
  (correlation); the plan conflates them.

### 3.5 RFC 9457 shape is incomplete  — **API design**

Plan's problem document has `type, title, status, detail, trace_id`. RFC 9457 also defines `instance`
(URI ref for the specific occurrence). For validation errors (422) the plan gives no `errors`/
extension member schema, so the frontend cannot render field-level messages. Define a standard
extension (e.g. `errors: [{pointer, detail}]`) once, in `schemas/errors.py`.

### 3.6 SSE stream design  — **correctness (latent)**

Plan §10 `event_generator`:
- Polls `event_repo.read_from` every 0.5s with no `request.is_disconnected()` check → leaked tasks and
  DB load after the client goes away.
- `seq = last_event_id or 0` — `Last-Event-ID: 0` is falsy; harmless here but the idiom is fragile.
- No heartbeat/keepalive comment frames → proxies will kill idle connections before the first event.
- Terminal detection keys on `event.type in ("run.finished", "run.failed")` but `RunStatus` also has
  `CANCELLED`; a cancelled run never terminates the stream.
- `payload.model_dump_json()` is called on `event.payload` which is described as `jsonb` (a dict) from
  the DB — a dict has no `.model_dump_json()`. Type mismatch between the ORM row and the Pydantic event.

### 3.7 Idempotency-Key (§9.4) has no storage design  — **API design**

"Idempotency-Key header honoured on all POSTs" but there is no table in the DDL (§4) for idempotency
keys and no middleware file for it. `POST /v1/runs` in particular (creates a run + spawns work) must
dedupe. Needs an `idempotency_keys(tenant_id, key, request_hash, response_json, created_at)` table with
a unique constraint and a 24h TTL.

### 3.8 UUIDv7 (§9.4 "All IDs: UUIDv7") vs `gen_random_uuid()` (§4 DDL)  — **consistency**

Every `CREATE TABLE` in §4 defaults `id` to `gen_random_uuid()` (v4, random, not time-sortable),
contradicting §9.4 and §11's `uuid7()`. `db/functions/uuid_v7.sql` exists (empty). Pick one: either
generate v7 in the app and drop the column default, or implement the SQL function and use it as the
default. Cursor pagination (§9.4 "Never offset") depends on sortable IDs.

---

## 4. Observability scope (`packages/observability/**`)

All four files empty: `logging.py`, `metrics.py`, `redaction.py`, `tracing.py`.
Plan §14 + §6.2 require `redaction.py` to guarantee **API keys are never logged** — this is a
BYOK security control, and it does not exist. The metrics dict (§14) and the per-run span tree
(§14) are unimplemented. `middleware/otel.py` (empty) would wire it in. Nothing to review; flag that
`redaction.py` is security-load-bearing and should be slice-1, not deferred.

---

## 5. What is genuinely fine

- The **directory structure** (minus the divergences in §2) closely mirrors the plan and is a
  reasonable hexagonal layout: `ports/` in core, adapters as separate packages, `apps/api` thin.
- Splitting the orchestrator into its own app (`apps/orchestrator`, Temporal-style) is a defensible
  upgrade over the plan's `asyncio.create_task` (§11) — that pattern loses runs on API restart, which
  the plan itself acknowledges ("Temporal later").
- `OWNERS` files per package and `docs/adr/` scaffold indicate good governance intent.
- The frontend (out of scope) is substantially implemented, so the empty backend is the critical path.

---

## Severity-ordered summary

| # | Severity | Finding | Location |
| --- | --- | --- | --- |
| 1 | Blocker | Entire backend scope is 0-byte files; nothing implemented | all of scope |
| 2 | Blocker | Root/package `pyproject.toml`, `ruff.toml`, `mypy.ini`, `Makefile` all empty → nothing installable, lintable, or testable; `uv.lock` committed against no manifest | §1.4 |
| 3 | High | Previous working backend + 11 test files deleted with no replacement | §1.2 |
| 4 | High | Misleading "feat: implement …" commit messages for empty scaffolds | §1.1 |
| 5 | High | `.importlinter` is an empty renamed file → architecture layering unenforced | §1.3 |
| 6 | High | No provider/agent-config domain model stubs and no `key_vault` port → BYOK core (Build Order slice 2) has no home | §2 |
| 7 | High (latent) | Plan's `SET LOCAL app.tenant_id = '{tenant_id}'` f-string → use `set_config` parameterized; RLS policy files also empty | §3.1 |
| 8 | High (latent) | JWT dependency: no exp/aud/iss checks, no 401 mapping, no `UnauthorizedError` in taxonomy, HS256 vs OIDC unresolved | §3.2, §3.4 |
| 9 | Medium | `BudgetExhaustedError` with `status = 200` violates RFC 9457; budget exhaustion should be a run state | §3.4 |
| 10 | Medium | SSE generator: no disconnect check, no heartbeat, misses `CANCELLED`, `payload.model_dump_json()` on a dict | §3.6 |
| 11 | Medium | `require_role` written as `async def` returning sync closure — broken as a FastAPI dependency factory | §3.3 |
| 12 | Medium | Idempotency-Key promised but no table / middleware | §3.7 |
| 13 | Medium | UUIDv7 requirement contradicted by `gen_random_uuid()` defaults throughout DDL | §3.8 |
| 14 | Medium | `redaction.py` (prevents API-key logging — a BYOK security control) unimplemented | §4 |
| 15 | Low | Missing `__init__.py` everywhere with no namespace-package build config | §1.5 |
| 16 | Low | Package layout diverges from plan §16 (`packages/adapters/*` flattened; storage/events packages absent); plan should be reconciled | §2 |
| 17 | Low | Test suites named in §15 (RLS integration, schemathesis contract, BYOK request-shape parity) not even stubbed; `openapi.yaml` empty | §1.6 |
