import os
import sqlite3

from datetime import date

from budget_ai.models import Budget, Goal, Receipt, Transaction

# Every expense, whether scanned (receipts) or entered by hand (transactions),
# as rows of (d, category, amount). Spending and budget figures read from this.
EXPENSES_SQL = (
    "SELECT purchase_date AS d, category, total AS amount FROM receipts "
    "UNION ALL "
    "SELECT txn_date AS d, category, amount FROM transactions WHERE kind = 'expense'"
)


class Database:
    """Handles SQLite operations for receipts and line items."""
    def __init__(self, db_path: str = ":memory:"):
        """Initialize the connection and create tables."""
        if db_path != ":memory:":
            folder = os.path.dirname(db_path)
            if folder:
                os.makedirs(folder, exist_ok=True)
        
        # FastAPI opens this in one worker thread (the get_db dependency) and
        # runs the endpoint in another, so allow the connection to cross
        # threads. Each request gets its own Database and uses it one step at
        # a time; never share one instance between concurrent threads.
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
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
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,
                monthly_limit REAL NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                saved_amount REAL NOT NULL DEFAULT 0,
                target_date TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK (kind IN ('expense', 'income')),
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                txn_date TEXT NOT NULL
            )
        """)
        # Columns added after the first release; older databases lack them.
        self._add_column_if_missing("goals", "description", "TEXT")
        self._add_column_if_missing("goals", "icon", "TEXT")
        self.conn.commit()

    def _add_column_if_missing(self, table: str, column: str, col_type: str) -> None:
        existing = {row["name"] for row in self.conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

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
        cursor.execute(
            f"SELECT category, SUM(amount) as total_sum FROM ({EXPENSES_SQL}) GROUP BY category"
        )
        rows = cursor.fetchall()
        totals = {row['category']: round(row['total_sum'], 2) for row in rows}
        return dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))

    def set_budget(self, budget: Budget) -> None:
        """Insert or replace a budget for a category."""
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO budgets (category, monthly_limit) VALUES (?, ?)",
                (budget.category, budget.monthly_limit)
            )

    def delete_budget(self, category: str) -> None:
        """Delete a budget for a category."""
        with self.conn:
            self.conn.execute("DELETE FROM budgets WHERE category = ?", (category,))

    def list_budgets(self) -> list[dict]:
        """List all budgets, sorted by category."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT category, monthly_limit FROM budgets ORDER BY category")
        return [dict(row) for row in cursor.fetchall()]

    def add_goal(self, goal: Goal) -> int:
        """Add a new goal and return its ID."""
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO goals (name, target_amount, saved_amount, target_date, description, icon) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (goal.name, goal.target_amount, goal.saved_amount,
                 goal.target_date.isoformat() if goal.target_date else None,
                 goal.description, goal.icon)
            )
            return cursor.lastrowid

    def list_goals(self) -> list[dict]:
        """List all goals, sorted by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, target_amount, saved_amount, target_date, description, icon "
            "FROM goals ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]

    def contribute_to_goal(self, goal_id: int, amount: float) -> None:
        """Add amount to a goal's saved_amount. Raise ValueError if goal doesn't exist or amount <= 0."""
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM goals WHERE id = ?", (goal_id,))
        if not cursor.fetchone():
            raise ValueError(f"Goal with ID {goal_id} does not exist")
        
        with self.conn:
            self.conn.execute(
                "UPDATE goals SET saved_amount = saved_amount + ? WHERE id = ?",
                (amount, goal_id)
            )

    def delete_goal(self, goal_id: int) -> None:
        """Delete a goal by ID."""
        with self.conn:
            self.conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))

    def spending_by_category_for_month(self, month: str) -> dict[str, float]:
        """Sum total spending grouped by category for a specific month (YYYY-MM)."""
        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT category, SUM(amount) as total_sum FROM ({EXPENSES_SQL}) "
            "WHERE d IS NOT NULL AND substr(d, 1, 7) = ? "
            "GROUP BY category",
            (month,),
        )
        rows = cursor.fetchall()
        totals = {row['category']: round(row['total_sum'], 2) for row in rows}
        return dict(totals)

    def list_receipts(self, limit: int = 100, offset: int = 0, category: str | None = None) -> list[dict]:
        """List receipts with optional category filter and pagination."""
        query = "SELECT * FROM receipts"
        params = []
        
        if category:
            query += " WHERE category = ?"
            params.append(category)
            
        query += " ORDER BY purchase_date DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = self.conn.cursor()
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def get_receipt_with_items(self, receipt_id: int) -> dict | None:
        """Get a receipt dictionary including its line items."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,))
        receipt_row = cursor.fetchone()
        if not receipt_row:
            return None
        
        receipt = dict(receipt_row)
        cursor.execute("SELECT * FROM line_items WHERE receipt_id = ?", (receipt_id,))
        items = [dict(row) for row in cursor.fetchall()]
        receipt["items"] = items
        return receipt

    def delete_receipt(self, receipt_id: int) -> bool:
        """Delete a receipt and its line items. Return False if it didn't exist."""
        with self.conn:
            cursor = self.conn.execute("DELETE FROM receipts WHERE id = ?", (receipt_id,))
        return cursor.rowcount > 0

    def update_receipt(self, receipt_id: int, receipt: Receipt) -> bool:
        """Replace a receipt's details and line items. Return False if it doesn't exist."""
        with self.conn:
            cursor = self.conn.execute(
                "UPDATE receipts SET merchant = ?, purchase_date = ?, currency = ?, subtotal = ?, "
                "tax = ?, total = ?, category = ?, confidence = ? WHERE id = ?",
                (receipt.merchant, receipt.purchase_date.isoformat() if receipt.purchase_date else None,
                 receipt.currency, receipt.subtotal, receipt.tax, receipt.total, receipt.category,
                 receipt.confidence, receipt_id),
            )
            if cursor.rowcount == 0:
                return False
            self.conn.execute("DELETE FROM line_items WHERE receipt_id = ?", (receipt_id,))
            for item in receipt.items:
                self.conn.execute(
                    "INSERT INTO line_items (receipt_id, description, quantity, unit_price, total_price, category) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (receipt_id, item.description, item.quantity, item.unit_price, item.total_price, item.category),
                )
        return True

    def add_transaction(self, txn: Transaction) -> int:
        """Save a manual expense or income and return its ID."""
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO transactions (kind, amount, category, description, txn_date) "
                "VALUES (?, ?, ?, ?, ?)",
                (txn.kind, txn.amount, txn.category, txn.description, txn.txn_date.isoformat()),
            )
        return cursor.lastrowid

    def update_transaction(self, txn_id: int, txn: Transaction) -> bool:
        """Replace a manual transaction's details. Return False if it doesn't exist."""
        with self.conn:
            cursor = self.conn.execute(
                "UPDATE transactions SET kind = ?, amount = ?, category = ?, description = ?, "
                "txn_date = ? WHERE id = ?",
                (txn.kind, txn.amount, txn.category, txn.description, txn.txn_date.isoformat(), txn_id),
            )
        return cursor.rowcount > 0

    def delete_transaction(self, txn_id: int) -> bool:
        """Delete a manual transaction. Return False if it didn't exist."""
        with self.conn:
            cursor = self.conn.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
        return cursor.rowcount > 0

    def list_activity(
        self,
        limit: int = 20,
        offset: int = 0,
        month: str | None = None,
        q: str | None = None,
        category: str | None = None,
        kind: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
    ) -> list[dict]:
        """Receipts and manual transactions together, newest first.

        Each row has source ("receipt" or "manual"), id, kind ("expense" or
        "income"), title, category, amount (always positive) and date.

        q searches the store or description and, for receipts, the line
        items (case-insensitive). The other arguments filter exactly; all
        given filters must match.
        """
        query = (
            "SELECT source, id, kind, title, category, amount, date FROM ("
            "SELECT 'receipt' AS source, id, 'expense' AS kind, merchant AS title, category, "
            "total AS amount, purchase_date AS date, "
            "(SELECT group_concat(description, ' ') FROM line_items WHERE receipt_id = receipts.id) "
            "AS items_text FROM receipts "
            "UNION ALL "
            "SELECT 'manual' AS source, id, kind, description AS title, category, "
            "amount, txn_date AS date, NULL AS items_text FROM transactions"
            ")"
        )
        where: list[str] = []
        params: list = []
        if month:
            where.append("substr(date, 1, 7) = ?")
            params.append(month)
        if q and q.strip():
            # Escape LIKE wildcards so "%" and "_" in the search are literal.
            escaped = q.strip().replace("!", "!!").replace("%", "!%").replace("_", "!_")
            pattern = f"%{escaped}%"
            where.append("(title LIKE ? ESCAPE '!' OR items_text LIKE ? ESCAPE '!')")
            params.extend([pattern, pattern])
        if category:
            where.append("category = ?")
            params.append(category)
        if kind:
            where.append("kind = ?")
            params.append(kind)
        if min_amount is not None:
            where.append("amount >= ?")
            params.append(min_amount)
        if max_amount is not None:
            where.append("amount <= ?")
            params.append(max_amount)
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY date IS NULL, date DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return [dict(row) for row in self.conn.execute(query, params).fetchall()]

    def spending_between(self, start: date, end: date) -> float:
        """Total spent from start to end, both inclusive."""
        row = self.conn.execute(
            f"SELECT SUM(amount) AS total FROM ({EXPENSES_SQL}) WHERE d BETWEEN ? AND ?",
            (start.isoformat(), end.isoformat()),
        ).fetchone()
        return round(row["total"] or 0.0, 2)

    def daily_spending(self, start: date, end: date) -> dict[str, float]:
        """Total spent per day (YYYY-MM-DD) from start to end; days with no spending are left out."""
        rows = self.conn.execute(
            f"SELECT d, SUM(amount) AS total FROM ({EXPENSES_SQL}) "
            "WHERE d BETWEEN ? AND ? GROUP BY d",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return {row["d"]: round(row["total"], 2) for row in rows}

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
