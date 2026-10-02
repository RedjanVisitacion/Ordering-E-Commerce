# AGENT.md — Lessons Learned for RPSV Store

This file documents every bug, root cause, and fix discovered during development of this Flask e-commerce app.
Use this as a reference before making changes or debugging future issues.

---

## Project Overview

- **Stack:** Python, Flask, SQLite, Bootstrap 5, Flask-Login
- **Entry point:** `ecommerce/app.py`
- **Database:** `ecommerce/database.db` (SQLite)
- **Templates:** `ecommerce/templates/`
- **Static files:** `ecommerce/static/` (css, js, uploads)
- **Admin user:** Redjan (seeded in `database.py`)
- **Buyer users:** Registered via `/register`

---

## Bug Log & Fixes

---

### BUG 1 — Sessions invalidated on every server restart

**Symptom:** Users appear logged in (name shows in navbar) but cart is empty and add-to-cart does nothing.  
**Root cause:** `app.secret_key = os.urandom(24)` generates a new random key every restart. Flask can no longer decrypt the old session cookies, so all users are silently treated as anonymous.  
**Fix:** Persist the secret key to a `.secret_key` file on first run, reload it on subsequent starts.

```python
_SECRET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.secret_key')
if os.path.exists(_SECRET_FILE):
    with open(_SECRET_FILE, 'rb') as _f:
        app.secret_key = _f.read()
else:
    app.secret_key = os.urandom(32)
    with open(_SECRET_FILE, 'wb') as _f:
        _f.write(app.secret_key)
```

**Rule:** Never use `os.urandom()` directly as `secret_key` in a running app.

---

### BUG 2 — `init_db()` never runs in Flask debug mode (reloader child process)

**Symptom:** Tables exist from a previous run but any fresh DB shows "no such table" errors, or changes to schema never apply. Cart/order writes silently fail.  
**Root cause:** Flask's debug reloader spawns a child process where `__name__ != '__main__'`. Putting `init_db()` inside `if __name__ == '__main__':` means it never runs in the actual request-handling process.  
**Fix:** Call `init_db()` inside `with app.app_context():` at module level, outside of `__main__`.

```python
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

**Rule:** Always initialize the DB using app context, not inside `__main__`.

---

### BUG 3 — Database path resolves differently depending on working directory

**Symptom:** Phone users see different data than PC users. Orders placed on phone don't show in admin. Cart items disappear.  
**Root cause:** `DATABASE = 'database.db'` is a relative path. It resolves to wherever Python is launched from — not necessarily the project folder. If Flask is started from a different directory, it creates or reads a different `database.db`.  
**Fix:** Always use an absolute path anchored to the file's location.

```python
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
```

**Rule:** Never use relative paths for the database file.

---

### BUG 4 — Multiple DB connections per request cause concurrency issues

**Symptom:** Under concurrent use (phone + PC at the same time), writes occasionally don't persist. `db.close()` sprinkled everywhere with inconsistent results.  
**Root cause:** Every `get_db()` call opened a brand new SQLite connection. Multiple open connections to the same SQLite file under concurrent writes cause locking errors.  
**Fix:** Use Flask's `g` object for one shared connection per request. Register `teardown_appcontext` to close it automatically.

```python
# database.py
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")  # allows concurrent reads+writes
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# app.py
app.teardown_appcontext(close_db)
```

Remove all manual `db.close()` calls from routes — teardown handles it.  
**Rule:** One DB connection per request via `g`. Never call `db.close()` manually in routes.

---

### BUG 5 — WAL mode not enabled, SQLite locks under concurrent access

**Symptom:** Occasional write failures when phone and PC use the app simultaneously.  
**Root cause:** Default SQLite journal mode (`DELETE`) only allows one writer and blocks readers during writes.  
**Fix:** Enable WAL (Write-Ahead Logging) mode which allows concurrent reads alongside a single writer.

```python
g.db.execute("PRAGMA journal_mode = WAL")
```

**Rule:** Always enable WAL mode for any multi-client SQLite app.

---

### BUG 6 — "Add to Cart" POST never reaches the server (mobile)

**Symptom:** Button shows "Added!" animation but cart stays empty. `POST /cart/add` never appears in Flask logs.  
**Root cause:** The JavaScript click handler on the submit button called `this.disabled = true` before the browser had a chance to submit the form. Mobile Chrome (and some desktop browsers) cancel form submission when the submit button is disabled during the click event.  
**Fix:** Listen on the form's `submit` event instead of the button's `click` event, so the POST fires first.

```javascript
// WRONG — disabling button on click cancels form submission on mobile
document.querySelectorAll('form[action*="cart/add"] button[type="submit"]').forEach(btn => {
    btn.addEventListener('click', function () {
        this.disabled = true; // ← kills the POST on mobile
    });
});

// CORRECT — attach to form submit, not button click
document.querySelectorAll('form[action*="cart/add"]').forEach(form => {
    form.addEventListener('submit', function () {
        const btn = this.querySelector('button[type="submit"]');
        if (btn) btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Adding...';
    });
});
```

**Rule:** Never disable a submit button inside a `click` handler. Use the form's `submit` event.

---

### BUG 7 — Flask only accessible on localhost, not on phone

**Symptom:** `http://192.168.x.x:5000` refused to connect from phone.  
**Root cause:** Default `app.run()` binds to `127.0.0.1` (loopback only). Also, Windows Firewall blocks port 5000 by default.  
**Fix:**

```python
app.run(host='0.0.0.0', port=5000, debug=True)
```

Then open port 5000 in Windows Firewall (requires admin CMD):
```
netsh advfirewall firewall add rule name="Flask 5000" dir=in action=allow protocol=TCP localport=5000
```

**Rule:** Use `host='0.0.0.0'` for LAN access. Always open the port in the firewall.

---

### BUG 8 — Phone on different subnet sees different data

**Symptom:** PC on `192.168.15.x`, phone on `192.168.137.x` (hotspot). They appeared to use different sessions.  
**Root cause:** The phone connected via Windows Mobile Hotspot (a different network adapter) while the PC was on Ethernet. When the phone first accessed the site on one IP, then later via another, the session cookie domain didn't match.  
**Fix:** Ensure `SESSION_COOKIE_SAMESITE = 'Lax'` and `SESSION_COOKIE_SECURE = False` so cookies are sent freely over plain HTTP on the local network.

```python
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
app.config['REMEMBER_COOKIE_SECURE'] = False
```

Also use `login_user(user, remember=True)` so sessions survive browser restarts on the phone.  
**Rule:** On LAN/hotspot, always set `SESSION_COOKIE_SECURE = False` and `SAMESITE = 'Lax'`.

---

### BUG 9 — Image preview shows broken image (inaccurate preview)

**Symptom:** Image preview appears immediately for any text typed in the URL field, showing a broken image icon for invalid URLs.  
**Root cause:** Preview was set on every `input` event without checking if the image actually loaded. Also no debounce, so it fired on every keystroke.  
**Fix:** Only show the preview container after the `<img>` fires its `load` event. Hide it on `error`. Add 500ms debounce on the URL input.

```javascript
previewImg.addEventListener('load', function () {
    if (this.naturalWidth > 0) previewContainer.style.display = 'block';
});
previewImg.addEventListener('error', function () {
    previewContainer.style.display = 'none';
});
```

**Rule:** Never show an image preview until the `load` event confirms the image is valid.

---

### BUG 10 — `buyer_required` silently redirected users without showing why

**Symptom:** Clicking "Add to Cart" or visiting `/cart` as a non-buyer (or unauthenticated) user just redirected to homepage with no message.  
**Root cause:** The decorator redirected to `url_for('index')` without a flash message or `next` parameter, making it impossible for the user to know they needed to log in.  
**Fix:** Split the check into two cases and redirect to login with `next` for unauthenticated users.

```python
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
```

**Rule:** Always pass `next=request.url` when redirecting to login so users return to what they were doing.

---

## Image Upload System

- Uploaded images are saved to `static/uploads/` with a UUID filename.
- Max file size: 5 MB. Allowed types: PNG, JPG, JPEG, GIF, WebP.
- Uploaded file takes priority over URL if both are provided.
- Old uploaded file is deleted when a product image is replaced.
- The product form supports both drag-and-drop upload and URL input via a tab toggle.

```python
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
```

---

## General Rules for This Project

1. **Always use absolute paths** for database and upload folder — never relative.
2. **One DB connection per request** via Flask `g` — never open/close manually in routes.
3. **WAL mode always on** for SQLite when multiple clients are possible.
4. **Secret key must be stable** — persist to `.secret_key` file, never regenerate on restart.
5. **`init_db()` in `app.app_context()`** — not inside `if __name__ == '__main__'`.
6. **Never disable submit buttons in click handlers** — use form `submit` event instead.
7. **`host='0.0.0.0'`** always when LAN/phone access is needed.
8. **`SESSION_COOKIE_SECURE = False`** on plain HTTP local network.
9. **Image previews only on `load` event** — not on input change directly.
10. **Always flash a message and pass `next=`** when redirecting to login.
