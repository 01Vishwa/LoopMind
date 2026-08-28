# Phase 1 — Foundation Repair + Domain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `make lint && make test` run green on a pruned repository whose
`vera_core` domain layer and `vera_testing` fakes are complete, committed, and
verified against their port protocols.

**Architecture:** Everything in this phase is pure Python with no I/O. `vera_core`
holds domain models (Pydantic v2, frozen), port protocols (`typing.Protocol`,
keyword-only, `@runtime_checkable`), pure policy functions, and the error
taxonomy. `vera_testing` holds in-memory fakes that satisfy those protocols, so
every later phase can be tested without a network, a database, or Docker. No
adapter in this phase imports anything but `vera_core`.

**Tech Stack:** Python 3.13, Pydantic v2, pytest, ruff, mypy (strict),
import-linter, uv workspace.

**Spec:** `docs/VERA_BACKEND_PLAN.md` (§3 Domain Model, §13 Error Taxonomy,
§16 File Structure, §18 slice 1)

**Roadmap:** `docs/superpowers/plans/2026-08-27-vera-backend-roadmap.md`

## Global Constraints

- Python `>=3.13` in every `pyproject.toml`; `ruff target-version = "py313"`.
- Line length 100. Ruff lint set exactly `["E", "F", "I", "N", "UP", "B", "SIM"]`,
  ignore `["E501"]`.
- mypy runs `strict = True` with the pydantic plugin.
- Every module: one-line docstring first, then `from __future__ import annotations`,
  and `__all__` at the bottom.
- Pydantic models set `model_config = {"frozen": True}` unless mutation is
  required. `RunState` is the only deliberate mutable model.
- Ports are `typing.Protocol`, `@runtime_checkable`, all parameters keyword-only.
- Domain IDs come from `vera_core.models.ids` — never a bare `UUID` in a signature.
- Errors subclass `VeraError` and set `status: int` and `type_uri: str`.
- Timestamps use `datetime.now(UTC)`. `datetime.utcnow()` is banned (deprecated in
  3.12+ and returns a naive datetime).
- `vera_core` imports nothing from `vera_llm`, `vera_api`, `vera_db`, or any other
  adapter. Enforced by import-linter, not by convention.

## Starting State

`packages/core` and `packages/testing` already contain most of the target code,
but almost all of it is **untracked** — see `git status`. This phase finishes,
verifies, and commits it. Do not rewrite what already works; the audit below is
what is actually missing.

**Broken, blocking everything:**
- `.importlinter` line 1 reads `importlinter]` — the `[` is missing, so
  `lint-imports` dies with "File contains no section headers".
- `mypy.ini` line 1 reads `mypy]` — same defect, `mypy` dies the same way.
- `ruff check packages/ apps/` reports 14 errors (all in `packages/core/tests/`).
- `mypy` reports `Library stubs not installed for "yaml"`.
- `.env.example` is empty.

**Missing:**
- Every `__init__.py` in `vera_core` and `vera_testing` is a bare docstring with
  no re-exports.
- `packages/testing/src/vera_testing/assertions.py` is 0 bytes.
- No test proves the fakes actually satisfy the port protocols.
- `packages/db` is not a uv workspace member and its `pyproject.toml` is empty.

**To delete (roadmap decisions D1, D2):** `apps/orchestrator/`, `apps/worker/`,
`db/schema/`, `db/policies/`, `db/functions/`, `db/queries/`, `config/`,
`tools/` (all of `codegen/`, `scripts/`, `vera-cli/` — every file is 0 bytes).

---

## File Structure

| File | Responsibility |
| --- | --- |
| `.importlinter` | Layer contracts. Repaired header; two new contracts. |
| `mypy.ini` | Strict typing config. Repaired header. |
| `.env.example` | Every environment variable the backend reads, with safe placeholders. |
| `pyproject.toml` | uv workspace members (adds `packages/db`), dev dependencies (adds `types-PyYAML`). |
| `packages/db/pyproject.toml` | Package metadata so `packages/db` resolves. Created empty-of-code. |
| `packages/core/src/vera_core/__init__.py` | Package version marker only. Deliberately exports nothing — submodule imports stay explicit. |
| `packages/core/src/vera_core/models/__init__.py` | Re-exports every domain model, so callers write `from vera_core.models import RunState`. |
| `packages/core/src/vera_core/ports/__init__.py` | Re-exports every port protocol. |
| `packages/core/src/vera_core/policies/__init__.py` | Re-exports every policy function and class. |
| `packages/testing/src/vera_testing/fakes/__init__.py` | Re-exports every fake. |
| `packages/testing/src/vera_testing/factories/__init__.py` | Re-exports the domain factories. |
| `packages/testing/src/vera_testing/assertions.py` | Shared custom assertions used across phases. |
| `packages/core/tests/test_models.py` | Existing. Ruff violations fixed; blind `Exception` assertions narrowed. |
| `packages/core/tests/test_policies.py` | Existing. Ruff violations fixed. |
| `packages/core/tests/conftest.py` | Existing. Unused import removed. |
| `packages/testing/tests/test_fakes_conform.py` | New. Proves each fake satisfies its port protocol. |
| `packages/testing/tests/test_assertions.py` | New. Tests the custom assertions. |

---

## Task 1: Repair the toolchain

Nothing else in this plan can be verified until `make lint` runs. This task is
first and stands alone.

**Files:**
- Modify: `.importlinter:1`
- Modify: `mypy.ini:1`
- Modify: `pyproject.toml` (dev-dependencies, workspace members)
- Create: `packages/db/pyproject.toml`
- Create: `.env.example`

**Interfaces:**
- Consumes: nothing.
- Produces: a working `make lint`. Later tasks depend on `uv run lint-imports`,
  `uv run mypy packages/core/src`, and `uv run ruff check` all executing.

- [ ] **Step 1: Confirm both configs are broken**

```bash
uv run lint-imports; uv run mypy packages/core/src
```

Expected: `lint-imports` prints `File contains no section headers. file: '<string>', line: 1 'importlinter]\n'`. `mypy` prints the same for `mypy.ini`. This confirms the defect before fixing it.

- [ ] **Step 2: Repair `.importlinter`**

Change line 1 from `importlinter]` to `[importlinter]`. The rest of the file is correct and stays as-is.

- [ ] **Step 3: Repair `mypy.ini`**

Change line 1 from `mypy]` to `[mypy]`. Then change `python_version = 3.13` — already correct — and leave the three `ignore_missing_imports` sections alone.

- [ ] **Step 4: Add the missing type stubs and workspace member**

In `pyproject.toml`, add `"packages/db"` to `[tool.uv.workspace].members` (after `"packages/core"`), and add `"types-PyYAML>=6.0"` to `[tool.uv] dev-dependencies`.

- [ ] **Step 5: Create `packages/db/pyproject.toml`**

The package holds no code yet — Phase 2 fills it — but it must resolve for the workspace to sync.

```toml
[project]
name = "vera-db"
version = "0.1.0"
description = "VERA persistence adapter — SQLAlchemy models, repositories, migrations"
requires-python = ">=3.13"
dependencies = [
    "vera-core",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "pgvector>=0.3",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/vera_db"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "integration: tests that require a real database",
    "e2e: end-to-end tests",
]

[tool.uv.sources]
vera-core = { workspace = true }
```

Also create `packages/db/src/vera_db/__init__.py` containing exactly:

```python
"""vera_db — VERA persistence adapter."""
```

- [ ] **Step 6: Write `.env.example`**

Every variable the backend will read, with placeholder values that are obviously
placeholders. No real secret ever lands here.

```bash
# ── Database ──────────────────────────────────────────────────────────────────
# Pooled connection — used by the API for normal request traffic.
VERA_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/vera
# Direct (unpooled) connection — used by Alembic migrations and LISTEN/NOTIFY.
VERA_DATABASE_URL_DIRECT=postgresql+asyncpg://user:password@localhost:5432/vera

# ── Security ──────────────────────────────────────────────────────────────────
# HS256 signing secret for VERA-issued JWTs. Generate: openssl rand -hex 32
VERA_JWT_SECRET=replace-me-with-32-bytes-of-hex
VERA_JWT_ACCESS_TTL_S=900
VERA_JWT_REFRESH_TTL_S=1209600
# Fernet master key for the BYOK vault. Generate:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
VERA_VAULT_MASTER_KEY=replace-me-with-a-fernet-key

# ── Swappable backends ────────────────────────────────────────────────────────
VERA_SANDBOX_BACKEND=subprocess          # subprocess | docker | fake
VERA_STORAGE_BACKEND=local_fs            # local_fs | fake
VERA_STORAGE_ROOT=.vera/objects
VERA_EVENT_BUS_BACKEND=postgres          # postgres | memory
VERA_KEYVAULT_BACKEND=fernet             # fernet | fake

# ── Limits ────────────────────────────────────────────────────────────────────
VERA_MAX_UPLOAD_BYTES=104857600
VERA_SANDBOX_TIMEOUT_S=120
VERA_SANDBOX_MEMORY_MB=2048

# ── Observability ─────────────────────────────────────────────────────────────
VERA_LOG_LEVEL=info
VERA_LOG_FORMAT=json                     # json | console
VERA_OTEL_EXPORTER=console               # console | otlp | none
VERA_OTEL_ENDPOINT=
```

- [ ] **Step 7: Sync and verify the toolchain runs**

```bash
uv sync --all-packages
uv run lint-imports
uv run mypy packages/core/src
```

Expected: `lint-imports` prints contract results (both contracts KEPT — `vera_llm` and `vera_api` have no code yet, so nothing can violate them). `mypy` prints `Success: no issues found` or real type errors — but no longer a config parse error.

- [ ] **Step 8: Commit**

```bash
git add .importlinter mypy.ini pyproject.toml .env.example packages/db/pyproject.toml packages/db/src/vera_db/__init__.py uv.lock
git commit -m "fix: repair import-linter and mypy configs, add vera-db workspace member and .env.example"
```

---

## Task 2: Prune the scaffolding the architecture does not use

Roadmap decisions D1 and D2. Deleting 0-byte trees now means every later grep,
import search, and file listing shows only real code.

**Files:**
- Delete: `apps/orchestrator/`, `apps/worker/`, `db/schema/`, `db/policies/`,
  `db/functions/`, `db/queries/`, `config/`, `tools/codegen/`, `tools/vera-cli/`
- Modify: `Makefile`
- Modify: `.importlinter`

**Interfaces:**
- Consumes: Task 1's repaired `.importlinter`.
- Produces: a repository where every tracked `.py` file outside `apps/web` is
  either real code or an intentional package marker.

- [ ] **Step 1: Prove the deletions are all empty**

```bash
find apps/orchestrator apps/worker db/schema db/policies db/functions db/queries config tools -type f ! -name '.gitkeep' -size +0c
```

Expected: no output. If any file has content, stop and report it — the roadmap
assumed these are empty and that assumption must hold before deleting.

- [ ] **Step 2: Delete the trees**

```bash
git rm -r --quiet apps/orchestrator apps/worker db/schema db/policies db/functions db/queries config tools
```

- [ ] **Step 3: Update the Makefile**

The `sandbox-build` target's path is correct. Replace the `lint` target so it
covers the packages that will exist, and add an `env-check` convenience target:

```makefile
lint:
	uv run ruff check packages/ apps/
	uv run ruff format --check packages/ apps/
	uv run mypy packages/core/src packages/testing/src
	uv run lint-imports
```

Note that `packages/llm/src` and `apps/api/src` are removed from the mypy line
for now — they contain 0-byte files, and mypy on an empty tree is noise. They are
added back by the phase that fills them.

- [ ] **Step 4: Add the layering contracts**

Append to `.importlinter`, and extend `root_packages` to include `vera_db` and `vera_testing`:

```ini
[importlinter:contract:core-is-independent]
name = vera_core must not import adapters or API
type = forbidden
source_modules =
    vera_core
forbidden_modules =
    vera_llm
    vera_api
    vera_db
    vera_testing

[importlinter:contract:testing-depends-only-on-core]
name = vera_testing must not import adapters or API
type = forbidden
source_modules =
    vera_testing
forbidden_modules =
    vera_llm
    vera_api
    vera_db
```

(The first contract replaces the existing `core-is-independent` block — do not
leave two contracts with the same name.)

- [ ] **Step 5: Verify**

```bash
uv run lint-imports && uv run pytest packages/ -q
```

Expected: contracts KEPT, 40 tests pass.

- [ ] **Step 6: Commit**

```bash
git add -A Makefile .importlinter apps db tools config
git commit -m "chore: remove unused scaffolding, tighten layering contracts

Orchestration lives in packages/core/loop and runs in-process (roadmap D1).
Alembic is the single source of truth for schema (roadmap D2)."
```

---

## Task 3: Fix the ruff violations in the existing tests

14 errors, all in `packages/core/tests/`. Ten are mechanical; four are real test
weaknesses worth fixing by hand.

**Files:**
- Modify: `packages/core/tests/conftest.py:5`
- Modify: `packages/core/tests/test_models.py` (imports, lines 68, 72, 88, 142, 144, 149)
- Modify: `packages/core/tests/test_policies.py` (imports, lines 70, 161)

**Interfaces:**
- Consumes: Task 1's working ruff.
- Produces: a green `uv run ruff check packages/ apps/`.

- [ ] **Step 1: Apply the mechanical fixes**

```bash
uv run ruff check packages/ apps/ --fix
uv run ruff format packages/ apps/
```

This resolves the ten `[*]` violations: unused imports (`pytest` in `conftest.py`,
`CodeArtifact`/`Role`/`User` in `test_models.py`), unsorted import blocks, and
`UP017` (`datetime.timezone.utc` → `datetime.UTC`).

- [ ] **Step 2: Narrow the four blind exception assertions**

`B017` at `test_models.py:68`, `:72`, `:144`, `:149` asserts `pytest.raises(Exception)`,
which passes if the code raises for *any* reason — including a typo in the test.
Two are Pydantic field-constraint violations and two are frozen-model mutations.
Import `ValidationError` from `pydantic` at the top of the file, then:

```python
    def test_temperature_bounds(self):
        with pytest.raises(ValidationError, match="less_than_equal"):
            ModelAssignment(
                tier=AgentTier.REASONING,
                provider_connection_id=pcid(),
                model_id="m",
                temperature=3.0,
            )

    def test_max_tokens_minimum(self):
        with pytest.raises(ValidationError, match="greater_than_equal"):
            ModelAssignment(
                tier=AgentTier.REASONING,
                provider_connection_id=pcid(),
                model_id="m",
                max_tokens=0,
            )
```

And for the two frozen-model tests — Pydantic v2 raises `ValidationError` with
`frozen_instance` as the error type on assignment to a frozen model:

```python
        with pytest.raises(ValidationError, match="frozen"):
            conn.display_name = "Modified"  # type: ignore[misc]
```

```python
    def test_model_info_frozen(self):
        info = ModelInfo(model_id="a/b", display_name="A B", context_window=4096)
        with pytest.raises(ValidationError, match="frozen"):
            info.model_id = "c/d"  # type: ignore[misc]
```

- [ ] **Step 3: Run the tests and ruff together**

```bash
uv run pytest packages/core -q && uv run ruff check packages/ apps/
```

Expected: `40 passed`, then `All checks passed!`. If a `match=` string does not
line up with the Pydantic error message, read the actual failure and correct the
pattern — do not widen it back to bare `Exception`.

- [ ] **Step 4: Commit**

```bash
git add packages/core/tests
git commit -m "test: fix ruff violations and narrow blind exception assertions in core tests"
```

---

## Task 4: Complete the package exports

Every `__init__.py` in `vera_core` and `vera_testing` is a bare docstring, so
callers must reach into submodules for everything. Re-exports give a stable
public surface that later phases import against.

**Files:**
- Modify: `packages/core/src/vera_core/__init__.py`
- Modify: `packages/core/src/vera_core/models/__init__.py`
- Modify: `packages/core/src/vera_core/ports/__init__.py`
- Modify: `packages/core/src/vera_core/policies/__init__.py`
- Modify: `packages/testing/src/vera_testing/fakes/__init__.py`
- Modify: `packages/testing/src/vera_testing/factories/__init__.py`
- Test: `packages/core/tests/test_exports.py` (create)

**Interfaces:**
- Consumes: the existing modules and their `__all__` lists.
- Produces: `from vera_core.models import RunState, ProviderConnection, AgentDefaults, ...`,
  `from vera_core.ports import LLMPort, KeyVaultPort, SandboxPort, ObjectStorePort, EventBusPort, RetrieverPort, ClockPort, SystemClock, FixedClock, RunRepositoryPort, ProviderRepositoryPort, AgentDefaultsRepositoryPort, WorkspaceRepositoryPort, FileRepositoryPort, Page`,
  `from vera_core.policies import check_budget, should_terminate, is_terminal_status, plan_fingerprint, CycleDetector, ...`,
  `from vera_testing.fakes import FakeLLM, FakeSandbox, FakeKeyVault, FakeObjectStore, FakeEventBus`.

- [ ] **Step 1: Write the failing test**

Create `packages/core/tests/test_exports.py`:

```python
"""Every public name is importable from its package root."""

from __future__ import annotations

import vera_core.models as models
import vera_core.policies as policies
import vera_core.ports as ports


def test_models_reexports_every_domain_type():
    expected = {
        "TenantId", "UserId", "WorkspaceId", "FileId", "RunId", "ProviderConnectionId",
        "Tenant", "TenantPlan", "User", "Role",
        "ProviderKind", "ConnectionStatus", "ModelInfo", "ProviderConnection",
        "ValidationResult",
        "AgentTier", "ModelAssignment", "AgentDefaults",
        "FileKind", "SchemaField", "FileRef", "FileDescription",
        "RunMode", "RunStatus", "PlanStep", "CodeArtifact", "ArtifactRef",
        "Observation", "Verdict", "RouterAction", "RouterDecision", "RunBudget",
        "RunState",
        "RunEvent",
    }
    missing = expected - set(models.__all__)
    assert not missing, f"vera_core.models does not re-export: {sorted(missing)}"
    for name in expected:
        assert getattr(models, name) is not None


def test_ports_reexports_every_protocol():
    expected = {
        "LLMPort", "LLMResponse",
        "KeyVaultPort",
        "SandboxPort", "DataMount", "ResourceLimits",
        "ObjectStorePort", "PresignedUpload",
        "EventBusPort",
        "RetrieverPort",
        "ClockPort", "SystemClock", "FixedClock",
        "Page",
        "RunRepositoryPort", "ProviderRepositoryPort", "AgentDefaultsRepositoryPort",
        "WorkspaceRepositoryPort", "FileRepositoryPort",
    }
    missing = expected - set(ports.__all__)
    assert not missing, f"vera_core.ports does not re-export: {sorted(missing)}"
    for name in expected:
        assert getattr(ports, name) is not None


def test_policies_reexports_every_policy():
    expected = {
        "check_budget", "should_terminate", "is_terminal_status",
        "plan_fingerprint", "CycleDetector",
        "apply_backtrack", "active_steps",
        "truncate_observation", "DEFAULT_STDOUT_CAP", "DEFAULT_STDERR_CAP",
        "ContextBudget",
    }
    missing = expected - set(policies.__all__)
    assert not missing, f"vera_core.policies does not re-export: {sorted(missing)}"
    for name in expected:
        assert getattr(policies, name) is not None
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
uv run pytest packages/core/tests/test_exports.py -v
```

Expected: three failures, each an `AssertionError` naming every symbol that is
missing, because the `__init__.py` files define no `__all__`.

- [ ] **Step 3: Write `models/__init__.py`**

```python
"""vera_core domain models — the shared vocabulary of the system."""

from __future__ import annotations

from vera_core.models.agent_config import AgentDefaults, AgentTier, ModelAssignment
from vera_core.models.events import RunEvent
from vera_core.models.file import FileDescription, FileKind, FileRef, SchemaField
from vera_core.models.ids import (
    FileId,
    ProviderConnectionId,
    RunId,
    TenantId,
    UserId,
    WorkspaceId,
)
from vera_core.models.provider import (
    ConnectionStatus,
    ModelInfo,
    ProviderConnection,
    ProviderKind,
    ValidationResult,
)
from vera_core.models.run import (
    ArtifactRef,
    CodeArtifact,
    Observation,
    PlanStep,
    RouterAction,
    RouterDecision,
    RunBudget,
    RunMode,
    RunState,
    RunStatus,
    Verdict,
)
from vera_core.models.tenancy import Role, Tenant, TenantPlan, User

__all__ = [
    "AgentDefaults",
    "AgentTier",
    "ArtifactRef",
    "CodeArtifact",
    "ConnectionStatus",
    "FileDescription",
    "FileId",
    "FileKind",
    "FileRef",
    "ModelAssignment",
    "ModelInfo",
    "Observation",
    "PlanStep",
    "ProviderConnection",
    "ProviderConnectionId",
    "ProviderKind",
    "Role",
    "RouterAction",
    "RouterDecision",
    "RunBudget",
    "RunEvent",
    "RunId",
    "RunMode",
    "RunState",
    "RunStatus",
    "SchemaField",
    "Tenant",
    "TenantId",
    "TenantPlan",
    "User",
    "UserId",
    "ValidationResult",
    "Verdict",
    "WorkspaceId",
]
```

- [ ] **Step 4: Write `ports/__init__.py`**

```python
"""vera_core ports — the protocols every adapter implements."""

from __future__ import annotations

from vera_core.ports.clock import ClockPort, FixedClock, SystemClock
from vera_core.ports.event_bus import EventBusPort
from vera_core.ports.key_vault import KeyVaultPort
from vera_core.ports.llm import LLMPort, LLMResponse
from vera_core.ports.object_store import ObjectStorePort, PresignedUpload
from vera_core.ports.repository import (
    AgentDefaultsRepositoryPort,
    FileRepositoryPort,
    Page,
    ProviderRepositoryPort,
    RunRepositoryPort,
    WorkspaceRepositoryPort,
)
from vera_core.ports.retriever import RetrieverPort
from vera_core.ports.sandbox import DataMount, ResourceLimits, SandboxPort

__all__ = [
    "AgentDefaultsRepositoryPort",
    "ClockPort",
    "DataMount",
    "EventBusPort",
    "FileRepositoryPort",
    "FixedClock",
    "KeyVaultPort",
    "LLMPort",
    "LLMResponse",
    "ObjectStorePort",
    "Page",
    "PresignedUpload",
    "ProviderRepositoryPort",
    "ResourceLimits",
    "RetrieverPort",
    "RunRepositoryPort",
    "SandboxPort",
    "SystemClock",
    "WorkspaceRepositoryPort",
]
```

- [ ] **Step 5: Write `policies/__init__.py`**

```python
"""vera_core policies — pure decision functions with no I/O."""

from __future__ import annotations

from vera_core.policies.backtrack import active_steps, apply_backtrack
from vera_core.policies.context_budget import ContextBudget
from vera_core.policies.cycle_detection import CycleDetector, plan_fingerprint
from vera_core.policies.termination import check_budget, is_terminal_status, should_terminate
from vera_core.policies.truncation import (
    DEFAULT_STDERR_CAP,
    DEFAULT_STDOUT_CAP,
    truncate_observation,
)

__all__ = [
    "DEFAULT_STDERR_CAP",
    "DEFAULT_STDOUT_CAP",
    "ContextBudget",
    "CycleDetector",
    "active_steps",
    "apply_backtrack",
    "check_budget",
    "is_terminal_status",
    "plan_fingerprint",
    "should_terminate",
    "truncate_observation",
]
```

- [ ] **Step 6: Write `vera_core/__init__.py`**

Deliberately minimal — a package-level re-export of the whole domain would create
import cycles once `loop/` lands in Phase 7.

```python
"""vera_core — VERA domain models, ports, policies, and the agent loop.

Import from the subpackages: `vera_core.models`, `vera_core.ports`,
`vera_core.policies`, `vera_core.errors`.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
```

- [ ] **Step 7: Write the `vera_testing` inits**

`packages/testing/src/vera_testing/fakes/__init__.py`:

```python
"""In-memory fakes implementing the vera_core ports."""

from __future__ import annotations

from vera_testing.fakes.event_bus import FakeEventBus
from vera_testing.fakes.llm import FakeLLM
from vera_testing.fakes.object_store import FakeObjectStore
from vera_testing.fakes.sandbox import FakeSandbox
from vera_testing.fakes.vault import FakeKeyVault

__all__ = [
    "FakeEventBus",
    "FakeKeyVault",
    "FakeLLM",
    "FakeObjectStore",
    "FakeSandbox",
]
```

Read each fake module's `__all__` first and use its real class name — for example
`vault.py` exports `FakeKeyVault`, not `FakeVault`.

`packages/testing/src/vera_testing/factories/__init__.py`:

```python
"""Deterministic factories for domain objects used in tests."""

from __future__ import annotations

from vera_testing.factories.domain import (
    make_agent_defaults,
    make_file_description,
    make_file_id,
    make_provider_connection,
    make_provider_connection_id,
    make_run_id,
    make_run_state,
    make_tenant,
    make_tenant_id,
    make_user,
    make_user_id,
    make_workspace_id,
)

__all__ = [
    "make_agent_defaults",
    "make_file_description",
    "make_file_id",
    "make_provider_connection",
    "make_provider_connection_id",
    "make_run_id",
    "make_run_state",
    "make_tenant",
    "make_tenant_id",
    "make_user",
    "make_user_id",
    "make_workspace_id",
]
```

- [ ] **Step 8: Run the test to verify it passes**

```bash
uv run pytest packages/core/tests/test_exports.py -v
```

Expected: 3 passed.

- [ ] **Step 9: Full verification**

```bash
uv run pytest packages/ -q && uv run ruff check packages/ apps/ && uv run mypy packages/core/src packages/testing/src
```

Expected: all tests pass, ruff clean, mypy `Success`.

- [ ] **Step 10: Commit**

```bash
git add packages/core/src/vera_core packages/testing/src/vera_testing packages/core/tests/test_exports.py
git commit -m "feat: re-export public domain, port, policy, and fake surfaces from package roots"
```

---

## Task 5: Prove the fakes satisfy the port protocols

The fakes are the substrate every later phase tests against. If `FakeLLM` drifts
from `LLMPort`, Phase 7 tests a graph against an interface no real adapter
implements, and the failure surfaces in Phase 8 as a mystery. A conformance test
catches it at the source.

**Files:**
- Create: `packages/testing/tests/__init__.py`
- Create: `packages/testing/tests/conftest.py`
- Create: `packages/testing/tests/test_fakes_conform.py`
- Modify: `packages/testing/src/vera_testing/assertions.py`
- Create: `packages/testing/tests/test_assertions.py`

**Interfaces:**
- Consumes: `vera_core.ports` (Task 4), `vera_testing.fakes` (Task 4).
- Produces: `vera_testing.assertions.assert_never_contains_secret(haystack, secret)`
  and `assert_conforms(instance, protocol)` — both used by Phases 4 and 8.

- [ ] **Step 1: Write the failing conformance test**

Create `packages/testing/tests/test_fakes_conform.py`:

```python
"""Every fake satisfies the vera_core port protocol it stands in for."""

from __future__ import annotations

import inspect

import pytest
from vera_core.ports import (
    EventBusPort,
    KeyVaultPort,
    LLMPort,
    ObjectStorePort,
    SandboxPort,
)
from vera_testing.assertions import assert_conforms
from vera_testing.fakes import (
    FakeEventBus,
    FakeKeyVault,
    FakeLLM,
    FakeObjectStore,
    FakeSandbox,
)

PAIRS = [
    (FakeLLM, LLMPort),
    (FakeKeyVault, KeyVaultPort),
    (FakeSandbox, SandboxPort),
    (FakeObjectStore, ObjectStorePort),
    (FakeEventBus, EventBusPort),
]


@pytest.mark.parametrize(("fake_cls", "protocol"), PAIRS, ids=lambda p: getattr(p, "__name__", str(p)))
def test_fake_is_runtime_instance_of_protocol(fake_cls, protocol):
    assert isinstance(fake_cls(), protocol)


@pytest.mark.parametrize(("fake_cls", "protocol"), PAIRS, ids=lambda p: getattr(p, "__name__", str(p)))
def test_fake_signatures_match_protocol(fake_cls, protocol):
    """runtime_checkable only checks method *names*. Check the signatures too."""
    assert_conforms(fake_cls(), protocol)


def test_every_port_method_is_keyword_only():
    """Convention: ports take keyword-only arguments so call sites stay readable."""
    for _, protocol in PAIRS:
        for name, member in inspect.getmembers(protocol, inspect.isfunction):
            if name.startswith("_"):
                continue
            params = list(inspect.signature(member).parameters.values())[1:]  # drop self
            positional = [p.name for p in params if p.kind is not inspect.Parameter.KEYWORD_ONLY]
            assert not positional, (
                f"{protocol.__name__}.{name} has positional parameters: {positional}"
            )
```

- [ ] **Step 2: Run it to verify it fails**

```bash
uv run pytest packages/testing/tests/test_fakes_conform.py -v
```

Expected: collection error — `ImportError: cannot import name 'assert_conforms' from 'vera_testing.assertions'`, because that module is empty.

- [ ] **Step 3: Write `assertions.py`**

```python
"""Shared custom assertions used across VERA test suites."""

from __future__ import annotations

import inspect
from typing import Any

__all__ = ["assert_conforms", "assert_never_contains_secret"]


def assert_conforms(instance: object, protocol: type) -> None:
    """Assert `instance` implements every public method of `protocol`, signature included.

    `typing.runtime_checkable` only compares method names, so a fake can drift
    from its port — a renamed keyword argument, a dropped parameter — and still
    pass `isinstance`. This closes that gap.

    Raises AssertionError naming the first mismatch found.
    """
    for name, expected in inspect.getmembers(protocol, inspect.isfunction):
        if name.startswith("_"):
            continue

        actual = getattr(type(instance), name, None)
        assert actual is not None, (
            f"{type(instance).__name__} is missing {protocol.__name__}.{name}"
        )

        expected_params = _public_params(expected)
        actual_params = _public_params(actual)

        missing = expected_params - actual_params
        assert not missing, (
            f"{type(instance).__name__}.{name} is missing parameters "
            f"required by {protocol.__name__}.{name}: {sorted(missing)}"
        )

        assert inspect.iscoroutinefunction(actual) == inspect.iscoroutinefunction(expected), (
            f"{type(instance).__name__}.{name} async-ness does not match "
            f"{protocol.__name__}.{name}"
        )


def _public_params(func: Any) -> set[str]:
    """Parameter names of `func`, excluding `self` and `**kwargs`."""
    return {
        name
        for name, param in inspect.signature(func).parameters.items()
        if name != "self" and param.kind is not inspect.Parameter.VAR_KEYWORD
    }


def assert_never_contains_secret(haystack: object, secret: str) -> None:
    """Assert a secret does not appear anywhere in `haystack`'s string form.

    Used to prove BYOK API keys never reach a response body, a log record, or a
    serialised error. A short or empty secret would match trivially, so it is
    rejected outright rather than passing a meaningless check.
    """
    assert len(secret) >= 8, f"secret is too short to check meaningfully: {len(secret)} chars"
    rendered = repr(haystack)
    assert secret not in rendered, (
        f"secret leaked into {type(haystack).__name__}: "
        f"found at index {rendered.index(secret)}"
    )
```

- [ ] **Step 4: Add the package markers**

`packages/testing/tests/__init__.py`:

```python
"""Tests for vera_testing."""
```

`packages/testing/tests/conftest.py`:

```python
"""conftest.py — makes packages/testing/tests a discoverable pytest root."""

from __future__ import annotations
```

- [ ] **Step 5: Run the conformance test**

```bash
uv run pytest packages/testing/tests/test_fakes_conform.py -v
```

Expected: all parametrised cases pass. If a fake genuinely diverges from its port,
**fix the fake**, not the assertion — the port is the contract. If a port method
takes positional arguments, fix the port to be keyword-only per the convention.

- [ ] **Step 6: Write the assertions' own tests**

Create `packages/testing/tests/test_assertions.py`:

```python
"""Tests for the custom assertions — they must fail when they should."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pytest
from vera_testing.assertions import assert_conforms, assert_never_contains_secret


@runtime_checkable
class _ExamplePort(Protocol):
    async def fetch(self, *, key: str, limit: int) -> str: ...


class _Good:
    async def fetch(self, *, key: str, limit: int) -> str:
        return key * limit


class _MissingParam:
    async def fetch(self, *, key: str) -> str:
        return key


class _NotAsync:
    def fetch(self, *, key: str, limit: int) -> str:
        return key


class _MissingMethod:
    pass


def test_conforms_accepts_a_matching_implementation():
    assert_conforms(_Good(), _ExamplePort)


def test_conforms_rejects_a_dropped_parameter():
    with pytest.raises(AssertionError, match="missing parameters.*limit"):
        assert_conforms(_MissingParam(), _ExamplePort)


def test_conforms_rejects_a_sync_implementation_of_an_async_port():
    with pytest.raises(AssertionError, match="async-ness"):
        assert_conforms(_NotAsync(), _ExamplePort)


def test_conforms_rejects_a_missing_method():
    with pytest.raises(AssertionError, match="is missing"):
        assert_conforms(_MissingMethod(), _ExamplePort)


def test_secret_check_passes_when_absent():
    assert_never_contains_secret({"api_key_masked": "sk-or-v1-****"}, "sk-or-v1-abc12345")


def test_secret_check_fails_when_present():
    with pytest.raises(AssertionError, match="leaked"):
        assert_never_contains_secret({"api_key": "sk-or-v1-abc12345"}, "sk-or-v1-abc12345")


def test_secret_check_rejects_a_trivially_short_secret():
    with pytest.raises(AssertionError, match="too short"):
        assert_never_contains_secret({"a": "b"}, "abc")
```

- [ ] **Step 7: Run the full suite**

```bash
uv run pytest packages/ -q
```

Expected: every test passes — the original 40, plus 3 export tests, plus the
conformance and assertion tests.

- [ ] **Step 8: Commit**

```bash
git add packages/testing
git commit -m "test: add port-conformance and secret-leak assertions with fake conformance suite"
```

---

## Task 6: Green the whole gate and commit the phase

**Files:**
- Modify: `Makefile` (add `check` target)
- Create: `docs/superpowers/plans/completed/2026-08-27-phase-1-notes.md`

**Interfaces:**
- Consumes: everything above.
- Produces: `make check` — the single command every later phase's exit gate runs.

- [ ] **Step 1: Add the `check` target**

```makefile
check: lint test-unit
	@echo "OK — lint, types, layering, and unit tests all pass."
```

Add `check` to the `PHONY` line at the top of the Makefile. Note that line
currently reads `PHONY:` — it is missing the leading `.`, so it declares a target
named `PHONY` rather than a directive. Fix it to `.PHONY:` while you are there.

- [ ] **Step 2: Run the gate**

```bash
uv run ruff check packages/ apps/
uv run ruff format --check packages/ apps/
uv run mypy packages/core/src packages/testing/src
uv run lint-imports
uv run pytest packages/ apps/ -q -m "not integration and not e2e"
```

Expected, in order: `All checks passed!`; format check clean; mypy `Success: no
issues found`; import-linter `Contracts: N kept, 0 broken`; pytest all passing.

Every one of these must pass before the phase is complete. If mypy strict flags
something in existing code, fix the code — do not add a blanket `ignore_errors`.
Per-line `# type: ignore[code]` with a specific code is acceptable only where a
third-party stub is genuinely wrong.

- [ ] **Step 3: Record what shipped**

Create `docs/superpowers/plans/completed/2026-08-27-phase-1-notes.md` with: the
final output of each gate command, the exact list of deleted paths, and any place
where the implementation diverged from this plan and why. Phase 2 reads this file
before starting.

- [ ] **Step 4: Commit and verify the tree is clean**

```bash
git add -A
git commit -m "chore: complete phase 1 — foundation repair and domain layer

make check is green: ruff, ruff format, mypy strict, import-linter, unit tests."
git status --porcelain
```

Expected: `git status --porcelain` prints nothing except possibly `apps/web/`
changes, which are outside this phase's scope and must not be committed here.

---

## Phase Exit Gate

Do not start Phase 2 until all of these hold:

- [ ] `make check` exits 0.
- [ ] `git status --porcelain` shows no untracked file under `packages/`.
- [ ] `uv run lint-imports` reports 0 broken contracts.
- [ ] `uv run mypy packages/core/src packages/testing/src` reports 0 errors under
      `strict = True`.
- [ ] `packages/core/src/vera_core` imports nothing outside itself and the stdlib
      plus Pydantic — verify with
      `grep -rn "^from vera_" packages/core/src/vera_core | grep -v "from vera_core"`,
      which must print nothing.
- [ ] Every fake passes `assert_conforms` against its port.
- [ ] `.env.example` lists every variable, and none of them holds a real secret —
      verify with `grep -iE "sk-|nvapi-|postgres://.*@[a-z0-9-]+\.(aws|neon)" .env.example`,
      which must print nothing.
