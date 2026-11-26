import os

import pytest

from budget_ai.db.database import Database
from budget_ai.models import LineItem, Receipt


@pytest.fixture
def db():
    """Fixture to provide an in-memory database."""
    database = Database(":memory:")
    yield database
    database.close()

def test_save_receipt(db: Database):
    """Test saving a receipt and retrieving it."""
    items = [LineItem(description="Bread", quantity=1.0, total_price=2.0, category="groceries")]
    receipt = Receipt(
        merchant="Bakery",
        total=2.0,
        items=items,
        confidence=0.9
    )
    
    receipt_id = db.save_receipt(receipt)
    assert receipt_id > 0
    
    recent = db.recent_receipts(limit=1)
    assert len(recent) == 1
    assert recent[0]["merchant"] == "Bakery"
    assert recent[0]["confidence"] == 0.9

def test_spending_by_category(db: Database):
    """Test that spending is correctly aggregated by category."""
    # Grocery 1
    db.save_receipt(Receipt(
        merchant="Store A",
        total=10.0,
        items=[LineItem(description="X", total_price=10.0, category="groceries")],
        category="groceries"
    ))
    # Grocery 2
    db.save_receipt(Receipt(
        merchant="Store B",
        total=5.0,
        items=[LineItem(description="Y", total_price=5.0, category="groceries")],
        category="groceries"
    ))
    # Dining
    db.save_receipt(Receipt(
        merchant="Cafe",
        total=20.0,
        items=[LineItem(description="Z", total_price=20.0, category="dining")],
        category="dining"
    ))
    
    totals = db.spending_by_category()
    assert list(totals.keys()) == ["dining", "groceries"]
    assert totals["groceries"] == 15.0
    assert totals["dining"] == 20.0

def test_database_folder_creation(tmp_path):
    """Test that database folder is created using tmp_path."""
    db_path = str(tmp_path / "sub" / "test.db")
    db = Database(db_path)
    db.close()
    assert os.path.exists(db_path)


def test_connection_usable_from_another_thread(tmp_path):
    """FastAPI opens the DB in one worker thread and uses it in another."""
    import threading

    db = Database(str(tmp_path / "test.db"))
    errors = []

    def use_db():
        try:
            db.list_budgets()
        except Exception as e:
            errors.append(e)

    worker = threading.Thread(target=use_db)
    worker.start()
    worker.join()
    db.close()
    assert errors == []
