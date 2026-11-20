"""Shared schemas: the contract between the vision agent, database and reasoning agent."""

from datetime import date

from pydantic import BaseModel, Field

CATEGORIES = [
    "groceries",
    "dining",
    "transport",
    "utilities",
    "housing",
    "health",
    "entertainment",
    "shopping",
    "education",
    "other",
]


class LineItem(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float | None = None
    total_price: float
    category: str = "other"


class Receipt(BaseModel):
    merchant: str
    purchase_date: date | None = None
    currency: str = Field(default="USD", description="ISO 4217 code")
    subtotal: float | None = None
    tax: float | None = None
    total: float
    category: str = "other"
    items: list[LineItem] = Field(default_factory=list)
    confidence: float = Field(
        default=1.0, ge=0, le=1, description="Model's self-reported confidence"
    )
