"""
Database connection layer for StockFlow.

Ships configured for SQLite so the app runs anywhere with zero setup
(no server to install). See README.md -> "Switching to MySQL" if you'd
rather point it at MySQL for parity with the NHS Trust Database project;
schema_mysql.sql has the matching schema.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "stockflow.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the database file and tables if they don't exist yet."""
    is_new = not DB_PATH.exists()
    conn = get_connection()
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    return is_new
