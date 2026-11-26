from datetime import date, datetime
from typing import List, Dict, Any, Optional
from budget_ai.db.database import Database

def current_month(today: date | None = None) -> str:
    """Return the current month in YYYY-MM format."""
    if today is None:
        today = date.today()
    return today.strftime("%Y-%m")

def budget_status(db: Database, month: str | None = None) -> List[Dict[str, Any]]:
    """Get the status of all budgets for a given month, sorted by usage."""
    if month is None:
        month = current_month()
    
    budgets = db.list_budgets()
    spending = db.spending_by_category_for_month(month)
    
    status_list = []
    for budget in budgets:
        category = budget["category"]
        limit = float(budget["monthly_limit"])
        spent = float(spending.get(category, 0.0))
        
        remaining = round(limit - spent, 2)
        pct_used = round((spent / limit * 100), 1) if limit > 0 else 0.0
        
        if spent > limit:
            state = "over"
        elif pct_used >= 80:
            state = "warning"
        else:
            state = "ok"
            
        status_list.append({
            "category": category,
            "monthly_limit": limit,
            "spent": spent,
            "remaining": remaining,
            "pct_used": pct_used,
            "state": state
        })
    
    # Sort by pct_used descending
    status_list.sort(key=lambda x: x["pct_used"], reverse=True)
    return status_list

def unbudgeted_spending(db: Database, month: str | None = None) -> Dict[str, float]:
    """Identify spending in categories that do not have a budget set."""
    if month is None:
        month = current_month()
        
    budgets = db.list_budgets()
    budgeted_categories = {b["category"] for b in budgets}
    spending = db.spending_by_category_for_month(month)
    
    unbudgeted = {}
    for category, amount in spending.items():
        if category not in budgeted_categories:
            unbudgeted[category] = amount
            
    return unbudgeted

def goal_status(db: Database, today: date | None = None) -> List[Dict[str, Any]]:
    """Get the status of all goals based on the current date."""
    if today is None:
        today = date.today()
    
    goals = db.list_goals()
    status_list = []
    
    for goal in goals:
        goal_id = goal["id"]
        name = goal["name"]
        target_amount = float(goal["target_amount"])
        saved_amount = float(goal["saved_amount"])
        target_date_str = goal["target_date"]
        
        remaining = round(target_amount - saved_amount, 2)
        
        if saved_amount >= target_amount:
            pct_complete = 100.0
            state = "done"
        else:
            pct_complete = round((saved_amount / target_amount * 100), 1) if target_amount > 0 else 0.0
            state = "on_track"
            
        months_left = None
        monthly_needed = None
        
        if target_date_str:
            target_date = date.fromisoformat(target_date_str)
            
            # Calculate whole months left
            if target_date > today:
                months_left = (target_date.year - today.year) * 12 + (target_date.month - today.month)
                if months_left < 0:
                    months_left = 0
            else:
                months_left = 0
            
            # Monthly needed calculation
            if months_left == 0 and remaining > 0:
                monthly_needed = round(remaining, 2)
            elif months_left > 0 and remaining > 0:
                monthly_needed = round(remaining / months_left, 2)
            
            if today > target_date and state != "done":
                state = "overdue"
        else:
            # No target date, check if it's overdue (impossible if no target date, but logic says target_date is None)
            pass

        status_list.append({
            "id": goal_id,
            "name": name,
            "description": goal.get("description"),
            "icon": goal.get("icon"),
            "target_amount": target_amount,
            "saved_amount": saved_amount,
            "remaining": remaining,
            "pct_complete": min(pct_complete, 100.0),
            "target_date": target_date_str,
            "months_left": months_left,
            "monthly_needed": monthly_needed,
            "state": state
        })
        
    return status_list

def budget_report(db: Database, month: str | None = None, today: date | None = None) -> Dict[str, Any]:
    """Generate a JSON-serialisable summary report of budgets and goals."""
    if month is None:
        month = current_month()
    if today is None:
        today = date.today()
        
    budgets = budget_status(db, month)
    unbudgeted = unbudgeted_spending(db, month)
    goals = goal_status(db, today)
    
    total_budget = sum(float(b["monthly_limit"]) for b in budgets)
    total_spent_on_budgeted = sum(float(b["spent"]) for b in budgets)
    
    return {
        "month": month,
        "budgets": budgets,
        "unbudgeted": unbudgeted,
        "goals": goals,
        "total_budget": round(total_budget, 2),
        "total_spent_on_budgeted": round(total_spent_on_budgeted, 2)
    }
