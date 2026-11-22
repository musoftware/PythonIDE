"""RAD Store - FastAPI application."""
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


def render(request: Request, template: str, status: int = 200, **ctx):
    session = load_session(request)
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    ctx.update(request=request, user=session.get("user"), csrf=session["csrf"])
    return save_session(templates.TemplateResponse(request, template, ctx, status_code=status), session)


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
