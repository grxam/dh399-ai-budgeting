import io
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from budget_ai.api.app import app
from budget_ai.api.deps import get_db
from budget_ai.db.database import Database
from budget_ai.models import Receipt, Goal, LineItem
import os
import tempfile

client = TestClient(app)

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_budget.db"
    return str(db_file)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_categories():
    response = client.get("/api/categories")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("budget_ai.api.app.budget_report")
def test_report(mock_report, test_db):
    mock_report.return_value = {
        "month": "2026-01",
        "budgets": [],
        "unbudgeted": {},
        "goals": [],
        "total_budget": 100.0,
        "total_spent_on_budgeted": 50.0
    }
    response = client.get("/api/report?month=2026-01")
    assert response.status_code == 200
    assert response.json()["month"] == "2026-01"

def test_budget_put_get(test_db):
    app.dependency_overrides[get_db] = lambda: Database(test_db)
    
    # Ensure fresh DB
    Database(test_db).close() # This might fail if it doesn't exist, but Database init creates it
    # Wait, Database init creates it.
    
    # Test PUT
    response = client.put("/api/budgets/groceries", json={"monthly_limit": 100.0})
    assert response.status_code == 200
    
    # Test GET
    response = client.get("/api/budgets")
    assert response.status_code == 200
    assert response.json()[0]["category"] == "groceries"
    assert response.json()[0]["monthly_limit"] == 100.0
    
    del app.dependency_overrides[get_db]

def test_unknown_category_422(test_db):
    app.dependency_overrides[get_db] = lambda: Database(test_db)
    
    response = client.put("/api/budgets/nonexistent", json={"monthly_limit": 100.0})
    assert response.status_code == 422
    
    del app.dependency_overrides[get_db]

def test_goal_flow(test_db):
    app.dependency_overrides[get_db] = lambda: Database(test_db)
    # Database(test_db) will create it.
    
    # Create
    res = client.post("/api/goals", json={"name": "Save for Car", "target_amount": 5000.0, "saved_amount": 0.0})
    assert res.status_code == 201
    goal_id = res.json()["id"]
    
    # Contribute
    res = client.post(f"/api/goals/{goal_id}/contribute", json={"amount": 100.0})
    assert res.status_code == 200
    
    # Missing goal
    res = client.post("/api/goals/9999/contribute", json={"amount": 10.0})
    assert res.status_code == 404
    
    del app.dependency_overrides[get_db]

def test_receipts_pagination(test_db):
    app.dependency_overrides[get_db] = lambda: Database(test_db)
    
    # No receipts, should return empty items
    response = client.get("/api/receipts?limit=20&offset=0")
    assert response.status_code == 200
    assert response.json()["items"] == []
    
    del app.dependency_overrides[get_db]

def test_receipt_save_fetch(test_db):
    app.dependency_overrides[get_db] = lambda: Database(test_db)
    
    # Save
    receipt_data = {
        "merchant": "Test Store",
        "total": 10.0,
        "category": "groceries",
        "items": [{"description": "Item", "total_price": 10.0, "category": "groceries"}]
    }
    res = client.post("/api/receipts", json=receipt_data)
    assert res.status_code == 201
    receipt_id = res.json()["id"]
    
    # Fetch
    res = client.get(f"/api/receipts/{receipt_id}")
    assert res.status_code == 200
    assert res.json()["merchant"] == "Test Store"
    
    del app.dependency_overrides[get_db]

@patch("budget_ai.api.app.VisionAgent")
@patch("budget_ai.api.app.get_client")
def test_extract_receipt_needs_review(mock_get_client, mock_vision_agent, test_db):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    mock_agent_instance = mock_vision_agent.return_value
    mock_agent_instance.extract.return_value = Receipt(
        merchant="Test Store",
        total=10.0,
        category="groceries",
        confidence=0.5, # Low confidence
        items=[]
    )
    
    files = {"file": ("receipt.jpg", io.BytesIO(b"fake image data"), "image/jpeg")}
    response = client.post("/api/receipts/extract", files=files)
    
    assert response.status_code == 200
    assert response.json()["needs_review"] is True
    
@patch("budget_ai.api.app.ReasoningAgent")
@patch("budget_ai.api.app.get_client")
def test_advice_mock(mock_get_client, mock_reasoning_agent, test_db):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    mock_agent_instance = mock_reasoning_agent.return_value
    mock_agent_instance.advise.return_value = "Mocked advice."
    
    response = client.post("/api/advice", json={"question": "How can I save more?"})
    assert response.status_code == 200
    assert response.json()["answer"] == "Mocked advice."
