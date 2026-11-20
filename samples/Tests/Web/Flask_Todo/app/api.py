"""JSON API: GET /api/todos, POST /api/todos {"title": ...}, PATCH/DELETE /api/todos/<id>."""
from flask import Blueprint, abort, jsonify, request

from .db import get_db

bp = Blueprint("api", __name__)


def as_dict(row):
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"]), "created": row["created"]}


@bp.get("/todos")
def list_todos():
    return jsonify([as_dict(r) for r in get_db().execute("SELECT * FROM todo ORDER BY id")])


@bp.post("/todos")
def create_todo():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    if not title:
        return jsonify(error="title is required"), 400
    db = get_db()
    cur = db.execute("INSERT INTO todo (title) VALUES (?)", (title,))
    db.commit()
    return jsonify(as_dict(db.execute("SELECT * FROM todo WHERE id = ?", (cur.lastrowid,)).fetchone())), 201


@bp.route("/todos/<int:todo_id>", methods=["PATCH", "DELETE"])
def change_todo(todo_id):
    db = get_db()
    row = db.execute("SELECT * FROM todo WHERE id = ?", (todo_id,)).fetchone()
    if row is None:
        abort(404)
    if request.method == "DELETE":
        db.execute("DELETE FROM todo WHERE id = ?", (todo_id,))
        db.commit()
        return "", 204
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", row["title"])).strip() or row["title"]
    done = int(bool(data.get("done", row["done"])))
    db.execute("UPDATE todo SET title = ?, done = ? WHERE id = ?", (title, done, todo_id))
    db.commit()
    return jsonify(as_dict(db.execute("SELECT * FROM todo WHERE id = ?", (todo_id,)).fetchone()))
