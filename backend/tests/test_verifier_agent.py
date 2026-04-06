"""Tests for VerifierAgent — asserts is_sufficient True/False from mocked NIM."""

import pytest

from tests.conftest import make_mock_chain, fake_verifier_output


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Shared inputs
# ---------------------------------------------------------------------------

_QUERY = "What is the average sales per region?"
_DATA_DESC = "=== DATA DESCRIPTION ===\n--- File: sales.csv ---\n  Columns: [region, sales]\n"
_PLAN_STEPS = [
    {"index": 0, "description": "Load CSV.", "status": "pending"},
    {"index": 1, "description": "Group by region, compute mean.", "status": "pending"},
]
_CODE = "import pandas as pd\ndf = pd.read_csv('sales.csv')\nprint(df.groupby('region')['sales'].mean())"
_STDOUT_OK = "region\nNorth    150.0\nSouth    120.0\ndtype: float64"
_STDOUT_BAD = "Traceback (most recent call last):\n  FileNotFoundError: sales.csv"


# ---------------------------------------------------------------------------
# Sufficient path
# ---------------------------------------------------------------------------

async def test_verifier_sufficient():
    """VerifierAgent returns is_sufficient=True when execution output is good."""
    from core.verifier.verifier_agent import VerifierAgent

    agent = VerifierAgent()
    agent._chain = make_mock_chain(fake_verifier_output(is_sufficient=True))

    result = await agent.verify(
        query=_QUERY,
        data_description=_DATA_DESC,
        plan_steps=_PLAN_STEPS,
        code=_CODE,
        execution_output=_STDOUT_OK,
    )

    assert result["is_sufficient"] is True
    assert isinstance(result["reason"], str)
    assert 0.0 <= result["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# Insufficient path
# ---------------------------------------------------------------------------

async def test_verifier_insufficient():
    """VerifierAgent returns is_sufficient=False when execution failed."""
    from core.verifier.verifier_agent import VerifierAgent

    agent = VerifierAgent()
    agent._chain = make_mock_chain(fake_verifier_output(is_sufficient=False))

    result = await agent.verify(
        query=_QUERY,
        data_description=_DATA_DESC,
        plan_steps=_PLAN_STEPS,
        code=_CODE,
        execution_output=_STDOUT_BAD,
    )

    assert result["is_sufficient"] is False
    assert len(result["reason"]) > 0


# ---------------------------------------------------------------------------
# Schema completeness
# ---------------------------------------------------------------------------

async def test_verifier_output_schema():
    """VerifierAgent result always has is_sufficient, reason, confidence."""
    from core.verifier.verifier_agent import VerifierAgent

    agent = VerifierAgent()
    agent._chain = make_mock_chain(fake_verifier_output())

    result = await agent.verify(
        query=_QUERY,
        data_description=_DATA_DESC,
        plan_steps=_PLAN_STEPS,
        code=_CODE,
        execution_output=_STDOUT_OK,
    )

    assert "is_sufficient" in result
    assert "reason" in result
    assert "confidence" in result
    assert isinstance(result["confidence"], float)


# ---------------------------------------------------------------------------
# Confidence clamped to [0, 1]
# ---------------------------------------------------------------------------

async def test_verifier_confidence_bounds():
    """Pydantic ge/le validators ensure confidence is always 0.0–1.0."""
    from core.verifier.verifier_agent import VerifierOutput
    from pydantic import ValidationError

    # Valid boundary values
    v = VerifierOutput(is_sufficient=True, reason="ok", confidence=0.0)
    assert v.confidence == 0.0
    v2 = VerifierOutput(is_sufficient=True, reason="ok", confidence=1.0)
    assert v2.confidence == 1.0

    # Out-of-range should raise ValidationError
    with pytest.raises(ValidationError):
        VerifierOutput(is_sufficient=True, reason="bad", confidence=1.5)
