"""The todo list: list with a filter, add, toggle, rename, delete, clear completed."""
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from .db import get_db

bp = Blueprint("todos", __name__)
FILTERS = {"all": "", "active": "WHERE done = 0", "done": "WHERE done = 1"}


@bp.route("/")
def index():
    show = request.args.get("show", "all")
    if show not in FILTERS:
        show = "all"
    db = get_db()
    todos = db.execute(f"SELECT * FROM todo {FILTERS[show]} ORDER BY done, id DESC").fetchall()
    left = db.execute("SELECT COUNT(*) FROM todo WHERE done = 0").fetchone()[0]
    return render_template("todos/index.html", todos=todos, show=show, left=left,
                           site_name=current_app.config["SITE_NAME"])


@bp.post("/add")
def add():
    title = request.form.get("title", "").strip()
    if not title:
        flash("Write something first.", "error")
    else:
        db = get_db()
        db.execute("INSERT INTO todo (title) VALUES (?)", (title,))
        db.commit()
        flash(f"Added: {title}")
    return redirect(url_for("todos.index"))


def _todo(todo_id):
    row = get_db().execute("SELECT * FROM todo WHERE id = ?", (todo_id,)).fetchone()
    if row is None:
        abort(404)
    return row


@bp.post("/<int:todo_id>/toggle")
def toggle(todo_id):
    todo = _todo(todo_id)
    db = get_db()
    db.execute("UPDATE todo SET done = ? WHERE id = ?", (0 if todo["done"] else 1, todo_id))
    db.commit()
    return redirect(request.referrer or url_for("todos.index"))


@bp.route("/<int:todo_id>/edit", methods=["GET", "POST"])
def edit(todo_id):
    todo = _todo(todo_id)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if title:
            db = get_db()
            db.execute("UPDATE todo SET title = ? WHERE id = ?", (title, todo_id))
            db.commit()
            flash("Saved.")
            return redirect(url_for("todos.index"))
        flash("The title cannot be empty.", "error")
    return render_template("todos/edit.html", todo=todo, site_name=current_app.config["SITE_NAME"])


@bp.post("/<int:todo_id>/delete")
def delete(todo_id):
    _todo(todo_id)
    db = get_db()
    db.execute("DELETE FROM todo WHERE id = ?", (todo_id,))
    db.commit()
    flash("Deleted.")
    return redirect(url_for("todos.index"))


@bp.post("/clear")
def clear_done():
    db = get_db()
    n = db.execute("DELETE FROM todo WHERE done = 1").rowcount
    db.commit()
    flash(f"Removed {n} completed todo(s).")
    return redirect(url_for("todos.index"))
