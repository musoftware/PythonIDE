# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""JSON API of the guestbook (try it in the IDE's REST client): GET /api/entries, POST /api/entries."""
from flask import Blueprint, jsonify, request

from .db import get_db

bp = Blueprint("api", __name__)


@bp.get("/entries")
def entries():
    rows = get_db().execute("SELECT * FROM entry ORDER BY id DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@bp.post("/entries")
def add_entry():
    data = request.get_json(silent=True) or {}
    name, message = str(data.get("name", "")).strip(), str(data.get("message", "")).strip()
    if not name or len(message) < 3:
        return jsonify({"error": "name and message (3+ characters) are required"}), 400
    rating = int(data.get("rating", 5)) if str(data.get("rating", 5)).isdigit() else 5
    db = get_db()
    cur = db.execute("INSERT INTO entry (name, message, rating) VALUES (?, ?, ?)",
                     (name, message, max(1, min(5, rating))))
    db.commit()
    row = db.execute("SELECT * FROM entry WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201
