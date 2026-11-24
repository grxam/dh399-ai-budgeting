import unittest
import json
from datetime import date, timedelta
from budget_ai.db.database import Database
from budget_ai.models import Receipt, LineItem, Budget, Goal
from budget_ai.budgets import (
    budget_status,
    unbudgeted_spending,
    goal_status,
    budget_report,
    current_month
)

class TestBudgets(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def tearDown(self):
        self.db.close()

    def test_current_month(self):
        today = date(2026, 5, 15)
        self.assertEqual(current_month(today), "2026-05")
        self.assertTrue(current_month().startswith("2026"))

    def test_budget_status_states(self):
        self.db.set_budget(Budget(category="groceries", monthly_limit=1000.0))
        self.db.set_budget(Budget(category="dining", monthly_limit=1000.0))
        self.db.set_budget(Budget(category="transport", monthly_limit=1000.0))
        
        def insert_spending(category, amount):
            self.db.save_receipt(Receipt(
                merchant="Test",
                purchase_date=date(2026, 5, 1),
                total=amount,
                category=category,
                items=[LineItem(description="test", total_price=amount, category=category)]
            ))

        insert_spending("groceries", 500.0)
        insert_spending("dining", 800.0)
        insert_spending("transport", 1200.0)
        
        status = budget_status(self.db, month="2026-05")
        
        # Sort order check (highest pct_used first)
        # Transport: 120%
        # Dining: 80%
        # Groceries: 50%
        self.assertEqual(status[0]["category"], "transport")
        self.assertEqual(status[0]["state"], "over")
        self.assertEqual(status[0]["pct_used"], 120.0)
        
        self.assertEqual(status[1]["category"], "dining")
        self.assertEqual(status[1]["state"], "warning")
        self.assertEqual(status[1]["pct_used"], 80.0)
        
        self.assertEqual(status[2]["category"], "groceries")
        self.assertEqual(status[2]["state"], "ok")
        self.assertEqual(status[2]["pct_used"], 50.0)

    def test_budget_status_no_spending(self):
        self.db.set_budget(Budget(category="utilities", monthly_limit=100.0))
        status = budget_status(self.db, month="2026-05")
        self.assertEqual(status[0]["spent"], 0.0)
        self.assertEqual(status[0]["remaining"], 100.0)
        self.assertEqual(status[0]["pct_used"], 0.0)
        self.assertEqual(status[0]["state"], "ok")

    def test_unbudgeted_spending(self):
        self.db.set_budget(Budget(category="groceries", monthly_limit=1000.0))
        # Spending in groceries (budgeted) and "other" (not budgeted)
        # Note: categories not in CATEGORIES become "other" due to model validation
        self.db.save_receipt(Receipt(
            merchant="Store",
            purchase_date=date(2026, 5, 1),
            total=50.0,
            category="groceries",
            items=[LineItem(description="food", total_price=50.0, category="groceries")]
        ))
        self.db.save_receipt(Receipt(
            merchant="Tech",
            purchase_date=date(2026, 5, 1),
            total=200.0,
            category="other",
            items=[LineItem(description="gadget", total_price=200.0, category="other")]
        ))

        unbudgeted = unbudgeted_spending(self.db, month="2026-05")
        self.assertEqual(unbudgeted, {"other": 200.0})
        self.assertNotIn("groceries", unbudgeted)

    def test_goal_status(self):
        today = date(2026, 1, 1)
        # Goal 1: Done
        self.db.add_goal(Goal(name="Phone", target_amount=500.0, saved_amount=500.0))
        # Goal 2: Not done, on track
        self.db.add_goal(Goal(name="Car", target_amount=10000.0, saved_amount=5000.0, target_date=date(2026, 12, 31)))
        # Goal 3: No target date
        self.db.add_goal(Goal(name="House", target_amount=200000.0, saved_amount=0.0))
        # Goal 4: Overdue
        self.db.add_goal(Goal(name="Old Laptop", target_amount=1000.0, saved_amount=500.0, target_date=date(2025, 1, 1)))

        status = goal_status(self.db, today=today)
        
        # Find specific goals
        status_dict = {g["name"]: g for g in status}
        
        self.assertEqual(status_dict["Phone"]["state"], "done")
        self.assertEqual(status_dict["Phone"]["pct_complete"], 100.0)

        self.assertEqual(status_dict["Car"]["state"], "on_track")
        # Months left from 2026-01-01 to 2026-12-31:
        # (2026-2026)*12 + (12-1) = 11
        self.assertEqual(status_dict["Car"]["months_left"], 11)
        self.assertEqual(status_dict["Car"]["monthly_needed"], 454.55)
        
        self.assertEqual(status_dict["House"]["target_date"], None)
        self.assertEqual(status_dict["House"]["months_left"], None)
        
        self.assertEqual(status_dict["Old Laptop"]["state"], "overdue")

    def test_goal_status_months_left_zero(self):
        today = date(2026, 1, 1)
        # Goal with target today
        self.db.add_goal(Goal(name="TodayGoal", target_amount=1000.0, saved_amount=500.0, target_date=date(2026, 1, 1)))
        status = goal_status(self.db, today=today)
        goal = status[0]
        self.assertEqual(goal["months_left"], 0)
        self.assertEqual(goal["monthly_needed"], 500.0)

    def test_budget_report_json_serializable(self):
        self.db.set_budget(Budget(category="groceries", monthly_limit=1000.0))
        self.db.save_receipt(Receipt(
            merchant="Store",
            purchase_date=date(2026, 5, 1),
            total=50.0,
            category="groceries",
            items=[LineItem(description="food", total_price=50.0, category="groceries")]
        ))
        
        report = budget_report(self.db, month="2026-05", today=date(2026, 5, 1))
        
        # Test JSON serializability
        try:
            json.dumps(report)
        except TypeError as e:
            self.fail(f"budget_report output is not JSON serializable: {e}")

if __name__ == "__main__":
    unittest.main()
