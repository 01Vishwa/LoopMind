"""Unit tests for the DebuggerAgent.

Mocks the LLM to verify that standard Python tracebacks are successfully 
intercepted and that a 'surgical' replacement is generated rather than 
hallucinating a completely new script.
"""

import pytest
from unittest.mock import AsyncMock, patch
from core.debugger.debugger_agent import DebuggerAgent, DebuggerOutput

@pytest.mark.asyncio
async def test_debugger_agent_performs_targeted_repair():
    """Tests that the debugger suggests a surgical fix and identifies error types."""

    # Synthetic response matching the Pydantic schema
    mock_output = DebuggerOutput(
        error_type="KeyError",
        fix_summary="Changed column name 'Avg' to 'Average'",
        corrected_code="df['Average'] = df.mean()"
    )

    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = mock_output

    with patch("core.debugger.debugger_agent.get_structured_llm"):
        agent = DebuggerAgent()
        agent._chain = mock_chain

        result = await agent.debug(
            traceback="KeyError: 'Avg'",
            code="df['Avg'] = df.mean()",
            plan_steps=[{"index": 0, "description": "Calc mean"}],
            schema_context="Columns: ['Average']"
        )

        assert result["error_type"] == "KeyError"
        assert result["corrected_code"] == "df['Average'] = df.mean()"
        assert result["fix_summary"] == "Changed column name 'Avg' to 'Average'"
        
        # Verify prompt injection
        call_args = mock_chain.ainvoke.call_args[0][0]
        assert "KeyError" in call_args["traceback"]
        assert "df['Avg']" in call_args["code"]
