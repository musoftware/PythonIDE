"""RAD Store - Flask application factory."""
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
