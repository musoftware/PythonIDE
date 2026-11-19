"""Databases engine (WebMatrix "Databases" workspace) - no UI code here (UI: radide/features/databases.py).

One interface (``Database``) over three adapters:

* ``SQLiteDatabase``   - the standard library ``sqlite3`` (always available),
* ``MySQLDatabase``    - PyMySQL (``pip install pymysql``), also MariaDB,
* ``PostgresDatabase`` - psycopg 3 (``pip install "psycopg[binary]"``).

Every adapter offers: tables / views, columns, primary key, indexes, foreign keys, CREATE statement,
paged ``select`` with a row key for editing, ``insert_row`` / ``update_row`` / ``delete_row``,
``execute`` (several statements, results + errors), ``create_table`` / ``add_column`` / ``drop_column`` /
``drop_table`` / ``rename_table``, CSV / SQL export and CSV import.

Threads: an adapter (one connection) is used by one thread at a time; ``clone()`` gives a new adapter with
its own connection for a worker thread, and ``cancel()`` - callable from any thread - stops the running
statement (SQLite ``interrupt()``, PostgreSQL ``cancel()``, MySQL ``KILL QUERY`` from a second connection,
else the connection is closed and re-opened on next use). Cancelled statements fail with ``CANCELLED``.

Connections are stored in ``project.radproj`` under ``"databases"`` (``ConnectionInfo.to_dict``) -
**without passwords**. ``PasswordStore`` keeps a password (only when the user asks) in the IDE settings,
encrypted with Windows DPAPI (or obfuscated on other systems - the UI warns about that).

``AdminerServer`` serves the bundled Adminer (radide/web/adminer/) with ``php -S 127.0.0.1:<private port>``
and builds URLs that log in automatically with a random per-server token.
"""
from __future__ import annotations

import base64
import csv
import datetime as _dt
import decimal
import hashlib
import importlib
import json
import os
import re
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

KINDS = {"sqlite": "SQLite", "mysql": "MySQL / MariaDB", "postgresql": "PostgreSQL"}
SQLITE_EXTS = (".db", ".sqlite", ".sqlite3", ".db3", ".sdb")
DEFAULT_PORTS = {"mysql": 3306, "postgresql": 5432}
KEY_ALIAS = "__radide_key__"          # hidden row key column (SQLite rowid / PostgreSQL ctid)
MAX_RESULT_ROWS = 10000               # rows fetched per query result in the SQL window
CANCELLED = "Cancelled by the user"   # error text of a statement stopped by Database.cancel()

ADMINER_DIR = Path(__file__).resolve().parent.parent / "web" / "adminer"


class DatabaseError(Exception):
    """Any error of a database operation (message ready to show)."""


# =============================================================================== data classes
@dataclass
class ConnectionInfo:
    """A saved connection. ``path`` (SQLite) is relative to the project folder when inside it."""
    name: str
    kind: str = "sqlite"                  # "sqlite" | "mysql" | "postgresql"
    path: str = ""                        # SQLite file
    host: str = "127.0.0.1"
    port: int = 0                         # 0 = default port
    user: str = ""
    database: str = ""
    schema: str = ""                      # PostgreSQL schema ("" = current_schema(), normally public)
    options: dict = field(default_factory=dict)   # extra driver arguments (e.g. {"charset": "utf8mb4"})
    remember_password: bool = False       # the password is in the IDE settings (PasswordStore), never here

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"name": self.name, "kind": self.kind}
        if self.kind == "sqlite":
            d["path"] = self.path
        else:
            d.update(host=self.host, port=self.port or DEFAULT_PORTS.get(self.kind, 0), user=self.user,
                     database=self.database)
            if self.schema:
                d["schema"] = self.schema
            if self.remember_password:
                d["remember_password"] = True
        if self.options:
            d["options"] = dict(self.options)
        return d

    @staticmethod
    def from_dict(d: dict) -> "ConnectionInfo":
        kind = str(d.get("kind") or "sqlite").lower()
        if kind in ("postgres", "pgsql", "pg"):
            kind = "postgresql"
        if kind == "mariadb":
            kind = "mysql"
        try:
            port = int(d.get("port") or 0)
        except (TypeError, ValueError):
            port = 0
        opts = d.get("options") if isinstance(d.get("options"), dict) else {}
        return ConnectionInfo(str(d.get("name") or "Database"), kind if kind in KINDS else "sqlite",
                              str(d.get("path") or ""), str(d.get("host") or "127.0.0.1"), port,
                              str(d.get("user") or ""), str(d.get("database") or ""), str(d.get("schema") or ""),
                              dict(opts), bool(d.get("remember_password")))

    @property
    def needs_password(self) -> bool:
        return self.kind != "sqlite"

    def resolved_path(self, base: Path | None) -> Path:
        p = Path(os.path.expandvars(os.path.expanduser(self.path)))
        if not p.is_absolute() and base is not None:
            p = Path(base) / p
        return p

    def effective_port(self) -> int:
        return int(self.port or DEFAULT_PORTS.get(self.kind, 0))

    def describe(self, base: Path | None = None) -> str:
        if self.kind == "sqlite":
            return f"SQLite: {self.resolved_path(base)}"
        who = f"{self.user}@" if self.user else ""
        return f"{KINDS[self.kind]}: {who}{self.host}:{self.effective_port()}/{self.database}"


@dataclass
class Column:
    name: str
    type: str = ""
    notnull: bool = False
    default: str | None = None            # SQL text of the default (None = no default)
    pk: int = 0                           # position in the primary key (1-based), 0 = not part of it
    autoinc: bool = False                 # AUTOINCREMENT / AUTO_INCREMENT / serial / identity


@dataclass
class Index:
    name: str
    columns: list[str]
    unique: bool = False
    primary: bool = False
    sql: str = ""


@dataclass
class ForeignKey:
    columns: list[str]
    ref_table: str
    ref_columns: list[str]
    on_delete: str = ""
    on_update: str = ""


@dataclass
class ColumnDef:
    """A column to create (Create Table / Add Column dialogs)."""
    name: str
    type: str = "TEXT"
    pk: bool = False
    notnull: bool = False
    autoinc: bool = False
    unique: bool = False
    default: str = ""                     # "" = none; plain text is quoted unless it is a number/keyword/'..'


@dataclass
class TableData:
    """One page of a table: rows as lists, plus the key that identifies each row for update/delete."""
    table: str
    columns: list[Column]
    rows: list[list]
    keys: list[dict]                      # per row: {column: original value} or {KEY_ALIAS: rowid/ctid}
    total: int = 0
    offset: int = 0
    editable: bool = True

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]


@dataclass
class Result:
    """The outcome of one statement of the SQL window."""
    statement: str
    columns: list[str] = field(default_factory=list)
    rows: list[tuple] = field(default_factory=list)
    rowcount: int = -1
    elapsed: float = 0.0                  # seconds
    error: str = ""
    line: int = 1                         # 1-based line of the statement in the script
    truncated: bool = False

    @property
    def is_query(self) -> bool:
        return bool(self.columns)

    @property
    def ok(self) -> bool:
        return not self.error

    def message(self) -> str:
        ms = f"{self.elapsed * 1000:.0f} ms"
        if self.error:
            return f"Line {self.line}: error: {self.error}"
        if self.is_query:
            more = f" (first {len(self.rows)} shown)" if self.truncated else ""
            return f"Line {self.line}: {len(self.rows)} row(s){more} - {ms}"
        n = "" if self.rowcount is None or self.rowcount < 0 else f"{self.rowcount} row(s) affected - "
        return f"Line {self.line}: {n or 'OK - '}{ms}"


# =============================================================================== SQL helpers
_KEYWORD_DEFAULTS = {"NULL", "TRUE", "FALSE", "CURRENT_TIMESTAMP", "CURRENT_DATE", "CURRENT_TIME", "NOW()",
                     "LOCALTIMESTAMP", "LOCALTIME"}


def default_sql(text: str) -> str:
    """SQL for a default value typed in a dialog: numbers, 'quoted', keywords and (expressions) stay,
    anything else becomes a string literal."""
    t = (text or "").strip()
    if not t:
        return ""
    if re.fullmatch(r"[+-]?\d+(\.\d+)?([eE][+-]?\d+)?", t) or t.upper() in _KEYWORD_DEFAULTS:
        return t
    if (t.startswith("'") and t.endswith("'") and len(t) >= 2) or (t.startswith("(") and t.endswith(")")):
        return t
    if re.fullmatch(r"\w+\(.*\)", t):               # function call: now(), gen_random_uuid(), datetime('now')
        return t
    return "'" + t.replace("'", "''") + "'"


def split_sql(text: str, dialect: str = "sqlite") -> list[tuple[str, int]]:
    """Split a script into statements -> [(statement, 1-based start line)]. Understands '...', "...",
    `...`, -- and /* */ comments, MySQL # comments, PostgreSQL $tag$...$tag$ bodies, MySQL DELIMITER
    and SQLite CREATE TRIGGER ... BEGIN ... END."""
    out: list[tuple[str, int]] = []
    i, n = 0, len(text)
    start = 0
    delim = ";"
    depth_begin = 0                                 # SQLite/MySQL trigger BEGIN ... END nesting
    word_rx = re.compile(r"[A-Za-z_]+")

    def push(end: int):
        stmt = text[start:end].strip()
        if stmt and not _only_comments(stmt):
            first = start + _code_start(text[start:end])
            out.append((stmt, text.count("\n", 0, first) + 1))

    while i < n:
        ch = text[i]
        if ch in "'\"`":
            j = i + 1
            while j < n:
                if text[j] == "\\" and dialect == "mysql" and ch != "`":
                    j += 2
                    continue
                if text[j] == ch:
                    if j + 1 < n and text[j + 1] == ch:   # doubled quote
                        j += 2
                        continue
                    break
                j += 1
            i = j + 1
            continue
        if text.startswith("--", i) or (ch == "#" and dialect == "mysql"):
            j = text.find("\n", i)
            i = n if j < 0 else j + 1
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if ch == "$" and dialect == "postgresql":
            m = re.match(r"\$([A-Za-z_]\w*)?\$", text[i:])
            if m:
                tag = m.group(0)
                j = text.find(tag, i + len(tag))
                i = n if j < 0 else j + len(tag)
                continue
        if dialect == "mysql" and (i == 0 or text[i - 1] == "\n"):
            m = re.match(r"[ \t]*DELIMITER[ \t]+(\S+)[ \t]*(\r?\n|$)", text[i:], re.IGNORECASE)
            if m:
                push(i)
                delim = m.group(1)
                i += m.end()
                start = i
                continue
        if ch.isalpha() or ch == "_":
            m = word_rx.match(text, i)
            w = m.group(0).upper()
            if dialect in ("sqlite", "mysql") and delim == ";":
                if w in ("BEGIN", "CASE") and _inside_trigger(text[start:i]):
                    depth_begin += 1
                elif w == "END" and depth_begin:
                    depth_begin -= 1
            i = m.end()
            continue
        if text.startswith(delim, i) and depth_begin == 0:
            push(i)
            i += len(delim)
            start = i
            continue
        i += 1
    push(n)
    return out


def _inside_trigger(prefix: str) -> bool:
    return bool(re.search(r"\bCREATE\s+(TEMP\w*\s+)?TRIGGER\b", prefix, re.IGNORECASE))


def _code_start(chunk: str) -> int:
    """Offset of the first character that is not white space or a comment."""
    i = 0
    while i < len(chunk):
        if chunk[i].isspace():
            i += 1
        elif chunk.startswith("--", i) or chunk.startswith("#", i):
            j = chunk.find("\n", i)
            i = len(chunk) if j < 0 else j + 1
        elif chunk.startswith("/*", i):
            j = chunk.find("*/", i + 2)
            i = len(chunk) if j < 0 else j + 2
        else:
            return i
    return 0


def _only_comments(stmt: str) -> bool:
    s = re.sub(r"/\*.*?\*/", "", stmt, flags=re.DOTALL)
    s = re.sub(r"(--|#)[^\n]*", "", s)
    return not s.strip()


def _infer_type(values: Iterable[str]) -> str:
    kind = "INTEGER"
    seen = False
    for v in values:
        v = (v or "").strip()
        if not v:
            continue
        seen = True
        if kind == "INTEGER" and not re.fullmatch(r"[+-]?\d{1,18}", v):
            kind = "REAL"
        if kind == "REAL" and not re.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?", v):
            return "TEXT"
    return kind if seen else "TEXT"


def display_value(v) -> str:
    """Text shown in grids for a value."""
    if v is None:
        return "NULL"
    if isinstance(v, (bytes, bytearray, memoryview)):
        b = bytes(v)
        return f"<BLOB {len(b)} bytes>" if len(b) > 32 else "0x" + b.hex()
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(v)
    return str(v)


def _remove_partial(path) -> None:
    """Delete the half-written file of a failed / cancelled export."""
    try:
        Path(path).unlink()
    except OSError:
        pass


def _read_text_file(path: Path) -> str:
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1256", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


# =============================================================================== base adapter
class Database:
    """Common interface of every adapter. Subclasses fill the introspection queries and dialect bits."""
    kind = ""
    dialect = ""
    placeholder = "?"
    quote_char = '"'
    hidden_key = ""                 # SQL expression of a hidden row key ("rowid", "ctid") - "" = none
    types: list[str] = []           # column types offered by the dialogs
    dump_prologue = ""              # written before / after the tables of an SQL export
    dump_epilogue = ""

    def __init__(self, info: ConnectionInfo):
        self.info = info
        self.conn = None
        self._cancel = False                # set by cancel() (any thread), cleared by reset_cancel()
        self.conn_lost = False              # cancel() had to close the connection: reconnect on next use

    # ------------------------------------------------------------------ connection
    def connect(self):
        raise NotImplementedError

    def clone(self) -> "Database":
        """A new, not yet connected adapter for the same database (own connection / session).

        The UI gives every worker its own connection: DB-API connections must not be used by two
        threads at the same time, and a slow statement on one connection must not block the others."""
        raise NotImplementedError

    def close(self) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:  # noqa: BLE001 - closing a dead connection
                pass
        self.conn = None
        self.conn_lost = False

    # ------------------------------------------------------------------ cancel (thread-safe)
    @property
    def cancel_requested(self) -> bool:
        return self._cancel

    def reset_cancel(self) -> None:
        self._cancel = False

    def check_cancel(self) -> None:
        if self._cancel:
            raise DatabaseError(CANCELLED)

    def cancel(self) -> str:
        """Stop the statement running on this connection. Called from ANOTHER thread than the one
        running it (the UI thread). Returns how it was done: "idle", "interrupted", "cancelled",
        "killed" or "closed" (the connection had to be closed - it reconnects on next use)."""
        self._cancel = True
        conn = self.conn
        if conn is None:
            return "idle"
        try:
            return self._interrupt(conn)
        except Exception:  # noqa: BLE001 - the driver cannot cancel: drop the connection
            return self._force_close(conn)

    def _interrupt(self, conn) -> str:
        """Driver-specific cancel of the running statement (override)."""
        return self._force_close(conn)

    def _force_close(self, conn) -> str:
        self.conn_lost = True
        sock = getattr(conn, "_sock", None)            # PyMySQL
        try:
            if sock is not None and hasattr(sock, "shutdown"):
                sock.shutdown(socket.SHUT_RDWR)        # wakes up a thread blocked reading the socket
            else:
                conn.close()
        except Exception:  # noqa: BLE001
            pass
        return "closed"

    def _error(self, e: Exception) -> str:
        """Error text of a driver exception ("Cancelled by the user" after cancel())."""
        if self._cancel:
            return CANCELLED
        return self._error_text(e)

    @property
    def connected(self) -> bool:
        return self.conn is not None

    def __enter__(self):
        if self.conn is None:
            self.connect()
        return self

    def __exit__(self, *exc):
        self.close()

    def _cur(self):
        if self.conn_lost:
            self.close()
        if self.conn is None:
            self.connect()
        return self.conn.cursor()

    def _run(self, sql: str, params: Iterable | None = None) -> tuple[list[str], list[tuple], int]:
        """Execute one statement -> (column names, rows, rowcount). Raises DatabaseError."""
        cur = self._cur()
        try:
            if params is None:
                cur.execute(sql)
            else:
                cur.execute(sql, tuple(params))
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = [tuple(r) for r in cur.fetchall()] if cols else []
            return cols, rows, cur.rowcount
        except DatabaseError:
            raise
        except Exception as e:  # noqa: BLE001 - every driver has its own exception classes
            raise DatabaseError(self._error(e)) from e
        finally:
            try:
                cur.close()
            except Exception:  # noqa: BLE001
                pass

    def _rows(self, sql: str, params: Iterable | None = None) -> list[tuple]:
        return self._run(sql, params)[1]

    @staticmethod
    def _error_text(e: Exception) -> str:
        args = getattr(e, "args", ())
        if len(args) == 2 and isinstance(args[0], int):          # PyMySQL: (code, message)
            return f"({args[0]}) {args[1]}"
        return str(e).strip() or type(e).__name__

    def begin(self) -> None:
        self._run("BEGIN")

    def commit(self) -> None:
        self._run("COMMIT")

    def rollback(self) -> None:
        try:
            self._run("ROLLBACK")
        except DatabaseError:
            pass

    # ------------------------------------------------------------------ quoting
    def q(self, name: str) -> str:
        c = self.quote_char
        return c + str(name).replace(c, c + c) + c

    def literal(self, v) -> str:
        """SQL literal for exports."""
        if v is None:
            return "NULL"
        if isinstance(v, bool):
            return ("TRUE" if v else "FALSE") if self.dialect == "postgresql" else ("1" if v else "0")
        if isinstance(v, (int, float, decimal.Decimal)) and not isinstance(v, bool):
            if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
                return "NULL"
            return str(v)
        if isinstance(v, (bytes, bytearray, memoryview)):
            b = bytes(v)
            if self.dialect == "postgresql":
                return "'\\x" + b.hex() + "'::bytea"
            return "X'" + b.hex() + "'"
        if isinstance(v, (_dt.datetime, _dt.date, _dt.time)):
            v = v.isoformat(sep=" ") if isinstance(v, _dt.datetime) else v.isoformat()
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        s = str(v).replace("'", "''")
        if self.dialect == "mysql":
            s = s.replace("\\", "\\\\")
        return "'" + s + "'"

    # ------------------------------------------------------------------ introspection (override)
    def tables(self) -> list[str]:
        raise NotImplementedError

    def views(self) -> list[str]:
        return []

    def columns(self, table: str) -> list[Column]:
        raise NotImplementedError

    def indexes(self, table: str) -> list[Index]:
        return []

    def foreign_keys(self, table: str) -> list[ForeignKey]:
        return []

    def create_sql(self, table: str) -> str:
        return self.ddl_create_table(table, [ColumnDef(c.name, c.type, c.pk > 0, c.notnull, c.autoinc,
                                                       False, c.default or "") for c in self.columns(table)],
                                     raw_defaults=True)

    def server_version(self) -> str:
        return ""

    def is_view(self, table: str) -> bool:
        return table in self.views()

    def primary_key(self, table: str, cols: list[Column] | None = None) -> list[str]:
        cols = cols if cols is not None else self.columns(table)
        return [c.name for c in sorted((c for c in cols if c.pk), key=lambda c: c.pk)]

    # ------------------------------------------------------------------ data
    def count(self, table: str, where: str = "") -> int:
        sql = f"SELECT COUNT(*) FROM {self.q(table)}" + (f" WHERE {where}" if where.strip() else "")
        rows = self._rows(sql)
        return int(rows[0][0]) if rows else 0

    def _limit(self, limit: int, offset: int) -> str:
        return f" LIMIT {int(limit)} OFFSET {int(offset)}"

    def select(self, table: str, limit: int = 200, offset: int = 0, order_by: str = "",
               descending: bool = False, where: str = "") -> TableData:
        cols = self.columns(table)
        view = self.is_view(table)
        pk = [] if view else self.primary_key(table, cols)
        names = [self.q(c.name) for c in cols]
        hidden = bool(not pk and not view and self.hidden_key)
        sel = ", ".join(([f"{self.hidden_key_select()} AS {self.q(KEY_ALIAS)}"] if hidden else []) + names)
        sql = f"SELECT {sel or '*'} FROM {self.q(table)}"
        if where.strip():
            sql += f" WHERE {where}"
        if order_by:
            sql += f" ORDER BY {self.q(order_by)}{' DESC' if descending else ''}"
        elif pk:
            sql += " ORDER BY " + ", ".join(self.q(k) for k in pk)
        sql += self._limit(limit, offset)
        _cols, raw, _n = self._run(sql)
        rows, keys = [], []
        cnames = [c.name for c in cols]
        for r in raw:
            r = list(r)
            if hidden:
                keys.append({KEY_ALIAS: r[0]})
                r = r[1:]
            elif pk:
                keys.append({k: r[cnames.index(k)] for k in pk})
            else:
                keys.append(dict(zip(cnames, r)))
            rows.append(r)
        total = self.count(table, where)
        return TableData(table, cols, rows, keys, total, offset, editable=not view)

    def hidden_key_select(self) -> str:
        return self.hidden_key

    def _key_where(self, key: dict) -> tuple[str, list]:
        parts, params = [], []
        for k, v in key.items():
            if k == KEY_ALIAS:
                parts.append(self.hidden_key_where())
                params.append(v)
            elif v is None:
                parts.append(f"{self.q(k)} IS NULL")
            else:
                parts.append(f"{self.q(k)} = {self.placeholder}")
                params.append(v)
        if not parts:
            raise DatabaseError("This row cannot be identified (no key)")
        return " AND ".join(parts), params

    def hidden_key_where(self) -> str:
        return f"{self.hidden_key} = {self.placeholder}"

    def _one_row_suffix(self, key: dict) -> str:
        """Tables without a key are matched on all their values: change only one of the equal rows."""
        return ""

    def insert_row(self, table: str, values: dict) -> Any:
        """Insert a row (columns missing from ``values`` get their defaults). Returns the new row id if known."""
        values = {k: v for k, v in values.items()}
        if values:
            cols = ", ".join(self.q(k) for k in values)
            marks = ", ".join([self.placeholder] * len(values))
            sql = f"INSERT INTO {self.q(table)} ({cols}) VALUES ({marks})"
        else:
            sql = self._insert_defaults_sql(table)
        return self._insert(sql, list(values.values()))

    def _insert_defaults_sql(self, table: str) -> str:
        return f"INSERT INTO {self.q(table)} DEFAULT VALUES"

    def _insert(self, sql: str, params: list):
        cur = self._cur()
        try:
            cur.execute(sql, tuple(params))
            return getattr(cur, "lastrowid", None)
        except Exception as e:  # noqa: BLE001
            raise DatabaseError(self._error(e)) from e
        finally:
            cur.close()

    def update_row(self, table: str, key: dict, values: dict) -> int:
        if not values:
            return 0
        sets = ", ".join(f"{self.q(k)} = {self.placeholder}" for k in values)
        where, wp = self._key_where(key)
        sql = f"UPDATE {self.q(table)} SET {sets} WHERE {where}{self._one_row_suffix(key)}"
        n = self._run(sql, list(values.values()) + wp)[2]
        if n == 0:
            raise DatabaseError("The row was not found (changed or deleted by someone else?) - refresh the data")
        return n

    def delete_row(self, table: str, key: dict) -> int:
        where, wp = self._key_where(key)
        return self._run(f"DELETE FROM {self.q(table)} WHERE {where}{self._one_row_suffix(key)}", wp)[2]

    def delete_rows(self, table: str, keys: list[dict]) -> int:
        n = 0
        self.begin()
        try:
            for k in keys:
                n += max(0, self.delete_row(table, k) or 0)
            self.commit()
        except Exception:
            self.rollback()
            raise
        return n

    def coerce(self, column: Column | None, text: str):
        """Value to store for text typed in the grid ("" stays "", the grid has 'Set to NULL')."""
        if column is None or not isinstance(text, str):
            return text
        t = (column.type or "").upper()
        s = text.strip()
        if re.search(r"INT|SERIAL", t) and re.fullmatch(r"[+-]?\d+", s):
            return int(s)
        if re.search(r"REAL|FLOA|DOUB|NUMERIC|DECIMAL", t) and re.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?", s):
            return float(s) if self.dialect == "sqlite" else s
        if re.search(r"BOOL", t) and s.lower() in ("true", "false", "1", "0", "yes", "no"):
            b = s.lower() in ("true", "1", "yes")
            return b if self.dialect == "postgresql" else int(b)
        return text

    # ------------------------------------------------------------------ SQL window
    def execute(self, script: str, max_rows: int = MAX_RESULT_ROWS, stop_on_error: bool = True) -> list[Result]:
        results: list[Result] = []
        for stmt, line in split_sql(script, self.dialect):
            r = Result(stmt, line=line)
            if self._cancel:                            # cancelled between two statements
                r.error = CANCELLED
                results.append(r)
                break
            t0 = time.perf_counter()
            cur = None
            try:
                cur = self._cur()
                cur.execute(stmt)
                if cur.description:
                    r.columns = [d[0] for d in cur.description]
                    rows = cur.fetchmany(max_rows + 1)
                    r.truncated = len(rows) > max_rows
                    r.rows = [tuple(x) for x in rows[:max_rows]]
                r.rowcount = cur.rowcount
            except Exception as e:  # noqa: BLE001
                r.error = self._error(e)
            finally:
                if cur is not None:
                    try:
                        cur.close()
                    except Exception:  # noqa: BLE001
                        pass
            r.elapsed = time.perf_counter() - t0
            results.append(r)
            if r.error and stop_on_error:
                break
        return results

    # ------------------------------------------------------------------ DDL
    def column_sql(self, c: ColumnDef, single_pk: bool, raw_default: bool = False) -> str:
        parts = [self.q(c.name), c.type or "TEXT"]
        if c.pk and single_pk:
            parts.append("PRIMARY KEY")
            if c.autoinc:
                parts.append("AUTOINCREMENT")
        if c.notnull and not (c.pk and single_pk):
            parts.append("NOT NULL")
        if c.unique and not c.pk:
            parts.append("UNIQUE")
        d = c.default if raw_default else default_sql(c.default)
        if d:
            parts.append(f"DEFAULT {d}")
        return " ".join(parts)

    def ddl_create_table(self, table: str, cols: list[ColumnDef], raw_defaults: bool = False) -> str:
        if not table.strip():
            raise DatabaseError("The table needs a name")
        if not cols:
            raise DatabaseError("The table needs at least one column")
        names = [c.name.strip() for c in cols]
        if any(not n for n in names):
            raise DatabaseError("Every column needs a name")
        dup = {n.lower() for n in names if [m.lower() for m in names].count(n.lower()) > 1}
        if dup:
            raise DatabaseError("Duplicate column name: " + ", ".join(sorted(dup)))
        pks = [c for c in cols if c.pk]
        single = len(pks) == 1
        body = [self.column_sql(c, single, raw_defaults) for c in cols]
        if len(pks) > 1:
            body.append("PRIMARY KEY (" + ", ".join(self.q(c.name) for c in pks) + ")")
        return f"CREATE TABLE {self.q(table)} (\n  " + ",\n  ".join(body) + "\n)"

    def create_table(self, table: str, cols: list[ColumnDef]) -> str:
        sql = self.ddl_create_table(table, cols)
        self._run(sql)
        return sql

    def ddl_add_column(self, table: str, c: ColumnDef) -> str:
        return f"ALTER TABLE {self.q(table)} ADD COLUMN {self.column_sql(c, True)}"

    def add_column(self, table: str, c: ColumnDef) -> str:
        if not c.name.strip():
            raise DatabaseError("The column needs a name")
        sql = self.ddl_add_column(table, c)
        self._run(sql)
        return sql

    def drop_column(self, table: str, column: str) -> str:
        sql = f"ALTER TABLE {self.q(table)} DROP COLUMN {self.q(column)}"
        self._run(sql)
        return sql

    def rename_table(self, table: str, new: str) -> str:
        sql = f"ALTER TABLE {self.q(table)} RENAME TO {self.q(new)}"
        self._run(sql)
        return sql

    def drop_table(self, table: str) -> str:
        sql = f"DROP {'VIEW' if self.is_view(table) else 'TABLE'} {self.q(table)}"
        self._run(sql)
        return sql

    # ------------------------------------------------------------------ export / import
    def _all_rows(self, table: str, batch: int = 5000):
        cols = self.columns(table)
        names = ", ".join(self.q(c.name) for c in cols) or "*"
        order = self.primary_key(table, cols)
        sql = f"SELECT {names} FROM {self.q(table)}"
        if order and not self.is_view(table):
            sql += " ORDER BY " + ", ".join(self.q(k) for k in order)
        cur = self._cur()
        try:
            cur.execute(sql)
            while True:
                self.check_cancel()
                chunk = cur.fetchmany(batch)
                if not chunk:
                    break
                yield from chunk
        except DatabaseError:
            raise
        except Exception as e:  # noqa: BLE001
            raise DatabaseError(self._error(e)) from e
        finally:
            cur.close()

    def export_csv(self, table: str, path: Path, delimiter: str = ",", header: bool = True) -> int:
        cols = [c.name for c in self.columns(table)]
        n = 0
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:     # BOM: Excel shows Arabic correctly
                w = csv.writer(f, delimiter=delimiter)
                if header:
                    w.writerow(cols)
                for row in self._all_rows(table):
                    w.writerow(["" if v is None else (bytes(v).hex() if isinstance(v, (bytes, bytearray, memoryview))
                                                      else v) for v in row])
                    n += 1
        except DatabaseError:
            _remove_partial(path)
            raise
        return n

    def dump_table_sql(self, table: str, schema: bool = True, data: bool = True) -> Iterable[str]:
        if schema:
            yield f"-- Table {table}\n"
            yield f"DROP {'VIEW' if self.is_view(table) else 'TABLE'} IF EXISTS {self.q(table)};\n"
            yield self.create_sql(table).rstrip().rstrip(";") + ";\n"
            if not self.is_view(table):
                for ix in self.indexes(table):
                    if ix.sql and not ix.primary:
                        yield ix.sql.rstrip().rstrip(";") + ";\n"
        if data and not self.is_view(table):
            cols = [c.name for c in self.columns(table)]
            head = f"INSERT INTO {self.q(table)} (" + ", ".join(self.q(c) for c in cols) + ") VALUES "
            for row in self._all_rows(table):
                yield head + "(" + ", ".join(self.literal(v) for v in row) + ");\n"
        yield "\n"

    def export_sql(self, table: str | None, path: Path, schema: bool = True, data: bool = True) -> int:
        """Write ``table`` (or every table and view when None) as SQL. Returns the number of tables."""
        tables = [table] if table else self.tables() + self.views()
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(f"-- Exported by RAD IDE from {self.info.describe()} on "
                        f"{_dt.datetime.now().isoformat(sep=' ', timespec='seconds')}\n\n")
                f.write(self.dump_prologue)
                for t in tables:
                    self.check_cancel()
                    for chunk in self.dump_table_sql(t, schema, data):
                        f.write(chunk)
                f.write(self.dump_epilogue)
        except DatabaseError:
            _remove_partial(path)
            raise
        return len(tables)

    def import_csv(self, table: str, path: Path, header: bool = True, create: bool = False,
                   delimiter: str | None = None, empty_as_null: bool = True) -> int:
        """Load a CSV file into ``table`` (created with inferred column types when ``create``).
        Columns are matched by header name (case-insensitive) when the table exists, else by position."""
        text = _read_text_file(Path(path))
        if delimiter is None:
            try:
                delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
            except csv.Error:
                delimiter = ","
        rows = [r for r in csv.reader(text.splitlines(), delimiter=delimiter) if r]
        if not rows:
            return 0
        head = rows.pop(0) if header else [f"Column{i + 1}" for i in range(len(rows[0]))]
        head = [h.strip() or f"Column{i + 1}" for i, h in enumerate(head)]
        exists = table in self.tables()
        if not exists:
            if not create:
                raise DatabaseError(f"Table {table!r} does not exist")
            defs = [ColumnDef(h, self._sql_type(_infer_type(r[i] if i < len(r) else "" for r in rows)))
                    for i, h in enumerate(head)]
            self.create_table(table, defs)
            targets = head
        else:
            existing = [c.name for c in self.columns(table)]
            low = {c.lower(): c for c in existing}
            if header and all(h.lower() in low for h in head):
                targets = [low[h.lower()] for h in head]
            elif len(head) <= len(existing):
                targets = existing[:len(head)]
            else:
                raise DatabaseError(f"The CSV has {len(head)} columns, the table {len(existing)}")
        cols = {c.name: c for c in self.columns(table)}
        sql = (f"INSERT INTO {self.q(table)} (" + ", ".join(self.q(t) for t in targets) + ") VALUES ("
               + ", ".join([self.placeholder] * len(targets)) + ")")
        data = []
        for r in rows:
            r = (r + [""] * len(targets))[:len(targets)]
            data.append(tuple(None if (empty_as_null and v == "") else self.coerce(cols.get(t), v)
                              for t, v in zip(targets, r)))
        self.check_cancel()
        cur = self._cur()
        self.begin()
        try:
            cur.executemany(sql, data)
            self.commit()
        except Exception as e:  # noqa: BLE001
            self.rollback()
            raise DatabaseError(self._error(e)) from e
        finally:
            cur.close()
        return len(data)

    def _sql_type(self, generic: str) -> str:
        return generic


# =============================================================================== SQLite
class SQLiteDatabase(Database):
    kind = dialect = "sqlite"
    placeholder = "?"
    hidden_key = "rowid"
    types = ["INTEGER", "TEXT", "REAL", "NUMERIC", "BLOB", "BOOLEAN", "DATE", "DATETIME", "VARCHAR(255)"]

    def __init__(self, info: ConnectionInfo | str | Path, base: Path | None = None, create: bool = True):
        if not isinstance(info, ConnectionInfo):
            info = ConnectionInfo(Path(info).stem, "sqlite", str(info))
        super().__init__(info)
        self.path = info.resolved_path(base)
        self.create = create

    def connect(self):
        if not self.create and not self.path.exists():
            raise DatabaseError(f"Database file not found: {self.path}")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(self.path), isolation_level=None, check_same_thread=False)
            self.conn.execute("PRAGMA foreign_keys = ON")
        except Exception as e:  # noqa: BLE001
            self.conn = None
            raise DatabaseError(f"{self.path}: {e}") from e
        return self

    def clone(self) -> "SQLiteDatabase":
        c = SQLiteDatabase(self.info, None, self.create)
        c.path = self.path
        return c

    def _interrupt(self, conn) -> str:
        conn.interrupt()                    # documented as safe to call from another thread
        return "interrupted"

    def server_version(self) -> str:
        return "SQLite " + sqlite3.sqlite_version

    def tables(self) -> list[str]:
        return [r[0] for r in self._rows("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE "
                                         "'sqlite_%' ORDER BY name COLLATE NOCASE")]

    def views(self) -> list[str]:
        return [r[0] for r in self._rows("SELECT name FROM sqlite_master WHERE type = 'view' ORDER BY name "
                                         "COLLATE NOCASE")]

    def is_view(self, table: str) -> bool:
        return bool(self._rows("SELECT 1 FROM sqlite_master WHERE type = 'view' AND name = ?", [table]))

    def columns(self, table: str) -> list[Column]:
        rows = self._rows(f"PRAGMA table_xinfo({self.q(table)})")
        cols = [Column(r[1], r[2] or "", bool(r[3]), r[4], int(r[5] or 0)) for r in rows if int(r[6] or 0) == 0]
        pks = [c for c in cols if c.pk]
        if len(pks) == 1 and pks[0].type.upper() == "INTEGER":
            pks[0].autoinc = True                  # INTEGER PRIMARY KEY = rowid alias, filled automatically
        return cols

    def indexes(self, table: str) -> list[Index]:
        out = []
        for r in self._rows(f"PRAGMA index_list({self.q(table)})"):
            name, unique, origin = r[1], bool(r[2]), (r[3] if len(r) > 3 else "c")
            cols = [x[2] for x in self._rows(f"PRAGMA index_info({self.q(name)})")]
            sql = self._rows("SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?", [name])
            out.append(Index(name, cols, unique, origin == "pk", (sql[0][0] or "") if sql else ""))
        return out

    def foreign_keys(self, table: str) -> list[ForeignKey]:
        groups: dict[int, ForeignKey] = {}
        for r in self._rows(f"PRAGMA foreign_key_list({self.q(table)})"):
            fk = groups.setdefault(r[0], ForeignKey([], r[2], [], r[6], r[5]))
            fk.columns.append(r[3])
            fk.ref_columns.append(r[4] or "")
        return list(groups.values())

    def create_sql(self, table: str) -> str:
        rows = self._rows("SELECT sql FROM sqlite_master WHERE name = ? AND type IN ('table', 'view')", [table])
        return (rows[0][0] or "") if rows else ""

    def _insert(self, sql: str, params: list):
        if self.conn is None:
            self.connect()
        try:
            return self.conn.execute(sql, params).lastrowid
        except Exception as e:  # noqa: BLE001
            raise DatabaseError(self._error(e)) from e

    def _sql_type(self, generic: str) -> str:
        return generic

    def databases(self) -> list[str]:
        return ["main"]


# =============================================================================== server databases
class _ServerDatabase(Database):
    """MySQL / PostgreSQL: a DB-API driver module imported on first use (or given, e.g. a test mock)."""
    driver_name = ""
    install_hint = ""

    def __init__(self, info: ConnectionInfo, password: str = "", driver=None):
        super().__init__(info)
        self.password = password or ""
        self._driver = driver

    def clone(self) -> "_ServerDatabase":
        return type(self)(self.info, self.password, self._driver)

    def driver(self):
        if self._driver is None:
            try:
                self._driver = importlib.import_module(self.driver_name)
            except ImportError as e:
                raise DatabaseError(f"{KINDS[self.kind]} needs the Python package '{self.driver_name}' "
                                    f"({self.install_hint})") from e
        return self._driver


# =============================================================================== MySQL / MariaDB
class MySQLDatabase(_ServerDatabase):
    kind = dialect = "mysql"
    placeholder = "%s"
    quote_char = "`"
    # tables are dumped by name, so a parent can be dropped / filled before its children: re-importing a
    # dump with foreign keys only works with the checks off (what mysqldump writes too)
    dump_prologue = "SET FOREIGN_KEY_CHECKS=0;\n\n"
    dump_epilogue = "SET FOREIGN_KEY_CHECKS=1;\n"
    types = ["INT", "BIGINT", "VARCHAR(255)", "TEXT", "LONGTEXT", "DECIMAL(10,2)", "DOUBLE", "DATE", "DATETIME",
             "TIMESTAMP", "BOOLEAN", "BLOB", "JSON"]
    driver_name = "pymysql"
    install_hint = "pip install pymysql"

    def connect(self):
        drv = self.driver()
        kw = dict(host=self.info.host or "127.0.0.1", port=self.info.effective_port(), user=self.info.user,
                  password=self.password, charset="utf8mb4", autocommit=True, connect_timeout=10)
        if self.info.database:
            kw["database"] = self.info.database
        kw.update(self.info.options or {})
        try:
            self.conn = drv.connect(**kw)
        except Exception as e:  # noqa: BLE001
            self.conn = None
            raise DatabaseError(self._error(e)) from e
        return self

    def _interrupt(self, conn) -> str:
        """PyMySQL cannot cancel by itself: KILL QUERY <thread id> from a second connection."""
        tid = int(conn.thread_id())
        killer = self.clone()
        try:
            killer.connect()
            killer._run(f"KILL QUERY {tid}")
        finally:
            killer.close()
        return "killed"

    def server_version(self) -> str:
        rows = self._rows("SELECT VERSION()")
        return f"MySQL {rows[0][0]}" if rows else "MySQL"

    def begin(self) -> None:
        self._run("START TRANSACTION")

    def databases(self) -> list[str]:
        return [r[0] for r in self._rows("SHOW DATABASES")]

    def _full_tables(self) -> list[tuple]:
        return self._rows("SHOW FULL TABLES")

    def tables(self) -> list[str]:
        return sorted((r[0] for r in self._full_tables() if str(r[1]).upper() != "VIEW"), key=str.lower)

    def views(self) -> list[str]:
        return sorted((r[0] for r in self._full_tables() if str(r[1]).upper() == "VIEW"), key=str.lower)

    def is_view(self, table: str) -> bool:
        return table in self.views()

    def columns(self, table: str) -> list[Column]:
        rows = self._rows("SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_KEY, EXTRA "
                          "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                          "ORDER BY ORDINAL_POSITION", [table])
        pk_order = [r[0] for r in self._rows(
            "SELECT COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = %s AND CONSTRAINT_NAME = 'PRIMARY' ORDER BY ORDINAL_POSITION", [table])]
        out = []
        for name, ctype, nullable, default, key, extra in rows:
            pk = pk_order.index(name) + 1 if name in pk_order else (1 if str(key) == "PRI" and not pk_order else 0)
            out.append(Column(name, str(ctype), str(nullable).upper() == "NO",
                              None if default is None else str(default), pk,
                              "auto_increment" in str(extra or "").lower()))
        return out

    def indexes(self, table: str) -> list[Index]:
        groups: dict[str, Index] = {}
        for name, col, non_unique, _seq in self._rows(
                "SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE, SEQ_IN_INDEX FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s ORDER BY INDEX_NAME, SEQ_IN_INDEX", [table]):
            ix = groups.setdefault(name, Index(name, [], not int(non_unique), name == "PRIMARY"))
            ix.columns.append(col)
        for ix in groups.values():
            if not ix.primary:
                ix.sql = (f"CREATE {'UNIQUE ' if ix.unique else ''}INDEX {self.q(ix.name)} ON {self.q(table)} ("
                          + ", ".join(self.q(c) for c in ix.columns) + ")")
        return list(groups.values())

    def foreign_keys(self, table: str) -> list[ForeignKey]:
        groups: dict[str, ForeignKey] = {}
        for cname, col, rtable, rcol in self._rows(
                "SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME "
                "FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                "AND REFERENCED_TABLE_NAME IS NOT NULL ORDER BY CONSTRAINT_NAME, ORDINAL_POSITION", [table]):
            fk = groups.setdefault(cname, ForeignKey([], rtable, []))
            fk.columns.append(col)
            fk.ref_columns.append(rcol)
        return list(groups.values())

    def create_sql(self, table: str) -> str:
        rows = self._rows(f"SHOW CREATE TABLE {self.q(table)}")
        return str(rows[0][1]) if rows else ""

    def dump_table_sql(self, table: str, schema: bool = True, data: bool = True) -> Iterable[str]:
        # SHOW CREATE TABLE already contains the indexes
        if schema:
            yield f"-- Table {table}\n"
            yield f"DROP {'VIEW' if self.is_view(table) else 'TABLE'} IF EXISTS {self.q(table)};\n"
            yield self.create_sql(table).rstrip().rstrip(";") + ";\n"
        if data:
            yield from super().dump_table_sql(table, schema=False, data=True)
        else:
            yield "\n"

    def _one_row_suffix(self, key: dict) -> str:
        return " LIMIT 1"

    def _key_where(self, key: dict) -> tuple[str, list]:
        parts, params = [], []
        for k, v in key.items():
            parts.append(f"{self.q(k)} <=> %s")         # NULL-safe equality
            params.append(v)
        if not parts:
            raise DatabaseError("This row cannot be identified (no key)")
        return " AND ".join(parts), params

    def _insert_defaults_sql(self, table: str) -> str:
        return f"INSERT INTO {self.q(table)} () VALUES ()"

    def column_sql(self, c: ColumnDef, single_pk: bool, raw_default: bool = False) -> str:
        parts = [self.q(c.name), c.type or "TEXT"]
        if c.notnull or c.pk:
            parts.append("NOT NULL")
        if c.autoinc:
            parts.append("AUTO_INCREMENT")
        if c.pk and single_pk:
            parts.append("PRIMARY KEY")
        if c.unique and not c.pk:
            parts.append("UNIQUE")
        d = c.default if raw_default else default_sql(c.default)
        if d:
            parts.append(f"DEFAULT {d}")
        return " ".join(parts)

    def ddl_add_column(self, table: str, c: ColumnDef) -> str:
        return f"ALTER TABLE {self.q(table)} ADD COLUMN {self.column_sql(c, True)}"

    def rename_table(self, table: str, new: str) -> str:
        sql = f"RENAME TABLE {self.q(table)} TO {self.q(new)}"
        self._run(sql)
        return sql

    def _sql_type(self, generic: str) -> str:
        return {"INTEGER": "BIGINT", "REAL": "DOUBLE", "TEXT": "TEXT"}.get(generic, generic)


# =============================================================================== PostgreSQL
class PostgresDatabase(_ServerDatabase):
    kind = dialect = "postgresql"
    placeholder = "%s"
    hidden_key = "ctid"
    types = ["integer", "bigint", "serial", "varchar(255)", "text", "numeric(10,2)", "double precision", "boolean",
             "date", "timestamp", "timestamptz", "jsonb", "bytea", "uuid"]
    driver_name = "psycopg"
    install_hint = 'pip install "psycopg[binary]"'

    def connect(self):
        drv = self.driver()
        kw = dict(host=self.info.host or "127.0.0.1", port=self.info.effective_port(), user=self.info.user,
                  password=self.password, dbname=self.info.database or "postgres", autocommit=True,
                  connect_timeout=10)
        kw.update(self.info.options or {})
        try:
            self.conn = drv.connect(**kw)
        except Exception as e:  # noqa: BLE001
            self.conn = None
            raise DatabaseError(self._error(e)) from e
        if self.info.schema:
            self._run(f"SET search_path TO {self.q(self.info.schema)}, public")
        return self

    def _interrupt(self, conn) -> str:
        """psycopg 3: cancel_safe() (3.2+) / cancel() send a cancel request on a separate channel."""
        fn = getattr(conn, "cancel_safe", None) or getattr(conn, "cancel")
        fn()
        return "cancelled"

    def server_version(self) -> str:
        rows = self._rows("SELECT version()")
        return str(rows[0][0]).split(",")[0] if rows else "PostgreSQL"

    def _schema(self) -> tuple[str, list]:
        if self.info.schema:
            return "%s", [self.info.schema]
        return "current_schema()", []

    def databases(self) -> list[str]:
        return [r[0] for r in self._rows("SELECT datname FROM pg_database WHERE NOT datistemplate ORDER BY datname")]

    def _tables_of(self, kind: str) -> list[str]:
        s, p = self._schema()
        return [r[0] for r in self._rows(
            f"SELECT table_name FROM information_schema.tables WHERE table_schema = {s} AND table_type = %s "
            "ORDER BY table_name", p + [kind])]

    def tables(self) -> list[str]:
        return self._tables_of("BASE TABLE")

    def views(self) -> list[str]:
        return self._tables_of("VIEW")

    def is_view(self, table: str) -> bool:
        return table in self.views()

    def columns(self, table: str) -> list[Column]:
        s, p = self._schema()
        rows = self._rows(
            "SELECT column_name, data_type, character_maximum_length, numeric_precision, numeric_scale, "
            f"is_nullable, column_default, is_identity FROM information_schema.columns WHERE table_schema = {s} "
            "AND table_name = %s ORDER BY ordinal_position", p + [table])
        pk_order = [r[0] for r in self._rows(
            "SELECT kcu.column_name FROM information_schema.table_constraints tc JOIN "
            "information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name AND "
            f"tc.table_schema = kcu.table_schema WHERE tc.table_schema = {s} AND tc.table_name = %s "
            "AND tc.constraint_type = 'PRIMARY KEY' ORDER BY kcu.ordinal_position", p + [table])]
        out = []
        for name, dtype, clen, prec, scale, nullable, default, identity in rows:
            t = str(dtype)
            if clen and t in ("character varying", "character"):
                t = f"{'varchar' if t == 'character varying' else 'char'}({clen})"
            elif t == "numeric" and prec:
                t = f"numeric({prec},{scale or 0})"
            auto = str(identity).upper() == "YES" or str(default or "").startswith("nextval(")
            out.append(Column(name, t, str(nullable).upper() == "NO", None if default is None else str(default),
                              pk_order.index(name) + 1 if name in pk_order else 0, auto))
        return out

    def indexes(self, table: str) -> list[Index]:
        s, p = self._schema()
        out = []
        for name, idef in self._rows(f"SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = {s} "
                                     "AND tablename = %s ORDER BY indexname", p + [table]):
            m = re.search(r"\((.*)\)\s*$", idef or "")
            cols = [c.strip().strip('"') for c in m.group(1).split(",")] if m else []
            out.append(Index(name, cols, "UNIQUE" in (idef or "").upper(), name.endswith("_pkey"), idef or ""))
        return out

    def foreign_keys(self, table: str) -> list[ForeignKey]:
        s, p = self._schema()
        groups: dict[str, ForeignKey] = {}
        for cname, col, rtable, rcol in self._rows(
                "SELECT tc.constraint_name, kcu.column_name, ccu.table_name, ccu.column_name FROM "
                "information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu "
                "ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema "
                "JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name "
                f"WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = {s} AND tc.table_name = %s",
                p + [table]):
            fk = groups.setdefault(cname, ForeignKey([], rtable, []))
            fk.columns.append(col)
            fk.ref_columns.append(rcol)
        return list(groups.values())

    def create_sql(self, table: str) -> str:
        if self.is_view(table):
            s, p = self._schema()
            rows = self._rows(f"SELECT view_definition FROM information_schema.views WHERE table_schema = {s} "
                              "AND table_name = %s", p + [table])
            body = str(rows[0][0]).strip().rstrip(";") if rows else "SELECT 1"
            return f"CREATE VIEW {self.q(table)} AS\n{body}"
        cols = self.columns(table)
        defs = []
        for c in cols:
            ctype = c.type
            default = c.default or ""
            if c.autoinc and default.startswith("nextval("):
                ctype = {"integer": "serial", "bigint": "bigserial", "smallint": "smallserial"}.get(ctype, ctype)
                default = ""
            defs.append(ColumnDef(c.name, ctype, c.pk > 0, c.notnull, c.autoinc and not default and
                                  ctype not in ("serial", "bigserial", "smallserial"), False, default))
        sql = self.ddl_create_table(table, defs, raw_defaults=True)
        for fk in self.foreign_keys(table):
            sql = sql[:-2] + (",\n  FOREIGN KEY (" + ", ".join(self.q(c) for c in fk.columns) + f") REFERENCES "
                              f"{self.q(fk.ref_table)} (" + ", ".join(self.q(c) for c in fk.ref_columns) + ")\n)")
        return sql

    def hidden_key_select(self) -> str:
        return "ctid::text"

    def hidden_key_where(self) -> str:
        return "ctid = %s::tid"

    def column_sql(self, c: ColumnDef, single_pk: bool, raw_default: bool = False) -> str:
        parts = [self.q(c.name), c.type or "text"]
        if c.autoinc and c.type.lower() not in ("serial", "bigserial", "smallserial"):
            parts.append("GENERATED BY DEFAULT AS IDENTITY")
        if c.pk and single_pk:
            parts.append("PRIMARY KEY")
        if c.notnull and not (c.pk and single_pk):
            parts.append("NOT NULL")
        if c.unique and not c.pk:
            parts.append("UNIQUE")
        d = c.default if raw_default else default_sql(c.default)
        if d:
            parts.append(f"DEFAULT {d}")
        return " ".join(parts)

    def _insert(self, sql: str, params: list):
        cur = self._cur()
        try:
            cur.execute(sql, tuple(params))
            return None
        except Exception as e:  # noqa: BLE001
            raise DatabaseError(self._error(e)) from e
        finally:
            cur.close()

    def _sql_type(self, generic: str) -> str:
        return {"INTEGER": "bigint", "REAL": "double precision", "TEXT": "text"}.get(generic, generic)


ADAPTERS = {"sqlite": SQLiteDatabase, "mysql": MySQLDatabase, "postgresql": PostgresDatabase}


def driver_available(kind: str) -> bool:
    if kind == "sqlite":
        return True
    name = ADAPTERS[kind].driver_name
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


def open_database(info: ConnectionInfo, base: Path | None = None, password: str = "", driver=None,
                  connect: bool = True) -> Database:
    """The adapter for ``info`` (connected unless ``connect`` is False)."""
    if info.kind == "sqlite":
        db: Database = SQLiteDatabase(info, base)
    elif info.kind in ADAPTERS:
        db = ADAPTERS[info.kind](info, password, driver)
    else:
        raise DatabaseError(f"Unknown database kind {info.kind!r}")
    if connect:
        db.connect()
    return db


# =============================================================================== project connections
class ConnectionManager:
    """The connections of one project (``project.radproj`` "databases") + SQLite files found in its folder."""
    KEY = "databases"

    def __init__(self, project=None, folder: Path | None = None):
        self.project = project
        self.folder = Path(folder) if folder is not None else (Path(project.folder) if project is not None else None)
        self.connections: list[ConnectionInfo] = []
        self.load()

    def _extra(self) -> dict | None:
        return getattr(self.project, "extra", None) if self.project is not None else None

    def load(self) -> list[ConnectionInfo]:
        raw = []
        extra = self._extra()
        if extra is not None:
            raw = extra.get(self.KEY) or []
        self.connections = [ConnectionInfo.from_dict(d) for d in raw if isinstance(d, dict)]
        return self.connections

    def save(self) -> None:
        extra = self._extra()
        if extra is None:
            return
        data = [c.to_dict() for c in self.connections]
        if data:
            extra[self.KEY] = data
        else:
            extra.pop(self.KEY, None)
        if hasattr(self.project, "save"):
            self.project.save()

    def find(self, name: str) -> ConnectionInfo | None:
        for c in self.connections:
            if c.name.lower() == name.lower():
                return c
        return None

    def unique_name(self, base: str) -> str:
        base = base or "Database"
        name, i = base, 2
        while self.find(name):
            name = f"{base}{i}"
            i += 1
        return name

    def relative(self, path: Path | str) -> str:
        p = Path(path)
        if self.folder is not None:
            try:
                return p.resolve().relative_to(self.folder.resolve()).as_posix()
            except ValueError:
                pass
        return str(p)

    def add(self, info: ConnectionInfo, save: bool = True) -> ConnectionInfo:
        if self.find(info.name):
            info.name = self.unique_name(info.name)
        if info.kind == "sqlite" and info.path:
            info.path = self.relative(info.path)
        self.connections.append(info)
        if save:
            self.save()
        return info

    def add_sqlite(self, path: Path | str, name: str = "", save: bool = True) -> ConnectionInfo:
        return self.add(ConnectionInfo(name or Path(path).stem, "sqlite", str(path)), save)

    def remove(self, name: str, save: bool = True) -> bool:
        c = self.find(name)
        if c is None:
            return False
        self.connections.remove(c)
        if save:
            self.save()
        return True

    def replace(self, old_name: str, info: ConnectionInfo) -> None:
        for i, c in enumerate(self.connections):
            if c.name.lower() == old_name.lower():
                if info.kind == "sqlite" and info.path:
                    info.path = self.relative(info.path)
                self.connections[i] = info
                self.save()
                return
        self.add(info)

    def detect_sqlite_files(self, max_files: int = 50) -> list[Path]:
        """SQLite files in the project folder (App_Data, data, db, ...) not yet saved as connections."""
        if self.folder is None or not self.folder.is_dir():
            return []
        known = {os.path.normcase(str(c.resolved_path(self.folder).resolve())) for c in self.connections
                 if c.kind == "sqlite"}
        skip = {".git", "node_modules", "vendor", "__pycache__", ".venv", "venv", ".radide_backup", "bin", "obj"}
        found: list[Path] = []
        for root, dirs, files in os.walk(self.folder):
            dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
            for f in files:
                if f.lower().endswith(SQLITE_EXTS):
                    p = Path(root) / f
                    if os.path.normcase(str(p.resolve())) not in known and is_sqlite_file(p):
                        found.append(p)
                        if len(found) >= max_files:
                            return found
        return sorted(found)

    def base(self) -> Path | None:
        return self.folder


def is_sqlite_file(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            head = f.read(16)
        return head == b"SQLite format 3\x00" or (head == b"" and Path(path).stat().st_size == 0)
    except OSError:
        return False


# =============================================================================== passwords
class PasswordStore:
    """Passwords kept in the IDE settings (never in project files): Windows DPAPI encryption for the
    current Windows user; elsewhere only base64-obfuscated (``secure`` is False - warn the user)."""
    PREFIX = "databases/passwords/"

    def __init__(self, settings):
        self.settings = settings            # QSettings-like: value(key, default) / setValue / remove

    @property
    def secure(self) -> bool:
        return sys.platform == "win32"

    @staticmethod
    def key_for(info: ConnectionInfo, folder: Path | None = None) -> str:
        ident = f"{folder or ''}|{info.kind}|{info.host}|{info.effective_port()}|{info.user}|{info.database}"
        return hashlib.sha1(ident.lower().encode("utf-8")).hexdigest()

    def get(self, info: ConnectionInfo, folder: Path | None = None) -> str | None:
        raw = self.settings.value(self.PREFIX + self.key_for(info, folder), "")
        if not raw:
            return None
        try:
            kind, _, payload = str(raw).partition(":")
            blob = base64.b64decode(payload)
            if kind == "dpapi":
                return _dpapi(blob, encrypt=False).decode("utf-8")
            if kind == "b64":
                return blob.decode("utf-8")
        except Exception:  # noqa: BLE001 - corrupt or from another user: ask again
            return None
        return None

    def set(self, info: ConnectionInfo, password: str, folder: Path | None = None) -> None:
        data = password.encode("utf-8")
        if self.secure:
            value = "dpapi:" + base64.b64encode(_dpapi(data, encrypt=True)).decode("ascii")
        else:
            value = "b64:" + base64.b64encode(data).decode("ascii")
        self.settings.setValue(self.PREFIX + self.key_for(info, folder), value)

    def forget(self, info: ConnectionInfo, folder: Path | None = None) -> None:
        self.settings.remove(self.PREFIX + self.key_for(info, folder))


def _dpapi(data: bytes, encrypt: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    buf = ctypes.create_string_buffer(data, len(data))
    src = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    dst = BLOB()
    entropy_raw = b"RAD IDE databases"
    ebuf = ctypes.create_string_buffer(entropy_raw, len(entropy_raw))
    entropy = BLOB(len(entropy_raw), ctypes.cast(ebuf, ctypes.POINTER(ctypes.c_char)))
    fn = crypt32.CryptProtectData if encrypt else crypt32.CryptUnprotectData
    if encrypt:
        ok = fn(ctypes.byref(src), "RAD IDE", ctypes.byref(entropy), None, None, 0x1, ctypes.byref(dst))
    else:
        ok = fn(ctypes.byref(src), None, ctypes.byref(entropy), None, None, 0x1, ctypes.byref(dst))
    if not ok:
        raise OSError("DPAPI failed")
    try:
        return ctypes.string_at(dst.pbData, dst.cbData)
    finally:
        kernel32.LocalFree(dst.pbData)


# =============================================================================== Adminer
PHP_HINTS = [r"C:\tools\php81\php.exe", r"C:\php\php.exe", r"C:\xampp\php\php.exe", r"C:\laragon\bin\php\php.exe"]


def find_php(configured: str = "") -> str:
    """php.exe: the configured path, PATH, then the usual install folders."""
    if configured and Path(configured).exists():
        return configured
    p = shutil.which("php")
    if p:
        return p
    for h in PHP_HINTS:
        if Path(h).exists():
            return h
    return ""


def free_port() -> int:
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def php_modules(php: str) -> set[str]:
    try:
        out = subprocess.run([php, "-m"], capture_output=True, text=True, timeout=20,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    return {ln.strip().lower() for ln in out.splitlines() if ln.strip() and not ln.startswith("[")}


def php_extension_args(php: str, wanted=("pdo_sqlite", "sqlite3", "mysqli", "pdo_mysql", "pgsql", "pdo_pgsql")
                       ) -> list[str]:
    """``-d extension=...`` for database extensions that php.ini does not load but whose DLL exists."""
    have = php_modules(php)
    try:
        ext_dir = subprocess.run([php, "-r", "echo ini_get('extension_dir');"], capture_output=True, text=True,
                                 timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        ext_dir = ""
    d = Path(ext_dir) if ext_dir else Path(php).parent / "ext"
    if not d.is_absolute():
        d = Path(php).parent / d
    if not d.is_dir():
        d = Path(php).parent / "ext"
    args = []
    for ext in wanted:
        if ext in have:
            continue
        dll = d / (f"php_{ext}.dll" if sys.platform == "win32" else f"{ext}.so")
        if not dll.exists():
            continue
        if ext in ("pgsql", "pdo_pgsql") and sys.platform == "win32" and not (Path(php).parent / "libpq.dll").exists():
            continue
        args += ["-d", f"extension={dll}"]
    return args


ADMINER_DRIVERS = {"sqlite": "sqlite", "mysql": "server", "postgresql": "pgsql"}


class AdminerServer:
    """Serves radide/web/adminer/ with ``php -S 127.0.0.1:<port>``. ``url_for(info)`` gives a URL that
    logs into that connection automatically (token checked by index.php; passwords stay in the server's
    environment, keyed by a hash). Restarted when a new password has to be added."""

    def __init__(self, php: str = "", root: Path = ADMINER_DIR):
        self.php = find_php(php)
        self.root = Path(root)
        self.port = 0
        self.proc: subprocess.Popen | None = None
        self.token = secrets.token_urlsafe(24)
        self.secrets: dict[str, str] = {}
        self.log_path = Path(tempfile.gettempdir()) / f"radide-adminer-{os.getpid()}.log"
        self._log = None

    @property
    def available(self) -> bool:
        return bool(self.php) and (self.root / "adminer.php").exists()

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def start(self, timeout: float = 15.0) -> str:
        if self.running:
            return self.base_url
        if not self.php:
            raise DatabaseError("PHP was not found - install PHP 8 or set its path (Tools > Interpreter Path for "
                                "a PHP project) to use Adminer")
        if not (self.root / "adminer.php").exists():
            raise DatabaseError(f"Adminer is missing: {self.root / 'adminer.php'}")
        self.port = free_port()
        sess = Path(tempfile.gettempdir()) / "radide-adminer-sessions"
        sess.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, RADIDE_ADMINER_TOKEN=self.token, RADIDE_ADMINER_SECRETS=json.dumps(self.secrets))
        args = [self.php, "-S", f"127.0.0.1:{self.port}", "-t", str(self.root),
                "-d", f"session.save_path={sess}", "-d", "display_errors=0", "-d", "memory_limit=512M",
                "-d", "upload_max_filesize=256M", "-d", "post_max_size=256M"]
        args += php_extension_args(self.php)
        self._log = open(self.log_path, "w", encoding="utf-8", errors="replace")
        self.proc = subprocess.Popen(args, cwd=str(self.root), env=env, stdin=subprocess.DEVNULL, stdout=self._log,
                                     stderr=subprocess.STDOUT,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                break
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return self.base_url
            except OSError:
                time.sleep(0.1)
        log = self.read_log()
        self.stop()
        raise DatabaseError("Adminer server did not start:\n" + log[-2000:])

    def read_log(self) -> str:
        try:
            return self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def stop(self) -> None:
        if self.proc is not None:
            if self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(5)
            self.proc = None
        if self._log is not None:
            try:
                self._log.close()
            except OSError:
                pass
            self._log = None

    def url_for(self, info: ConnectionInfo | None, base: Path | None = None, password: str = "") -> str:
        """Start (or restart for a new password) and return the auto-login URL (None = the login page)."""
        if info is None:
            return self.start()
        key = ""
        if info.kind != "sqlite":
            key = hashlib.sha1(f"{info.kind}|{info.host}|{info.effective_port()}|{info.user}".encode()).hexdigest()[:16]
            if self.secrets.get(key) != (password or ""):
                self.secrets[key] = password or ""
                if self.running:
                    self.stop()
        self.start()
        q = {"radide_auth": self.token, "radide_driver": ADMINER_DRIVERS[info.kind], "radide_secret": key}
        if info.kind == "sqlite":
            q.update(radide_server="", radide_user="", radide_db=str(info.resolved_path(base)))
        else:
            host = info.host or "127.0.0.1"
            port = info.effective_port()
            q.update(radide_server=f"{host}:{port}" if port and port != DEFAULT_PORTS[info.kind] else host,
                     radide_user=info.user, radide_db=info.database)
        return self.base_url + "?" + urllib.parse.urlencode(q)

    def __del__(self):
        try:
            self.stop()
        except Exception:  # noqa: BLE001
            pass
