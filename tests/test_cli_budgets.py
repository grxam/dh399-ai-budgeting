import os
import pytest
from budget_ai.cli import main

def test_budget_set_and_list(tmp_path, capsys, monkeypatch):
    db_path = str(tmp_path / "budget.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    
    # budget set groceries 200.0
    main(["budget", "set", "groceries", "200.0"])
    
    # budget list
    main(["budget", "list"])
    
    captured = capsys.readouterr()
    assert "Budget set for groceries to 200.0" in captured.out
    assert "groceries" in captured.out
    assert "200.0" in captured.out

def test_goal_add_contribute_and_list(tmp_path, capsys, monkeypatch):
    db_path = str(tmp_path / "budget.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    
    # goal add "Test Goal" 100.0 --date 2026-12-31
    main(["goal", "add", "Test Goal", "100.0", "--date", "2026-12-31"])
    
    # goal contribute 1 50.0
    main(["goal", "contribute", "1", "50.0"])
    
    # goal list
    main(["goal", "list"])
    
    captured = capsys.readouterr()
    assert "Goal 'Test Goal' added." in captured.out
    assert "Contributed 50.0 to goal 1." in captured.out
    assert "Test Goal" in captured.out
    assert "50.0" in captured.out

def test_invalid_category_exit(tmp_path, monkeypatch):
    db_path = str(tmp_path / "budget.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    
    with pytest.raises(SystemExit) as excinfo:
        main(["budget", "set", "invalid_category", "100.0"])
    
    assert excinfo.value.code == 1
