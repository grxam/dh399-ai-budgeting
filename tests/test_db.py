from datetime import date

from budget_ai.db import Database
from budget_ai.models import LineItem, Receipt


def make_receipt(**kw) -> Receipt:
    base = {
        "merchant": "Corner Market",
        "purchase_date": date(2026, 3, 1),
        "total": 12.5,
        "category": "groceries",
        "items": [LineItem(description="Milk", total_price=3.5, category="groceries")],
    }
    return Receipt(**{**base, **kw})


def test_save_and_summarise():
    db = Database(":memory:")
    db.save_receipt(make_receipt())
    db.save_receipt(make_receipt(total=7.5))
    db.save_receipt(make_receipt(merchant="Cafe", total=4.0, category="dining"))
    assert db.spending_by_category() == {"groceries": 20.0, "dining": 4.0}
    assert len(db.recent_receipts()) == 3


def test_line_items_stored():
    db = Database(":memory:")
    rid = db.save_receipt(make_receipt())
    rows = db.conn.execute("SELECT * FROM line_items WHERE receipt_id = ?", (rid,)).fetchall()
    assert [r["description"] for r in rows] == ["Milk"]
