"""REST Client (a Postman-like tab) + ``.http`` files compatible with the VS Code *REST Client* extension.

Panel: method, URL, Params / Headers / Body (none, JSON, form, raw) / Auth (Bearer, Basic) tabs, environment
selector, Send (Ctrl+Enter); the response shows status, time, size, pretty JSON, headers and raw text; History
(``.radide/rest-history.json`` in the project) and the project's saved requests (every ``*.http`` / ``*.rest``
file, grouped by file). *Save* appends the request to an ``.http`` file of the project.

``.http`` syntax (the REST Client subset that matters)::

    @host = http://127.0.0.1:8080          # file variables
    ### Get notes                           # "###" separates requests (the rest of the line is a title)
    # @name notes                           # request name -> {{notes.response.body.$.items[0].id}}
    GET {{host}}/api/notes?limit=10 HTTP/1.1
    Accept: application/json

    ###
    POST {{host}}/api/notes
    Content-Type: application/json

    {"text": "hello {{$guid}}"}

Variables: file variables, environments (``.vscode/settings.json`` ``rest-client.environmentVariables``,
``$shared`` + the selected one - the same place VS Code uses), named request results
(``{{name.response.body.$.path}}``, ``{{name.response.headers.Location}}``) and the system variables
``{{$guid}}``, ``{{$timestamp}}``, ``{{$randomInt 1 100}}``, ``{{$datetime iso8601}}``, ``{{$processEnv NAME}}``,
``{{$dotenv NAME}}``. A body line ``< ./file.json`` sends that file.

In the editor, every request line of an ``.http`` file gets a **Send Request** CodeLens (Monaco) and the
editor menu gets *Send Request* (Ctrl+Alt+R); the answer appears in the REST Client tab.
"""
from __future__ import annotations

import base64
import datetime as _dt
import http.client
import json
import os
import random
import re
import ssl
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit

METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
HTTP_EXT = (".http", ".rest")
HISTORY_FILE = ".radide/rest-history.json"
HISTORY_MAX = 100
SETTINGS_KEY = "rest-client.environmentVariables"
_REQ_LINE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|TRACE|CONNECT)\s+(\S.*?)(?:\s+HTTP/[\d.]+)?\s*$",
                       re.I)
_URL_ONLY = re.compile(r"^(https?://\S+|\{\{[^}]+\}\}\S*)\s*$", re.I)
_FILE_VAR = re.compile(r"^@([A-Za-z_][\w.-]*)\s*=\s*(.*)$")
_NAME = re.compile(r"^(?:#|//)\s*@name\s+([\w.-]+)\s*$")
_VAR = re.compile(r"\{\{\s*(.+?)\s*\}\}")


# ============================================================================ model
@dataclass
class HttpRequest:
    method: str = "GET"
    url: str = ""
    headers: list[tuple[str, str]] = field(default_factory=list)
    body: str = ""
    name: str = ""                 # "# @name x" (request variables)
    title: str = ""                # text after "###"
    line: int = 0                  # 0-based line of the request line in its file
    file: str = ""

    def header(self, name: str) -> str:
        for k, v in self.headers:
            if k.lower() == name.lower():
                return v
        return ""

    def label(self) -> str:
        return self.title or self.name or f"{self.method} {self.url}"

    def to_dict(self) -> dict:
        return {"method": self.method, "url": self.url, "headers": [list(h) for h in self.headers],
                "body": self.body, "name": self.name, "title": self.title}

    @classmethod
    def from_dict(cls, d: dict) -> "HttpRequest":
        return cls(d.get("method", "GET"), d.get("url", ""), [tuple(h) for h in d.get("headers", [])],
                   d.get("body", ""), d.get("name", ""), d.get("title", ""))


@dataclass
class HttpResponse:
    status: int = 0
    reason: str = ""
    headers: list[tuple[str, str]] = field(default_factory=list)
    body: bytes = b""
    elapsed_ms: float = 0.0
    url: str = ""
    error: str = ""
    http_version: str = "HTTP/1.1"
    redirects: list[str] = field(default_factory=list)

    def header(self, name: str) -> str:
        for k, v in self.headers:
            if k.lower() == name.lower():
                return v
        return ""

    @property
    def content_type(self) -> str:
        return self.header("Content-Type")

    def text(self) -> str:
        m = re.search(r"charset=([\w-]+)", self.content_type, re.I)
        try:
            return self.body.decode(m.group(1) if m else "utf-8", "replace")
        except LookupError:
            return self.body.decode("utf-8", "replace")

    def json(self):
        return json.loads(self.text())

    def pretty(self) -> str:
        """JSON bodies indented, everything else as text."""
        t = self.text()
        if "json" in self.content_type.lower() or t.lstrip()[:1] in ("{", "["):
            try:
                return json.dumps(json.loads(t), indent=2, ensure_ascii=False)
            except ValueError:
                pass
        return t


# ============================================================================ .http files
def parse_http(text: str, file: str = "") -> tuple[list[HttpRequest], dict[str, str]]:
    """Requests and file variables of an .http document."""
    lines = text.splitlines()
    variables: dict[str, str] = {}
    blocks: list[tuple[int, list[str], str]] = []
    start, title, cur = 0, "", []
    for i, ln in enumerate(lines):
        if ln.startswith("###"):
            blocks.append((start, cur, title))
            start, title, cur = i + 1, ln[3:].strip(), []
        else:
            cur.append(ln)
    blocks.append((start, cur, title))
    out = []
    for first, blines, title in blocks:
        req = _parse_block(first, blines, title, variables)
        if req is not None:
            req.file = file
            out.append(req)
    return out, variables


def _parse_block(first: int, blines: list[str], title: str, variables: dict) -> HttpRequest | None:
    i, n = 0, len(blines)
    name = ""
    req = None
    while i < n:                                     # comments, file variables, name - then the request line
        s = blines[i].strip()
        m = _FILE_VAR.match(s)
        if not s:
            i += 1
            continue
        if m:
            variables[m.group(1)] = m.group(2).strip()
            i += 1
            continue
        mn = _NAME.match(s)
        if mn:
            name = mn.group(1)
            i += 1
            continue
        if s.startswith("#") or s.startswith("//"):
            i += 1
            continue
        mr = _REQ_LINE.match(s)
        if mr:
            req = HttpRequest(mr.group(1).upper(), mr.group(2).strip(), line=first + i)
        elif _URL_ONLY.match(s):
            req = HttpRequest("GET", s.strip(), line=first + i)
        break
    if req is None:
        return None
    req.name, req.title = name, title
    i += 1
    while i < n and blines[i].strip()[:1] in ("?", "&") and blines[i].strip():   # multi-line query
        req.url += blines[i].strip()
        i += 1
    while i < n and blines[i].strip():               # headers
        s = blines[i].strip()
        if not (s.startswith("#") or s.startswith("//")) and ":" in s:
            k, v = s.split(":", 1)
            req.headers.append((k.strip(), v.strip()))
        i += 1
    body = blines[i + 1:] if i < n else []
    while body and not body[-1].strip():
        body.pop()
    req.body = "\n".join(body)
    return req


def to_http(req: HttpRequest) -> str:
    """One request as .http text (without the leading ###)."""
    out = []
    if req.name:
        out.append(f"# @name {req.name}")
    out.append(f"{req.method} {req.url}")
    out += [f"{k}: {v}" for k, v in req.headers]
    if req.body:
        out += ["", req.body]
    return "\n".join(out) + "\n"


def append_to_file(path: Path, req: HttpRequest) -> int:
    """Append *req* to an .http file; returns the 0-based line of its request line."""
    path = Path(path)
    old = path.read_text(encoding="utf-8") if path.is_file() else ""
    sep = "" if not old.strip() else ("\n" if old.endswith("\n") else "\n\n")
    block = f"### {req.title}\n" if req.title else "###\n"
    text = old + sep + block + to_http(req)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    reqs, _v = parse_http(text)
    return reqs[-1].line if reqs else 0


def request_at_line(text: str, line: int) -> HttpRequest | None:
    """The request whose block contains 0-based *line*."""
    reqs, _v = parse_http(text)
    lines = text.splitlines()
    for r in reversed(reqs):                         # the last request starting at/before the line
        start = r.line
        while start > 0 and not lines[start - 1].startswith("###"):
            start -= 1
        if start <= line:
            return r
    return reqs[0] if reqs else None


def http_files(folder) -> list[Path]:
    folder = Path(folder)
    skip = {"node_modules", ".git", ".radide", "vendor", "dist", "build", ".venv", "__pycache__"}
    out = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".radide")]
        out += [Path(root) / f for f in files if f.lower().endswith(HTTP_EXT)]
    return sorted(out)


# ============================================================================ environments
def _strip_jsonc(text: str) -> str:
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        else:
            out.append(c)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def _settings_path(folder) -> Path:
    return Path(folder) / ".vscode" / "settings.json"


def load_environments(folder) -> dict[str, dict[str, str]]:
    """{"$shared": {...}, "dev": {...}, ...} from .vscode/settings.json (VS Code REST Client format)."""
    p = _settings_path(folder)
    if not p.is_file():
        return {}
    try:
        data = json.loads(_strip_jsonc(p.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}
    envs = data.get(SETTINGS_KEY) or {}
    return {str(k): {str(a): str(b) for a, b in (v or {}).items()} for k, v in envs.items() if isinstance(v, dict)}


def save_environments(folder, envs: dict[str, dict[str, str]]) -> None:
    """Write the environments back into .vscode/settings.json, keeping its other settings."""
    p = _settings_path(folder)
    data = {}
    if p.is_file():
        try:
            data = json.loads(_strip_jsonc(p.read_text(encoding="utf-8")))
        except ValueError as e:
            raise ValueError(f"{p} is not valid JSON - fix it first ({e})") from e
    data[SETTINGS_KEY] = envs
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _dotenv(folder, name: str) -> str:
    p = Path(folder or ".") / ".env"
    try:
        for ln in p.read_text(encoding="utf-8").splitlines():
            if "=" in ln and not ln.lstrip().startswith("#"):
                k, v = ln.split("=", 1)
                if k.strip() == name:
                    return v.strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


# ============================================================================ variables
class Context:
    """Everything {{...}} can refer to."""

    def __init__(self, folder=None, file_vars=None, env: dict | None = None, results=None):
        self.folder = folder
        self.file_vars = dict(file_vars or {})
        self.env = dict(env or {})
        self.results: dict[str, tuple[HttpRequest, HttpResponse]] = results if results is not None else {}

    def lookup(self, expr: str, depth: int = 0) -> str | None:
        if expr.startswith("$"):
            return self._system(expr)
        if expr in self.file_vars:
            return self.resolve(self.file_vars[expr], depth + 1)
        if expr in self.env:
            return self.resolve(self.env[expr], depth + 1)
        if "." in expr:
            return self._request_var(expr)
        return None

    def resolve(self, text: str, depth: int = 0) -> str:
        if depth > 10 or "{{" not in text:
            return text

        def sub(m):
            v = self.lookup(m.group(1), depth)
            return m.group(0) if v is None else str(v)
        return _VAR.sub(sub, text)

    def unresolved(self, text: str) -> list[str]:
        return [m.group(1) for m in _VAR.finditer(self.resolve(text))]

    def _system(self, expr: str) -> str | None:
        parts = expr.split()
        name = parts[0]
        if name == "$guid":
            return str(uuid.uuid4())
        if name == "$timestamp":
            return str(int(time.time()))
        if name == "$randomInt":
            lo, hi = (int(parts[1]), int(parts[2])) if len(parts) >= 3 else (0, 1000)
            return str(random.randrange(lo, hi))
        if name in ("$datetime", "$localDatetime"):
            now = _dt.datetime.now(_dt.timezone.utc) if name == "$datetime" else _dt.datetime.now().astimezone()
            fmt = parts[1] if len(parts) > 1 else "iso8601"
            if fmt == "rfc1123":
                return now.astimezone(_dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
            if fmt == "iso8601":
                return now.isoformat(timespec="seconds")
            return now.strftime(fmt.strip("'\"").replace("YYYY", "%Y").replace("MM", "%m").replace("DD", "%d")
                                .replace("HH", "%H").replace("mm", "%M").replace("ss", "%S"))
        if name == "$processEnv" and len(parts) > 1:
            return os.environ.get(parts[1].lstrip("%"), "")
        if name == "$dotenv" and len(parts) > 1:
            return _dotenv(self.folder, parts[1])
        return None

    def _request_var(self, expr: str) -> str | None:
        name, _, rest = expr.partition(".")
        if name not in self.results:
            return None
        req, resp = self.results[name]
        kind, _, path = rest.partition(".")              # response.body.$.x / request.headers.X
        part, _, sel = path.partition(".")
        src = resp if kind == "response" else req if kind == "request" else None
        if src is None:
            return None
        if part == "headers":
            return src.header(sel)
        if part == "body":
            body = src.text() if isinstance(src, HttpResponse) else src.body
            if sel in ("", "*"):
                return body
            if sel.startswith("$"):
                try:
                    v = json_path(json.loads(body), sel)
                except ValueError:
                    return None
                return v if isinstance(v, str) else json.dumps(v)
        return None


def json_path(data, path: str):
    """A small JSONPath: $.a.b[0].c, $['a'], $.items[-1]."""
    tokens = re.findall(r"\.([\w$-]+)|\[(-?\d+)\]|\['([^']*)'\]|\[\"([^\"]*)\"\]", path[1:])
    cur = data
    for name, idx, q1, q2 in tokens:
        key = name or q1 or q2
        if idx:
            cur = cur[int(idx)]
        else:
            if isinstance(cur, list) and key.isdigit():
                cur = cur[int(key)]
            else:
                cur = cur[key]
    return cur


def prepare(req: HttpRequest, ctx: Context) -> HttpRequest:
    """A copy with every variable resolved and a "< file" body read."""
    body = ctx.resolve(req.body)
    if body.startswith("<") and "\n" not in body.strip():
        p = Path(body[1:].strip())
        base = Path(req.file).parent if req.file else Path(ctx.folder or ".")
        p = p if p.is_absolute() else base / p
        try:
            body = ctx.resolve(p.read_text(encoding="utf-8"))
        except OSError as e:
            raise ValueError(f"cannot read the body file {p}: {e}") from e
    return HttpRequest(req.method, ctx.resolve(req.url), [(k, ctx.resolve(v)) for k, v in req.headers], body,
                       req.name, req.title, req.line, req.file)


# ============================================================================ sending
def send(req: HttpRequest, timeout: float = 30.0, follow_redirects: bool = True, verify_tls: bool = True,
         cancel: threading.Event | None = None) -> HttpResponse:
    """Send an already prepared request (http.client; no proxies); never raises for HTTP/network errors."""
    url = req.url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    body = req.body.encode("utf-8") if req.body else None
    headers = {k: v for k, v in req.headers}
    lower = {k.lower() for k in headers}
    if "user-agent" not in lower:
        headers["User-Agent"] = "RAD-IDE-REST-Client/1.0"
    if "accept" not in lower:
        headers["Accept"] = "*/*"
    method = req.method.upper()
    resp = HttpResponse(url=url)
    t0 = time.perf_counter()
    for _hop in range(10):
        parts = urlsplit(url)
        try:
            if parts.scheme.lower() == "https":
                ctx = ssl.create_default_context()
                if not verify_tls:
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                conn = http.client.HTTPSConnection(parts.hostname, parts.port or 443, timeout=timeout, context=ctx)
            else:
                conn = http.client.HTTPConnection(parts.hostname, parts.port or 80, timeout=timeout)
            path = urlunsplit(("", "", quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~"), parts.query, ""))
            conn.request(method, path, body=body, headers=headers)
            r = conn.getresponse()
            data = b""
            while True:
                if cancel is not None and cancel.is_set():
                    conn.close()
                    resp.error = "cancelled"
                    return resp
                chunk = r.read(65536)
                if not chunk:
                    break
                data += chunk
            resp.status, resp.reason = r.status, r.reason
            resp.headers = list(r.getheaders())
            resp.http_version = "HTTP/1.0" if r.version == 10 else "HTTP/1.1"
            resp.body = data
            conn.close()
        except (OSError, http.client.HTTPException, ValueError) as e:
            resp.error = f"{type(e).__name__}: {e}"
            break
        loc = resp.header("Location")
        if follow_redirects and resp.status in (301, 302, 303, 307, 308) and loc:
            resp.redirects.append(f"{resp.status} {url}")
            url = urljoin(url, loc)
            if resp.status == 303 or (resp.status in (301, 302) and method == "POST"):
                method, body = "GET", None
                headers = {k: v for k, v in headers.items() if k.lower() not in ("content-type", "content-length")}
            continue
        break
    resp.url = url
    resp.elapsed_ms = (time.perf_counter() - t0) * 1000
    return resp


def basic_auth(value: str) -> str:
    """"Basic user:password" / "Basic user password" (REST Client syntax) -> "Basic <base64>"."""
    if not value.startswith("Basic "):
        return value
    cred = value[6:].strip()
    parts = cred.split()
    if ":" not in cred and len(parts) == 2:
        cred = f"{parts[0]}:{parts[1]}"
    elif ":" not in cred:
        return value                                   # already base64
    return "Basic " + base64.b64encode(cred.encode("utf-8")).decode()


def curl_command(req: HttpRequest) -> str:
    q = (lambda s: '"' + s.replace('"', '\\"') + '"')
    out = [f"curl -X {req.method} {q(req.url)}"]
    out += [f"-H {q(f'{k}: {v}')}" for k, v in req.headers]
    if req.body:
        out.append(f"--data-raw {q(req.body)}")
    return " ^\n  ".join(out)


# ============================================================================ history
def load_history(folder) -> list[dict]:
    p = Path(folder) / HISTORY_FILE
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def add_history(folder, req: HttpRequest, resp: HttpResponse) -> list[dict]:
    items = load_history(folder)
    items.insert(0, {"request": req.to_dict(), "status": resp.status, "ms": round(resp.elapsed_ms, 1),
                     "size": len(resp.body), "time": _dt.datetime.now().isoformat(timespec="seconds"),
                     "error": resp.error})
    del items[HISTORY_MAX:]
    p = Path(folder) / HISTORY_FILE
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return items


def human_size(n: int) -> str:
    return f"{n} B" if n < 1024 else f"{n / 1024:.1f} KB" if n < 1024 * 1024 else f"{n / 1048576:.2f} MB"


# ============================================================================ UI
def _qt():
    from PyQt6 import QtCore, QtGui, QtWidgets
    return QtCore, QtGui, QtWidgets


def build_panel_class():
    QtCore, QtGui, W = _qt()
    from PyQt6.QtCore import Qt, pyqtSignal
    from .. import theme

    class _Relay(QtCore.QObject):
        done = pyqtSignal(object, object)

    class KeyValueTable(W.QTableWidget):
        """Two columns with a check box per row; an empty row is always kept at the end."""
        edited = pyqtSignal()

        def __init__(self, key="Name", value="Value", parent=None):
            super().__init__(0, 2, parent)
            self.setHorizontalHeaderLabels([key, value])
            self.horizontalHeader().setStretchLastSection(True)
            self.horizontalHeader().resizeSection(0, 200)
            self.verticalHeader().setVisible(False)
            self._busy = False
            self.itemChanged.connect(self._changed)
            self._ensure_blank()

        def _ensure_blank(self):
            n = self.rowCount()
            if n == 0 or any((self.item(n - 1, c) and self.item(n - 1, c).text()) for c in (0, 1)):
                self._busy = True
                self.insertRow(n)
                it = W.QTableWidgetItem("")
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(Qt.CheckState.Checked)
                self.setItem(n, 0, it)
                self.setItem(n, 1, W.QTableWidgetItem(""))
                self._busy = False

        def _changed(self, _it):
            if not self._busy:
                self._ensure_blank()
                self.edited.emit()

        def pairs(self) -> list[tuple[str, str]]:
            out = []
            for r in range(self.rowCount()):
                k, v = self.item(r, 0), self.item(r, 1)
                if k and k.text().strip() and k.checkState() == Qt.CheckState.Checked:
                    out.append((k.text().strip(), v.text() if v else ""))
            return out

        def set_pairs(self, pairs):
            self._busy = True
            self.setRowCount(0)
            for k, v in pairs:
                r = self.rowCount()
                self.insertRow(r)
                it = W.QTableWidgetItem(k)
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(Qt.CheckState.Checked)
                self.setItem(r, 0, it)
                self.setItem(r, 1, W.QTableWidgetItem(v))
            self._busy = False
            self._ensure_blank()

    class EnvironmentDialog(W.QDialog):
        def __init__(self, folder, parent=None):
            super().__init__(parent)
            self.setWindowTitle("REST Client Environments")
            self.resize(640, 420)
            self.folder = folder
            self.envs = load_environments(folder) or {"$shared": {}, "local": {"host": "http://127.0.0.1:8080"}}
            lay = W.QHBoxLayout(self)
            left = W.QVBoxLayout()
            self.list = W.QListWidget()
            self.list.addItems(list(self.envs))
            left.addWidget(self.list, 1)
            row = W.QHBoxLayout()
            b_add, b_del = W.QPushButton("Add..."), W.QPushButton("Remove")
            row.addWidget(b_add)
            row.addWidget(b_del)
            left.addLayout(row)
            lay.addLayout(left, 1)
            right = W.QVBoxLayout()
            hint = W.QLabel("<b>$shared</b> variables apply to every environment. Use them as <code>{{name}}</code>."
                            " Stored in .vscode/settings.json (VS Code REST Client format).")
            hint.setWordWrap(True)
            theme.role(hint, "muted")
            right.addWidget(hint)
            self.table = KeyValueTable("Variable", "Value")
            right.addWidget(self.table, 1)
            box = W.QDialogButtonBox(W.QDialogButtonBox.StandardButton.Save | W.QDialogButtonBox.StandardButton.Cancel)
            box.accepted.connect(self._save)
            box.rejected.connect(self.reject)
            right.addWidget(box)
            lay.addLayout(right, 2)
            self._cur = None
            self.list.currentTextChanged.connect(self._select)
            b_add.clicked.connect(self._add)
            b_del.clicked.connect(self._remove)
            self.list.setCurrentRow(0)

        def _store(self):
            if self._cur is not None and self._cur in self.envs:
                self.envs[self._cur] = dict(self.table.pairs())

        def _select(self, name):
            self._store()
            self._cur = name
            self.table.set_pairs(list(self.envs.get(name, {}).items()))

        def _add(self):
            name, ok = W.QInputDialog.getText(self, "New environment", "Name (e.g. local, staging, production):")
            name = name.strip()
            if ok and name and name not in self.envs:
                self._store()
                base = {k: "" for k in self.envs.get(self._cur or "", {})}
                self.envs[name] = base
                self.list.addItem(name)
                self.list.setCurrentRow(self.list.count() - 1)

        def _remove(self):
            it = self.list.currentItem()
            if it is not None and it.text() != "$shared":
                self.envs.pop(it.text(), None)
                self._cur = None
                self.list.takeItem(self.list.row(it))

        def _save(self):
            self._store()
            try:
                save_environments(self.folder, self.envs)
            except (OSError, ValueError) as e:
                W.QMessageBox.warning(self, "Environments", str(e))
                return
            self.accept()

    class RestClientPanel(W.QWidget):
        """The REST Client tab."""
        sent = pyqtSignal(object, object)          # HttpRequest (prepared), HttpResponse

        def __init__(self, win=None, folder=None, parent=None):
            super().__init__(parent)
            self.win = win
            self._folder = Path(folder) if folder else None
            self.results: dict[str, tuple[HttpRequest, HttpResponse]] = {}
            self.file_vars: dict[str, str] = {}
            self.source: HttpRequest | None = None      # request loaded from an .http file
            self.last: tuple[HttpRequest, HttpResponse] | None = None
            self._thread = None
            self._cancel = None
            self._relay = _Relay(self)
            self._relay.done.connect(self._done)
            self._build()
            self.refresh()

        # ------------------------------------------------------------ layout
        def _build(self):
            root = W.QVBoxLayout(self)
            root.setContentsMargins(4, 4, 4, 4)
            top = W.QHBoxLayout()
            self.method = W.QComboBox()
            self.method.addItems(METHODS)
            self.method.setEditable(True)
            self.method.setMinimumWidth(90)
            self.url = W.QLineEdit()
            self.url.setPlaceholderText("https://api.example.com/items   or   {{host}}/api/items")
            self.url.returnPressed.connect(self.send_current)
            self.send_btn = W.QPushButton("Send")
            self.send_btn.setDefault(True)
            self.send_btn.setToolTip("Send the request (Ctrl+Enter)")
            self.send_btn.clicked.connect(self.send_current)
            self.env = W.QComboBox()
            self.env.setToolTip("Environment: variables from .vscode/settings.json (rest-client.environmentVariables)")
            self.env.setMinimumWidth(110)
            env_btn = W.QToolButton()
            env_btn.setText("...")
            env_btn.setToolTip("Edit environments")
            env_btn.clicked.connect(self.edit_environments)
            save_btn = W.QToolButton()
            save_btn.setText("Save")
            save_btn.setToolTip("Save this request into an .http file of the project")
            save_btn.clicked.connect(self.save_request)
            more = W.QToolButton()
            more.setText("More")
            more.setPopupMode(W.QToolButton.ToolButtonPopupMode.InstantPopup)
            m = W.QMenu(more)
            m.addAction("New request", self.new_request)
            m.addAction("Copy as cURL", self.copy_curl)
            m.addAction("Copy as .http", self.copy_http)
            m.addAction("Paste .http / cURL request", self.paste_request)
            m.addSeparator()
            self.a_follow = m.addAction("Follow redirects")
            self.a_follow.setCheckable(True)
            self.a_follow.setChecked(True)
            self.a_verify = m.addAction("Verify TLS certificates")
            self.a_verify.setCheckable(True)
            self.a_verify.setChecked(True)
            m.addAction("Clear history", self.clear_history)
            more.setMenu(m)
            for w in (self.method, self.url, self.send_btn, W.QLabel("Env:"), self.env, env_btn, save_btn, more):
                top.addWidget(w, 1 if w is self.url else 0)
            root.addLayout(top)
            QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Return"), self, activated=self.send_current)

            split = W.QSplitter(Qt.Orientation.Horizontal)
            # left: saved requests + history
            left = W.QTabWidget()
            self.saved = W.QTreeWidget()
            self.saved.setHeaderHidden(True)
            self.saved.itemActivated.connect(self._open_saved)
            self.saved.itemClicked.connect(self._open_saved)
            self.saved.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.saved.customContextMenuRequested.connect(self._saved_menu)
            left.addTab(self.saved, "Collections")
            self.history = W.QListWidget()
            self.history.itemActivated.connect(self._open_history)
            self.history.itemClicked.connect(self._open_history)
            left.addTab(self.history, "History")
            split.addWidget(left)

            right = W.QSplitter(Qt.Orientation.Vertical)
            self.req_tabs = W.QTabWidget()
            self.params = KeyValueTable("Parameter", "Value")
            self.params.edited.connect(self._params_to_url)
            self.url.textEdited.connect(self._url_to_params)
            self.headers = KeyValueTable("Header", "Value")
            body = W.QWidget()
            bl = W.QVBoxLayout(body)
            bl.setContentsMargins(0, 0, 0, 0)
            brow = W.QHBoxLayout()
            self.body_kind = W.QComboBox()
            self.body_kind.addItems(["none", "JSON", "form (x-www-form-urlencoded)", "raw text", "XML"])
            self.body_kind.currentIndexChanged.connect(self._body_kind_changed)
            fmt = W.QPushButton("Beautify")
            fmt.clicked.connect(self._beautify_body)
            brow.addWidget(W.QLabel("Body:"))
            brow.addWidget(self.body_kind)
            brow.addWidget(fmt)
            brow.addStretch(1)
            bl.addLayout(brow)
            self.body_stack = W.QStackedWidget()
            self.body = W.QPlainTextEdit()
            self.body.setFont(QtGui.QFont("Consolas", 10))
            self.body.setPlaceholderText('{"name": "value"}')
            self.form = KeyValueTable("Field", "Value")
            self.body_stack.addWidget(self.body)
            self.body_stack.addWidget(self.form)
            bl.addWidget(self.body_stack, 1)
            auth = W.QWidget()
            al = W.QFormLayout(auth)
            self.auth_kind = W.QComboBox()
            self.auth_kind.addItems(["No auth", "Bearer token", "Basic (user / password)"])
            self.auth_token = W.QLineEdit()
            self.auth_token.setPlaceholderText("{{token}}")
            self.auth_user = W.QLineEdit()
            self.auth_pass = W.QLineEdit()
            self.auth_pass.setEchoMode(W.QLineEdit.EchoMode.Password)
            al.addRow("Type:", self.auth_kind)
            al.addRow("Token:", self.auth_token)
            al.addRow("User:", self.auth_user)
            al.addRow("Password:", self.auth_pass)
            self.req_tabs.addTab(self.params, "Params")
            self.req_tabs.addTab(self.headers, "Headers")
            self.req_tabs.addTab(body, "Body")
            self.req_tabs.addTab(auth, "Auth")
            right.addWidget(self.req_tabs)

            resp = W.QWidget()
            rl = W.QVBoxLayout(resp)
            rl.setContentsMargins(0, 0, 0, 0)
            srow = W.QHBoxLayout()
            self.status = W.QLabel("No response yet - press Send")
            theme.role(self.status, "muted")
            self.timing = W.QLabel("")
            theme.role(self.timing, "muted")
            srow.addWidget(self.status)
            srow.addStretch(1)
            srow.addWidget(self.timing)
            rl.addLayout(srow)
            self.resp_tabs = W.QTabWidget()
            self.resp_body = W.QPlainTextEdit()
            self.resp_body.setReadOnly(True)
            self.resp_body.setFont(QtGui.QFont("Consolas", 10))
            self.resp_headers = W.QTableWidget(0, 2)
            self.resp_headers.setHorizontalHeaderLabels(["Header", "Value"])
            self.resp_headers.horizontalHeader().setStretchLastSection(True)
            self.resp_headers.verticalHeader().setVisible(False)
            self.resp_headers.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.resp_raw = W.QPlainTextEdit()
            self.resp_raw.setReadOnly(True)
            self.resp_raw.setFont(QtGui.QFont("Consolas", 10))
            self.resp_tabs.addTab(self.resp_body, "Body")
            self.resp_tabs.addTab(self.resp_headers, "Headers")
            self.resp_tabs.addTab(self.resp_raw, "Raw")
            rl.addWidget(self.resp_tabs, 1)
            right.addWidget(resp)
            right.setSizes([240, 360])
            split.addWidget(right)
            split.setSizes([220, 780])
            root.addWidget(split, 1)

        # ------------------------------------------------------------ project data
        def folder(self) -> Path | None:
            if self._folder is not None:
                return self._folder
            p = getattr(self.win, "project", None) if self.win is not None else None
            return Path(p.folder) if p is not None else None

        def set_folder(self, folder):
            self._folder = Path(folder) if folder else None
            self.refresh()

        def environments(self) -> dict[str, dict[str, str]]:
            f = self.folder()
            return load_environments(f) if f else {}

        def refresh(self):
            envs = self.environments()
            cur = self.env.currentText()
            self.env.blockSignals(True)
            self.env.clear()
            self.env.addItem("No Environment")
            self.env.addItems([e for e in envs if e != "$shared"])
            i = self.env.findText(cur)
            self.env.setCurrentIndex(i if i >= 0 else (1 if self.env.count() > 1 else 0))
            self.env.blockSignals(False)
            self.saved.clear()
            f = self.folder()
            if f is not None:
                for p in http_files(f):
                    try:
                        reqs, _v = parse_http(p.read_text(encoding="utf-8"), str(p))
                    except OSError:
                        continue
                    top = W.QTreeWidgetItem(self.saved, [str(p.relative_to(f))])
                    top.setData(0, Qt.ItemDataRole.UserRole, ("file", str(p)))
                    for r in reqs:
                        it = W.QTreeWidgetItem(top, [f"{r.method}  {r.label()}"])
                        it.setToolTip(0, f"{r.method} {r.url}")
                        it.setData(0, Qt.ItemDataRole.UserRole, ("req", str(p), r.line))
                    top.setExpanded(True)
            self._fill_history(load_history(f) if f else [])

        def _fill_history(self, items):
            self.history.clear()
            for h in items:
                r = h.get("request", {})
                st = h.get("status") or ("ERR" if h.get("error") else "")
                it = W.QListWidgetItem(f"{st}  {r.get('method', '')} {r.get('url', '')}")
                it.setToolTip(f"{h.get('time', '')}  {h.get('ms', '')} ms  {human_size(h.get('size', 0))}")
                it.setData(Qt.ItemDataRole.UserRole, r)
                self.history.addItem(it)

        def context(self) -> Context:
            envs = self.environments()
            env = dict(envs.get("$shared", {}))
            name = self.env.currentText()
            if name in envs:
                env.update(envs[name])
            return Context(self.folder(), self.file_vars, env, self.results)

        # ------------------------------------------------------------ editor <-> request
        def request(self) -> HttpRequest:
            """The request the editor fields describe (variables not resolved)."""
            headers = list(self.headers.pairs())
            kind = self.body_kind.currentIndex()
            body = ""
            if kind == 2:
                body = urlencode(self.form.pairs())
                if not any(k.lower() == "content-type" for k, _ in headers):
                    headers.append(("Content-Type", "application/x-www-form-urlencoded"))
            elif kind in (1, 3, 4):
                body = self.body.toPlainText()
                ctype = {1: "application/json", 3: "text/plain", 4: "application/xml"}[kind]
                if body and not any(k.lower() == "content-type" for k, _ in headers):
                    headers.append(("Content-Type", ctype))
            a = self.auth_kind.currentIndex()
            if a == 1 and self.auth_token.text().strip():
                headers.append(("Authorization", f"Bearer {self.auth_token.text().strip()}"))
            elif a == 2 and self.auth_user.text():
                headers.append(("Authorization", f"Basic {self.auth_user.text()}:{self.auth_pass.text()}"))
            src = self.source
            return HttpRequest(self.method.currentText().strip().upper() or "GET", self.url.text().strip(), headers,
                               body, src.name if src else "", src.title if src else "", src.line if src else 0,
                               src.file if src else "")

        def load_request(self, req: HttpRequest, file_vars: dict | None = None):
            self.source = req
            if file_vars is not None:
                self.file_vars = dict(file_vars)
            self.method.setCurrentText(req.method)
            self.url.setText(req.url)
            self._url_to_params()
            ctype = req.header("Content-Type").lower()
            heads = [(k, v) for k, v in req.headers]
            self.auth_kind.setCurrentIndex(0)
            for k, v in list(heads):
                if k.lower() == "authorization" and v.lower().startswith("bearer "):
                    self.auth_kind.setCurrentIndex(1)
                    self.auth_token.setText(v[7:].strip())
                    heads.remove((k, v))
            self.headers.set_pairs(heads)
            if not req.body:
                self.body_kind.setCurrentIndex(0)
                self.body.setPlainText("")
            elif "x-www-form-urlencoded" in ctype:
                self.body_kind.setCurrentIndex(2)
                self.form.set_pairs(parse_qsl(req.body, keep_blank_values=True))
            else:
                self.body_kind.setCurrentIndex(1 if "json" in ctype or req.body.lstrip()[:1] in "{[" else
                                               4 if "xml" in ctype else 3)
                self.body.setPlainText(req.body)
            self.req_tabs.setCurrentIndex(2 if req.body else 1 if heads else 0)

        def new_request(self):
            self.load_request(HttpRequest("GET", ""))
            self.source = None
            self.url.setFocus()

        def _body_kind_changed(self, i):
            self.body_stack.setCurrentIndex(1 if i == 2 else 0)
            self.body.setEnabled(i != 0)

        def _beautify_body(self):
            try:
                self.body.setPlainText(json.dumps(json.loads(self.body.toPlainText()), indent=2, ensure_ascii=False))
            except ValueError as e:
                self._status(f"Body is not valid JSON: {e}", "error")

        def _url_to_params(self, *_):
            parts = urlsplit(self.url.text())
            self.params.blockSignals(True)
            self.params.set_pairs(parse_qsl(parts.query, keep_blank_values=True))
            self.params.blockSignals(False)

        def _params_to_url(self):
            text = self.url.text()
            base = text.split("?", 1)[0]
            q = "&".join(f"{k}={v}" if v != "" else k for k, v in self.params.pairs())
            self.url.setText(base + ("?" + q if q else ""))

        # ------------------------------------------------------------ sending
        def send_current(self):
            self.send_request(self.request())

        def send_request(self, req: HttpRequest, file_vars: dict | None = None):
            if self._thread is not None and self._thread.is_alive():
                self._cancel.set()
                return
            if file_vars is not None:
                self.file_vars = dict(file_vars)
            ctx = self.context()
            try:
                ready = prepare(req, ctx)
            except ValueError as e:
                self._status(str(e), "error")
                return
            # "Basic user:password" (Auth tab, VS Code REST Client syntax) -> base64
            ready.headers = [(k, basic_auth(v)) if k.lower() == "authorization" else (k, v)
                             for k, v in ready.headers]
            missing = ctx.unresolved(ready.url + " " + " ".join(v for _k, v in ready.headers))
            if not ready.url:
                self._status("Type a URL first", "error")
                return
            if missing:
                self._status("Unknown variable(s): " + ", ".join(sorted(set(missing))) +
                             " - define them as @name = value in the .http file or in an environment", "error")
                return
            self._status(f"Sending {ready.method} {ready.url} ...", "muted")
            self.send_btn.setText("Cancel")
            self._cancel = threading.Event()
            follow, verify, cancel = self.a_follow.isChecked(), self.a_verify.isChecked(), self._cancel

            def work():
                r = send(ready, follow_redirects=follow, verify_tls=verify, cancel=cancel)
                self._relay.done.emit((req, ready), r)
            self._thread = threading.Thread(target=work, daemon=True, name="radide-rest")
            self._thread.start()

        def _done(self, pair, resp: HttpResponse):
            src, ready = pair
            self.send_btn.setText("Send")
            self._thread = None
            self.last = (ready, resp)
            if src.name:
                self.results[src.name] = (ready, resp)
            self.show_response(ready, resp)
            f = self.folder()
            if f is not None and resp.error != "cancelled":
                self._fill_history(add_history(f, ready, resp))
            self.sent.emit(ready, resp)

        def wait(self, timeout: float = 30.0) -> bool:
            """Tests: process events until the running request ends."""
            end = time.time() + timeout
            app = W.QApplication.instance()
            while self._thread is not None and time.time() < end:
                app.processEvents()
                time.sleep(0.01)
            app.processEvents()
            return self._thread is None

        def _status(self, text, role="muted"):
            self.status.setText(text)
            theme.role(self.status, role)

        def show_response(self, req: HttpRequest, resp: HttpResponse):
            if resp.error:
                self._status(f"Error: {resp.error}", "error")
                self.timing.setText(f"{resp.elapsed_ms:.0f} ms")
                self.resp_body.setPlainText(resp.error)
                self.resp_raw.setPlainText(resp.error)
                self.resp_headers.setRowCount(0)
                return
            ok = 200 <= resp.status < 400
            self._status(f"{resp.status} {resp.reason}", "success" if ok else "error")
            redirect = f"   ({len(resp.redirects)} redirect{'s' if len(resp.redirects) > 1 else ''})" \
                if resp.redirects else ""
            self.timing.setText(f"Time: {resp.elapsed_ms:.0f} ms   Size: {human_size(len(resp.body))}{redirect}")
            ctype = resp.content_type.lower()
            if ctype.startswith(("image/", "audio/", "video/", "application/octet-stream", "application/pdf")):
                self.resp_body.setPlainText(f"({ctype}, {human_size(len(resp.body))} - binary content not shown)")
            else:
                self.resp_body.setPlainText(resp.pretty())
            self.resp_headers.setRowCount(0)
            for k, v in resp.headers:
                r = self.resp_headers.rowCount()
                self.resp_headers.insertRow(r)
                self.resp_headers.setItem(r, 0, W.QTableWidgetItem(k))
                self.resp_headers.setItem(r, 1, W.QTableWidgetItem(v))
            raw = [f"{req.method} {req.url}"] + [f"{k}: {v}" for k, v in req.headers]
            if req.body:
                raw += ["", req.body]
            raw += ["", "-" * 60, f"{resp.http_version} {resp.status} {resp.reason}"]
            raw += [f"{k}: {v}" for k, v in resp.headers]
            raw += ["", resp.text()[:200000]]
            self.resp_raw.setPlainText("\n".join(raw))

        # ------------------------------------------------------------ saved / history
        def _open_saved(self, it, _col=0):
            data = it.data(0, Qt.ItemDataRole.UserRole)
            if not data or data[0] != "req":
                return
            p = Path(data[1])
            try:
                reqs, fvars = parse_http(p.read_text(encoding="utf-8"), str(p))
            except OSError:
                return
            r = next((x for x in reqs if x.line == data[2]), None)
            if r is not None:
                self.load_request(r, fvars)

        def _saved_menu(self, pos):
            it = self.saved.itemAt(pos)
            if it is None:
                return
            data = it.data(0, Qt.ItemDataRole.UserRole)
            m = W.QMenu(self)
            if data[0] == "req":
                m.addAction("Send", lambda: (self._open_saved(it), self.send_current()))
            if self.win is not None and hasattr(self.win, "open_file"):
                line = data[2] if data[0] == "req" else 0
                m.addAction("Open .http file", lambda: self.win.open_file(Path(data[1]), line + 1))
            m.addAction("Refresh", self.refresh)
            m.exec(self.saved.viewport().mapToGlobal(pos))

        def _open_history(self, it):
            d = it.data(Qt.ItemDataRole.UserRole)
            if d:
                self.load_request(HttpRequest.from_dict(d))
                self.source = None

        def clear_history(self):
            f = self.folder()
            if f is not None:
                try:
                    (f / HISTORY_FILE).unlink()
                except OSError:
                    pass
            self.history.clear()

        def save_request(self, path=None, title=None):
            f = self.folder()
            if f is None:
                self._status("Open a project first - requests are saved in its .http files", "error")
                return None
            req = self.request()
            if path is None:
                files = [str(p.relative_to(f)) for p in http_files(f)] or ["requests.http"]
                if "requests.http" not in files:
                    files.append("requests.http")
                name, ok = W.QInputDialog.getItem(self, "Save Request", ".http file (new name = new file):",
                                                  files, 0, True)
                if not ok or not name.strip():
                    return None
                path = f / (name.strip() if name.strip().lower().endswith(HTTP_EXT) else name.strip() + ".http")
                if title is None:
                    title, ok = W.QInputDialog.getText(self, "Save Request", "Title (optional):",
                                                       text=req.title or f"{req.method} {urlsplit(req.url).path}")
                    if not ok:
                        return None
            req.title = (title or "").strip()
            line = append_to_file(Path(path), req)
            self.source = HttpRequest(req.method, req.url, req.headers, req.body, req.name, req.title, line,
                                      str(path))
            self.refresh()
            self._status(f"Saved to {Path(path).name}", "success")
            return Path(path)

        def edit_environments(self):
            f = self.folder()
            if f is None:
                self._status("Open a project first", "error")
                return
            if EnvironmentDialog(f, self).exec():
                self.refresh()

        def copy_curl(self):
            W.QApplication.clipboard().setText(curl_command(prepare(self.request(), self.context())))

        def copy_http(self):
            W.QApplication.clipboard().setText(to_http(self.request()))

        def paste_request(self):
            text = W.QApplication.clipboard().text()
            req = parse_curl(text) if text.strip().lower().startswith("curl") else None
            if req is None:
                reqs, fvars = parse_http(text)
                req = reqs[0] if reqs else None
                self.file_vars.update(fvars)
            if req is None:
                self._status("The clipboard holds no request", "error")
                return
            self.load_request(req)
            self.source = None

    return RestClientPanel, EnvironmentDialog


def parse_curl(text: str) -> HttpRequest | None:
    """A cURL command (bash or cmd style) -> request."""
    import shlex
    t = re.sub(r"[\\^]\r?\n", " ", text.strip())
    try:
        argv = shlex.split(t, posix=True)
    except ValueError:
        return None
    if not argv or argv[0].lower() not in ("curl", "curl.exe"):
        return None
    req = HttpRequest("", "")
    i = 1
    while i < len(argv):
        a = argv[i]
        nxt = argv[i + 1] if i + 1 < len(argv) else ""
        if a in ("-X", "--request"):
            req.method, i = nxt.upper(), i + 2
        elif a in ("-H", "--header"):
            if ":" in nxt:
                k, v = nxt.split(":", 1)
                req.headers.append((k.strip(), v.strip()))
            i += 2
        elif a in ("-d", "--data", "--data-raw", "--data-binary", "--json"):
            req.body = nxt
            if a == "--json" and not req.header("Content-Type"):
                req.headers.append(("Content-Type", "application/json"))
            i += 2
        elif a in ("-u", "--user"):
            req.headers.append(("Authorization", "Basic " + base64.b64encode(nxt.encode()).decode()))
            i += 2
        elif a.startswith("-"):
            i += 2 if a in ("-o", "--output", "-A", "--user-agent", "-e", "--referer", "-m", "--max-time") else 1
        else:
            req.url, i = a, i + 1
    req.method = req.method or ("POST" if req.body else "GET")
    return req if req.url else None


_PANEL = None


def panel_class():
    global _PANEL
    if _PANEL is None:
        _PANEL = build_panel_class()
    return _PANEL[0]


def environment_dialog_class():
    panel_class()
    return _PANEL[1]


__all__ = ["Context", "HttpRequest", "HttpResponse", "add_history", "append_to_file", "curl_command", "http_files",
           "json_path", "load_environments", "load_history", "panel_class", "parse_curl", "parse_http", "prepare",
           "request_at_line", "save_environments", "send", "to_http"]
