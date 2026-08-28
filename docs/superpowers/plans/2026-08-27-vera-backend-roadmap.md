# VERA Backend — Phase Roadmap

> **For agentic workers:** This is the *roadmap*, not an executable plan. Each phase
> gets its own detailed plan document under `docs/superpowers/plans/` written
> immediately before that phase is executed. Execute detailed plans with
> superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Build the VERA backend — a BYOK, multi-agent data-analysis service — as a
modular monolith, in fourteen phases, each shipping something verifiable.

**Spec:** `docs/VERA_BACKEND_PLAN.md`

**Tech Stack:** Python 3.13, FastAPI, LangGraph, SQLAlchemy 2.0 (async), Alembic,
Pydantic v2, Neon Postgres (pgvector), Docker, uv workspace, ruff, mypy strict,
import-linter, pytest.

---

## Repository Reality (audited 2026-08-27)

This is not a greenfield repo, and it is not a working one either. The audit:

| Area | State |
| --- | --- |
| `packages/core` | **Real code.** Models, ports, policies, errors, config loader. 40 unit tests pass. Roughly 90% of spec slice 1, **uncommitted** (`git status` shows most of it untracked). |
| `packages/testing` | **Real code, uncommitted.** FakeLLM, FakeSandbox, FakeVault, FakeObjectStore, FakeEventBus, domain factories. |
| `apps/api` | Directory tree + `pyproject.toml` only. **Every `.py` file is 0 bytes.** |
| `apps/orchestrator`, `apps/worker` | Directory tree only. **Every file 0 bytes.** Not uv workspace members. |
| `packages/db`, `llm`, `sandbox`, `retrieval`, `observability`, `evals` | Directory trees only. **Every `.py` file 0 bytes.** `packages/db/pyproject.toml` is empty. |
| `db/schema/*.sql`, `db/policies/*.sql` | **All 0 bytes.** |
| `docs/api/openapi.yaml`, `config/*.yaml`, `tools/**` | **All 0 bytes.** |
| `.importlinter` | **Broken** — first line is `importlinter]`, missing `[`. `lint-imports` crashes. |
| `mypy.ini` | **Broken** — first line is `mypy]`, missing `[`. `mypy` crashes on the config. |
| `.env.example` | **Empty.** |
| `ruff check` | **14 errors**, 10 auto-fixable. |

So: `make lint` does not run today. The first phase repairs the toolchain before
anything else, because every later phase's exit gate depends on it.

---

## Architectural Decisions

These are decisions this roadmap locks in. Where they deviate from
`docs/VERA_BACKEND_PLAN.md`, the deviation and its reason are stated.

### D1. Modular monolith. Delete `apps/orchestrator` and `apps/worker`.

The spec's own file structure (§16) puts the graph in `packages/core/loop/` and
lists only `apps/api`, `apps/cli`, `apps/web`. §11 dispatches runs with
`asyncio.create_task` inside the API process. The `apps/orchestrator` and
`apps/worker` trees are leftover scaffolding from an earlier, more distributed
design and contain zero bytes of code. They get deleted.

Background jobs (cost rollup, retention sweep, artifact GC) run on APScheduler
inside the API process. No Celery, no Temporal, no Redis, no message queue.

**Revisit when:** a single run's wall-clock exceeds what a web process should
hold, or horizontal scaling requires run affinity. Both are post-launch problems.

### D2. Alembic migrations are the single source of truth for schema.

The spec (§4) writes DDL as `db/schema/NN_*.sql`. The Makefile already calls
Alembic. Maintaining both means they drift, and drifted schema is worse than no
documentation. Alembic wins; `db/schema/` is deleted; `db/ERD.md` is generated
from the models. RLS policies live in migrations too, so a fresh database is
correct after `make migrate` alone.

### D3. Persistence moves from spec slice 8 to Phase 2.

The spec's build order defers the database to slice 8, but slice 2 (key vault +
provider CRUD) *requires* tables: `key_vault`, `provider_connections`,
`provider_models_cache`. Fake repositories that later get thrown away are wasted
work and hide exactly the concurrency and integrity questions that matter. The DB
foundation lands before the first persisted feature.

Everything else in the spec's build order is preserved, including both gates.

### D4. `packages/db` becomes a uv workspace member.

It is currently outside `[tool.uv.workspace].members`, so nothing can import it.
It is added, and import-linter gains a contract: `vera_core` must not import
`vera_db`.

### D5. Two sandbox backends, subprocess first.

`SubprocessSandbox` (resource-limited, AST-scanned, no network) for local dev and
CI, where Docker-in-Docker is a liability. `DockerSandbox` for any deployment that
executes model-authored code. The AST scanner and resource limits are shared and
are the security boundary tested against both.

### D6. Auth is local JWT (HS256) with argon2 password hashing.

The spec allows "local auth (dev) or OIDC (prod)". Local is built; OIDC is a
later swap behind the same `Principal` dependency. Tokens carry
`{sub, tenant_id, role, exp, jti}`.

### D7. Postgres is the event bus and the checkpoint store.

`run_events` table with a per-run monotonic `seq`, polled at 500 ms by the SSE
endpoint, resumable by `Last-Event-ID`. `LISTEN/NOTIFY` is the optimisation, not
the v1. No Redis.

### D8. Python 3.13, not 3.12.

`requires-python = ">=3.13"` across every package, `ruff target-version = py313`.
The spec header says 3.12; the repo is already on 3.13 and the code uses
`StrEnum` and PEP 695 generics. 3.13 wins.

---

## Phase Table

Each phase ends with a green `make lint && make test-unit` and a commit. The
"Proves" column is the phase's exit gate — the thing you demonstrate before
moving on.

| # | Phase | Ships | Proves | Spec slice |
| --- | --- | --- | --- | --- |
| 1 | **Foundation repair + domain** | Working toolchain, pruned scaffold, complete models/ports/policies/fakes | `make lint` and `make test` both run and pass; the type system holds under mypy strict | 1 |
| 2 | **Persistence foundation** | `packages/db` workspace member, async engine, session, Alembic, tenancy + vault + provider tables, RLS | A cross-tenant read returns zero rows against a real Postgres | 8 (moved) |
| 3 | **API skeleton, auth, tenancy** | FastAPI app, DI container, request-id/error/security middleware, RFC 9457 problem+json, JWT auth, RBAC, per-request RLS binding, `/healthz` `/readyz`, register/login/refresh | An authenticated request round-trips; a wrong-tenant request 404s; every error is problem+json | 9 (partial) |
| 4 | **Key vault + provider CRUD** | FernetKeyVault (HKDF per-tenant), `/v1/providers` CRUD + validate + refresh, model cache, redaction, audit log, `vera_llm` validation + `list_models` | A user connects OpenRouter against a mocked transport, sees models, and the raw key never appears in a response, a log line, or a trace | 2 |
| 5 | **Agent defaults** | `agent_defaults` + `model_assignments`, GET/PUT/reset, tier→model resolution with referential validation | A user assigns a model per tier; run preflight passes; deleting a connection in use is rejected | 3 |
| 6 | **Workspaces, files, object store** | `workspaces` + `files`, local-fs object store, upload-url/confirm flow, SHA-256 dedupe, size and kind limits | A file uploads, registers with its content hash, and an oversize or wrong-kind upload is refused | — |
| 7 | **The loop, with fakes** — **GATE A** | `packages/core/loop/` graph + all nodes + edges, prompt registry, all nine agents, remaining policies | Scripted FakeLLM drives backtrack, debug-retry, cycle-break and budget exhaustion — deterministically, no network | 4 |
| 8 | **LLM gateway** | Real OpenRouter + NVIDIA NIM client, structured output (native + prompt fallback), retry/backoff, circuit breaker, cost extraction, `llm_calls` recording | The BYOK parity test: an identical logical request produces an identical body shape on both providers; the circuit opens after 5 failures in 60s | 5 |
| 9 | **Sandbox** | AST scanner, resource limits, subprocess + Docker backends, read-only mounts, output capture and truncation, artifact scan, sandbox image | Denied imports are blocked pre-execution; timeout kills; network egress is zero; a crash is captured, not raised | 6 |
| 10 | **Run persistence + SSE + real prompts** — **GATE B** | `runs` and friends, Postgres checkpointer, Postgres event bus, `RunService` with preflight and cancellation, SSE with resume, real prompts on CSV/JSON fixtures | The loop with real prompts beats single-shot on the fixture set; a run survives an API restart; SSE resumes from `Last-Event-ID` | 7 + 8 |
| 11 | **Full API surface** | Runs list/get/cancel/fork/provenance, saved analyses, profile, notifications, team, VERA API keys, usage, cursor pagination, idempotency, rate limits, generated `openapi.yaml` | Schemathesis passes against the generated spec; the frontend integrates without a backend change | 9 |
| 12 | **Heterogeneous files + retrieval** | XLSX/MD/PDF/SQLite/ZIP analyzers, embedder, pgvector halfvec + HNSW, hybrid search, file selector | A multi-file workspace answers a question that requires picking the right two files out of twenty | 10 |
| 13 | **DS-STAR+ research mode** | Sub-question generator, bounded fan-out, report writer, gap detection and refinement, report endpoints | A research run produces a cited markdown report from parallel sub-runs | 11 |
| 14 | **Usage, team, notifications, ops** | Cost rollups, usage breakdown/history/daily, team CRUD + invitations, webhook dispatch, APScheduler jobs, metrics, tracing, runbooks | Every settings page has a backend; the metric set in §14 is emitted; the runbooks are accurate | 12 |

---

## The Two Gates

**Gate A — end of Phase 7.** The state machine must be provably correct on fakes
before a real provider is touched. Debugging a bad graph and a bad prompt at the
same time is how this class of project stalls. Exit criteria: a test drives every
conditional edge in the graph, and a scripted planner that repeats itself is
caught by cycle detection rather than looping forever.

**Gate B — end of Phase 10.** The loop with real prompts must beat a single-shot
prompt on the fixture set, measured, with the numbers written into the phase's
completion note. If it does not, no amount of Phase 11 API surface rescues the
product — go back to Phase 7's prompts and policies.

---

## Cross-Cutting Requirements

Every phase carries these. They are not a separate phase.

**Failure modes.** For every operation that writes: what happens on DB failure, on
external timeout, on a duplicated request, on two concurrent requests, and is it
safe to retry? POSTs honour `Idempotency-Key`. Writes spanning tables use one
transaction. Uniqueness is enforced by a database constraint, not a pre-check.

**Security.** All external input validated at the schema boundary. Provider API
keys never leave the vault as plaintext beyond the single call that uses them:
never logged, never traced, never serialised into an error, never returned to the
frontend beyond a mask. `SecretStr` at every boundary that could serialise. RLS
enforced by the database, not only by the query.

**Observability.** Structured JSON logs carrying `request_id` and `trace_id`. A
redaction filter that drops anything matching the provider-key shapes. One trace
per run with the span tree from spec §14. Never log a password, token, key, or a
user's file contents.

**Tests.** Every phase adds unit tests for its logic, contract tests for its
endpoints, and integration tests for its schema. Failure paths are tested, not
just happy paths. Tests needing Postgres are marked `integration` and excluded
from `make test-unit`.

---

## Naming and Convention Constraints

Copied from the existing codebase — these hold everywhere.

- Modules start with a one-line docstring; every module ends with `__all__`.
- `from __future__ import annotations` at the top of every module.
- Pydantic models declare `model_config = {"frozen": True}` unless mutation is
  required (`RunState` is the deliberate exception).
- Ports are `typing.Protocol` marked `@runtime_checkable`, keyword-only args.
- Domain IDs are `NewType` wrappers over `UUID` from `vera_core.models.ids`.
- Errors subclass `VeraError` with `status` and `type_uri` class attributes.
- Line length 100. `ruff` lint set: `E, F, I, N, UP, B, SIM`.
- IDs generated as UUIDv7. Timestamps RFC 3339 UTC via `datetime.now(UTC)` —
  never `datetime.utcnow()`.

---

## What Gets Deleted in Phase 1

Empty scaffolding the target architecture does not use. Listed here so the
deletion is a roadmap decision rather than a surprise inside a task.

```
apps/orchestrator/          # D1 — orchestration lives in packages/core/loop
apps/worker/                # D1 — background jobs run in-process
db/schema/                  # D2 — Alembic is the source of truth
db/policies/                # D2 — RLS ships in migrations
db/functions/               # D2
db/queries/                 # D2 — queries live next to their repository
config/                     # duplicate of packages/core/src/vera_core/config/
tools/                      # codegen/, scripts/, vera-cli/ — all 0 bytes, no consumer
```

`db/ERD.md` and `db/seeds/` are kept.
