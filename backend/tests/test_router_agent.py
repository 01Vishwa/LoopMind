"""Tests for RouterAgent — asserts ADD_STEP / FIX_STEP parsing from mocked NIM."""

import pytest
from unittest.mock import patch

from tests.conftest import make_mock_chain, fake_router_output


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_QUERY = "What is the average sales per region?"
_DATA_DESC = "=== DATA DESCRIPTION ===\n--- File: sales.csv (type: CSV) ---\n  Columns: [region, sales]\n"
_PLAN_STEPS = [
    {"index": 0, "description": "Load CSV into DataFrame.", "status": "pending"},
    {"index": 1, "description": "Group by region and compute mean.", "status": "pending"},
]
_VERIFIER_REASON = "The histogram of sales is missing from the output."


# ---------------------------------------------------------------------------
# ADD_STEP path
# ---------------------------------------------------------------------------

async def test_router_add_step():
    """RouterAgent returns ADD_STEP when the verifier says a step is missing."""
    from core.router.router_agent import RouterAgent

    agent = RouterAgent()
    agent._chain = make_mock_chain(fake_router_output(action="ADD_STEP"))

    result = await agent.route(
        query=_QUERY,
        data_description=_DATA_DESC,
        plan_steps=_PLAN_STEPS,
        verifier_reason=_VERIFIER_REASON,
    )

    assert result["action"] == "ADD_STEP"
    assert result["step_index"] is None
    assert "description" in result["new_step"]
    assert len(result["new_step"]["description"]) > 0


# ---------------------------------------------------------------------------
# FIX_STEP path
# ---------------------------------------------------------------------------

async def test_router_fix_step():
    """RouterAgent returns FIX_STEP with a valid step_index."""
    from core.router.router_agent import RouterAgent

    agent = RouterAgent()
    agent._chain = make_mock_chain(fake_router_output(action="FIX_STEP"))

    result = await agent.route(
        query=_QUERY,
        data_description=_DATA_DESC,
        plan_steps=_PLAN_STEPS,
        verifier_reason=_VERIFIER_REASON,
    )

    assert result["action"] == "FIX_STEP"
    assert result["step_index"] == 0
    assert "description" in result["new_step"]


# ---------------------------------------------------------------------------
# Output schema completeness
# ---------------------------------------------------------------------------

async def test_router_output_keys():
    """RouterAgent result always has action, step_index, new_step."""
    from core.router.router_agent import RouterAgent

    agent = RouterAgent()
    agent._chain = make_mock_chain(fake_router_output())

    result = await agent.route(
        query=_QUERY,
        data_description=_DATA_DESC,
        plan_steps=_PLAN_STEPS,
        verifier_reason=_VERIFIER_REASON,
    )

    assert set(result.keys()) >= {"action", "step_index", "new_step"}
