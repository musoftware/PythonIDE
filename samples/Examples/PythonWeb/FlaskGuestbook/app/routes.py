# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Guestbook pages: list + search + paging, sign (form with validation and flash messages), delete."""
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from .db import get_db

bp = Blueprint("main", __name__)
PAGE_SIZE = 10


@bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    page = max(1, request.args.get("page", 1, type=int))
    sql, args = "SELECT * FROM entry", []
    if q:
        sql += " WHERE name LIKE ? OR message LIKE ?"
        args = [f"%{q}%", f"%{q}%"]
    db = get_db()
    total = db.execute(sql.replace("*", "COUNT(*)", 1), args).fetchone()[0]
    rows = db.execute(sql + " ORDER BY id DESC LIMIT ? OFFSET ?", args + [PAGE_SIZE, (page - 1) * PAGE_SIZE]).fetchall()
    avg = db.execute("SELECT AVG(rating) FROM entry").fetchone()[0]
    return render_template("index.html", entries=rows, q=q, page=page, total=total,
                           pages=max(1, -(-total // PAGE_SIZE)), avg=avg, site_name=current_app.config["SITE_NAME"])


@bp.route("/sign", methods=["GET", "POST"])
def sign():
    form = {"name": "", "message": "", "rating": "5"}
    errors = {}
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in form}
        if not form["name"]:
            errors["name"] = "Please enter your name."
        elif len(form["name"]) > 60:
            errors["name"] = "The name is too long (60 characters at most)."
        if len(form["message"]) < 3:
            errors["message"] = "The message needs at least 3 characters."
        if form["rating"] not in {"1", "2", "3", "4", "5"}:
            errors["rating"] = "Choose 1 to 5 stars."
        if not errors:
            db = get_db()
            db.execute("INSERT INTO entry (name, message, rating) VALUES (?, ?, ?)",
                       (form["name"], form["message"], int(form["rating"])))
            db.commit()
            flash(f"Thank you, {form['name']}! Your message was added.")
            return redirect(url_for("main.index"))
    return render_template("sign.html", form=form, errors=errors, site_name=current_app.config["SITE_NAME"])


@bp.route("/delete/<int:entry_id>", methods=["POST"])
def delete(entry_id):
    db = get_db()
    if db.execute("SELECT id FROM entry WHERE id = ?", (entry_id,)).fetchone() is None:
        abort(404)
    db.execute("DELETE FROM entry WHERE id = ?", (entry_id,))
    db.commit()
    flash("The message was deleted.")
    return redirect(url_for("main.index"))
