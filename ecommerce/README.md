# ShopKart — E-Commerce Web Application

A fully functional, modern E-Commerce web app built with **Flask**, **Bootstrap 5**, and **SQLite**.

---

## Features

- User registration & secure login (Werkzeug password hashing)
- Product catalog with search & category filtering
- Product detail pages with quantity selector
- Shopping cart with live quantity updates
- Checkout, stock deduction, and order confirmation
- Buyer order history with status tracking
- Admin dashboard: stats, product CRUD, order status management
- Pre-seeded admin account + 8 sample products

---

## Project Structure

```
ecommerce/
├── app.py              # Flask routes & business logic
├── database.py         # DB init, seeding, connection helper
├── requirements.txt    # Python dependencies
├── database.db         # SQLite DB (auto-created on first run)
├── static/
│   ├── css/custom.css  # Custom styles (CSS variables + Bootstrap overrides)
│   └── js/main.js      # Frontend JS (alerts, qty controls, cart totals)
└── templates/
    ├── base.html                    # Base layout + navbar
    ├── index.html                   # Product catalog / home
    ├── auth/
    │   ├── login.html
    │   └── register.html
    ├── buyer/
    │   ├── product_detail.html
    │   ├── cart.html
    │   ├── checkout_success.html
    │   └── orders.html
    └── admin/
        ├── dashboard.html
        ├── products.html
        ├── product_form.html        # Used for both Add and Edit
        └── orders.html
```

---

## Setup Instructions

### 1. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
python app.py
```

The database is **auto-initialized** on first run — no separate migration step needed.

Open your browser: **http://127.0.0.1:5000**

---

## Default Accounts

| Role  | Username | Password        | Notes                        |
|-------|----------|-----------------|------------------------------|
| Admin | `admin`  | `adminpassword` | Pre-seeded at startup        |
| Buyer | —        | —               | Register a new account       |

---

## Tech Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Backend   | Python 3, Flask 3, Flask-Login      |
| Database  | SQLite via `sqlite3` stdlib module  |
| Frontend  | Bootstrap 5.3, Bootstrap Icons      |
| Styling   | Custom CSS with CSS custom properties |
| JS        | Vanilla JavaScript                  |
