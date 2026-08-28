"""Domain object factories for tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from vera_core.models.agent_config import AgentDefaults, AgentTier, ModelAssignment
from vera_core.models.code import CodeArtifact
from vera_core.models.file import FileDescription, SchemaField
from vera_core.models.ids import (
    FileId,
    ProviderConnectionId,
    RunId,
    TenantId,
    UserId,
    WorkspaceId,
)
from vera_core.models.observation import Observation
from vera_core.models.plan import PlanStep
from vera_core.models.provider import ConnectionStatus, ProviderConnection, ProviderKind
from vera_core.models.run import RunBudget, RunMode, RunState, RunStatus
from vera_core.models.tenancy import Role, Tenant, TenantPlan, User
from vera_core.models.verdict import Verdict


def make_tenant_id() -> TenantId:
    return TenantId(uuid.uuid4())


def make_user_id() -> UserId:
    return UserId(uuid.uuid4())


def make_workspace_id() -> WorkspaceId:
    return WorkspaceId(uuid.uuid4())


def make_run_id() -> RunId:
    return RunId(uuid.uuid4())


def make_file_id() -> FileId:
    return FileId(uuid.uuid4())


def make_provider_connection_id() -> ProviderConnectionId:
    return ProviderConnectionId(uuid.uuid4())


def make_tenant(
    *,
    id: TenantId | None = None,
    name: str = "Test Tenant",
    plan: TenantPlan = TenantPlan.FREE,
    created_at: datetime | None = None,
) -> Tenant:
    return Tenant(
        id=id or make_tenant_id(),
        name=name,
        plan=plan,
        created_at=created_at or datetime.now(UTC),
    )


def make_user(
    tenant_id: TenantId | None = None,
    *,
    id: UserId | None = None,
    email: str = "test@example.com",
    full_name: str = "Test User",
    role: Role = Role.ANALYST,
    created_at: datetime | None = None,
) -> User:
    return User(
        id=id or make_user_id(),
        tenant_id=tenant_id or make_tenant_id(),
        email=email,
        full_name=full_name,
        role=role,
        created_at=created_at or datetime.now(UTC),
    )


def make_provider_connection(
    user_id: UserId | None = None,
    tenant_id: TenantId | None = None,
    *,
    id: ProviderConnectionId | None = None,
    kind: ProviderKind = ProviderKind.OPENROUTER,
    display_name: str = "Test OpenRouter",
    base_url: str = "https://openrouter.ai/api/v1",
    api_key_ref: str | None = None,
    status: ConnectionStatus = ConnectionStatus.CONNECTED,
    created_at: datetime | None = None,
) -> ProviderConnection:
    return ProviderConnection(
        id=id or make_provider_connection_id(),
        tenant_id=tenant_id or make_tenant_id(),
        user_id=user_id or make_user_id(),
        kind=kind,
        display_name=display_name,
        base_url=base_url,
        api_key_ref=api_key_ref or f"provider:{uuid.uuid4()}:api_key",
        status=status,
        created_at=created_at or datetime.now(UTC),
    )


def make_agent_defaults(
    user_id: UserId | None = None,
    provider_connection_id: ProviderConnectionId | None = None,
    *,
    assignments: list[ModelAssignment] | None = None,
    max_rounds: int = 10,
    max_cost_usd: Decimal = Decimal("5.00"),
    max_debug_attempts: int = 3,
    retriever_top_k: int = 12,
) -> AgentDefaults:
    conn_id = provider_connection_id or make_provider_connection_id()
    return AgentDefaults(
        user_id=user_id or make_user_id(),
        assignments=assignments
        if assignments is not None
        else [
            ModelAssignment(
                tier=AgentTier.REASONING,
                provider_connection_id=conn_id,
                model_id="anthropic/claude-sonnet-5",
            ),
            ModelAssignment(
                tier=AgentTier.UTILITY,
                provider_connection_id=conn_id,
                model_id="meta/llama-3.1-70b-instruct",
            ),
        ],
        max_rounds=max_rounds,
        max_cost_usd=max_cost_usd,
        max_debug_attempts=max_debug_attempts,
        retriever_top_k=retriever_top_k,
    )


def make_file_description(
    file_id: FileId | None = None,
    *,
    summary_text: str = "A CSV file with sales data.",
    schema_fields: list[SchemaField] | None = None,
    row_count: int | None = 1000,
) -> FileDescription:
    return FileDescription(
        file_id=file_id or make_file_id(),
        summary_text=summary_text,
        schema_fields=schema_fields
        if schema_fields is not None
        else [
            SchemaField(name="date", dtype="string"),
            SchemaField(name="revenue", dtype="float64"),
        ],
        row_count=row_count,
        analyzer_model="fake/model",
    )


def make_run_state(
    user_id: UserId | None = None,
    tenant_id: TenantId | None = None,
    workspace_id: WorkspaceId | None = None,
    *,
    run_id: RunId | None = None,
    query: str = "What is the total revenue by region?",
    mode: RunMode = RunMode.PRECISE,
    status: RunStatus = RunStatus.RUNNING,
    budget: RunBudget | None = None,
    started_at: datetime | None = None,
) -> RunState:
    return RunState(
        run_id=run_id or make_run_id(),
        tenant_id=tenant_id or make_tenant_id(),
        user_id=user_id or make_user_id(),
        workspace_id=workspace_id or make_workspace_id(),
        query=query,
        mode=mode,
        status=status,
        budget=budget or RunBudget(),
        started_at=started_at or datetime.now(UTC),
    )


def make_plan_step(
    *,
    index: int = 0,
    text: str = "step",
    acceptance_criteria: list[str] | None = None,
    created_at_round: int = 0,
    superseded: bool = False,
) -> PlanStep:
    return PlanStep(
        index=index,
        text=text,
        acceptance_criteria=acceptance_criteria if acceptance_criteria is not None else [],
        created_at_round=created_at_round,
        superseded=superseded,
    )


def make_code_artifact(
    *,
    source: str = "print(1)",
    sha256: str = "sha",
    parent_sha256: str | None = None,
) -> CodeArtifact:
    return CodeArtifact(source=source, sha256=sha256, parent_sha256=parent_sha256)


def make_observation(
    *,
    stdout: str = "ok",
    stderr: str = "",
    exit_code: int = 0,
    duration_ms: int = 1,
) -> Observation:
    return Observation(
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        duration_ms=duration_ms,
    )


def make_verdict(
    *,
    sufficient: bool = True,
    reason: str = "looks correct enough",
    missing_aspects: list[str] | None = None,
) -> Verdict:
    return Verdict(
        sufficient=sufficient,
        reason=reason,
        missing_aspects=missing_aspects if missing_aspects is not None else [],
    )


__all__ = [
    "make_tenant_id",
    "make_user_id",
    "make_workspace_id",
    "make_run_id",
    "make_file_id",
    "make_provider_connection_id",
    "make_tenant",
    "make_user",
    "make_provider_connection",
    "make_agent_defaults",
    "make_file_description",
    "make_run_state",
    "make_plan_step",
    "make_code_artifact",
    "make_observation",
    "make_verdict",
]
