from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from database import get_db, close_db, init_db
import os
import uuid

app = Flask(__name__)

# Stable secret key — persisted to file so sessions survive server restarts
_SECRET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.secret_key')
if os.path.exists(_SECRET_FILE):
    with open(_SECRET_FILE, 'rb') as _f:
        app.secret_key = _f.read()
else:
    app.secret_key = os.urandom(32)
    with open(_SECRET_FILE, 'wb') as _f:
        _f.write(app.secret_key)

# Session config — ensures cookies work on phones over the local network
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False      # HTTP only (no HTTPS on local network)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
app.config['REMEMBER_COOKIE_SECURE'] = False

# Image upload config
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Automatically close the DB connection at the end of every request
app.teardown_appcontext(close_db)

# ─── User Model ────────────────────────────────────────────────────────────────

class User(UserMixin):
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if row:
        return User(row['id'], row['username'], row['email'], row['role'])
    return None

# ─── Decorators ────────────────────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

def buyer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login', next=request.url))
        if current_user.role != 'buyer':
            flash('This action requires a buyer account.', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ─── Public Routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        params += [f'%{search}%', f'%{search}%']
    if category:
        query += " AND category=?"
        params.append(category)
    query += " ORDER BY id DESC"
    products = db.execute(query, params).fetchall()
    categories = db.execute("SELECT DISTINCT category FROM products WHERE category != '' ORDER BY category").fetchall()
    return render_template('index.html', products=products, categories=categories,
                           search=search, selected_category=category)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        flash('Product not found.', 'warning')
        return redirect(url_for('index'))
    return render_template('buyer/product_detail.html', product=product)

# ─── Auth Routes ───────────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        confirm = request.form['confirm_password']
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('auth/register.html')
        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE username=? OR email=?", (username, email)).fetchone()
        if existing:
            flash('Username or email already exists.', 'danger')
            return render_template('auth/register.html')
        db.execute("INSERT INTO users (username, email, password_hash, role) VALUES (?,?,?,?)",
                   (username, email, generate_password_hash(password), 'buyer'))
        db.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        db = get_db()
        row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if row and check_password_hash(row['password_hash'], password):
            user = User(row['id'], row['username'], row['email'], row['role'])
            login_user(user, remember=True)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            if row['role'] == 'admin':
                return redirect(next_page or url_for('admin_dashboard'))
            return redirect(next_page or url_for('index'))
        flash('Invalid credentials.', 'danger')
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))

# ─── Cart Routes ───────────────────────────────────────────────────────────────

@app.route('/cart')
@login_required
@buyer_required
def cart():
    db = get_db()
    items = db.execute('''
        SELECT c.id as cart_id, c.quantity,
               p.id as product_id, p.name, p.price, p.image_url, p.stock
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', (current_user.id,)).fetchall()
    subtotal = sum(item['price'] * item['quantity'] for item in items)
    return render_template('buyer/cart.html', items=items, subtotal=subtotal)

@app.route('/cart/add', methods=['POST'])
@login_required
@buyer_required
def add_to_cart():
    try:
        product_id = int(request.form.get('product_id', 0))
        quantity = int(request.form.get('quantity', 1))
    except (ValueError, TypeError):
        flash('Invalid request.', 'danger')
        return redirect(url_for('index'))

    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('index'))
    if product['stock'] < quantity:
        flash('Not enough stock available.', 'danger')
        return redirect(request.referrer or url_for('index'))

    existing = db.execute(
        "SELECT * FROM cart WHERE user_id=? AND product_id=?",
        (current_user.id, product_id)
    ).fetchone()

    if existing:
        new_qty = existing['quantity'] + quantity
        if new_qty > product['stock']:
            flash('Not enough stock for the total quantity requested.', 'danger')
            return redirect(request.referrer or url_for('index'))
        db.execute("UPDATE cart SET quantity=? WHERE id=?", (new_qty, existing['id']))
    else:
        db.execute(
            "INSERT INTO cart (user_id, product_id, quantity) VALUES (?,?,?)",
            (current_user.id, product_id, quantity)
        )
    db.commit()
    flash(f'"{product["name"]}" added to cart!', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/cart/update', methods=['POST'])
@login_required
@buyer_required
def update_cart():
    try:
        cart_id = int(request.form.get('cart_id', 0))
        quantity = int(request.form.get('quantity', 1))
    except (ValueError, TypeError):
        return redirect(url_for('cart'))

    db = get_db()
    if quantity <= 0:
        db.execute("DELETE FROM cart WHERE id=? AND user_id=?", (cart_id, current_user.id))
    else:
        item = db.execute(
            "SELECT c.*, p.stock FROM cart c JOIN products p ON c.product_id=p.id WHERE c.id=? AND c.user_id=?",
            (cart_id, current_user.id)
        ).fetchone()
        if item and quantity <= item['stock']:
            db.execute("UPDATE cart SET quantity=? WHERE id=? AND user_id=?",
                       (quantity, cart_id, current_user.id))
        else:
            flash('Requested quantity exceeds available stock.', 'danger')
    db.commit()
    return redirect(url_for('cart'))

@app.route('/cart/remove/<int:cart_id>', methods=['POST'])
@login_required
@buyer_required
def remove_from_cart(cart_id):
    db = get_db()
    db.execute("DELETE FROM cart WHERE id=? AND user_id=?", (cart_id, current_user.id))
    db.commit()
    flash('Item removed from cart.', 'info')
    return redirect(url_for('cart'))

# ─── Checkout & Orders ─────────────────────────────────────────────────────────

@app.route('/checkout', methods=['POST'])
@login_required
@buyer_required
def checkout():
    db = get_db()
    items = db.execute('''
        SELECT c.id as cart_id, c.quantity,
               p.id as product_id, p.name, p.price, p.stock
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', (current_user.id,)).fetchall()

    if not items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('cart'))

    for item in items:
        if item['quantity'] > item['stock']:
            flash(f'Not enough stock for "{item["name"]}".', 'danger')
            return redirect(url_for('cart'))

    total = sum(item['price'] * item['quantity'] for item in items)
    cur = db.cursor()
    cur.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (?,?,?)",
                (current_user.id, total, 'Pending'))
    order_id = cur.lastrowid
    for item in items:
        cur.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase) VALUES (?,?,?,?)",
            (order_id, item['product_id'], item['quantity'], item['price'])
        )
        cur.execute("UPDATE products SET stock = stock - ? WHERE id=?",
                    (item['quantity'], item['product_id']))
    cur.execute("DELETE FROM cart WHERE user_id=?", (current_user.id,))
    db.commit()
    return redirect(url_for('checkout_success', order_id=order_id))

@app.route('/checkout/success/<int:order_id>')
@login_required
@buyer_required
def checkout_success(order_id):
    db = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id=? AND user_id=?",
        (order_id, current_user.id)
    ).fetchone()
    if not order:
        return redirect(url_for('index'))
    items = db.execute('''
        SELECT oi.*, p.name, p.image_url
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    ''', (order_id,)).fetchall()
    return render_template('buyer/checkout_success.html', order=order, items=items)

@app.route('/orders')
@login_required
@buyer_required
def my_orders():
    db = get_db()
    orders = db.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC",
        (current_user.id,)
    ).fetchall()
    order_items_map = {}
    for order in orders:
        items = db.execute('''
            SELECT oi.*, p.name, p.image_url
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        ''', (order['id'],)).fetchall()
        order_items_map[order['id']] = items
    return render_template('buyer/orders.html', orders=orders, order_items_map=order_items_map)

# ─── Admin Routes ──────────────────────────────────────────────────────────────

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    db = get_db()
    total_products = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_orders   = db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    total_revenue  = db.execute("SELECT COALESCE(SUM(total_amount),0) FROM orders").fetchone()[0]
    total_users    = db.execute("SELECT COUNT(*) FROM users WHERE role='buyer'").fetchone()[0]
    recent_orders  = db.execute('''
        SELECT o.*, u.username FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC LIMIT 5
    ''').fetchall()
    return render_template('admin/dashboard.html',
                           total_products=total_products,
                           total_orders=total_orders,
                           total_revenue=total_revenue,
                           total_users=total_users,
                           recent_orders=recent_orders)

@app.route('/admin/products')
@login_required
@admin_required
def admin_products():
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_product():
    if request.method == 'POST':
        name        = request.form['name'].strip()
        description = request.form['description'].strip()
        price       = float(request.form['price'])
        stock       = int(request.form['stock'])
        category    = request.form['category'].strip()
        image_url   = request.form.get('image_url', '').strip()
        file = request.files.get('image_file')
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('static', filename=f'uploads/{filename}')
        db = get_db()
        db.execute(
            "INSERT INTO products (name, description, price, stock, image_url, category) VALUES (?,?,?,?,?,?)",
            (name, description, price, stock, image_url, category)
        )
        db.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin/product_form.html', product=None, action='Add')

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_product(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        flash('Product not found.', 'warning')
        return redirect(url_for('admin_products'))
    if request.method == 'POST':
        name        = request.form['name'].strip()
        description = request.form['description'].strip()
        price       = float(request.form['price'])
        stock       = int(request.form['stock'])
        category    = request.form['category'].strip()
        image_url   = request.form.get('image_url', '').strip()
        file = request.files.get('image_file')
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('static', filename=f'uploads/{filename}')
            # Remove the old uploaded file
            old_url = product['image_url'] or ''
            if '/static/uploads/' in old_url:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_url.rsplit('/', 1)[-1])
                if os.path.exists(old_path):
                    os.remove(old_path)
        db.execute(
            "UPDATE products SET name=?, description=?, price=?, stock=?, image_url=?, category=? WHERE id=?",
            (name, description, price, stock, image_url, category, product_id)
        )
        db.commit()
        flash('Product updated!', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin/product_form.html', product=product, action='Edit')

@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_product(product_id):
    db = get_db()
    db.execute("DELETE FROM products WHERE id=?", (product_id,))
    db.commit()
    flash('Product deleted.', 'info')
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    db = get_db()
    orders = db.execute('''
        SELECT o.*, u.username, u.email FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC
    ''').fetchall()
    order_items_map = {}
    for order in orders:
        items = db.execute('''
            SELECT oi.*, p.name FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        ''', (order['id'],)).fetchall()
        order_items_map[order['id']] = items
    return render_template('admin/orders.html', orders=orders, order_items_map=order_items_map)

@app.route('/admin/orders/update/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def admin_update_order(order_id):
    status = request.form.get('status')
    valid_statuses = ['Pending', 'Shipped', 'Delivered', 'Cancelled']
    if status in valid_statuses:
        db = get_db()
        db.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        db.commit()
        flash(f'Order #{order_id} status updated to {status}.', 'success')
    return redirect(url_for('admin_orders'))

# ─── Cart count context processor ─────────────────────────────────────────────

@app.context_processor
def inject_cart_count():
    count = 0
    if current_user.is_authenticated and current_user.role == 'buyer':
        db = get_db()
        row = db.execute(
            "SELECT COALESCE(SUM(quantity),0) FROM cart WHERE user_id=?",
            (current_user.id,)
        ).fetchone()
        count = row[0] if row else 0
    return dict(cart_count=count)

# ─── Init DB on startup (works with debug reloader too) ───────────────────────

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
