"""Manual transactions, activity feed, goal extras, insights and notifications."""
import sqlite3
from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from budget_ai.api.app import app
from budget_ai.api.deps import get_db
from budget_ai.budgets import budget_status, goal_status
from budget_ai.db.database import Database
from budget_ai.insights import notifications, spending_insights
from budget_ai.models import Budget, Goal, Receipt, Transaction


@pytest.fixture
def db():
    database = Database(":memory:")
    yield database
    database.close()


def receipt(total, day, category="groceries", merchant="Shop"):
    return Receipt(merchant=merchant, total=total, purchase_date=day, category=category)


def expense(amount, day, category="dining", description="Coffee"):
    return Transaction(kind="expense", amount=amount, category=category,
                       description=description, txn_date=day)


# --- model ---------------------------------------------------------------

def test_income_category_is_always_income():
    txn = Transaction(kind="income", amount=3200, category="groceries")
    assert txn.category == "income"


def test_expense_rejects_unknown_category():
    with pytest.raises(ValidationError):
        Transaction(kind="expense", amount=5, category="coffee")


def test_expense_category_is_normalised():
    assert Transaction(kind="expense", amount=5, category=" Dining ").category == "dining"


def test_transaction_amount_must_be_positive():
    with pytest.raises(ValidationError):
        Transaction(kind="expense", amount=0, category="dining")


# --- database ------------------------------------------------------------

def test_manual_expenses_count_toward_budgets(db):
    db.set_budget(Budget(category="dining", monthly_limit=100))
    db.save_receipt(receipt(30, date(2026, 11, 3), category="dining"))
    db.add_transaction(expense(5.5, date(2026, 11, 4)))
    db.add_transaction(Transaction(kind="income", amount=3200, txn_date=date(2026, 11, 4)))

    assert db.spending_by_category_for_month("2026-11") == {"dining": 35.5}
    assert db.spending_by_category() == {"dining": 35.5}
    assert budget_status(db, "2026-11")[0]["spent"] == 35.5


def test_activity_merges_receipts_and_transactions_newest_first(db):
    db.save_receipt(receipt(64.8, date(2026, 11, 18), merchant="Whole Foods"))
    db.add_transaction(expense(5.5, date(2026, 11, 18), description="Coffee break"))
    db.add_transaction(Transaction(kind="income", amount=3200, description="Payday",
                                   txn_date=date(2026, 11, 17)))
    db.save_receipt(receipt(10, date(2026, 10, 30), merchant="Old"))
    db.save_receipt(Receipt(merchant="No date", total=1))

    items = db.list_activity()
    titles = [i["title"] for i in items]
    # Order within one day isn't defined (ids come from two tables).
    assert set(titles[:2]) == {"Coffee break", "Whole Foods"}
    assert titles[2:] == ["Payday", "Old", "No date"]
    payday = items[2]
    assert payday["source"] == "manual" and payday["kind"] == "income"
    assert payday["amount"] == 3200 and payday["category"] == "income"
    whole_foods = next(i for i in items if i["title"] == "Whole Foods")
    assert whole_foods["source"] == "receipt" and whole_foods["kind"] == "expense"

    assert [i["title"] for i in db.list_activity(month="2026-10")] == ["Old"]
    assert len(db.list_activity(limit=2, offset=1)) == 2


def test_delete_transaction_and_receipt(db):
    txn_id = db.add_transaction(expense(5, date(2026, 11, 1)))
    rec_id = db.save_receipt(receipt(5, date(2026, 11, 1)))
    assert db.delete_transaction(txn_id) is True
    assert db.delete_transaction(txn_id) is False
    assert db.delete_receipt(rec_id) is True
    assert db.delete_receipt(rec_id) is False
    assert db.list_activity() == []


def test_goal_description_and_icon_round_trip(db):
    db.add_goal(Goal(name="Emergency fund", target_amount=6000, saved_amount=3600,
                     description="Build your safety net", icon="shield"))
    goal = goal_status(db, today=date(2026, 11, 18))[0]
    assert goal["description"] == "Build your safety net"
    assert goal["icon"] == "shield"


def test_old_goals_table_gets_new_columns(tmp_path):
    path = str(tmp_path / "old.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE goals (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, "
                 "target_amount REAL NOT NULL, saved_amount REAL NOT NULL DEFAULT 0, target_date TEXT)")
    conn.execute("INSERT INTO goals (name, target_amount) VALUES ('Laptop', 2000)")
    conn.commit()
    conn.close()

    db = Database(path)
    goals = db.list_goals()
    db.close()
    assert goals[0]["name"] == "Laptop"
    assert goals[0]["description"] is None and goals[0]["icon"] is None


# --- insights ------------------------------------------------------------

def test_insights_compares_month_to_date_with_same_days_last_month(db):
    db.save_receipt(receipt(100, date(2026, 11, 2)))
    db.add_transaction(expense(50, date(2026, 11, 18)))
    db.save_receipt(receipt(999, date(2026, 11, 19)))   # after "today": not in the period
    db.save_receipt(receipt(200, date(2026, 10, 10)))
    db.save_receipt(receipt(777, date(2026, 10, 25)))   # after Oct 18: not compared

    result = spending_insights(db, today=date(2026, 11, 18))
    assert result["month"] == "2026-11"
    assert result["period"] == {"start": "2026-11-01", "end": "2026-11-18"}
    assert result["spent"] == 150
    assert result["previous"] == {"start": "2026-10-01", "end": "2026-10-18", "spent": 200}
    assert result["change_pct"] == -25.0
    assert result["difference"] == 50

    assert [d["date"] for d in result["daily"]] == [f"2026-11-{n}" for n in range(12, 19)]
    assert result["daily"][-1]["amount"] == 50
    assert result["last_7_days_total"] == 50
    # by_category covers the whole month, largest first
    assert result["by_category"][0] == {"category": "groceries", "amount": 1099}


def test_insights_past_month_uses_whole_month_and_short_previous_month(db):
    db.save_receipt(receipt(10, date(2026, 3, 31)))
    db.save_receipt(receipt(40, date(2026, 2, 28)))
    result = spending_insights(db, month="2026-03", today=date(2026, 11, 18))
    assert result["period"] == {"start": "2026-03-01", "end": "2026-03-31"}
    assert result["previous"]["end"] == "2026-02-28"
    assert result["spent"] == 10 and result["previous"]["spent"] == 40
    assert result["daily"][0]["date"] == "2026-03-25"


def test_insights_change_is_none_without_previous_spending(db):
    db.save_receipt(receipt(10, date(2026, 11, 2)))
    assert spending_insights(db, today=date(2026, 11, 18))["change_pct"] is None


# --- notifications -------------------------------------------------------

def test_notifications_most_urgent_first(db):
    db.set_budget(Budget(category="dining", monthly_limit=100))
    db.set_budget(Budget(category="groceries", monthly_limit=100))
    db.set_budget(Budget(category="transport", monthly_limit=100))
    db.save_receipt(receipt(85, date(2026, 11, 2), category="dining"))
    db.save_receipt(receipt(120, date(2026, 11, 2), category="groceries"))
    db.save_receipt(receipt(10, date(2026, 11, 2), category="transport"))
    db.add_goal(Goal(name="Laptop", target_amount=100, saved_amount=100))
    db.add_goal(Goal(name="Trip", target_amount=100, target_date=date(2026, 1, 1)))

    items = notifications(db, month="2026-11", today=date(2026, 11, 18))
    assert [n["kind"] for n in items] == ["budget_over", "goal_overdue", "budget_warning", "goal_done"]
    assert items[0]["id"] == "budget_over:groceries:2026-11"
    assert items[0]["category"] == "groceries" and items[0]["limit"] == 100


# --- API -----------------------------------------------------------------

@pytest.fixture
def client(tmp_path):
    path = str(tmp_path / "api.db")
    app.dependency_overrides[get_db] = lambda: Database(path)
    yield TestClient(app)
    del app.dependency_overrides[get_db]


def test_api_transactions_and_activity(client):
    r = client.post("/api/transactions", json={"kind": "expense", "amount": 5.5, "category": "dining",
                                               "description": "Coffee break", "txn_date": "2026-11-18"})
    assert r.status_code == 201
    txn_id = r.json()["id"]
    assert client.post("/api/transactions", json={"kind": "income", "amount": 3200,
                                                  "txn_date": "2026-11-17"}).status_code == 201

    items = client.get("/api/activity?month=2026-11").json()["items"]
    assert [i["kind"] for i in items] == ["expense", "income"]

    assert client.delete(f"/api/transactions/{txn_id}").status_code == 204
    assert client.delete(f"/api/transactions/{txn_id}").status_code == 404


def test_api_transaction_rejects_bad_input(client):
    assert client.post("/api/transactions", json={"kind": "expense", "amount": 5,
                                                  "category": "coffee"}).status_code == 422
    assert client.post("/api/transactions", json={"kind": "gift", "amount": 5}).status_code == 422


def test_api_delete_receipt(client):
    rid = client.post("/api/receipts", json={"merchant": "A", "total": 3,
                                             "purchase_date": "2026-11-01"}).json()["id"]
    assert client.delete(f"/api/receipts/{rid}").status_code == 204
    assert client.get(f"/api/receipts/{rid}").status_code == 404


def test_api_goal_with_description_and_icon(client):
    r = client.post("/api/goals", json={"name": "Summer escape", "target_amount": 4000,
                                        "description": "A well-earned adventure", "icon": "sun"})
    assert r.status_code == 201
    goal = client.get("/api/goals").json()[0]
    assert goal["description"] == "A well-earned adventure" and goal["icon"] == "sun"


def test_api_insights_and_notifications(client):
    client.put("/api/budgets/dining", json={"monthly_limit": 10})
    client.post("/api/transactions", json={"kind": "expense", "amount": 20, "category": "dining"})
    insights = client.get("/api/insights").json()
    assert insights["spent"] == 20 and len(insights["daily"]) == 7
    assert client.get("/api/notifications").json()[0]["kind"] == "budget_over"


@pytest.mark.parametrize("path", ["/api/insights", "/api/notifications", "/api/activity",
                                  "/api/report", "/api/spending"])
def test_api_rejects_malformed_month(client, path):
    assert client.get(f"{path}?month=2026-13").status_code == 422
    assert client.get(f"{path}?month=November").status_code == 422
