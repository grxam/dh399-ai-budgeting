from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

CATEGORIES = [
    "groceries", "dining", "transport", "utilities", 
    "housing", "health", "entertainment", "shopping", 
    "education", "other"
]

class LineItem(BaseModel):
    """Represents an individual line item on a receipt."""
    description: str
    quantity: float = 1.0
    unit_price: float | None = None
    total_price: float
    category: str = "other"

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Lowercase, strip, and validate category."""
        v = v.lower().strip()
        return v if v in CATEGORIES else "other"

class Budget(BaseModel):
    """Represents a monthly spending budget for a specific category."""
    category: str
    monthly_limit: float = Field(..., gt=0)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Lowercase, strip, and reject unknown categories."""
        v = v.lower().strip()
        if v not in CATEGORIES:
            raise ValueError(f"Unknown category: {v!r}. Choose from {', '.join(CATEGORIES)}")
        return v

class Receipt(BaseModel):
    """Represents the structured data of a financial receipt."""
    merchant: str
    purchase_date: date | None = None
    currency: str = "USD"
    subtotal: float | None = None
    tax: float | None = None
    total: float
    category: str = "other"
    items: list[LineItem] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Lowercase, strip, and validate category."""
        v = v.lower().strip()
        return v if v in CATEGORIES else "other"

    def arithmetic_warnings(self) -> list[str]:
        """Return warnings if subtotal or total calculations are inconsistent."""
        warnings = []
        if self.subtotal is not None and self.items:
            item_sum = sum(item.total_price for item in self.items)
            if abs(item_sum - self.subtotal) > 0.05:
                warnings.append(f"Item sum ({item_sum:.2f}) differs from subtotal ({self.subtotal:.2f}) by more than 0.05")
        
        if self.subtotal is not None and self.tax is not None:
            if abs((self.subtotal + self.tax) - self.total) > 0.05:
                warnings.append(f"Subtotal + Tax ({self.subtotal + self.tax:.2f}) differs from total ({self.total:.2f}) by more than 0.05")
        
        return warnings

    def date_warnings(self, today: date | None = None) -> list[str]:
        """Return warnings if the purchase date is missing or implausible.

        Receipts print dates in many orders (26/11/16 can be 2026-11-16 or
        2016-11-26), so a date in the future or over a year old is most
        likely a misread. A missing date also matters: the receipt won't
        count toward any month's budget.
        """
        today = today or date.today()
        if self.purchase_date is None:
            return ["No purchase date found; it won't count toward a month's budget"]
        if self.purchase_date > today:
            return [f"Purchase date {self.purchase_date.isoformat()} is in the future"]
        if (today - self.purchase_date).days > 365:
            return [f"Purchase date {self.purchase_date.isoformat()} is more than a year ago"]
        return []

    def review_warnings(self, today: date | None = None) -> list[str]:
        """Every reason a person should check this receipt before saving it."""
        return self.arithmetic_warnings() + self.date_warnings(today)

class Goal(BaseModel):
    """Represents a savings goal."""
    name: str = Field(..., min_length=1)
    target_amount: float = Field(..., gt=0)
    saved_amount: float = Field(default=0.0, ge=0.0)
    target_date: date | None = None
    description: str | None = Field(default=None, max_length=120)
    icon: str | None = Field(default=None, max_length=30)

    def progress_pct(self) -> float:
        """Return the percentage of the goal completed, capped at 100.0."""
        if self.target_amount == 0:
            return 0.0
        progress = (self.saved_amount / self.target_amount) * 100
        return round(min(progress, 100.0), 1)


class Transaction(BaseModel):
    """A manually entered expense or income (anything not scanned from a receipt).

    Expenses need a known category and count toward spending and budgets.
    Income is always stored with the category "income".
    """
    kind: Literal["expense", "income"]
    amount: float = Field(..., gt=0)
    category: str = "other"
    description: str | None = Field(default=None, max_length=200)
    txn_date: date = Field(default_factory=date.today)

    @model_validator(mode="after")
    def check_category(self) -> "Transaction":
        if self.kind == "income":
            self.category = "income"
            return self
        self.category = self.category.lower().strip()
        if self.category not in CATEGORIES:
            raise ValueError(
                f"Unknown category: {self.category!r}. Choose from {', '.join(CATEGORIES)}"
            )
        return self
