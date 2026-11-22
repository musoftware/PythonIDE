# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""RAD Store in FastAPI (New Project > Web > FastAPI App): Jinja pages + form posts (python-multipart),
a signed-cookie session, sqlite3, a Pydantic-typed JSON API, StaticFiles."""
TITLE = "Python FastAPI + SQLite"
LANG, TEMPLATE, NAME = "python-fastapi", "fastapi-app", "FastApiStore"
TOOLS = []
WEBROOT = "."
DB_FILE = "data/store.db"
DESIGN = "app/templates/index.html"
DESIGN_TARGET = "#home"
DESIGN_KEEP = ["{{ url_for('static', path='css/site.css') }}"]
ROUTES = {"home": "/", "products": "/products", "add": "/products/add", "edit": "/products/{id}/edit",
          "login": "/login", "logout": "/logout", "ar": "/ar", "api": "/api/products",
          "css": "/static/css/site.css", "js": "/static/js/app.js"}
DEBUG = {"file": "app/main.py", "match": "rows = db().execute(\"SELECT id, name, price FROM products WHERE",
         "path": "/products"}
INTELLI = {"file": "app/main.py", "after": "def products(request: Request", "type": "request.query_para",
           "expect": "query_params", "html_file": "app/templates/ar.html", "css_file": "app/static/css/site.css"}
PUBLISH_EXPECT = ["app/main.py", "app/templates/index.html", "app/static/css/site.css", "requirements.txt"]
PUBLISH_FORBID = ["data/store.db"]
RUN_TIMEOUT = 600
CTX: dict = {}


def serve_published(dest, port, **_):
    import os
    from radide.web_site.frameworks.python_web import venv_python
    py = venv_python(CTX.get("folder", "")) if CTX.get("folder") else ""
    if not py:
        return None, "the project's .venv was not created", None
    return [py, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)], str(dest), \
        dict(os.environ)


def after_create(j, win, project, folder):
    CTX["folder"] = str(folder)
    return ""


DB_SQL = """-- RAD Store schema (Databases workspace)
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  price REAL NOT NULL DEFAULT 0
);
INSERT INTO products (name, price) VALUES ('Laptop', 999.5), ('Phone', 450);
"""

MAIN = '''"""RAD Store - FastAPI application."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
DB_PATH = HERE.parent / "data" / "store.db"
SECRET = os.environ.get("SECRET_KEY", "dev-only-rad-store").encode()

app = FastAPI(title="RAD Store")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")


class Product(BaseModel):
    id: int
    name: str
    price: float


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, "
                 "price REAL NOT NULL DEFAULT 0)")
    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        conn.executemany("INSERT INTO products (name, price) VALUES (?, ?)", [("Laptop", 999.5), ("Phone", 450)])
        conn.commit()
    return conn


# ---- a small signed-cookie session
def load_session(request: Request) -> dict:
    raw = request.cookies.get("store_session", "")
    try:
        data, sig = raw.rsplit(".", 1)
        if hmac.compare_digest(sig, hmac.new(SECRET, data.encode(), hashlib.sha256).hexdigest()):
            return json.loads(base64.urlsafe_b64decode(data.encode()))
    except ValueError:
        pass
    return {}


def save_session(response, session: dict):
    data = base64.urlsafe_b64encode(json.dumps(session).encode()).decode()
    sig = hmac.new(SECRET, data.encode(), hashlib.sha256).hexdigest()
    response.set_cookie("store_session", f"{data}.{sig}", httponly=True, samesite="lax")
    return response


def render(request: Request, name: str, status: int = 200, **ctx):
    session = load_session(request)
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    ctx.update(request=request, user=session.get("user"), csrf=session["csrf"])
    return save_session(templates.TemplateResponse(request, name, ctx, status_code=status), session)


def check_csrf(request: Request, token: str):
    if not hmac.compare_digest(load_session(request).get("csrf", ""), token or ""):
        raise HTTPException(400, "Bad CSRF token")


def login_redirect(request: Request):
    if not load_session(request).get("user"):
        return RedirectResponse(f"/login?next={request.url.path}", status_code=303)
    return None


def validate(name: str, price: str):
    errors = []
    name = (name or "").strip()
    try:
        value = float(price)
    except (TypeError, ValueError):
        value = -1
    if not name:
        errors.append("Name is required")
    if value < 0:
        errors.append("Price must be a positive number")
    return errors, name, value


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return render(request, "index.html")


@app.get("/products", response_class=HTMLResponse)
def products(request: Request, q: str = ""):
    rows = db().execute("SELECT id, name, price FROM products WHERE name LIKE ? ORDER BY id", (f"%{q}%",)).fetchall()
    return render(request, "products.html", products=rows, q=q)


@app.get("/products/add", response_class=HTMLResponse)
def add_form(request: Request):
    return login_redirect(request) or render(request, "product_form.html", title="Add product", errors=[],
                                             name="", price="", product=None)


@app.post("/products/add", response_class=HTMLResponse)
def add(request: Request, name: str = Form(""), price: str = Form(""), csrf: str = Form("")):
    if (r := login_redirect(request)) is not None:
        return r
    check_csrf(request, csrf)
    errors, name, value = validate(name, price)
    if errors:
        return render(request, "product_form.html", 422, title="Add product", errors=errors, name=name, price=price,
                      product=None)
    with db() as conn:
        conn.execute("INSERT INTO products (name, price) VALUES (?, ?)", (name, value))
    return RedirectResponse("/products", status_code=303)


def get_product(pid: int):
    row = db().execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if row is None:
        raise HTTPException(404, "Product not found")
    return row


@app.get("/products/{pid}/edit", response_class=HTMLResponse)
def edit_form(request: Request, pid: int):
    if (r := login_redirect(request)) is not None:
        return r
    p = get_product(pid)
    return render(request, "product_form.html", title="Edit product", errors=[], name=p["name"], price=p["price"],
                  product=p)


@app.post("/products/{pid}/edit", response_class=HTMLResponse)
def edit(request: Request, pid: int, name: str = Form(""), price: str = Form(""), csrf: str = Form("")):
    if (r := login_redirect(request)) is not None:
        return r
    check_csrf(request, csrf)
    p = get_product(pid)
    errors, name, value = validate(name, price)
    if errors:
        return render(request, "product_form.html", 422, title="Edit product", errors=errors, name=name,
                      price=price, product=p)
    with db() as conn:
        conn.execute("UPDATE products SET name = ?, price = ? WHERE id = ?", (name, value, pid))
    return RedirectResponse("/products", status_code=303)


@app.post("/products/{pid}/delete")
def delete(request: Request, pid: int, csrf: str = Form("")):
    if (r := login_redirect(request)) is not None:
        return r
    check_csrf(request, csrf)
    with db() as conn:
        conn.execute("DELETE FROM products WHERE id = ?", (pid,))
    return RedirectResponse("/products", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, next: str = "/products"):
    return render(request, "login.html", error="", next=next)


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(""), password: str = Form(""), csrf: str = Form(""),
          next: str = Form("/products")):
    check_csrf(request, csrf)
    if username == "admin" and hmac.compare_digest(password, "secret"):
        session = load_session(request)
        session["user"] = "admin"
        return save_session(RedirectResponse(next if next.startswith("/") else "/products", status_code=303), session)
    return render(request, "login.html", 401, error="Invalid user name or password", next=next)


@app.get("/logout")
def logout(request: Request):
    session = load_session(request)
    session.pop("user", None)
    return save_session(RedirectResponse("/", status_code=303), session)


@app.get("/ar", response_class=HTMLResponse)
def arabic(request: Request):
    count = db().execute("SELECT COUNT(*) FROM products").fetchone()[0]
    return render(request, "ar.html", count=count)


@app.get("/api/products", response_model=list[Product])
def api_products():
    return [dict(r) for r in db().execute("SELECT id, name, price FROM products ORDER BY id")]
'''

BASE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}RAD Store{% endblock %} - RAD Store</title>
<link rel="stylesheet" href="{{ url_for('static', path='css/site.css') }}">
</head>
<body>
<nav class="top"><a href="/">Home</a> <a href="/products">Products</a> <a href="/ar">العربية</a>
{% if user %}<span class="user">{{ user }}</span> <a href="/logout">Log out</a>{% else %}<a href="/login">Log in</a>{% endif %}</nav>
<main>{% block content %}{% endblock %}</main>
<script src="{{ url_for('static', path='js/app.js') }}"></script>
</body>
</html>
"""

INDEX = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RAD Store</title>
<link rel="stylesheet" href="{{ url_for('static', path='css/site.css') }}">
</head>
<body>
<nav class="top"><a href="/">Home</a> <a href="/products">Products</a> <a href="/ar">العربية</a> <a href="/login">Log in</a></nav>
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
{% if user %}<p><a class="btn" href="/products/add">Add product</a></p>{% endif %}
<table id="products"><thead><tr><th>Name</th><th>Price</th><th></th></tr></thead><tbody>
{% for p in products %}
<tr data-id="{{ p.id }}"><td class="name">{{ p.name }}</td><td>{{ '%.2f'|format(p.price) }}</td>
<td>{% if user %}<a href="/products/{{ p.id }}/edit">Edit</a>{% endif %}</td></tr>
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
<form method="post" action="/products/{{ product.id }}/delete" class="delete">
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
<title>متجر راد</title><link rel="stylesheet" href="{{ url_for('static', path='css/site.css') }}"></head>
<body>
<nav class="top"><a href="/">English</a> <a href="/products">المنتجات</a></nav>
<main><h1>مرحبا بكم في متجر راد</h1><p id="count">عدد المنتجات: {{ count }}</p></main>
</body>
</html>
"""

CSS = """/* RAD Store */
body { font-family: "Segoe UI", Tahoma, sans-serif; margin: 0; background: #f2f7f6; color: #222; }
nav.top { background: #009688; padding: 10px 16px; }
nav.top a, nav.top .user { color: #fff; margin-inline-end: 14px; text-decoration: none; }
main { max-width: 900px; margin: 20px auto; padding: 0 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; }
th, td { padding: 8px; border-bottom: 1px solid #ddd; text-align: start; }
.error { color: #b00020; font-weight: bold; }
.hero { padding: 40px 20px; background: linear-gradient(90deg, #00796b, #26a69a); color: #fff; border-radius: 12px; }
"""


def files():
    return {"app/main.py": MAIN, "app/templates/base.html": BASE, "app/templates/index.html": INDEX,
            "app/templates/products.html": PRODUCTS, "app/templates/product_form.html": FORM,
            "app/templates/login.html": LOGIN, "app/templates/ar.html": AR, "app/static/css/site.css": CSS,
            "app/static/js/app.js": "// RAD Store\n"}
