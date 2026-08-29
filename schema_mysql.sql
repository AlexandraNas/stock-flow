-- StockFlow schema (MySQL 8.0+)
-- Use this instead of schema.sql if you'd rather run StockFlow on MySQL,
-- for parity with the NHS Trust Database project. See README.md ("Switching
-- to MySQL") for the two lines of database.py you need to change to match.

CREATE DATABASE IF NOT EXISTS stockflow_db;
USE stockflow_db;

CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(100) NOT NULL,
    role          ENUM('manager', 'sales_assistant') NOT NULL,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS categories (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS products (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    sku                VARCHAR(30) NOT NULL UNIQUE,
    name               VARCHAR(150) NOT NULL,
    category_id        INT NOT NULL,
    price              DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    current_stock      INT NOT NULL DEFAULT 0 CHECK (current_stock >= 0),
    reorder_threshold  INT NOT NULL DEFAULT 5 CHECK (reorder_threshold >= 0),
    created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS stock_movements (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    product_id     INT NOT NULL,
    user_id        INT NOT NULL,
    movement_type  ENUM('IN', 'OUT') NOT NULL,
    quantity       INT NOT NULL CHECK (quantity > 0),
    reason         ENUM('delivery', 'sale', 'damaged', 'correction', 'return') NOT NULL,
    note           VARCHAR(255),
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE INDEX idx_movements_product ON stock_movements(product_id);
CREATE INDEX idx_movements_created ON stock_movements(created_at);
CREATE INDEX idx_products_category ON products(category_id);
