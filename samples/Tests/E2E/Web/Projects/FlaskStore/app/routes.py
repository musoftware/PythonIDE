"""RAD Store pages, login and the JSON API."""
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
