from unittest.mock import MagicMock

from openai import OpenAI

from budget_ai.reasoning.agent import ReasoningAgent


def test_reasoning_agent_context_in_prompt():
    """Test that the reasoning agent includes data in the prompt."""
    # Mock Database
    mock_db = MagicMock()
    mock_db.spending_by_category.return_value = {"groceries": 100.0}
    mock_db.recent_receipts.return_value = [{"merchant": "Test Store", "total": 100.0}]
    
    # Mock OpenAI Client
    mock_client = MagicMock(spec=OpenAI)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Mocked advice"))]
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = ReasoningAgent(mock_db, mock_client, "fake-model")
    agent.advise("How am I doing?")
    
    kwargs = mock_client.chat.completions.create.call_args.kwargs
    prompt_content = kwargs["messages"][1]["content"]
    
    assert "<data>" in prompt_content
    assert "groceries" in prompt_content
    assert "Test Store" in prompt_content
