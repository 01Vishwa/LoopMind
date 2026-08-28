# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status — read this first

VERA is a **verifiable data-analysis platform**: an analyst uploads heterogeneous
files (CSV, XLSX, JSON, PDF, Markdown, SQLite), asks a natural-language question,
and a multi-agent loop writes → executes → verifies → self-corrects code until a
verifier accepts the answer. Every answer ships with the script, intermediate
observations, verifier reasoning, and data hashes so the numbers are reproducible.

**The backend is a greenfield rewrite in progress. Do not assume a file's
contents from its name or from git commit messages.** An earlier `backend/`
implementation was deleted and replaced with the `apps/` + `packages/` monorepo
scaffold described in `docs/VERA_BACKEND_PLAN.md`. Many committed files with
feature-y commit messages are **0 bytes**. Currently real:

- `packages/core` — domain models, ports, policies, config, error taxonomy (Phase 1 done)
- `packages/testing` — polyfactory factories, fakes, conformance assertions
- `apps/web` — the Next.js frontend (~5k LOC TS, builds, but not wired to a live API)

Everything else (`apps/api`, `packages/db`, `packages/llm`, `packages/sandbox`,
`packages/retrieval`, `packages/evals`, `packages/observability`, all `agents/`,
`loop/`, and `prompts/registry.py` under core) is an **empty stub**. `pyproject.toml`
files, `.jinja` prompt templates, and YAML config under `packages/core/config`
are real; the Python modules beside them are not.

Before editing, check the file is non-empty:
`git ls-files '*.py' | while read f; do [ -s "$f" ] || echo "EMPTY: $f"; done`

## Roadmap and how work is sequenced

- `docs/VERA_BACKEND_PLAN.md` — the full backend design (domain model, DB DDL,
  LLM gateway, sandbox, API surface, SSE). Treated as the spec.
- `docs/VERA_BACKEND_PHASES.md` — 8 ordered phases, each with a runnable exit
  gate. **No phase starts until the previous phase's gate passes.** Phase 1
  (skeleton + domain) is complete; Phase 2 (Key Vault + BYOK) is next.
- `docs/superpowers/plans/` — active implementation plans; `completed/` holds
  per-phase completion notes with the exact gate output.
- `docs/UI.md` — the frontend design brief (companion to the built `apps/web`).
- `.review/` — a consolidated multi-pass code review from 2026-08-27 and the
  record of frontend fixes applied. Note it predates Phase 1 completion; its
  "repo hygiene" findings about empty root config files are now resolved.

The layout of the actual repo diverges from `PLAN.md §16` in places
(`packages/llm` not `packages/adapters/llm`; no separate `keyvault`/`storage`/
`events` adapter packages; CLI lives under `packages/` not `apps/cli`). Follow
the phase plans and existing tree, not the plan's file lists verbatim.

## Commands

Python (run from repo root; `uv` drives a workspace of the `packages/*` + `apps/api` members):

```bash
make install          # uv sync --all-packages
make lint             # ruff check + ruff format --check + mypy + import-linter
make fmt              # ruff format packages/ apps/
make test             # pytest packages/ apps/ -x -q   (all markers)
make test-unit        # pytest -m "not integration and not e2e"
make test-db          # pytest -m integration          (needs a real Postgres)
```

Single test / narrower runs:

```bash
uv run pytest packages/core/tests/test_policies.py -q
uv run pytest packages/core/tests/test_models.py::test_run_state_round_trips -q
uv run pytest packages/testing -q
```

Individual lint tools (all part of `make lint`):

```bash
uv run ruff check packages/ apps/
uv run mypy packages/core/src packages/testing/src      # strict; only these paths are type-checked today
uv run lint-imports                                     # enforces .importlinter layer contracts
```

Not yet functional (targets exist, dependencies are stubs): `make migrate`,
`make migrate-new`, `make sandbox-build`, `make api-dev`.

Frontend (`apps/web`) — uses **npm**, not pnpm, despite the root `pnpm-workspace.yaml`/`pnpm-lock.yaml`:

```bash
cd apps/web
npm install
npm run dev            # next dev on :3000
npm run build          # next build (used as the frontend gate — must pass, 14 pages)
npm run type-check     # tsc --noEmit
npm run lint           # next lint
```

## Architecture

### Hexagonal core — the layering contract is enforced

`packages/core` (`vera_core`) is the domain: **Pydantic models, `Protocol` ports,
and pure policy functions, with zero dependency on any adapter or the API.**
`.importlinter` enforces three contracts checked in CI / `make lint`:

1. `vera_core` must not import `vera_llm`, `vera_api`, `vera_db`, or `vera_testing`.
2. `vera_testing` must not import adapters or the API.
3. `vera_api` must not import `vera_llm` directly — only through core ports.

When adding a capability: define the `Protocol` in `vera_core/ports/`, add the
domain types it needs to `vera_core/models/`, then implement the adapter in its
own `packages/*` package. The API composes adapters into ports (a `container.py`
is planned). Config the core needs is bundled YAML under
`vera_core/config/` and read via `config/loader.py` — the core does **not** read
environment variables.

### Ports (the seams)

`vera_core/ports/`: `LLMPort`, `KeyVaultPort`, `SandboxPort`, `ObjectStorePort`,
`EventBusPort`, `RetrieverPort`, `ClockPort`, and the repository ports. Every
port is `@runtime_checkable` and has a fake in
`packages/testing/src/vera_testing/fakes/` (`FakeLLM`, `FakeVault`,
`FakeSandbox`, `FakeObjectStore`, `FakeEventBus`).

### The port is the contract — fakes are conformance-tested

`vera_testing/assertions.py::assert_conforms` compares a fake against its port
method-by-method including parameter names and async-ness (`runtime_checkable`
alone only checks method names). `packages/testing/tests/test_fakes_conform.py`
runs this for every fake. When you change a port signature, the conformance test
tells you which fake drifted. `assert_never_contains_secret` guards that
serialized models never leak key material.

### The DS-STAR agent loop (Phase 3+, not yet built)

Planned as an in-process LangGraph `StateGraph` over `RunState`:
`analyze → retrieve → plan → code → execute → {verify | debug | finalize}`, with
`verify → route → {plan | truncate→plan}` for multi-round refinement and
backtracking. The **truncate/backtrack node is the hard part** — it must roll
back plan, script, *and* observations together; `vera_core/policies/backtrack.py`
holds the invariants and there is a property test for them. Other policies:
`truncation` (cap observation text before prompt injection), `context_budget`,
`cycle_detection` (planner oscillation guard), `termination`.

### BYOK model access

VERA never pays for inference. Users connect their own OpenRouter and/or NVIDIA
NIM API keys; both speak the OpenAI `/chat/completions` contract, so the LLM
gateway is a thin router, not a translator. Keys are stored encrypted in a
per-tenant vault (`KeyVaultPort`), never returned to the frontend, never logged.
Default model recommendations live in `vera_core/config/model_routing.yaml`
(reasoning / utility / embedding tiers).

### Multi-tenancy

Every tenant-scoped table gets Postgres RLS with `FORCE ROW LEVEL SECURITY`;
the API sets `app.tenant_id` per request via `set_config(...)` (never string
interpolation) and the DB role must not own tables or have `BYPASSRLS`. The RLS
isolation integration test (Phase 5) is load-bearing — do not delete it.

### Frontend (`apps/web`)

Next.js 15 App Router, React 19, Tailwind 3, Zustand, TanStack Query, Radix, Monaco.

- **Two-tier data flow:** components call `lib/data/*` → Next.js route handlers
  under `app/api/*` (a BFF). Each handler is `proxyOr(request, "/v1/…", <stub>)`
  (`app/api/_lib/proxy.ts`): it proxies to `API_URL` when that env var is set,
  and returns a local stub otherwise. **`API_URL` is currently unset, so the UI
  runs entirely on stubs** that degrade to empty states.
- The `/api/v1/*` rewrite in `next.config.ts` is kept **only for the SSE run
  stream** (`lib/hooks/useRunStream.ts`).
- **No auth flow exists.** `lib/auth/token.ts` is an in-memory token holder and
  `http.ts` sends `Authorization: Bearer` when a token is set, but there is no
  login page and `/api/auth/me` returns a blank viewer. This is a known deferred item.
- Design tokens: `--vera-*` CSS vars are RGB-channel triples in `globals.css`;
  Tailwind `vera.*` colors are `rgb(var(--vera-*-rgb) / <alpha-value>)` so
  opacity/ring/divide variants are theme-aware. `darkMode` matches
  `:root:not(.light)`; theme is owned solely by `next-themes` (default dark).
  Keep colors as tokens — don't hard-code hex.
- Run-mode union is `"precise" | "research"` everywhere — never `"deep"`.

## Conventions

- Python **3.13**, `ruff` (line length 100, rules `E,F,I,N,UP,B,SIM`), `mypy --strict`.
- All domain types are Pydantic v2 models; many are `frozen`. Add a round-trip
  serialization test in `test_models.py` for every new model.
- IDs are `NewType` aliases over `UUID` in `vera_core/models/ids.py`.
- Errors: subclass `VeraError` in `vera_core/errors.py` with `status` and
  `type_uri`; the API maps these to RFC 9457 `application/problem+json`.
- API is versioned under `/v1`; cursor pagination only (never offset); timestamps
  RFC 3339 UTC.
- Prompts are versioned Jinja templates under `vera_core/prompts/templates/<agent>/vN.jinja`,
  resolved by name+version through a registry that records a sha256.
- Tests use polyfactory builders and typed keyword-only factory helpers from
  `vera_testing/factories/` — don't hand-build domain objects in tests.
- `pytest` markers: `integration` (needs real Postgres), `e2e`. Default CI runs
  exclude both.

## Known hazards flagged in review (fix as you touch these areas)

- `.env.example` defaults `VERA_SANDBOX_BACKEND=subprocess` — model-generated
  code must **never** run un-isolated. Fail closed when Docker/gVisor is absent.
- The planned AST deny-list scanner is not a security boundary (`getattr`,
  dunder traversal, string obfuscation bypass it). The container/microVM is.
- User-supplied NIM `base_url` and notification `webhook_url` need SSRF
  validation (block private / link-local / `169.254.169.254`) before any
  request carries a decrypted key.
- JWT auth must enforce `exp`/`aud`/`iss`, pin the algorithm, and construct
  `Principal` field-by-field (no mass-assignment of `role`).
- Root `pnpm-workspace.yaml` + `pnpm-lock.yaml` coexist with `apps/web`'s
  `package-lock.json`. The frontend actually uses npm — pick one before wiring CI.
