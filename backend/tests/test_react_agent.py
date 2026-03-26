import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import inspect


def test_run_agent_has_correct_signature():
    """run_agent and resume_agent exist with expected parameters"""
    from app.core.react_agent import run_agent, resume_agent

    run_sig = inspect.signature(run_agent)
    assert "message" in run_sig.parameters
    assert "history" in run_sig.parameters
    assert "session_id" in run_sig.parameters

    resume_sig = inspect.signature(resume_agent)
    assert "thread_id" in resume_sig.parameters
    assert "approved" in resume_sig.parameters
    assert "session_id" in resume_sig.parameters


@pytest.mark.asyncio
async def test_run_agent_returns_done_shape():
    """run_agent result dict has all required keys"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Paris is the capital of France."
    mock_response.tool_calls = []
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("app.core.react_agent.get_llm", return_value=mock_llm):
        # Re-import to pick up mock
        import importlib
        import app.core.react_agent as agent_module
        importlib.reload(agent_module)

        result = await agent_module.run_agent(
            message="What is the capital of France?",
            history=[],
            session_id="test-session",
        )

    assert "status" in result
    assert "answer" in result
    assert "sources" in result
    assert "thread_id" in result
    assert "pending_tool" in result
    assert "session_id" in result
