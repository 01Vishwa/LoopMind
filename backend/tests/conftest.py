"""pytest fixtures — mock NIM responses and shared test utilities.

All NIM calls are patched at the langchain_nvidia_ai_endpoints.ChatNVIDIA
level so tests run without a real API key.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Event-loop fixture (required by pytest-asyncio)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default asyncio policy."""
    return asyncio.DefaultEventLoopPolicy()


# ---------------------------------------------------------------------------
# Helper: build a fake ChatNVIDIA instance whose ainvoke returns a parsed obj
# ---------------------------------------------------------------------------

def make_mock_chain(return_value: Any):
    """Returns a mock chain whose ainvoke returns ``return_value``.

    Args:
        return_value: The object the chain will return on ainvoke.

    Returns:
        MagicMock with async ainvoke.
    """
    chain = MagicMock()
    chain.ainvoke = AsyncMock(return_value=return_value)
    return chain


# ---------------------------------------------------------------------------
# Fake Pydantic output objects
# ---------------------------------------------------------------------------

def fake_plan_output():
    """Minimal PlanOutput-like object for planner tests."""
    from core.planner.planner_agent import PlanOutput, PlanStep
    return PlanOutput(steps=[
        PlanStep(index=0, description="Load CSV data.", status="pending"),
        PlanStep(index=1, description="Compute summary statistics.", status="pending"),
    ])


def fake_verifier_output(is_sufficient: bool = True):
    """VerifierOutput-like object."""
    from core.verifier.verifier_agent import VerifierOutput
    return VerifierOutput(
        is_sufficient=is_sufficient,
        reason="The output directly answers the query." if is_sufficient else "Missing histogram.",
        confidence=0.92 if is_sufficient else 0.45,
    )


def fake_router_output(action: str = "ADD_STEP"):
    """RouterOutput-like object."""
    from core.router.router_agent import RouterOutput, StepDetail
    return RouterOutput(
        action=action,
        step_index=0 if action == "FIX_STEP" else None,
        new_step=StepDetail(description="Plot distribution of target column."),
    )


def fake_code_output():
    """CodeOutput-like object."""
    from core.coder.coder_agent import CodeOutput
    return CodeOutput(code="import pandas as pd\nprint('Hello DS-STAR')")
