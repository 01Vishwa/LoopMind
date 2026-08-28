"""Provider connection domain models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel

from vera_core.models.ids import ProviderConnectionId, TenantId, UserId


class ProviderKind(StrEnum):
    OPENROUTER = "openrouter"
    NVIDIA_NIM = "nvidia_nim"


class ConnectionStatus(StrEnum):
    CONNECTED = "connected"
    VALIDATING = "validating"
    FAILED = "failed"
    REVOKED = "revoked"


class ModelInfo(BaseModel):
    """A model available through a provider connection."""

    model_id: str  # e.g. "anthropic/claude-sonnet-5"
    display_name: str  # e.g. "Claude Sonnet 5"
    context_window: int = 0
    input_price_per_m: Decimal | None = None  # per million tokens
    output_price_per_m: Decimal | None = None
    supports_json_mode: bool = False
    supports_function_calling: bool = False
    supports_vision: bool = False

    model_config = {"frozen": True}


class ProviderConnection(BaseModel):
    """A user's BYOK connection to an LLM provider."""

    id: ProviderConnectionId
    tenant_id: TenantId
    user_id: UserId
    kind: ProviderKind
    display_name: str
    base_url: str  # validated as URL at API layer; kept str here for simplicity
    api_key_ref: str  # vault reference, NEVER the raw key
    status: ConnectionStatus
    available_models: list[ModelInfo] | None = None  # cached from /models
    created_at: datetime
    last_validated_at: datetime | None = None
    last_error: str | None = None

    model_config = {"frozen": True}


class ValidationResult(BaseModel):
    """Result of validating a provider connection."""

    valid: bool
    error: str | None = None
    models: list[ModelInfo] = []


__all__ = [
    "ProviderKind",
    "ConnectionStatus",
    "ModelInfo",
    "ProviderConnection",
    "ValidationResult",
]
