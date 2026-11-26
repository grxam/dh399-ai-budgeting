"""Activity search and filters, and editing receipts and transactions."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from budget_ai.api.app import app
from budget_ai.api.deps import get_db
from budget_ai.budgets import budget_status
from budget_ai.db.database import Database
from budget_ai.models import Budget, LineItem, Receipt, Transaction


def receipt(merchant, total, day, category="groceries", items=()):
    return Receipt(merchant=merchant, total=total, purchase_date=day, category=category,
                   items=[LineItem(description=d, total_price=p, category=category) for d, p in items])


def expense(description, amount, day, category="dining"):
    return Transaction(kind="expense", amount=amount, description=description,
                       category=category, txn_date=day)


@pytest.fixture
def db():
    database = Database(":memory:")
    database.save_receipt(receipt("Fresh Market", 48.20, date(2026, 11, 3)))
    database.save_receipt(receipt("Fresh Market", 61.50, date(2026, 10, 20)))
    database.save_receipt(receipt("Zehrs", 7.18, date(2026, 11, 16),
                                  items=[("BLUEBERRIES 12OZ", 4.00), ("CUCUMBERS", 0.0)]))
    database.add_transaction(expense("Coffee break", 5.50, date(2026, 11, 18)))
    database.add_transaction(expense("Dinner out", 41.00, date(2026, 11, 12)))
    database.add_transaction(expense("50% off sale_day", 12.00, date(2026, 11, 5), category="shopping"))
    database.add_transaction(Transaction(kind="income", amount=3200, description="Payday",
                                         txn_date=date(2026, 11, 17)))
    yield database
    database.close()


def titles(rows):
    return [r["title"] for r in rows]


# --- search and filters ---------------------------------------------------------

def test_search_matches_title_across_all_months(db):
    assert titles(db.list_activity(q="fresh")) == ["Fresh Market", "Fresh Market"]
    assert titles(db.list_activity(q="FRESH", month="2026-11")) == ["Fresh Market"]


def test_search_matches_receipt_line_items(db):
    assert titles(db.list_activity(q="blueberries")) == ["Zehrs"]


def test_search_treats_wildcards_literally(db):
    assert titles(db.list_activity(q="50%")) == ["50% off sale_day"]
    assert titles(db.list_activity(q="sale_day")) == ["50% off sale_day"]
    assert db.list_activity(q="%") == db.list_activity(q="50%")  # "%" only matches a real "%"
    assert db.list_activity(q="_") == db.list_activity(q="sale_")


def test_filters_by_category_kind_and_amount(db):
    assert titles(db.list_activity(category="dining")) == ["Coffee break", "Dinner out"]
    assert titles(db.list_activity(kind="income")) == ["Payday"]
    assert titles(db.list_activity(category="dining", min_amount=30)) == ["Dinner out"]
    assert titles(db.list_activity(kind="expense", max_amount=10)) == ["Coffee break", "Zehrs"]
    assert titles(db.list_activity(min_amount=40, max_amount=50, month="2026-11")) == ["Dinner out", "Fresh Market"]


def test_rows_keep_the_same_shape(db):
    row = db.list_activity(q="zehrs")[0]
    assert set(row) == {"source", "id", "kind", "title", "category", "amount", "date"}


# --- editing ---------------------------------------------------------------------

def test_update_transaction(db):
    coffee = db.list_activity(q="coffee")[0]
    changed = expense("Coffee and cake", 6.00, date(2026, 11, 19), category="dining")
    assert db.update_transaction(coffee["id"], changed) is True

    row = db.list_activity(q="coffee")[0]
    assert (row["title"], row["amount"], row["date"]) == ("Coffee and cake", 6.0, "2026-11-19")
    assert db.update_transaction(9999, changed) is False


def test_update_transaction_to_income_uses_income_category(db):
    coffee = db.list_activity(q="coffee")[0]
    db.update_transaction(coffee["id"], Transaction(kind="income", amount=20, category="dining",
                                                    description="Refund", txn_date=date(2026, 11, 18)))
    row = db.list_activity(q="refund")[0]
    assert row["kind"] == "income" and row["category"] == "income"


def test_update_receipt_replaces_items_and_budgets_follow(db):
    db.set_budget(Budget(category="groceries", monthly_limit=500))
    zehrs = db.list_activity(q="zehrs")[0]
    edited = receipt("Zehrs Conestoga", 6.00, date(2026, 11, 16),
                     items=[("BLUEBERRIES 12OZ", 4.00), ("BROTH", 2.00)])
    assert db.update_receipt(zehrs["id"], edited) is True

    saved = db.get_receipt_with_items(zehrs["id"])
    assert saved["merchant"] == "Zehrs Conestoga" and saved["total"] == 6.0
    assert [i["description"] for i in saved["items"]] == ["BLUEBERRIES 12OZ", "BROTH"]
    assert db.list_activity(q="cucumbers") == []
    groceries = next(b for b in budget_status(db, "2026-11") if b["category"] == "groceries")
    assert groceries["spent"] == round(48.20 + 6.00, 2)

    assert db.update_receipt(9999, edited) is False


# --- API ---------------------------------------------------------------------------

@pytest.fixture
def client(tmp_path):
    path = str(tmp_path / "api.db")
    seed = Database(path)
    seed.save_receipt(receipt("Zehrs", 7.18, date(2026, 11, 16), items=[("BLUEBERRIES", 4.0)]))
    seed.add_transaction(expense("Coffee break", 5.50, date(2026, 11, 18)))
    seed.add_transaction(Transaction(kind="income", amount=3200, description="Payday",
                                     txn_date=date(2026, 11, 17)))
    seed.close()
    app.dependency_overrides[get_db] = lambda: Database(path)
    yield TestClient(app)
    del app.dependency_overrides[get_db]


def test_api_activity_search_and_filters(client):
    assert [i["title"] for i in client.get("/api/activity?q=blueb").json()["items"]] == ["Zehrs"]
    assert [i["title"] for i in client.get("/api/activity?kind=income").json()["items"]] == ["Payday"]
    rows = client.get("/api/activity?category=dining&min_amount=5&max_amount=6&month=2026-11").json()["items"]
    assert [i["title"] for i in rows] == ["Coffee break"]
    assert [i["title"] for i in client.get("/api/activity?category=income").json()["items"]] == ["Payday"]


@pytest.mark.parametrize("query", ["category=coffee", "kind=gift", "min_amount=-1", "max_amount=-5", "q=" + "x" * 101])
def test_api_activity_rejects_bad_filters(client, query):
    assert client.get(f"/api/activity?{query}").status_code == 422


def test_api_update_transaction(client):
    coffee = client.get("/api/activity?q=coffee").json()["items"][0]
    body = {"kind": "expense", "amount": 6, "category": "dining", "description": "Coffee", "txn_date": "2026-11-18"}
    assert client.put(f"/api/transactions/{coffee['id']}", json=body).status_code == 200
    assert client.get("/api/activity?q=coffee").json()["items"][0]["amount"] == 6

    assert client.put("/api/transactions/9999", json=body).status_code == 404
    assert client.put(f"/api/transactions/{coffee['id']}", json={**body, "category": "coffee"}).status_code == 422
    assert client.put(f"/api/transactions/{coffee['id']}", json={**body, "amount": 0}).status_code == 422


def test_api_update_receipt(client):
    zehrs = client.get("/api/activity?q=zehrs").json()["items"][0]
    detail = client.get(f"/api/receipts/{zehrs['id']}").json()
    body = {
        "merchant": "Zehrs Conestoga", "purchase_date": "2026-11-16", "currency": detail["currency"],
        "total": 6.0, "category": "groceries", "confidence": detail["confidence"],
        "items": [{"description": "BLUEBERRIES", "quantity": 1, "total_price": 4.0},
                  {"description": "BROTH", "quantity": 1, "total_price": 2.0}],
    }
    assert client.put(f"/api/receipts/{zehrs['id']}", json=body).status_code == 200
    saved = client.get(f"/api/receipts/{zehrs['id']}").json()
    assert saved["merchant"] == "Zehrs Conestoga" and len(saved["items"]) == 2

    assert client.put("/api/receipts/9999", json=body).status_code == 404
    assert client.put(f"/api/receipts/{zehrs['id']}", json={**body, "total": "lots"}).status_code == 422
