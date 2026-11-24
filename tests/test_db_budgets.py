import pytest
from datetime import date
from budget_ai.db.database import Database
from budget_ai.models import Receipt, LineItem, Budget, Goal

@pytest.fixture
def db():
    """Fixture to provide an in-memory database."""
    database = Database(":memory:")
    yield database
    database.close()

def test_budget_crud(db: Database):
    """Test setting, replacing, and deleting budgets."""
    # Set budget
    budget1 = Budget(category="groceries", monthly_limit=500.0)
    db.set_budget(budget1)
    budgets = db.list_budgets()
    assert len(budgets) == 1
    assert budgets[0]["category"] == "groceries"
    assert budgets[0]["monthly_limit"] == 500.0

    # Replace budget
    budget2 = Budget(category="groceries", monthly_limit=600.0)
    db.set_budget(budget2)
    budgets = db.list_budgets()
    assert len(budgets) == 1
    assert budgets[0]["monthly_limit"] == 600.0

    # Delete budget
    db.delete_budget("groceries")
    budgets = db.list_budgets()
    assert len(budgets) == 0

def test_goal_crud(db: Database):
    """Test adding goals and contributing to them."""
    goal = Goal(name="New Car", target_amount=20000.0, saved_amount=1000.0, target_date=date(2027, 1, 1))
    goal_id = db.add_goal(goal)
    assert goal_id > 0
    
    goals = db.list_goals()
    assert len(goals) == 1
    assert goals[0]["name"] == "New Car"
    assert goals[0]["saved_amount"] == 1000.0

    # Contribute
    db.contribute_to_goal(goal_id, 500.0)
    goals = db.list_goals()
    assert goals[0]["saved_amount"] == 1500.0

def test_contribute_to_missing_goal(db: Database):
    """Test that contributing to a missing goal raises ValueError."""
    with pytest.raises(ValueError, match="Goal with ID 999 does not exist"):
        db.contribute_to_goal(999, 100.0)

def test_contribute_negative_amount(db: Database):
    """Test that contributing a negative amount raises ValueError."""
    goal = Goal(name="Test", target_amount=100.0, saved_amount=0.0)
    goal_id = db.add_goal(goal)
    with pytest.raises(ValueError, match="Amount must be greater than zero"):
        db.contribute_to_goal(goal_id, -10.0)

def test_spending_by_month_filtering(db: Database):
    """Test month filtering and exclusion of NULL dates."""
    # 2026-03
    db.save_receipt(Receipt(
        merchant="Store 1",
        total=100.0,
        purchase_date=date(2026, 3, 15),
        category="groceries",
        items=[LineItem(description="X", total_price=100.0, category="groceries")]
    ))
    # 2026-04
    db.save_receipt(Receipt(
        merchant="Store 2",
        total=200.0,
        purchase_date=date(2026, 4, 10),
        category="groceries",
        items=[LineItem(description="Y", total_price=200.0, category="groceries")]
    ))
    # NULL date
    db.save_receipt(Receipt(
        merchant="Store 3",
        total=300.0,
        purchase_date=None,
        category="groceries",
        items=[LineItem(description="Z", total_price=300.0, category="groceries")]
    ))

    # Check March
    march_spend = db.spending_by_category_for_month("2026-03")
    assert march_spend["groceries"] == 100.0
    
    # Check April
    april_spend = db.spending_by_category_for_month("2026-04")
    assert april_spend["groceries"] == 200.0
    
    # Check that NULL date is excluded (total spend should not include 300)
    # This is implicit as it's not in March or April.

def test_list_receipts_filtering_and_pagination(db: Database):
    """Test category filtering and pagination for receipts."""
    # Category A
    db.save_receipt(Receipt(
        merchant="A1",
        total=10.0,
        purchase_date=date(2026, 1, 1),
        category="groceries",
        items=[LineItem(description="X", total_price=10.0, category="groceries")]
    ))
    # Category A
    db.save_receipt(Receipt(
        merchant="A2",
        total=20.0,
        purchase_date=date(2026, 1, 2),
        category="groceries",
        items=[LineItem(description="Y", total_price=20.0, category="groceries")]
    ))
    # Category B
    db.save_receipt(Receipt(
        merchant="B1",
        total=30.0,
        purchase_date=date(2026, 1, 3),
        category="transport",
        items=[LineItem(description="Z", total_price=30.0, category="transport")]
    ))

    # List all - newest first (1-3, then 1-2, then 1-1)
    all_receipts = db.list_receipts()
    assert len(all_receipts) == 3
    assert all_receipts[0]["merchant"] == "B1"
    assert all_receipts[1]["merchant"] == "A2"
    assert all_receipts[2]["merchant"] == "A1"

    # Category filter
    groceries = db.list_receipts(category="groceries")
    assert len(groceries) == 2
    assert all(r["category"] == "groceries" for r in groceries)

    # Pagination
    page1 = db.list_receipts(limit=1, offset=0)
    page2 = db.list_receipts(limit=1, offset=1)
    assert len(page1) == 1
    assert page1[0]["merchant"] == "B1"
    assert len(page2) == 1
    assert page2[0]["merchant"] == "A2"

def test_get_receipt_with_items(db: Database):
    """Test retrieving a receipt with its items."""
    items = [
        LineItem(description="Item 1", total_price=5.0, category="groceries"),
        LineItem(description="Item 2", total_price=10.0, category="groceries")
    ]
    receipt = Receipt(
        merchant="Store",
        total=15.0,
        items=items,
        category="groceries"
    )
    receipt_id = db.save_receipt(receipt)
    
    full_receipt = db.get_receipt_with_items(receipt_id)
    assert full_receipt is not None
    assert full_receipt["merchant"] == "Store"
    assert len(full_receipt["items"]) == 2
    assert full_receipt["items"][0]["description"] == "Item 1"

def test_model_validators():
    """Test pydantic model validators for Budget and Goal."""
    # Budget category validation
    with pytest.raises(ValueError):
        Budget(category="invalid_category", monthly_limit=100.0)
    
    # Budget limit validation
    with pytest.raises(ValueError):
        Budget(category="groceries", monthly_limit=0)
    with pytest.raises(ValueError):
        Budget(category="groceries", monthly_limit=-10.0)

    # Goal name validation
    with pytest.raises(ValueError):
        Goal(name="", target_amount=100.0)

    # Goal amount validation
    with pytest.raises(ValueError):
        Goal(name="Test", target_amount=0)

    # Goal progress_pct cap
    goal_over = Goal(name="Over", target_amount=100.0, saved_amount=200.0)
    assert goal_over.progress_pct() == 100.0
    
    goal_under = Goal(name="Under", target_amount=100.0, saved_amount=50.0)
    assert goal_under.progress_pct() == 50.0

