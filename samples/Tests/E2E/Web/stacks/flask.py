# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""RAD Store in Flask 3 + sqlite3: New Project > Web > Flask App (the IDE creates the project's .venv)."""
TITLE = "Python Flask + SQLite"
LANG, TEMPLATE, NAME = "python-flask", "flask-app", "FlaskStore"
TOOLS = []
WEBROOT = "."
DB_FILE = "data/store.db"
DESIGN = "app/templates/index.html"
DESIGN_TARGET = "#home"
DESIGN_KEEP = ["{{ url_for('static', filename='css/site.css') }}", "{{ url_for('main.products') }}"]
ROUTES = {"home": "/", "products": "/products", "add": "/products/add", "edit": "/products/{id}/edit",
          "login": "/login", "logout": "/logout", "ar": "/ar", "api": "/api/products",
          "css": "/static/css/site.css", "js": "/static/js/app.js"}
DEBUG = {"file": "app/routes.py", "match": "rows = db().execute(", "path": "/products"}
INTELLI = {"file": "app/routes.py", "after": "def products():", "type": "request.ar", "expect": "args",
           "html_file": "app/templates/ar.html", "css_file": "app/static/css/site.css"}
PUBLISH_EXPECT = ["app/__init__.py", "app/routes.py", "app/templates/index.html", "app/static/css/site.css",
                  "requirements.txt"]
PUBLISH_FORBID = ["data/store.db"]
RUN_TIMEOUT = 600


def serve_published(dest, port, **_):
    import os
    from pathlib import Path
    from radide.web_site.frameworks.python_web import venv_python
    import e2e_lib as E
    py = venv_python(E.Path(CTX_FOLDER[0])) if CTX_FOLDER else ""
    if not py:
        return None, "the project's .venv was not created", None
    return [py, "-m", "flask", "--app", "app", "run", "--host", "127.0.0.1", "--port", str(port)], str(dest), \
        dict(os.environ, FLASK_DEBUG="0")


CTX_FOLDER: list = []


def after_create(j, win, project, folder):
    CTX_FOLDER[:] = [str(folder)]
    from radide.web_site.frameworks.python_web import venv_python
    return f".venv python: {venv_python(folder) or '(created on first run)'}"


DB_SQL = """-- RAD Store schema (Databases workspace)
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  price REAL NOT NULL DEFAULT 0
);
INSERT INTO products (name, price) VALUES ('Laptop', 999.5), ('Phone', 450);
"""

INIT = '''"""RAD Store - Flask application factory."""
import os
import secrets
import sqlite3
from pathlib import Path

from flask import Flask, g, session

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "store.db"


def db():
    if "db" not in g:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                     "name TEXT NOT NULL, price REAL NOT NULL DEFAULT 0)")
        if g.db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            g.db.executemany("INSERT INTO products (name, price) VALUES (?, ?)", [("Laptop", 999.5), ("Phone", 450)])
            g.db.commit()
    return g.db


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-rad-store")
    app.json.ensure_ascii = False

    @app.teardown_appcontext
    def close_db(_exc):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    @app.context_processor
    def inject():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        return {"csrf": session["csrf"], "user": session.get("user")}

    from .routes import bp
    app.register_blueprint(bp)
    return app
'''

ROUTES_PY = '''"""RAD Store pages, login and the JSON API."""
from functools import wraps
import hmac

from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for

from . import db

bp = Blueprint("main", __name__)


def csrf_ok():
    return hmac.compare_digest(session.get("csrf", ""), request.form.get("csrf", ""))


def login_required(view):
    @wraps(view)
    def wrapped(*a, **k):
        if not session.get("user"):
            return redirect(url_for("main.login", next=request.path))
        return view(*a, **k)
    return wrapped


def validate(form):
    errors = []
    name = form.get("name", "").strip()
    try:
        price = float(form.get("price", ""))
    except ValueError:
        price = -1
    if not name:
        errors.append("Name is required")
    if price < 0:
        errors.append("Price must be a positive number")
    return errors, name, price


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/products")
def products():
    q = request.args.get("q", "")
    rows = db().execute("SELECT id, name, price FROM products WHERE name LIKE ? ORDER BY id", (f"%{q}%",)).fetchall()
    return render_template("products.html", products=rows, q=q)


@bp.route("/products/add", methods=["GET", "POST"])
@login_required
def add():
    errors, name, price = [], "", ""
    if request.method == "POST":
        if not csrf_ok():
            abort(400)
        errors, name, price = validate(request.form)
        if not errors:
            db().execute("INSERT INTO products (name, price) VALUES (?, ?)", (name, price))
            db().commit()
            return redirect(url_for("main.products"))
    return render_template("product_form.html", title="Add product", errors=errors, name=name, price=price,
                           product=None), (422 if errors else 200)


@bp.route("/products/<int:pid>/edit", methods=["GET", "POST"])
@login_required
def edit(pid):
    row = db().execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if row is None:
        abort(404)
    errors, name, price = [], row["name"], row["price"]
    if request.method == "POST":
        if not csrf_ok():
            abort(400)
        errors, name, price = validate(request.form)
        if not errors:
            db().execute("UPDATE products SET name = ?, price = ? WHERE id = ?", (name, price, pid))
            db().commit()
            return redirect(url_for("main.products"))
    return render_template("product_form.html", title="Edit product", errors=errors, name=name, price=price,
                           product=row), (422 if errors else 200)


@bp.post("/products/<int:pid>/delete")
@login_required
def delete(pid):
    if not csrf_ok():
        abort(400)
    db().execute("DELETE FROM products WHERE id = ?", (pid,))
    db().commit()
    return redirect(url_for("main.products"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if not csrf_ok():
            abort(400)
        if request.form.get("username") == "admin" and hmac.compare_digest(request.form.get("password", ""), "secret"):
            session["user"] = "admin"
            nxt = request.form.get("next") or url_for("main.products")
            return redirect(nxt if nxt.startswith("/") else url_for("main.products"))
        error = "Invalid user name or password"
    return render_template("login.html", error=error, next=request.args.get("next", "")), (401 if error else 200)


@bp.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("main.index"))


@bp.route("/ar")
def arabic():
    count = db().execute("SELECT COUNT(*) FROM products").fetchone()[0]
    return render_template("ar.html", count=count)


@bp.route("/api/products")
def api_products():
    rows = db().execute("SELECT id, name, price FROM products ORDER BY id").fetchall()
    return jsonify([dict(r) for r in rows])
'''

BASE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}RAD Store{% endblock %} - RAD Store</title>
<link rel="stylesheet" href="{{ url_for('static', filename='css/site.css') }}">
</head>
<body>
<nav class="top"><a href="{{ url_for('main.index') }}">Home</a> <a href="{{ url_for('main.products') }}">Products</a>
<a href="{{ url_for('main.arabic') }}">العربية</a>
{% if user %}<span class="user">{{ user }}</span> <a href="{{ url_for('main.logout') }}">Log out</a>
{% else %}<a href="{{ url_for('main.login') }}">Log in</a>{% endif %}</nav>
<main>{% block content %}{% endblock %}</main>
<script src="{{ url_for('static', filename='js/app.js') }}"></script>
</body>
</html>
"""

INDEX = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RAD Store</title>
<link rel="stylesheet" href="{{ url_for('static', filename='css/site.css') }}">
</head>
<body>
<nav class="top"><a href="/">Home</a> <a href="{{ url_for('main.products') }}">Products</a> <a href="/ar">العربية</a> <a href="/login">Log in</a></nav>
<main id="home">
</main>
</body>
</html>
"""

PRODUCTS = """{% extends "base.html" %}
{% block title %}Products{% endblock %}
{% block content %}
<h1>Products</h1>
<form method="get" class="search"><input name="q" value="{{ q }}" placeholder="Search"><button>Search</button></form>
{% if user %}<p><a class="btn" href="{{ url_for('main.add') }}">Add product</a></p>{% endif %}
<table id="products"><thead><tr><th>Name</th><th>Price</th><th></th></tr></thead><tbody>
{% for p in products %}
<tr data-id="{{ p.id }}"><td class="name">{{ p.name }}</td><td>{{ '%.2f'|format(p.price) }}</td>
<td>{% if user %}<a href="{{ url_for('main.edit', pid=p.id) }}">Edit</a>{% endif %}</td></tr>
{% endfor %}
</tbody></table>
<p class="count">{{ products|length }} products</p>
{% endblock %}
"""

FORM = """{% extends "base.html" %}
{% block title %}{{ title }}{% endblock %}
{% block content %}
<h1>{{ title }}</h1>
{% for e in errors %}<p class="error">{{ e }}</p>{% endfor %}
<form method="post" class="product">
  <input type="hidden" name="csrf" value="{{ csrf }}">
  <label>Name <input name="name" value="{{ name }}" required></label>
  <label>Price <input name="price" value="{{ price }}" type="number" step="0.01" min="0"></label>
  <button type="submit">Save</button>
</form>
{% if product %}
<form method="post" action="{{ url_for('main.delete', pid=product.id) }}" class="delete">
  <input type="hidden" name="csrf" value="{{ csrf }}"><button type="submit">Delete</button>
</form>
{% endif %}
{% endblock %}
"""

LOGIN = """{% extends "base.html" %}
{% block title %}Log in{% endblock %}
{% block content %}
<h1>Log in</h1>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
<form method="post" class="login">
  <input type="hidden" name="csrf" value="{{ csrf }}"><input type="hidden" name="next" value="{{ next }}">
  <label>User name <input name="username"></label>
  <label>Password <input name="password" type="password"></label>
  <button type="submit">Log in</button>
</form>
{% endblock %}
"""

AR = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>متجر راد</title><link rel="stylesheet" href="{{ url_for('static', filename='css/site.css') }}"></head>
<body>
<nav class="top"><a href="/">English</a> <a href="/products">المنتجات</a></nav>
<main><h1>مرحبا بكم في متجر راد</h1><p id="count">عدد المنتجات: {{ count }}</p></main>
</body>
</html>
"""

CSS = """/* RAD Store */
body { font-family: "Segoe UI", Tahoma, sans-serif; margin: 0; background: #f6f7fb; color: #222; }
nav.top { background: #1f2937; padding: 10px 16px; }
nav.top a, nav.top .user { color: #fff; margin-inline-end: 14px; text-decoration: none; }
main { max-width: 900px; margin: 20px auto; padding: 0 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; }
th, td { padding: 8px; border-bottom: 1px solid #ddd; text-align: start; }
.error { color: #b00020; font-weight: bold; }
.hero { padding: 40px 20px; background: linear-gradient(90deg, #1f2937, #4b5563); color: #fff; border-radius: 12px; }
"""


def files():
    return {"app/__init__.py": INIT, "app/routes.py": ROUTES_PY, "app/templates/base.html": BASE,
            "app/templates/index.html": INDEX, "app/templates/products.html": PRODUCTS,
            "app/templates/product_form.html": FORM, "app/templates/login.html": LOGIN, "app/templates/ar.html": AR,
            "app/static/css/site.css": CSS, "app/static/js/app.js": "// RAD Store\n"}
