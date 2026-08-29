"""
Populates stockflow.db with realistic demo data: two staff accounts,
a small beauty & cosmetics retail catalogue, and a few weeks of stock
movement history so the dashboard and reports have something to show.

Run with: python seed.py
Safe to re-run — it wipes and rebuilds the demo data each time.
"""

import random
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

import database

random.seed(42)

CATEGORIES = ["Skincare", "Makeup", "Haircare", "Fragrance", "Tools & Accessories"]

PRODUCTS = [
    ("SKN-001", "Hydrating Facial Cleanser", "Skincare", 11.99, 6),
    ("SKN-002", "Vitamin C Brightening Serum", "Skincare", 18.99, 5),
    ("SKN-003", "SPF 50 Daily Moisturiser", "Skincare", 14.99, 6),
    ("SKN-004", "Clay Detox Face Mask", "Skincare", 9.99, 6),
    ("MUP-001", "Matte Liquid Foundation", "Makeup", 16.99, 5),
    ("MUP-002", "Volumising Mascara", "Makeup", 10.99, 8),
    ("MUP-003", "Velvet Matte Lipstick", "Makeup", 8.99, 8),
    ("MUP-004", "Eyeshadow Palette", "Makeup", 22.99, 4),
    ("HAI-001", "Argan Oil Shampoo", "Haircare", 9.99, 6),
    ("HAI-002", "Repair Conditioner", "Haircare", 9.99, 6),
    ("HAI-003", "Leave-In Hair Serum", "Haircare", 13.99, 5),
    ("FRA-001", "Eau de Parfum 50ml", "Fragrance", 39.99, 3),
    ("FRA-002", "Body Mist 100ml", "Fragrance", 12.99, 5),
    ("ACC-001", "Makeup Brush Set", "Tools & Accessories", 19.99, 4),
    ("ACC-002", "Beauty Blender Sponge", "Tools & Accessories", 6.99, 8),
]

USERS = [
    ("a.nastase", "Manager123!", "Alexandra Nastase", "manager"),
    ("j.smith", "SalesFloor1!", "Jamie Smith", "sales_assistant"),
]


def run():
    database.init_db()
    conn = database.get_connection()

    # wipe existing demo data (keep schema)
    conn.executescript(
        "DELETE FROM stock_movements; DELETE FROM products; "
        "DELETE FROM categories; DELETE FROM users;"
    )
    conn.commit()

    category_ids = {}
    for name in CATEGORIES:
        cur = conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        category_ids[name] = cur.lastrowid

    user_ids = {}
    for username, password, full_name, role in USERS:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            (username, generate_password_hash(password), full_name, role),
        )
        user_ids[username] = cur.lastrowid

    product_ids = {}
    for sku, name, category, price, threshold in PRODUCTS:
        starting_stock = random.randint(threshold, threshold * 5)
        cur = conn.execute(
            """INSERT INTO products (sku, name, category_id, price, current_stock, reorder_threshold)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sku, name, category_ids[category], price, starting_stock, threshold),
        )
        product_ids[sku] = cur.lastrowid
    conn.commit()

    # simulate ~5 weeks of movement history, ending "today"
    usernames = list(user_ids.keys())
    skus = list(product_ids.keys())
    now = datetime.now()
    movements = []

    for days_ago in range(35, 0, -1):
        day = now - timedelta(days=days_ago)
        for _ in range(random.randint(1, 4)):
            sku = random.choice(skus)
            product_id = product_ids[sku]
            username = random.choice(usernames)
            user_id = user_ids[username]
            hour = random.randint(8, 19)
            minute = random.randint(0, 59)
            ts = day.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if random.random() < 0.25:
                movement_type, reason, qty = "IN", "delivery", random.randint(5, 20)
            else:
                movement_type, reason, qty = "OUT", "sale", random.randint(1, 3)

            movements.append((product_id, user_id, movement_type, qty, reason, ts))

    # apply movements in chronological order, skipping any that would
    # take a product below zero (can happen with random data + low stock)
    movements.sort(key=lambda m: m[5])
    for product_id, user_id, movement_type, qty, reason, ts in movements:
        row = conn.execute(
            "SELECT current_stock FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if movement_type == "OUT" and qty > row["current_stock"]:
            continue
        delta = qty if movement_type == "IN" else -qty
        conn.execute(
            "UPDATE products SET current_stock = current_stock + ? WHERE id = ?",
            (delta, product_id),
        )
        conn.execute(
            """INSERT INTO stock_movements (product_id, user_id, movement_type, quantity, reason, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (product_id, user_id, movement_type, qty, reason, ts.strftime("%Y-%m-%d %H:%M:%S")),
        )

    conn.commit()
    conn.close()

    print("Seeded stockflow.db:")
    print(f"  {len(CATEGORIES)} categories, {len(PRODUCTS)} products, {len(USERS)} users")
    print(f"  ~{len(movements)} stock movements over the last 35 days")
    print()
    print("Demo logins:")
    for username, password, full_name, role in USERS:
        print(f"  {role:16s} {username:12s} / {password}")


if __name__ == "__main__":
    run()
