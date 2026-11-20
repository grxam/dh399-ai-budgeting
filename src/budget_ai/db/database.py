"""SQLite storage for receipts and line items."""

import sqlite3
from pathlib import Path

from budget_ai.models import Receipt

SCHEMA = """
CREATE TABLE IF NOT EXISTS receipts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    merchant      TEXT NOT NULL,
    purchase_date TEXT,
    currency      TEXT NOT NULL,
    subtotal      REAL,
    tax           REAL,
    total         REAL NOT NULL,
    category      TEXT NOT NULL,
    confidence    REAL NOT NULL,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS line_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id  INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantity    REAL NOT NULL,
    unit_price  REAL,
    total_price REAL NOT NULL,
    category    TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path | str = "data/budget.db"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    def save_receipt(self, receipt: Receipt) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO receipts (merchant, purchase_date, currency, subtotal, tax, total,"
                " category, confidence) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    receipt.merchant,
                    receipt.purchase_date.isoformat() if receipt.purchase_date else None,
                    receipt.currency,
                    receipt.subtotal,
                    receipt.tax,
                    receipt.total,
                    receipt.category,
                    receipt.confidence,
                ),
            )
            receipt_id = cur.lastrowid
            self.conn.executemany(
                "INSERT INTO line_items (receipt_id, description, quantity, unit_price,"
                " total_price, category) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (receipt_id, i.description, i.quantity, i.unit_price, i.total_price, i.category)
                    for i in receipt.items
                ],
            )
        return receipt_id

    def recent_receipts(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM receipts ORDER BY COALESCE(purchase_date, created_at) DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def spending_by_category(self) -> dict[str, float]:
        rows = self.conn.execute(
            "SELECT category, ROUND(SUM(total), 2) AS spent FROM receipts"
            " GROUP BY category ORDER BY spent DESC"
        ).fetchall()
        return {r["category"]: r["spent"] for r in rows}

    def close(self) -> None:
        self.conn.close()
