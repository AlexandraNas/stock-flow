-- StockFlow schema (SQLite)
-- Run automatically by database.py on first startup if stockflow.db doesn't exist.
-- See schema_mysql.sql for the MySQL-flavoured equivalent.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('manager', 'sales_assistant')),
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    sku                TEXT NOT NULL UNIQUE,
    name               TEXT NOT NULL,
    category_id        INTEGER NOT NULL,
    price              REAL NOT NULL CHECK (price >= 0),
    current_stock      INTEGER NOT NULL DEFAULT 0 CHECK (current_stock >= 0),
    reorder_threshold  INTEGER NOT NULL DEFAULT 5 CHECK (reorder_threshold >= 0),
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id     INTEGER NOT NULL,
    user_id        INTEGER NOT NULL,
    movement_type  TEXT NOT NULL CHECK (movement_type IN ('IN', 'OUT')),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    reason         TEXT NOT NULL CHECK (reason IN ('delivery', 'sale', 'damaged', 'correction', 'return')),
    note           TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_movements_product ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_movements_created ON stock_movements(created_at);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
