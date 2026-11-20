"""SQLite with the standard sqlite3 module: one connection per request (flask.g)."""
import os
import sqlite3

import click
from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS todo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def get_db():
    if "db" not in g:
        path = current_app.config["DATABASE"]
        if path != ":memory:":
            os.makedirs(os.path.dirname(path), exist_ok=True)
        g.db = sqlite3.connect(path)
        g.db.row_factory = sqlite3.Row
        g.db.executescript(SCHEMA)
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@click.command("init-db")
def init_db_command():
    """Clear the todo list and add three examples."""
    db = get_db()
    db.execute("DELETE FROM todo")
    for title, done in (("Try RAD IDE's Flask support", 1), ("Set a breakpoint in todos.py", 0),
                        ("Type url_for(' in a template", 0)):
        db.execute("INSERT INTO todo (title, done) VALUES (?, ?)", (title, done))
    db.commit()
    click.echo("Initialized the database with 3 todos.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
