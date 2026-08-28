"""Every public name is importable from its package root."""

from __future__ import annotations

import vera_core.models as models
import vera_core.policies as policies
import vera_core.ports as ports


def test_models_reexports_every_domain_type() -> None:
    expected = {
        "TenantId",
        "UserId",
        "WorkspaceId",
        "FileId",
        "RunId",
        "ProviderConnectionId",
        "Tenant",
        "TenantPlan",
        "User",
        "Role",
        "ProviderKind",
        "ConnectionStatus",
        "ModelInfo",
        "ProviderConnection",
        "ValidationResult",
        "AgentTier",
        "ModelAssignment",
        "AgentDefaults",
        "FileKind",
        "SchemaField",
        "FileRef",
        "FileDescription",
        "RunMode",
        "RunStatus",
        "PlanStep",
        "CodeArtifact",
        "ArtifactRef",
        "Observation",
        "Verdict",
        "RouterAction",
        "RouterDecision",
        "RunBudget",
        "RunState",
        "RunEvent",
    }
    missing = expected - set(models.__all__)
    assert not missing, f"vera_core.models does not re-export: {sorted(missing)}"
    for name in expected:
        assert getattr(models, name) is not None


def test_ports_reexports_every_protocol() -> None:
    expected = {
        "LLMPort",
        "LLMResponse",
        "KeyVaultPort",
        "SandboxPort",
        "DataMount",
        "ResourceLimits",
        "ObjectStorePort",
        "PresignedUpload",
        "EventBusPort",
        "RetrieverPort",
        "ClockPort",
        "SystemClock",
        "FixedClock",
        "Page",
        "RunRepositoryPort",
        "ProviderRepositoryPort",
        "AgentDefaultsRepositoryPort",
        "WorkspaceRepositoryPort",
        "FileRepositoryPort",
    }
    missing = expected - set(ports.__all__)
    assert not missing, f"vera_core.ports does not re-export: {sorted(missing)}"
    for name in expected:
        assert getattr(ports, name) is not None


def test_policies_reexports_every_policy() -> None:
    expected = {
        "check_budget",
        "should_terminate",
        "is_terminal_status",
        "plan_fingerprint",
        "CycleDetector",
        "apply_backtrack",
        "active_steps",
        "truncate_observation",
        "DEFAULT_STDOUT_CAP",
        "DEFAULT_STDERR_CAP",
        "ContextBudget",
    }
    missing = expected - set(policies.__all__)
    assert not missing, f"vera_core.policies does not re-export: {sorted(missing)}"
    for name in expected:
        assert getattr(policies, name) is not None


def test_loop_surface() -> None:
    from vera_core.loop import LoopDeps, run_precise

    assert set({"LoopDeps", "run_precise"}).issubset(_loop_all())
    assert LoopDeps is not None
    assert callable(run_precise)


def _loop_all() -> set[str]:
    import vera_core.loop as loop

    return set(loop.__all__)
