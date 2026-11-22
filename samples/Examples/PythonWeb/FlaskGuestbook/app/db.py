# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""SQLite with the standard sqlite3 module: one connection per request (flask.g), the schema is created on
first use, and `flask --app app init-db` recreates it."""
import sqlite3

import click
from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS entry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    message TEXT NOT NULL,
    rating INTEGER NOT NULL DEFAULT 5,
    created TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.executescript(SCHEMA)
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@click.command("init-db")
def init_db_command():
    """Delete every entry and create an empty table."""
    db = get_db()
    db.executescript("DROP TABLE IF EXISTS entry;" + SCHEMA)
    click.echo("Initialized the guestbook database.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
