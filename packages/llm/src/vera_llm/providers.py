"""Static per-provider configuration for BYOK connections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from vera_core.models.provider import ProviderKind


@dataclass(frozen=True)
class ProviderConfig:
    """Immutable wire configuration for a single provider kind."""

    default_base_url: str
    auth_header: str
    auth_prefix: str
    extra_headers: dict[str, str]
    models_path: str
    cost_source: Literal["header", "compute"]


PROVIDER_CONFIGS: dict[ProviderKind, ProviderConfig] = {
    ProviderKind.OPENROUTER: ProviderConfig(
        default_base_url="https://openrouter.ai/api/v1",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        extra_headers={"HTTP-Referer": "https://vera.app", "X-Title": "VERA Analytics"},
        models_path="/models",
        cost_source="header",
    ),
    ProviderKind.NVIDIA_NIM: ProviderConfig(
        default_base_url="https://integrate.api.nvidia.com/v1",
        auth_header="Authorization",
        auth_prefix="Bearer ",
        extra_headers={},
        models_path="/models",
        cost_source="compute",
    ),
}


__all__ = ["ProviderConfig", "PROVIDER_CONFIGS"]
