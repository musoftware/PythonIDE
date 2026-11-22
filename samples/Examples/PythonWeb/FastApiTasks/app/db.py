# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Tiny SQLite data layer (standard sqlite3): tasks.db next to the project, created on first use."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("TASKS_DB") or Path(__file__).resolve().parent.parent / "tasks.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'normal',
    done INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


@contextmanager
def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()


def row_to_dict(row) -> dict:
    d = dict(row)
    d["done"] = bool(d["done"])
    return d
