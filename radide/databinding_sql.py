"""VB 2005 style data binding to real databases (Data Sources window, TableAdapter / BindingSource /
BindingNavigator) for python-tk, python-qt and vb-basic forms.  No Qt here (UI: features/data_sources.py).

Model, in the .form (``form.extra["dbsources"]``)::

    {"name": "Customers",                       # self.Customers in code (+ CustomersBindingSource /
                                                #  CustomersTableAdapter aliases)
     "connection": {"name": "Shop", "kind": "sqlite", "path": "shop.db"},   # snapshot, never a password
     "table": "Customers", "query": "",         # a table, or a SELECT (editable when table + key are set)
     "columns": [{"name": "Id", "type": "INTEGER", "pk": 1}, ...], "key": ["Id"],
     "filter": "", "sort": "", "autofill": true,
     "navigator": {"MoveFirst": "btn..", "MovePrevious": .., "MoveNext": .., "MoveLast": .., "AddNew": ..,
                   "Delete": .., "Save": .., "Position": "lbl.."}}       # optional BindingNavigator buttons

Control properties (category Data): ``DataSource`` (a data source name), ``DataMember`` (a column - or
``Source.Column`` - for TextBox / Label / CheckBox; for ListBox / ComboBox the ``Source.Column`` that receives
the SelectedValue, i.e. a lookup), ``DisplayMember`` / ``ValueMember`` (ListBox / ComboBox).  A
DataGridView shows the columns of its ``Columns`` property that exist in the source (else all of them).

Generated code (runtime ``DB_RT`` + ``_DbTkIO`` / ``_DbQtIO``): ``_DbConnection`` (sqlite3, PyMySQL, psycopg 3,
pyodbc; passwords from the environment, ``connections.json`` next to the program or a prompt - never in the
code), ``_DbTable`` (Fill / FillBy / Update / AddNew / RemoveCurrent / EndEdit / CancelEdit / RejectChanges /
Position / Move* / Current / Value / SetValue / Search / SortBy / Find / HasChanges) with parameterized
INSERT / UPDATE / DELETE, and ``_DbBindings`` (two-way bindings + navigator buttons)."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

DATA_PROPS = {
    "DataGridView": ("DataSource",),
    "ListBox": ("DataSource", "DisplayMember", "ValueMember", "DataMember"),
    "ComboBox": ("DataSource", "DisplayMember", "ValueMember", "DataMember"),
    "TextBox": ("DataSource", "DataMember"),
    "Label": ("DataSource", "DataMember"),
    "CheckBox": ("DataSource", "DataMember"),
}
PROP_HELP = {
    "DataSource": "The data source (Data Sources window) this control shows. Drag a table from the "
                  "Data Sources window to create bound controls.",
    "DataMember": "The column shown and edited by the control (Column, or Source.Column). On a ListBox / "
                  "ComboBox: the Source.Column that receives the selected item's ValueMember (lookup).",
    "DisplayMember": "The column whose values are listed (ListBox / ComboBox).",
    "ValueMember": "The column that is the value of an item (SelectedValue) - usually the key.",
}
NAV_ACTIONS = ("MoveFirst", "MovePrevious", "MoveNext", "MoveLast", "AddNew", "Delete", "Save")
KINDS = ("sqlite", "mysql", "postgresql", "odbc")
KIND_TITLES = {"sqlite": "SQLite", "mysql": "MySQL / MariaDB", "postgresql": "PostgreSQL", "odbc": "ODBC"}
DRIVERS = {"mysql": "pymysql", "postgresql": "psycopg", "odbc": "pyodbc"}
MIME = "application/x-radide-dbsource"


# ====================================================================== model
def sources(form) -> list[dict]:
    v = form.extra.get("dbsources")
    if not isinstance(v, list):
        v = []
        form.extra["dbsources"] = v
    return v


def find_source(form, name: str) -> dict | None:
    for s in form.extra.get("dbsources") or []:
        if isinstance(s, dict) and str(s.get("name")) == name:
            return s
    return None


def ident(text: str, default: str = "Data") -> str:
    out = re.sub(r"\W", "_", str(text or "")).strip("_") or default
    if not (out[0].isalpha() or out[0] == "_"):
        out = default + out
    return out[0].upper() + out[1:]


def unique_source_name(form, base: str) -> str:
    base = ident(base)
    taken = {n.lower() for n in form.all_names()}
    for s in form.extra.get("dbsources") or []:
        n = str(s.get("name") or "").lower()
        taken |= {n, n + "bindingsource", n + "tableadapter", n + "bindingnavigator"}
        taken.add(conn_attr(s).lower())
    name, i = base, 1
    while name.lower() in taken or name.lower() in RESERVED:
        i += 1
        name = f"{base}{i}"
    return name


RESERVED = {"root", "show", "hide", "close", "destroy", "after", "title", "update", "resize", "move", "fillall",
            "updateall", "refresh", "self", "form", "me"}


def conn_attr(src: dict) -> str:
    c = src.get("connection") or {}
    return ident(c.get("name") or "Db", "Db") + "Connection"


def columns_of(src: dict) -> list[str]:
    return [str(c.get("name")) for c in src.get("columns") or [] if isinstance(c, dict) and c.get("name")]


def snapshot(info, base_folder: Path | None, form_folder: Path | None) -> dict:
    """The connection part of a data source, from a Databases-workspace ``ConnectionInfo`` (no password).
    A SQLite path is stored relative to the form's folder (the program resolves it next to itself)."""
    d = {"name": info.name, "kind": info.kind}
    if info.kind == "sqlite":
        p = info.resolved_path(base_folder)
        try:
            d["path"] = Path(os.path.relpath(p.resolve(), Path(form_folder).resolve())).as_posix() \
                if form_folder is not None else str(p)
            if d["path"].startswith("../../.."):
                d["path"] = str(p.resolve())
        except ValueError:                  # another drive
            d["path"] = str(p.resolve())
    else:
        d.update(host=info.host, port=info.effective_port(), user=info.user, database=info.database)
        if info.schema:
            d["schema"] = info.schema
        if info.options:
            d["options"] = dict(info.options)
    return d


def odbc_snapshot(name: str, connstr: str) -> dict:
    """An ODBC data source: the connection string, with any PWD=... removed (asked at run time)."""
    clean = ";".join(p for p in str(connstr).split(";") if p.strip() and not p.strip().lower().startswith(
        ("pwd=", "password=")))
    return {"name": name, "kind": "odbc", "odbc": clean}


def make_source(form, conn: dict, table: str = "", columns: list | None = None, key: list | None = None,
                query: str = "", name: str = "") -> dict:
    cols = [{k: v for k, v in c.items() if k in ("name", "type", "pk", "autoinc", "notnull", "default")}
            for c in columns or []]
    if key is None:
        key = [c["name"] for c in sorted((c for c in cols if c.get("pk")), key=lambda c: int(c.get("pk") or 0))]
    src = {"name": unique_source_name(form, name or table or "Query"), "connection": dict(conn),
           "table": table, "query": query, "columns": cols, "key": list(key), "filter": "", "sort": "",
           "autofill": True}
    sources(form).append(src)
    return src


def remove_source(form, name: str) -> None:
    form.extra["dbsources"] = [s for s in sources(form) if s.get("name") != name]
    for c in form.controls:
        for p in ("DataSource", "DataMember"):
            v = str(c.props.get(p) or "")
            if v == name or v.startswith(name + "."):
                c.props[p] = ""


def rename_references(form, old: str, new: str) -> None:
    """A control was renamed: keep the navigator buttons attached."""
    for s in sources(form):
        nav = s.get("navigator")
        if isinstance(nav, dict):
            for k, v in list(nav.items()):
                if v == old:
                    nav[k] = new


def readonly(src: dict) -> bool:
    return not (src.get("table") and src.get("key"))


def split_member(member: str, default_source: str) -> tuple[str, str]:
    member = str(member or "").strip()
    if "." in member:
        s, _, c = member.partition(".")
        return s.strip(), c.strip()
    return default_source, member


def prop_choices(form, ctrl, prop: str) -> list[str]:
    """Values offered by the Properties window for a data property."""
    srcs = [s for s in form.extra.get("dbsources") or [] if isinstance(s, dict)]
    if prop == "DataSource":
        return [""] + [str(s.get("name")) for s in srcs]
    own = find_source(form, str(ctrl.props.get("DataSource") or ""))
    if prop in ("DisplayMember", "ValueMember"):
        return [""] + (columns_of(own) if own else [])
    if prop == "DataMember":
        if ctrl.type in ("ListBox", "ComboBox"):
            return [""] + [f"{s.get('name')}.{c}" for s in srcs if s is not own for c in columns_of(s)]
        out = [""] + (columns_of(own) if own else [])
        return out + [f"{s.get('name')}.{c}" for s in srcs if s is not own for c in columns_of(s)]
    return [""]


# ====================================================================== bindings for code / preview
def binding_specs(form) -> tuple[list[dict], list[list], list[list]]:
    """(valid sources, binding specs, navigators) of a form."""
    srcs = []
    names = set()
    for s in form.extra.get("dbsources") or []:
        if not isinstance(s, dict):
            continue
        n = str(s.get("name") or "")
        conn = s.get("connection") or {}
        if not n.isidentifier() or n in names or n.lower() in RESERVED or conn.get("kind") not in KINDS:
            continue
        if not (s.get("table") or s.get("query")):
            continue
        names.add(n)
        srcs.append(s)
    by_name = {s["name"]: s for s in srcs}
    specs: list[list] = []
    for c in form.visual():
        p = c.props
        ds = str(p.get("DataSource") or "")
        if c.type == "DataGridView" and ds in by_name:
            cols = [x.strip() for x in str(p.get("Columns") or "").split(";") if x.strip()]
            specs.append(["grid", c.name, ds, cols])
        elif c.type in ("TextBox", "Label", "CheckBox"):
            s, col = split_member(p.get("DataMember"), ds)
            if s in by_name and col:
                kind = "check" if c.type == "CheckBox" else "text"
                specs.append([kind, c.name, s, col, c.type == "TextBox" and not p.get("ReadOnly")])
        elif c.type in ("ListBox", "ComboBox"):
            ts, tcol = split_member(p.get("DataMember"), "")
            if ts not in by_name:
                ts, tcol = "", ""
            if ds in by_name:
                cols = columns_of(by_name[ds])
                disp = str(p.get("DisplayMember") or "") or (cols[1] if len(cols) > 1 else (cols[0] if cols else ""))
                val = str(p.get("ValueMember") or "") or disp
                specs.append(["list", c.name, ds, disp, val, ts, tcol])
            elif ts and c.type == "ComboBox":
                specs.append(["text", c.name, ts, tcol, True])
    navs = []
    ctrl_names = {c.name for c in form.visual()}
    for s in srcs:
        nav = s.get("navigator")
        if isinstance(nav, dict):
            m = {k: v for k, v in nav.items() if (k in NAV_ACTIONS or k in ("Position", "Count")) and v in ctrl_names}
            if m:
                navs.append([s["name"], m])
    return srcs, specs, navs


def _conn_args(conn: dict) -> str:
    keys = ("kind", "path", "host", "port", "user", "database", "schema", "options", "odbc")
    args = [f"{k}={conn[k]!r}" for k in keys if conn.get(k) not in (None, "", {}, 0)]
    return ", ".join(args)


def python_code(form, toolkit: str) -> dict | None:
    """Runtime + __init__ lines + methods for a python-tk ("tk") / python-qt ("qt") designer file, or None."""
    srcs, specs, navs = binding_specs(form)
    if not srcs:
        return None
    I = "        "
    init = ["", I + "# Data sources (Data Sources window): connections, table adapters, bindings",
            I + f"self._dbio = {'_DbTkIO' if toolkit == 'tk' else '_DbQtIO'}(self)"]
    conns: dict[str, str] = {}
    for s in srcs:
        attr = conn_attr(s)
        if attr not in conns:
            conns[attr] = s["connection"].get("name") or attr
            init.append(I + f"self.{attr} = _DbConnection(self, {conns[attr]!r}, {_conn_args(s['connection'])})")
    for s in srcs:
        n = s["name"]
        cols = [{k: v for k, v in c.items() if k in ("name", "type", "pk", "default")} for c in s.get("columns") or []]
        init.append(I + f"self.{n} = _DbTable(self, {n!r}, self.{conn_attr(s)}, {str(s.get('table') or '')!r}, "
                        f"{cols!r}, key={list(s.get('key') or [])!r}, query={str(s.get('query') or '')!r}, "
                        f"filter={str(s.get('filter') or '')!r}, sort={str(s.get('sort') or '')!r})")
        init.append(I + f"self.{n}BindingSource = self.{n}TableAdapter = self.{n}")
    init.append(I + f"self._db_sources = {[s['name'] for s in srcs]!r}")
    init.append(I + f"self._dbbind = _DbBindings(self, self._dbio, {specs!r}, {navs!r})")
    fills = [s["name"] for s in srcs if s.get("autofill", True)]
    if fills:
        init.append(I + f"self._dbbind.FillAll({fills!r})")
    methods = ["", "    # ---------------------------------------------------------------- data sources",
               "    def FillAll(self):",
               "        \"\"\"Fill every data source of the form from its database (like TableAdapter.Fill).\"\"\"",
               "        return self._dbbind.FillAll(self._db_sources)",
               "",
               "    def UpdateAll(self):",
               "        \"\"\"Save the changes of every data source to the database (TableAdapterManager.UpdateAll).\"\"\"",
               "        return self._dbbind.UpdateAll(self._db_sources)"]
    runtime = DB_RT + (TK_DB_IO if toolkit == "tk" else QT_DB_IO)
    return {"runtime": runtime, "init": init, "after_load": [], "methods": methods}


def merge_blend(res: dict | None, form, toolkit: str) -> dict | None:
    """Adds the data-source code to the Blend code of python_tk / python_qt (``_blend``)."""
    try:
        code = python_code(form, toolkit)
    except Exception:  # noqa: BLE001 - a broken data source must never break code generation
        return res
    if code is None:
        return res
    if res is None:
        return code
    return {"runtime": res["runtime"] + code["runtime"], "init": res["init"] + code["init"],
            "after_load": res["after_load"] + code["after_load"], "methods": res["methods"] + code["methods"]}


# ====================================================================== generated runtime
DB_RT = r'''

import json as _db_json  # noqa: E402


def _db_text(v):
    """The text a control shows for a database value."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, (bytes, bytearray, memoryview)):
        return "(binary)"
    return str(v)


def _db_kind(sqltype):
    t = str(sqltype or "").lower()
    if "bool" in t or t in ("bit", "tinyint(1)"):
        return "bool"
    if "int" in t or "serial" in t:
        return "int"
    if any(k in t for k in ("real", "floa", "doub", "dec", "num", "money")):
        return "float"
    return "text"


def _db_convert(kind, v, column=""):
    """A value typed in a control -> the value for the column (raises ValueError when it is not valid)."""
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        if kind != "text" and s == "":
            return None
        if kind == "int":
            try:
                return int(s)
            except ValueError:
                try:
                    f = float(s)
                except ValueError:
                    raise ValueError(f"{column}: '{v}' is not a whole number") from None
                if not f.is_integer():
                    raise ValueError(f"{column}: '{v}' is not a whole number") from None
                return int(f)
        if kind == "float":
            try:
                return float(s)
            except ValueError:
                raise ValueError(f"{column}: '{v}' is not a number") from None
        if kind == "bool":
            return s.lower() in ("1", "true", "yes", "on", "-1")
        return v
    if kind == "bool":
        return bool(v)
    if kind == "int" and isinstance(v, bool):
        return int(v)
    return v


def _db_sql(sql, style):
    """SQL written with ? placeholders -> the driver's paramstyle (%s for PyMySQL / psycopg)."""
    if style == "?":
        return sql
    out, quote = [], None
    for ch in sql:
        if quote:
            out.append("%%" if ch == "%" else ch)
            if ch == quote:
                quote = None
        elif ch in "'\"`":
            quote = ch
            out.append(ch)
        elif ch == "?":
            out.append("%s")
        elif ch == "%":
            out.append("%%")
        else:
            out.append(ch)
    return "".join(out)


class _DbConnection:
    """The database of one or more data sources (Kind: sqlite / mysql / postgresql / odbc).
    The password is never in the code: environment variable RADIDE_DB_<NAME>_PASSWORD (or <NAME>_PASSWORD),
    else connections.json next to the program ({"<Name>": {"password": "..."}}), else the user is asked.
    Execute(sql, *params) / Query(sql, *params) run your own SQL with ? placeholders."""

    def __init__(self, owner, name, kind="sqlite", path="", host="127.0.0.1", port=0, user="", database="",
                 schema="", options=None, odbc=""):
        self._o = owner
        self.Name, self.Kind, self.Path = name, kind, path
        self.Host, self.Port, self.User, self.Database, self.Schema = host, int(port or 0), user, database, schema
        self.Options, self.Odbc = dict(options or {}), odbc
        self._conn = None
        self._password = None

    @property
    def ParamStyle(self):
        return "%s" if self.Kind in ("mysql", "postgresql") else "?"

    def Quote(self, name):
        if self.Kind == "mysql":
            return "`" + str(name).replace("`", "``") + "`"
        return '"' + str(name).replace('"', '""') + '"'

    def _config(self):
        try:
            with open(self._o._res("connections.json"), encoding="utf-8-sig") as f:
                cfg = _db_json.load(f)
            return cfg.get(self.Name) if isinstance(cfg, dict) else None
        except (OSError, ValueError, AttributeError):
            return None

    def Password(self):
        if self._password is not None:
            return self._password
        key = "".join(ch if ch.isalnum() else "_" for ch in self.Name).upper()
        for env in (f"RADIDE_DB_{key}_PASSWORD", f"{key}_PASSWORD"):
            if os.environ.get(env) is not None:
                self._password = os.environ[env]
                return self._password
        cfg = self._config()
        if isinstance(cfg, dict) and cfg.get("password") is not None:
            self._password = str(cfg["password"])
            return self._password
        io = getattr(self._o, "_dbio", None)
        pw = io.ask_password(f"Connect to {self.Name}", f"Password for {self.User or 'the database'} "
                             f"({self.Name}):") if io is not None else None
        if pw is None:
            raise RuntimeError(f"No password for the connection {self.Name}")
        self._password = pw
        return pw

    def Open(self):
        """The DB-API connection (opened on first use)."""
        if self._conn is not None:
            return self._conn
        k = self.Kind
        if k == "sqlite":
            import sqlite3
            path = self.Path if os.path.isabs(self.Path) else self._o._res(self.Path)
            if not os.path.exists(path):
                raise RuntimeError(f"Database file not found: {path}")
            self._conn = sqlite3.connect(path)
        elif k == "mysql":
            try:
                import pymysql
            except ImportError:
                raise RuntimeError("MySQL / MariaDB needs PyMySQL: pip install pymysql") from None
            opts = {"charset": "utf8mb4", **self.Options}
            self._conn = pymysql.connect(host=self.Host, port=self.Port or 3306, user=self.User,
                                         password=self.Password(), database=self.Database or None,
                                         autocommit=False, connect_timeout=10, **opts)
        elif k == "postgresql":
            try:
                import psycopg
            except ImportError:
                raise RuntimeError('PostgreSQL needs psycopg: pip install "psycopg[binary]"') from None
            self._conn = psycopg.connect(host=self.Host, port=self.Port or 5432, user=self.User,
                                         password=self.Password(), dbname=self.Database, connect_timeout=10,
                                         **self.Options)
            if self.Schema:
                self._conn.execute("SET search_path TO " + self.Quote(self.Schema))
                self._conn.commit()
        elif k == "odbc":
            try:
                import pyodbc
            except ImportError:
                raise RuntimeError("ODBC needs pyodbc: pip install pyodbc") from None
            cs = self.Odbc
            if "{PASSWORD}" in cs:
                cs = cs.replace("{PASSWORD}", self.Password())
            elif "uid=" in cs.lower() and "pwd=" not in cs.lower() and "trusted_connection" not in cs.lower():
                cs = cs.rstrip(";") + ";PWD=" + self.Password()
            self._conn = pyodbc.connect(cs, autocommit=False)
        else:
            raise RuntimeError(f"Unknown database kind {k!r}")
        return self._conn

    def Close(self):
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def Execute(self, sql, *params):
        """Run SQL (? placeholders) and return the cursor; call Commit() after changes."""
        cur = self.Open().cursor()
        if params:
            cur.execute(_db_sql(sql, self.ParamStyle), tuple(params))
        else:
            cur.execute(sql)
        return cur

    def Query(self, sql, *params):
        """Rows of a SELECT (? placeholders) as dicts."""
        cur = self.Execute(sql, *params)
        names = [d[0] for d in cur.description or []]
        rows = [dict(zip(names, r)) for r in cur.fetchall()]
        self.Commit()
        return rows

    def Commit(self):
        if self._conn is not None:
            self._conn.commit()

    def Rollback(self):
        if self._conn is not None:
            try:
                self._conn.rollback()
            except Exception:  # noqa: BLE001 - connection already broken
                pass


class _DbRow:
    """One record: row["Column"] reads / writes a value; State = unchanged / added / modified / deleted."""

    def __init__(self, table, values, state="unchanged"):
        self._t = table
        self.Values = values
        self.Original = None if state == "added" else dict(values)
        self.State = state

    def __getitem__(self, column):
        return self.Values.get(column)

    def __setitem__(self, column, value):
        self._t._set(self, column, value)

    def get(self, column, default=None):
        return self.Values.get(column, default)

    def keys(self):
        return list(self.Values)

    def __repr__(self):
        return f"<{self.State} {self.Values!r}>"


class _DbTable:
    """A table of a data source = VB TableAdapter + BindingSource in one object.
    Fill() / FillBy(where, *params) load the rows; Update() saves the changes (parameterized INSERT /
    UPDATE / DELETE in one transaction); AddNew() / RemoveCurrent() / EndEdit() / CancelEdit() /
    RejectChanges(); Position, Count, Current, MoveFirst/Previous/Next/Last(); Value(col) / SetValue(col, v);
    Search(text) and SortBy(col) filter / sort the loaded rows; Filter / Sort (SQL) apply on the next Fill."""

    def __init__(self, owner, name, connection, table, columns, key=(), query="", filter="", sort=""):
        self._o = owner
        self.Name, self.Connection, self.TableName = name, connection, table
        self._types = {c["name"]: c.get("type", "") for c in columns}
        self._defaults = {c["name"]: c["default"] for c in columns if c.get("default") is not None}
        self.Columns = [c["name"] for c in columns]
        self.Key = list(key)
        self.Query, self.Filter, self.Sort = query, filter, sort
        self._rows, self._view, self._pos = [], [], -1
        self._search, self._order = None, None
        self._listeners, self._editors = [], []
        self.LastError = ""

    # ------------------------------------------------------------ state
    @property
    def ReadOnly(self):
        return not (self.TableName and self.Key)

    @property
    def Count(self):
        return len(self._view)

    @property
    def Rows(self):
        return list(self._view)

    @property
    def Current(self):
        return self._view[self._pos] if 0 <= self._pos < len(self._view) else None

    @property
    def Position(self):
        return self._pos

    @Position.setter
    def Position(self, index):
        index = max(0, min(int(index), len(self._view) - 1)) if self._view else -1
        if index != self._pos:
            self.EndEdit()
            self._pos = index
            self._notify("position")

    @property
    def HasChanges(self):
        return any(r.State != "unchanged" for r in self._rows)

    def Item(self, index):
        return self._view[index]

    def Value(self, column, index=None):
        row = self.Current if index is None else self._view[index]
        return None if row is None else row.Values.get(column)

    def SetValue(self, column, value, index=None):
        row = self.Current if index is None else self._view[index]
        if row is not None:
            self._set(row, column, value)

    def _set(self, row, column, value):
        if self.ReadOnly:
            raise ValueError(f"{self.Name} is read-only (no table / primary key)")
        value = _db_convert(_db_kind(self._types.get(column)), value, column)
        old = row.Values.get(column)
        if _db_text(old) == _db_text(value) and (old is None) == (value is None):
            return
        row.Values[column] = value
        if row.State == "unchanged":
            row.State = "modified"
        self._notify("item", row, column)

    def Find(self, column, value):
        """Index (in the current view) of the first row whose column equals value, or -1."""
        t = _db_text(value)
        for i, r in enumerate(self._view):
            if _db_text(r.Values.get(column)) == t:
                return i
        return -1

    # ------------------------------------------------------------ events
    def _notify(self, kind, row=None, column=None):
        for fn in list(self._listeners):
            fn(kind, row, column)
        if kind in ("position", "list"):
            fn = getattr(self._o, f"{self.Name}_PositionChanged", None) if self._o is not None else None
            if callable(fn):
                fn()

    def _rebuild(self, keep=None):
        view = [r for r in self._rows if r.State != "deleted"]
        if self._search:
            text, cols = self._search
            cols = cols or self.Columns
            view = [r for r in view if any(text in _db_text(r.Values.get(c)).lower() for c in cols)]
        if self._order:
            col, desc = self._order

            def key(r):
                v = r.Values.get(col)
                return (v is None, v if isinstance(v, (int, float)) and not isinstance(v, bool) else _db_text(v).lower())
            try:
                view.sort(key=key, reverse=desc)
            except TypeError:
                view.sort(key=lambda r: _db_text(r.Values.get(col)).lower(), reverse=desc)
        self._view = view
        if keep is not None and keep in view:
            self._pos = view.index(keep)
        else:
            self._pos = min(max(self._pos, 0), len(view) - 1) if view else -1

    def Search(self, text, *columns):
        """Show only the loaded rows whose columns contain text (no database query; "" shows all)."""
        self.EndEdit()
        cur = self.Current
        self._search = (str(text).lower(), list(columns)) if str(text or "") else None
        self._rebuild(cur)
        self._notify("list")

    def SortBy(self, column="", descending=False):
        """Sort the loaded rows by a column ("" = database order)."""
        self.EndEdit()
        cur = self.Current
        self._order = (column, bool(descending)) if column else None
        self._rebuild(cur)
        self._notify("list")

    # ------------------------------------------------------------ SQL
    def SelectCommand(self, where=""):
        q = self.Connection.Quote
        if self.Query:
            sql = self.Query.strip().rstrip(";")
            conds = [c for c in (self.Filter, where) if c]
            if conds:
                sql = f"SELECT * FROM ({sql}) AS _q WHERE " + " AND ".join(f"({c})" for c in conds)
        else:
            cols = ", ".join(q(c) for c in self.Columns) if self.Columns else "*"
            sql = f"SELECT {cols} FROM {q(self.TableName)}"
            conds = [c for c in (self.Filter, where) if c]
            if conds:
                sql += " WHERE " + " AND ".join(f"({c})" for c in conds)
        if self.Sort:
            sql += " ORDER BY " + self.Sort
        return sql

    def Fill(self, where="", *params):
        """Load the rows from the database (pending changes are discarded). where: an extra SQL condition
        with ? placeholders, e.g. Fill("City = ?", "Cairo"). Returns the number of rows."""
        c = self.Connection
        try:
            cur = c.Execute(self.SelectCommand(where), *params)
            names = [d[0] for d in cur.description or []]
            data = cur.fetchall()
            c.Commit()
        except Exception as e:
            c.Rollback()
            self.LastError = str(e)
            raise
        if names and not self.Columns:
            self.Columns = names
        bools = [n for n in names if _db_kind(self._types.get(n)) == "bool"]
        if bools:                               # SQLite / MySQL keep booleans as 0 / 1
            data = [tuple(bool(v) if n in bools and isinstance(v, int) else v for n, v in zip(names, r))
                    for r in data]
        self._rows = [_DbRow(self, dict(zip(names, r))) for r in data]
        self._pos = 0
        self._rebuild()
        self._notify("list")
        return len(self._rows)

    FillBy = Fill

    def GetData(self, where="", *params):
        """The rows of the table as dicts (does not change the loaded rows)."""
        return self.Connection.Query(self.SelectCommand(where), *params)

    def _where_key(self, row):
        q = self.Connection.Quote
        src = row.Original or row.Values
        parts, args = [], []
        for k in self.Key:
            v = src.get(k)
            if v is None:
                parts.append(f"{q(k)} IS NULL")
            else:
                parts.append(f"{q(k)} = ?")
                args.append(v)
        return " AND ".join(parts), args

    def Update(self):
        """Save the added / changed / deleted rows to the database; returns the number of rows saved."""
        self.EndEdit()
        if not self.HasChanges:
            return 0
        if self.ReadOnly:
            raise RuntimeError(f"{self.Name} cannot be saved: it has no table or primary key")
        c = self.Connection
        q = c.Quote
        conn = c.Open()
        cur = conn.cursor()
        style = c.ParamStyle
        done = 0
        known = set(self._types) or set(self.Columns)
        try:
            for r in [r for r in self._rows if r.State == "deleted" and r.Original is not None]:
                where, args = self._where_key(r)
                cur.execute(_db_sql(f"DELETE FROM {q(self.TableName)} WHERE {where}", style), tuple(args))
                done += 1
            for r in [r for r in self._rows if r.State == "modified"]:
                cols = [k for k in r.Values if k in known and _db_text(r.Values.get(k)) != _db_text(
                    (r.Original or {}).get(k))]
                if not cols:
                    continue
                where, args = self._where_key(r)
                sets = ", ".join(f"{q(k)} = ?" for k in cols)
                cur.execute(_db_sql(f"UPDATE {q(self.TableName)} SET {sets} WHERE {where}", style),
                            tuple([r.Values[k] for k in cols] + args))
                done += 1
            for r in [r for r in self._rows if r.State == "added"]:
                cols = [k for k in self.Columns if k in known and r.Values.get(k) is not None]
                one_key = self.Key[0] if len(self.Key) == 1 and r.Values.get(self.Key[0]) is None else None
                if cols:
                    sql = (f"INSERT INTO {q(self.TableName)} ({', '.join(q(k) for k in cols)}) "
                           f"VALUES ({', '.join('?' for _ in cols)})")
                elif c.Kind == "mysql":
                    sql = f"INSERT INTO {q(self.TableName)} () VALUES ()"
                else:
                    sql = f"INSERT INTO {q(self.TableName)} DEFAULT VALUES"
                if one_key and c.Kind == "postgresql":
                    sql += f" RETURNING {q(one_key)}"
                cur.execute(_db_sql(sql, style), tuple(r.Values[k] for k in cols))
                if one_key:
                    new = None
                    if c.Kind == "postgresql":
                        got = cur.fetchone()
                        new = got[0] if got else None
                    elif c.Kind == "odbc":
                        try:
                            cur.execute("SELECT @@IDENTITY")
                            got = cur.fetchone()
                            new = got[0] if got else None
                        except Exception:  # noqa: BLE001 - not every ODBC database has @@IDENTITY
                            new = None
                    else:
                        new = cur.lastrowid
                    if new is not None:
                        r.Values[one_key] = int(new) if isinstance(new, (int, float)) or str(new).isdigit() else new
                done += 1
            conn.commit()
        except Exception as e:
            c.Rollback()
            self.LastError = str(e)
            raise
        self.AcceptChanges()
        return done

    def AcceptChanges(self):
        self._rows = [r for r in self._rows if r.State != "deleted"]
        for r in self._rows:
            r.State, r.Original = "unchanged", dict(r.Values)
        cur = self.Current
        self._rebuild(cur)
        self._notify("list")

    def RejectChanges(self):
        """Undo every change since the last Fill / Update."""
        keep = []
        for r in self._rows:
            if r.State == "added":
                continue
            if r.Original is not None:
                r.Values = dict(r.Original)
            r.State = "unchanged"
            keep.append(r)
        self._rows = keep
        self._rebuild()
        self._notify("list")

    # ------------------------------------------------------------ editing / navigation
    def AddNew(self, **values):
        """Add a new row (saved by Update) and move to it."""
        if self.ReadOnly:
            raise RuntimeError(f"{self.Name} is read-only (no table / primary key)")
        self.EndEdit()
        row = _DbRow(self, {c: None for c in self.Columns}, "added")
        for k, v in self._defaults.items():         # the columns' DEFAULT values (DataColumn.DefaultValue)
            try:
                row.Values[k] = _db_convert(_db_kind(self._types.get(k)), v, k)
            except ValueError:
                pass
        for k, v in values.items():
            row.Values[k] = _db_convert(_db_kind(self._types.get(k)), v, k)
        self._rows.append(row)
        self._view.append(row)
        self._pos = len(self._view) - 1
        self._notify("list")
        return row

    def RemoveAt(self, index):
        if self.ReadOnly:
            raise RuntimeError(f"{self.Name} is read-only (no table / primary key)")
        if not 0 <= index < len(self._view):
            return
        row = self._view.pop(index)
        if row.State == "added":
            self._rows.remove(row)
        else:
            row.State = "deleted"
        self._pos = min(self._pos, len(self._view) - 1)
        self._notify("list")

    def RemoveCurrent(self):
        """Delete the current row (saved by Update)."""
        self.RemoveAt(self._pos)

    def EndEdit(self):
        """Copy the values typed in the bound controls into the current row."""
        if self.Current is None or self.ReadOnly:
            return
        pending = [got for got in (fn() for fn in list(self._editors)) if got is not None]
        for column, value in pending:           # read every control first: SetValue refreshes them
            self.SetValue(column, value)

    def CancelEdit(self):
        """Show the current row's values again (forget what was typed but not yet ended)."""
        self._notify("position")

    def MoveFirst(self):
        self.Position = 0

    def MoveLast(self):
        self.Position = len(self._view) - 1

    def MoveNext(self):
        self.Position = self._pos + 1

    def MovePrevious(self):
        self.Position = max(0, self._pos - 1)


class _DbBindings:
    """Control <-> data source bindings (two way) and BindingNavigator buttons."""

    def __init__(self, owner, io, specs, navs):
        self._o, self._io = owner, io
        self._busy = 0
        self._by_src = {}
        for spec in specs:
            try:
                self._add(spec)
            except Exception as e:  # noqa: BLE001 - one broken binding must not stop the form
                print(f"data binding {spec[:3]}: {e}")
        for src, m in navs:
            try:
                self._nav(src, m)
            except Exception as e:  # noqa: BLE001
                print(f"binding navigator {src}: {e}")
        for name in self._by_src:
            t = getattr(owner, name, None)
            if t is not None:
                t._listeners.append(lambda kind, row, col, n=name: self._changed(n, kind, row, col))

    def _t(self, name):
        return getattr(self._o, name)

    def _guard(self, fn, *a):
        if self._busy:
            return
        try:
            fn(*a)
        except Exception as e:  # noqa: BLE001 - show it, keep the form running
            self._io.error("Data", str(e))
            for n in self._by_src:
                self._changed(n, "list", None)

    def _on(self, src, kind, fn):
        self._by_src.setdefault(src, []).append((kind, fn))

    def _changed(self, src, kind, row, col=None):
        self._busy += 1
        try:
            for k, fn in self._by_src.get(src, []):
                if k in ("text", "check", "lookup"):
                    fn(kind, row, col)
                else:
                    fn(kind, row)
        finally:
            self._busy -= 1

    # ------------------------------------------------------------ binding kinds
    def _add(self, spec):
        kind, ctrl, src = spec[0], spec[1], spec[2]
        t = self._t(src)
        io = self._io
        if kind == "grid":
            want = spec[3]

            def cols():
                have = [c for c in want if c in t.Columns]
                return have if have else list(t.Columns)

            def fill(k, row):
                cs = cols()
                if k == "item" and row is not None:
                    if row in t._view:
                        io.grid_set_row(ctrl, t._view.index(row), [_db_text(row.Values.get(c)) for c in cs])
                    return
                if k == "list":
                    io.grid_fill(ctrl, cs, [[_db_text(r.Values.get(c)) for c in cs] for r in t._view], t.ReadOnly)
                io.grid_select(ctrl, t.Position)
            self._on(src, "grid", fill)
            io.on_grid_select(ctrl, lambda r: self._guard(setattr, t, "Position", r))
            io.on_grid_edit(ctrl, lambda r, c, text: self._guard(lambda: t.SetValue(cols()[c], text, r)))
        elif kind == "text":
            col, editable = spec[3], spec[4]

            def show(k, row, column=None):
                if k in ("list", "position") or (row is t.Current and column in (None, col)):
                    io.set_text(ctrl, _db_text(t.Value(col)))
            self._on(src, "text", show)
            if editable:
                def typed():
                    if self._busy or t.Current is None:
                        return None
                    text = io.get_text(ctrl)
                    return (col, text) if text != _db_text(t.Value(col)) else None
                t._editors.append(typed)
                io.on_commit(ctrl, lambda: self._busy or t.Current is None or self._guard(t.EndEdit))
        elif kind == "check":
            col = spec[3]

            def show(k, row, column=None):
                if k in ("list", "position") or (row is t.Current and column in (None, col)):
                    v = t.Value(col)
                    io.set_check(ctrl, _db_convert("bool", v) if v is not None else False)
            self._on(src, "check", show)
            io.on_toggle(ctrl, lambda: t.Current is not None and self._guard(t.SetValue, col, io.get_check(ctrl)))
        elif kind == "list":
            disp, val, tsrc, tcol = spec[3], spec[4], spec[5], spec[6]

            def items(k, row):
                if k in ("list", "item"):
                    io.set_list(ctrl, [_db_text(r.Values.get(disp)) for r in t._view])
                if not tsrc:
                    io.select_list(ctrl, t.Position)
                else:
                    sync("position", None)
            self._on(src, "list", items)
            if tsrc:
                target = self._t(tsrc)

                def sync(k, row, column=None):
                    if k in ("list", "position") or (row is target.Current and column in (None, tcol)):
                        io.select_list(ctrl, t.Find(val, target.Value(tcol)) if target.Current is not None else -1)
                self._on(tsrc, "lookup", sync)
                io.on_list_select(ctrl, lambda i: target.Current is not None and 0 <= i < t.Count and self._guard(
                    target.SetValue, tcol, t._view[i].Values.get(val)))
            else:
                io.on_list_select(ctrl, lambda i: self._guard(setattr, t, "Position", i))

    def _nav(self, src, m):
        t = self._t(src)
        io = self._io
        acts = {"MoveFirst": t.MoveFirst, "MovePrevious": t.MovePrevious, "MoveNext": t.MoveNext,
                "MoveLast": t.MoveLast, "AddNew": t.AddNew, "Delete": t.RemoveCurrent,
                "Save": lambda: self._save(t)}
        for act, ctrl in m.items():
            if act in acts:
                io.on_click(ctrl, lambda f=acts[act]: self._guard(f))

        def pos(k, row):
            if "Position" in m:
                io.set_text(m["Position"], f"{t.Position + 1 if t.Count else 0} of {t.Count}")
            if "Count" in m:
                io.set_text(m["Count"], f"of {t.Count}")
        self._on(src, "nav", pos)

    def _save(self, t):
        n = t.Update()
        print(f"{t.Name}: {n} row(s) saved")

    # ------------------------------------------------------------ form helpers
    def FillAll(self, names):
        total = 0
        for n in names:
            t = self._t(n)
            try:
                total += t.Fill()
            except Exception as e:  # noqa: BLE001 - a missing database must not stop the form
                self._io.later(lambda n=n, e=e: self._io.error("Data", f"{n}.Fill(): {e}"))
                self._changed(n, "list", None)
        return total

    def UpdateAll(self, names):
        total = 0
        for n in names:
            t = self._t(n)
            if not t.ReadOnly:
                total += t.Update()
        return total
'''

TK_DB_IO = r'''

class _DbTkIO:
    """Reads / writes the Tk controls of data bindings."""

    def __init__(self, owner):
        self.o = owner

    def w(self, name):
        return getattr(self.o, name)

    def _var(self, name):
        return self.o.__dict__.get(name + "_var")

    def get_text(self, name):
        w = self.w(name)
        if isinstance(w, tk.Text):
            return w.get("1.0", "end-1c")
        if isinstance(w, (tk.Entry, ttk.Entry, ttk.Combobox)):
            return w.get()
        return str(w.cget("text"))

    def set_text(self, name, text):
        w = self.w(name)
        if isinstance(w, tk.Text):
            state = w.cget("state")
            w.configure(state="normal")
            w.delete("1.0", "end")
            w.insert("1.0", text)
            w.configure(state=state)
            w.edit_modified(False)
        elif isinstance(w, (tk.Entry, ttk.Entry, ttk.Combobox)):
            var = self._var(name)
            if var is not None:
                var.set(text)
            else:
                state = str(w.cget("state"))
                w.configure(state="normal")
                w.delete(0, "end")
                w.insert(0, text)
                w.configure(state=state)
        else:
            w.configure(text=text)

    def get_check(self, name):
        var = self._var(name)
        return bool(var.get()) if var is not None else False

    def set_check(self, name, on):
        var = self._var(name)
        if var is not None:
            var.set(bool(on))

    def on_toggle(self, name, fn):
        var = self._var(name)
        if var is not None:
            var.trace_add("write", lambda *_: fn())

    def on_commit(self, name, fn):
        w = self.w(name)
        w.bind("<FocusOut>", lambda _e: fn(), add="+")
        if not isinstance(w, tk.Text):
            w.bind("<Return>", lambda _e: fn(), add="+")
        if isinstance(w, ttk.Combobox):
            w.bind("<<ComboboxSelected>>", lambda _e: fn(), add="+")

    def set_list(self, name, items):
        w = self.w(name)
        if isinstance(w, tk.Listbox):
            w.delete(0, "end")
            if items:
                w.insert("end", *items)
        elif isinstance(w, ttk.Combobox):
            w.configure(values=list(items))

    def select_list(self, name, index):
        w = self.w(name)
        if isinstance(w, tk.Listbox):
            w.selection_clear(0, "end")
            if 0 <= index < w.size():
                w.selection_set(index)
                w.activate(index)
                w.see(index)
        elif isinstance(w, ttk.Combobox):
            vals = w.cget("values") or ()
            if 0 <= index < len(vals):
                w.current(index)
            else:
                var = self._var(name)
                if var is not None:
                    var.set("")
                else:
                    w.set("")

    def on_list_select(self, name, fn):
        w = self.w(name)
        if isinstance(w, tk.Listbox):
            w.bind("<<ListboxSelect>>", lambda _e: w.curselection() and fn(w.curselection()[0]), add="+")
        elif isinstance(w, ttk.Combobox):
            w.bind("<<ComboboxSelected>>", lambda _e: w.current() >= 0 and fn(w.current()), add="+")

    def grid_fill(self, name, columns, rows, readonly):
        g = self.w(name)
        g.SetColumns(list(columns))
        g.Clear()
        for r in rows:
            g.AddRow(*r)
        g.ReadOnly = bool(readonly) or bool(getattr(g, "_rad_ro", False))

    def grid_set_row(self, name, index, cells):
        g = self.w(name)
        kids = g.get_children()
        if 0 <= index < len(kids):
            g.item(kids[index], values=[str(c) for c in cells])

    def grid_select(self, name, index):
        g = self.w(name)
        kids = g.get_children()
        if 0 <= index < len(kids):
            if tuple(g.selection()) != (kids[index],):
                g.selection_set(kids[index])
            g.see(kids[index])
            g.CurrentRow = index
        elif g.selection():
            g.selection_remove(*g.selection())

    def on_grid_select(self, name, fn):
        g = self.w(name)
        g._rad_ro = bool(g.ReadOnly)
        g.bind("<<TreeviewSelect>>", lambda _e: g.selection() and fn(g.index(g.selection()[0])), add="+")

    def on_grid_edit(self, name, fn):
        g = self.w(name)
        old = g._on_change

        def changed():
            r, c = g.CurrentRow, g.CurrentColumn
            fn(r, c, g.GetCell(r, c))
            if old is not None:
                old()
        g._on_change = changed

    def on_click(self, name, fn):
        w = self.w(name)
        old = str(w.cget("command") or "")

        def click():
            fn()
            if old:
                w.tk.call(old)
        w.configure(command=click)

    def error(self, title, text):
        from tkinter import messagebox
        messagebox.showerror(title, text, parent=self.o.root)

    def ask_password(self, title, prompt):
        from tkinter import simpledialog
        return simpledialog.askstring(title, prompt, show="*", parent=self.o.root)

    def later(self, fn):
        self.o.root.after(0, fn)
'''

QT_DB_IO = r'''

class _DbFocusOut(QObject):
    def __init__(self, widget, fn):
        super().__init__(widget)
        self.fn = fn
        widget.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.FocusOut:
            self.fn()
        return False


class _DbQtIO:
    """Reads / writes the Qt controls of data bindings."""

    def __init__(self, owner):
        self.o = owner
        self._keep = []

    def w(self, name):
        return getattr(self.o, name)

    def get_text(self, name):
        w = self.w(name)
        if isinstance(w, QPlainTextEdit):
            return w.toPlainText()
        if isinstance(w, QComboBox):
            return w.currentText()
        return w.text() if hasattr(w, "text") else ""

    def set_text(self, name, text):
        w = self.w(name)
        if isinstance(w, QPlainTextEdit):
            w.setPlainText(text)
        elif isinstance(w, QComboBox):
            if w.isEditable():
                w.setEditText(text)
            else:
                w.setCurrentIndex(w.findText(text))
        elif hasattr(w, "setText"):
            w.setText(text)

    def get_check(self, name):
        return self.w(name).isChecked()

    def set_check(self, name, on):
        self.w(name).setChecked(bool(on))

    def on_toggle(self, name, fn):
        self.w(name).toggled.connect(lambda _v: fn())

    def on_commit(self, name, fn):
        w = self.w(name)
        if isinstance(w, QLineEdit):
            w.editingFinished.connect(fn)
        elif isinstance(w, QComboBox):
            if w.isEditable():
                w.lineEdit().editingFinished.connect(fn)
            w.activated.connect(lambda _i: fn())
        else:
            self._keep.append(_DbFocusOut(w, fn))

    def set_list(self, name, items):
        w = self.w(name)
        w.blockSignals(True)
        try:
            w.clear()
            w.addItems([str(i) for i in items])
        finally:
            w.blockSignals(False)

    def select_list(self, name, index):
        w = self.w(name)
        w.blockSignals(True)
        try:
            if isinstance(w, QListWidget):
                w.setCurrentRow(index if 0 <= index < w.count() else -1)
            else:
                w.setCurrentIndex(index if 0 <= index < w.count() else -1)
        finally:
            w.blockSignals(False)

    def on_list_select(self, name, fn):
        w = self.w(name)
        sig = w.currentRowChanged if isinstance(w, QListWidget) else w.currentIndexChanged
        sig.connect(lambda i: i >= 0 and fn(i))

    def grid_fill(self, name, columns, rows, readonly):
        w = self.w(name)
        if not hasattr(w, "_rad_triggers"):
            w._rad_triggers = w.editTriggers()
        w.blockSignals(True)
        try:
            w.clearContents()
            w.setColumnCount(max(1, len(columns)))
            w.setHorizontalHeaderLabels([str(c) for c in columns])
            w.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, text in enumerate(row):
                    w.setItem(r, c, QTableWidgetItem(str(text)))
        finally:
            w.blockSignals(False)
        w.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers if readonly else w._rad_triggers)

    def grid_set_row(self, name, index, cells):
        w = self.w(name)
        if not 0 <= index < w.rowCount():
            return
        w.blockSignals(True)
        try:
            for c, text in enumerate(cells):
                it = w.item(index, c)
                if it is None:
                    w.setItem(index, c, QTableWidgetItem(str(text)))
                elif it.text() != str(text):
                    it.setText(str(text))
        finally:
            w.blockSignals(False)

    def grid_select(self, name, index):
        w = self.w(name)
        if 0 <= index < w.rowCount():
            if w.currentRow() != index:
                w.setCurrentCell(index, max(0, w.currentColumn()))
        else:
            w.clearSelection()

    def on_grid_select(self, name, fn):
        w = self.w(name)
        w.currentCellChanged.connect(lambda r, c, pr, pc: r >= 0 and r != pr and fn(r))

    def on_grid_edit(self, name, fn):
        w = self.w(name)
        w.cellChanged.connect(lambda r, c: fn(r, c, w.item(r, c).text() if w.item(r, c) is not None else ""))

    def on_click(self, name, fn):
        self.w(name).clicked.connect(lambda *_: fn())

    def error(self, title, text):
        QMessageBox.critical(self.o, title, text)

    def ask_password(self, title, prompt):
        text, ok = QInputDialog.getText(self.o, title, prompt, QLineEdit.EchoMode.Password)
        return text if ok else None

    def later(self, fn):
        QTimer.singleShot(0, fn)
'''


# ====================================================================== IDE side: schema, rows
class OdbcDatabase:
    """A tiny adapter over pyodbc with the parts of radide.web_site.databases.Database we need."""

    def __init__(self, connstr: str, password: str = ""):
        import pyodbc
        cs = connstr
        if password:
            cs = cs.replace("{PASSWORD}", password) if "{PASSWORD}" in cs else cs.rstrip(";") + ";PWD=" + password
        self.conn = pyodbc.connect(cs, autocommit=True, timeout=10)

    def tables(self) -> list[str]:
        return sorted({r.table_name for r in self.conn.cursor().tables(tableType="TABLE")})

    def views(self) -> list[str]:
        return sorted({r.table_name for r in self.conn.cursor().tables(tableType="VIEW")})

    def columns(self, table: str):
        from .web_site.databases import Column
        pk = self.primary_key(table)
        return [Column(r.column_name, r.type_name or "", not r.nullable, None,
                       pk.index(r.column_name) + 1 if r.column_name in pk else 0)
                for r in self.conn.cursor().columns(table=table)]

    def primary_key(self, table: str, cols=None) -> list[str]:
        try:
            rows = sorted(self.conn.cursor().primaryKeys(table=table), key=lambda r: r.key_seq)
            return [r.column_name for r in rows]
        except Exception:  # noqa: BLE001 - some drivers have no SQLPrimaryKeys
            return []

    def query(self, sql: str, limit: int) -> tuple[list[str], list[tuple]]:
        cur = self.conn.cursor()
        cur.execute(sql)
        return [d[0] for d in cur.description or []], [tuple(r) for r in cur.fetchmany(limit)]

    def q(self, name: str) -> str:
        return '"' + name.replace('"', '""') + '"'

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:  # noqa: BLE001
            pass


def info_of(conn: dict, form_folder: Path | None):
    """A ConnectionInfo for a data-source connection snapshot (SQLite path resolved next to the form)."""
    from .web_site.databases import ConnectionInfo
    info = ConnectionInfo.from_dict(conn)
    if info.kind == "sqlite" and form_folder is not None:
        info.path = str(info.resolved_path(Path(form_folder)))
    return info


def open_db(conn: dict, form_folder: Path | None, password: str = ""):
    """A connected adapter (Databases workspace adapter, or OdbcDatabase) for a connection snapshot."""
    if conn.get("kind") == "odbc":
        return OdbcDatabase(str(conn.get("odbc") or ""), password)
    from .web_site.databases import open_database
    info = info_of(conn, form_folder)
    if info.kind == "sqlite" and not Path(info.path).is_file():
        from .web_site.databases import DatabaseError
        raise DatabaseError(f"Database file not found: {info.path}")
    return open_database(info, None, password)


def table_columns(db, table: str) -> tuple[list[dict], list[str]]:
    """(columns as dicts, primary key) of a table."""
    cols = db.columns(table)
    pk = db.primary_key(table, cols) if hasattr(db, "primary_key") else []
    out = []
    for c in cols:
        d = {"name": c.name, "type": c.type or ""}
        if c.name in pk:
            d["pk"] = pk.index(c.name) + 1
        if getattr(c, "autoinc", False):
            d["autoinc"] = True
        if getattr(c, "notnull", False):
            d["notnull"] = True
        default = literal_default(getattr(c, "default", None))
        if default is not None:
            d["default"] = default
        out.append(d)
    return out, list(pk)


def literal_default(sql) -> str | None:
    """A column DEFAULT that is a plain literal (number, 'text', TRUE / FALSE), as text; else None
    (functions such as CURRENT_TIMESTAMP or nextval(...) are left to the database)."""
    if sql is None:
        return None
    t = str(sql).strip()
    while t.startswith("(") and t.endswith(")"):
        t = t[1:-1].strip()
    t = re.sub(r"::[\w\s]+$", "", t).strip()           # PostgreSQL 'x'::character varying
    if re.fullmatch(r"[-+]?\d+(\.\d+)?", t) or t.lower() in ("true", "false"):
        return t
    if len(t) >= 2 and t[0] == t[-1] == "'" and "'" not in t[1:-1].replace("''", ""):
        return t[1:-1].replace("''", "'")
    return None


def query_columns(db, sql: str) -> list[dict]:
    names, _rows = run_query(db, sql, 1)
    return [{"name": n, "type": ""} for n in names]


def run_query(db, sql: str, limit: int) -> tuple[list[str], list[tuple]]:
    if isinstance(db, OdbcDatabase):
        return db.query(sql, limit)
    res = db.execute(sql, max_rows=limit)
    last = res[-1] if res else None
    if last is None:
        return [], []
    if last.error:
        from .web_site.databases import DatabaseError
        raise DatabaseError(last.error)
    return list(last.columns), [tuple(r) for r in last.rows[:limit]]


def select_sql(db, src: dict, limit: int) -> str:
    q = db.q
    if src.get("query"):
        sql = str(src["query"]).strip().rstrip(";")
        if src.get("filter"):
            sql = f"SELECT * FROM ({sql}) AS _q WHERE ({src['filter']})"
    else:
        cols = ", ".join(q(c) for c in columns_of(src)) or "*"
        sql = f"SELECT {cols} FROM {q(src['table'])}"
        if src.get("filter"):
            sql += f" WHERE ({src['filter']})"
    if src.get("sort"):
        sql += f" ORDER BY {src['sort']}"
    return sql


def fetch_rows(src: dict, form_folder: Path | None, password: str = "", limit: int = 200):
    """(columns, rows) of a data source from its database (the design-time preview / Preview Data)."""
    db = open_db(src.get("connection") or {}, form_folder, password)
    try:
        return run_query(db, select_sql(db, src, limit), limit)
    finally:
        db.close()


# design-time preview (BlendPreview.effective -> sample_props)
PASSWORD_PROVIDER = None        # set by features/data_sources.py: fn(conn snapshot, form folder) -> str | None
_ROWS: dict = {}
_FAILED: dict = {}
PREVIEW_ROWS = 30


def clear_cache() -> None:
    _ROWS.clear()
    _FAILED.clear()


def design_rows(src: dict, form_folder: Path | None):
    """Cached (columns, rows) for the designer; None when the database cannot be read now."""
    conn = src.get("connection") or {}
    key = json.dumps([conn, src.get("table"), src.get("query"), src.get("filter"), src.get("sort"),
                      columns_of(src), str(form_folder)], sort_keys=True, default=str)
    if conn.get("kind") == "sqlite":
        try:
            key += str(info_of(conn, form_folder).resolved_path(None).stat().st_mtime)
        except OSError:
            return None
    if key in _ROWS:
        return _ROWS[key]
    if time.time() - _FAILED.get(key, 0) < 30:
        return None
    pw = ""
    if conn.get("kind") in ("mysql", "postgresql") or (conn.get("kind") == "odbc" and "uid=" in str(
            conn.get("odbc", "")).lower()):
        pw = PASSWORD_PROVIDER(conn, form_folder) if PASSWORD_PROVIDER else None
        if pw is None:
            _FAILED[key] = time.time()
            return None
    try:
        got = fetch_rows(src, form_folder, pw, PREVIEW_ROWS)
    except Exception:  # noqa: BLE001 - no preview when the database is not reachable
        _FAILED[key] = time.time()
        return None
    if len(_ROWS) > 64:
        _ROWS.clear()
    _ROWS[key] = got
    return got


def _txt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, (bytes, bytearray, memoryview)):
        return "(binary)"
    return str(v)


def sample_props(doc, ctrl) -> dict:
    """Real rows shown by bound controls in the designer (first row for TextBox / Label / CheckBox)."""
    form = doc.form
    if not form.extra.get("dbsources"):
        return {}
    p = ctrl.props
    folder = Path(doc.path).parent
    out: dict = {}
    ds = str(p.get("DataSource") or "")
    if ctrl.type == "DataGridView":
        src = find_source(form, ds)
        got = design_rows(src, folder) if src else None
        if got:
            cols, rows = got
            want = [c.strip() for c in str(p.get("Columns") or "").split(";") if c.strip() in cols]
            show = want or cols
            idx = [cols.index(c) for c in show]
            out["Columns"] = ";".join(show)
            out["Rows"] = ";".join("|".join(_txt(r[i]).replace(";", ",").replace("|", "/") for i in idx)
                                   for r in rows)
    elif ctrl.type in ("ListBox", "ComboBox") and ds:
        src = find_source(form, ds)
        got = design_rows(src, folder) if src else None
        if got:
            cols, rows = got
            disp = str(p.get("DisplayMember") or "") or (cols[1] if len(cols) > 1 else cols[0] if cols else "")
            if disp in cols:
                i = cols.index(disp)
                out["Items"] = ";".join(_txt(r[i]).replace(";", ",") for r in rows)
    elif ctrl.type in ("TextBox", "Label", "CheckBox"):
        s, col = split_member(p.get("DataMember"), ds)
        src = find_source(form, s) if s else None
        got = design_rows(src, folder) if src and col else None
        if got and got[1] and col in got[0]:
            v = got[1][0][got[0].index(col)]
            if ctrl.type == "CheckBox":
                out["Checked"] = str(v).strip().lower() in ("1", "true", "yes", "on", "-1")
            else:
                out["Text"] = _txt(v)
    if ctrl.type == "Label":
        for s in form.extra.get("dbsources") or []:
            nav = s.get("navigator") if isinstance(s, dict) else None
            if isinstance(nav, dict) and nav.get("Position") == ctrl.name:
                got = design_rows(s, folder)
                if got:
                    out["Text"] = f"1 of {len(got[1])}" + ("+" if len(got[1]) >= PREVIEW_ROWS else "")
    return out


# ====================================================================== drag a table onto a form
def column_kind(sqltype) -> str:
    """bool / int / float / text - the same rule as the generated runtime's _db_kind."""
    t = str(sqltype or "").lower()
    if "bool" in t or t in ("bit", "tinyint(1)"):
        return "bool"
    if "int" in t or "serial" in t:
        return "int"
    if any(k in t for k in ("real", "floa", "doub", "dec", "num", "money")):
        return "float"
    return "text"


def layout_controls(form, src: dict, mode: str, x: int, y: int, parent: str = "",
                    column: str = "") -> list:
    """Create the controls VB makes when a table (or a column) is dropped on a form:
    mode "grid": a BindingNavigator (panel + buttons) and a DataGridView bound to the source;
    mode "details": the navigator + a Label and a TextBox / CheckBox per column; a column alone: Label + editor.
    Returns the new controls (already in form.controls)."""
    name = src["name"]
    cols = src.get("columns") or []
    ro = readonly(src)
    created = []

    def add(type_name, base, left, top, w=None, h=None, par=parent, **props):
        c = form.add(type_name, left, top, par)
        nm = base if base.lower() not in form.all_names() - {c.name.lower()} else form.unique_name(base)
        c.props["Name"] = nm
        if "Text" in c.props and "Text" not in props:
            c.props["Text"] = nm
        if w is not None:
            c.props["Width"] = w
        if h is not None:
            c.props["Height"] = h
        c.props.update(props)
        created.append(c)
        return c

    def editor(col: dict, left: int, top: int, label_w: int, par: str):
        cname = str(col["name"])
        base = ident(cname, "Field")
        kind = "check" if column_kind(col.get("type")) == "bool" else "text"
        add("Label", f"{base}Label", left, top + 3, label_w, 17, par, Text=f"{cname}:")
        if kind == "check":
            add("CheckBox", f"{base}CheckBox", left + label_w + 6, top, 160, 20, par, Text="",
                DataSource=name, DataMember=cname)
        else:
            pk = bool(col.get("pk"))
            add("TextBox", f"{base}TextBox", left + label_w + 6, top, 180, 20, par, Text="",
                DataSource=name, DataMember=cname, ReadOnly=ro or (pk and bool(col.get("autoinc")
                                                                                  or "int" in str(col.get("type", "")).lower())))

    if column:
        col = next((c for c in cols if c.get("name") == column), {"name": column})
        editor(col, x, y, max(60, 8 * len(str(column)) + 10), parent)
        return created

    def body(top: int) -> None:
        if mode == "details":
            label_w = max(60, min(140, 8 * max((len(str(c.get("name"))) for c in cols), default=6) + 10))
            for i, col in enumerate(cols):
                editor(col, x, top + i * 26, label_w, parent)
        else:
            names = columns_of(src)
            add("DataGridView", f"{name}DataGridView", x, top, min(620, max(260, 90 * len(names) + 40)), 190,
                DataSource=name, Columns=";".join(names), Rows="", ReadOnly=ro)

    old_nav = src.get("navigator") if isinstance(src.get("navigator"), dict) else {}
    if any(form.find(str(v)) is not None for v in old_nav.values()):
        body(y)             # one BindingNavigator per data source (like VB): later drops add the grid / fields
        return created

    # BindingNavigator: a panel with the VB buttons
    nav = add("Panel", f"{name}BindingNavigator", x, y, 330, 27, BackColor="#F0F0F0")
    nav_map: dict[str, str] = {}
    bx = 2
    for act, text, w in (("MoveFirst", "|<", 26), ("MovePrevious", "<", 26), ("Position", "0 of 0", 70),
                         ("MoveNext", ">", 26), ("MoveLast", ">|", 26), ("AddNew", "Add", 44),
                         ("Delete", "Delete", 50), ("Save", "Save", 44)):
        if ro and act in ("AddNew", "Delete", "Save"):
            continue
        if act == "Position":
            c = add("Label", f"{name}BindingNavigatorPositionItem", bx, 5, w, 17, par=nav.name, Text=text,
                    TextAlign="Center")
        else:
            c = add("Button", f"{name}BindingNavigator{act}Item", bx, 2, w, 23, par=nav.name, Text=text,
                    ToolTip={"MoveFirst": "Move first", "MovePrevious": "Move previous", "MoveNext": "Move next",
                             "MoveLast": "Move last", "AddNew": "Add new", "Delete": "Delete",
                             "Save": "Save data"}[act])
        nav_map[act] = c.name
        bx += w + 2
    nav.props["Width"] = bx + 2
    src["navigator"] = nav_map
    body(y + 33)
    return created


# ====================================================================== VB (vbrun) objects
class VBDataObject:
    """Lets VB code use a data source: Customers.MoveNext, Customers.Fill, n = Customers.Count,
    Customers.Value("Name"), Customers.SetValue "Name", "x", Customers.Update, Customers.Position = 0."""
    vb_typename = "BindingSource"

    def __init__(self, obj):
        self._o = obj

    def _name(self, name: str) -> str:
        low = name.lower()
        for n in list(type(self._o).__dict__) + list(getattr(self._o, "__dict__", {})):
            if n.lower() == low and not n.startswith("_"):
                return n
        for klass in type(self._o).__mro__:
            for n in klass.__dict__:
                if n.lower() == low and not n.startswith("_"):
                    return n
        raise AttributeError(name)

    @staticmethod
    def _vb(v):
        if hasattr(v, "Values") and hasattr(v, "State"):
            return VBDataObject(v)
        if isinstance(v, list):
            return v
        if v is None:
            return ""
        return v

    def vb_get(self, name):
        attr = getattr(self._o, self._name(name))
        return self._vb(attr() if callable(attr) else attr)

    def vb_set(self, name, value):
        setattr(self._o, self._name(name), value)

    def vb_call(self, name, args):
        if hasattr(self._o, "Values") and hasattr(self._o, "State") and name.lower() in ("item", "value", "fields"):
            return self._vb(self._o[args[0]]) if args else ""
        try:
            attr = getattr(self._o, self._name(name))
        except AttributeError:
            if hasattr(self._o, "Values") and not args:          # row.Name
                return self._vb(self._o[name] if name in self._o.Values else next(
                    (v for k, v in self._o.Values.items() if k.lower() == name.lower()), ""))
            raise
        if callable(attr):
            return self._vb(attr(*args))
        if args and hasattr(attr, "__getitem__"):
            return self._vb(attr[args[0]])
        return self._vb(attr)



def vb_objects(ui) -> dict:
    """{lower-case name: VBDataObject} for the data sources of a built form (vbrun VBForm.load)."""
    out = {}
    for n in getattr(ui, "__dict__", {}).get("_db_sources") or []:
        obj = getattr(ui, n, None)
        if obj is None:
            continue
        wrap = VBDataObject(obj)
        for alias in (n, n + "BindingSource", n + "TableAdapter"):
            out[alias.lower()] = wrap
        conn = getattr(obj, "Connection", None)
        if conn is not None:
            for k, v in ui.__dict__.items():
                if v is conn:
                    out[k.lower()] = VBDataObject(conn)
    return out
