"""Spending insights and notifications for the web app.

Both are worked out from the database on request; nothing extra is stored.
"""
from calendar import monthrange
from datetime import date, timedelta
from typing import Any

from budget_ai.budgets import budget_report, current_month
from budget_ai.db.database import Database


def month_bounds(month: str) -> tuple[date, date]:
    """First and last day of a YYYY-MM month."""
    year, mon = (int(part) for part in month.split("-"))
    return date(year, mon, 1), date(year, mon, monthrange(year, mon)[1])


def previous_month(month: str) -> str:
    first, _ = month_bounds(month)
    return (first - timedelta(days=1)).strftime("%Y-%m")


def spending_insights(
    db: Database, month: str | None = None, today: date | None = None
) -> dict[str, Any]:
    """Spending for a month compared with the same days of the month before.

    For the current month the period runs from the 1st to today; for a past
    month it is the whole month. The comparison uses the same number of days
    from the start of the previous month (cut short if that month is shorter).
    """
    today = today or date.today()
    month = month or current_month(today)
    first, last = month_bounds(month)
    end = today if first <= today <= last else last
    days = (end - first).days + 1

    prev_first, prev_last = month_bounds(previous_month(month))
    prev_end = min(prev_first + timedelta(days=days - 1), prev_last)

    spent = db.spending_between(first, end)
    prev_spent = db.spending_between(prev_first, prev_end)
    change_pct = round((spent - prev_spent) / prev_spent * 100, 1) if prev_spent > 0 else None

    week_start = end - timedelta(days=6)
    per_day = db.daily_spending(week_start, end)
    daily = []
    for offset in range(7):
        day = week_start + timedelta(days=offset)
        daily.append({"date": day.isoformat(), "amount": per_day.get(day.isoformat(), 0.0)})

    by_category = sorted(
        db.spending_by_category_for_month(month).items(), key=lambda kv: kv[1], reverse=True
    )

    return {
        "month": month,
        "period": {"start": first.isoformat(), "end": end.isoformat()},
        "spent": spent,
        "previous": {
            "start": prev_first.isoformat(),
            "end": prev_end.isoformat(),
            "spent": prev_spent,
        },
        "change_pct": change_pct,
        "difference": round(prev_spent - spent, 2),
        "daily": daily,
        "last_7_days_total": round(sum(d["amount"] for d in daily), 2),
        "by_category": [{"category": c, "amount": a} for c, a in by_category],
    }


def notifications(
    db: Database, month: str | None = None, today: date | None = None
) -> list[dict[str, Any]]:
    """Alerts about budgets and goals, most urgent first.

    Each has a stable "id" (so the app can remember which were read), a
    "kind" and the numbers needed to word it. The app writes the text, so
    category names can be shown with friendly labels.
    """
    today = today or date.today()
    report = budget_report(db, month=month, today=today)
    month = report["month"]
    items: list[dict[str, Any]] = []

    for b in report["budgets"]:
        if b["state"] in ("over", "warning"):
            kind = "budget_over" if b["state"] == "over" else "budget_warning"
            items.append({
                "id": f"{kind}:{b['category']}:{month}",
                "kind": kind,
                "category": b["category"],
                "spent": b["spent"],
                "limit": b["monthly_limit"],
                "pct_used": b["pct_used"],
            })

    for g in report["goals"]:
        if g["state"] in ("done", "overdue"):
            kind = "goal_done" if g["state"] == "done" else "goal_overdue"
            items.append({
                "id": f"{kind}:{g['id']}",
                "kind": kind,
                "goal_id": g["id"],
                "name": g["name"],
                "saved": g["saved_amount"],
                "target": g["target_amount"],
            })

    order = {"budget_over": 0, "goal_overdue": 1, "budget_warning": 2, "goal_done": 3}
    items.sort(key=lambda n: order[n["kind"]])
    return items
