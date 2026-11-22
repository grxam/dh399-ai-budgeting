from unittest.mock import MagicMock

import pytest
from openai import OpenAI

from budget_ai.vision.agent import VisionAgent


def test_vision_agent_extract_success(tmp_path):
    """Test successful receipt extraction with a mocked client."""
    mock_client = MagicMock(spec=OpenAI)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"merchant": "Test Store", "total": 10.0, "items": [], "confidence": 1.0}'))]
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = VisionAgent(mock_client, "fake-model")
    
    # Write a dummy image file
    image_path = tmp_path / "receipt.jpg"
    image_path.write_bytes(b"fake_image_data")
    
    receipt = agent.extract(str(image_path))
    
    assert receipt.merchant == "Test Store"
    assert receipt.total == 10.0
    assert receipt.confidence == 1.0

def test_vision_agent_parse_json_with_fences():
    """Test parsing JSON that is wrapped in markdown fences."""
    json_text = '```json\n{"merchant": "Store", "total": 5.0, "items": [], "confidence": 0.9}\n```'
    receipt = VisionAgent.parse_receipt_json(json_text)
    assert receipt.merchant == "Store"
    assert receipt.total == 5.0

def test_vision_agent_parse_json_failure():
    """Test that parsing invalid JSON raises a ValueError."""
    invalid_json = '{"merchant": "Store", "total": "invalid_number"}'
    with pytest.raises(ValueError):
        VisionAgent.parse_receipt_json(invalid_json)
