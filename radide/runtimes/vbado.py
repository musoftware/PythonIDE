"""ADO (ADODB.Connection / Recordset / Command) and DAO (DBEngine / OpenDatabase / Database / Recordset) for
VB6 programs run by the IDE's interpreter (radide/runtimes/vbrun.py) and for programs migrated to Python.

Real VB6 database programs mostly use Access ``.mdb`` files through the Jet OLE DB provider, which exists only
as a 32-bit COM component.  The IDE runs 64-bit Python, so the work is split:

* **Backends** (``_open_backend``) - all speak ``execute(sql) -> (columns, types, rows, affected)``:
  - ``_Ado32Bridge`` (Windows): a 32-bit ``cscript.exe`` (``%SystemRoot%\\SysWOW64``) running a small VBScript
    that uses the *real* ADO with the connection string as given (Jet 4.0 / ACE / ODBC DSN / SQL Server /
    any 32-bit provider); one helper process per open connection, line protocol over stdin/stdout.
  - ``_OdbcBackend``: pyodbc with a 64-bit "Microsoft Access Driver (*.mdb, *.accdb)" when one is installed.
  - ``_SqliteBackend``: ``.db`` / ``.sqlite`` / ``.sqlite3`` files (``Data Source=x.db`` or ``Driver=SQLite``).
* **Recordset** is client-side (static cursor): rows are fetched once, Move*/EOF/BOF/Find/Filter/Sort run in
  Python, and ``AddNew`` / ``Update`` / ``Delete`` / DAO ``Edit`` become INSERT / UPDATE / DELETE statements
  (WHERE on the primary key, or on all comparable columns of the original row).
* A database path that does not exist (VB6 programs often hard-code ``D:\\project\\db.mdb``) is looked up by
  file name under the program folder; the substitution is reported on stderr.

Every object speaks the interpreter's object protocol (``vb_get`` / ``vb_set`` / ``vb_call`` / ``vb_items`` /
``vb_setitem`` / ``vb_setindexed``, names in lower case) **and** has a Pythonic API with the VB names
(``rs.EOF``, ``rs.MoveNext()``, ``rs.Fields("Name").Value``, ``rs("Name")``) for migrated code, so this file
has no hard dependency on the interpreter (it is copied next to migrated programs).
"""
from __future__ import annotations

import atexit
import datetime as _dt
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

# ============================================================================ errors / helpers
try:
    from .vbinterp import EMPTY as _EMPTY, err as _vb_err  # type: ignore
except ImportError:                                          # migrated program: no interpreter
    _EMPTY = None
    _vb_err = None


class ADOError(Exception):
    def __init__(self, number, description):
        super().__init__(f"Run-time error '{number}': {description}")
        self.number, self.description = number, description


def _err(number, msg):
    if _vb_err is not None:
        return _vb_err(number, msg)
    return ADOError(number, msg)


def _given(v) -> bool:
    if v is None:
        return False
    if _EMPTY is not None and v is _EMPTY:
        return False
    return type(v).__name__ not in ("Empty", "_Missing")


def _plain(v):
    """A Field (or any object with a default value) -> its value."""
    if isinstance(v, Field):
        return v.Value
    return v


def _to_str(v) -> str:
    v = _plain(v)
    if v is None or not _given(v):
        return ""
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _to_int(v, default=0) -> int:
    v = _plain(v)
    if not _given(v):
        return default
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


OLE_EPOCH = _dt.datetime(1899, 12, 30)


def _ole_to_dt(d: float) -> _dt.datetime:
    return OLE_EPOCH + _dt.timedelta(days=d)


def _parse_date(s: str):
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
                "%d-%b-%Y", "%d %b %Y", "%Y/%m/%d", "%H:%M:%S", "%H:%M"):
        try:
            return _dt.datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


# ADO DataTypeEnum families
NUM_TYPES = {2, 3, 4, 5, 6, 14, 16, 17, 18, 19, 20, 21, 131, 139}
DATE_TYPES = {7, 133, 134, 135}
BOOL_TYPES = {11}
TEXT_TYPES = {8, 129, 130, 200, 201, 202, 203}
LONG_TYPES = {201, 203, 205, 128, 204}           # memo / binary: not comparable in Jet WHERE clauses

# ============================================================================ connection strings / paths
_KV = re.compile(r'\s*([^=;]+?)\s*=\s*("[^"]*"|\'[^\']*\'|\{[^}]*\}|[^;]*)\s*(?:;|$)')


def parse_connstr(s: str) -> list[list[str]]:
    out = []
    for m in _KV.finditer(s or ""):
        k, v = m.group(1).strip(), m.group(2).strip()
        if k:
            out.append([k, v])
    return out


def build_connstr(pairs) -> str:
    return ";".join(f"{k}={v}" for k, v in pairs)


def _get(pairs, *keys):
    for k, v in pairs:
        if k.lower() in keys:
            return v.strip('"\'')
    return ""


SEARCH_ROOTS: list[Path] = []                 # program folders (vbrun adds its project folder)
_REPORTED: set = set()


def resolve_db_path(path: str, base: Path | None = None) -> str:
    """An existing file for *path*: as given, relative to *base*, else the same file name under the program
    folder (VB6 programs often hard-code D:\\app\\db.mdb)."""
    if not path:
        return path
    p = Path(path)
    if not p.is_absolute() and base is not None and (base / p).exists():
        return str((base / p).resolve())
    if p.exists():
        return str(p)
    name = p.name.lower()
    if not name:
        return path
    roots = [r for r in ([base] if base else []) + SEARCH_ROOTS + [Path.cwd()] if r is not None]
    seen = set()
    for root in roots:
        try:
            root = Path(root).resolve()
        except OSError:
            continue
        if root in seen or not root.is_dir():
            continue
        seen.add(root)
        hits = []
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in ("__pycache__", "node_modules")]
            for f in files:
                if f.lower() == name:
                    hits.append(Path(dirpath) / f)
            if len(hits) > 5:
                break
        if hits:
            hits.sort(key=lambda h: len(h.parts))
            found = str(hits[0])
            if (path, found) not in _REPORTED:
                _REPORTED.add((path, found))
                print(f"[VB6 data] database '{path}' not found - using '{found}' from the program folder",
                      file=sys.stderr, flush=True)
            return found
    return path


def fix_connstr(connstr: str, provider: str = "", base: Path | None = None) -> tuple[str, list]:
    """(connection string with Provider and an existing Data Source, parsed pairs)."""
    s = (connstr or "").strip()
    pairs = parse_connstr(s) if "=" in s else []
    if s and not pairs:                                   # ConnectionString = "C:\x\db.mdb" (Provider set apart)
        pairs = [["Data Source", s]]
    if provider and not _get(pairs, "provider", "driver", "dsn"):
        pairs.insert(0, ["Provider", provider])
    for kv in pairs:
        if kv[0].lower() in ("data source", "dbq", "database") and re.search(r"\.(mdb|accdb|db|sqlite3?)\W*$",
                                                                             kv[1], re.I):
            raw = kv[1].strip('"\'')
            kv[1] = resolve_db_path(raw, base)
    if not _get(pairs, "provider", "driver", "dsn") and re.search(r"\.(mdb|accdb)$", _get(pairs, "data source"),
                                                                 re.I):
        pairs.insert(0, ["Provider", "Microsoft.Jet.OLEDB.4.0"])
    return build_connstr(pairs), pairs


# ============================================================================ backends
_JS_SAFE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@*_+-./")


def _js_escape(s: str) -> str:
    out = []
    for ch in s:
        if ch in _JS_SAFE:
            out.append(ch)
        elif ord(ch) < 256:
            out.append("%%%02X" % ord(ch))
        else:
            out.append("%%u%04X" % ord(ch))
    return "".join(out)


_UNESC = re.compile(r"%u([0-9A-Fa-f]{4})|%([0-9A-Fa-f]{2})")


def _js_unescape(s: str) -> str:
    return _UNESC.sub(lambda m: chr(int(m.group(1) or m.group(2), 16)), s)


_BRIDGE_VBS = r'''
Option Explicit
SetLocale 1033
Dim conn, ln, cmd, arg, p, ra, rs
Set conn = Nothing
Function Enc(v)
  Dim t
  If IsNull(v) Or IsEmpty(v) Then
    Enc = "N"
    Exit Function
  End If
  t = VarType(v)
  If t = 7 Then
    Enc = "T" & CStr(CDbl(v))
  ElseIf t = 11 Then
    If v Then Enc = "B1" Else Enc = "B0"
  ElseIf t = 2 Or t = 3 Or t = 4 Or t = 5 Or t = 6 Or t = 14 Or t = 16 Or t = 17 Or t = 18 Or t = 19 Or t = 20 Or t = 21 Then
    Enc = "D" & CStr(v)
  ElseIf t = 8 Then
    Enc = "S" & Escape(v)
  ElseIf t = 8209 Then
    Enc = "X" & CStr(LenB(v))
  Else
    Enc = "S" & Escape(CStr(v))
  End If
End Function
Sub DoExec(sql)
  Dim i, n, out, row, nf, data, r, c
  Set rs = conn.Execute(sql, ra)
  If rs.State = 0 Then
    WScript.StdOut.WriteLine "AFF" & vbTab & CStr(ra)
    Exit Sub
  End If
  nf = rs.Fields.Count
  row = ""
  For i = 0 To nf - 1
    If i > 0 Then row = row & vbTab
    row = row & Escape(rs.Fields(i).Name)
  Next
  out = row
  row = ""
  For i = 0 To nf - 1
    If i > 0 Then row = row & vbTab
    row = row & CStr(rs.Fields(i).Type)
  Next
  out = out & vbLf & row
  n = 0
  If Not rs.EOF Then
    data = rs.GetRows()
    n = UBound(data, 2) + 1
    Dim lines()
    ReDim lines(n - 1)
    For r = 0 To n - 1
      row = ""
      For c = 0 To nf - 1
        If c > 0 Then row = row & vbTab
        row = row & Enc(data(c, r))
      Next
      lines(r) = row
    Next
    out = out & vbLf & Join(lines, vbLf)
  End If
  rs.Close
  WScript.StdOut.WriteLine "ROWS" & vbTab & CStr(nf) & vbTab & CStr(n)
  WScript.StdOut.WriteLine out
End Sub
Sub DoPK(tbl)
  Dim s, out
  Set s = conn.OpenSchema(28, Array(Empty, Empty, tbl))
  out = ""
  Do While Not s.EOF
    If out <> "" Then out = out & vbTab
    out = out & Escape(s.Fields("COLUMN_NAME").Value)
    s.MoveNext
  Loop
  s.Close
  WScript.StdOut.WriteLine "PK" & vbTab & out
End Sub
Sub DoTables()
  Dim s, out
  Set s = conn.OpenSchema(20)
  out = ""
  Do While Not s.EOF
    If s.Fields("TABLE_TYPE").Value = "TABLE" Or s.Fields("TABLE_TYPE").Value = "VIEW" Then
      If out <> "" Then out = out & vbTab
      out = out & Escape(s.Fields("TABLE_NAME").Value)
    End If
    s.MoveNext
  Loop
  s.Close
  WScript.StdOut.WriteLine "TABLES" & vbTab & out
End Sub
Do While Not WScript.StdIn.AtEndOfStream
  ln = WScript.StdIn.ReadLine
  p = InStr(ln, vbTab)
  If p > 0 Then
    cmd = Left(ln, p - 1)
    arg = Unescape(Mid(ln, p + 1))
  Else
    cmd = ln
    arg = ""
  End If
  If cmd = "QUIT" Then Exit Do
  On Error Resume Next
  Err.Clear
  If cmd = "OPEN" Then
    Set conn = CreateObject("ADODB.Connection")
    conn.CursorLocation = 3
    conn.Open arg
    If Err.Number = 0 Then WScript.StdOut.WriteLine "OK"
  ElseIf cmd = "EXEC" Then
    DoExec arg
  ElseIf cmd = "PK" Then
    DoPK arg
  ElseIf cmd = "TABLES" Then
    DoTables
  ElseIf cmd = "BEGIN" Then
    conn.BeginTrans
    If Err.Number = 0 Then WScript.StdOut.WriteLine "OK"
  ElseIf cmd = "COMMIT" Then
    conn.CommitTrans
    If Err.Number = 0 Then WScript.StdOut.WriteLine "OK"
  ElseIf cmd = "ROLLBACK" Then
    conn.RollbackTrans
    If Err.Number = 0 Then WScript.StdOut.WriteLine "OK"
  ElseIf cmd = "CLOSE" Then
    conn.Close
    WScript.StdOut.WriteLine "OK"
  Else
    WScript.StdOut.WriteLine "OK"
  End If
  If Err.Number <> 0 Then
    Dim d
    d = Err.Description
    If Not conn Is Nothing Then
      If conn.Errors.Count > 0 Then d = conn.Errors(0).Description
    End If
    WScript.StdOut.WriteLine "ERR" & vbTab & CStr(Err.Number) & vbTab & Escape(d)
  End If
  On Error GoTo 0
Loop
'''


def _bridge_script() -> Path:
    d = Path(tempfile.gettempdir()) / "radide-vb6"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "adobridge3.vbs"
    if not p.exists() or p.read_text(encoding="ascii", errors="replace") != _BRIDGE_VBS:
        p.write_text(_BRIDGE_VBS, encoding="ascii")
    return p


def _cscript32() -> str | None:
    if os.name != "nt":
        return None
    root = os.environ.get("SystemRoot", r"C:\Windows")
    for sub in ("SysWOW64", "System32"):
        p = Path(root) / sub / "cscript.exe"
        if p.is_file():
            return str(p)
    return None


_LIVE: list = []


@atexit.register
def _close_all():
    for b in list(_LIVE):
        try:
            b.close()
        except Exception:  # noqa: BLE001
            pass


class _Ado32Bridge:
    """The real ADO in a 32-bit helper process (Jet/ACE providers are 32-bit only)."""
    kind = "ado32"

    def __init__(self, connstr: str):
        exe = _cscript32()
        if exe is None:
            raise _err(3706, "Provider cannot be found (the 32-bit ADO bridge needs Windows)")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.p = subprocess.Popen([exe, "//nologo", "//E:vbscript", str(_bridge_script())], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags,
                                  encoding="latin-1")
        _LIVE.append(self)
        self._send("OPEN", connstr)
        self._expect("OK")

    def _send(self, cmd, arg=None):
        if self.p.poll() is not None:
            raise _err(3709, "The connection cannot be used to perform this operation (helper ended)")
        line = cmd if arg is None else cmd + "\t" + _js_escape(arg)
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()

    def _line(self) -> str:
        ln = self.p.stdout.readline()
        if not ln:
            msg = (self.p.stderr.read() or "").strip()[:300]
            raise _err(3709, f"database helper stopped {msg}")
        return ln.rstrip("\r\n")

    def _check(self, ln: str):
        if ln.startswith("ERR\t"):
            _, num, desc = (ln.split("\t", 2) + ["", ""])[:3]
            desc = _js_unescape(desc)
            try:
                n = int(num)
            except ValueError:
                n = -2147467259
            if n < 0 and (n & 0xFFFF0000) == 0x800A0000:          # ADO's own errors: 3021, 3265, 3704 ...
                n &= 0xFFFF
            raise _err(n, desc)

    def _expect(self, what):
        ln = self._line()
        self._check(ln)
        if not ln.startswith(what):
            raise _err(-2147467259, f"unexpected reply from the database helper: {ln[:80]}")
        return ln

    @staticmethod
    def _dec(tok: str):
        if not tok:
            return ""
        t, v = tok[0], tok[1:]
        if t == "N":
            return None
        if t == "S":
            return _js_unescape(v)
        if t == "D":
            try:
                f = float(v)
                return int(f) if f.is_integer() and "." not in v and "E" not in v.upper() else f
            except ValueError:
                return v
        if t == "T":
            try:
                return _ole_to_dt(float(v))
            except (ValueError, OverflowError):
                return None
        if t == "B":
            return v == "1"
        if t == "X":
            return b""
        return v

    def execute(self, sql: str):
        self._send("EXEC", sql)
        ln = self._line()
        self._check(ln)
        if ln.startswith("AFF"):
            return None, None, None, _to_int(ln.split("\t")[1], -1)
        if not ln.startswith("ROWS"):
            raise _err(-2147467259, f"unexpected reply from the database helper: {ln[:80]}")
        _, nf, n = ln.split("\t")
        nf, n = int(nf), int(n)
        names = [_js_unescape(x) for x in self._line().split("\t")] if nf else []
        if not nf:
            self._line()
        types_line = self._line()
        types = [int(x) for x in types_line.split("\t")] if nf else []
        rows = []
        for _i in range(n):
            parts = self._line().split("\t")
            rows.append([self._dec(x) for x in parts][:nf] + [None] * max(0, nf - len(parts)))
        return names, types, rows, -1

    def primary_key(self, table: str) -> list[str]:
        try:
            self._send("PK", table)
            ln = self._expect("PK")
            rest = ln[3:]
            return [_js_unescape(x) for x in rest.split("\t") if x]
        except Exception:  # noqa: BLE001
            return []

    def tables(self) -> list[str]:
        self._send("TABLES")
        ln = self._expect("TABLES")
        return [_js_unescape(x) for x in ln[7:].split("\t") if x]

    def tx(self, what):
        self._send(what)
        self._expect("OK")

    def close(self):
        if self.p.poll() is None:
            try:
                self.p.stdin.write("QUIT\n")
                self.p.stdin.flush()
                self.p.wait(3)
            except Exception:  # noqa: BLE001
                self.p.kill()
        if self in _LIVE:
            _LIVE.remove(self)

    # literals for Jet SQL
    @staticmethod
    def date_literal(d: _dt.datetime) -> str:
        if d.hour == d.minute == d.second == 0:
            return d.strftime("#%m/%d/%Y#")
        return d.strftime("#%m/%d/%Y %H:%M:%S#")

    bool_true, bool_false = "True", "False"


def _odbc_type(code) -> int:
    if code is bool:
        return 11
    if code is int:
        return 3
    if code is float:
        return 5
    if code in (_dt.datetime, _dt.date):
        return 7
    if code in (bytes, bytearray):
        return 205
    return 202


class _OdbcBackend:
    kind = "odbc"

    def __init__(self, connstr: str):
        import pyodbc  # type: ignore
        self.cn = pyodbc.connect(connstr, autocommit=True)

    def execute(self, sql: str):
        cur = self.cn.cursor()
        cur.execute(sql)
        if cur.description is None:
            return None, None, None, cur.rowcount
        names = [d[0] for d in cur.description]
        types = [_odbc_type(d[1]) for d in cur.description]
        rows = [list(r) for r in cur.fetchall()]
        for r in rows:
            for i, v in enumerate(r):
                if isinstance(v, _dt.date) and not isinstance(v, _dt.datetime):
                    r[i] = _dt.datetime(v.year, v.month, v.day)
                elif type(v).__name__ == "Decimal":
                    r[i] = float(v)
        return names, types, rows, -1

    def primary_key(self, table):
        try:
            return [r.column_name for r in self.cn.cursor().primaryKeys(table)]
        except Exception:  # noqa: BLE001
            return []

    def tables(self):
        return [r.table_name for r in self.cn.cursor().tables(tableType="TABLE")]

    def tx(self, what):
        if what == "BEGIN":
            self.cn.autocommit = False
        elif what == "COMMIT":
            self.cn.commit()
            self.cn.autocommit = True
        else:
            self.cn.rollback()
            self.cn.autocommit = True

    def close(self):
        self.cn.close()

    date_literal = _Ado32Bridge.date_literal
    bool_true, bool_false = "True", "False"


class _SqliteBackend:
    kind = "sqlite"

    def __init__(self, path: str):
        self.cn = sqlite3.connect(path, isolation_level=None, detect_types=sqlite3.PARSE_DECLTYPES)

    def execute(self, sql: str):
        sql = re.sub(r"#(\d{1,2})/(\d{1,2})/(\d{4})( [\d:]+)?#",
                     lambda m: f"'{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}{m.group(4) or ''}'", sql)
        cur = self.cn.execute(sql)
        if cur.description is None:
            return None, None, None, cur.rowcount
        names = [d[0] for d in cur.description]
        rows = [list(r) for r in cur.fetchall()]
        types = []
        for i in range(len(names)):
            v = next((r[i] for r in rows if r[i] is not None), None)
            types.append(3 if isinstance(v, int) else 5 if isinstance(v, float) else 7
                         if isinstance(v, _dt.datetime) else 202)
        return names, types, rows, -1

    def primary_key(self, table):
        try:
            return [r[1] for r in self.cn.execute(f'PRAGMA table_info("{table}")') if r[5]]
        except sqlite3.Error:
            return []

    def tables(self):
        return [r[0] for r in self.cn.execute("select name from sqlite_master where type in ('table','view')")]

    def tx(self, what):
        self.cn.execute({"BEGIN": "BEGIN", "COMMIT": "COMMIT", "ROLLBACK": "ROLLBACK"}[what])

    def close(self):
        self.cn.close()

    @staticmethod
    def date_literal(d):
        return "'" + d.strftime("%Y-%m-%d %H:%M:%S" if (d.hour or d.minute or d.second) else "%Y-%m-%d") + "'"

    bool_true, bool_false = "1", "0"


def _access_odbc_driver() -> str | None:
    try:
        import pyodbc  # type: ignore
    except ImportError:
        return None
    for d in pyodbc.drivers():
        if "access driver" in d.lower() and "accdb" in d.lower():
            return d
    return None


def _open_backend(connstr: str, pairs: list):
    src = _get(pairs, "data source", "dbq", "database")
    prov = _get(pairs, "provider").lower()
    drv = _get(pairs, "driver").lower()
    if re.search(r"\.(db|sqlite3?)$", src, re.I) or "sqlite" in drv or "sqlite" in prov:
        return _SqliteBackend(src)
    if re.search(r"\.(mdb|accdb)$", src, re.I) and (prov.startswith("microsoft.jet") or prov.startswith(
            "microsoft.ace") or not prov):
        drv64 = _access_odbc_driver()
        if drv64 and sys.maxsize > 2 ** 32:
            pwd = _get(pairs, "jet oledb:database password", "password", "pwd")
            return _OdbcBackend(f"DRIVER={{{drv64}}};DBQ={src};" + (f"PWD={pwd};" if pwd else ""))
    if _cscript32():
        return _Ado32Bridge(connstr)
    if drv or _get(pairs, "dsn"):
        return _OdbcBackend(connstr)
    raise _err(3706, "Provider cannot be found. It may not be properly installed.")


# ============================================================================ VB object protocol
class _VBObj:
    """vb_get / vb_set / vb_call over the Python members (case-insensitive)."""
    vb_typename = "Object"
    _members: dict | None = None

    def _member(self, name: str):
        cls = type(self)
        m = cls.__dict__.get("_mcache")
        if m is None:
            m = {}
            for klass in reversed(cls.__mro__):
                for n in klass.__dict__:
                    if not n.startswith("_"):
                        m[n.lower()] = n
            cls._mcache = m
        low = name.lower()
        hit = m.get(low)
        if hit is None:
            for n in self.__dict__:                       # instance attributes (Connection.Provider ...)
                if n.lower() == low and not n.startswith("_"):
                    return n
        return hit

    def vb_get(self, name):
        n = self._member(name)
        if n is None:
            raise _err(438, f"Object doesn't support this property or method ({self.vb_typename}.{name})")
        v = getattr(self, n)
        if callable(v) and not isinstance(v, _VBObj):
            try:
                return v()
            except TypeError as ex:
                raise _err(450, f"Wrong number of arguments or invalid property assignment "
                                f"({self.vb_typename}.{name}): {ex}") from None
        return v

    def vb_set(self, name, value):
        n = self._member(name)
        if n is None or callable(getattr(type(self), n, None)):
            raise _err(438, f"Object doesn't support this property ({self.vb_typename}.{name})")
        setattr(self, n, value)

    def vb_call(self, name, args):
        n = self._member(name)
        if n is None:
            raise _err(438, f"Object doesn't support this property or method ({self.vb_typename}.{name})")
        v = getattr(self, n)
        if callable(v) and not isinstance(v, _VBObj):
            try:
                return v(*args)
            except TypeError as ex:
                if "positional argument" not in str(ex) and "argument" not in str(ex):
                    raise
                raise _err(450, f"Wrong number of arguments or invalid property assignment "
                                f"({self.vb_typename}.{name}): {ex}") from None
        if args and isinstance(v, _VBObj) and getattr(v, "vb_default", None):
            return v.vb_call(v.vb_default, args)
        return v

    def __getattr__(self, name):                  # migrated code: rs.movenext / rs.eof (VB is not case-sensitive)
        if name.startswith("_"):
            raise AttributeError(name)
        n = self._member(name)
        if n is None or n == name:
            raise AttributeError(name)
        return getattr(self, n)

    def __iter__(self):                              # For Each in migrated code (TableDefs, Fields, Parameters)
        items = getattr(self, "vb_items", None)
        if items is None:
            raise TypeError(f"{self.vb_typename} is not a collection")
        return iter(items())

    def __call__(self, *args):                       # coll(i) / coll("name") in migrated code
        d = getattr(self, "vb_default", None)
        if not d:
            raise TypeError(f"{self.vb_typename} has no default member")
        return self.vb_call(d, list(args))

    def vb_setindexed(self, name, args, value):
        n = self._member(name)
        v = getattr(self, n) if n else None
        if isinstance(v, _VBObj) and hasattr(v, "vb_setitem"):
            v.vb_setitem(args, value)
            return
        raise _err(438, f"'{name}' cannot be indexed")


# ============================================================================ ADO objects
class Field(_VBObj):
    vb_typename = "Field"
    vb_default = "value"
    vb_deref_on_let = True          # x = rs!Name stores the value (VB default-property semantics)

    def __init__(self, rs: "Recordset", index: int):
        self._rs, self._i = rs, index

    @property
    def Name(self):
        return self._rs._cols[self._i]

    @property
    def Type(self):
        return self._rs._types[self._i] if self._i < len(self._rs._types) else 202

    @property
    def Value(self):
        return self._rs._get_value(self._i)

    @Value.setter
    def Value(self, v):
        self._rs._set_value(self._i, _plain(v))

    @property
    def OriginalValue(self):
        r = self._rs._current_row(False)
        return r[self._i] if r is not None else None

    UnderlyingValue = OriginalValue

    @property
    def DefinedSize(self):
        return 255 if self.Type in TEXT_TYPES else 8

    @property
    def ActualSize(self):
        return len(_to_str(self.Value))

    Precision = 0
    NumericScale = 0
    Attributes = 0
    Size = DefinedSize

    def AppendChunk(self, data):
        self.Value = _to_str(self.Value) + _to_str(data)

    def GetChunk(self, n):
        return _to_str(self.Value)[:_to_int(n)]

    # Python conveniences (migrated code)
    def __str__(self):
        return _to_str(self.Value)

    def __repr__(self):
        return f"<Field {self.Name}={self.Value!r}>"

    def __eq__(self, other):
        return self.Value == _plain(other)

    def __hash__(self):
        return hash(self.Name)

    def __int__(self):
        return _to_int(self.Value)

    def __float__(self):
        return float(self.Value or 0)

    def __bool__(self):
        return bool(self.Value)

    def __add__(self, o):
        v = self.Value
        return (v if v is not None else "") + o if isinstance(o, str) else (v or 0) + o

    def __radd__(self, o):
        v = self.Value
        return o + (_to_str(v) if isinstance(o, str) else (v or 0))


class Fields(_VBObj):
    vb_typename = "Fields"
    vb_default = "item"

    def __init__(self, rs):
        self._rs = rs

    @property
    def Count(self):
        return len(self._rs._cols)

    def Item(self, key):
        return self._rs._field(key)

    def Append(self, name, type_=202, size=0, attrib=0, value=None):
        self._rs._cols.append(_to_str(name))
        self._rs._types.append(_to_int(type_, 202))
        for r in self._rs._rows:
            r.append(None)

    def Refresh(self):
        return None

    def vb_items(self):
        return [Field(self._rs, i) for i in range(len(self._rs._cols))]

    def vb_setitem(self, args, value):
        self._rs._field(args[0]).Value = value

    def __call__(self, key):
        return self.Item(key)

    def __getitem__(self, key):
        return self.Item(key)

    def __setitem__(self, key, value):
        self.Item(key).Value = value

    def __iter__(self):
        return iter(self.vb_items())

    def __len__(self):
        return self.Count


class _Errors(_VBObj):
    vb_typename = "Errors"
    vb_default = "item"
    Count = 0

    def Clear(self):
        return None

    def Item(self, i):
        raise _err(9, "Subscript out of range")

    def vb_items(self):
        return []


class Connection(_VBObj):
    vb_typename = "Connection"
    vb_default = "connectionstring"

    def __init__(self, connstr: str = ""):
        self.ConnectionString = connstr
        self.Provider = ""
        self.CursorLocation = 2
        self.ConnectionTimeout = 15
        self.CommandTimeout = 30
        self.Mode = 0
        self.DefaultDatabase = ""
        self.IsolationLevel = 4096
        self.Attributes = 0
        self.Version = "2.8"
        self.Errors = _Errors()
        self._db = None
        self._pairs = []
        self._base = None

    @property
    def State(self):
        return 1 if self._db is not None else 0

    def Open(self, connstr=None, user=None, password=None, options=None):
        if self._db is not None:
            raise _err(3705, "Operation is not allowed when the object is open.")
        if _given(connstr) and _to_str(connstr):
            self.ConnectionString = _to_str(connstr)
        cs, pairs = fix_connstr(_to_str(self.ConnectionString), _to_str(self.Provider), self._base)
        if _given(user) and _to_str(user) and not _get(pairs, "user id", "uid"):
            pairs.append(["User ID", _to_str(user)])
        if _given(password) and _to_str(password) and not _get(pairs, "password", "pwd"):
            pairs.append(["Password", _to_str(password)])
        cs = build_connstr(pairs)
        if not cs:
            raise _err(3706, "Provider cannot be found. It may not be properly installed.")
        self._pairs = pairs
        self._db = _open_backend(cs, pairs)
        self.ConnectionString = cs
        return None

    def Close(self):
        if self._db is None:
            raise _err(3704, "Operation is not allowed when the object is closed.")
        self._db.close()
        self._db = None

    def _need(self):
        if self._db is None:
            raise _err(3709, "The connection cannot be used to perform this operation. "
                             "It is either closed or invalid in this context.")
        return self._db

    def Execute(self, sql, records_affected=None, options=None):
        db = self._need()
        sql = _to_str(sql)
        if _to_int(options, 0) & 2 or re.fullmatch(r"\s*\[?[\w ]+\]?\s*", sql) and not re.match(
                r"\s*(select|insert|update|delete|create|drop|alter|exec)\b", sql, re.I):
            sql = f"SELECT * FROM [{sql.strip().strip('[]')}]"
        cols, types, rows, aff = db.execute(sql)
        self._affected = aff
        rs = Recordset()
        if cols is not None:
            rs._load(self, sql, cols, types, rows, lock=1)
        return rs

    def vb_call_cells(self, name, args, cells):
        """Execute(sql, RecordsAffected): the second argument is ByRef."""
        r = self.vb_call(name, args)
        if name.lower() == "execute" and cells and len(cells) > 1 and cells[1] is not None:
            cells[1].value = max(0, getattr(self, "_affected", 0) or 0)
        return r

    def BeginTrans(self):
        self._need().tx("BEGIN")
        return 1

    def CommitTrans(self):
        self._need().tx("COMMIT")

    def RollbackTrans(self):
        self._need().tx("ROLLBACK")

    def OpenSchema(self, schema, criteria=None, schema_id=None):
        db = self._need()
        rs = Recordset()
        names = db.tables() if _to_int(schema) == 20 else []
        rs._load(self, "", ["TABLE_CATALOG", "TABLE_SCHEMA", "TABLE_NAME", "TABLE_TYPE"], [202, 202, 202, 202],
                 [[None, None, n, "TABLE"] for n in names], lock=1)
        return rs

    def Cancel(self):
        return None

    @property
    def Properties(self):
        return _Errors()


class Parameter(_VBObj):
    vb_typename = "Parameter"
    vb_default = "value"

    def __init__(self, name="", type_=202, direction=1, size=0, value=None):
        self.Name, self.Type, self.Direction, self.Size, self.Value = name, type_, direction, size, value


class Parameters(_VBObj):
    vb_typename = "Parameters"
    vb_default = "item"

    def __init__(self):
        self._items: list[Parameter] = []

    @property
    def Count(self):
        return len(self._items)

    def Append(self, p):
        self._items.append(p)

    def Delete(self, i):
        self._items.pop(self._index(i))

    def Refresh(self):
        return None

    def _index(self, k):
        k = _plain(k)
        if isinstance(k, str):
            for i, p in enumerate(self._items):
                if _to_str(p.Name).lower() == k.lower():
                    return i
            raise _err(3265, f"Item cannot be found in the collection ({k})")
        return int(k)

    def Item(self, k):
        return self._items[self._index(k)]

    def vb_items(self):
        return list(self._items)

    def vb_setitem(self, args, value):
        self.Item(args[0]).Value = _plain(value)


class Command(_VBObj):
    vb_typename = "Command"

    def __init__(self):
        self.CommandText = ""
        self.CommandType = 1
        self.CommandTimeout = 30
        self.Prepared = False
        self.Name = ""
        self._conn = None
        self.Parameters = Parameters()

    @property
    def ActiveConnection(self):
        return self._conn

    @ActiveConnection.setter
    def ActiveConnection(self, v):
        if isinstance(v, str):
            c = Connection(v)
            c.Open()
            v = c
        self._conn = v

    def CreateParameter(self, name="", type_=202, direction=1, size=0, value=None):
        return Parameter(_to_str(name), _to_int(type_, 202), _to_int(direction, 1), _to_int(size),
                         _plain(value) if _given(value) else None)

    def _sql(self, params=None):
        sql = _to_str(self.CommandText)
        if _to_int(self.CommandType) == 2:
            return f"SELECT * FROM [{sql.strip('[]')}]"
        vals = [p.Value for p in self.Parameters._items]
        if params is not None and _given(params):
            vals = list(params) if isinstance(params, (list, tuple)) else (
                [params] if not hasattr(params, "items") else [x for x in params.items()])
        db = self._conn._need() if self._conn else None
        parts = re.split(r"('(?:[^']|'')*')", sql)
        it = iter(vals)
        out = []
        for part in parts:
            if part.startswith("'"):
                out.append(part)
            else:
                out.append(re.sub(r"\?", lambda m: _literal(db, next(it, None)), part))
        return "".join(out)

    def Execute(self, records_affected=None, params=None, options=None):
        if self._conn is None:
            raise _err(3709, "The connection cannot be used to perform this operation.")
        return self._conn.Execute(self._sql(params))


def _literal(db, v, typ: int | None = None) -> str:
    v = _plain(v)
    if v is None or not _given(v):
        return "NULL"
    if isinstance(v, bool):
        return (db.bool_true if v else db.bool_false) if db else ("True" if v else "False")
    if isinstance(v, _dt.datetime):
        return db.date_literal(v) if db else "#" + v.strftime("%m/%d/%Y %H:%M:%S") + "#"
    if isinstance(v, (int, float)):
        if typ in TEXT_TYPES:
            return "'" + _to_str(v) + "'"
        return repr(v) if isinstance(v, float) else str(v)
    s = str(v)
    if typ in NUM_TYPES:
        t = s.strip()
        if t == "":
            return "NULL"
        try:
            float(t)
            return t
        except ValueError:
            pass
    if typ in DATE_TYPES:
        d = _parse_date(s)
        if d is not None:
            return db.date_literal(d) if db else d.strftime("#%m/%d/%Y#")
        if s.strip() == "":
            return "NULL"
    if typ in BOOL_TYPES:
        if s.strip().lower() in ("true", "-1", "1", "yes"):
            return db.bool_true if db else "True"
        if s.strip().lower() in ("false", "0", "no", ""):
            return db.bool_false if db else "False"
    return "'" + s.replace("'", "''") + "'"


def _ident(name: str) -> str:
    return "[" + name.replace("]", "]]") + "]"


_FROM = re.compile(r"\bfrom\s+(\[[^\]]+\]|[\w$#]+)(?:\s+(?:as\s+)?(?!where\b|order\b|group\b|inner\b|left\b|"
                   r"right\b|join\b|having\b|union\b)\w+)?\s*(?:$|where\b|order\b|group\b|having\b|;)", re.I)


def _criteria(expr: str):
    """Compile a Find / Filter / FindFirst criteria string ("Name = 'x' AND Age > 3", LIKE with * or %)."""
    toks = re.findall(r"\[[^\]]+\]|'(?:[^']|'')*'|\"[^\"]*\"|#[^#]+#|<>|<=|>=|=|<|>|\(|\)|[\w.$]+", expr)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def value(t):
        if t is None:
            return None
        if t[0] in "'\"":
            return t[1:-1].replace("''", "'")
        if t[0] == "#":
            return _parse_date(t[1:-1]) or t[1:-1]
        if t.lower() == "null":
            return None
        try:
            return float(t) if "." in t else int(t)
        except ValueError:
            return t

    def comp():
        t = take()
        if t == "(":
            f = disj()
            take()
            return f
        if t and t.lower() == "not":
            f = comp()
            return lambda row: not f(row)
        col = (t or "").strip("[]")
        op = (take() or "=").lower()
        if op == "is":
            neg = peek() and peek().lower() == "not"
            if neg:
                take()
            take()
            return (lambda row: row(col) is not None) if neg else (lambda row: row(col) is None)
        if op == "not" and peek() and peek().lower() == "like":
            take()
            f = _like(col, value(take()))
            return lambda row: not f(row)
        v = value(take())
        if op == "like":
            return _like(col, v)

        def cmp(row):
            a = row(col)
            b = v
            if a is None:
                return False
            if isinstance(a, str) or isinstance(b, str):
                a, b = _to_str(a).lower(), _to_str(b).lower()
                if isinstance(row(col), (int, float)) and not isinstance(row(col), bool):
                    try:
                        a, b = float(row(col)), float(v)
                    except (TypeError, ValueError):
                        pass
            try:
                return {"=": a == b, "<>": a != b, "<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]
            except TypeError:
                return False
        return cmp

    def conj():
        f = comp()
        while peek() and peek().lower() == "and":
            take()
            g = comp()
            f = (lambda f1, g1: lambda row: f1(row) and g1(row))(f, g)
        return f

    def disj():
        f = conj()
        while peek() and peek().lower() == "or":
            take()
            g = conj()
            f = (lambda f1, g1: lambda row: f1(row) or g1(row))(f, g)
        return f
    return disj()


def _like(col, pat):
    rx = "^" + "".join(".*" if c in "*%" else "." if c in "?_" else re.escape(c) for c in _to_str(pat)) + "$"
    r = re.compile(rx, re.I | re.S)
    return lambda row: row(col) is not None and bool(r.match(_to_str(row(col))))


class Recordset(_VBObj):
    """Client-side (static) recordset shared by ADO and DAO."""
    vb_typename = "Recordset"
    vb_default = "fields"

    def __init__(self, dao: bool = False):
        self._dao = dao
        self._conn = None
        self._cols: list[str] = []
        self._types: list[int] = []
        self._rows: list[list] = []
        self._all: list[list] | None = None
        self._pos = 0
        self._open = False
        self._edit = None                 # dict col index -> new value
        self._mode = 0                    # 0 none, 1 edit, 2 add
        self._table = None
        self._key: list[str] | None = None
        self._lock = 1
        self.Source = ""
        self.CursorType = 0
        self.CursorLocation = 3
        self.CacheSize = 1
        self.MaxRecords = 0
        self.PageSize = 10
        self.NoMatch = False
        self._filter = ""
        self._sort = ""
        self._bindings: list = []          # callbacks (data controls refresh bound controls)
        self._pre_update: list = []        # callbacks before Update (data controls write bound controls)

    # -- loading
    def _load(self, conn, sql, cols, types, rows, lock=3):
        self._conn = conn
        self.Source = sql
        self._cols = list(cols)
        self._types = list(types or [202] * len(cols))
        self._rows = rows
        self._all = None
        self._pos = 0 if rows else 0
        self._open = True
        self._lock = lock
        self._mode = 0
        self._edit = None
        self._filter = ""
        self._sort = ""
        m = _FROM.search(sql or "")
        self._table = m.group(1).strip("[]") if m and not re.search(r"\bjoin\b|,\s*\w+\s*(where|$)", sql, re.I) \
            else None
        self._key = None
        self._notify()

    def _notify(self):
        for cb in list(self._bindings):
            try:
                cb(self)
            except Exception:  # noqa: BLE001
                pass

    # -- properties
    @property
    def State(self):
        return 1 if self._open else 0

    @property
    def EOF(self):
        self._need()
        return self._pos >= len(self._rows) or not self._rows

    @property
    def BOF(self):
        self._need()
        return self._pos < 0 or not self._rows

    @property
    def RecordCount(self):
        self._need()
        return len(self._rows)

    @property
    def AbsolutePosition(self):
        return self._pos + 1 if 0 <= self._pos < len(self._rows) else -1

    @AbsolutePosition.setter
    def AbsolutePosition(self, v):
        self._commit_pending()
        self._pos = max(0, min(len(self._rows), _to_int(v) - 1))
        self._notify()

    PercentPosition = AbsolutePosition

    @property
    def Bookmark(self):
        r = self._current_row(False)
        return id(r) if r is not None else 0

    @Bookmark.setter
    def Bookmark(self, v):
        for i, r in enumerate(self._rows):
            if id(r) == v:
                self._pos = i
                self._notify()
                return
        raise _err(3021, "Either BOF or EOF is True, or the current record has been deleted.")

    @property
    def Fields(self):
        return Fields(self)

    @property
    def ActiveConnection(self):
        return self._conn

    @ActiveConnection.setter
    def ActiveConnection(self, v):
        self._conn = v

    @property
    def LockType(self):
        return self._lock

    @LockType.setter
    def LockType(self, v):
        self._lock = _to_int(v, 1)

    @property
    def EditMode(self):
        return self._mode

    @property
    def Updatable(self):
        return self._lock != 1 and bool(self._table)

    @property
    def Filter(self):
        return self._filter

    @Filter.setter
    def Filter(self, v):
        self._commit_pending()
        crit = _to_str(v) if not isinstance(_plain(v), (int, float)) else ""
        if self._all is None:
            self._all = self._rows
        if crit.strip():
            f = _criteria(crit)
            self._rows = [r for r in self._all if f(self._getter(r))]
        else:
            self._rows = self._all
            self._all = None
        self._filter = crit
        self._pos = 0
        self._notify()

    @property
    def Sort(self):
        return self._sort

    @Sort.setter
    def Sort(self, v):
        self._sort = _to_str(v)
        for part in reversed([p.strip() for p in self._sort.split(",") if p.strip()]):
            bits = part.split()
            col = self._index(bits[0].strip("[]"))
            desc = len(bits) > 1 and bits[1].lower() == "desc"
            self._rows.sort(key=lambda r: (r[col] is None, r[col] if r[col] is not None else 0), reverse=desc)
        self._pos = 0
        self._notify()

    @property
    def Index(self):
        return ""

    @Index.setter
    def Index(self, v):
        pass

    @property
    def Name(self):
        return self.Source

    # -- helpers
    def _need(self):
        if not self._open:
            raise _err(3704, "Operation is not allowed when the object is closed.")

    def _index(self, key) -> int:
        key = _plain(key)
        if isinstance(key, (int, float)) and not isinstance(key, bool):
            i = int(key)
            if not 0 <= i < len(self._cols):
                raise _err(3265, "Item cannot be found in the collection corresponding to the requested name "
                                 "or ordinal.")
            return i
        k = _to_str(key).strip("[]").lower()
        for i, c in enumerate(self._cols):
            if c.lower() == k:
                return i
        for i, c in enumerate(self._cols):              # "table.col" in a join
            if c.lower().split(".")[-1] == k.split(".")[-1]:
                return i
        raise _err(3265, f"Item cannot be found in the collection corresponding to the requested name or "
                         f"ordinal ({_to_str(key)}).")

    def _field(self, key) -> Field:
        self._need()
        return Field(self, self._index(key))

    def _getter(self, row):
        return lambda col: row[self._index(col)]

    def _current_row(self, strict=True):
        if 0 <= self._pos < len(self._rows):
            return self._rows[self._pos]
        if strict:
            raise _err(3021, "Either BOF or EOF is True, or the current record has been deleted. "
                             "Requested operation requires a current record.")
        return None

    def _get_value(self, i):
        self._need()
        if self._mode and self._edit is not None and i in self._edit:
            return self._edit[i]
        if self._mode == 2:
            return None
        return self._current_row()[i]

    def _set_value(self, i, v):
        self._need()
        if self._lock == 1 and not self._dao:
            raise _err(3251, "Current Recordset does not support updating. This may be a limitation of the "
                             "provider, or of the selected locktype.")
        if not self._mode:
            self._current_row()
            self._mode = 1
            self._edit = {}
        self._edit[i] = v

    def _commit_pending(self):
        if self._mode and not self._dao:
            self.Update()
        elif self._mode:
            self._mode, self._edit = 0, None

    def _db(self):
        if self._conn is None:
            raise _err(3709, "The connection cannot be used to perform this operation.")
        return self._conn._need()

    def _keys(self):
        if self._key is None:
            pk = self._db().primary_key(self._table) if self._table else []
            self._key = [c for c in pk if any(c.lower() == x.lower() for x in self._cols)]
        return self._key

    def _where(self, row):
        db = self._db()
        keys = self._keys()
        idxs = [self._index(k) for k in keys] if keys else [
            i for i, t in enumerate(self._types) if t not in LONG_TYPES]
        conds = []
        for i in idxs:
            v = row[i]
            if v is None:
                conds.append(f"{_ident(self._cols[i])} IS NULL")
            elif isinstance(v, float) and not keys:
                continue                                  # float equality is unreliable
            else:
                conds.append(f"{_ident(self._cols[i])} = {_literal(db, v, self._types[i])}")
        return " AND ".join(conds) or "1=1"

    def _need_table(self):
        if not self._table:
            raise _err(3251, "Current Recordset does not support updating (the source is not a single table).")

    # -- navigation
    def MoveFirst(self):
        self._need()
        self._commit_pending()
        self._pos = 0
        self._notify()

    def MoveLast(self):
        self._need()
        self._commit_pending()
        self._pos = max(0, len(self._rows) - 1)
        self._notify()

    def MoveNext(self):
        self._need()
        if self._pos >= len(self._rows):
            raise _err(3021, "Either BOF or EOF is True, or the current record has been deleted. "
                             "Requested operation requires a current record.")
        self._commit_pending()
        self._pos += 1
        self._notify()

    def MovePrevious(self):
        self._need()
        if self._pos < 0:
            raise _err(3021, "Either BOF or EOF is True, or the current record has been deleted. "
                             "Requested operation requires a current record.")
        self._commit_pending()
        self._pos -= 1
        self._notify()

    def Move(self, n, start=None):
        self._need()
        self._commit_pending()
        self._pos = max(-1, min(len(self._rows), self._pos + _to_int(n)))
        self._notify()

    # -- open / close
    def Open(self, source=None, conn=None, cursor_type=None, lock_type=None, options=None):
        if self._open:
            raise _err(3705, "Operation is not allowed when the object is open.")
        if _given(source):
            src = source
            self.Source = _to_str(source) if not isinstance(source, Command) else source.CommandText
        else:
            src = self.Source
        if _given(conn):
            if isinstance(conn, str):
                c = Connection(conn)
                c.Open()
                conn = c
            self._conn = conn
        if self._conn is None:
            raise _err(3709, "The connection cannot be used to perform this operation. It is either closed or "
                             "invalid in this context.")
        if _given(cursor_type):
            self.CursorType = _to_int(cursor_type)
        if _given(lock_type):
            self._lock = _to_int(lock_type, 1)
        sql = src._sql() if isinstance(src, Command) else _to_str(src)
        if _to_int(options, 0) & 2 or (re.fullmatch(r"\s*\[?[\w ]+\]?\s*", sql) and not re.match(
                r"\s*(select|exec)\b", sql, re.I)):
            sql = f"SELECT * FROM [{sql.strip().strip('[]')}]"
        cols, types, rows, _aff = self._conn._need().execute(sql)
        if cols is None:                           # an action query opened as a recordset
            self._open = False
            return None
        self._load(self._conn, sql, cols, types, rows, self._lock if not self._dao else 3)
        return None

    def Close(self):
        self._need()
        self._open = False
        self._rows, self._mode, self._edit = [], 0, None
        self._notify()

    def Requery(self, options=None):
        self._need()
        lock = self._lock
        self._open = False
        self.Open(self.Source, self._conn, None, lock)

    def Resync(self, *a):
        return None

    def Refresh(self):
        self.Requery()

    # -- editing
    def AddNew(self, fields=None, values=None):
        self._need()
        if self._lock == 1 and not self._dao:
            raise _err(3251, "Current Recordset does not support updating. This may be a limitation of the "
                             "provider, or of the selected locktype.")
        self._commit_pending()
        self._mode, self._edit = 2, {}
        if _given(fields):
            self._assign(fields, values)
            if not self._dao:
                self.Update()

    def Edit(self):                                # DAO
        self._need()
        self._current_row()
        self._mode, self._edit = 1, {}

    def _assign(self, fields, values):
        fl = fields if isinstance(fields, (list, tuple)) else (
            fields.items() if hasattr(fields, "items") and callable(fields.items) else [fields])
        vl = values if isinstance(values, (list, tuple)) else (
            values.items() if hasattr(values, "items") and callable(values.items) else [values])
        for f, v in zip(list(fl), list(vl)):
            self._edit[self._index(f)] = _plain(v)

    def Update(self, fields=None, values=None):
        self._need()
        for cb in list(self._pre_update):
            cb(self)
        if _given(fields):
            if not self._mode:
                self._mode, self._edit = 1, {}
            self._assign(fields, values)
        if not self._mode:
            if self._dao:
                raise _err(3020, "Update or CancelUpdate without AddNew or Edit.")
            return None
        self._need_table()
        db = self._db()
        edit = self._edit or {}
        if self._mode == 2:
            cols = sorted(edit)
            if cols:
                sql = (f"INSERT INTO {_ident(self._table)} (" + ", ".join(_ident(self._cols[i]) for i in cols) +
                       ") VALUES (" + ", ".join(_literal(db, edit[i], self._types[i]) for i in cols) + ")")
            else:
                sql = f"INSERT INTO {_ident(self._table)} DEFAULT VALUES"
            db.execute(sql)
            row = [edit.get(i) for i in range(len(self._cols))]
            for i, v in list(enumerate(row)):
                t = self._types[i]
                if v is not None and t in NUM_TYPES and isinstance(v, str):
                    try:
                        row[i] = float(v) if "." in v else int(v)
                    except ValueError:
                        pass
            keys = self._keys()
            if len(keys) == 1 and row[self._index(keys[0])] is None:       # AutoNumber
                try:
                    c, _t, r, _a = db.execute("SELECT @@IDENTITY" if db.kind != "sqlite" else
                                              "SELECT last_insert_rowid()")
                    if r:
                        row[self._index(keys[0])] = r[0][0]
                except Exception:  # noqa: BLE001
                    pass
            self._rows.append(row)
            if self._all is not None and self._all is not self._rows:
                self._all.append(row)
            self._pos = len(self._rows) - 1
        else:
            row = self._current_row()
            if edit:
                sets = ", ".join(f"{_ident(self._cols[i])} = {_literal(db, v, self._types[i])}"
                                 for i, v in sorted(edit.items()))
                db.execute(f"UPDATE {_ident(self._table)} SET {sets} WHERE {self._where(row)}")
                for i, v in edit.items():
                    row[i] = v
        self._mode, self._edit = 0, None
        self._notify()
        return None

    def UpdateBatch(self, *a):
        return self.Update()

    def CancelUpdate(self):
        self._mode, self._edit = 0, None
        self._notify()

    CancelBatch = CancelUpdate

    def Delete(self, affect=None):
        self._need()
        self._need_table()
        if self._lock == 1 and not self._dao:
            raise _err(3251, "Current Recordset does not support updating.")
        row = self._current_row()
        self._db().execute(f"DELETE FROM {_ident(self._table)} WHERE {self._where(row)}")
        self._rows.pop(self._pos)
        if self._all is not None and self._all is not self._rows:
            self._all = [r for r in self._all if r is not row]
        self._mode, self._edit = 0, None
        if self._dao:
            pass                                      # DAO: current record is invalid until a Move
        self._notify()

    # -- searching
    def _find(self, crit, start, step):
        f = _criteria(_to_str(crit))
        i = start
        while 0 <= i < len(self._rows):
            if f(self._getter(self._rows[i])):
                return i
            i += step
        return None

    def Find(self, criteria, skip=0, direction=1, start=None):
        self._need()
        self._commit_pending()
        step = -1 if _to_int(direction, 1) == -1 else 1
        i = self._find(criteria, max(0, self._pos) + _to_int(skip) * step, step)
        self._pos = i if i is not None else (len(self._rows) if step == 1 else -1)
        self._notify()

    def FindFirst(self, criteria):
        i = self._find(criteria, 0, 1)
        self.NoMatch = i is None
        if i is not None:
            self._pos = i
            self._notify()

    def FindLast(self, criteria):
        i = self._find(criteria, len(self._rows) - 1, -1)
        self.NoMatch = i is None
        if i is not None:
            self._pos = i
            self._notify()

    def FindNext(self, criteria):
        i = self._find(criteria, self._pos + 1, 1)
        self.NoMatch = i is None
        if i is not None:
            self._pos = i
            self._notify()

    def FindPrevious(self, criteria):
        i = self._find(criteria, self._pos - 1, -1)
        self.NoMatch = i is None
        if i is not None:
            self._pos = i
            self._notify()

    def Seek(self, op, *keys):
        keys_ = self._keys() or self._cols[:1]
        crit = " AND ".join(f"[{k}] {_to_str(op)} {_literal(None, v)}" for k, v in zip(keys_, keys))
        self.FindFirst(crit)

    # -- bulk
    def GetRows(self, rows=-1, start=None, fields=None):
        self._need()
        n = _to_int(rows, -1)
        chunk = self._rows[max(0, self._pos):] if n < 0 else self._rows[max(0, self._pos):max(0, self._pos) + n]
        self._pos = min(len(self._rows), max(0, self._pos) + len(chunk))
        try:
            from .vbinterp import VBArray  # type: ignore
            arr = VBArray([(0, len(self._cols) - 1), (0, len(chunk) - 1)])
            for r, row in enumerate(chunk):
                for c, v in enumerate(row):
                    arr.set([c, r], v)
            return arr
        except ImportError:
            return [list(col) for col in zip(*chunk)] if chunk else []

    def GetString(self, fmt=2, rows=-1, col_delim="\t", row_delim="\r", null_expr=""):
        self._need()
        cd = _to_str(col_delim) if _given(col_delim) else "\t"
        rd = _to_str(row_delim) if _given(row_delim) else "\r"
        ne = _to_str(null_expr) if _given(null_expr) else ""
        out = []
        for row in self._rows[max(0, self._pos):]:
            out.append(cd.join(ne if v is None else _to_str(v) for v in row) + rd)
        self._pos = len(self._rows)
        return "".join(out)

    def Clone(self, lock=None):
        rs = Recordset(self._dao)
        rs._load(self._conn, self.Source, self._cols, self._types, self._rows, self._lock)
        return rs

    def Supports(self, what):
        return True

    def NextRecordset(self, *a):
        return None

    def Save(self, *a):
        return None

    def CopyQueryDef(self):
        return None

    @property
    def DateCreated(self):
        return _dt.datetime.now()

    # Python conveniences (migrated code)
    def __call__(self, key):
        return self._field(key)

    def __getitem__(self, key):
        return self._field(key)

    def __setitem__(self, key, value):
        self._field(key).Value = value

    def vb_setitem(self, args, value):
        self._field(args[0]).Value = value

    def vb_items(self):
        return Fields(self).vb_items()


# ============================================================================ DAO
class Database(_VBObj):
    vb_typename = "Database"

    def __init__(self, path: str, base: Path | None = None, connect: str = "", read_only=False):
        real = resolve_db_path(path, base)
        self.Name = real
        self.Connect = connect
        self.Updatable = not read_only
        cs, pairs = fix_connstr(f"Provider=Microsoft.Jet.OLEDB.4.0;Data Source={real}"
                                if not re.search(r"\.(db|sqlite3?)$", real, re.I) else f"Data Source={real}", "",
                                base)
        if connect and ";pwd=" in connect.lower():
            pwd = re.search(r";pwd=([^;]*)", connect, re.I).group(1)
            cs += f";Jet OLEDB:Database Password={pwd}"
        self._conn = Connection(cs)
        self._conn._base = base
        self._conn.Open()
        self.RecordsAffected = 0

    def OpenRecordset(self, source, type_=None, options=None, lockedit=None):
        rs = Recordset(dao=True)
        rs.Open(_to_str(source), self._conn, 1, 3)
        return rs

    def Execute(self, sql, options=None):
        self._conn.Execute(_to_str(sql))
        self.RecordsAffected = getattr(self._conn, "_affected", 0)

    def Close(self):
        if self._conn.State:
            self._conn.Close()

    @property
    def TableDefs(self):
        names = self._conn._need().tables()
        return _NamedList([_TableDef(n) for n in names])

    def CreateQueryDef(self, name="", sql=""):
        return _QueryDef(self, _to_str(sql))


class _TableDef(_VBObj):
    vb_typename = "TableDef"

    def __init__(self, name):
        self.Name = name
        self.Attributes = 0


class _QueryDef(_VBObj):
    vb_typename = "QueryDef"

    def __init__(self, db, sql):
        self._db, self.SQL = db, sql

    def OpenRecordset(self, *a):
        return self._db.OpenRecordset(self.SQL)

    def Execute(self, *a):
        self._db.Execute(self.SQL)


class _NamedList(_VBObj):
    vb_default = "item"

    def __init__(self, items):
        self._items = items

    @property
    def Count(self):
        return len(self._items)

    def Item(self, k):
        k = _plain(k)
        if isinstance(k, str):
            for it in self._items:
                if it.Name.lower() == k.lower():
                    return it
            raise _err(3265, f"Item not found in this collection ({k})")
        return self._items[int(k)]

    def vb_items(self):
        return list(self._items)


class Workspace(_VBObj):
    vb_typename = "Workspace"

    def __init__(self, engine):
        self._engine = engine
        self.Name = "#Default Workspace#"
        self.UserName = "admin"

    def OpenDatabase(self, name, options=None, read_only=None, connect=None):
        return Database(_to_str(name), self._engine.base, _to_str(connect) if _given(connect) else "",
                        bool(_plain(read_only)) if _given(read_only) else False)

    def BeginTrans(self):
        return None

    def CommitTrans(self, *a):
        return None

    def Rollback(self):
        return None

    def Close(self):
        return None


class DBEngine(_VBObj):
    vb_typename = "DBEngine"

    def __init__(self, base: Path | None = None):
        self.base = base
        self._ws = Workspace(self)
        self.Version = "3.6"
        self.DefaultUser = "admin"
        self.DefaultPassword = ""

    @property
    def Workspaces(self):
        return _NamedList([self._ws])

    def OpenDatabase(self, name, options=None, read_only=None, connect=None):
        return self._ws.OpenDatabase(name, options, read_only, connect)

    def CreateWorkspace(self, *a):
        return self._ws

    def CompactDatabase(self, *a):
        return None

    def RepairDatabase(self, *a):
        return None

    def Idle(self, *a):
        return None


# ============================================================================ constants
CONSTANTS = {
    # ADO CursorTypeEnum / LockTypeEnum / CommandTypeEnum / CursorLocationEnum / ObjectStateEnum ...
    "adopenforwardonly": 0, "adopenkeyset": 1, "adopendynamic": 2, "adopenstatic": 3, "adopenunspecified": -1,
    "adlockreadonly": 1, "adlockpessimistic": 2, "adlockoptimistic": 3, "adlockbatchoptimistic": 4,
    "adlockunspecified": -1, "adcmdtext": 1, "adcmdtable": 2, "adcmdstoredproc": 4, "adcmdunknown": 8,
    "adcmdtabledirect": 512, "adcmdfile": 256, "adexecutenorecords": 128, "adasyncexecute": 16,
    "aduseclient": 3, "aduseserver": 2, "adusenone": 1, "adstateclosed": 0, "adstateopen": 1,
    "adstateconnecting": 2, "adstateexecuting": 4, "adstatefetching": 8,
    "adsearchforward": 1, "adsearchbackward": -1, "adbookmarkfirst": 1, "adbookmarklast": 2,
    "adbookmarkcurrent": 0, "adaffectcurrent": 1, "adaffectgroup": 2, "adaffectall": 3,
    "adfilternone": 0, "adfilterpendingrecords": 1, "adeditnone": 0, "adeditinprogress": 1, "adeditadd": 2,
    "adschematables": 20, "adschemacolumns": 4, "adschemaprimarykeys": 28, "adclipstring": 2,
    "adinteger": 3, "adsmallint": 2, "adbigint": 20, "adtinyint": 16, "adunsignedtinyint": 17, "adsingle": 4,
    "addouble": 5, "adcurrency": 6, "addecimal": 14, "adnumeric": 131, "adboolean": 11, "addate": 7,
    "addbdate": 133, "addbtime": 134, "addbtimestamp": 135, "adbstr": 8, "adchar": 129, "advarchar": 200,
    "adlongvarchar": 201, "adwchar": 130, "advarwchar": 202, "adlongvarwchar": 203, "adbinary": 128,
    "advarbinary": 204, "adlongvarbinary": 205, "advariant": 12, "adempty": 0, "adguid": 72,
    "adparaminput": 1, "adparamoutput": 2, "adparaminputoutput": 3, "adparamreturnvalue": 4,
    "admoderead": 1, "admodewrite": 2, "admodereadwrite": 3, "admodesharedenynone": 16, "admodeunknown": 0,
    "adxactreadcommitted": 4096, "adresyncallvalues": 2, "adpromptnever": 4, "adpersistxml": 1,
    # DAO
    "dbopentable": 1, "dbopendynaset": 2, "dbopensnapshot": 4, "dbopenforwardonly": 8, "dbopendynamic": 16,
    "dbreadonly": 4, "dbappendonly": 8, "dbseechanges": 512, "dbfailonerror": 128, "dbdenywrite": 1,
    "dbdenyread": 2, "dbinconsistent": 16, "dbconsistent": 32, "dbsqlpassthrough": 64,
    "dbpessimistic": 2, "dboptimistic": 3, "dbeditnone": 0, "dbeditinprogress": 1, "dbeditadd": 2,
    "dbtext": 10, "dblong": 4, "dbinteger": 3, "dbdouble": 7, "dbsingle": 6, "dbdate": 8, "dbboolean": 1,
    "dbcurrency": 5, "dbmemo": 12, "dbbyte": 2, "dblanggeneral": ";LANGID=0x0409;CP=1252;COUNTRY=0",
    "dbversion40": 64, "dbversion30": 32, "dbautoincrfield": 16,
    # data control
    "vbdataactionmovefirst": 1, "vbdataactionmoveprevious": 2, "vbdataactionmovenext": 3,
    "vbdataactionmovelast": 4, "vbdataactionaddnew": 5, "vbdataactionupdate": 6, "vbdataactiondelete": 7,
    "vbdataactionfind": 8, "vbdataactionbookmark": 9, "vbdataactionclose": 10, "vbdataactionunload": 11,
    "vbdataactioncancel": 0, "vbmovefirst": 0, "vbbofactionmovefirst": 0, "vbeofactionmovelast": 0,
    "vbeofactionaddnew": 2, "adbofactionmovefirst": 0, "adeofactionmovelast": 0, "adeofactionaddnew": 2,
    # common controls (MSComctlLib / MSComCtl2) used with these programs
    "tvwfirst": 0, "tvwlast": 1, "tvwnext": 2, "tvwprevious": 3, "tvwchild": 4, "tvwtextonly": 0,
    "tvwtreelinestext": 4, "tvwtreelinesplusminustext": 6, "tvwtreelinesplusminuspicturetext": 7,
    "lvwicon": 0, "lvwsmallicon": 1, "lvwlist": 2, "lvwreport": 3, "lvwascending": 0, "lvwdescending": 1,
    "lvwcolumnleft": 0, "lvwcolumnright": 1, "lvwcolumncenter": 2, "sbrtext": 0, "sbrsimple": 1, "sbrnormal": 0,
    "dtplongdate": 0, "dtpshortdate": 1, "dtptime": 2, "dtpcustom": 3, "flexalignleftcenter": 1,
    "flexaligncentercenter": 4, "flexalignrightcenter": 7, "flexselectionbyrow": 1, "flexselectionfree": 0,
    "cdlofnfilemustexist": 4096, "cdlofnhidereadonly": 4, "cdlofnoverwriteprompt": 2, "cdlofnpathmustexist": 2048,
    "cdlcfboth": 3, "cdlcfeffects": 256, "cdlccrgbinit": 1,
}


_CANON = """adOpenForwardOnly adOpenKeyset adOpenDynamic adOpenStatic adOpenUnspecified adLockReadOnly
adLockPessimistic adLockOptimistic adLockBatchOptimistic adLockUnspecified adCmdText adCmdTable adCmdStoredProc
adCmdUnknown adCmdTableDirect adCmdFile adExecuteNoRecords adAsyncExecute adUseClient adUseServer adUseNone
adStateClosed adStateOpen adStateConnecting adStateExecuting adStateFetching adSearchForward adSearchBackward
adBookmarkFirst adBookmarkLast adBookmarkCurrent adAffectCurrent adAffectGroup adAffectAll adFilterNone
adFilterPendingRecords adEditNone adEditInProgress adEditAdd adSchemaTables adSchemaColumns adSchemaPrimaryKeys
adClipString adInteger adSmallInt adBigInt adTinyInt adUnsignedTinyInt adSingle adDouble adCurrency adDecimal
adNumeric adBoolean adDate adDBDate adDBTime adDBTimeStamp adBSTR adChar adVarChar adLongVarChar adWChar
adVarWChar adLongVarWChar adBinary adVarBinary adLongVarBinary adVariant adEmpty adGUID adParamInput
adParamOutput adParamInputOutput adParamReturnValue adModeRead adModeWrite adModeReadWrite adModeShareDenyNone
adModeUnknown adXactReadCommitted adResyncAllValues adPromptNever adPersistXML dbOpenTable dbOpenDynaset
dbOpenSnapshot dbOpenForwardOnly dbOpenDynamic dbReadOnly dbAppendOnly dbSeeChanges dbFailOnError dbDenyWrite
dbDenyRead dbInconsistent dbConsistent dbSQLPassThrough dbPessimistic dbOptimistic dbEditNone dbEditInProgress
dbEditAdd dbText dbLong dbInteger dbDouble dbSingle dbDate dbBoolean dbCurrency dbMemo dbByte dbLangGeneral
dbVersion40 dbVersion30 dbAutoIncrField""".split()
CANONICAL_CONSTANTS = {n: CONSTANTS[n.lower()] for n in _CANON if n.lower() in CONSTANTS}


# ============================================================================ factory
_CLASSES = {
    "adodb.connection": Connection, "connection": Connection, "adodb.recordset": Recordset, "recordset": Recordset,
    "adodb.command": Command, "command": Command, "adodb.parameter": Parameter, "parameter": Parameter,
    "adodb.field": None, "dao.dbengine": DBEngine, "dao.dbengine.36": DBEngine, "dao.dbengine.35": DBEngine,
    "dbengine": DBEngine, "dao.recordset": None, "adodb.stream": None,
}


def create(progid: str, base=None):
    """An emulated ADO / DAO object for *progid* (``New ADODB.Recordset``, ``CreateObject("ADODB.Connection")``)
    or None."""
    p = (progid or "").strip().lower()
    if p.endswith(".6.0") or p.endswith(".2.8"):
        p = p.rsplit(".", 2)[0]
    k = _CLASSES.get(p)
    if k is None:
        return None
    if k is DBEngine:
        return DBEngine(Path(base) if base else None)
    obj = k()
    if isinstance(obj, Connection) and base:
        obj._base = Path(base)
    return obj


def open_database(name, options=None, read_only=None, connect=None, base=None):
    """DAO's global OpenDatabase(...)."""
    return DBEngine(Path(base) if base else None).OpenDatabase(name, options, read_only, connect)
