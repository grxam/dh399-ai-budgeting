"""Demo data for presentations, shaped like the team's Figma frames.

All dates are worked out from `today`, so the demo always shows the current
month part-way through, last month for comparison, and a busy last week.
"""
import os
import random
from datetime import date, timedelta

from budget_ai.db.database import Database
from budget_ai.models import Budget, Goal, Receipt, Transaction

DEFAULT_DEMO_PATH = "data/demo.db"

BUDGETS = {
    "housing": 1500, "groceries": 500, "dining": 250, "transport": 300,
    "utilities": 450, "shopping": 500, "other": 500,
}


def seed_demo(path: str = DEFAULT_DEMO_PATH, today: date | None = None, force: bool = False) -> None:
    """Create a demo database at `path`.

    Raises FileExistsError if the file exists and force is False, so real
    data is never overwritten by accident.
    """
    today = today or date.today()
    if os.path.exists(path):
        if not force:
            raise FileExistsError(f"{path} already exists; use --force to replace it")
        os.remove(path)

    db = Database(path)
    try:
        _fill(db, today)
    finally:
        db.close()


def _fill(db: Database, today: date) -> None:
    rng = random.Random(4)  # same demo every time
    first = today.replace(day=1)
    # Keep this month's dates between the 1st and today.
    def day(n: int) -> date:
        return min(first + timedelta(days=n), today)

    def receipt(merchant: str, total: float, when: date, category: str) -> None:
        db.save_receipt(Receipt(merchant=merchant, total=total, purchase_date=when, category=category))

    def expense(description: str, amount: float, when: date, category: str) -> None:
        if when >= first:  # don't spill into last month
            db.add_transaction(Transaction(kind="expense", amount=amount, description=description,
                                           txn_date=when, category=category))

    for category, limit in BUDGETS.items():
        db.set_budget(Budget(category=category, monthly_limit=limit))

    # This month
    receipt("Landlord", 1500, first, "housing")
    receipt("Metro card", 150, day(2), "transport")
    receipt("City Power", 140, day(4), "utilities")
    receipt("Fibre Co", 110, day(6), "utilities")
    receipt("Outdoor Store", 150, day(9), "shopping")
    for i, amount in enumerate([48.20, 61.50, 72.00, 73.50]):
        receipt("Fresh Market", amount, day(2 + i * 5), "groceries")
    receipt("Whole Foods", 64.80, today, "groceries")
    for i, amount in enumerate([22.00, 38.50, 41.00, 27.50, 45.50]):
        expense("Dinner out", amount, today - timedelta(days=1 + i * 3), "dining")
    expense("Coffee break", 5.50, today, "dining")
    db.add_transaction(Transaction(kind="income", amount=3200, description="Payday",
                                   txn_date=max(today - timedelta(days=1), first)))

    # Last month, for the Insights comparison
    prev_first = (first - timedelta(days=1)).replace(day=1)
    receipt("Landlord", 1500, prev_first, "housing")
    for i in range(22):
        receipt("Various", round(rng.uniform(20, 70), 2), prev_first + timedelta(days=i + 1),
                rng.choice(["groceries", "dining", "shopping", "transport"]))

    db.add_goal(Goal(name="Emergency fund", description="Build your safety net", icon="shield",
                     target_amount=6000, saved_amount=3600))
    db.add_goal(Goal(name="Summer escape", description="A well-earned adventure", icon="sun",
                     target_amount=4000, saved_amount=2400,
                     target_date=date(today.year + 1, 6, 1)))
    db.add_goal(Goal(name="New laptop", description="An upgrade worth saving for", icon="laptop",
                     target_amount=2000, saved_amount=1200))
