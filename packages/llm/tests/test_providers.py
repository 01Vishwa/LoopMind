"""Unit tests for PROVIDER_CONFIGS and parse_models."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from vera_core.models.provider import ProviderKind
from vera_llm.model_parsing import parse_models
from vera_llm.providers import PROVIDER_CONFIGS

_FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


def test_provider_configs_cover_both_kinds() -> None:
    assert set(PROVIDER_CONFIGS) == {ProviderKind.OPENROUTER, ProviderKind.NVIDIA_NIM}


def test_openrouter_config_shape() -> None:
    cfg = PROVIDER_CONFIGS[ProviderKind.OPENROUTER]
    assert cfg.default_base_url == "https://openrouter.ai/api/v1"
    assert cfg.auth_header == "Authorization"
    assert cfg.auth_prefix == "Bearer "
    assert cfg.models_path == "/models"
    assert cfg.cost_source == "header"
    assert cfg.extra_headers["X-Title"] == "VERA Analytics"
    assert cfg.extra_headers["HTTP-Referer"] == "https://vera.app"


def test_nim_config_shape() -> None:
    cfg = PROVIDER_CONFIGS[ProviderKind.NVIDIA_NIM]
    assert cfg.default_base_url == "https://integrate.api.nvidia.com/v1"
    assert cfg.auth_header == "Authorization"
    assert cfg.auth_prefix == "Bearer "
    assert cfg.models_path == "/models"
    assert cfg.cost_source == "compute"
    assert cfg.extra_headers == {}


def test_provider_config_is_frozen() -> None:
    cfg = PROVIDER_CONFIGS[ProviderKind.OPENROUTER]
    try:
        cfg.default_base_url = "x"  # type: ignore[misc]
    except Exception as exc:  # noqa: BLE001
        assert exc.__class__.__name__ in {"FrozenInstanceError", "AttributeError"}
    else:
        raise AssertionError("ProviderConfig should be immutable")


def test_parse_openrouter_models() -> None:
    models = parse_models(ProviderKind.OPENROUTER, _load("openrouter_models.json"))
    assert len(models) == 4
    by_id = {m.model_id: m for m in models}

    sonnet = by_id["anthropic/claude-sonnet-4"]
    assert sonnet.display_name == "Anthropic: Claude Sonnet 4"
    assert sonnet.context_window == 200000
    # 0.000003 USD/token -> 3.00 USD per million
    assert sonnet.input_price_per_m == Decimal("3.000000")
    assert sonnet.output_price_per_m == Decimal("15.000000")
    assert sonnet.supports_json_mode is True
    assert sonnet.supports_function_calling is True
    assert sonnet.supports_vision is True

    mistral = by_id["mistralai/mistral-7b-instruct"]
    assert mistral.supports_json_mode is False
    assert mistral.supports_function_calling is False
    assert mistral.supports_vision is False
    assert mistral.input_price_per_m == Decimal("0.030000")

    llama = by_id["meta-llama/llama-3.1-70b-instruct"]
    assert llama.supports_function_calling is True
    assert llama.supports_json_mode is False
    assert llama.supports_vision is False


def test_parse_nim_models() -> None:
    models = parse_models(ProviderKind.NVIDIA_NIM, _load("nvidia_models.json"))
    assert len(models) == 3
    first = models[0]
    assert first.model_id == "meta/llama-3.1-8b-instruct"
    assert first.display_name == "meta/llama-3.1-8b-instruct"
    assert first.context_window == 0
    assert first.input_price_per_m is None
    assert first.output_price_per_m is None
    assert first.supports_json_mode is False
    assert first.supports_vision is False


def test_parse_models_empty_payload() -> None:
    assert parse_models(ProviderKind.OPENROUTER, {"data": []}) == []
    assert parse_models(ProviderKind.NVIDIA_NIM, {}) == []
