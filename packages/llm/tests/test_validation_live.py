"""Live provider checks — skipped unless real API keys are in the environment."""

from __future__ import annotations

import os

import httpx
import pytest
from vera_core.models.provider import ProviderKind
from vera_llm.providers import PROVIDER_CONFIGS
from vera_llm.validation import validate_connection

pytestmark = pytest.mark.live_llm


@pytest.mark.skipif("OPENROUTER_API_KEY" not in os.environ, reason="no OPENROUTER_API_KEY")
async def test_openrouter_models_live() -> None:
    async with httpx.AsyncClient() as http:
        result = await validate_connection(
            kind=ProviderKind.OPENROUTER,
            base_url=PROVIDER_CONFIGS[ProviderKind.OPENROUTER].default_base_url,
            api_key=os.environ["OPENROUTER_API_KEY"],
            http=http,
        )
    assert result.valid is True
    assert result.models
