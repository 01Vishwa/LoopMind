"""Agent configuration domain models — tier-to-model assignments."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

from vera_core.models.ids import ProviderConnectionId, UserId


class AgentTier(StrEnum):
    REASONING = "reasoning"  # planner, coder, verifier, router
    UTILITY = "utility"  # analyzer, debugger, finalizer
    EMBEDDING = "embedding"  # retriever


class ModelAssignment(BaseModel):
    """Maps an agent tier to a specific model on a specific provider."""

    tier: AgentTier
    provider_connection_id: ProviderConnectionId
    model_id: str  # provider-specific model identifier
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=128_000)

    model_config = {"frozen": True}


class AgentDefaults(BaseModel):
    """User-level default configuration applied to all runs."""

    user_id: UserId
    assignments: list[ModelAssignment] = Field(default_factory=list)
    max_rounds: int = Field(default=10, ge=1, le=50)
    max_cost_usd: Decimal = Field(default=Decimal("5.00"))
    max_debug_attempts: int = Field(default=3, ge=0, le=10)
    max_files_per_workspace: int = Field(default=50, ge=1, le=500)
    max_file_size_bytes: int = Field(default=104_857_600, ge=1)  # 100 MB
    retriever_top_k: int = Field(default=12, ge=1, le=50)

    def has_all_tiers(self) -> bool:
        """Return True if reasoning and utility tiers are both assigned."""
        assigned_tiers = {a.tier for a in self.assignments}
        return AgentTier.REASONING in assigned_tiers and AgentTier.UTILITY in assigned_tiers

    def get_assignment(self, tier: AgentTier) -> ModelAssignment:
        """Return the assignment for a tier. Raises ValueError if missing."""
        for assignment in self.assignments:
            if assignment.tier == tier:
                return assignment
        raise ValueError(f"No model assignment for tier {tier!r}")

    def to_budget_dict(self) -> dict[str, object]:
        return {
            "max_rounds": self.max_rounds,
            "max_cost_usd": self.max_cost_usd,
            "max_debug_attempts": self.max_debug_attempts,
            "max_wall_clock_s": 900,
        }


__all__ = ["AgentTier", "ModelAssignment", "AgentDefaults"]
