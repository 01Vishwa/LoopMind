# VERA — Backend Engineering Plan

### End-to-end backend development with BYOK model access

**Role perspective:** Senior Backend Engineer + AI Engineer
**Stack:** Python 3.13, FastAPI, LangGraph, SQLAlchemy 2.0, Pydantic v2, Supabase Postgres (Supavisor pooling), Docker
**Model access:** BYOK via OpenRouter (500+ models) and NVIDIA NIM (self-hosted or cloud endpoints)
**Status:** v1.0 — Implementation-ready

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [BYOK Model Access — The Core Design Decision](#2-byok-model-access--the-core-design-decision)
3. [Domain Model — Complete Schema](#3-domain-model--complete-schema)
4. [Database Schema — Full DDL](#4-database-schema--full-ddl)
5. [The LLM Gateway — Provider-Agnostic Routing](#5-the-llm-gateway--provider-agnostic-routing)
6. [Key Vault — Secure BYOK Storage](#6-key-vault--secure-byok-storage)
7. [Agent Orchestration — The DS-STAR Loop](#7-agent-orchestration--the-ds-star-loop)
8. [Sandbox — Untrusted Code Execution](#8-sandbox--untrusted-code-execution)
9. [API Surface — Complete Endpoint Specification](#9-api-surface--complete-endpoint-specification)
10. [SSE Event Streaming](#10-sse-event-streaming)
11. [Background Jobs](#11-background-jobs)
12. [Authentication & Authorization](#12-authentication--authorization)
13. [Error Taxonomy](#13-error-taxonomy)
14. [Observability](#14-observability)
15. [Testing Strategy](#15-testing-strategy)
16. [Backend File Structure](#16-backend-file-structure)
17. [Configuration & Environment](#17-configuration--environment)
18. [Build Order](#18-build-order)

---

## 1. Architecture Overview

```
                            ┌───────────────────────┐
                            │     Next.js Web App    │
                            └──────────┬────────────┘
                                       │ REST + SSE
                            ┌──────────▼────────────┐
                            │   FastAPI (vera-api)   │
                            │   Auth · RBAC · RLS    │
                            └──────────┬────────────┘
                                       │
                     ┌─────────────────┼──────────────────┐
                     │                 │                   │
              ┌──────▼──────┐  ┌───────▼──────┐  ┌────────▼───────┐
              │  LLM Gateway │  │  Orchestrator │  │  Sandbox Fleet │
              │  (BYOK)      │  │  (LangGraph)  │  │  (Docker)      │
              └──────┬──────┘  └──────────────┘  └────────────────┘
                     │
         ┌───────────┼────────────┐
         │           │            │
   ┌─────▼────┐ ┌────▼─────┐ ┌───▼──────────┐
   │OpenRouter │ │ NVIDIA   │ │ Direct       │
   │  API      │ │ NIM API  │ │ Provider*    │
   └──────────┘ └──────────┘ └──────────────┘
                              * future: Anthropic, OpenAI direct
```

**The critical insight:** <cite index="9-1">OpenRouter provides a unified API to access models from multiple providers including OpenAI, Anthropic, Google, and open-source models</cite> — and <cite index="24-1">NVIDIA NIM exposes `/v1/chat/completions` following the OpenAI-compatible format</cite>. Both providers implement the same OpenAI chat completions contract. This means the LLM Gateway is a thin routing layer, not a translation layer — the same request shape works everywhere.

---

## 2. BYOK Model Access — The Core Design Decision

### 2.1 What BYOK means for VERA

VERA does not pay for model inference. Users bring their own API keys from supported providers. VERA stores those keys encrypted, routes requests through them, and tracks usage for the user's visibility. VERA never sees the bill — the user's provider account is charged directly.

### 2.2 Why OpenRouter + NVIDIA NIM

| Provider | What it gives VERA | User value |
| --- | --- | --- |
| **OpenRouter** | <cite index="10-1">Access to 400+ models from 74 infrastructure providers through one API key</cite>. Single key unlocks Claude, GPT, Gemini, Llama, Mistral, DeepSeek, Qwen — everything. | One key, every model. No vendor lock-in. User picks the cheapest provider per model. |
| **NVIDIA NIM** | <cite index="25-1">Performance-optimised inference microservices for deploying AI models in the cloud, data centre, or on your own workstation, exposing industry-standard APIs</cite>. OpenAI-compatible endpoints. | Enterprise users self-host models behind their firewall. Data never leaves their VPC. On-prem compliance. |

### 2.3 Provider capabilities matrix

| Capability | OpenRouter | NVIDIA NIM |
| --- | --- | --- |
| Endpoint | `https://openrouter.ai/api/v1/chat/completions` | User-provided (e.g., `https://nim.corp.internal/v1/chat/completions`) |
| Auth | `Authorization: Bearer <OPENROUTER_API_KEY>` | `Authorization: Bearer <NVIDIA_API_KEY>` |
| Model selection | `model: "anthropic/claude-sonnet-5"` (OpenRouter model ID) | `model: "meta/llama-3.1-70b-instruct"` (NIM model ID) |
| Structured output | JSON mode on supporting models | JSON mode on supporting models |
| Streaming | SSE `stream: true` | SSE `stream: true` |
| Function calling | On supporting models | On supporting models |
| List models | `GET /api/v1/models` | `GET /v1/models` |
| Cost tracking | Response header `x-openrouter-cost` | Not provided — compute locally from token counts |

### 2.4 The connection model

A user can connect **multiple providers**, each with its own key. Each provider connection is validated on creation (a test call), stored encrypted, and selectable per-agent-tier in Agent Defaults.

```
User Account
├── Provider: OpenRouter
│   ├── Key: or_sk_●●●●●●
│   ├── Status: ✓ Connected
│   └── Available models: 500+ (fetched from /api/v1/models)
│
├── Provider: NVIDIA NIM
│   ├── Key: nvapi-●●●●●●
│   ├── Endpoint: https://integrate.api.nvidia.com
│   ├── Status: ✓ Connected
│   └── Available models: 12 (fetched from /v1/models)
│
└── Agent Defaults
    ├── Reasoning tier → anthropic/claude-sonnet-5 (via OpenRouter)
    └── Utility tier → meta/llama-3.1-70b-instruct (via NVIDIA NIM)
```

---

## 3. Domain Model — Complete Schema

### 3.1 Core domain types

```python
# packages/core/src/vera_core/models/ids.py
from uuid import UUID
from typing import NewType

TenantId = NewType("TenantId", UUID)
UserId = NewType("UserId", UUID)
WorkspaceId = NewType("WorkspaceId", UUID)
FileId = NewType("FileId", UUID)
RunId = NewType("RunId", UUID)
ProviderConnectionId = NewType("ProviderConnectionId", UUID)
```

```python
# packages/core/src/vera_core/models/provider.py
from enum import StrEnum
from pydantic import BaseModel, HttpUrl, SecretStr

class ProviderKind(StrEnum):
    OPENROUTER = "openrouter"
    NVIDIA_NIM = "nvidia_nim"

class ProviderConnection(BaseModel):
    """A user's BYOK connection to an LLM provider."""
    id: ProviderConnectionId
    tenant_id: TenantId
    user_id: UserId
    kind: ProviderKind
    display_name: str                          # "My OpenRouter", "Corp NIM"
    base_url: HttpUrl                          # openrouter.ai/api/v1 or custom NIM endpoint
    api_key_ref: str                           # vault reference, never the raw key
    status: ConnectionStatus
    available_models: list[ModelInfo] | None   # cached from /models, refreshed periodically
    created_at: datetime
    last_validated_at: datetime | None
    last_error: str | None

class ConnectionStatus(StrEnum):
    CONNECTED = "connected"
    VALIDATING = "validating"
    FAILED = "failed"
    REVOKED = "revoked"

class ModelInfo(BaseModel):
    """A model available through a provider connection."""
    model_id: str                              # e.g., "anthropic/claude-sonnet-5"
    display_name: str                          # e.g., "Claude Sonnet 5"
    context_window: int
    input_price_per_m: Decimal | None          # per million tokens, null if unknown
    output_price_per_m: Decimal | None
    supports_json_mode: bool
    supports_function_calling: bool
    supports_vision: bool
```

```python
# packages/core/src/vera_core/models/agent_config.py
class AgentTier(StrEnum):
    REASONING = "reasoning"      # planner, coder, verifier, router
    UTILITY = "utility"          # analyzer, debugger, finalizer
    EMBEDDING = "embedding"      # retriever

class ModelAssignment(BaseModel):
    """Maps an agent tier to a specific model on a specific provider."""
    tier: AgentTier
    provider_connection_id: ProviderConnectionId
    model_id: str                # the provider's model identifier
    temperature: float = 0.0
    max_tokens: int = 4096

class AgentDefaults(BaseModel):
    """User-level default configuration for all runs."""
    user_id: UserId
    assignments: list[ModelAssignment]
    max_rounds: int = 10
    max_cost_usd: Decimal = Decimal("5.00")
    max_debug_attempts: int = 3
    max_files_per_workspace: int = 50
    max_file_size_bytes: int = 104_857_600     # 100 MB
    retriever_top_k: int = 12
```

```python
# packages/core/src/vera_core/models/workspace.py
class FileKind(StrEnum):
    CSV = "csv"; XLSX = "xlsx"; JSON = "json"; PARQUET = "parquet"
    MARKDOWN = "md"; TXT = "txt"; PDF = "pdf"; SQLITE = "sqlite"; ZIP = "zip"

class FileRef(BaseModel):
    file_id: FileId
    workspace_id: WorkspaceId
    filename: str
    kind: FileKind
    size_bytes: int
    content_sha256: str
    uri: str                                   # local: .vera/objects/<sha>
    created_at: datetime

class FileDescription(BaseModel):
    file_id: FileId
    summary_text: str                          # capped at 8 KB
    schema_fields: list[SchemaField]
    row_count: int | None
    sheet_names: list[str] | None
    sample_rows: list[dict] | None
    generated_by_script_sha: str
    analyzer_model: str                        # which model generated it
    embedding: list[float] | None = Field(default=None, exclude=True)
```

```python
# packages/core/src/vera_core/models/run.py
class RunMode(StrEnum):
    PRECISE = "precise"
    RESEARCH = "research"

class RunStatus(StrEnum):
    QUEUED = "queued"
    ANALYZING = "analyzing"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PlanStep(BaseModel):
    index: int
    text: str
    acceptance_criteria: list[str] | None
    created_at_round: int
    superseded: bool = False

class CodeArtifact(BaseModel):
    language: Literal["python", "sql"] = "python"
    source: str
    sha256: str
    parent_sha256: str | None

class Observation(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    artifacts: list[ArtifactRef]
    truncated: bool

class Verdict(BaseModel):
    sufficient: bool
    reason: str = Field(min_length=10)
    missing_aspects: list[str] = []

class RouterAction(StrEnum):
    ADD_STEP = "add_step"
    BACKTRACK = "backtrack"

class RouterDecision(BaseModel):
    action: RouterAction
    backtrack_index: int | None = None
    rationale: str

class RunBudget(BaseModel):
    max_rounds: int = 10
    max_debug_attempts: int = 3
    max_wall_clock_s: int = 900
    max_cost_usd: Decimal = Decimal("5.00")

class RunState(BaseModel):
    run_id: RunId
    tenant_id: TenantId
    user_id: UserId
    workspace_id: WorkspaceId
    query: str
    mode: RunMode
    status: RunStatus
    descriptions: list[FileDescription]
    plan: list[PlanStep]
    script: CodeArtifact | None
    observations: list[Observation]
    verdicts: list[Verdict]
    routes: list[RouterDecision]
    round: int = 0
    debug_attempts: int = 0
    budget: RunBudget
    cost_usd: Decimal = Decimal("0")
    total_tokens: int = 0
    answer: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
```

### 3.2 Port interfaces

```python
# packages/core/src/vera_core/ports/llm.py
from typing import Protocol

class LLMPort(Protocol):
    async def complete(
        self,
        *,
        provider_connection_id: ProviderConnectionId,
        model_id: str,
        messages: list[dict],
        response_schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        run_id: RunId | None = None,
    ) -> LLMResponse: ...

    async def list_models(
        self,
        *,
        provider_connection_id: ProviderConnectionId,
    ) -> list[ModelInfo]: ...

    async def validate_connection(
        self,
        *,
        kind: ProviderKind,
        base_url: str,
        api_key: str,
    ) -> ValidationResult: ...

class LLMResponse(BaseModel):
    content: str
    parsed: BaseModel | None            # if response_schema was provided
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    cost_usd: Decimal | None            # from provider header or computed
    model_id: str
    latency_ms: int
    provider_kind: ProviderKind
```

```python
# packages/core/src/vera_core/ports/key_vault.py
class KeyVaultPort(Protocol):
    async def store(self, *, tenant_id: TenantId, ref: str, plaintext: str) -> None: ...
    async def retrieve(self, *, tenant_id: TenantId, ref: str) -> str: ...
    async def delete(self, *, tenant_id: TenantId, ref: str) -> None: ...

# packages/core/src/vera_core/ports/sandbox.py
class SandboxPort(Protocol):
    async def execute(
        self, *, script: CodeArtifact, mounts: list[DataMount],
        limits: ResourceLimits, run_id: RunId
    ) -> Observation: ...

# packages/core/src/vera_core/ports/object_store.py
class ObjectStorePort(Protocol):
    async def put(self, *, key: str, data: bytes) -> str: ...
    async def get(self, *, key: str) -> bytes: ...
    async def delete(self, *, key: str) -> None: ...
    async def presign_upload(self, *, key: str, content_type: str, max_bytes: int) -> PresignedUpload: ...

# packages/core/src/vera_core/ports/event_bus.py
class EventBusPort(Protocol):
    async def emit(self, *, run_id: RunId, event: RunEvent) -> int: ...
    async def read_from(self, *, run_id: RunId, after_seq: int) -> AsyncIterator[RunEvent]: ...

# packages/core/src/vera_core/ports/retriever.py
class RetrieverPort(Protocol):
    async def search(
        self, *, query: str, workspace_id: WorkspaceId,
        top_k: int = 12, pinned_file_ids: list[FileId] | None = None
    ) -> list[FileDescription]: ...

# packages/core/src/vera_core/ports/repository.py
class RunRepositoryPort(Protocol):
    async def create(self, *, run: RunState) -> RunState: ...
    async def get(self, *, run_id: RunId, tenant_id: TenantId) -> RunState | None: ...
    async def update(self, *, run: RunState) -> RunState: ...
    async def list_for_user(self, *, user_id: UserId, cursor: str | None, limit: int) -> Page[RunSummary]: ...

class ProviderRepositoryPort(Protocol):
    async def create_connection(self, *, conn: ProviderConnection) -> ProviderConnection: ...
    async def get_connection(self, *, id: ProviderConnectionId, tenant_id: TenantId) -> ProviderConnection | None: ...
    async def list_connections(self, *, user_id: UserId) -> list[ProviderConnection]: ...
    async def update_connection(self, *, conn: ProviderConnection) -> ProviderConnection: ...
    async def delete_connection(self, *, id: ProviderConnectionId, tenant_id: TenantId) -> None: ...

class AgentDefaultsRepositoryPort(Protocol):
    async def get(self, *, user_id: UserId) -> AgentDefaults | None: ...
    async def upsert(self, *, defaults: AgentDefaults) -> AgentDefaults: ...
```

---

## 4. Database Schema — Full DDL

> **Supabase edition:** the database is **Supabase Postgres**, not Neon. Runtime
> traffic goes through **Supavisor** transaction-mode pooling (`:6543`,
> `statement_cache_size=0` / `NullPool` on the async engine); migrations,
> `LISTEN/NOTIFY`, and the RLS integration test use the session-mode direct
> connection (`:5432`). Schema is applied from `supabase/migrations/*.sql` via
> `supabase db push` — there is no Alembic. The DDL below is otherwise unchanged
> (Postgres is Postgres); `supabase_vault` is added to the extensions list.

```sql
-- db/schema/00_extensions.sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- db/schema/01_tenancy.sql
CREATE TABLE tenants (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL,
    plan            text NOT NULL DEFAULT 'free',
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email           text NOT NULL UNIQUE,
    full_name       text NOT NULL,
    role            text NOT NULL DEFAULT 'analyst',  -- owner|admin|analyst|viewer
    avatar_url      text,
    timezone        text DEFAULT 'UTC',
    date_format     text DEFAULT 'YYYY-MM-DD',
    default_run_mode text DEFAULT 'precise',
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- db/schema/02_providers.sql
CREATE TABLE provider_connections (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind            text NOT NULL,                    -- openrouter | nvidia_nim
    display_name    text NOT NULL,
    base_url        text NOT NULL,
    api_key_ref     text NOT NULL,                    -- vault reference, NEVER plaintext
    status          text NOT NULL DEFAULT 'validating',
    last_validated_at timestamptz,
    last_error      text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE provider_models_cache (
    provider_connection_id uuid NOT NULL REFERENCES provider_connections(id) ON DELETE CASCADE,
    model_id        text NOT NULL,
    display_name    text NOT NULL,
    context_window  integer,
    input_price_per_m  numeric(12, 6),
    output_price_per_m numeric(12, 6),
    supports_json_mode boolean DEFAULT false,
    supports_function_calling boolean DEFAULT false,
    supports_vision boolean DEFAULT false,
    cached_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (provider_connection_id, model_id)
);

CREATE TABLE agent_defaults (
    user_id         uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    max_rounds      integer NOT NULL DEFAULT 10,
    max_cost_usd    numeric(10, 2) NOT NULL DEFAULT 5.00,
    max_debug_attempts integer NOT NULL DEFAULT 3,
    max_files_per_workspace integer NOT NULL DEFAULT 50,
    max_file_size_bytes bigint NOT NULL DEFAULT 104857600,
    retriever_top_k integer NOT NULL DEFAULT 12,
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE model_assignments (
    user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tier            text NOT NULL,                    -- reasoning | utility | embedding
    provider_connection_id uuid NOT NULL REFERENCES provider_connections(id),
    model_id        text NOT NULL,
    temperature     real NOT NULL DEFAULT 0.0,
    max_tokens      integer NOT NULL DEFAULT 4096,
    PRIMARY KEY (user_id, tier)
);

-- db/schema/03_workspaces.sql
CREATE TABLE workspaces (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id         uuid NOT NULL REFERENCES users(id),
    name            text NOT NULL,
    description     text,
    status          text NOT NULL DEFAULT 'empty',   -- empty|ingesting|partial|ready
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE files (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    filename        text NOT NULL,
    kind            text NOT NULL,
    size_bytes      bigint NOT NULL,
    content_sha256  text NOT NULL,
    uri             text NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- db/schema/04_descriptions.sql
CREATE TABLE file_descriptions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id         uuid NOT NULL UNIQUE REFERENCES files(id) ON DELETE CASCADE,
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    summary_text    text NOT NULL,
    schema_fields   jsonb,
    row_count       integer,
    sheet_names     jsonb,
    sample_rows     jsonb,
    script_sha      text NOT NULL,
    analyzer_model  text NOT NULL,
    prompt_version  text NOT NULL,
    embedding       halfvec(3072),
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_fd_embedding ON file_descriptions
    USING hnsw (embedding halfvec_cosine_ops) WITH (m = 16, ef_construction = 64);

-- db/schema/05_runs.sql
CREATE TABLE runs (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id         uuid NOT NULL REFERENCES users(id),
    workspace_id    uuid NOT NULL REFERENCES workspaces(id),
    query           text NOT NULL,
    mode            text NOT NULL DEFAULT 'precise',
    status          text NOT NULL DEFAULT 'queued',
    round           integer NOT NULL DEFAULT 0,
    cost_usd        numeric(10, 4) NOT NULL DEFAULT 0,
    total_tokens    integer NOT NULL DEFAULT 0,
    answer          text,
    budget          jsonb NOT NULL,
    started_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz,
    trace_id        text
);

CREATE TABLE run_steps (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    round           integer NOT NULL,
    step_index      integer NOT NULL,
    step_text       text NOT NULL,
    acceptance_criteria jsonb,
    code_sha        text,
    code_source     text,
    observation_ref text,                            -- object store key for full output
    observation_truncated text,                      -- prompt-safe truncation
    superseded      boolean NOT NULL DEFAULT false,
    superseded_by_round integer,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE verdicts (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    round           integer NOT NULL,
    sufficient      boolean NOT NULL,
    reason          text NOT NULL,
    missing_aspects jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE router_decisions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    round           integer NOT NULL,
    action          text NOT NULL,                   -- add_step | backtrack
    backtrack_index integer,
    rationale       text NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- db/schema/06_run_events.sql
CREATE TABLE run_events (
    run_id          uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    seq             bigint NOT NULL,
    type            text NOT NULL,
    payload         jsonb NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, seq)
);

-- db/schema/07_llm_calls.sql
CREATE TABLE llm_calls (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          uuid REFERENCES runs(id) ON DELETE SET NULL,
    tenant_id       uuid NOT NULL REFERENCES tenants(id),
    user_id         uuid NOT NULL REFERENCES users(id),
    agent           text NOT NULL,                   -- analyzer|planner|coder|verifier|...
    provider_kind   text NOT NULL,
    model_id        text NOT NULL,
    prompt_version  text NOT NULL,
    input_tokens    integer NOT NULL,
    output_tokens   integer NOT NULL,
    cached_tokens   integer NOT NULL DEFAULT 0,
    cost_usd        numeric(10, 6),
    latency_ms      integer NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_llm_calls_tenant_created ON llm_calls (tenant_id, created_at DESC);
CREATE INDEX idx_llm_calls_run ON llm_calls (run_id) WHERE run_id IS NOT NULL;

-- db/schema/08_subquestions.sql
CREATE TABLE sub_questions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    idx             integer NOT NULL,
    text            text NOT NULL,
    status          text NOT NULL DEFAULT 'pending',
    answer          text,
    child_run_id    uuid REFERENCES runs(id),
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- db/schema/09_checkpoints.sql
CREATE TABLE graph_checkpoints (
    run_id          uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    checkpoint_id   text NOT NULL,
    state           jsonb NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, checkpoint_id)
);

-- db/schema/10_notifications.sql
CREATE TABLE notification_preferences (
    user_id         uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    run_succeeded   boolean NOT NULL DEFAULT true,
    run_failed      boolean NOT NULL DEFAULT true,
    saved_run_done  boolean NOT NULL DEFAULT true,
    ingest_complete boolean NOT NULL DEFAULT true,
    ingest_failed   boolean NOT NULL DEFAULT true,
    member_joined   boolean NOT NULL DEFAULT true,
    key_rotated     boolean NOT NULL DEFAULT true,
    webhook_url     text,
    webhook_active  boolean NOT NULL DEFAULT false,
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- db/schema/11_saved.sql
CREATE TABLE saved_analyses (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id         uuid NOT NULL REFERENCES users(id),
    workspace_id    uuid NOT NULL REFERENCES workspaces(id),
    name            text NOT NULL,
    query           text NOT NULL,
    mode            text NOT NULL,
    schedule        text,                            -- cron expression or null
    last_run_id     uuid REFERENCES runs(id),
    last_run_at     timestamptz,
    status          text NOT NULL DEFAULT 'active',
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- db/schema/12_audit.sql
CREATE TABLE audit_log (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL,
    actor_id        uuid NOT NULL,
    action          text NOT NULL,                   -- key.created|key.revoked|run.started|...
    resource_type   text NOT NULL,
    resource_id     uuid,
    metadata        jsonb,
    ip_address      inet,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_tenant_created ON audit_log (tenant_id, created_at DESC);
```

```sql
-- db/policies/rls_tenancy.sql
-- Applied to EVERY tenant-scoped table

ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_tenant ON workspaces
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- repeat for: files, file_descriptions, runs, run_steps, verdicts,
-- router_decisions, run_events, llm_calls, sub_questions,
-- provider_connections, saved_analyses, audit_log
```

---

## 5. The LLM Gateway — Provider-Agnostic Routing

### 5.1 Architecture

```python
# packages/adapters/llm/src/vera_llm/client.py

class LLMClient:
    """Implements LLMPort. Routes requests through the user's BYOK provider."""

    def __init__(
        self,
        key_vault: KeyVaultPort,
        provider_repo: ProviderRepositoryPort,
        http: httpx.AsyncClient,
        cost_tracker: CostTracker,
    ): ...

    async def complete(self, *, provider_connection_id, model_id, messages,
                       response_schema, temperature, max_tokens, run_id) -> LLMResponse:
        # 1. Resolve connection → get kind, base_url, api_key_ref
        conn = await self.provider_repo.get_connection(id=provider_connection_id, ...)
        api_key = await self.key_vault.retrieve(tenant_id=conn.tenant_id, ref=conn.api_key_ref)

        # 2. Build the OpenAI-compatible request (same for ALL providers)
        body = self._build_request(model_id, messages, response_schema, temperature, max_tokens)

        # 3. Add provider-specific headers
        headers = self._provider_headers(conn.kind, api_key)

        # 4. Call with retry + circuit breaker
        url = f"{conn.base_url}/chat/completions"
        raw = await self._call_with_resilience(url, headers, body)

        # 5. Parse response, extract cost, track usage
        response = self._parse_response(raw, conn.kind)
        await self.cost_tracker.record(run_id=run_id, response=response, agent=...)
        return response
```

### 5.2 Provider-specific details

```python
# packages/adapters/llm/src/vera_llm/providers.py

PROVIDER_CONFIGS = {
    ProviderKind.OPENROUTER: ProviderConfig(
        default_base_url="https://openrouter.ai/api/v1",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        extra_headers={
            "HTTP-Referer": "https://vera.app",       # OpenRouter requires this
            "X-Title": "VERA Analytics",               # shows in OpenRouter dashboard
        },
        cost_source="header",                          # x-openrouter-cost header
        models_endpoint="/models",
    ),
    ProviderKind.NVIDIA_NIM: ProviderConfig(
        default_base_url="https://integrate.api.nvidia.com/v1",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        extra_headers={},
        cost_source="compute",                         # no cost header; compute from token prices
        models_endpoint="/models",
    ),
}
```

### 5.3 Structured output handling

```python
# packages/adapters/llm/src/vera_llm/structured.py

async def complete_structured(
    self, *, messages, response_schema: type[BaseModel], **kwargs
) -> LLMResponse:
    """
    Two strategies, tried in order:
    1. Native JSON mode (if model supports it): set response_format={"type": "json_schema", ...}
    2. Prompt-constrained: append schema to the system prompt + validate + retry on parse failure
    """
    model_info = self._get_model_info(kwargs["model_id"])

    if model_info.supports_json_mode:
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": response_schema.__name__,
                "schema": response_schema.model_json_schema(),
            }
        }
        response = await self.complete(**kwargs)
        response.parsed = response_schema.model_validate_json(response.content)
    else:
        # Fallback: inject schema into prompt, parse output, retry once on failure
        schema_instruction = f"\nRespond ONLY with valid JSON matching: {json.dumps(response_schema.model_json_schema(), indent=2)}"
        kwargs["messages"][-1]["content"] += schema_instruction
        response = await self.complete(**kwargs)
        try:
            response.parsed = response_schema.model_validate_json(
                response.content.strip().removeprefix("```json").removesuffix("```").strip()
            )
        except ValidationError as e:
            # One retry with the validation error appended
            kwargs["messages"].append({"role": "assistant", "content": response.content})
            kwargs["messages"].append({"role": "user", "content": f"JSON validation failed: {e}. Fix and return valid JSON only."})
            response = await self.complete(**kwargs)
            response.parsed = response_schema.model_validate_json(response.content)

    return response
```

### 5.4 Resilience

```python
# packages/adapters/llm/src/vera_llm/resilience.py

class ResilientCaller:
    """Retry with backoff + circuit breaker per provider connection."""

    # Retry: 3 attempts, exponential backoff (1s, 2s, 4s), jitter ±500ms
    # Retry only on: 429 (rate limit), 502/503/504 (infra), timeout
    # Do NOT retry on: 400 (bad request), 401 (auth), 404 (model not found)

    # Circuit breaker: per provider_connection_id
    # Open after 5 failures in 60 seconds → reject immediately for 30 seconds → half-open
    # When open: raise ProviderUnavailableError immediately (no wasted latency)
```

### 5.5 Connection validation

```python
# packages/adapters/llm/src/vera_llm/validation.py

async def validate_connection(self, *, kind, base_url, api_key) -> ValidationResult:
    """
    Called when a user adds a new provider connection.
    1. List models → confirms auth works and base_url is correct
    2. Small completion → confirms generation works
    3. Returns available models list on success
    """
    config = PROVIDER_CONFIGS[kind]
    headers = {config.auth_header: f"{config.auth_prefix}{api_key}"}

    # Step 1: list models
    models_resp = await self.http.get(f"{base_url}{config.models_endpoint}", headers=headers, timeout=10)
    if models_resp.status_code == 401:
        return ValidationResult(valid=False, error="Invalid API key")
    models_resp.raise_for_status()
    models = self._parse_models_response(models_resp.json(), kind)

    # Step 2: test completion with the cheapest available model
    test_model = self._pick_cheapest(models)
    test_resp = await self.http.post(
        f"{base_url}/chat/completions", headers=headers, timeout=15,
        json={"model": test_model.model_id, "messages": [{"role": "user", "content": "Say ok"}], "max_tokens": 5}
    )
    test_resp.raise_for_status()

    return ValidationResult(valid=True, models=models)
```

---

## 6. Key Vault — Secure BYOK Storage

### 6.1 Supabase Vault (encryption-at-rest strategy)

> **Supabase edition:** BYOK keys live in **Supabase Vault** (`supabase_vault`
> extension: `pgsodium`-backed authenticated encryption). There is **no
> application `key_vault` table and no `VERA_VAULT_MASTER_KEY`** — Vault manages
> its own encryption key. The adapter is a thin repository over Vault's SQL
> surface, sharing the caller's `AsyncSession` so the connection insert and the
> secret write commit in one transaction.

`VaultRepository` implements `KeyVaultPort`. Every secret is named
`t:{tenant_id}:{ref}` (the `ref` already contains the connection id, e.g.
`provider:<conn_id>:api_key`), so names never collide across tenants.

```python
# packages/db/src/vera_db/repositories/vault_repository.py — sketch

class VaultRepository:
    """Implements KeyVaultPort over Supabase Vault. Parameterised SQL only."""

    async def store(self, *, tenant_id, ref, plaintext):
        name = f"t:{tenant_id}:{ref}"
        # SELECT id FROM vault.secrets WHERE name = :name
        # if found  -> SELECT vault.update_secret(:id, :secret)
        # else      -> SELECT vault.create_secret(:secret, :name, :description)

    async def retrieve(self, *, tenant_id, ref):
        # SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = :name
        # raise vera_core.errors.NotFoundError if no row

    async def delete(self, *, tenant_id, ref):
        # DELETE FROM vault.secrets WHERE name = :name
```

Manual verification: `select secret from vault.secrets where name = <ref>` is
ciphertext; `select decrypted_secret from vault.decrypted_secrets where name =
<ref>` returns the key; the raw key never appears in `provider_connections`
(only `api_key_ref`).

### 6.2 Security rules

- **Never log an API key.** Not in error messages, not in traces, not in request bodies. The `SecretStr` type in Pydantic prevents accidental serialisation. `validate_connection` logs `kind`, `base_url`, `status_code`, `model_count` only.
- **Never return a key to the frontend.** The API returns only the `api_key_ref` and a masked prefix (`or_sk_●●●●`).
- **`vault.decrypted_secrets` is server-side only** — never granted to the `authenticated` (browser) Postgres role. See `supabase/migrations/0005_grants.sql`.
- **Per-tenant secret naming** (`t:{tenant_id}:...`) ensures one tenant's refs cannot address another tenant's secrets.
- **Key rotation:** rotating a provider key calls `vault.update_secret` — the old ciphertext is not preserved.
- **Later:** swap `VaultRepository` for `AwsKmsVault` or `HashiCorpVault` behind the same `KeyVaultPort`.

---

## 7. Agent Orchestration — The DS-STAR Loop

### 7.1 Graph assembly

```python
# packages/core/src/vera_core/loop/graph.py

from langgraph.graph import StateGraph, END

def build_precise_graph() -> StateGraph:
    graph = StateGraph(RunState)

    graph.add_node("analyze", analyze_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("plan", plan_node)
    graph.add_node("code", code_node)
    graph.add_node("execute", execute_node)
    graph.add_node("debug", debug_node)
    graph.add_node("verify", verify_node)
    graph.add_node("route", route_node)
    graph.add_node("truncate", truncate_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "retrieve")
    graph.add_edge("retrieve", "plan")
    graph.add_edge("plan", "code")
    graph.add_edge("code", "execute")

    graph.add_conditional_edges("execute", execution_outcome, {
        "success": "verify",
        "crash": "debug",
        "budget_exhausted": "finalize",
    })

    graph.add_conditional_edges("debug", debug_outcome, {
        "fixed": "execute",
        "max_retries": "finalize",
    })

    graph.add_conditional_edges("verify", verification_outcome, {
        "sufficient": "finalize",
        "insufficient": "route",
        "max_rounds": "finalize",
    })

    graph.add_conditional_edges("route", routing_outcome, {
        "add_step": "plan",
        "backtrack": "truncate",
    })

    graph.add_edge("truncate", "plan")
    graph.add_edge("finalize", END)

    return graph.compile(checkpointer=PostgresCheckpointer())
```

### 7.2 Node implementations — model resolution

Every node that calls the LLM resolves the model from the user's Agent Defaults:

```python
# packages/core/src/vera_core/loop/nodes/verify.py

async def verify_node(state: RunState, *, llm: LLMPort, config: AgentDefaults) -> RunState:
    # Resolve which model to use for verifier (reasoning tier)
    assignment = config.get_assignment(AgentTier.REASONING)

    prompt = PromptRegistry.get("verifier", version="v1")
    rendered = prompt.render(
        query=state.query,
        plan=[s.text for s in state.plan if not s.superseded],
        code=state.script.source,
        observation=state.observations[-1].stdout,
    )

    response = await llm.complete(
        provider_connection_id=assignment.provider_connection_id,
        model_id=assignment.model_id,
        messages=[{"role": "system", "content": rendered}],
        response_schema=Verdict,
        temperature=0.0,
        run_id=state.run_id,
    )

    state.verdicts.append(response.parsed)
    state.cost_usd += response.cost_usd or Decimal("0")
    state.total_tokens += response.input_tokens + response.output_tokens

    await state.event_bus.emit(run_id=state.run_id, event=VerifyVerdictEvent(
        sufficient=response.parsed.sufficient,
        reason=response.parsed.reason,
        missing_aspects=response.parsed.missing_aspects,
    ))

    return state
```

### 7.3 DS-STAR+ research mode

```python
# packages/core/src/vera_core/loop/research.py

async def run_research(state: RunState, *, llm, sandbox, config) -> RunState:
    # 1. Generate sub-questions
    sub_questions = await subquestion_generator.run(state, llm=llm, config=config)

    # 2. Solve each sub-question through the core loop (bounded concurrency)
    semaphore = asyncio.Semaphore(8)
    async def solve(sq):
        async with semaphore:
            child_state = await run_precise_loop(
                query=sq.text, workspace_id=state.workspace_id, ...
            )
            return sq, child_state.answer

    results = await asyncio.gather(*[solve(sq) for sq in sub_questions], return_exceptions=True)

    # 3. Compile report with citations
    report = await report_writer.run(state, results=results, llm=llm, config=config)

    # 4. Gap detection + refinement round
    supplementary = await subquestion_generator.find_gaps(state, report=report, llm=llm, config=config)
    if supplementary:
        supp_results = await asyncio.gather(*[solve(sq) for sq in supplementary], return_exceptions=True)
        report = await report_writer.refine(state, report=report, new_results=supp_results, llm=llm, config=config)

    state.answer = report.markdown
    return state
```

---

## 8. Sandbox — Untrusted Code Execution

```python
# packages/adapters/sandbox/src/vera_sandbox/client.py

class DockerSandboxClient:
    """
    Implements SandboxPort.
    One container per execution. Destroyed after. Never reused.
    """

    IMAGE = "vera-sandbox:latest"   # fat image with polars, pandas, duckdb, etc.

    async def execute(self, *, script, mounts, limits, run_id) -> Observation:
        # 1. AST pre-scan — reject dangerous code before it runs
        violations = AstScanner.scan(script.source)
        if violations:
            return Observation(stdout="", stderr=f"Blocked: {violations}", exit_code=1, ...)

        # 2. Write script to a temp dir
        with tempfile.TemporaryDirectory() as workdir:
            script_path = Path(workdir) / "run.py"
            script_path.write_text(script.source)

            # 3. Run in Docker with strict limits
            container = await docker.containers.run(
                self.IMAGE,
                command=["python", "/workspace/run.py"],
                volumes={
                    workdir: {"bind": "/workspace", "mode": "ro"},
                    **{m.host_path: {"bind": m.container_path, "mode": "ro"} for m in mounts},
                },
                network_disabled=True,                 # zero egress
                mem_limit=f"{limits.memory_mb}m",
                cpu_period=100000, cpu_quota=limits.cpu_quota,
                pids_limit=256,
                user="nonroot",
                read_only=True,
                tmpfs={"/tmp": "size=512M,noexec"},
                detach=True,
            )

            # 4. Stream stdout/stderr with timeout
            stdout, stderr = await self._stream_with_timeout(container, limits.timeout_s)
            exit_code = (await container.wait())["StatusCode"]
            await container.remove(force=True)

            return Observation(
                stdout=stdout, stderr=stderr, exit_code=exit_code,
                duration_ms=..., artifacts=self._scan_artifacts(workdir), truncated=...
            )
```

### AST scanner deny-list

```python
# packages/adapters/sandbox/src/vera_sandbox/guards/ast_scanner.py

DENIED_MODULES = {
    "socket", "requests", "urllib", "http.client", "httpx",
    "subprocess", "os", "sys", "shutil", "ctypes", "pickle",
    "importlib", "code", "compile", "exec", "eval",
    "smtplib", "ftplib", "telnetlib", "webbrowser",
}

DENIED_ATTRIBUTES = {
    "os.system", "os.popen", "os.exec", "os.spawn",
    "__import__", "globals", "locals", "breakpoint",
}
```

---

## 9. API Surface — Complete Endpoint Specification

### 9.1 Authentication

```
All requests: Authorization: Bearer <jwt>
JWT issued by: local auth (dev) or OIDC provider (prod)
JWT claims: { sub: user_id, tenant_id, role, exp }
```

### 9.2 Endpoints

```
── Auth ──────────────────────────────────────────
POST   /v1/auth/register              register (dev only)
POST   /v1/auth/login                 login → JWT
POST   /v1/auth/refresh               refresh token

── Providers (BYOK) ─────────────────────────────
POST   /v1/providers                  add provider connection (validate + store key)
GET    /v1/providers                  list user's connections
GET    /v1/providers/{id}             get connection detail + cached models
POST   /v1/providers/{id}/refresh     re-fetch available models from provider
DELETE /v1/providers/{id}             delete connection + vault entry
POST   /v1/providers/validate         test a key without saving

── Agent Defaults ───────────────────────────────
GET    /v1/settings/agent-defaults    get user's defaults
PUT    /v1/settings/agent-defaults    update defaults + model assignments
POST   /v1/settings/agent-defaults/reset  reset to recommended

── Workspaces ───────────────────────────────────
POST   /v1/workspaces                 create workspace
GET    /v1/workspaces                 list workspaces
GET    /v1/workspaces/{id}            get workspace + file summary
DELETE /v1/workspaces/{id}            delete workspace + cascade

── Files ────────────────────────────────────────
POST   /v1/workspaces/{id}/files/upload-url    presigned upload URL
POST   /v1/workspaces/{id}/files/confirm       confirm upload (register file)
GET    /v1/workspaces/{id}/files               list files
GET    /v1/files/{id}                          get file metadata
GET    /v1/files/{id}/description              get file description detail

── Ingestion ────────────────────────────────────
POST   /v1/workspaces/{id}/ingest     trigger analyzer on pending files → 202
GET    /v1/workspaces/{id}/ingest/status  ingestion progress

── Runs ─────────────────────────────────────────
POST   /v1/runs                       create + start run → 202 {run_id}
GET    /v1/runs                       list runs (cursor paginated)
GET    /v1/runs/{id}                  full run state
GET    /v1/runs/{id}/events           SSE event stream
POST   /v1/runs/{id}/cancel           cooperative cancellation
POST   /v1/runs/{id}/fork             re-run from a specific step with modifications
GET    /v1/runs/{id}/provenance       provenance bundle

── Reports (DS-STAR+) ───────────────────────────
GET    /v1/runs/{id}/report           markdown report + citations
GET    /v1/runs/{id}/sub-questions    sub-question list + answers

── Saved Analyses ───────────────────────────────
POST   /v1/saved-analyses             pin a run as saved
GET    /v1/saved-analyses             list
PUT    /v1/saved-analyses/{id}        update name/schedule
DELETE /v1/saved-analyses/{id}        delete
POST   /v1/saved-analyses/{id}/rerun  trigger re-execution

── Settings ─────────────────────────────────────
GET    /v1/settings/profile           get profile
PUT    /v1/settings/profile           update profile
POST   /v1/settings/profile/avatar    upload avatar
GET    /v1/settings/notifications     get notification prefs
PUT    /v1/settings/notifications     update prefs
POST   /v1/settings/notifications/test-webhook   test webhook URL

── Team ─────────────────────────────────────────
GET    /v1/team/members               list members + pending invites
POST   /v1/team/invitations           send invite
DELETE /v1/team/invitations/{id}      revoke invite
PUT    /v1/team/members/{id}/role     change member role
DELETE /v1/team/members/{id}          remove member

── API Keys (VERA API Keys, not provider keys) ──
POST   /v1/api-keys                   create VERA API key
GET    /v1/api-keys                   list keys (masked)
POST   /v1/api-keys/{id}/rotate       rotate
DELETE /v1/api-keys/{id}              revoke

── Usage ────────────────────────────────────────
GET    /v1/usage                      current period summary
GET    /v1/usage/breakdown            by model / agent / workspace
GET    /v1/usage/history              historical periods
GET    /v1/usage/daily                daily cost chart data

── Health ───────────────────────────────────────
GET    /healthz                       liveness
GET    /readyz                        readiness (DB + provider connectivity)
```

### 9.3 Request/Response examples

**Create provider connection:**
```json
// POST /v1/providers
{
  "kind": "openrouter",
  "display_name": "My OpenRouter",
  "api_key": "sk-or-v1-abc123...",
  "base_url": "https://openrouter.ai/api/v1"  // optional, defaults per kind
}
// → 201
{
  "id": "prov_abc123",
  "kind": "openrouter",
  "display_name": "My OpenRouter",
  "base_url": "https://openrouter.ai/api/v1",
  "api_key_masked": "sk-or-v1-●●●●●●●●",
  "status": "connected",
  "model_count": 486,
  "created_at": "2026-08-27T10:00:00Z"
}
```

**Create run:**
```json
// POST /v1/runs
{
  "workspace_id": "ws_abc123",
  "query": "What share of Q3 chargebacks came from merchants with manual capture delay?",
  "mode": "precise",
  "budget": {
    "max_rounds": 10,
    "max_cost_usd": 2.50
  }
}
// → 202
{
  "run_id": "run_xyz789",
  "status": "queued",
  "events_url": "/v1/runs/run_xyz789/events"
}
```

### 9.4 API conventions

- Versioned prefix `/v1`; additive changes only within a version.
- All errors: RFC 9457 `application/problem+json` with `type`, `title`, `status`, `detail`, `trace_id`.
- Cursor pagination: `?cursor=<opaque>&limit=25`. Never offset.
- All timestamps: RFC 3339 UTC. All IDs: UUIDv7 (time-sortable).
- Idempotency-Key header honoured on all POSTs.
- Rate limiting: per-user, per-endpoint. `429` with `Retry-After` header.
- `X-Request-Id` header on every response for tracing.

---

## 10. SSE Event Streaming

> **Supabase edition:** in Phase 6 the durable stream is backed by **Supabase
> Realtime** (Postgres change feed on `run_events`) behind `EventBusPort`, which
> supersedes the `asyncio.sleep(0.5)` polling loop below. The SSE endpoint and
> `Last-Event-ID` reconnect contract are unchanged — Realtime replaces the poll,
> not the wire format.

```python
# apps/api/src/vera_api/routers/v1/run_events.py

@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: UUID,
    request: Request,
    last_event_id: int | None = Header(None, alias="Last-Event-ID"),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(auth),
):
    run = await run_repo.get(run_id=run_id, tenant_id=principal.tenant_id)
    if not run:
        raise NotFoundError("Run not found")

    async def event_generator():
        seq = last_event_id or 0
        while True:
            # Read new events from run_events table
            events = await event_repo.read_from(run_id=run_id, after_seq=seq)
            for event in events:
                yield {
                    "event": event.type,
                    "id": str(event.seq),
                    "data": event.payload.model_dump_json(),
                    "retry": 3000,
                }
                seq = event.seq

                # Stream ends when run is terminal
                if event.type in ("run.finished", "run.failed"):
                    return

            # Poll interval — replaced by LISTEN/NOTIFY in production
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())
```

---

## 11. Background Jobs

```python
# apps/api/src/vera_api/services/run_service.py

class RunService:
    async def create_run(self, *, request: CreateRunRequest, principal: Principal) -> RunResponse:
        # 1. Validate: user has at least one connected provider
        connections = await provider_repo.list_connections(user_id=principal.user_id)
        if not connections:
            raise NeedsProviderError("Connect a model provider before starting a run")

        # 2. Validate: agent defaults have model assignments
        defaults = await defaults_repo.get(user_id=principal.user_id)
        if not defaults or not defaults.has_all_tiers():
            raise NeedsConfigError("Configure model assignments in Agent Defaults")

        # 3. Create run record
        run = RunState(
            run_id=uuid7(), tenant_id=principal.tenant_id, user_id=principal.user_id,
            workspace_id=request.workspace_id, query=request.query, mode=request.mode,
            budget=request.budget or defaults.to_budget(), status=RunStatus.QUEUED, ...
        )
        await run_repo.create(run=run)

        # 4. Dispatch to orchestrator (in-process for now; Temporal later)
        asyncio.create_task(self.orchestrator.execute(run))

        # 5. Audit log
        await audit.log(action="run.started", resource_type="run", resource_id=run.run_id, ...)

        return RunResponse(run_id=run.run_id, status="queued", events_url=f"/v1/runs/{run.run_id}/events")
```

---

## 12. Authentication & Authorization

> **Supabase edition:** in Phase 6, **Supabase Auth** issues and verifies the
> JWT; the API validates it against Supabase's JWKS (pinned alg, `exp`/`aud`/`iss`
> enforced) and builds `Principal` field-by-field. The `tenant_id` travels as a
> JWT claim read by `public.current_tenant_id()`, so the `SET LOCAL app.tenant_id`
> GUC approach below becomes a fallback for the service-role path only. The
> hand-rolled `jwt.decode(..., settings.jwt_secret, ["HS256"])` and the
> f-string `SET LOCAL` are replaced.

```python
# apps/api/src/vera_api/dependencies/auth.py

class Principal(BaseModel):
    user_id: UserId
    tenant_id: TenantId
    role: Role   # owner | admin | analyst | viewer
    email: str

async def auth(authorization: str = Header(...)) -> Principal:
    token = authorization.removeprefix("Bearer ").strip()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    return Principal(**payload)

async def require_role(*allowed: Role):
    def checker(principal: Principal = Depends(auth)):
        if principal.role not in allowed:
            raise ForbiddenError(f"Requires role: {', '.join(allowed)}")
        return principal
    return checker
```

```python
# apps/api/src/vera_api/dependencies/tenancy.py

async def set_tenant(db: AsyncSession, principal: Principal):
    """Set RLS context for every request."""
    await db.execute(text(f"SET LOCAL app.tenant_id = '{principal.tenant_id}'"))
```

### RBAC matrix

| Endpoint | Owner | Admin | Analyst | Viewer |
| --- | --- | --- | --- | --- |
| Create/delete workspace | ✓ | ✓ | ✓ | ✗ |
| Upload files | ✓ | ✓ | ✓ | ✗ |
| Start runs | ✓ | ✓ | ✓ | ✗ |
| View runs | ✓ | ✓ | ✓ | ✓ |
| Manage providers | ✓ | ✓ | ✓ | ✗ |
| Manage team | ✓ | ✓ | ✗ | ✗ |
| Delete team member | ✓ | ✗ | ✗ | ✗ |
| Manage VERA API keys | ✓ | ✓ | ✓ | ✗ |
| View usage | ✓ | ✓ | ✓ | ✓ |
| Delete account | ✓ | ✗ | ✗ | ✗ |

---

## 13. Error Taxonomy

```python
# packages/core/src/vera_core/errors.py

class VeraError(Exception):
    status: int = 500
    type_uri: str = "urn:vera:error:internal"

class NotFoundError(VeraError):          status = 404
class ForbiddenError(VeraError):         status = 403
class ValidationError(VeraError):        status = 422

# Provider errors
class NeedsProviderError(VeraError):     status = 422; type_uri = "urn:vera:error:needs-provider"
class NeedsConfigError(VeraError):       status = 422; type_uri = "urn:vera:error:needs-config"
class ProviderAuthError(VeraError):      status = 502; type_uri = "urn:vera:error:provider-auth"
class ProviderUnavailableError(VeraError): status = 503; type_uri = "urn:vera:error:provider-unavailable"
class ProviderRateLimitError(VeraError): status = 429; type_uri = "urn:vera:error:provider-rate-limit"

# Run errors
class BudgetExhaustedError(VeraError):   status = 200; type_uri = "urn:vera:error:budget-exhausted"
class SandboxTimeoutError(VeraError):    status = 500; type_uri = "urn:vera:error:sandbox-timeout"
class AgentOutputError(VeraError):       status = 500; type_uri = "urn:vera:error:agent-output"
```

```python
# apps/api/src/vera_api/middleware/error_handler.py

@app.exception_handler(VeraError)
async def vera_error_handler(request: Request, exc: VeraError):
    return JSONResponse(
        status_code=exc.status,
        content={
            "type": exc.type_uri,
            "title": exc.__class__.__name__,
            "status": exc.status,
            "detail": str(exc),
            "trace_id": request.state.trace_id,
        },
        media_type="application/problem+json",
    )
```

---

## 14. Observability

```python
# packages/observability/src/vera_obs/tracing.py

# One trace per run. Span tree:
# run
#   ├── round.0
#   │   ├── plan   {agent=planner, model=anthropic/claude-sonnet-5, tokens=1200, cost=$0.012}
#   │   ├── code   {agent=coder, ...}
#   │   ├── execute {duration_ms=340, exit_code=0}
#   │   └── verify {sufficient=false, missing=["fee deduction"]}
#   ├── round.1
#   │   ├── route  {action=backtrack, index=2}
#   │   ├── plan   ...
#   │   └── ...
```

Key metrics:
```python
METRICS = {
    "vera_run_total":                Counter,   # by status, mode
    "vera_run_duration_seconds":     Histogram, # by mode
    "vera_rounds_to_sufficient":     Histogram, # the DS-STAR diagnostic
    "vera_backtrack_count":          Counter,   # rising = planner degradation
    "vera_llm_call_duration_seconds": Histogram, # by provider, model, agent
    "vera_llm_call_tokens":          Counter,   # by provider, model, direction
    "vera_llm_call_cost_usd":        Counter,   # by provider, model, agent
    "vera_sandbox_duration_seconds":  Histogram,
    "vera_provider_errors":          Counter,   # by provider, error_type
    "vera_provider_circuit_open":    Gauge,     # by provider_connection_id
}
```

---

## 15. Testing Strategy

| Layer | What | How | Depends on |
| --- | --- | --- | --- |
| **Unit** | Agent logic, policies, truncation, backtrack, budget | pytest + hypothesis, `FakeLLM`, `FakeSandbox`, `FakeVault` | Nothing |
| **Unit** | LLM gateway routing, structured output parsing, retry logic | pytest + httpx mock | Nothing |
| **Integration** | Repositories + RLS | Real Neon branch | Neon |
| **Integration** | Provider validation + model listing | Recorded HTTP cassettes | httpx mock |
| **Contract** | API against OpenAPI spec | schemathesis | Nothing |
| **E2E** | Provider connect → create run → answer | FakeLLM + FakeSandbox + real DB | Neon |
| **Eval** | Answer quality on golden set | vera-evals harness | Real LLM (nightly) |

**The BYOK-specific test:** a unit test that validates the LLM gateway produces identical request shapes for OpenRouter and NVIDIA NIM for the same logical request. If the shapes diverge, the gateway abstraction is leaking.

---

## 16. Backend File Structure

```
packages/
├── core/src/vera_core/
│   ├── models/{ids,provider,agent_config,workspace,run,report,events,tenancy}.py
│   ├── agents/{base,analyzer,planner,coder,verifier,router,debugger,finalizer,...}.py
│   ├── loop/{graph,edges,research,nodes/*.py}
│   ├── prompts/{registry,templates/**/*.jinja}
│   ├── policies/{truncation,context_budget,backtrack,termination,cycle_detection,budget}.py
│   ├── ports/{llm,key_vault,sandbox,object_store,event_bus,retriever,repository,clock}.py
│   ├── config/{model_routing.yaml,budgets.yaml,loader.py}
│   └── errors.py
│
├── adapters/
│   ├── llm/src/vera_llm/{client,providers,structured,resilience,validation,cost,fakes}.py
│   ├── keyvault/src/vera_keyvault/{fernet_vault,fake}.py
│   ├── sandbox/src/vera_sandbox/{client,backends/,guards/,mounts,capture,image/}
│   ├── db/src/vera_db/{engine,session,models/,repositories/,checkpointer,migrations/,types/}
│   ├── storage/src/vera_storage/{local_fs,fake}.py
│   ├── events/src/vera_events/{postgres_bus,memory_bus}.py
│   └── retrieval/src/vera_retrieval/{embedder,indexer,hybrid_search,selector}.py
│
├── evals/src/vera_evals/{harness,scorers/,datasets/,baselines/,report}.py
├── observability/src/vera_obs/{logging,tracing,metrics,redaction}.py
└── testing/src/vera_testing/{factories/,fixtures/,assertions}.py

apps/
├── api/src/vera_api/{main,settings,container,dependencies/,middleware/,routers/v1/,schemas/,services/}
├── cli/src/vera_cli/{main,commands/}
└── web/  (frontend)

db/schema/{00..13}_*.sql
db/policies/{rls_tenancy,roles}.sql
db/functions/{uuid_v7,current_tenant}.sql
```

---

## 17. Configuration & Environment

```bash
# .env.example  (Supabase edition — see docs/adr/0002-supabase-platform.md)

# ── Supabase ──
SUPABASE_URL=https://YOUR-PROJECT-REF.supabase.co
SUPABASE_ANON_KEY=replace-me
SUPABASE_SERVICE_ROLE_KEY=replace-me            # server-side only; bypasses RLS

# Postgres — transaction pooler (Supavisor :6543), used by the API at runtime
VERA_DATABASE_URL=postgresql+asyncpg://postgres.YOUR-REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
# Postgres — session mode (:5432), used by migrations, LISTEN/NOTIFY, and tests
VERA_DATABASE_URL_DIRECT=postgresql+asyncpg://postgres.YOUR-REF:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres

# ── Security ──
VERA_JWT_SECRET=change-me-in-production   # unused until Phase 6 (Supabase Auth JWKS)

# ── Backends (swappable via config) ──
VERA_SANDBOX_BACKEND=local_docker        # local_docker | fake
VERA_STORAGE_BACKEND=local_fs            # local_fs | fake
VERA_EVENT_BUS_BACKEND=postgres          # postgres | memory
VERA_KEYVAULT_BACKEND=supabase_vault     # supabase_vault | fake

# ── Observability ──
VERA_LOG_LEVEL=info
VERA_OTEL_EXPORTER=console               # console | otlp
VERA_LANGFUSE_PUBLIC_KEY=
VERA_LANGFUSE_SECRET_KEY=
```

Removed: `VERA_VAULT_MASTER_KEY` (Supabase Vault manages its own encryption key).

---

## 18. Build Order

| # | Slice | Ships | Proves |
| --- | --- | --- | --- |
| 1 | **Domain + ports + fakes** | all models, all ports, FakeLLM, FakeSandbox, FakeVault, .importlinter | The type system holds |
| 2 | **Key vault + provider CRUD** | Fernet vault, provider connection endpoints, validation flow | A user can connect OpenRouter and see available models |
| 3 | **Agent defaults + model assignments** | Defaults endpoints, tier→model resolution | A user can configure which model runs each agent |
| 4 | **Loop with fakes** | LangGraph graph, all nodes, FakeLLM with scripted responses | The state machine backtracks correctly |
| 5 | **LLM gateway** | Real OpenRouter + NVIDIA NIM client, structured output, retry, circuit breaker | A real model call succeeds through the gateway |
| 6 | **Sandbox** | Docker backend, AST scanner, stdout capture | Model-generated code executes safely |
| 7 | **Real agents, one format** | All nine prompts, CSV + JSON fixtures | The loop beats single-shot on fixtures |
| 8 | **Persistence** | DB schema, migrations, RLS, repositories, checkpointer, SSE events | Runs survive restart; tenants are isolated |
| 9 | **Full API** | All endpoints, auth, RBAC, error handling, pagination | Frontend can integrate |
| 10 | **Heterogeneous files** | XLSX, MD, PDF, SQLite, ZIP support; retriever + pgvector | Hard multi-file tasks work |
| 11 | **DS-STAR+** | Sub-question generator, fan-out, report writer | Research mode works |
| 12 | **Usage, team, notifications** | Usage breakdown, team CRUD, webhook dispatch | Settings pages have backends |

**Gate between slices 4 and 5:** the loop must work perfectly with fakes before touching a real provider. Debug the state machine and the prompts separately — doing both at once is how these projects stall.

**Gate between slices 7 and 8:** the loop with real prompts must beat a single-shot prompt on your fixtures. If it doesn't, no amount of database schema will save it.

---

### Closing note

The BYOK architecture means VERA has no model-inference cost, no provider contract, and no margin on token usage. The user's OpenRouter or NVIDIA account gets billed directly. VERA's value is the orchestration — the nine-agent loop, the verification, the backtracking, the provenance — not model access.

That also means the LLM gateway must never be the bottleneck or the failure point. It's a thin pass-through with retry and circuit breaking, not a translation layer. Both providers speak OpenAI-compatible `/v1/chat/completions`, so the same request body works everywhere. The only provider-specific code is three lines of header configuration and the cost-extraction method. Keep it that way.
