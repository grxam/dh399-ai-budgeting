import os
import sqlite3

from budget_ai.models import Receipt


class Database:
    """Handles SQLite operations for receipts and line items."""
    def __init__(self, db_path: str = ":memory:"):
        """Initialize the connection and create tables."""
        if db_path != ":memory:":
            folder = os.path.dirname(db_path)
            if folder:
                os.makedirs(folder, exist_ok=True)
        
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        """Create the schema for receipts and line_items."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant TEXT,
                purchase_date TEXT,
                currency TEXT,
                subtotal REAL,
                tax REAL,
                total REAL,
                category TEXT,
                confidence REAL NOT NULL DEFAULT 1.0
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS line_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id INTEGER,
                description TEXT,
                quantity REAL,
                unit_price REAL,
                total_price REAL,
                category TEXT,
                FOREIGN KEY(receipt_id) REFERENCES receipts(id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def save_receipt(self, receipt: Receipt) -> int:
        """Save a receipt and its items to the database in a transaction."""
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO receipts (merchant, purchase_date, currency, subtotal, tax, total, category, confidence) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (receipt.merchant, receipt.purchase_date.isoformat() if receipt.purchase_date else None,
                 receipt.currency, receipt.subtotal, receipt.tax, receipt.total, receipt.category, receipt.confidence)
            )
            receipt_id = cursor.lastrowid
            
            for item in receipt.items:
                cursor.execute(
                    """INSERT INTO line_items (receipt_id, description, quantity, unit_price, total_price, category) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (receipt_id, item.description, item.quantity, item.unit_price, item.total_price, item.category)
                )
            return receipt_id

    def recent_receipts(self, limit: int = 50) -> list[dict]:
        """Get the most recent receipts."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM receipts ORDER BY purchase_date DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def spending_by_category(self) -> dict[str, float]:
        """Sum total spending grouped by category from receipts, sorted and rounded."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT category, SUM(total) as total_sum FROM receipts GROUP BY category")
        rows = cursor.fetchall()
        totals = {row['category']: round(row['total_sum'], 2) for row in rows}
        return dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
