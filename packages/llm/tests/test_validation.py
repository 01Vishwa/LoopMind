"""Unit tests for validate_connection using httpx.MockTransport."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from vera_core.models.provider import ProviderKind
from vera_llm.validation import _cheapest, validate_connection

_FIXTURES = Path(__file__).parent / "fixtures"
_API_KEY = "sk-secret-do-not-leak-abc123"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


def _client(handler: object) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


async def test_valid_key_returns_models() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json=_load("openrouter_models.json"))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    async with _client(handler) as http:
        result = await validate_connection(
            kind=ProviderKind.OPENROUTER,
            base_url="https://openrouter.ai/api/v1",
            api_key=_API_KEY,
            http=http,
        )

    assert result.valid is True
    assert len(result.models) == 4
    assert any(p.endswith("/chat/completions") for p in seen)


async def test_models_401_is_invalid_key_and_skips_completion() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(401, json={"error": "unauthorized"})

    async with _client(handler) as http:
        result = await validate_connection(
            kind=ProviderKind.OPENROUTER,
            base_url="https://openrouter.ai/api/v1",
            api_key=_API_KEY,
            http=http,
        )

    assert result.valid is False
    assert result.error == "Invalid API key"
    assert not any(p.endswith("/chat/completions") for p in calls)
    assert _API_KEY not in (result.error or "")


async def test_empty_model_list_is_invalid() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    async with _client(handler) as http:
        result = await validate_connection(
            kind=ProviderKind.NVIDIA_NIM,
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=_API_KEY,
            http=http,
        )

    assert result.valid is False
    assert result.error == "Provider returned no models"


async def test_completion_500_is_invalid() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json=_load("openrouter_models.json"))
        return httpx.Response(500, json={"error": "boom"})

    async with _client(handler) as http:
        result = await validate_connection(
            kind=ProviderKind.OPENROUTER,
            base_url="https://openrouter.ai/api/v1",
            api_key=_API_KEY,
            http=http,
        )

    assert result.valid is False
    assert result.error == "Completion test failed (500)"


async def test_request_shape_parity_across_providers() -> None:
    bodies: dict[str, dict] = {}

    # Force both providers to advertise the same single model so the cheapest
    # pick is identical and only the wire shape differs.
    single_model = {"data": [{"id": "shared/model", "name": "Shared"}]}

    def or_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/chat/completions"):
            bodies["openrouter"] = json.loads(request.content)
            return httpx.Response(200, json={"choices": []})
        return httpx.Response(200, json=single_model)

    def nim_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/chat/completions"):
            bodies["nvidia_nim"] = json.loads(request.content)
            return httpx.Response(200, json={"choices": []})
        return httpx.Response(200, json=single_model)

    async with _client(or_handler) as http:
        await validate_connection(
            kind=ProviderKind.OPENROUTER,
            base_url="https://openrouter.ai/api/v1",
            api_key=_API_KEY,
            http=http,
        )
    async with _client(nim_handler) as http:
        await validate_connection(
            kind=ProviderKind.NVIDIA_NIM,
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=_API_KEY,
            http=http,
        )

    assert bodies["openrouter"] == bodies["nvidia_nim"]


async def test_api_key_never_leaks_on_error_paths() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    async with _client(handler) as http:
        result = await validate_connection(
            kind=ProviderKind.OPENROUTER,
            base_url="https://openrouter.ai/api/v1",
            api_key=_API_KEY,
            http=http,
        )

    assert result.valid is False
    assert _API_KEY not in (result.error or "")


def test_cheapest_prefers_lowest_input_price() -> None:
    from decimal import Decimal

    from vera_core.models.provider import ModelInfo

    models = [
        ModelInfo(model_id="a", display_name="a", input_price_per_m=Decimal("5")),
        ModelInfo(model_id="b", display_name="b", input_price_per_m=None),
        ModelInfo(model_id="c", display_name="c", input_price_per_m=Decimal("1")),
    ]
    assert _cheapest(models).model_id == "c"


def test_cheapest_falls_back_to_first_when_all_none() -> None:
    from vera_core.models.provider import ModelInfo

    models = [
        ModelInfo(model_id="a", display_name="a"),
        ModelInfo(model_id="b", display_name="b"),
    ]
    assert _cheapest(models).model_id == "a"


@pytest.mark.parametrize("status", [400, 404, 500])
async def test_models_http_error_reports_status(status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": "x"})

    async with _client(handler) as http:
        result = await validate_connection(
            kind=ProviderKind.OPENROUTER,
            base_url="https://openrouter.ai/api/v1",
            api_key=_API_KEY,
            http=http,
        )
    assert result.valid is False
    assert str(status) in (result.error or "")
