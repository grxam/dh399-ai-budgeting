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

def test_reasoning_agent_budget_report_in_context():
    """Test that build_context includes budget_report and it's reflected in the prompt."""
    # Mock Database
    mock_db = MagicMock()
    mock_db.spending_by_category.return_value = {"groceries": 100.0}
    mock_db.recent_receipts.return_value = [{"merchant": "Test Store", "total": 100.0}]
    
    # Mock budget data
    mock_db.list_budgets.return_value = [
        {"category": "groceries", "monthly_limit": 200.0}
    ]
    mock_db.spending_by_category_for_month.return_value = {
        "groceries": 100.0
    }
    mock_db.list_goals.return_value = []
    
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
    # Check if budget report is in data
    assert "monthly_limit" in prompt_content
    assert "200.0" in prompt_content
    assert "spent" in prompt_content
    assert "100.0" in prompt_content

