import pytest
from pydantic import ValidationError

from budget_ai.models import LineItem, Receipt


def test_line_item_creation():
    """Test that a valid LineItem can be created with default values."""
    item = LineItem(description="Milk", total_price=3.50)
    assert item.quantity == 1.0
    assert item.category == "other"

def test_category_validation():
    """Test that category is lowercase, stripped, and validated against CATEGORIES."""
    # Valid category
    item = LineItem(description="Bread", total_price=2.0, category=" Groceries ")
    assert item.category == "groceries"
    
    # Invalid category
    item = LineItem(description="Candy", total_price=1.0, category="Sweets")
    assert item.category == "other"

def test_fractional_quantity():
    """Test that fractional quantity is accepted."""
    item = LineItem(description="Meat", total_price=5.0, quantity=0.75)
    assert item.quantity == 0.75

def test_receipt_creation():
    """Test that a valid Receipt can be created."""
    items = [LineItem(description="Apple", total_price=1.0)]
    receipt = Receipt(merchant="Store", total=1.0, items=items)
    assert receipt.merchant == "Store"
    assert receipt.confidence == 1.0

def test_receipt_invalid_confidence():
    """Test that a Receipt with confidence > 1.0 raises a ValidationError."""
    items = [LineItem(description="Apple", total_price=1.0)]
    with pytest.raises(ValidationError):
        Receipt(merchant="Store", total=1.0, items=items, confidence=1.5)

def test_arithmetic_warnings():
    """Test that arithmetic_warnings returns warnings for inconsistent totals."""
    # Inconsistent subtotal
    receipt1 = Receipt(
        merchant="Test 1",
        total=12.0,
        subtotal=10.0,
        items=[LineItem(description="Item 1", total_price=11.0)] # 11.0 != 10.0
    )
    warnings1 = receipt1.arithmetic_warnings()
    assert len(warnings1) == 1
    assert "differs from subtotal" in warnings1[0]

    # Consistent subtotal
    receipt2 = Receipt(
        merchant="Test 2",
        total=12.0,
        subtotal=11.0,
        items=[LineItem(description="Item 1", total_price=11.0)] # 11.0 == 11.0
    )
    warnings2 = receipt2.arithmetic_warnings()
    assert len(warnings2) == 0

def test_arithmetic_warnings_tax():
    """Test that arithmetic_warnings returns warnings for inconsistent tax/total."""
    # Inconsistent tax
    receipt3 = Receipt(
        merchant="Test 3",
        total=12.0,
        subtotal=10.0,
        tax=1.5, # 10.0 + 1.5 = 11.5 != 12.0
        items=[]
    )
    warnings3 = receipt3.arithmetic_warnings()
    assert len(warnings3) == 1
    assert "differs from total" in warnings3[0]


# --- date checks ----------------------------------------------------------

from datetime import date  # noqa: E402

TODAY = date(2026, 11, 26)


@pytest.mark.parametrize("purchase_date, expected", [
    (date(2026, 11, 16), []),                       # recent: fine
    (TODAY, []),                                    # today: fine
    (date(2025, 11, 27), []),                       # just under a year: fine
    (date(2026, 11, 27), ["in the future"]),
    (date(2016, 11, 26), ["more than a year ago"]),  # 26/11/16 read day-first
    (None, ["No purchase date"]),
])
def test_date_warnings(purchase_date, expected):
    warnings = Receipt(merchant="Zehrs", total=7.18, purchase_date=purchase_date).date_warnings(TODAY)
    assert len(warnings) == len(expected)
    for warning, text in zip(warnings, expected):
        assert text in warning


def test_review_warnings_combines_arithmetic_and_date():
    receipt = Receipt(merchant="Zehrs", subtotal=7.98, tax=0.0, total=7.18,
                      purchase_date=date(2016, 11, 26))
    warnings = receipt.review_warnings(TODAY)
    assert len(warnings) == 2
    assert "Subtotal + Tax" in warnings[0] and "more than a year ago" in warnings[1]
