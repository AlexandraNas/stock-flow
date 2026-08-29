"""
StockFlow — a small beauty retail inventory & stock management system.

Flask REST API + a vanilla HTML/CSS/JS front-end served from /static.
Run with: python app.py   (see README.md for setup)
"""

import os
import sqlite3
from functools import wraps

from flask import Flask, jsonify, request, session, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

import database

app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = os.environ.get("STOCKFLOW_SECRET_KEY", "dev-secret-key-change-in-production")

VALID_REASONS = {"delivery", "sale", "damaged", "correction", "return"}


# ---------------------------------------------------------------- helpers --

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Login required."}), 401
        return view(*args, **kwargs)
    return wrapped


def manager_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Login required."}), 401
        if session.get("role") != "manager":
            return jsonify({"error": "Manager access required."}), 403
        return view(*args, **kwargs)
    return wrapped


def current_user_dict():
    return {
        "id": session["user_id"],
        "username": session["username"],
        "full_name": session["full_name"],
        "role": session["role"],
    }


def row_to_dict(row):
    return dict(row) if row is not None else None


# --------------------------------------------------------------- frontend --

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# -------------------------------------------------------------------- auth --

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    conn = database.get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid username or password."}), 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["full_name"] = user["full_name"]
    session["role"] = user["role"]

    return jsonify({"user": current_user_dict()})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/me")
def me():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in."}), 401
    return jsonify({"user": current_user_dict()})


# ---------------------------------------------------------------- products --

@app.route("/api/categories", methods=["GET"])
@login_required
def list_categories():
    conn = database.get_connection()
    rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return jsonify({"categories": [row_to_dict(r) for r in rows]})


@app.route("/api/categories", methods=["POST"])
@manager_required
def create_category():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Category name is required."}), 400

    conn = database.get_connection()
    try:
        cur = conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "A category with that name already exists."}), 409
    conn.close()
    return jsonify({"id": new_id, "name": name}), 201


def _product_query():
    return """
        SELECT p.*, c.name AS category_name,
               CASE WHEN p.current_stock <= p.reorder_threshold THEN 1 ELSE 0 END AS low_stock
        FROM products p
        JOIN categories c ON c.id = p.category_id
    """


@app.route("/api/products", methods=["GET"])
@login_required
def list_products():
    conn = database.get_connection()
    rows = conn.execute(_product_query() + " ORDER BY p.name").fetchall()
    conn.close()
    return jsonify({"products": [row_to_dict(r) for r in rows]})


@app.route("/api/products/<int:product_id>", methods=["GET"])
@login_required
def get_product(product_id):
    conn = database.get_connection()
    row = conn.execute(_product_query() + " WHERE p.id = ?", (product_id,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Product not found."}), 404
    return jsonify({"product": row_to_dict(row)})


@app.route("/api/products", methods=["POST"])
@manager_required
def create_product():
    data = request.get_json(silent=True) or {}
    sku = (data.get("sku") or "").strip()
    name = (data.get("name") or "").strip()
    category_id = data.get("category_id")
    price = data.get("price")
    current_stock = data.get("current_stock", 0)
    reorder_threshold = data.get("reorder_threshold", 5)

    if not sku or not name or category_id is None or price is None:
        return jsonify({"error": "sku, name, category_id and price are required."}), 400
    try:
        price = float(price)
        current_stock = int(current_stock)
        reorder_threshold = int(reorder_threshold)
        if price < 0 or current_stock < 0 or reorder_threshold < 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "price, current_stock and reorder_threshold must be non-negative numbers."}), 400

    conn = database.get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO products (sku, name, category_id, price, current_stock, reorder_threshold)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sku, name, category_id, price, current_stock, reorder_threshold),
        )
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "A product with that SKU already exists."}), 409
    conn.close()
    return jsonify({"id": new_id}), 201


@app.route("/api/products/<int:product_id>", methods=["PUT"])
@manager_required
def update_product(product_id):
    data = request.get_json(silent=True) or {}
    fields = {}
    for key in ("sku", "name", "category_id", "price", "reorder_threshold"):
        if key in data:
            fields[key] = data[key]

    if not fields:
        return jsonify({"error": "No fields to update."}), 400

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [product_id]

    conn = database.get_connection()
    existing = conn.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Product not found."}), 404

    conn.execute(f"UPDATE products SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
@manager_required
def delete_product(product_id):
    conn = database.get_connection()
    existing = conn.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Product not found."}), 404

    conn.execute("DELETE FROM stock_movements WHERE product_id = ?", (product_id,))
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# --------------------------------------------------------- stock movements --

@app.route("/api/stock-movements", methods=["GET"])
@login_required
def list_stock_movements():
    limit = request.args.get("limit", default=50, type=int)
    limit = max(1, min(limit, 200))
    conn = database.get_connection()
    rows = conn.execute(
        """SELECT m.*, p.name AS product_name, p.sku, u.full_name AS user_name
           FROM stock_movements m
           JOIN products p ON p.id = m.product_id
           JOIN users u ON u.id = m.user_id
           ORDER BY m.created_at DESC, m.id DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return jsonify({"movements": [row_to_dict(r) for r in rows]})


@app.route("/api/stock-movements", methods=["POST"])
@login_required
def create_stock_movement():
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    movement_type = data.get("movement_type")
    quantity = data.get("quantity")
    reason = data.get("reason")
    note = (data.get("note") or "").strip() or None

    if product_id is None or movement_type not in ("IN", "OUT") or reason not in VALID_REASONS:
        return jsonify({"error": "product_id, a valid movement_type (IN/OUT) and reason are required."}), 400
    try:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "quantity must be a positive whole number."}), 400

    conn = database.get_connection()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        conn.close()
        return jsonify({"error": "Product not found."}), 404

    if movement_type == "OUT" and quantity > product["current_stock"]:
        conn.close()
        return jsonify({
            "error": f"Not enough stock: {product['name']} only has {product['current_stock']} units."
        }), 400

    delta = quantity if movement_type == "IN" else -quantity
    try:
        conn.execute(
            "UPDATE products SET current_stock = current_stock + ? WHERE id = ?",
            (delta, product_id),
        )
        cur = conn.execute(
            """INSERT INTO stock_movements (product_id, user_id, movement_type, quantity, reason, note)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (product_id, session["user_id"], movement_type, quantity, reason, note),
        )
        conn.commit()
        movement_id = cur.lastrowid
    except Exception as exc:
        conn.rollback()
        conn.close()
        return jsonify({"error": f"Could not log movement: {exc}"}), 500

    conn.close()
    return jsonify({"id": movement_id}), 201


# --------------------------------------------------------------- dashboard --

@app.route("/api/dashboard", methods=["GET"])
@login_required
def dashboard():
    conn = database.get_connection()

    totals = conn.execute(
        """SELECT COUNT(*) AS product_count,
                  COALESCE(SUM(current_stock * price), 0) AS stock_value,
                  COALESCE(SUM(current_stock), 0) AS total_units
           FROM products"""
    ).fetchone()

    low_stock = conn.execute(
        _product_query() + " WHERE p.current_stock <= p.reorder_threshold ORDER BY p.current_stock ASC"
    ).fetchall()

    recent = conn.execute(
        """SELECT m.*, p.name AS product_name, u.full_name AS user_name
           FROM stock_movements m
           JOIN products p ON p.id = m.product_id
           JOIN users u ON u.id = m.user_id
           ORDER BY m.created_at DESC, m.id DESC
           LIMIT 8"""
    ).fetchall()

    conn.close()
    return jsonify({
        "product_count": totals["product_count"],
        "stock_value": round(totals["stock_value"], 2),
        "total_units": totals["total_units"],
        "low_stock": [row_to_dict(r) for r in low_stock],
        "recent_activity": [row_to_dict(r) for r in recent],
    })


@app.route("/api/reports/top-products", methods=["GET"])
@login_required
def top_products():
    limit = request.args.get("limit", default=5, type=int)
    limit = max(1, min(limit, 50))
    conn = database.get_connection()
    rows = conn.execute(
        """SELECT p.id, p.name, p.sku, SUM(m.quantity) AS units_sold,
                  ROUND(SUM(m.quantity * p.price), 2) AS revenue
           FROM stock_movements m
           JOIN products p ON p.id = m.product_id
           WHERE m.movement_type = 'OUT' AND m.reason = 'sale'
           GROUP BY p.id
           ORDER BY units_sold DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return jsonify({"top_products": [row_to_dict(r) for r in rows]})


# ----------------------------------------------------------------- users --

@app.route("/api/users", methods=["GET"])
@manager_required
def list_users():
    conn = database.get_connection()
    rows = conn.execute(
        "SELECT id, username, full_name, role, created_at FROM users ORDER BY full_name"
    ).fetchall()
    conn.close()
    return jsonify({"users": [row_to_dict(r) for r in rows]})


@app.route("/api/users", methods=["POST"])
@manager_required
def create_user():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()
    role = data.get("role")

    if not username or not password or not full_name or role not in ("manager", "sales_assistant"):
        return jsonify({"error": "username, password, full_name and a valid role are required."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400

    conn = database.get_connection()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing is not None:
        conn.close()
        return jsonify({"error": "That username is already taken."}), 409

    cur = conn.execute(
        "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
        (username, generate_password_hash(password), full_name, role),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"id": new_id}), 201


if __name__ == "__main__":
    is_new = database.init_db()
    running_on_host = "PORT" in os.environ  # set by Render/Railway/etc, not present locally
    if is_new:
        print("Created a fresh stockflow.db.")
        if running_on_host:
            # No terminal access to run `python seed.py` by hand on a hosting
            # platform, so seed the demo data automatically on first boot.
            import seed
            seed.run()
            print("Auto-seeded demo data for the live deployment.")
        else:
            print("Run `python seed.py` to add demo data.")
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=not running_on_host)
