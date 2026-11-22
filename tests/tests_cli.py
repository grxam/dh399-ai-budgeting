from unittest.mock import MagicMock, patch

import pytest

from budget_ai.cli import main


def test_ingest_high_confidence_no_prompt(monkeypatch, tmp_path):
    """Test that ingest saves a high-confidence receipt without prompting."""
    # Setup dummy image path
    img_path = str(tmp_path / "receipt.jpg")
    img_path.write_bytes(b"dummy data")
    
    # Mock Database and VisionAgent
    mock_db = MagicMock()
    mock_db.save_receipt.return_value = 123
    
    mock_agent = MagicMock()
    mock_agent.extract.return_value = MagicMock(
        merchant="Test Merchant",
        total=50.0,
        currency="USD",
        confidence=0.9,
        items=[],
        arithmetic_warnings=lambda: []
    )

    # Patch environment and classes
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "budget.db"))
    monkeypatch.setattr("budget_ai.cli.Database", lambda path: mock_db)
    monkeypatch.setattr("budget_ai.cli.VisionAgent", lambda client, name: mock_agent)
    
    with patch("builtins.input", return_value="y"):
        # Capture stdout to prevent cluttering test output
        with pytest.capture_output():
            main(["ingest", img_path])
            
        mock_db.save_receipt.assert_called_once()
        assert "Saved Receipt ID: 123" in mock_agent.extract.call_args[0][0] # actually check output if possible

def test_summary_no_receipts(monkeypatch, tmp_path):
    """Test that summary prints 'No receipts yet.' on an empty database."""
    db_path = str(tmp_path / "empty_budget.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    
    mock_db = MagicMock()
    mock_db.spending_by_category.return_value = {}
    monkeypatch.setattr("budget_ai.cli.Database", lambda path: mock_db)
    
    with pytest.capture_output() as capsys:
        main(["summary"])
        output = capsys.text
        assert "No receipts yet." in output

def test_ingest_missing_file_exit_code(monkeypatch, tmp_path):
    """Test that ingest with a missing file exits with code 1."""
    db_path = str(tmp_path / "missing.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    
    # Mocking the agent to fail on FileNotFoundError is tricky since it's raised by open()
    # but we can mock the call to extract to raise it.
    mock_agent = MagicMock()
    mock_agent.extract.side_effect = FileNotFoundError("File not found")
    monkeypatch.setattr("budget_ai.cli.VisionAgent", lambda client, name: mock_agent)
    
    # We need to check the exit code. We can catch SystemExit.
    with pytest.raises(SystemExit) as excinfo:
        main(["ingest", "non_existent_file.jpg"])
    
    assert excinfo.value.code == 1
