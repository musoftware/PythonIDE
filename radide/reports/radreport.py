"""radreport - banded reports for RAD IDE programs (a copy of this file lives in every project that uses
reports; the IDE's report designer uses the very same module).

A report is a JSON file (``Name.rpt.json``) made in the IDE's Report Designer:

* bands: report header/footer, page header/footer, group header/footer (one pair per group field) and detail;
* items: text (with ``{expression}`` placeholders), field, expression, line, box, image, barcode / QR code,
  chart (bar / line / pie);
* data: an SQL query on a database connection (SQLite built in; MySQL with pymysql, PostgreSQL with psycopg),
  a CSV or JSON file, inline rows, or rows given by code (``SetData``); parameters (``:Name`` in SQL,
  ``Parameters.Name`` in expressions).

Expressions are small Python expressions: field names (``Qty * Price`` or ``Fields["Unit Price"]``),
``Parameters.Name``, ``Sum("Amount")``, ``Count()``, ``Avg``, ``Min``, ``Max``, ``First``, ``Last``,
``CountDistinct``, ``RunningSum("Amount")``, ``RunningCount()``, ``PageNumber``, ``TotalPages``, ``RowNumber``,
``Now()``, ``Today()``, ``IIf(c, a, b)``, ``Format(v, "N2")``.

Use from code::

    import radreport
    r = radreport.Report("Invoice.rpt.json")
    r.Parameters["CustomerId"] = 3
    r.ExportPdf("invoice.pdf")              # also ExportHtml / ExportCsv / ExportExcel / Print()

    radreport.show("Invoice.rpt.json")      # a preview window (Qt)

Forms use the ReportViewer control (``QtReportViewer`` for Qt programs, ``TkReportViewer`` for Tkinter).
Drawing, PDF and printing use Qt (PySide6 or PyQt6, whichever is installed); Excel export needs openpyxl,
barcodes python-barcode, QR codes qrcode.  Arabic and other right-to-left text is shaped and ordered by Qt.
"""
from __future__ import annotations

import base64
import csv
import datetime as _dt
import importlib
import io
import json
import math
import os
import re
import sqlite3
import sys
import unicodedata
from types import SimpleNamespace

VERSION = "1.0"

PAPER = {"A4": (595.28, 841.89), "A3": (841.89, 1190.55), "A5": (419.53, 595.28), "Letter": (612.0, 792.0),
         "Legal": (612.0, 1008.0), "B5": (498.9, 708.66)}
BAND_KINDS = ("reportHeader", "pageHeader", "detail", "reportFooter", "pageFooter")
BAND_TITLES = {"reportHeader": "Report Header", "pageHeader": "Page Header", "detail": "Detail",
               "reportFooter": "Report Footer", "pageFooter": "Page Footer",
               "groupHeader": "Group Header", "groupFooter": "Group Footer"}
ITEM_TYPES = ("text", "field", "expression", "line", "box", "image", "barcode", "chart")
CHART_COLORS = ("#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5", "#70AD47", "#264478", "#9E480E",
                "#636363", "#997300")


class ReportError(Exception):
    """A problem with the report definition or its data (message ready to show)."""


# ============================================================================== definition helpers
def new_report(name: str = "Report1") -> dict:
    """An empty report definition (A4 portrait, the usual bands)."""
    return {
        "format": "radreport", "version": 1, "name": name, "title": name,
        "page": {"size": "A4", "orientation": "Portrait", "margins": [36, 36, 36, 36]},
        "rightToLeft": False, "mirrorLayout": False,
        "font": {"name": "Segoe UI", "size": 10},
        "dataSource": {"type": "none"},
        "parameters": [], "sort": [], "filter": "", "sortByGroups": True,
        "groups": [],
        "bands": {
            "reportHeader": {"height": 50, "items": []},
            "pageHeader": {"height": 30, "items": []},
            "detail": {"height": 20, "items": []},
            "reportFooter": {"height": 40, "items": []},
            "pageFooter": {"height": 24, "items": []},
        },
    }


def new_group(field: str = "", name: str = "") -> dict:
    return {"name": name or f"Group_{field or 'X'}", "field": field, "expression": "", "newPage": False,
            "repeatHeader": True, "keepTogether": False, "sort": "asc",
            "header": {"height": 26, "items": []}, "footer": {"height": 26, "items": []}}


def page_size(defn: dict) -> tuple[float, float]:
    """(width, height) of the page in points, orientation applied."""
    pg = defn.get("page") or {}
    if pg.get("width") and pg.get("height"):
        w, h = float(pg["width"]), float(pg["height"])
    else:
        w, h = PAPER.get(str(pg.get("size") or "A4"), PAPER["A4"])
    if str(pg.get("orientation") or "Portrait").lower().startswith("land"):
        w, h = max(w, h), min(w, h)
    return w, h


def margins(defn: dict) -> tuple[float, float, float, float]:
    """(left, top, right, bottom) in points."""
    m = (defn.get("page") or {}).get("margins") or [36, 36, 36, 36]
    m = [float(v) for v in (list(m) + [36, 36, 36, 36])[:4]]
    return m[0], m[1], m[2], m[3]


def all_bands(defn: dict) -> list[tuple[str, int, dict]]:
    """Bands in designer order: (kind, group level or -1, band)."""
    b = defn.setdefault("bands", {})
    out = [("reportHeader", -1, b.setdefault("reportHeader", {"height": 0, "items": []})),
           ("pageHeader", -1, b.setdefault("pageHeader", {"height": 0, "items": []}))]
    groups = defn.get("groups") or []
    for i, g in enumerate(groups):
        out.append(("groupHeader", i, g.setdefault("header", {"height": 24, "items": []})))
    out.append(("detail", -1, b.setdefault("detail", {"height": 20, "items": []})))
    for i in reversed(range(len(groups))):
        out.append(("groupFooter", i, groups[i].setdefault("footer", {"height": 24, "items": []})))
    out.append(("reportFooter", -1, b.setdefault("reportFooter", {"height": 0, "items": []})))
    out.append(("pageFooter", -1, b.setdefault("pageFooter", {"height": 0, "items": []})))
    return out


def band_title(defn: dict, kind: str, level: int) -> str:
    if kind in ("groupHeader", "groupFooter"):
        g = (defn.get("groups") or [{}])[level]
        what = g.get("field") or g.get("expression") or "?"
        return f"{BAND_TITLES[kind]} #{level + 1}: {what}"
    return BAND_TITLES[kind]


def load_definition(path) -> dict:
    with open(path, encoding="utf-8-sig") as f:
        d = json.load(f)
    if not isinstance(d, dict) or "bands" not in d:
        raise ReportError(f"{os.path.basename(str(path))} is not a report file")
    return d


def save_definition(defn: dict, path) -> None:
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(defn, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, str(path))


# ============================================================================== data
def _convert(v):
    """'12' -> 12, '3.5' -> 3.5 (CSV values); everything else unchanged."""
    if not isinstance(v, str):
        return v
    s = v.strip()
    if re.fullmatch(r"[+-]?\d{1,15}", s) and not (len(s) > 1 and s.lstrip("+-").startswith("0")):
        return int(s)
    if re.fullmatch(r"[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?", s):
        try:
            return float(s)
        except ValueError:
            return v
    return v


def _records(data, root: str = ""):
    for part in [p for p in str(root or "").split(".") if p]:
        if isinstance(data, dict):
            data = data.get(part)
        elif isinstance(data, list) and part.isdigit() and int(part) < len(data):
            data = data[int(part)]
        else:
            data = None
    if isinstance(data, dict):
        lists = [v for v in data.values() if isinstance(v, list)]
        data = lists[0] if lists else [data]
    if not isinstance(data, list):
        return []
    return [r if isinstance(r, dict) else {"value": r} for r in data]


def _read_text(path: str) -> str:
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1256", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def _resolve(path: str, base_dir: str) -> str:
    p = os.path.expandvars(os.path.expanduser(str(path or "")))
    if p and not os.path.isabs(p):
        p = os.path.join(base_dir or os.getcwd(), p)
    return p


def _paramstyle_pyformat(sql: str) -> str:
    """:Name -> %(Name)s (pymysql / psycopg), leaving strings and ::casts alone."""
    out, i, n = [], 0, len(sql)
    while i < n:
        ch = sql[i]
        if ch in "'\"":
            j = sql.find(ch, i + 1)
            j = n - 1 if j < 0 else j
            out.append(sql[i:j + 1])
            i = j + 1
            continue
        if ch == "%":
            out.append("%%")
            i += 1
            continue
        if ch == ":" and i + 1 < n and (sql[i + 1].isalpha() or sql[i + 1] == "_") and (i == 0 or sql[i - 1] != ":"):
            m = re.match(r"[A-Za-z_]\w*", sql[i + 1:])
            out.append(f"%({m.group(0)})s")
            i += 1 + len(m.group(0))
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def connect(conn: dict, base_dir: str = "", password: str | None = None):
    """A DB-API connection for a connection description {"kind": "sqlite", "path": ...} /
    {"kind": "mysql"|"postgresql", "host", "port", "user", "database"}."""
    kind = str(conn.get("kind") or "sqlite").lower()
    if kind == "sqlite":
        path = _resolve(conn.get("path") or "", base_dir)
        if not path or not os.path.exists(path):
            raise ReportError(f"SQLite database not found: {path or '(none)'}")
        return sqlite3.connect(path)
    pw = password if password is not None else (conn.get("password") or os.environ.get("RADREPORT_PASSWORD", ""))
    if kind in ("mysql", "mariadb"):
        try:
            import pymysql
        except ImportError:
            raise ReportError("MySQL reports need pymysql (pip install pymysql)") from None
        return pymysql.connect(host=conn.get("host") or "127.0.0.1", port=int(conn.get("port") or 3306),
                               user=conn.get("user") or "", password=pw, database=conn.get("database") or "",
                               charset="utf8mb4")
    if kind in ("postgresql", "postgres", "pg"):
        try:
            import psycopg
        except ImportError:
            raise ReportError("PostgreSQL reports need psycopg (pip install psycopg[binary])") from None
        return psycopg.connect(host=conn.get("host") or "127.0.0.1", port=int(conn.get("port") or 5432),
                               user=conn.get("user") or "", password=pw, dbname=conn.get("database") or "")
    raise ReportError(f"Unknown database kind: {kind}")


def fetch(ds: dict, base_dir: str = "", params: dict | None = None, password: str | None = None,
          limit: int = 0) -> tuple[list[str], list[dict]]:
    """(columns, rows) of a data source."""
    params = dict(params or {})
    t = str(ds.get("type") or "none").lower()
    rows: list[dict] = []
    cols: list[str] = []
    if t == "sql":
        conn_d = ds.get("connection") or {}
        sql = str(ds.get("query") or "").strip().rstrip(";")
        if not sql:
            raise ReportError("The data source has no SQL query")
        db = connect(conn_d, base_dir, password)
        try:
            cur = db.cursor()
            kind = str(conn_d.get("kind") or "sqlite").lower()
            names = set(re.findall(r"(?<!:):([A-Za-z_]\w*)", re.sub(r"'[^']*'", "", sql)))
            if kind == "sqlite":
                cur.execute(sql, {k: params.get(k) for k in names} if names else ())
            else:
                q = _paramstyle_pyformat(sql) if names else sql
                cur.execute(q, {k: params.get(k) for k in names} if names else None)
            cols = [d[0] for d in (cur.description or [])]
            data = cur.fetchmany(limit) if limit else cur.fetchall()
            rows = [dict(zip(cols, r)) for r in data]
        except ReportError:
            raise
        except Exception as e:  # noqa: BLE001 - every driver has its own errors
            raise ReportError(f"SQL error: {e}") from None
        finally:
            try:
                db.close()
            except Exception:  # noqa: BLE001
                pass
    elif t in ("csv", "json", "dataset"):
        path = _resolve(ds.get("file") or "", base_dir)
        if not path or not os.path.exists(path):
            raise ReportError(f"Data file not found: {path or '(none)'}")
        if path.lower().endswith(".csv") or t == "csv":
            text = _read_text(path)
            delim = ds.get("delimiter") or ""
            if not delim:
                try:
                    delim = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
                except csv.Error:
                    delim = ","
            rd = csv.DictReader(io.StringIO(text), delimiter=delim)
            cols = list(rd.fieldnames or [])
            rows = [{k: _convert(v) for k, v in r.items() if k is not None} for r in rd]
        else:
            rows = _records(json.loads(_read_text(path)), ds.get("root") or "")
    elif t == "inline":
        rows = [dict(r) for r in ds.get("rows") or [] if isinstance(r, dict)]
    if not cols:
        seen: dict[str, None] = {}
        for r in rows[:200]:
            for k in r:
                seen.setdefault(str(k), None)
        cols = list(seen)
    if limit:
        rows = rows[:limit]
    return cols, rows


# ============================================================================== formatting
_DOTNET_DATE = [("yyyy", "%Y"), ("yy", "%y"), ("MMMM", "%B"), ("MMM", "%b"), ("MM", "%m"), ("dddd", "%A"),
                ("ddd", "%a"), ("dd", "%d"), ("HH", "%H"), ("hh", "%I"), ("mm", "%M"), ("ss", "%S"), ("tt", "%p")]


def _as_date(v):
    if isinstance(v, (_dt.date, _dt.datetime)):
        return v
    if isinstance(v, str):
        s = v.strip().replace("T", " ")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
            try:
                return _dt.datetime.strptime(s[:19], fmt)
            except ValueError:
                continue
    return None


def _num(v):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        c = _convert(v)
        if isinstance(c, (int, float)):
            return c
    try:
        import decimal
        if isinstance(v, decimal.Decimal):
            return float(v)
    except ImportError:
        pass
    return None


def format_value(v, fmt: str = "", currency: str = "") -> str:
    """Value -> text. fmt: Python spec (",.2f"), VB codes (N2, F1, C2, P0, D5, X), .NET patterns
    ("#,##0.00", "0.0", "yyyy-MM-dd") or strftime ("%d/%m/%Y")."""
    if v is None:
        return ""
    fmt = str(fmt or "")
    if not fmt:
        if isinstance(v, float):
            return f"{v:.10g}" if abs(v) < 1e15 else str(v)
        if isinstance(v, bytes):
            return f"<{len(v)} bytes>"
        if isinstance(v, bool):
            return "True" if v else "False"
        try:
            import decimal
            if isinstance(v, decimal.Decimal):
                return str(v)
        except ImportError:
            pass
        return str(v)
    try:
        m = re.fullmatch(r"([NnFfCcPpDdXxEe])(\d*)", fmt)
        if m:
            code, digits = m.group(1).upper(), m.group(2)
            n = _num(v)
            if n is None:
                return str(v)
            d = int(digits) if digits else (2 if code in "NFCP" else 0)
            if code == "N":
                return f"{n:,.{d}f}"
            if code == "F":
                return f"{n:.{d}f}"
            if code == "C":
                return f"{currency}{n:,.{d}f}" if currency else f"{n:,.{d}f}"
            if code == "P":
                return f"{n * 100:.{d}f}%"
            if code == "D":
                return f"{int(n):0{d}d}"
            if code == "X":
                return f"{int(n):X}"
            if code == "E":
                return f"{n:.{d}E}"
        if "%" in fmt and not re.fullmatch(r"[,.\d]*%", fmt):
            d = _as_date(v)
            return d.strftime(fmt) if d else str(v)
        if re.search(r"yy|MM|dd|HH|mm|ss", fmt):
            d = _as_date(v)
            if d is None:
                return str(v)
            out = fmt
            for a, b in _DOTNET_DATE:
                out = out.replace(a, "\0" + b[1] + "\0")
            out = re.sub("\0(.)\0", lambda mm: "%" + mm.group(1), out)
            return d.strftime(out)
        if re.fullmatch(r"[#0,]*\.?[#0]*%?", fmt) and ("0" in fmt or "#" in fmt):
            n = _num(v)
            if n is None:
                return str(v)
            pct = fmt.endswith("%")
            if pct:
                n, fmt = n * 100, fmt[:-1]
            dec = len(fmt.split(".", 1)[1]) if "." in fmt else 0
            s = f"{n:{',' if ',' in fmt else ''}.{dec}f}"
            return s + ("%" if pct else "")
        n = _num(v)
        return format(n if n is not None and re.search(r"[dfeEgGn%,xXob]$", fmt) else v, fmt)
    except (ValueError, TypeError):
        return str(v)


# ============================================================================== expressions
class _Obj:
    """Attribute and item access to a dict (case-insensitive): Fields.Amount, Fields["Unit Price"]."""
    __slots__ = ("_d",)

    def __init__(self, d):
        object.__setattr__(self, "_d", d if d is not None else {})

    def _get(self, k):
        d = self._d
        if k in d:
            return d[k]
        lk = str(k).lower()
        for kk, vv in d.items():
            if str(kk).lower() == lk:
                return vv
        raise KeyError(k)

    def __getattr__(self, k):
        try:
            return self._get(k)
        except KeyError:
            raise AttributeError(k) from None

    def __getitem__(self, k):
        return self._get(k)

    def get(self, k, default=None):
        try:
            return self._get(k)
        except KeyError:
            return default

    def __contains__(self, k):
        try:
            self._get(k)
            return True
        except KeyError:
            return False


def _now():
    return _dt.datetime.now()      # a Python frame: C code that imports sees the real builtins


def _today():
    return _dt.date.today()


def _iif(c, a, b=None):
    return a if c else b


def _safe_sum(values):
    total = 0
    for v in values:
        n = _num(v)
        if n is not None:
            total += n
    return total


SAFE_BUILTINS = {"abs": abs, "round": round, "min": min, "max": max, "len": len, "str": str, "int": int,
                 "float": float, "bool": bool, "sum": sum, "sorted": sorted, "any": any, "all": all, "range": range,
                 "list": list, "dict": dict, "tuple": tuple, "enumerate": enumerate, "zip": zip, "True": True,
                 "False": False, "None": None, "isinstance": isinstance}

_CODE_CACHE: dict[str, object] = {}


class Context:
    """Everything an expression can see while a band is printed."""

    def __init__(self, report: "Report", rows, row, page=1, total_pages=0, row_number=0, running=None, extra=None):
        self.report = report
        self.rows = rows or []
        self.row = row
        self.page = page
        self.total_pages = total_pages
        self.row_number = row_number
        self.running = running or {}
        self.extra = extra or {}

    # ------------------------------------------------------------ aggregates
    def _values(self, expr, rows):
        if expr is None or expr == "":
            return [1 for _ in rows]
        if callable(expr):
            return [expr(_Obj(r)) for r in rows]
        e = str(expr)
        if rows and e in rows[0]:
            return [r.get(e) for r in rows]
        return [self.report.evaluate(e, self.child(r)) for r in rows]

    def _scope_rows(self, scope):
        if scope is None:
            return self.rows
        s = str(scope)
        if s.lower() == "report":
            return self.report._rows
        if s.lower() == "page":
            return self.extra.get("page_rows", self.rows)
        g = self.extra.get("group_rows", {})
        return g.get(s, g.get(s.lower(), self.rows))

    def child(self, row):
        return Context(self.report, self.rows, row, self.page, self.total_pages, self.row_number, self.running,
                       self.extra)

    def namespace(self):
        rpt = self.report
        values = self._values
        scope_rows = self._scope_rows

        def agg(fn):
            def f(expr=None, scope=None):
                vals = [v for v in values(expr, scope_rows(scope)) if v is not None]
                return fn(vals)
            return f

        def _avg(vals):
            nums = [n for n in (_num(v) for v in vals) if n is not None]
            return sum(nums) / len(nums) if nums else 0

        def _min(vals):
            try:
                return min(vals) if vals else None
            except TypeError:
                return min(str(v) for v in vals)

        def _max(vals):
            try:
                return max(vals) if vals else None
            except TypeError:
                return max(str(v) for v in vals)

        def running(kind):
            def f(expr=None, reset="group"):
                rows = self.running.get(str(reset).lower(), self.running.get("report", self.rows))
                vals = [v for v in values(expr, rows) if v is not None]
                return len(vals) if kind == "count" else _safe_sum(vals)
            return f

        ns = dict(SAFE_BUILTINS)
        ns.update(
            Fields=_Obj(self.row or {}), Parameters=_Obj(rpt.Parameters), Params=_Obj(rpt.Parameters),
            Sum=agg(_safe_sum), Count=agg(len), Avg=agg(_avg), Average=agg(_avg), Min=agg(_min), Max=agg(_max),
            First=agg(lambda v: v[0] if v else None), Last=agg(lambda v: v[-1] if v else None),
            CountDistinct=agg(lambda v: len({repr(x) for x in v})),
            RunningSum=running("sum"), RunningCount=running("count"), RunningTotal=running("sum"),
            PageNumber=self.page, Page=self.page, TotalPages=self.total_pages, PageCount=self.total_pages,
            RowNumber=self.row_number, RecordCount=len(rpt._rows), Continued=bool(self.extra.get("continued")),
            ReportName=rpt.definition.get("name", ""), ReportTitle=rpt.definition.get("title", ""),
            Now=_now, Today=_today, IIf=_iif, Format=format_value,
            Upper=lambda s: str(s or "").upper(), Lower=lambda s: str(s or "").lower(),
            Trim=lambda s: str(s or "").strip(), Len=lambda s: len(str(s or "")),
            Left=lambda s, n: str(s or "")[:int(n)], Right=lambda s, n: str(s or "")[-int(n):] if int(n) else "",
            Year=lambda d: (_as_date(d) or _dt.date.min).year, Month=lambda d: (_as_date(d) or _dt.date.min).month,
            Day=lambda d: (_as_date(d) or _dt.date.min).day, CDate=_as_date, Val=lambda s: _num(s) or 0,
            IsNull=lambda v, alt=None: alt if v is None else v, Math=math,
        )
        return ns


class _Locals(dict):
    """Expression locals: names not in the namespace are fields of the current row, then parameters."""

    def __init__(self, ns, ctx):
        super().__init__(ns)
        self.ctx = ctx

    def __missing__(self, key):
        row = self.ctx.row or {}
        if key in row:
            return row[key]
        lk = key.lower()
        for k, v in row.items():
            if str(k).lower() == lk:
                return v
        for k, v in self.ctx.report.Parameters.items():
            if str(k).lower() == lk:
                return v
        raise NameError(f"name '{key}' is not a field, parameter or function")


def split_format(body: str) -> tuple[str, str]:
    """'Sum("A"):N2' -> ('Sum("A")', 'N2'): the first top-level ':' followed by a format spec."""
    depth, quote = 0, ""
    for i, ch in enumerate(body):
        if quote:
            if ch == quote:
                quote = ""
            continue
        if ch in "'\"":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == ":" and depth == 0 and i > 0 and _SPEC.match(body[i + 1:].strip()):
            return body[:i], body[i + 1:].strip()
    return body, ""


_PLACEHOLDER = re.compile(r"\{\{|\}\}|\{([^{}]+)\}")
_SPEC = re.compile(r"^(?:[<>^=]?[+\- ]?#?0?\d*[,_]?(?:\.\d+)?[bcdeEfFgGnosxX%]?|[NnFfCcPpDdXxEe]\d*|[#0,.]+%?"
                   r"|[yMdHhmst/\-.: ]+|%.*)$")


# ============================================================================== report
class Report:
    """A report definition + its data. Report(path_or_dict, base_dir=None)."""

    def __init__(self, source=None, base_dir: str | None = None):
        self.path = ""
        if isinstance(source, dict):
            self.definition = source
        elif source:
            self.path = os.path.abspath(str(source))
            self.definition = load_definition(self.path)
        else:
            self.definition = new_report()
        self.base_dir = base_dir or (os.path.dirname(self.path) if self.path else os.getcwd())
        self.Parameters: dict = {}
        for p in self.definition.get("parameters") or []:
            if p.get("name"):
                self.Parameters[p["name"]] = _convert(p.get("default")) if p.get("default") not in (None, "") \
                    else None
        self.Password: str | None = None
        self._data: list[dict] | None = None
        self._rows: list[dict] = []
        self.columns: list[str] = []
        self.pages: list[dict] = []
        self.log: list[dict] = []
        self.errors: list[str] = []
        self._built = False

    # ------------------------------------------------------------ VB-style API
    @property
    def PageCount(self) -> int:
        self._ensure()
        return len(self.pages)

    @property
    def Rows(self) -> list[dict]:
        self._ensure()
        return self._rows

    def SetData(self, rows, columns=None) -> None:
        """Use these rows (list of dicts, or list of lists/tuples with columns) instead of the data source."""
        rows = list(rows or [])
        if rows and not isinstance(rows[0], dict):
            cols = list(columns or [f"Column{i + 1}" for i in range(len(rows[0]))])
            rows = [dict(zip(cols, r)) for r in rows]
        self._data = [dict(r) for r in rows]
        self._built = False

    def Refresh(self) -> list[dict]:
        self._built = False
        return self.Run()

    def Run(self) -> list[dict]:
        self._load_rows()
        self.pages, self.log = self._layout(0)
        total = len(self.pages)
        self.pages, self.log = self._layout(total)
        self._built = True
        return self.pages

    def _ensure(self):
        if not self._built:
            self.Run()

    def ExportPdf(self, path: str) -> str:
        self._ensure()
        return export_pdf(self, path)

    def ExportHtml(self, path: str) -> str:
        self._ensure()
        return export_html(self, path)

    def ExportCsv(self, path: str) -> str:
        self._ensure()
        return export_csv(self, path)

    def ExportExcel(self, path: str) -> str:
        self._ensure()
        return export_excel(self, path)

    def Export(self, path: str) -> str:
        ext = os.path.splitext(str(path))[1].lower()
        fn = {".pdf": self.ExportPdf, ".html": self.ExportHtml, ".htm": self.ExportHtml, ".csv": self.ExportCsv,
              ".xlsx": self.ExportExcel}.get(ext)
        if fn is None:
            raise ReportError(f"Unknown export format: {ext or path}")
        return fn(path)

    def Print(self, show_dialog: bool = True, parent=None) -> bool:
        self._ensure()
        return print_report(self, show_dialog, parent)

    def RenderPage(self, index: int, zoom: float = 1.0):
        """A QImage of one page (zoom 1 = 96 dpi)."""
        self._ensure()
        return render_image(self, index, zoom)

    # ------------------------------------------------------------ data
    def _load_rows(self) -> None:
        d = self.definition
        if self._data is not None:
            rows = [dict(r) for r in self._data]
            cols = list(rows[0]) if rows else []
        else:
            cols, rows = fetch(d.get("dataSource") or {}, self.base_dir, self.Parameters, self.Password)
        self.columns = cols
        flt = str(d.get("filter") or "").strip()
        self._rows = rows
        if flt:
            rows = [r for r in rows if self.evaluate(flt, Context(self, rows, r))]
        keys = []
        if d.get("sortByGroups", True):
            for g in d.get("groups") or []:
                if g.get("field") or g.get("expression"):
                    keys.append((g, g.get("sort", "asc") == "desc"))
        sorts = [(s, bool(s.get("desc"))) for s in d.get("sort") or [] if s.get("field")]

        def keyval(r, spec):
            v = self._group_key(spec, r) if "header" in spec else r.get(spec.get("field"))
            return (v is None, v if isinstance(v, (int, float)) else str(v if v is not None else ""))

        for spec, desc in reversed(keys + sorts):       # stable: last key first
            try:
                rows = sorted(rows, key=lambda r, s=spec: keyval(r, s), reverse=desc)
            except TypeError:
                rows = sorted(rows, key=lambda r, s=spec: str(keyval(r, s)), reverse=desc)
        self._rows = rows

    def _group_key(self, g, row):
        if g.get("expression"):
            return self.evaluate(g["expression"], Context(self, self._rows, row))
        f = g.get("field") or ""
        if f in row:
            return row[f]
        lf = f.lower()
        for k, v in row.items():
            if str(k).lower() == lf:
                return v
        return None

    # ------------------------------------------------------------ expressions
    def evaluate(self, expr: str, ctx: Context):
        expr = str(expr or "").strip()
        if expr.startswith("="):
            expr = expr[1:].strip()
        if not expr:
            return None
        code = _CODE_CACHE.get(expr)
        if code is None:
            try:
                code = compile(expr, "<expression>", "eval")
            except SyntaxError as e:
                raise ReportError(f"Syntax error in expression {expr!r}: {e.msg}") from None
            _CODE_CACHE[expr] = code
        ns = ctx.namespace()
        return eval(code, {"__builtins__": SAFE_BUILTINS}, _Locals(ns, ctx))  # noqa: S307 - report expressions

    def _safe_eval(self, expr, ctx):
        try:
            return self.evaluate(expr, ctx)
        except Exception as e:  # noqa: BLE001 - shown in the report, never a crash
            msg = f"#Error: {e}"
            if msg not in self.errors:
                self.errors.append(msg)
            return msg

    def expand(self, text: str, ctx: Context) -> str:
        """'Page {PageNumber} of {TotalPages}' / 'Total: {Sum("Amount"):N2}'."""
        text = str(text or "")
        if "{" not in text and "}" not in text:
            return text

        def rep(m):
            tok = m.group(0)
            if tok == "{{":
                return "{"
            if tok == "}}":
                return "}"
            body = m.group(1)
            fmt = ""
            body, fmt = split_format(body)
            return format_value(self._safe_eval(body, ctx), fmt, self.definition.get("currency", ""))
        return _PLACEHOLDER.sub(rep, text)

    def item_value(self, it: dict, ctx: Context):
        """(raw value, text) of an item in a context."""
        t = it.get("type")
        cur = self.definition.get("currency", "")
        if t == "field":
            f = it.get("field") or ""
            row = ctx.row or {}
            v = row.get(f)
            if v is None and f not in row:
                lf = f.lower()
                v = next((vv for k, vv in row.items() if str(k).lower() == lf), None)
            return v, format_value(v, it.get("format", ""), cur)
        if t == "expression":
            v = self._safe_eval(it.get("expression") or "", ctx)
            return v, format_value(v, it.get("format", ""), cur)
        if t == "text":
            s = self.expand(it.get("text", ""), ctx)
            return s, s
        return None, ""

    # ------------------------------------------------------------ layout
    def _layout(self, total_pages: int):
        return _Layout(self, total_pages).run()


class _Layout:
    def __init__(self, rpt: Report, total_pages: int):
        self.r = rpt
        self.d = rpt.definition
        self.total = total_pages
        self.pw, self.ph = page_size(self.d)
        self.ml, self.mt, self.mr, self.mb = margins(self.d)
        self.cw = self.pw - self.ml - self.mr
        b = self.d.get("bands") or {}
        self.bands = b
        self.groups = [g for g in (self.d.get("groups") or []) if g.get("field") or g.get("expression")]
        self.pf_h = self._h(b.get("pageFooter"))
        self.bottom = self.ph - self.mb - self.pf_h
        self.pages: list[dict] = []
        self.log: list[dict] = []
        self.page = None
        self.y = 0.0
        self.page_rows: list[dict] = []
        self.last_row = None
        self.open_groups: list[tuple[dict, list[dict], int]] = []   # (group, rows, level) currently open
        self.group_rows: dict = {}
        self.body_on_page = False
        self.rtl = bool(self.d.get("rightToLeft"))
        self.mirror = bool(self.d.get("mirrorLayout"))
        f = self.d.get("font") or {}
        self.def_font = (f.get("name") or "Segoe UI", float(f.get("size") or 10))

    @staticmethod
    def _h(band) -> float:
        if not band or band.get("visible", True) is False:
            return 0.0
        return max(0.0, float(band.get("height") or 0))

    # ------------------------------------------------------------ pages
    def new_page(self, continued=False, header=True):
        if self.page is not None:
            self.finish_page()
        self.page = {"number": len(self.pages) + 1, "ops": [], "width": self.pw, "height": self.ph}
        self.pages.append(self.page)
        self.y = self.mt
        self.page_rows = []
        self.body_on_page = False
        if header:
            self.page_header()
        if continued:
            for g, rows, level in self.open_groups:
                if g.get("repeatHeader") and self._h(g.get("header")):
                    c = self.ctx(rows, rows[0] if rows else None, continued=True)
                    self.emit(g["header"], "groupHeader", level, c, log=False, check=False)

    def page_header(self):
        ph = self.bands.get("pageHeader")
        if ph and self._h(ph) and not (self.page["number"] == 1 and ph.get("skipFirstPage")):
            self.emit(ph, "pageHeader", -1, self.ctx(self.page_rows, self.last_row), log=False, check=False)

    def finish_page(self):
        pf = self.bands.get("pageFooter")
        if pf and self.pf_h and not (self.page["number"] == 1 and pf.get("skipFirstPage")):
            keep = self.y
            self.y = self.ph - self.mb - self.pf_h
            self.emit(pf, "pageFooter", -1, self.ctx(self.page_rows, self.last_row), log=False, check=False)
            self.y = keep

    def ctx(self, rows, row, row_number=0, running=None, continued=False):
        extra = {"page_rows": self.page_rows, "group_rows": self.group_rows, "continued": continued}
        return Context(self.r, rows, row, self.page["number"] if self.page else 1, self.total, row_number,
                       running, extra)

    def fits(self, h):
        return self.y + h <= self.bottom + 0.01

    # ------------------------------------------------------------ bands
    def emit(self, band, kind, level, ctx, log=True, check=True, alt=False):
        if not band or band.get("visible", True) is False:
            return
        vis = str(band.get("visibleIf") or "").strip()
        if vis and not self.r._safe_eval(vis, ctx):
            return
        h = self._h(band)
        if h <= 0:
            return
        if check and not self.fits(h) and self.body_on_page:
            self.new_page(continued=True)
            ctx.page = self.page["number"]
        ops = self.page["ops"]
        y0 = self.y
        if band.get("back"):
            ops.append({"op": "rect", "x": self.ml, "y": y0, "w": self.cw, "h": h, "fill": band["back"], "bw": 0})
        if alt and self.bands.get("detail", {}).get("alternateColor"):
            ops.append({"op": "rect", "x": self.ml, "y": y0, "w": self.cw, "h": h,
                        "fill": self.bands["detail"]["alternateColor"], "bw": 0})
        entry = {"band": kind, "level": level, "cells": []} if log else None
        for it in band.get("items") or []:
            self.item_ops(it, ctx, y0, ops, entry)
        if entry is not None:
            self.log.append(entry)
        self.y = y0 + h
        if kind not in ("pageHeader", "pageFooter"):
            self.body_on_page = True

    def item_ops(self, it, ctx, y0, ops, entry):
        r = self.r
        vis = str(it.get("visibleIf") or "").strip()
        if vis and not r._safe_eval(vis, ctx):
            return
        x, y = float(it.get("x", 0)), float(it.get("y", 0))
        w, h = float(it.get("w", 80)), float(it.get("h", 18))
        if self.mirror:
            x = self.cw - x - w
        ax, ay = self.ml + x, y0 + y
        t = it.get("type")
        if t in ("text", "field", "expression"):
            raw, text = r.item_value(it, ctx)
            if it.get("hideZero") and _num(raw) == 0:
                text = ""
            rtl = it.get("rtl")
            if rtl in (None, "", "auto"):
                rtl = None if not self.rtl else True
            align = it.get("align") or ("right" if (self.rtl and rtl is not False) else "left")
            ops.append({"op": "text", "x": ax, "y": ay, "w": w, "h": h, "text": text,
                        "font": it.get("fontName") or self.def_font[0],
                        "size": float(it.get("fontSize") or self.def_font[1]), "bold": bool(it.get("bold")),
                        "italic": bool(it.get("italic")), "underline": bool(it.get("underline")),
                        "color": it.get("color") or "#000000", "back": it.get("back") or "",
                        "align": align, "valign": it.get("valign") or "middle", "rtl": rtl,
                        "wrap": bool(it.get("wrap", False)), "bw": float(it.get("border") or 0),
                        "bc": it.get("borderColor") or "#000000", "pad": float(it.get("padding", 2))})
            if entry is not None:
                entry["cells"].append({"x": x, "w": w, "y": y, "h": h, "value": raw, "text": text, "type": t,
                                       "name": it.get("name", ""), "field": it.get("field", ""),
                                       "bold": bool(it.get("bold")), "format": it.get("format", "")})
        elif t == "line":
            lw = float(it.get("lineWidth") or 1)
            col = it.get("lineColor") or it.get("color") or "#000000"
            if it.get("diagonal"):
                x1, y1, x2, y2 = ax, ay, ax + w, ay + h
            elif w >= h:
                x1, y1, x2, y2 = ax, ay + h / 2, ax + w, ay + h / 2
            else:
                x1, y1, x2, y2 = ax + w / 2, ay, ax + w / 2, ay + h
            ops.append({"op": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "lw": lw, "color": col,
                        "style": it.get("lineStyle") or "solid"})
        elif t == "box":
            ops.append({"op": "rect", "x": ax, "y": ay, "w": w, "h": h, "fill": it.get("fill") or "",
                        "bw": float(it.get("lineWidth", 1) or 0), "bc": it.get("lineColor") or "#000000",
                        "radius": float(it.get("radius") or 0)})
        elif t == "image":
            src = None
            if it.get("imageField"):
                v = (ctx.row or {}).get(it["imageField"])
                if isinstance(v, (bytes, bytearray, memoryview)):
                    src = {"data": base64.b64encode(bytes(v)).decode("ascii")}
                elif v:
                    src = {"path": _resolve(str(v), r.base_dir)}
            elif it.get("image"):
                src = {"path": _resolve(it["image"], r.base_dir)}
            ops.append({"op": "image", "x": ax, "y": ay, "w": w, "h": h, "keep": it.get("keepAspect", True),
                        **(src or {})})
        elif t == "barcode":
            value = r.expand(it.get("text", ""), ctx) if it.get("text") else ""
            if it.get("field"):
                value = format_value((ctx.row or {}).get(it["field"]))
            ops.append({"op": "barcode", "x": ax, "y": ay, "w": w, "h": h, "kind": it.get("barcodeType") or "code128",
                        "value": value, "showText": bool(it.get("showText", True)),
                        "color": it.get("color") or "#000000"})
        elif t == "chart":
            labels, values = chart_data(r, it, ctx)
            ops.append({"op": "chart", "x": ax, "y": ay, "w": w, "h": h, "kind": it.get("chartType") or "bar",
                        "labels": labels, "values": values, "title": r.expand(it.get("title", ""), ctx),
                        "font": it.get("fontName") or self.def_font[0], "size": float(it.get("fontSize") or 8),
                        "showValues": bool(it.get("showValues", True)), "color": it.get("color") or ""})

    # ------------------------------------------------------------ run
    def run(self):
        rows = self.r._rows
        b = self.bands
        rh = b.get("reportHeader")
        has_rh = bool(rh and self._h(rh))
        self.new_page(header=not has_rh)          # page 1: the report header comes first, then the page header
        all_ctx = self.ctx(rows, rows[0] if rows else None)
        self.group_rows = {}
        if has_rh:
            self.emit(rh, "reportHeader", -1, all_ctx)
            if rh.get("newPageAfter"):
                self.new_page()
            else:
                self.page_header()
        groups = self.groups
        n = len(rows)
        # pre-compute group runs: for each level the list of (start, end) slices
        keys = [[self.r._group_key(g, row) for g in groups] for row in rows]
        detail = b.get("detail")
        running_report: list[dict] = []
        group_runs: list[list[dict]] = [[] for _ in groups]
        i = 0
        first_group_done = [False] * len(groups)
        row_in_group = 0
        while i < n:
            # which levels start here?
            start_level = None
            for lv in range(len(groups)):
                if i == 0 or keys[i][:lv + 1] != keys[i - 1][:lv + 1]:
                    start_level = lv
                    break
            if start_level is not None:
                for lv in range(start_level, len(groups)):
                    j = i
                    while j < n and keys[j][:lv + 1] == keys[i][:lv + 1]:
                        j += 1
                    grows = rows[i:j]
                    g = groups[lv]
                    self.group_rows[g.get("name") or f"Group{lv + 1}"] = grows
                    self.group_rows[(g.get("name") or f"Group{lv + 1}").lower()] = grows
                    self.open_groups = [og for og in self.open_groups if og[2] < lv] + [(g, grows, lv)]
                    group_runs[lv] = []
                    if g.get("newPage") and first_group_done[lv] and self.body_on_page:
                        self.new_page()
                    elif g.get("keepTogether"):
                        need = self._h(g.get("header")) + len(grows) * self._h(detail) + self._h(g.get("footer"))
                        if not self.fits(need) and need <= self.bottom - self.mt and self.body_on_page:
                            self.new_page()
                    first_group_done[lv] = True
                    gh = g.get("header")
                    if gh and self._h(gh):
                        self.emit(gh, "groupHeader", lv, self.ctx(grows, grows[0]))
                    row_in_group = 0
            row = rows[i]
            row_in_group += 1
            running_report.append(row)
            for lv in range(len(groups)):
                group_runs[lv].append(row)
            running = {"report": list(running_report), "page": self.page_rows + [row],
                       "group": list(group_runs[-1]) if groups else list(running_report)}
            for lv, g in enumerate(groups):
                running[(g.get("name") or f"Group{lv + 1}").lower()] = list(group_runs[lv])
            scope = self.open_groups[-1][1] if self.open_groups else rows
            if detail and self._h(detail):
                if not self.fits(self._h(detail)) and self.body_on_page:
                    self.new_page(continued=True)
                    running["page"] = [row]
                c = self.ctx(scope, row, row_in_group, running)
                self.emit(detail, "detail", -1, c, alt=(row_in_group % 2 == 0))
            self.page_rows.append(row)
            self.last_row = row
            # which levels end here?
            for lv in reversed(range(len(groups))):
                if i == n - 1 or keys[i + 1][:lv + 1] != keys[i][:lv + 1]:
                    g = groups[lv]
                    og = next((o for o in self.open_groups if o[2] == lv), None)
                    grows = og[1] if og else [row]
                    gf = g.get("footer")
                    if gf and self._h(gf):
                        run = {"report": list(running_report), "page": list(self.page_rows),
                               "group": list(grows)}
                        self.emit(gf, "groupFooter", lv, self.ctx(grows, grows[-1], running=run))
                    self.open_groups = [o for o in self.open_groups if o[2] < lv]
            i += 1
        rf = b.get("reportFooter")
        if rf and self._h(rf):
            self.emit(rf, "reportFooter", -1, self.ctx(rows, rows[-1] if rows else None,
                                                      running={"report": rows, "page": self.page_rows,
                                                               "group": rows}))
        self.finish_page()
        return self.pages, self.log


def chart_data(r: Report, it: dict, ctx: Context):
    """(labels, values) for a chart item: rows of the band's scope grouped by the category field."""
    cat = it.get("category") or ""
    val = it.get("valueField") or ""
    how = str(it.get("aggregate") or "sum").lower()
    rows = ctx.rows if it.get("scope", "band") == "band" else r._rows
    order: list = []
    buckets: dict = {}
    for row in rows:
        c = ctx.child(row)
        key = r._safe_eval(cat, c) if cat and cat not in row else row.get(cat, "")
        v = None
        if val:
            v = row.get(val) if val in row else r._safe_eval(val, c)
        k = format_value(key)
        if k not in buckets:
            buckets[k] = []
            order.append(k)
        buckets[k].append(v)
    values = []
    for k in order:
        vs = [_num(v) for v in buckets[k]]
        nums = [x for x in vs if x is not None]
        if how == "count" or not val:
            values.append(len(vs))
        elif how in ("avg", "average"):
            values.append(sum(nums) / len(nums) if nums else 0)
        elif how == "min":
            values.append(min(nums) if nums else 0)
        elif how == "max":
            values.append(max(nums) if nums else 0)
        else:
            values.append(sum(nums))
    return order, values


# ============================================================================== Qt (optional)
_QT = None


def qt():
    """SimpleNamespace(name, QtCore, QtGui, QtWidgets, QtPrintSupport) of PySide6 / PyQt6, or None."""
    global _QT
    if _QT is not None:
        return _QT or None
    loaded = [n for n in ("PyQt6", "PySide6") if n + ".QtCore" in sys.modules]
    running = [n for n in loaded if sys.modules[n + ".QtCore"].QCoreApplication.instance() is not None]
    order = ([os.environ["RADREPORT_QT"]] if os.environ.get("RADREPORT_QT") else []) + running + loaded +         ["PySide6", "PyQt6"]
    for name in dict.fromkeys(order):
        try:
            core = importlib.import_module(name + ".QtCore")
            gui = importlib.import_module(name + ".QtGui")
        except ImportError:
            continue
        ns = SimpleNamespace(name=name, QtCore=core, QtGui=gui, QtWidgets=None, QtPrintSupport=None)
        try:
            ns.QtWidgets = importlib.import_module(name + ".QtWidgets")
        except ImportError:
            pass
        try:
            ns.QtPrintSupport = importlib.import_module(name + ".QtPrintSupport")
        except ImportError:
            pass
        ns.Signal = getattr(core, "Signal", None) or getattr(core, "pyqtSignal")
        _QT = ns
        return ns
    _QT = False
    return None


def _need_qt():
    q = qt()
    if q is None:
        raise ReportError("Drawing reports needs Qt: pip install PySide6 (or PyQt6)")
    return q


def ensure_app(widgets: bool = False):
    """A Q(Gui)Application must exist to draw text; create one when the program has none (Tkinter...)."""
    q = _need_qt()
    app = q.QtCore.QCoreApplication.instance()
    if app is None:
        if os.name == "nt" and not os.environ.get("QT_QPA_FONTDIR"):      # offscreen / minimal platforms
            os.environ["QT_QPA_FONTDIR"] = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        if (widgets or q.QtWidgets is not None) and q.QtWidgets is not None:
            app = q.QtWidgets.QApplication(["radreport"])
        else:
            app = q.QtGui.QGuiApplication(["radreport"])
    return app


def _flags(*vals) -> int:
    out = 0
    for v in vals:
        out |= int(getattr(v, "value", v))
    return out


def _color(q, s, default="#000000"):
    c = q.QtGui.QColor(s or default)
    return c if c.isValid() else q.QtGui.QColor(default)


def _font(q, op, painter):
    f = q.QtGui.QFont(op.get("font") or "Segoe UI")
    dpi = painter.device().logicalDpiY() or 96
    f.setPointSizeF(max(1.0, float(op.get("size") or 10)) * 72.0 / dpi)
    f.setBold(bool(op.get("bold")))
    f.setItalic(bool(op.get("italic")))
    f.setUnderline(bool(op.get("underline")))
    f.setHintingPreference(q.QtGui.QFont.HintingPreference.PreferNoHinting)   # same layout at every zoom
    return f


def is_rtl_text(s: str) -> bool:
    """True when the first strong character is right-to-left (Arabic, Hebrew...)."""
    for ch in str(s or ""):
        bd = unicodedata.bidirectional(ch)
        if bd in ("R", "AL"):
            return True
        if bd == "L":
            return False
    return False


def paint_page(painter, page: dict, scale: float = 1.0) -> None:
    """Draw a page (points) with *painter*; scale = device units per point."""
    q = _need_qt()
    painter.save()
    painter.scale(scale, scale)
    painter.setRenderHint(q.QtGui.QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(q.QtGui.QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(q.QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
    for op in page.get("ops") or []:
        try:
            paint_op(painter, op)
        except Exception as e:  # noqa: BLE001 - one bad item must not stop the page
            print(f"radreport: cannot draw {op.get('op')}: {e}", file=sys.stderr)
    painter.restore()


def paint_op(painter, op: dict) -> None:
    q = _need_qt()
    G, C = q.QtGui, q.QtCore
    Qt = C.Qt
    kind = op.get("op")
    if kind == "text":
        rect = C.QRectF(op["x"], op["y"], op["w"], op["h"])
        if op.get("back"):
            painter.fillRect(rect, _color(q, op["back"]))
        if op.get("bw"):
            pen = G.QPen(_color(q, op.get("bc")))
            pen.setWidthF(op["bw"])
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
        text = op.get("text") or ""
        if not text:
            return
        pad = float(op.get("pad", 2))
        inner = rect.adjusted(pad, 0, -pad, 0)
        painter.setFont(_font(q, op, painter))
        painter.setPen(_color(q, op.get("color")))
        rtl = op.get("rtl")
        if rtl is None:
            direction = Qt.LayoutDirection.RightToLeft if is_rtl_text(text) else Qt.LayoutDirection.LeftToRight
        else:
            direction = Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight
        painter.setLayoutDirection(direction)
        h = {"left": Qt.AlignmentFlag.AlignLeft, "center": Qt.AlignmentFlag.AlignHCenter,
             "right": Qt.AlignmentFlag.AlignRight, "justify": Qt.AlignmentFlag.AlignJustify}.get(
            op.get("align") or "left", Qt.AlignmentFlag.AlignLeft)
        v = {"top": Qt.AlignmentFlag.AlignTop, "bottom": Qt.AlignmentFlag.AlignBottom}.get(
            op.get("valign") or "middle", Qt.AlignmentFlag.AlignVCenter)
        flags = [h, v, Qt.AlignmentFlag.AlignAbsolute]
        if op.get("wrap"):
            flags.append(Qt.TextFlag.TextWordWrap)
        painter.save()
        painter.setClipRect(rect)
        painter.drawText(inner, _flags(*flags), text)
        painter.restore()
    elif kind == "line":
        pen = G.QPen(_color(q, op.get("color")))
        pen.setWidthF(float(op.get("lw") or 1))
        pen.setStyle({"dash": Qt.PenStyle.DashLine, "dot": Qt.PenStyle.DotLine}.get(op.get("style"),
                                                                                    Qt.PenStyle.SolidLine))
        painter.setPen(pen)
        painter.drawLine(C.QPointF(op["x1"], op["y1"]), C.QPointF(op["x2"], op["y2"]))
    elif kind == "rect":
        rect = C.QRectF(op["x"], op["y"], op["w"], op["h"])
        if op.get("bw"):
            pen = G.QPen(_color(q, op.get("bc")))
            pen.setWidthF(float(op["bw"]))
            painter.setPen(pen)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_color(q, op["fill"]) if op.get("fill") else Qt.BrushStyle.NoBrush)
        r = float(op.get("radius") or 0)
        if r:
            painter.drawRoundedRect(rect, r, r)
        else:
            painter.drawRect(rect)
    elif kind == "image":
        rect = C.QRectF(op["x"], op["y"], op["w"], op["h"])
        img = G.QImage()
        if op.get("data"):
            img.loadFromData(base64.b64decode(op["data"]))
        elif op.get("path") and os.path.exists(op["path"]):
            img.load(op["path"])
        if img.isNull():
            pen = G.QPen(G.QColor("#B0B0B0"))
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            return
        if op.get("keep", True):
            sw, sh = img.width(), img.height()
            k = min(rect.width() / sw, rect.height() / sh)
            w, h = sw * k, sh * k
            rect = C.QRectF(rect.x() + (rect.width() - w) / 2, rect.y() + (rect.height() - h) / 2, w, h)
        painter.drawImage(rect, img)
    elif kind == "barcode":
        _paint_barcode(painter, op)
    elif kind == "chart":
        _paint_chart(painter, op)


def barcode_modules(kind: str, value: str):
    """('bars', '1011...') for linear codes, ('matrix', [[bool]]) for QR, or (None, error)."""
    kind = (kind or "code128").lower()
    if not value:
        return None, "no value"
    if kind == "qr":
        try:
            import qrcode
        except ImportError:
            return None, "QR codes need: pip install qrcode"
        qr_ = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr_.add_data(value)
        qr_.make(fit=True)
        return "matrix", qr_.get_matrix()
    try:
        import barcode
    except ImportError:
        return None, "barcodes need: pip install python-barcode"
    try:
        cls = barcode.get_barcode_class(kind)
        code = cls(value, writer=None)
        return "bars", "".join(code.build())
    except Exception as e:  # noqa: BLE001 - invalid value for that symbology
        return None, str(e)


def _paint_barcode(painter, op):
    q = _need_qt()
    G, C = q.QtGui, q.QtCore
    Qt = C.Qt
    x, y, w, h = op["x"], op["y"], op["w"], op["h"]
    kind, data = barcode_modules(op.get("kind"), op.get("value") or "")
    col = _color(q, op.get("color"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(col)
    if kind == "matrix":
        n = len(data)
        side = min(w, h)
        m = side / max(1, n)
        ox, oy = x + (w - side) / 2, y + (h - side) / 2
        for r_, row in enumerate(data):
            for c_, on in enumerate(row):
                if on:
                    painter.drawRect(C.QRectF(ox + c_ * m, oy + r_ * m, m + 0.02, m + 0.02))
        return
    if kind == "bars":
        text_h = h * 0.22 if op.get("showText") else 0
        mw = w / max(1, len(data))
        bx = x
        for ch in data:
            if ch == "1":
                painter.drawRect(C.QRectF(bx, y, mw + 0.02, h - text_h))
            bx += mw
        if text_h:
            f = G.QFont("Consolas")
            dpi = painter.device().logicalDpiY() or 96
            f.setPointSizeF(max(1.0, text_h * 0.8) * 72.0 / dpi)
            painter.setFont(f)
            painter.setPen(col)
            painter.drawText(C.QRectF(x, y + h - text_h, w, text_h),
                             _flags(Qt.AlignmentFlag.AlignCenter), op.get("value") or "")
        return
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(G.QColor("#C00000"))
    painter.drawRect(C.QRectF(x, y, w, h))
    f = G.QFont("Segoe UI")
    f.setPointSizeF(7 * 72.0 / (painter.device().logicalDpiY() or 96))
    painter.setFont(f)
    painter.drawText(C.QRectF(x, y, w, h), _flags(Qt.AlignmentFlag.AlignCenter, Qt.TextFlag.TextWordWrap),
                     f"barcode: {data}")


def _paint_chart(painter, op):
    q = _need_qt()
    G, C = q.QtGui, q.QtCore
    Qt = C.Qt
    x, y, w, h = op["x"], op["y"], op["w"], op["h"]
    labels, values = list(op.get("labels") or []), [float(v or 0) for v in op.get("values") or []]
    dpi = painter.device().logicalDpiY() or 96
    fsize = float(op.get("size") or 8)
    f = G.QFont(op.get("font") or "Segoe UI")
    f.setPointSizeF(fsize * 72.0 / dpi)
    painter.setFont(f)
    painter.setPen(G.QColor("#404040"))
    top = y
    if op.get("title"):
        tf = G.QFont(f)
        tf.setBold(True)
        painter.setFont(tf)
        painter.drawText(C.QRectF(x, y, w, fsize * 1.8), _flags(Qt.AlignmentFlag.AlignCenter), op["title"])
        painter.setFont(f)
        top += fsize * 1.9
    area = C.QRectF(x, top, w, y + h - top)
    if not values:
        painter.drawText(area, _flags(Qt.AlignmentFlag.AlignCenter), "(no data)")
        return
    colors = [_color(q, c) for c in CHART_COLORS]
    if op.get("color"):
        colors[0] = _color(q, op["color"])
    kind = (op.get("kind") or "bar").lower()
    if kind == "pie":
        total = sum(v for v in values if v > 0) or 1
        side = min(area.width() * 0.55, area.height())
        pie = C.QRectF(area.x() + 2, area.y() + (area.height() - side) / 2, side, side)
        start = 90 * 16
        painter.setPen(G.QPen(G.QColor("#FFFFFF"), 0.8))
        for i, v in enumerate(values):
            span = int(round(-360 * 16 * max(v, 0) / total))
            painter.setBrush(colors[i % len(colors)])
            painter.drawPie(pie, start, span)
            start += span
        lx = pie.right() + 8
        ly = area.y() + 2
        lh = fsize * 1.5
        for i, (lab, v) in enumerate(zip(labels, values)):
            if ly + lh > area.bottom():
                break
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(colors[i % len(colors)])
            painter.drawRect(C.QRectF(lx, ly + lh * 0.2, lh * 0.6, lh * 0.6))
            painter.setPen(G.QColor("#303030"))
            pct = 100.0 * max(v, 0) / total
            painter.drawText(C.QRectF(lx + lh * 0.8, ly, area.right() - lx - lh * 0.8, lh),
                             _flags(Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignVCenter),
                             f"{lab} ({pct:.0f}%)")
            ly += lh
        return
    # bar / line: axes
    lab_h = fsize * 1.6
    vmax = max(values + [0])
    vmin = min(values + [0])
    if vmax == vmin:
        vmax = vmin + 1
    axis_w = fsize * 4.5
    plot = C.QRectF(area.x() + axis_w, area.y() + fsize * 0.6, area.width() - axis_w - 4,
                    area.height() - lab_h - fsize * 0.6)
    painter.setPen(G.QPen(G.QColor("#DADADA"), 0.5))
    for k in range(5):
        gy = plot.bottom() - plot.height() * k / 4
        painter.drawLine(C.QPointF(plot.left(), gy), C.QPointF(plot.right(), gy))
        painter.setPen(G.QColor("#606060"))
        val = vmin + (vmax - vmin) * k / 4
        painter.drawText(C.QRectF(area.x(), gy - fsize, axis_w - 3, fsize * 2),
                         _flags(Qt.AlignmentFlag.AlignRight, Qt.AlignmentFlag.AlignVCenter), format_value(
                             round(val, 2) if abs(val) < 1000 else int(val), "N0" if abs(vmax) >= 100 else ""))
        painter.setPen(G.QPen(G.QColor("#DADADA"), 0.5))
    painter.setPen(G.QPen(G.QColor("#808080"), 0.8))
    zero_y = plot.bottom() - plot.height() * (0 - vmin) / (vmax - vmin)
    painter.drawLine(C.QPointF(plot.left(), zero_y), C.QPointF(plot.right(), zero_y))
    n = len(values)
    slot = plot.width() / n
    pts = []
    for i, v in enumerate(values):
        cx = plot.left() + slot * (i + 0.5)
        vy = plot.bottom() - plot.height() * (v - vmin) / (vmax - vmin)
        if kind == "line":
            pts.append(C.QPointF(cx, vy))
        else:
            bw = slot * 0.62
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(colors[0] if op.get("color") or kind == "bar" and n > len(colors) else
                             colors[i % len(colors)])
            painter.drawRect(C.QRectF(cx - bw / 2, min(vy, zero_y), bw, abs(zero_y - vy)))
        if op.get("showValues", True):
            painter.setPen(G.QColor("#303030"))
            painter.drawText(C.QRectF(cx - slot / 2, min(vy, zero_y) - fsize * 1.6, slot, fsize * 1.5),
                             _flags(Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignBottom),
                             format_value(round(v, 2)))
        painter.setPen(G.QColor("#404040"))
        painter.drawText(C.QRectF(cx - slot / 2, plot.bottom() + 2, slot, lab_h),
                         _flags(Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignTop),
                         painter.fontMetrics().elidedText(str(labels[i]) if i < len(labels) else "",
                                                          Qt.TextElideMode.ElideRight, int(max(4, slot * dpi / 72))))
    if kind == "line" and pts:
        pen = G.QPen(colors[0])
        pen.setWidthF(1.6)
        painter.setPen(pen)
        painter.drawPolyline(G.QPolygonF(pts))
        painter.setBrush(colors[0])
        for p in pts:
            painter.drawEllipse(p, 2.2, 2.2)


# ------------------------------------------------------------------------------ outputs
def render_image(rpt: Report, index: int, zoom: float = 1.0):
    """QImage of page *index* at zoom (1 = 96 dpi)."""
    q = _need_qt()
    ensure_app()
    page = rpt.pages[index]
    scale = zoom * 96.0 / 72.0
    img = q.QtGui.QImage(max(1, int(page["width"] * scale)), max(1, int(page["height"] * scale)),
                         q.QtGui.QImage.Format.Format_ARGB32_Premultiplied)
    img.setDotsPerMeterX(int(96 * zoom / 0.0254))
    img.setDotsPerMeterY(int(96 * zoom / 0.0254))
    img.fill(q.QtGui.QColor("#FFFFFF"))
    p = q.QtGui.QPainter(img)
    paint_page(p, page, img.logicalDpiY() / 72.0)
    p.end()
    return img


def image_png(img) -> bytes:
    q = _need_qt()
    buf = q.QtCore.QBuffer()
    buf.open(q.QtCore.QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def _page_layout(q, rpt):
    w, h = page_size(rpt.definition)
    size = q.QtGui.QPageSize(q.QtCore.QSizeF(w, h), q.QtGui.QPageSize.Unit.Point, "",
                             q.QtGui.QPageSize.SizeMatchPolicy.FuzzyMatch)
    orient = q.QtGui.QPageLayout.Orientation.Portrait
    if w > h:      # QPageSize is always portrait; landscape = rotated
        size = q.QtGui.QPageSize(q.QtCore.QSizeF(h, w), q.QtGui.QPageSize.Unit.Point, "",
                                 q.QtGui.QPageSize.SizeMatchPolicy.FuzzyMatch)
        orient = q.QtGui.QPageLayout.Orientation.Landscape
    return q.QtGui.QPageLayout(size, orient, q.QtCore.QMarginsF(0, 0, 0, 0))


def export_pdf(rpt: Report, path: str) -> str:
    q = _need_qt()
    ensure_app()
    path = os.path.abspath(path)
    writer = q.QtGui.QPdfWriter(path)
    writer.setResolution(1200)
    writer.setPageLayout(_page_layout(q, rpt))
    writer.setTitle(str(rpt.definition.get("title") or rpt.definition.get("name") or "Report"))
    writer.setCreator("RAD IDE radreport")
    p = q.QtGui.QPainter(writer)
    try:
        for i, page in enumerate(rpt.pages):
            if i:
                writer.newPage()
            paint_page(p, page, writer.resolution() / 72.0)
    finally:
        p.end()
    return path


def print_report(rpt: Report, show_dialog: bool = True, parent=None, printer=None) -> bool:
    q = _need_qt()
    ensure_app(widgets=True)
    PS = q.QtPrintSupport
    if PS is None:
        raise ReportError("Printing needs QtPrintSupport")
    if printer is None:
        printer = PS.QPrinter(PS.QPrinter.PrinterMode.HighResolution)
    printer.setFullPage(True)
    printer.setPageLayout(_page_layout(q, rpt))
    printer.setDocName(str(rpt.definition.get("title") or "Report"))
    printer.setFromTo(1, max(1, len(rpt.pages)))
    if show_dialog:
        dlg = PS.QPrintDialog(printer, parent)
        dlg.setMinMax(1, max(1, len(rpt.pages)))
        if int(dlg.exec()) != 1:
            return False
    first, last = printer.fromPage(), printer.toPage()
    if first <= 0:
        first, last = 1, len(rpt.pages)
    p = q.QtGui.QPainter(printer)
    try:
        dpi = printer.resolution()
        for n in range(first, min(last, len(rpt.pages)) + 1):
            if n > first:
                printer.newPage()
            paint_page(p, rpt.pages[n - 1], dpi / 72.0)
    finally:
        p.end()
    return True


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _op_png_uri(op) -> str:
    """A PNG data: URI of one graphic op (image, barcode, chart), drawn by Qt at 2x."""
    q = qt()
    if q is None:
        return ""
    ensure_app()
    s = 2.0 * 96 / 72
    img = q.QtGui.QImage(max(1, int(op["w"] * s)), max(1, int(op["h"] * s)),
                         q.QtGui.QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(q.QtGui.QColor(0, 0, 0, 0))
    p = q.QtGui.QPainter(img)
    p.scale(s, s)
    p.translate(-op["x"], -op["y"])
    p.setRenderHint(q.QtGui.QPainter.RenderHint.Antialiasing, True)
    paint_op(p, op)
    p.end()
    return "data:image/png;base64," + base64.b64encode(image_png(img)).decode("ascii")


def export_html(rpt: Report, path: str) -> str:
    d = rpt.definition
    title = _esc(d.get("title") or d.get("name") or "Report")
    rtl = bool(d.get("rightToLeft"))
    out = ["<!DOCTYPE html>", f"<html lang=\"{'ar' if rtl else 'en'}\"><head><meta charset=\"utf-8\">",
           f"<title>{title}</title><style>",
           "body{background:#888;margin:0;padding:16px;font-family:'Segoe UI',Tahoma,Arial,sans-serif}",
           ".page{position:relative;background:#fff;margin:0 auto 16px;box-shadow:0 2px 8px rgba(0,0,0,.4);"
           "overflow:hidden}",
           ".t{position:absolute;overflow:hidden;box-sizing:border-box;display:flex}",
           ".g{position:absolute}",
           "@media print{body{background:none;padding:0}.page{margin:0;box-shadow:none;page-break-after:always}}",
           "</style></head><body>"]
    for page in rpt.pages:
        pw, ph = page["width"], page["height"]
        out.append(f'<div class="page" style="width:{pw:.1f}pt;height:{ph:.1f}pt">')
        svg = []
        for op in page["ops"]:
            k = op["op"]
            if k == "line":
                dash = {"dash": ' stroke-dasharray="4 2"', "dot": ' stroke-dasharray="1 2"'}.get(op.get("style"), "")
                svg.append(f'<line x1="{op["x1"]:.2f}" y1="{op["y1"]:.2f}" x2="{op["x2"]:.2f}" y2="{op["y2"]:.2f}" '
                           f'stroke="{_esc(op["color"])}" stroke-width="{op["lw"]}"{dash}/>')
            elif k == "rect":
                fill = _esc(op.get("fill") or "none")
                stroke = f' stroke="{_esc(op.get("bc") or "#000")}" stroke-width="{op["bw"]}"' if op.get("bw") else ""
                rr = f' rx="{op["radius"]}"' if op.get("radius") else ""
                svg.append(f'<rect x="{op["x"]:.2f}" y="{op["y"]:.2f}" width="{op["w"]:.2f}" height="{op["h"]:.2f}" '
                           f'fill="{fill}"{stroke}{rr}/>')
        if svg:
            out.append(f'<svg class="g" style="left:0;top:0" width="{pw:.1f}pt" height="{ph:.1f}pt" '
                       f'viewBox="0 0 {pw:.2f} {ph:.2f}">' + "".join(svg) + "</svg>")
        for op in page["ops"]:
            k = op["op"]
            if k == "text":
                if not op.get("text") and not op.get("back") and not op.get("bw"):
                    continue
                direction = "rtl" if (op.get("rtl") or (op.get("rtl") is None and is_rtl_text(op["text"]))) \
                    else "ltr"
                ja = {"left": "flex-start", "center": "center", "right": "flex-end", "justify": "stretch"}
                va = {"top": "flex-start", "middle": "center", "bottom": "flex-end"}
                st = [f"left:{op['x']:.2f}pt", f"top:{op['y']:.2f}pt", f"width:{op['w']:.2f}pt",
                      f"height:{op['h']:.2f}pt", f"font-family:'{_esc(op['font'])}',Tahoma,Arial",
                      f"font-size:{op['size']}pt", f"color:{_esc(op['color'])}",
                      f"justify-content:{ja.get(op.get('align'), 'flex-start')}",
                      f"align-items:{va.get(op.get('valign'), 'center')}",
                      f"padding:0 {op.get('pad', 2)}pt", f"text-align:{op.get('align') or 'left'}",
                      "white-space:" + ("normal" if op.get("wrap") else "nowrap")]
                if op.get("bold"):
                    st.append("font-weight:bold")
                if op.get("italic"):
                    st.append("font-style:italic")
                if op.get("underline"):
                    st.append("text-decoration:underline")
                if op.get("back"):
                    st.append(f"background:{_esc(op['back'])}")
                if op.get("bw"):
                    st.append(f"border:{op['bw']}pt solid {_esc(op.get('bc') or '#000')}")
                out.append(f'<div class="t" dir="{direction}" style="{";".join(st)}"><span>{_esc(op["text"])}'
                           f'</span></div>')
            elif k in ("image", "barcode", "chart"):
                uri = ""
                if k == "image" and op.get("data"):
                    uri = "data:image/png;base64," + op["data"]
                if not uri:
                    try:
                        uri = _op_png_uri(op)
                    except Exception:  # noqa: BLE001
                        uri = ""
                if uri:
                    out.append(f'<img class="g" alt="" src="{uri}" style="left:{op["x"]:.2f}pt;top:{op["y"]:.2f}pt;'
                               f'width:{op["w"]:.2f}pt;height:{op["h"]:.2f}pt">')
        out.append("</div>")
    out.append("</body></html>")
    path = os.path.abspath(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return path


def _columns(rpt: Report):
    """Table columns for CSV / Excel: the detail band's field / expression items from left to right."""
    items = [it for it in (rpt.definition.get("bands", {}).get("detail", {}).get("items") or [])
             if it.get("type") in ("field", "expression", "text")]
    items.sort(key=lambda it: float(it.get("x", 0)), reverse=bool(rpt.definition.get("mirrorLayout")))
    # headers: a page-header text above the column, else the field name
    heads = [it for it in (rpt.definition.get("bands", {}).get("pageHeader", {}).get("items") or [])
             if it.get("type") == "text"]
    cols = []
    for it in items:
        x0, x1 = float(it.get("x", 0)), float(it.get("x", 0)) + float(it.get("w", 0))
        best, ov = None, 0.0
        for hd in heads:
            hx0, hx1 = float(hd.get("x", 0)), float(hd.get("x", 0)) + float(hd.get("w", 0))
            o = min(x1, hx1) - max(x0, hx0)
            if o > ov and "{" not in str(hd.get("text", "")):
                best, ov = hd, o
        title = best.get("text") if best is not None else (it.get("field") or it.get("name") or "")
        cols.append({"item": it, "title": str(title), "x0": x0, "x1": x1})
    return cols


def _decimals(fmt: str):
    """Decimals shown by a number format (N2 -> 2, "#,##0.0" -> 1), or None."""
    fmt = str(fmt or "")
    m = re.fullmatch(r"[NnFfCc](\d*)", fmt)
    if m:
        return int(m.group(1) or 2)
    m = re.fullmatch(r"[Pp](\d*)", fmt)
    if m:
        return int(m.group(1) or 2) + 2
    m = re.fullmatch(r"[#0,]*\.?([#0]*)", fmt)
    if m and ("0" in fmt or "#" in fmt):
        return len(m.group(1))
    m = re.fullmatch(r",?\.(\d+)[f%]", fmt)
    if m:
        return int(m.group(1))
    return None


def _cell_value(cl):
    v = cl["value"]
    if isinstance(v, (int, float)) and not isinstance(v, bool) and cl["type"] != "text":
        d = _decimals(cl.get("format", ""))
        if isinstance(v, float):
            v = round(v, d if d is not None else 10)
        return v
    return cl["text"]


def _table(rpt: Report, details_only: bool):
    """Rows for CSV / Excel: [(kind, [values...], [formats...])]."""
    cols = _columns(rpt)
    head = ("header", [c["title"] for c in cols], [""] * len(cols))
    out = []
    for entry in rpt.log:
        kind = entry["band"]
        if head is not None and kind != "reportHeader":
            out.append(head)
            head = None
        if kind == "detail":
            vals, fmts = [], []
            cells = entry["cells"]
            for c in cols:
                cell = next((cl for cl in cells if abs(cl["x"] - float(c["item"].get("x", 0))) < 0.01 and
                             cl["name"] == c["item"].get("name", "")), None)
                vals.append(_cell_value(cell) if cell is not None else "")
                fmts.append(cell.get("format", "") if cell is not None else "")
            out.append(("detail", vals, fmts))
        elif not details_only and entry["cells"]:
            # the band's items line by line (top to bottom), each item in the column under its centre
            lines: list[list[dict]] = []
            bottom = None
            for cl in sorted((c for c in entry["cells"] if c["text"]), key=lambda c: (c.get("y", 0), c["x"])):
                mid = cl.get("y", 0) + cl.get("h", 0) / 2
                if lines and bottom is not None and mid < bottom:
                    lines[-1].append(cl)
                    bottom = max(bottom, cl.get("y", 0) + cl.get("h", 0))
                else:
                    lines.append([cl])
                    bottom = cl.get("y", 0) + cl.get("h", 0)
            for line in lines:
                vals = [""] * max(1, len(cols))
                fmts = [""] * len(vals)
                spill = []
                for cl in sorted(line, key=lambda c: c["x"]):
                    cx = cl["x"] + cl["w"] / 2
                    idx = next((i for i, c in enumerate(cols) if c["x0"] <= cx <= c["x1"]), None)
                    if idx is None or vals[idx] != "":
                        spill.append(cl["text"])
                    else:
                        vals[idx] = _cell_value(cl)
                        fmts[idx] = cl.get("format", "")
                if spill:
                    first_free = next((i for i, v in enumerate(vals) if v == ""), None)
                    if first_free is None:
                        vals.append(" ".join(spill))
                        fmts.append("")
                    else:
                        vals[first_free] = " ".join(spill)
                out.append((kind, vals, fmts))
    if head is not None:
        out.append(head)
    return out


def export_csv(rpt: Report, path: str) -> str:
    path = os.path.abspath(path)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        for _kind, vals, _fmts in _table(rpt, details_only=True):
            w.writerow(["" if v is None else v for v in vals])
    return path


def export_excel(rpt: Report, path: str) -> str:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError:
        raise ReportError("Excel export needs openpyxl (pip install openpyxl)") from None
    wb = Workbook()
    ws = wb.active
    ws.title = str(rpt.definition.get("name") or "Report")[:31]
    rtl = bool(rpt.definition.get("rightToLeft"))
    if rtl:
        ws.sheet_view.rightToLeft = True
    r = 1
    widths: dict[int, int] = {}
    head_fill = PatternFill("solid", fgColor="DDE4EE")
    group_fill = PatternFill("solid", fgColor="F2F2F2")
    for kind, vals, fmts in _table(rpt, details_only=False):
        for c, v in enumerate(vals, start=1):
            if v is None or v == "":
                continue
            cell = ws.cell(row=r, column=c, value=v)
            if kind == "header":
                cell.font = Font(bold=True)
                cell.fill = head_fill
            elif kind in ("groupHeader", "groupFooter", "reportFooter", "reportHeader"):
                cell.font = Font(bold=True)
                if kind == "groupHeader":
                    cell.fill = group_fill
            d = _decimals(fmts[c - 1]) if c - 1 < len(fmts) else None
            if isinstance(v, (int, float)) and not isinstance(v, bool) and d is not None:
                f = fmts[c - 1]
                if f[:1] in "Pp":
                    cell.number_format = "0" + ("." + "0" * (d - 2) if d > 2 else "") + "%"
                else:
                    grp = "#,##" if (f[:1] in "NnCc" or "," in f) else ""
                    cell.number_format = grp + "0" + ("." + "0" * d if d else "")
            if rtl:
                cell.alignment = Alignment(horizontal="right")
            widths[c] = max(widths.get(c, 6), min(60, len(str(v)) + 2))
        r += 1
    from openpyxl.utils import get_column_letter
    for c, wdt in widths.items():
        ws.column_dimensions[get_column_letter(c)].width = wdt
    path = os.path.abspath(path)
    wb.save(path)
    return path


# ============================================================================== viewers
_QT_VIEWER = None


def _qt_viewer_class():
    """QtReportViewer: a QWidget with a toolbar (pages, zoom, print, export) and the page."""
    global _QT_VIEWER
    if _QT_VIEWER is not None:
        return _QT_VIEWER
    q = _need_qt()
    W, G, C = q.QtWidgets, q.QtGui, q.QtCore
    Qt = C.Qt

    class _Page(W.QWidget):
        def __init__(self, viewer):
            super().__init__()
            self.v = viewer
            self.setAutoFillBackground(False)

        def sizeHint(self):
            return self.minimumSize()

        def paintEvent(self, _e):
            v = self.v
            p = G.QPainter(self)
            p.fillRect(self.rect(), v._stage)
            page = v.current_page()
            if page is None:
                p.setPen(G.QColor("#FFFFFF"))
                p.drawText(self.rect(), _flags(Qt.AlignmentFlag.AlignCenter), v._message or "No report")
                p.end()
                return
            s = v._scale()
            pw, ph = page["width"] * s, page["height"] * s
            ox = max(10.0, (self.width() - pw) / 2)
            p.fillRect(C.QRectF(ox + 3, 13, pw, ph), G.QColor(0, 0, 0, 70))
            p.fillRect(C.QRectF(ox, 10, pw, ph), G.QColor("#FFFFFF"))
            p.translate(ox, 10)
            p.setClipRect(C.QRectF(0, 0, pw, ph))
            paint_page(p, page, s)
            p.end()

        def wheelEvent(self, e):
            if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.v.SetZoom(self.v.Zoom + (10 if e.angleDelta().y() > 0 else -10))
                e.accept()
            else:
                e.ignore()

    class QtReportViewer(W.QWidget):
        """ReportViewer for Qt programs: ReportFile, Parameters, SetData(), Refresh(), Print(), Export*()."""
        PageChanged = q.Signal(int)

        def __init__(self, parent=None, report=None, ReportFile="", Zoom=100, ShowToolbar=True, AutoLoad=True):
            super().__init__(parent)
            self.Report: Report | None = None
            self.Parameters: dict = {}
            self._data = None
            self._page = 0
            self._fit = ""
            self.Zoom = int(Zoom or 100)
            self._message = ""
            self._stage = G.QColor("#808080")
            lay = W.QVBoxLayout(self)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(0)
            self.toolbar = tb = W.QToolBar(self)
            tb.setIconSize(C.QSize(16, 16))
            st = self.style()
            sp = W.QStyle.StandardPixmap
            self._a_first = tb.addAction(st.standardIcon(sp.SP_MediaSkipBackward), "First page", self.FirstPage)
            self._a_prev = tb.addAction(st.standardIcon(sp.SP_MediaSeekBackward), "Previous page",
                                        self.PreviousPage)
            self._page_edit = W.QSpinBox(self)
            self._page_edit.setMinimum(1)
            self._page_edit.setKeyboardTracking(False)
            self._page_edit.valueChanged.connect(lambda n: self.GoToPage(n))
            tb.addWidget(self._page_edit)
            self._page_lbl = W.QLabel(" of 0 ", self)
            tb.addWidget(self._page_lbl)
            self._a_next = tb.addAction(st.standardIcon(sp.SP_MediaSeekForward), "Next page", self.NextPage)
            self._a_last = tb.addAction(st.standardIcon(sp.SP_MediaSkipForward), "Last page", self.LastPage)
            tb.addSeparator()
            self._zoom = W.QComboBox(self)
            self._zoom.setEditable(True)
            self._zoom.addItems(["Page width", "Whole page", "50%", "75%", "100%", "125%", "150%", "200%", "300%"])
            self._zoom.setCurrentText(f"{self.Zoom}%")
            self._zoom.textActivated.connect(self._zoom_text)
            self._zoom.lineEdit().editingFinished.connect(lambda: self._zoom_text(self._zoom.currentText()))
            tb.addWidget(self._zoom)
            tb.addSeparator()
            tb.addAction(st.standardIcon(sp.SP_BrowserReload), "Refresh", self.Refresh)
            self._a_params = tb.addAction(st.standardIcon(sp.SP_FileDialogDetailedView), "Parameters...",
                                          self.AskParameters)
            self._a_params.setVisible(False)
            self._a_print = tb.addAction("Print...", lambda: self.Print())
            exp = W.QToolButton(self)
            exp.setText("Export")
            exp.setPopupMode(W.QToolButton.ToolButtonPopupMode.InstantPopup)
            menu = W.QMenu(exp)
            for text, ext in (("PDF...", "pdf"), ("HTML...", "html"), ("CSV...", "csv"), ("Excel...", "xlsx")):
                menu.addAction(text, lambda e=ext: self._export_dialog(e))
            exp.setMenu(menu)
            tb.addWidget(exp)
            lay.addWidget(tb)
            self.scroll = W.QScrollArea(self)
            self.scroll.setWidgetResizable(False)
            self.scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.canvas = _Page(self)
            self.scroll.setWidget(self.canvas)
            lay.addWidget(self.scroll, 1)
            self.toolbar.setVisible(bool(ShowToolbar))
            self._update()
            if report is not None:
                self.SetReport(report)
            elif ReportFile:
                self.ReportFile = ReportFile
                if AutoLoad:
                    C.QTimer.singleShot(0, self._autoload)
            else:
                self.ReportFile = ""

        # ---------------------------------------------------------- API
        def _autoload(self):
            try:
                self.LoadReport(self.ReportFile)
            except Exception as e:  # noqa: BLE001
                self._message = str(e)
                self.canvas.update()

        def LoadReport(self, path, **params):
            self.ReportFile = str(path)
            r = Report(path)
            r.Parameters.update(self.Parameters)
            r.Parameters.update(params)
            self.Parameters = r.Parameters
            if self._data is not None:
                r.SetData(self._data)
            self.SetReport(r)

        def SetReport(self, report):
            if not isinstance(report, Report):
                report = Report(report)
            self.Report = report
            self.Parameters = report.Parameters
            self.Refresh()

        def SetData(self, rows, columns=None):
            self._data = rows
            if self.Report is not None:
                self.Report.SetData(rows, columns)
                self.Refresh()

        def AskParameters(self):
            """Ask the user for the report's parameters (their prompts); True when OK."""
            params = [p for p in (self.Report.definition.get("parameters") or []) if p.get("name")]                 if self.Report is not None else []
            if not params:
                return False
            dlg = W.QDialog(self)
            dlg.setWindowTitle("Report parameters")
            form = W.QFormLayout(dlg)
            edits = {}
            for p in params:
                cur = self.Parameters.get(p["name"])
                e = W.QLineEdit("" if cur is None else str(cur), dlg)
                e.setPlaceholderText("(empty)")
                form.addRow(p.get("prompt") or p["name"], e)
                edits[p["name"]] = e
            bb = W.QDialogButtonBox(W.QDialogButtonBox.StandardButton.Ok |
                                    W.QDialogButtonBox.StandardButton.Cancel, dlg)
            bb.accepted.connect(dlg.accept)
            bb.rejected.connect(dlg.reject)
            form.addRow(bb)
            if int(dlg.exec()) != 1:
                return False
            for name, e in edits.items():
                t = e.text().strip()
                self.Parameters[name] = _convert(t) if t else None
            self.Refresh()
            return True

        def Refresh(self):
            if self.Report is None:
                if self.ReportFile:
                    return self.LoadReport(self.ReportFile)
                return
            self.Report.Parameters = self.Parameters
            try:
                self.Report.Refresh()
                self._message = ""
            except Exception as e:  # noqa: BLE001
                self.Report.pages = []
                self._message = f"Cannot run the report:\n{e}"
            self._page = min(self._page, max(0, len(self.Report.pages) - 1))
            self._update()

        @property
        def PageCount(self):
            return len(self.Report.pages) if self.Report is not None else 0

        @property
        def Page(self):
            return self._page + 1

        def current_page(self):
            if self.Report is None or not self.Report.pages:
                return None
            return self.Report.pages[min(self._page, len(self.Report.pages) - 1)]

        def GoToPage(self, n):
            n = max(1, min(int(n), max(1, self.PageCount)))
            if n - 1 != self._page:
                self._page = n - 1
                self._update()
                self.PageChanged.emit(n)

        def FirstPage(self):
            self.GoToPage(1)

        def LastPage(self):
            self.GoToPage(self.PageCount)

        def NextPage(self):
            self.GoToPage(self.Page + 1)

        def PreviousPage(self):
            self.GoToPage(self.Page - 1)

        def SetZoom(self, percent):
            self._fit = ""
            self.Zoom = max(10, min(800, int(percent)))
            self._zoom.setCurrentText(f"{self.Zoom}%")
            self._update()

        def FitWidth(self):
            self._fit = "width"
            self._update()

        def FitPage(self):
            self._fit = "page"
            self._update()

        def Print(self, show_dialog=True):
            if self.Report is None:
                return False
            return print_report(self.Report, show_dialog, self)

        def ExportPdf(self, path):
            return self.Report.ExportPdf(path)

        def ExportHtml(self, path):
            return self.Report.ExportHtml(path)

        def ExportCsv(self, path):
            return self.Report.ExportCsv(path)

        def ExportExcel(self, path):
            return self.Report.ExportExcel(path)

        def Export(self, path):
            return self.Report.Export(path)

        @property
        def ShowToolbar(self):
            return self.toolbar.isVisible()

        @ShowToolbar.setter
        def ShowToolbar(self, on):
            self.toolbar.setVisible(bool(on))

        # ---------------------------------------------------------- internals
        def _scale(self):
            page = self.current_page()
            vw = max(50, self.scroll.viewport().width() - 24)
            vh = max(50, self.scroll.viewport().height() - 24)
            if page is not None and self._fit == "width":
                return vw / page["width"]
            if page is not None and self._fit == "page":
                return min(vw / page["width"], vh / page["height"])
            return self.Zoom / 100.0 * 96.0 / 72.0

        def _zoom_text(self, text):
            t = str(text).strip().lower()
            if t.startswith("page"):
                self.FitWidth()
            elif t.startswith("whole"):
                self.FitPage()
            else:
                m = re.match(r"(\d+)", t)
                if m:
                    self.SetZoom(int(m.group(1)))

        def _update(self):
            n = self.PageCount
            self._page_edit.blockSignals(True)
            self._page_edit.setMaximum(max(1, n))
            self._page_edit.setValue(self._page + 1)
            self._page_edit.blockSignals(False)
            self._page_lbl.setText(f" of {n} ")
            for a, on in ((self._a_first, self._page > 0), (self._a_prev, self._page > 0),
                          (self._a_next, self._page < n - 1), (self._a_last, self._page < n - 1),
                          (self._a_print, n > 0)):
                a.setEnabled(on)
            self._a_params.setVisible(bool(self.Report is not None and self.Report.definition.get("parameters")))
            page = self.current_page()
            s = self._scale()
            if page is not None:
                self.canvas.setMinimumSize(int(page["width"] * s + 24), int(page["height"] * s + 24))
            else:
                self.canvas.setMinimumSize(200, 120)
            self.canvas.resize(max(self.canvas.minimumWidth(), self.scroll.viewport().width()),
                               max(self.canvas.minimumHeight(), self.scroll.viewport().height()))
            self.canvas.update()

        def resizeEvent(self, e):
            super().resizeEvent(e)
            self._update()

        def keyPressEvent(self, e):
            k = e.key()
            if k == Qt.Key.Key_PageDown:
                self.NextPage()
            elif k == Qt.Key.Key_PageUp:
                self.PreviousPage()
            elif k == Qt.Key.Key_Home and e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.FirstPage()
            elif k == Qt.Key.Key_End and e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.LastPage()
            else:
                super().keyPressEvent(e)

        def _export_dialog(self, ext):
            if self.Report is None:
                return
            names = {"pdf": "PDF files (*.pdf)", "html": "Web pages (*.html)", "csv": "CSV files (*.csv)",
                     "xlsx": "Excel workbooks (*.xlsx)"}
            base = os.path.splitext(os.path.basename(self.Report.path or "report"))[0].replace(".rpt", "")
            path, _ = W.QFileDialog.getSaveFileName(self, "Export report", base + "." + ext, names[ext])
            if not path:
                return
            try:
                self.Report.Export(path)
            except Exception as e:  # noqa: BLE001
                W.QMessageBox.warning(self, "Export", str(e))
                return
            G.QDesktopServices.openUrl(C.QUrl.fromLocalFile(path))

    _QT_VIEWER = QtReportViewer
    return QtReportViewer


_TK_VIEWER = None


def _tk_viewer_class():
    """TkReportViewer: a tkinter Frame with a toolbar and the page (drawn by Qt when installed)."""
    global _TK_VIEWER
    if _TK_VIEWER is not None:
        return _TK_VIEWER
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    class TkReportViewer(tk.Frame):
        """ReportViewer for Tkinter programs: ReportFile, Parameters, SetData(), Refresh(), Print(), Export*()."""

        def __init__(self, master=None, report=None, ReportFile="", Zoom=100, ShowToolbar=True, AutoLoad=True,
                     **kw):
            kw.setdefault("bg", "#808080")
            super().__init__(master, **kw)
            self.Report: Report | None = None
            self.Parameters: dict = {}
            self.ReportFile = ReportFile
            self.Zoom = int(Zoom or 100)
            self.on_page_changed = None
            self._data = None
            self._page = 0
            self._img = None
            self._message = ""
            self.toolbar = bar = tk.Frame(self, bd=1, relief="raised")
            b = dict(relief="flat", padx=6)
            tk.Button(bar, text="|<", command=self.FirstPage, **b).pack(side="left")
            tk.Button(bar, text="<", command=self.PreviousPage, **b).pack(side="left")
            self._page_var = tk.StringVar(value="0 / 0")
            tk.Label(bar, textvariable=self._page_var, width=10).pack(side="left")
            tk.Button(bar, text=">", command=self.NextPage, **b).pack(side="left")
            tk.Button(bar, text=">|", command=self.LastPage, **b).pack(side="left")
            self._zoom_var = tk.StringVar(value=f"{self.Zoom}%")
            zc = ttk.Combobox(bar, textvariable=self._zoom_var, width=7,
                              values=["50%", "75%", "100%", "125%", "150%", "200%"])
            zc.pack(side="left", padx=6)
            zc.bind("<<ComboboxSelected>>", lambda _e: self._zoom_from_text())
            zc.bind("<Return>", lambda _e: self._zoom_from_text())
            tk.Button(bar, text="Refresh", command=self.Refresh, **b).pack(side="left")
            tk.Button(bar, text="Parameters...", command=self.AskParameters, **b).pack(side="left")
            tk.Button(bar, text="Print...", command=lambda: self.Print(), **b).pack(side="left")
            mb = tk.Menubutton(bar, text="Export ▾", relief="flat", padx=6)
            m = tk.Menu(mb, tearoff=False)
            for text, ext in (("PDF...", "pdf"), ("HTML...", "html"), ("CSV...", "csv"), ("Excel...", "xlsx")):
                m.add_command(label=text, command=lambda e=ext: self._export_dialog(e))
            mb.configure(menu=m)
            mb.pack(side="left")
            if ShowToolbar:
                bar.pack(side="top", fill="x")
            body = tk.Frame(self, bg="#808080")
            body.pack(side="top", fill="both", expand=True)
            self.canvas = tk.Canvas(body, bg="#808080", highlightthickness=0)
            ys = tk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
            xs = tk.Scrollbar(body, orient="horizontal", command=self.canvas.xview)
            self.canvas.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
            ys.pack(side="right", fill="y")
            xs.pack(side="bottom", fill="x")
            self.canvas.pack(side="left", fill="both", expand=True)
            self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
            self.canvas.bind("<Configure>", lambda _e: self._draw())
            self.bind_all("<Next>", lambda _e: self.NextPage(), add="+")
            self.bind_all("<Prior>", lambda _e: self.PreviousPage(), add="+")
            if report is not None:
                self.SetReport(report)
            elif ReportFile and AutoLoad:
                self.after(0, self._autoload)

        def _autoload(self):
            try:
                self.LoadReport(self.ReportFile)
            except Exception as e:  # noqa: BLE001
                self._message = str(e)
                self._draw()

        def LoadReport(self, path, **params):
            self.ReportFile = str(path)
            r = Report(path)
            r.Parameters.update(self.Parameters)
            r.Parameters.update(params)
            self.Parameters = r.Parameters
            if self._data is not None:
                r.SetData(self._data)
            self.SetReport(r)

        def SetReport(self, report):
            if not isinstance(report, Report):
                report = Report(report)
            self.Report = report
            self.Parameters = report.Parameters
            self.Refresh()

        def SetData(self, rows, columns=None):
            self._data = rows
            if self.Report is not None:
                self.Report.SetData(rows, columns)
                self.Refresh()

        def Refresh(self):
            if self.Report is None:
                if self.ReportFile:
                    self.LoadReport(self.ReportFile)
                return
            self.Report.Parameters = self.Parameters
            try:
                self.Report.Refresh()
                self._message = ""
            except Exception as e:  # noqa: BLE001
                self.Report.pages = []
                self._message = f"Cannot run the report:\n{e}"
            self._page = min(self._page, max(0, len(self.Report.pages) - 1))
            self._draw()

        @property
        def PageCount(self):
            return len(self.Report.pages) if self.Report is not None else 0

        @property
        def Page(self):
            return self._page + 1

        def GoToPage(self, n):
            n = max(1, min(int(n), max(1, self.PageCount)))
            if n - 1 != self._page:
                self._page = n - 1
                self._draw()
                if callable(self.on_page_changed):
                    self.on_page_changed(n)

        def AskParameters(self):
            """Ask the user for the report's parameters (their prompts); True when OK."""
            from tkinter import simpledialog
            if self.Report is None:
                return False
            for p in self.Report.definition.get("parameters") or []:
                name = p.get("name")
                if not name:
                    continue
                cur = self.Parameters.get(name)
                v = simpledialog.askstring("Report parameters", p.get("prompt") or name,
                                           initialvalue="" if cur is None else str(cur), parent=self)
                if v is None:
                    return False
                self.Parameters[name] = _convert(v) if v != "" else None
            self.Refresh()
            return True

        def FirstPage(self):
            self.GoToPage(1)

        def LastPage(self):
            self.GoToPage(self.PageCount)

        def NextPage(self):
            self.GoToPage(self.Page + 1)

        def PreviousPage(self):
            self.GoToPage(self.Page - 1)

        def SetZoom(self, percent):
            self.Zoom = max(10, min(800, int(percent)))
            self._zoom_var.set(f"{self.Zoom}%")
            self._draw()

        def Print(self, show_dialog=True):
            if self.Report is None:
                return False
            if qt() is not None:
                return print_report(self.Report, show_dialog)
            import tempfile
            import webbrowser
            path = os.path.join(tempfile.gettempdir(), "radreport_print.html")
            export_html(self.Report, path)
            webbrowser.open("file:///" + path.replace("\\", "/"))
            return True

        def ExportPdf(self, path):
            return self.Report.ExportPdf(path)

        def ExportHtml(self, path):
            return self.Report.ExportHtml(path)

        def ExportCsv(self, path):
            return self.Report.ExportCsv(path)

        def ExportExcel(self, path):
            return self.Report.ExportExcel(path)

        def Export(self, path):
            return self.Report.Export(path)

        def _zoom_from_text(self):
            m = re.match(r"\s*(\d+)", self._zoom_var.get())
            if m:
                self.SetZoom(int(m.group(1)))

        def _export_dialog(self, ext):
            if self.Report is None:
                return
            types = {"pdf": ("PDF files", "*.pdf"), "html": ("Web pages", "*.html"), "csv": ("CSV files", "*.csv"),
                     "xlsx": ("Excel workbooks", "*.xlsx")}
            path = filedialog.asksaveasfilename(defaultextension="." + ext, filetypes=[types[ext]])
            if not path:
                return
            try:
                self.Report.Export(path)
            except Exception as e:  # noqa: BLE001
                messagebox.showwarning("Export", str(e))
                return
            try:
                os.startfile(path)  # type: ignore[attr-defined]
            except (AttributeError, OSError):
                pass

        def _draw(self):
            c = self.canvas
            c.delete("all")
            n = self.PageCount
            self._page_var.set(f"{self._page + 1 if n else 0} / {n}")
            if not n:
                c.create_text(max(100, c.winfo_width() // 2), 60, text=self._message or "No report",
                              fill="#FFFFFF", justify="center")
                return
            page = self.Report.pages[self._page]
            zoom = self.Zoom / 100.0
            s = zoom * 96 / 72
            pw, ph = int(page["width"] * s), int(page["height"] * s)
            ox = max(10, (c.winfo_width() - pw) // 2)
            c.create_rectangle(ox + 3, 13, ox + pw + 3, ph + 13, fill="#505050", outline="")
            if qt() is not None:
                try:
                    png = image_png(render_image(self.Report, self._page, zoom))
                    self._img = tk.PhotoImage(data=base64.b64encode(png).decode("ascii"))
                    c.create_image(ox, 10, image=self._img, anchor="nw")
                except Exception as e:  # noqa: BLE001
                    self._message = str(e)
                    self._img = None
            if self._img is None:
                c.create_rectangle(ox, 10, ox + pw, ph + 10, fill="#FFFFFF", outline="#404040")
                _tk_paint(c, page, s, ox, 10)
            c.configure(scrollregion=(0, 0, max(pw + 20, c.winfo_width()), ph + 24))

    _TK_VIEWER = TkReportViewer
    return TkReportViewer


def _tk_paint(c, page, s, ox, oy):
    """Plain Tk drawing when Qt is not installed (no charts / barcodes)."""
    for op in page["ops"]:
        k = op["op"]
        if k == "line":
            c.create_line(ox + op["x1"] * s, oy + op["y1"] * s, ox + op["x2"] * s, oy + op["y2"] * s,
                          fill=op["color"], width=max(1, op["lw"] * s))
        elif k == "rect":
            c.create_rectangle(ox + op["x"] * s, oy + op["y"] * s, ox + (op["x"] + op["w"]) * s,
                               oy + (op["y"] + op["h"]) * s, fill=op.get("fill") or "",
                               outline=op.get("bc") if op.get("bw") else "")
        elif k == "text" and op.get("text"):
            anchor = {"left": "w", "center": "center", "right": "e"}.get(op.get("align"), "w")
            x = {"w": op["x"] + 2, "center": op["x"] + op["w"] / 2, "e": op["x"] + op["w"] - 2}[anchor]
            style = ("bold " if op.get("bold") else "") + ("italic" if op.get("italic") else "")
            c.create_text(ox + x * s, oy + (op["y"] + op["h"] / 2) * s, text=op["text"], anchor=anchor,
                          fill=op["color"], font=(op["font"], -max(6, int(op["size"] * s)), style.strip()))
        elif k in ("image", "barcode", "chart"):
            c.create_rectangle(ox + op["x"] * s, oy + op["y"] * s, ox + (op["x"] + op["w"]) * s,
                               oy + (op["y"] + op["h"]) * s, outline="#A0A0A0", dash=(3, 2))


def __getattr__(name):
    if name == "QtReportViewer":
        return _qt_viewer_class()
    if name == "TkReportViewer":
        return _tk_viewer_class()
    raise AttributeError(name)


def show(path, **params):
    """Open a report preview window (Qt) and run until it is closed; returns nothing."""
    q = _need_qt()
    app = ensure_app(widgets=True)
    v = _qt_viewer_class()(None)
    v.LoadReport(path, **params)
    v.setWindowTitle(str(v.Report.definition.get("title") or os.path.basename(str(path))))
    v.resize(900, 1000)
    v.show()
    if not getattr(app, "_radreport_running", False) and q.QtCore.QCoreApplication.instance() is app:
        app.exec()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Run a RAD IDE report (.rpt.json)")
    ap.add_argument("report")
    ap.add_argument("-o", "--out", help="export to .pdf / .html / .csv / .xlsx instead of showing")
    ap.add_argument("-p", "--param", action="append", default=[], help="Name=Value")
    a = ap.parse_args()
    prm = dict(s.split("=", 1) for s in a.param if "=" in s)
    if a.out:
        rep = Report(a.report)
        rep.Parameters.update({k: _convert(v) for k, v in prm.items()})
        print(rep.Export(a.out))
    else:
        show(a.report, **{k: _convert(v) for k, v in prm.items()})
