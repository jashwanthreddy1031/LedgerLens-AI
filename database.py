"""
database.py - Database operations for LedgerLens AI.
Handles SQLite database persistence, transaction management, and summaries.
"""

from decimal import Decimal, ROUND_HALF_UP
import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ledgerlens.database")

DB_PATH = Path(__file__).resolve().parent / "ledgerlens.db"


def get_connection() -> sqlite3.Connection:
    """Return a thread-safe SQLite connection with Row factory."""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_database() -> None:
    """Initialize SQLite database tables if they do not exist."""
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL NOT NULL CHECK(amount > 0),
                    description TEXT
                )
                """
            )
    finally:
        conn.close()


def add_transaction(
    date: str,
    type_: str,
    category: str,
    amount: float,
    description: str = "",
) -> int:
    """
    Insert a new transaction record.
    Returns the newly created row ID.
    """
    cleaned_desc = description.strip() if description else ""
    cleaned_cat = category.strip()
    cleaned_type = type_.strip().capitalize()
    
    # Store with 2 decimal precision
    dec_amount = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    float_amount = float(dec_amount)
    
    if float_amount <= 0:
        raise ValueError("Transaction amount must be strictly greater than zero.")

    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO transactions (date, type, category, amount, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                (date, cleaned_type, cleaned_cat, float_amount, cleaned_desc),
            )
            return cursor.lastrowid or 0
    finally:
        conn.close()


def get_transactions() -> List[Dict[str, Any]]:
    """Retrieve all transactions ordered by date and id descending."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, date, type, category, amount, description
            FROM transactions
            ORDER BY date DESC, id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_transaction_by_id(transaction_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single transaction by its primary key ID."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, date, type, category, amount, description
            FROM transactions
            WHERE id = ?
            """,
            (transaction_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_transaction(
    id_: int,
    date: str,
    type_: str,
    category: str,
    amount: float,
    description: str = "",
) -> bool:
    """Update an existing transaction record by ID."""
    cleaned_desc = description.strip() if description else ""
    cleaned_cat = category.strip()
    cleaned_type = type_.strip().capitalize()
    dec_amount = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    float_amount = float(dec_amount)

    if float_amount <= 0:
        raise ValueError("Transaction amount must be strictly greater than zero.")

    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                """
                UPDATE transactions
                SET date = ?, type = ?, category = ?, amount = ?, description = ?
                WHERE id = ?
                """,
                (date, cleaned_type, cleaned_cat, float_amount, cleaned_desc, id_),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def delete_transaction(id_: int) -> bool:
    """Delete a transaction record by ID."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute("DELETE FROM transactions WHERE id = ?", (id_,))
            return cursor.rowcount > 0
    finally:
        conn.close()


def get_summary() -> Dict[str, float]:
    """Calculate overall total income, total expenses, and net balance."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN type = 'Income' THEN amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN type = 'Expense' THEN amount ELSE 0 END), 0) AS expenses
            FROM transactions
            """
        ).fetchone()

        income = Decimal(str(row["income"] or 0))
        expenses = Decimal(str(row["expenses"] or 0))
        balance = income - expenses

        return {
            "income": float(income),
            "expenses": float(expenses),
            "balance": float(balance),
        }
    finally:
        conn.close()


def get_database_info() -> Dict[str, Any]:
    """Return database diagnostic information."""
    size_bytes = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        return {
            "path": str(DB_PATH),
            "size_kb": round(size_bytes / 1024, 2),
            "total_transactions": count,
        }
    finally:
        conn.close()


# Automatically ensure tables exist on module import
create_database()
