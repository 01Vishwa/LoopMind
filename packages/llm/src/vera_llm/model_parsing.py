"""Parse provider ``/models`` responses into domain ``ModelInfo`` lists."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from vera_core.models.provider import ModelInfo, ProviderKind

_PER_MILLION = Decimal(1_000_000)


def _price_per_million(raw: Any) -> Decimal | None:
    """Convert a provider "USD per token" string to Decimal USD per million tokens."""
    if raw is None:
        return None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None
    if value <= 0:
        return None
    return value * _PER_MILLION


def _parse_openrouter(payload: dict[str, Any]) -> list[ModelInfo]:
    models: list[ModelInfo] = []
    for item in payload.get("data", []) or []:
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")
        if not model_id:
            continue
        pricing = item.get("pricing") or {}
        architecture = item.get("architecture") or {}
        modality = str(architecture.get("modality", "")).lower()
        params = item.get("supported_parameters") or []
        models.append(
            ModelInfo(
                model_id=str(model_id),
                display_name=str(item.get("name") or model_id),
                context_window=int(item.get("context_length") or 0),
                input_price_per_m=_price_per_million(pricing.get("prompt")),
                output_price_per_m=_price_per_million(pricing.get("completion")),
                supports_json_mode="response_format" in params,
                supports_function_calling="tools" in params,
                supports_vision="image" in modality,
            )
        )
    return models


def _parse_nim(payload: dict[str, Any]) -> list[ModelInfo]:
    models: list[ModelInfo] = []
    for item in payload.get("data", []) or []:
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")
        if not model_id:
            continue
        models.append(
            ModelInfo(
                model_id=str(model_id),
                display_name=str(model_id),
            )
        )
    return models


def parse_models(kind: ProviderKind, payload: dict[str, Any]) -> list[ModelInfo]:
    """Return the models advertised in a provider's ``/models`` payload."""
    if kind is ProviderKind.OPENROUTER:
        return _parse_openrouter(payload)
    if kind is ProviderKind.NVIDIA_NIM:
        return _parse_nim(payload)
    raise ValueError(f"Unsupported provider kind: {kind}")


__all__ = ["parse_models"]
