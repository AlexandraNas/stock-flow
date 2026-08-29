# StockFlow

A full-stack inventory & stock management system built for a small beauty retail business — tracking product catalogues, stock levels, staff-logged stock movements (deliveries, sales, damages, returns), low-stock alerts, and top-seller reporting.

Built with a Python/Flask REST API on the back end and vanilla HTML/CSS/JS on the front end, with role-based access control for **Manager** and **Sales Assistant** accounts — the same RBAC pattern used in my [NHS Patient Database](../nhs-patient-database) project.

## Features

- **Authentication** — cookie-based session login, passwords hashed with Werkzeug's `generate_password_hash`.
- **Role-based access control** — Managers can add/edit/delete products, manage staff accounts, and view all data. Sales Assistants can view products, log stock movements, and view reports, but can't touch staff accounts or delete products. Enforced both in the UI (manager-only controls hidden) and on the server (protected routes return `403` for the wrong role).
- **Product catalogue** — SKU, name, category, price, current stock, reorder threshold.
- **Stock movements** — every stock in/out is logged with type, quantity, reason, note, timestamp, and the staff member who logged it. Stock levels update automatically and atomically with each movement.
- **Dashboard** — live stats (products tracked, total stock value, units in stock, low-stock alerts), a low-stock panel, and a recent-activity feed.
- **Reports** — top-selling products by units sold and revenue.
- **Staff management** (Manager only) — add new staff accounts and assign roles.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3 + Flask |
| Database | SQLite (zero-install, file-based) — see below for switching to MySQL |
| Frontend | HTML, CSS, vanilla JavaScript (`fetch` API) |
| Auth | Flask sessions + Werkzeug password hashing |

## Getting started

**Requirements:** Python 3.9+ and `pip`.

1. Install Flask:
   ```bash
   pip install flask
   ```

2. Seed the demo database (creates `stockflow.db` with sample categories, products, staff accounts, and ~5 weeks of stock movement history):
   ```bash
   python seed.py
   ```

3. Run the app:
   ```bash
   python app.py
   ```

4. Open **http://localhost:5050** in your browser.

### Demo logins

| Role | Username | Password |
|---|---|---|
| Manager | `a.nastase` | `Manager123!` |
| Sales Assistant | `j.smith` | `SalesFloor1!` |

Re-run `python seed.py` any time to reset the demo data — it wipes and rebuilds it safely.

## Project structure

```
stockflow/
├── app.py                # Flask app + REST API routes
├── database.py            # SQLite connection helpers
├── schema.sql              # SQLite schema (users, categories, products, stock_movements)
├── schema_mysql.sql        # Equivalent MySQL schema, for production/deployment
├── seed.py                 # Demo data seeder
└── static/
    ├── index.html
    ├── css/style.css
    └── js/
        ├── api.js          # fetch() wrapper for the API
        └── app.js           # front-end app logic (views, forms, RBAC UI)
```

## API overview

All routes except `/api/login` require an active session.

| Method | Route | Description | Manager only |
|---|---|---|---|
| POST | `/api/login` | Log in | |
| POST | `/api/logout` | Log out | |
| GET | `/api/me` | Current user info | |
| GET | `/api/dashboard` | Dashboard stats | |
| GET | `/api/products` | List products | |
| POST | `/api/products` | Create product | ✅ |
| PUT | `/api/products/<id>` | Update product | ✅ |
| DELETE | `/api/products/<id>` | Delete product | ✅ |
| GET | `/api/categories` | List categories | |
| GET | `/api/movements` | List recent stock movements | |
| POST | `/api/movements` | Log a stock movement | |
| GET | `/api/reports/top-products` | Top-selling products | |
| GET | `/api/users` | List staff | ✅ |
| POST | `/api/users` | Add staff account | ✅ |

## Switching to MySQL

The app runs on SQLite by default so it works out of the box with no setup. `schema_mysql.sql` is a ready-to-use MySQL 8.0+ equivalent of the schema, for anyone who wants to deploy this against a real MySQL server (e.g. alongside the NHS project's database):

```bash
mysql -u <user> -p < schema_mysql.sql
```

Swapping the backend to MySQL would mean replacing the `sqlite3` calls in `database.py` with a MySQL driver (e.g. `PyMySQL` or `mysql-connector-python`) and updating the connection string — the rest of the app (routes, front end) doesn't need to change, since the queries are standard SQL.

## Why this project

Built to round out my portfolio alongside the NHS Patient Database (SQL/RBAC) and Beauty E-Commerce (front-end) projects, this one demonstrates a full-stack Python/Flask API with a real database behind it — end to end, from schema design to a working UI, themed around the same beauty retail space as my e-commerce project.
