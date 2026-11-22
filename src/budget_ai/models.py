from datetime import date

from pydantic import BaseModel, Field, field_validator

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
