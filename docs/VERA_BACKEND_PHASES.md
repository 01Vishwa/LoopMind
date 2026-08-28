# VERA Backend — Phase-by-Phase Implementation Sequence

### Ordered build plan with entry criteria, exit criteria, and exact file deliverables per phase

**Companion to:** `VERA_BACKEND_PLAN.md`
**Rule:** no phase starts until the previous phase's exit gate passes. Every gate is a runnable command, not a judgement call.

---

## Overview — 8 Phases, 12 Weeks

```
Phase 1  Skeleton & Domain          ██░░░░░░░░░░░░░░  Week 1
Phase 2  Key Vault & BYOK           ████░░░░░░░░░░░░  Week 2
Phase 3  Loop with Fakes            ██████░░░░░░░░░░  Week 3–4
Phase 4  LLM Gateway & Sandbox      ████████░░░░░░░░  Week 5–6
Phase 5  Persistence & Events       ██████████░░░░░░  Week 7–8
Phase 6  Full API Surface           ████████████░░░░  Week 9–10
Phase 7  Heterogeneous Files & RAG  ██████████████░░  Week 11
Phase 8  DS-STAR+ & Evals           ████████████████  Week 12
```

---

## Phase 1 — Skeleton & Domain Core

**Goal:** the monorepo compiles, types check, linter passes, import layers hold, and every domain concept has a Pydantic model.

**Duration:** ~3 days

### What you build

```
Files created:
  pyproject.toml                           # uv workspace root
  ruff.toml                                # ALL rules enabled, documented ignores
  mypy.ini                                 # strict mode
  .importlinter                            # layer contracts
  .pre-commit-config.yaml
  Makefile                                 # verify, lint, typecheck, test, layers
  .env.example

  packages/core/pyproject.toml
  packages/core/src/vera_core/
    models/ids.py                          # UUIDv7 newtypes
    models/tenancy.py                      # TenantId, Principal, Role
    models/provider.py                     # ProviderKind, ProviderConnection, ModelInfo
    models/agent_config.py                 # AgentTier, ModelAssignment, AgentDefaults
    models/workspace.py                    # FileKind, FileRef, FileDescription, SchemaField
    models/plan.py                         # PlanStep
    models/code.py                         # CodeArtifact
    models/observation.py                  # Observation, ArtifactRef
    models/verdict.py                      # Verdict
    models/routing.py                      # RouterAction, RouterDecision
    models/run.py                          # RunState, RunBudget, RunStatus, RunMode
    models/report.py                       # SubQuestion, Report, Citation
    models/events.py                       # RunEvent union type
    ports/llm.py                           # LLMPort, LLMResponse
    ports/key_vault.py                     # KeyVaultPort
    ports/sandbox.py                       # SandboxPort
    ports/object_store.py                  # ObjectStorePort
    ports/event_bus.py                     # EventBusPort
    ports/retriever.py                     # RetrieverPort
    ports/repository.py                    # all repository ports
    ports/clock.py                         # ClockPort
    policies/truncation.py                 # head+tail, dataframe-aware, traceback
    policies/budget.py                     # RunBudget enforcement
    policies/backtrack.py                  # plan + script rollback invariants
    policies/termination.py                # MAX_ROUNDS, graceful degradation
    policies/cycle_detection.py            # planner-loop guard
    policies/context_budget.py             # per-segment token allocation
    config/loader.py                       # YAML config reader
    config/model_routing.yaml
    config/budgets.yaml
    errors.py                              # VeraError hierarchy (every error class)

  packages/core/tests/unit/
    test_backtrack.py                      # property test: plan+script rollback
    test_truncation.py                     # property test: idempotent, bounded
    test_budget.py                         # property test: monotonic, bounded
    test_models.py                         # round-trip serialisation for every model

  packages/testing/pyproject.toml
  packages/testing/src/vera_testing/
    factories/                             # polyfactory builders for every domain model
    fixtures/                              # pytest fixtures
    assertions.py                          # assert_plan_invariants, assert_backtrack_correct
```

### Implementation sequence

```
Step 1.1  Create workspace root files (pyproject.toml, ruff.toml, mypy.ini, Makefile)
Step 1.2  Create packages/core/pyproject.toml with zero dependencies except pydantic
Step 1.3  Write all model files — start from ids.py, work outward
Step 1.4  Write all port interfaces — each is a Protocol class, no implementation
Step 1.5  Write errors.py — the full typed exception hierarchy
Step 1.6  Write policies — truncation, budget, backtrack, termination, cycle detection
Step 1.7  Write config loader + YAML defaults
Step 1.8  Write .importlinter — the layer contract
Step 1.9  Write packages/testing — factories + fixtures + assertions
Step 1.10 Write unit tests — property tests for backtrack, truncation, budget
Step 1.11 Wire up pre-commit, Makefile targets
```

### Exit gate

```bash
make verify   # must pass: ruff, mypy --strict, import-linter, pytest
```

All green, zero warnings. The domain model is the vocabulary every subsequent phase speaks — if a field name is wrong here, it cascades everywhere.

---

## Phase 2 — Key Vault & BYOK Provider Management

**Goal:** a user can connect an OpenRouter or NVIDIA NIM key, VERA validates it, stores it encrypted, and fetches the available models list.

**Duration:** ~4 days

**Entry gate:** Phase 1 exit gate passes.

### What you build

```
Files created:
  packages/adapters/keyvault/pyproject.toml
  packages/adapters/keyvault/src/vera_keyvault/
    fernet_vault.py                        # Fernet encryption, per-tenant derivation
    fake.py                                # FakeVault (in-memory dict)
    tests/unit/test_fernet_vault.py

  packages/adapters/llm/pyproject.toml
  packages/adapters/llm/src/vera_llm/
    providers.py                           # PROVIDER_CONFIGS (OpenRouter, NVIDIA NIM)
    validation.py                          # validate_connection: list models + test completion
    fakes.py                               # FakeLLM (scripted responses), RecordReplayLLM
    tests/unit/
      test_providers.py
      test_validation.py                   # with httpx mock, recorded cassettes

  db/schema/02_providers.sql               # provider_connections, provider_models_cache
  db/schema/13_keyvault.sql                # key_vault table
  db/policies/rls_tenancy.sql              # RLS on provider tables

  packages/adapters/db/pyproject.toml
  packages/adapters/db/src/vera_db/
    engine.py                              # pooled vs direct Neon DSN
    session.py                             # async_sessionmaker + RLS GUC binding
    models/provider.py                     # SQLAlchemy ORM for provider_connections
    models/keyvault.py                     # SQLAlchemy ORM for key_vault
    repositories/provider_repository.py    # implements ProviderRepositoryPort
    types/                                 # halfvec, UUIDv7 custom types
    migrations/env.py
    migrations/versions/001_initial_providers.py

  apps/cli/pyproject.toml
  apps/cli/src/vera_cli/
    main.py                                # typer app
    commands/db.py                         # branch create, migrate, seed
    commands/doctor.py                     # environment validation
    commands/provider.py                   # vera provider add, list, validate
```

### Implementation sequence

```
Step 2.1  Implement FakeVault (in-memory, for tests)
Step 2.2  Implement FernetVault with per-tenant key derivation
Step 2.3  Write FernetVault unit tests — encrypt/decrypt round-trip, tenant isolation
Step 2.4  Define PROVIDER_CONFIGS for OpenRouter and NVIDIA NIM
Step 2.5  Implement validate_connection (list models + test completion)
Step 2.6  Record HTTP cassettes for validation against both providers
Step 2.7  Write validation unit tests using recorded cassettes
Step 2.8  Create DB schema (02_providers.sql, 13_keyvault.sql)
Step 2.9  Create Alembic migration 001
Step 2.10 Implement provider_repository (CRUD + model cache refresh)
Step 2.11 Write CLI commands: vera provider add --kind openrouter --key sk-or-v1-...
Step 2.12 Integration test: add provider → validate → list models → store encrypted key
```

### Exit gate

```bash
# Unit tests pass
make test

# CLI flow works end-to-end against a real Neon branch
uv run vera db branch create --name test/phase2
uv run vera db migrate
uv run vera provider add --kind openrouter --key $OPENROUTER_API_KEY
uv run vera provider list   # shows connected provider + model count
```

The user can connect a provider and see available models from the terminal. No API, no frontend — just the CLI proving the vault, validation, and persistence work.

---

## Phase 3 — The DS-STAR Loop with Fakes

**Goal:** the complete agent loop — analyze, plan, code, execute, verify, route (including backtrack), debug, finalize — runs end-to-end with FakeLLM and FakeSandbox, from the CLI.

**Duration:** ~8 days

**Entry gate:** Phase 2 exit gate passes.

### Why this comes before real LLMs

Debugging a state machine and prompt engineering simultaneously is the single most common way agent projects stall. FakeLLM returns scripted responses, so you can deterministically force every path: a clean success (sufficient on round 1), a multi-round refinement (insufficient → add step → sufficient), and a backtrack (insufficient → backtrack(2) → replan → sufficient). If the state machine is wrong, you find out in milliseconds, not minutes.

### What you build

```
Files created:
  packages/core/src/vera_core/
    agents/base.py                         # Agent[TIn, TOut] protocol
    agents/analyzer.py                     # calls LLMPort, parses FileDescription
    agents/planner.py                      # calls LLMPort, returns PlanStep
    agents/coder.py                        # calls LLMPort, returns CodeArtifact
    agents/verifier.py                     # calls LLMPort, returns Verdict
    agents/router.py                       # calls LLMPort, returns RouterDecision
    agents/debugger.py                     # calls LLMPort, returns CodeArtifact
    agents/finalizer.py                    # calls LLMPort, returns CodeArtifact
    loop/graph.py                          # LangGraph StateGraph assembly
    loop/edges.py                          # conditional edge predicates
    loop/nodes/analyze.py
    loop/nodes/retrieve.py
    loop/nodes/plan.py
    loop/nodes/code.py
    loop/nodes/execute.py
    loop/nodes/debug.py
    loop/nodes/verify.py
    loop/nodes/route.py
    loop/nodes/truncate.py                 # ★ plan + script + observation rollback
    loop/nodes/finalize.py
    prompts/registry.py                    # name + version → template + sha256
    prompts/templates/analyzer/v1.jinja
    prompts/templates/planner/v1.jinja
    prompts/templates/coder/v1.jinja
    prompts/templates/verifier/v1.jinja
    prompts/templates/router/v1.jinja
    prompts/templates/debugger/v1.jinja
    prompts/templates/finalizer/v1.jinja

  packages/adapters/llm/src/vera_llm/
    fakes.py                               # FakeLLM with scenario scripting

  packages/adapters/sandbox/pyproject.toml
  packages/adapters/sandbox/src/vera_sandbox/
    backends/fake.py                       # FakeSandbox with recorded observations

  packages/adapters/events/pyproject.toml
  packages/adapters/events/src/vera_events/
    memory_bus.py                          # in-memory event bus for tests

  apps/cli/src/vera_cli/
    commands/run.py                        # vera run --workspace ./fixtures --fake-llm

  fixtures/
    payments/payments.csv
    payments/merchant_data.json
    payments/fees.json
    manifest.yaml                          # expected answers for smoke queries

  packages/core/tests/unit/
    test_graph.py                          # full loop: success, multi-round, backtrack
    test_truncate.py                       # backtrack invariants with real state
    test_cycle_detection.py                # oscillation guard
```

### Implementation sequence

```
Step 3.1  Implement FakeLLM with scenario scripting:
          fake.add_response("verifier", Verdict(sufficient=False, reason="missing fee deduction", ...))
          fake.add_response("router", RouterDecision(action=BACKTRACK, backtrack_index=2, ...))
          fake.add_response("verifier", Verdict(sufficient=True, reason="correct", ...))

Step 3.2  Implement FakeSandbox with recorded observations:
          fake.add_observation(Observation(stdout="merchant  revenue\nAcme     12340.50\n...", ...))

Step 3.3  Implement MemoryEventBus

Step 3.4  Write the Agent protocol (base.py) and all nine agent implementations
          Each agent: render prompt → call llm.complete → parse structured output → return

Step 3.5  Write the prompt templates (v1.jinja for each agent)
          These are DRAFT prompts — they will be refined in Phase 4
          Focus on the schema contract, not the quality of reasoning

Step 3.6  Implement loop/nodes/* — one node per agent
          Each node: update RunState, emit event, check budget, return state

Step 3.7  ★ Implement truncate.py — the hardest node:
          - Truncate plan to plan[:l]
          - Roll back script to the checkpoint at step l-1
          - Roll back observations
          - Record abandoned branch
          - Inject negative constraint for replanning

Step 3.8  Wire the LangGraph StateGraph in graph.py:
          - Entry → analyze → retrieve → plan → code → execute
          - Execute → verify (success) | debug (crash) | finalize (budget)
          - Verify → finalize (sufficient) | route (insufficient) | finalize (max_rounds)
          - Route → plan (add_step) | truncate (backtrack)
          - Truncate → plan
          - Debug → execute (fixed) | finalize (max_retries)

Step 3.9  Implement the CLI run command:
          vera run --workspace ./fixtures/payments --query "..." --fake-llm

Step 3.10 Write graph tests — three scenarios:
          Scenario A: sufficient on round 1 (happy path)
          Scenario B: insufficient → add_step → sufficient (multi-round)
          Scenario C: insufficient → backtrack(2) → replan → sufficient (the money test)

Step 3.11 Write the cycle detection test:
          Same step proposed twice at the same index → forced add_step or termination
```

### Exit gate

```bash
# All unit tests pass including the three graph scenarios
make test

# The CLI runs the full loop with fakes
make loop
# → prints: Analyzed 3 files → Plan: 5 steps → Backtracked step 3 → Answer: ...

# Backtrack invariant holds in every scenario
uv run pytest packages/core/tests/unit/test_graph.py -v
```

The entire DS-STAR state machine works. No real LLM, no real code execution, no database — but every path through the graph is verified, including backtracking.

---

## Phase 4 — Real LLM Gateway & Real Sandbox

**Goal:** replace fakes with real providers. A real OpenRouter/NVIDIA NIM call produces a real response; real model-generated code executes safely in Docker.

**Duration:** ~8 days

**Entry gate:** Phase 3 exit gate passes.

### What you build

```
Files created:
  packages/adapters/llm/src/vera_llm/
    client.py                              # LLMClient: implements LLMPort
    routing.py                             # resolve AgentDefaults → provider + model
    structured.py                          # JSON mode + prompt-constrained fallback
    resilience.py                          # retry (3x, backoff), circuit breaker
    cost.py                                # cost extraction (header or computed)
    tests/unit/
      test_structured.py                   # JSON parsing, retry on validation failure
      test_resilience.py                   # retry on 429/5xx, circuit breaker open/close
      test_cost.py                         # cost from OpenRouter header vs computed
    tests/integration/
      test_openrouter_live.py              # marked live_llm, runs nightly only
      test_nvidia_live.py

  packages/adapters/sandbox/src/vera_sandbox/
    client.py                              # DockerSandboxClient: implements SandboxPort
    backends/local_docker.py               # Docker container lifecycle
    guards/ast_scanner.py                  # deny-list: socket, subprocess, ctypes...
    mounts.py                              # read-only data binding
    capture.py                             # streamed stdout + artifact manifest
    image/
      Dockerfile                           # fat base image
      requirements.lock                    # pinned: polars, pandas, duckdb, scikit-learn, etc.
    tests/unit/
      test_ast_scanner.py                  # deny-list coverage
    tests/integration/
      test_docker_sandbox.py               # real execution of safe + unsafe scripts

  packages/core/src/vera_core/
    prompts/templates/                     # REFINED v2 prompts for all agents
      analyzer/v2.jinja
      planner/v2.jinja
      coder/v2.jinja
      verifier/v2.jinja
      router/v2.jinja
      debugger/v2.jinja
      finalizer/v2.jinja

  apps/cli/src/vera_cli/
    commands/describe.py                   # vera describe ./fixtures/payments/fees.json
```

### Implementation sequence

```
Step 4.1  Build the sandbox Docker image:
          docker build -t vera-sandbox:latest -f packages/adapters/sandbox/image/Dockerfile .

Step 4.2  Implement AstScanner — deny-list + AST walk
          Test: scan("import socket") → violation
          Test: scan("import pandas as pd") → clean

Step 4.3  Implement DockerSandboxClient:
          - Write script to tempdir
          - Mount data read-only
          - network_disabled=True, mem_limit, pids_limit, user=nonroot
          - Stream stdout with timeout
          - Destroy container after

Step 4.4  Test sandbox: execute safe script → observe output
          Test sandbox: execute "import socket" → AST rejection before execution
          Test sandbox: execute infinite loop → timeout kill

Step 4.5  Implement LLMClient.complete():
          - Resolve provider connection → get kind, base_url, api_key_ref
          - Retrieve key from vault
          - Build OpenAI-compatible request body
          - Add provider-specific headers
          - Send with resilience wrapper
          - Parse response, extract cost

Step 4.6  Implement structured output:
          - Strategy 1: native JSON mode (response_format)
          - Strategy 2: prompt-constrained + parse + retry on validation failure
          - Test both paths

Step 4.7  Implement resilience:
          - Retry with backoff on 429, 502, 503, 504, timeout
          - Do NOT retry on 400, 401, 404
          - Circuit breaker per provider_connection_id
          - Test: mock 429 → retry succeeds on attempt 2
          - Test: 5 failures in 60s → circuit opens → ProviderUnavailableError

Step 4.8  Implement cost tracking:
          - OpenRouter: extract from x-openrouter-cost response header
          - NVIDIA NIM: compute from token counts × model pricing
          - Test both extraction paths

Step 4.9  Refine prompts to v2:
          Run vera describe on each fixture file with a real model
          Iterate the analyzer prompt until descriptions are rich and accurate
          Then iterate planner/coder/verifier/router prompts

Step 4.10 End-to-end CLI test with real providers:
          vera run --workspace ./fixtures/payments --query "What percentage of transactions used credit cards?"
          → must produce a correct, verified answer

Step 4.11 ★ THE GATE TEST: does the loop beat single-shot?
          Compare: loop answer vs a single "write code to answer this" prompt
          On 10 fixture queries, the loop must win ≥ 7/10
```

### Exit gate

```bash
# AST scanner and sandbox tests pass
make test

# Real LLM call succeeds
uv run vera describe ./fixtures/payments/fees.json
# → prints structured FileDescription

# Full loop with real models beats single-shot on fixtures
uv run vera run --workspace ./fixtures/payments \
  --query "What share of Q3 chargebacks came from merchants with manual capture delay?"
# → verified answer with correct number
```

**This is the go/no-go gate for the entire project.** If the loop with real prompts doesn't beat a single-shot prompt on your own fixtures, stop and fix the prompts before building anything else. The verification loop, the backtracking, the incremental coding — they all have to *measurably help*, or the architectural complexity is unjustified.

---

## Phase 5 — Persistence & Event Streaming

**Goal:** runs survive process restart. Tenants are isolated by RLS. The event stream is durable and replayable.

**Duration:** ~8 days

**Entry gate:** Phase 4 exit gate passes.

### What you build

```
Files created:
  db/schema/00_extensions.sql
  db/schema/01_tenancy.sql
  db/schema/03_workspaces.sql
  db/schema/04_descriptions.sql
  db/schema/05_runs.sql
  db/schema/06_run_events.sql
  db/schema/07_llm_calls.sql
  db/schema/08_subquestions.sql
  db/schema/09_checkpoints.sql
  db/schema/10_notifications.sql
  db/schema/11_saved.sql
  db/schema/12_audit.sql
  db/policies/roles.sql
  db/functions/uuid_v7.sql
  db/functions/current_tenant.sql
  db/seeds/dev/
  db/seeds/test/

  packages/adapters/db/src/vera_db/
    models/{tenant,user,workspace,file,description,run,step,verdict,
            router_decision,event,llm_call,subquestion,checkpoint,
            saved_analysis,notification,audit}.py
    repositories/
      run_repository.py
      file_repository.py
      description_repository.py
      event_repository.py
      llm_call_repository.py
      workspace_repository.py
      saved_analysis_repository.py
      audit_repository.py
    checkpointer.py                        # LangGraph Postgres checkpointer
    migrations/versions/002_full_schema.py

  packages/adapters/storage/pyproject.toml
  packages/adapters/storage/src/vera_storage/
    local_fs.py                            # content-addressed .vera/objects/<sha>
    fake.py

  packages/adapters/events/src/vera_events/
    postgres_bus.py                        # INSERT into run_events + optional NOTIFY

  packages/adapters/db/tests/integration/
    test_rls.py                            # ★ tenant A cannot read tenant B, even without ORM filter
    test_run_repository.py
    test_event_repository.py
    test_checkpointer.py                   # kill mid-run → restart → resume from checkpoint
```

### Implementation sequence

```
Step 5.1  Write all remaining db/schema/*.sql files
Step 5.2  Write db/policies/rls_tenancy.sql — RLS on EVERY tenant-scoped table
Step 5.3  Create Alembic migration 002 applying the full schema
Step 5.4  Implement all SQLAlchemy ORM models (one file per table, mirrors schema)
Step 5.5  Implement all repositories — start with run_repository (most complex)
Step 5.6  Implement event_repository — append with auto-incrementing seq, range read
Step 5.7  Implement PostgresBus — INSERT + NOTIFY on the direct DSN
Step 5.8  Implement LangGraph PostgresCheckpointer — serialize RunState to jsonb
Step 5.9  Implement LocalFsStore — content-addressed put/get
Step 5.10 Implement audit_repository — append-only log

Step 5.11 ★ Write the RLS integration test:
          - Create tenant A and tenant B
          - Insert a run for tenant A
          - Set app.tenant_id = tenant B
          - SELECT * FROM runs → must return 0 rows
          - This test must NEVER be deleted

Step 5.12 Write the checkpoint resume test:
          - Start a run, checkpoint at round 2
          - Kill the process
          - Restart, load from checkpoint
          - Run continues from round 2, not round 0

Step 5.13 Wire persistence into the loop:
          - After each node: checkpoint state + persist step/verdict/decision
          - Emit events via PostgresBus

Step 5.14 Update CLI: vera run now persists results to DB
Step 5.15 Seed script: dev seed with a demo tenant, user, workspace, and files
```

### Exit gate

```bash
# Migrations apply cleanly
uv run vera db migrate

# RLS test passes
uv run pytest packages/adapters/db/tests/integration/test_rls.py -v

# Checkpoint resume test passes
uv run pytest packages/adapters/db/tests/integration/test_checkpointer.py -v

# Full loop persists to DB
uv run vera run --workspace ./fixtures/payments --query "..."
uv run vera run list   # shows the completed run with cost + status
```

---

## Phase 6 — Full API Surface

**Goal:** the frontend can integrate. Every endpoint from the spec works, with auth, RBAC, validation, pagination, SSE streaming, and RFC 9457 errors.

**Duration:** ~8 days

**Entry gate:** Phase 5 exit gate passes.

### What you build

```
Files created:
  apps/api/pyproject.toml
  apps/api/src/vera_api/
    main.py                                # app factory, lifespan, CORS
    settings.py                            # pydantic-settings
    container.py                           # ★ wires ports → adapters (one file)
    dependencies/auth.py                   # JWT → Principal
    dependencies/tenancy.py                # SET LOCAL app.tenant_id
    dependencies/db.py                     # async session per request
    middleware/request_id.py
    middleware/error_handler.py            # VeraError → RFC 9457
    middleware/logging.py
    schemas/workspace.py
    schemas/file.py
    schemas/run.py
    schemas/provider.py
    schemas/settings.py
    schemas/team.py
    schemas/problem.py
    routers/v1/workspaces.py
    routers/v1/files.py
    routers/v1/ingest.py
    routers/v1/providers.py
    routers/v1/agent_defaults.py
    routers/v1/runs.py
    routers/v1/run_events.py               # SSE endpoint
    routers/v1/reports.py
    routers/v1/provenance.py
    routers/v1/saved_analyses.py
    routers/v1/settings_profile.py
    routers/v1/settings_notifications.py
    routers/v1/team.py
    routers/v1/api_keys.py
    routers/v1/usage.py
    routers/health.py
    services/upload_service.py
    services/ingest_service.py
    services/run_service.py

  docs/api/openapi.yaml                    # hand-written contract
  tools/codegen/openapi_to_ts.sh

  apps/api/tests/
    unit/test_auth.py
    unit/test_error_handler.py
    contract/test_openapi.py               # schemathesis vs openapi.yaml
```

### Implementation sequence

```
Step 6.1  Write the OpenAPI spec (docs/api/openapi.yaml) first — contract-first
Step 6.2  Implement main.py, settings.py, container.py
Step 6.3  Implement auth + tenancy dependencies
Step 6.4  Implement error_handler middleware (VeraError → problem+json)
Step 6.5  Implement health endpoints (/healthz, /readyz)
Step 6.6  Implement provider endpoints (POST/GET/DELETE /v1/providers)
Step 6.7  Implement agent defaults endpoints (GET/PUT /v1/settings/agent-defaults)
Step 6.8  Implement workspace + file endpoints
Step 6.9  Implement ingest endpoint (POST /v1/workspaces/{id}/ingest → 202)
Step 6.10 Implement run endpoints (POST/GET /v1/runs, cancel, fork)
Step 6.11 ★ Implement SSE endpoint (GET /v1/runs/{id}/events):
          - Read from run_events table
          - Support Last-Event-ID for reconnect
          - End stream on terminal events
Step 6.12 Implement provenance endpoint
Step 6.13 Implement settings, team, API keys, usage endpoints
Step 6.14 Implement saved analyses endpoints
Step 6.15 Run schemathesis against the OpenAPI spec — every endpoint must match
Step 6.16 Generate TypeScript client from OpenAPI
```

### Exit gate

```bash
# API starts and health checks pass
uvicorn vera_api.main:app --port 8000
curl http://localhost:8000/healthz   # 200

# Contract tests pass
uv run pytest apps/api/tests/contract/ -v

# Full flow via HTTP:
# 1. POST /v1/providers → connect OpenRouter
# 2. PUT /v1/settings/agent-defaults → assign models
# 3. POST /v1/workspaces → create workspace
# 4. Upload files
# 5. POST /v1/workspaces/{id}/ingest → analyze
# 6. POST /v1/runs → start run
# 7. GET /v1/runs/{id}/events → SSE stream shows plan, code, verdict, answer
```

---

## Phase 7 — Heterogeneous Files & Retrieval

**Goal:** VERA handles XLSX (multi-sheet, irregular tables), Markdown, TXT, PDF, SQLite, ZIP, and Parquet. The Retriever selects the right files via hybrid search.

**Duration:** ~5 days

**Entry gate:** Phase 6 exit gate passes.

### What you build

```
Files created:
  packages/core/src/vera_core/
    prompts/templates/analyzer/formats/
      csv.jinja, json.jinja, xlsx.jinja, pdf.jinja,
      md.jinja, txt.jinja, sqlite.jinja, parquet.jinja, zip.jinja

  packages/adapters/retrieval/pyproject.toml
  packages/adapters/retrieval/src/vera_retrieval/
    embedder.py                            # embed description text
    indexer.py                             # pgvector HNSW upsert
    hybrid_search.py                       # vector ⊕ BM25 → RRF
    selector.py                            # top-K + pinned named files

  fixtures/
    proteomics/                            # multi-sheet xlsx with irregular tables
    mixed/                                 # csv + pdf + sqlite + zip

  packages/adapters/retrieval/tests/
    integration/test_hybrid_search.py      # real pgvector
```

### Implementation sequence

```
Step 7.1  Write per-format analyzer prompt templates
Step 7.2  Test analyzer on each format: xlsx, pdf, md, txt, sqlite, zip, parquet
Step 7.3  Implement embedder (call embedding model via LLMPort)
Step 7.4  Implement indexer (pgvector HNSW upsert)
Step 7.5  Implement hybrid_search (vector cosine + BM25 text search → RRF fusion)
Step 7.6  Implement selector (top-K + pin files mentioned by name in query)
Step 7.7  Wire retriever into the loop's retrieve node
Step 7.8  Test on mixed-format fixtures: query that requires joining CSV + JSON + PDF
```

### Exit gate

```bash
# Multi-format fixture produces correct answer
uv run vera run --workspace ./fixtures/mixed \
  --query "Cross-reference the invoice PDF with the transactions CSV and report discrepancies"
# → correct answer referencing both files

# Retriever selects the right files from a 20-file workspace
uv run pytest packages/adapters/retrieval/tests/integration/ -v
```

---

## Phase 8 — DS-STAR+ Research Mode & Evaluation Harness

**Goal:** open-ended research queries produce cited reports. An eval harness gates prompt changes in CI.

**Duration:** ~5 days

**Entry gate:** Phase 7 exit gate passes.

### What you build

```
Files created:
  packages/core/src/vera_core/
    agents/subquestion_generator.py
    agents/report_writer.py
    loop/research.py                       # fan-out, report compilation, gap detection
    prompts/templates/subquestion_generator/v1.jinja
    prompts/templates/report_writer/v1.jinja

  packages/evals/pyproject.toml
  packages/evals/src/vera_evals/
    harness.py                             # runner, concurrency, variance (n=3)
    scorers/numeric.py                     # tolerance match
    scorers/dataframe.py                   # schema + sorted content hash
    scorers/llm_judge.py                   # rubric + κ calibration
    scorers/component.py                   # verifier P/R, router action accuracy
    datasets/golden/                       # 40 curated cases (expand to 150+ over time)
    datasets/regression/                   # every prod failure becomes a permanent case
    datasets/adversarial/                  # prompt injection, malformed files, zip bombs
    baselines/main.json                    # committed scores from main branch
    report.py                              # markdown + JSON CI report

  apps/cli/src/vera_cli/
    commands/evals.py                      # vera evals run --suite fast
```

### Implementation sequence

```
Step 8.1  Implement SubQuestionGeneratorAgent + prompt
Step 8.2  Implement ReportWriterAgent + prompt (must enforce [SQ-n] citations)
Step 8.3  Implement research.py:
          - Generate sub-questions
          - Fan-out with bounded concurrency (semaphore 8)
          - Collect results (failed SQs → [SQ-n: UNRESOLVED])
          - Compile report with citations
          - Gap detection → supplementary questions → refine report

Step 8.4  Test research mode on fixtures:
          vera run --workspace ./fixtures/payments --mode research \
            --query "Produce a Q3 payments risk review"

Step 8.5  Build the eval harness:
          - Runner: execute N cases, 3 runs each, report mean ± σ
          - Numeric scorer: exact or tolerance match
          - LLM judge: rubric-based, calibrated against human labels

Step 8.6  Create the golden dataset: 40 cases across easy/hard × each format
Step 8.7  Create adversarial cases: CSV with "ignore instructions" cells, empty files
Step 8.8  Run full eval suite, commit baseline scores
Step 8.9  Wire eval into Makefile: make evals
```

### Exit gate

```bash
# Research mode produces a cited report
uv run vera run --workspace ./fixtures/payments --mode research \
  --query "Produce a comprehensive Q3 payments analysis"
# → markdown report with [SQ-1] through [SQ-N] citations

# Eval suite passes against baseline
make evals
# → 40 cases, mean accuracy ≥ 80% easy / ≥ 40% hard, all adversarial cases handled

# Baseline committed
cat packages/evals/baselines/main.json
```

---

## Summary — The Gates That Matter

| Gate | Phase | Question | If it fails |
| --- | --- | --- | --- |
| **Types hold** | 1 → 2 | Does `make verify` pass with zero warnings? | Fix the models before anything depends on them |
| **Provider connects** | 2 → 3 | Can you connect OpenRouter and list models from the CLI? | BYOK is the product; fix vault + validation |
| **Loop works with fakes** | 3 → 4 | Does backtrack correctly roll back plan AND script? | Fix the state machine before adding real LLMs |
| **Loop beats single-shot** | 4 → 5 | Does the loop produce better answers than one prompt? | Fix the prompts or reconsider the architecture |
| **Tenants are isolated** | 5 → 6 | Does the RLS test prove cross-tenant reads are impossible? | Fix RLS before building the API |
| **API matches contract** | 6 → 7 | Does schemathesis find zero contract violations? | Fix the API before the frontend integrates |
| **Mixed formats work** | 7 → 8 | Can a query join data across CSV + JSON + PDF? | Fix the analyzer prompts per format |
| **Evals are gated** | 8 → ship | Does the eval suite block a regression? | You have no quality guarantee without it |

**The single most important gate is Phase 4 → 5: "does the loop beat single-shot?"** If it doesn't, the nine-agent architecture, the backtracking, the verification — all of it is overhead without payoff. Find that out in week 6, not week 12.
