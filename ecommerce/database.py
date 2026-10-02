import sqlite3
import os
from flask import g
from werkzeug.security import generate_password_hash

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

def get_db():
    """Return the per-request DB connection, creating it if needed."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")   # allows concurrent reads + writes
    return g.db

def close_db(e=None):
    """Close the DB connection at the end of each request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'buyer',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        stock INTEGER NOT NULL DEFAULT 0,
        image_url TEXT,
        category TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        total_amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price_at_purchase REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')

    # Seed admin user
    admin = c.execute("SELECT id FROM users WHERE username='Redjan'").fetchone()
    if not admin:
        c.execute("INSERT INTO users (username, email, password_hash, role) VALUES (?,?,?,?)",
                  ('Redjan', 'redjan@rpsv.com', generate_password_hash('Redjan09'), 'admin'))

    # Seed sample products
    count = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        products = [
            ('Wireless Headphones',
             'Premium noise-cancelling wireless headphones with 30-hour battery life, deep bass, and crystal-clear highs. Foldable design with memory foam ear cushions.',
             79.99, 50,
             'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80',
             'Electronics'),
            ('Running Shoes',
             'Lightweight and breathable running shoes engineered for all terrains. Responsive foam midsole and durable rubber outsole for maximum performance.',
             59.99, 30,
             'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80',
             'Footwear'),
            ('Espresso Coffee Maker',
             'Barista-grade espresso machine with 15-bar pressure pump, built-in milk frother, and programmable settings for the perfect cup every time.',
             149.99, 25,
             'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=600&q=80',
             'Kitchen'),
            ('Mechanical Keyboard',
             'RGB backlit mechanical keyboard with tactile brown switches, per-key lighting, full N-key rollover, and durable aluminum frame.',
             89.99, 40,
             'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&q=80',
             'Electronics'),
            ('Yoga Mat',
             'Non-slip eco-friendly natural rubber yoga mat, 6mm thick with alignment lines. Antimicrobial surface, perfect for yoga, pilates, and stretching.',
             29.99, 60,
             'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=600&q=80',
             'Sports'),
            ('Leather Bifold Wallet',
             'Slim genuine full-grain leather bifold wallet with RFID blocking technology. 6 card slots, 2 bill compartments. Handcrafted in Italy.',
             34.99, 80,
             'https://images.unsplash.com/photo-1627123424574-724758594e93?w=600&q=80',
             'Accessories'),
            ('Insulated Water Bottle',
             'Vacuum insulated stainless steel 32oz water bottle. Keeps drinks cold 24 hours, hot 12 hours. Leak-proof lid, BPA-free.',
             24.99, 100,
             'https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&q=80',
             'Kitchen'),
            ('Polarized Sunglasses',
             'UV400 polarized sunglasses with lightweight titanium frame. Scratch-resistant lenses reduce glare. Includes hard case and microfiber cloth.',
             44.99, 35,
             'https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=600&q=80',
             'Accessories'),
            ('Smart Watch',
             'Feature-packed smartwatch with health tracking, GPS, heart rate monitor, sleep analysis, and 7-day battery life. Water resistant 50m.',
             199.99, 20,
             'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&q=80',
             'Electronics'),
            ('Denim Jacket',
             'Classic slim-fit denim jacket in premium stonewashed fabric. Timeless design with chest pockets and adjustable waist. Available in multiple washes.',
             69.99, 45,
             'https://images.unsplash.com/photo-1551537482-f2075a1d41f2?w=600&q=80',
             'Clothing'),
            ('Backpack',
             'Durable 30L travel backpack with laptop compartment (fits up to 17"), padded shoulder straps, USB charging port, and waterproof base.',
             54.99, 55,
             'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&q=80',
             'Accessories'),
            ('Basketball',
             'Official size and weight indoor/outdoor basketball with deep channel design for better grip. Composite leather cover, butyl rubber bladder.',
             39.99, 30,
             'https://images.unsplash.com/photo-1546519638405-a9f9c6d84b67?w=600&q=80',
             'Sports'),
        ]
        c.executemany("INSERT INTO products (name, description, price, stock, image_url, category) VALUES (?,?,?,?,?,?)", products)

    conn.commit()
    conn.close()
