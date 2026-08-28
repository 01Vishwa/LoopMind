"""Validate a BYOK provider connection against the live provider."""

from __future__ import annotations

import logging
from decimal import Decimal

import httpx
from vera_core.models.provider import ModelInfo, ProviderKind, ValidationResult

from vera_llm.model_parsing import parse_models
from vera_llm.providers import PROVIDER_CONFIGS

logger = logging.getLogger(__name__)

_MODELS_TIMEOUT = 10.0
_COMPLETION_TIMEOUT = 15.0


def _cheapest(models: list[ModelInfo]) -> ModelInfo:
    """Return the model with the lowest input price (``None`` treated as infinity)."""
    if not models:
        raise ValueError("no models to choose from")

    def key(model: ModelInfo) -> Decimal:
        price = model.input_price_per_m
        return price if price is not None else Decimal("Infinity")

    return min(models, key=key)


async def validate_connection(
    *,
    kind: ProviderKind,
    base_url: str,
    api_key: str,
    http: httpx.AsyncClient,
) -> ValidationResult:
    """Probe ``/models`` then a cheap completion; never leak ``api_key``."""
    cfg = PROVIDER_CONFIGS[kind]
    headers = {cfg.auth_header: f"{cfg.auth_prefix}{api_key}", **cfg.extra_headers}
    models_url = f"{base_url}{cfg.models_path}"

    try:
        r = await http.get(models_url, headers=headers, timeout=_MODELS_TIMEOUT)
    except httpx.HTTPError:
        logger.warning("provider models request failed kind=%s base_url=%s", kind, base_url)
        return ValidationResult(valid=False, error="Could not reach provider")

    logger.info(
        "provider models probe kind=%s base_url=%s status_code=%s",
        kind,
        base_url,
        r.status_code,
    )

    if r.status_code in (401, 403):
        return ValidationResult(valid=False, error="Invalid API key")
    if r.status_code >= 400:
        return ValidationResult(valid=False, error=f"Provider returned {r.status_code}")

    try:
        payload = r.json()
    except ValueError:
        return ValidationResult(valid=False, error="Provider returned an unparseable response")

    models = parse_models(kind, payload)
    if not models:
        return ValidationResult(valid=False, error="Provider returned no models")

    test = _cheapest(models)
    try:
        cr = await http.post(
            f"{base_url}/chat/completions",
            headers=headers,
            timeout=_COMPLETION_TIMEOUT,
            json={
                "model": test.model_id,
                "messages": [{"role": "user", "content": "Say ok"}],
                "max_tokens": 5,
            },
        )
    except httpx.HTTPError:
        logger.warning("provider completion probe failed kind=%s base_url=%s", kind, base_url)
        return ValidationResult(valid=False, error="Completion test could not reach provider")

    logger.info(
        "provider completion probe kind=%s base_url=%s status_code=%s model_count=%s",
        kind,
        base_url,
        cr.status_code,
        len(models),
    )

    if cr.status_code >= 400:
        return ValidationResult(valid=False, error=f"Completion test failed ({cr.status_code})")

    return ValidationResult(valid=True, models=models)


__all__ = ["validate_connection"]
