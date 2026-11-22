"""Development web server for website projects (docs/CONTRACTS.md 8.1) - like WebMatrix's IIS Express.

``DevServer(project_folder, plugin)`` listens on ``http://127.0.0.1:<port>/`` (``web.port``, 0 = a free port)
with a small threaded front server written in Python that

- serves static sites itself (``static-web``), or forwards every request to the site's own server
  (``php -S 127.0.0.1:<backend> -t <root>`` for ``php-web``, ``node <start>`` with ``PORT`` for ``node-web``),
  passing cookies, redirects, uploads, streaming responses and WebSocket upgrades through;
- measures each request and emits ``request(dict)`` with method, path, status, ms, size, type, time, url
  (the WebMatrix *Requests* view) plus the details: ``id``, ``remote``, ``req_headers`` / ``resp_headers``
  ([[name, value], ...]), ``req_body`` (text, at most MAX_BODY bytes; ``req_body_size`` = the real size,
  ``req_body_binary``), ``resp_preview`` (text responses, at most MAX_PREVIEW bytes) and ``reason``;
  the last MAX_REQUESTS of them are kept in ``DevServer.requests``;
- **live reload**: a file watcher bumps a version after every change (or ``notify_change()`` / ``check_now()``
  after a save; only source / asset files, never the files the site writes itself - data/, sessions, logs,
  SQLite databases, or anything written while a request was running); HTML pages get
  ``<script src="/__radide/livereload.js">`` injected, which long-polls ``/__radide/poll`` and reloads
  the page (CSS-only changes swap the stylesheets without a reload); bursts of changes are debounced;
- Node sites are restarted when their server code (.js/.json outside public/static) changes.

Signals: request(dict), log(str), reloaded(int), started(str url), stopped(), backendReady(), backendExited(int).
"""
from __future__ import annotations

import atexit
import collections
import http.client
import json
import mimetypes
import os
import re
import socket
import subprocess
import threading
import time
import weakref
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

from PyQt6.QtCore import QObject, pyqtSignal

from .project import HEAVY_DIRS, HIDDEN_DIRS, INDEX_FILES, web_config

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
              "transfer-encoding", "upgrade", "proxy-connection"}
MIME = {".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
        ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", ".gif": "image/gif", ".ico": "image/x-icon", ".webp": "image/webp",
        ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf", ".txt": "text/plain; charset=utf-8",
        ".xml": "application/xml", ".map": "application/json", ".wasm": "application/wasm",
        ".mp4": "video/mp4", ".webm": "video/webm", ".mp3": "audio/mpeg", ".pdf": "application/pdf"}
PHP_ACCESS = re.compile(r"^\[[^\]]+\]\s+(?:\[?[\d.:a-fA-F]+\]?):\d+\s+(?:Accepted|Closing|Closed without sending|\[\d{3}\]:\s)")
PHP_STARTED = re.compile(r"Development Server \(http://[^)]*\) started")
MAX_BODY = 64 * 1024           # request body kept for the Requests details (per request)
MAX_PREVIEW = 16 * 1024        # response body preview kept per request
MAX_REQUESTS = 500             # requests kept in DevServer.requests
TEXT_TYPES = ("text/", "json", "javascript", "xml", "svg", "x-www-form-urlencoded", "csv", "yaml", "graphql")
SERVER_JS_EXT = {".js", ".cjs", ".mjs", ".ts", ".json"}
CLIENT_DIRS = {"public", "static", "assets", "www", "wwwroot", "client", "views", "templates"}
# live reload: only edits of these (source / asset) files reload the Preview ...
WATCH_EXT = {".php", ".phtml", ".inc", ".html", ".htm", ".shtml", ".xhtml", ".css", ".scss", ".sass", ".less",
             ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".json", ".xml", ".svg", ".map",
             ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".bmp", ".ico", ".woff", ".woff2", ".ttf",
             ".otf", ".eot", ".twig", ".tpl", ".mustache", ".hbs", ".ejs", ".pug", ".njk", ".liquid", ".yml",
             ".yaml", ".mp4", ".webm", ".mp3", ".ogg", ".wav", ".pdf", ".wasm"}
WATCH_NAMES = {".htaccess", ".user.ini", "web.config", ".env"}
# ... and never files in folders a running site writes itself (SQLite databases, PHP sessions, logs, caches,
# uploads) - otherwise every request that touches the session would reload the page, which requests the page
# again, which writes the session again... (an endless reload loop)
RUNTIME_DIRS = {"data", "db", "database", "sessions", "session", "logs", "log", "cache", "tmp", "temp",
                "storage", "uploads", "upload", "var", "writable", "coverage"}
RUNTIME_SUFFIXES = (".sqlite", ".sqlite3", ".db", ".db3", ".sqlite-journal", ".sqlite-wal", ".sqlite-shm",
                    "-journal", "-wal", "-shm", ".log", ".lock", ".pid", ".tmp", ".swp", "~", ".bak")
REQUEST_SLACK = 0.5            # a file written up to this long after a backend request is "written by the site"
DEBOUNCE = 0.25                # coalesce a burst of changes (Save All, git checkout) into one reload

LIVERELOAD_JS = r"""(function () {
  if (window.__radideLiveReload) return; window.__radideLiveReload = true;
  var s = document.currentScript, m = s && /[?&]v=(\d+)/.exec(s.src), v = m ? parseInt(m[1], 10) : 0;
  function css() {
    document.querySelectorAll('link[rel~="stylesheet"]').forEach(function (l) {
      try { var u = new URL(l.href); u.searchParams.set('_radide', Date.now()); l.href = u.toString(); } catch (e) {}
    });
  }
  function poll() {
    fetch('/__radide/poll?v=' + v, {cache: 'no-store'}).then(function (r) { return r.text(); }).then(function (t) {
      var p = t.split(' '), n = parseInt(p[0], 10);
      if (isNaN(n)) { setTimeout(poll, 2000); return; }
      if (n !== v) { v = n; if (p[1] === 'css') { css(); poll(); } else { location.reload(); } }
      else { poll(); }
    }).catch(function () { setTimeout(poll, 2000); });
  }
  poll();
})();
"""


def free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def port_open(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        fam = socket.AF_INET6 if ":" in host else socket.AF_INET
        with socket.socket(fam, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            return True
    except OSError:
        return False


def inject_livereload(data: bytes, version: int) -> bytes:
    """Insert the live-reload <script> before </body> (or </html>, or at the end of an HTML document)."""
    tag = f'<script src="/__radide/livereload.js?v={version}"></script>'.encode()
    low = data.lower()
    for marker in (b"</body>", b"</html>"):
        i = low.rfind(marker)
        if i >= 0:
            return data[:i] + tag + data[i:]
    head = low.lstrip()[:300]
    if head.startswith((b"<!doctype html", b"<html")) or b"<body" in head:
        return data + tag
    return data


def is_text_type(ctype: str) -> bool:
    c = (ctype or "").lower()
    return any(t in c for t in TEXT_TYPES)


def body_text(data: bytes, ctype: str = "") -> tuple[str, bool]:
    """(text, binary) of a captured body: text bodies decoded as UTF-8 (or the charset of the type)."""
    if not data:
        return "", False
    m = re.search(r"charset=([\w.-]+)", ctype or "", re.I)
    if not is_text_type(ctype) and not (ctype or "").lower().startswith("multipart/") and b"\0" in data[:1024]:
        return "", True
    try:
        return data.decode(m.group(1) if m else "utf-8", errors="replace"), False
    except LookupError:
        return data.decode("utf-8", errors="replace"), False


def kill_tree(proc: subprocess.Popen) -> None:
    """Stop a process this server started, with its children (npm -> node)."""
    if proc is None or proc.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True,
                           creationflags=NO_WINDOW, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            pass
    if proc.poll() is None:
        try:
            proc.kill()
        except OSError:
            pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


_JOB = None                    # Windows Job Object handle (0 = not available)


def _job() -> int:
    """A Job Object with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: its handle lives only in the IDE process, so when
    the IDE exits - even when it crashes or is killed from the Task Manager - Windows closes the handle and
    kills every php / node process of the dev server (they would otherwise keep the project folder locked)."""
    global _JOB
    if _JOB is not None:
        return _JOB
    _JOB = 0
    if os.name != "nt":
        return 0
    try:
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        k32.SetInformationJobObject.restype = wintypes.BOOL
        k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        k32.AssignProcessToJobObject.restype = wintypes.BOOL
        k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]

        class _Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class _Io(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in ("ReadOperationCount", "WriteOperationCount",
                                                       "OtherOperationCount", "ReadTransferCount",
                                                       "WriteTransferCount", "OtherTransferCount")]

        class _Extended(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", _Basic), ("IoInfo", _Io), ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        handle = k32.CreateJobObjectW(None, None)
        if not handle:
            return 0
        info = _Extended()
        info.BasicLimitInformation.LimitFlags = 0x2000          # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not k32.SetInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            k32.CloseHandle(handle)                                # 9 = JobObjectExtendedLimitInformation
            return 0
        _JOB = int(handle)
        _job.assign = k32.AssignProcessToJobObject
    except (OSError, AttributeError, ValueError):
        _JOB = 0
    return _JOB


def adopt_process(proc: subprocess.Popen) -> bool:
    """Put a child process (and so all its future children) into the kill-on-close job (Windows only; does
    nothing elsewhere or when it is not possible)."""
    job = _job()
    handle = getattr(proc, "_handle", None)
    if not job or handle is None:
        return False
    try:
        return bool(_job.assign(job, int(handle)))
    except (OSError, ValueError, TypeError):
        return False


_LIVE: "weakref.WeakSet[DevServer]" = weakref.WeakSet()


@atexit.register
def _stop_all() -> None:
    """Never leave php/node processes behind when the IDE exits without stopping the server."""
    for srv in list(_LIVE):
        try:
            kill_tree(srv._proc)
        except Exception:  # noqa: BLE001
            pass


class _HTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False         # Windows: SO_REUSEADDR would let two servers share a port
    request_queue_size = 64


class DevServer(QObject):
    request = pyqtSignal(dict)
    log = pyqtSignal(str)
    reloaded = pyqtSignal(int)
    started = pyqtSignal(str)
    stopped = pyqtSignal()
    backendReady = pyqtSignal()
    backendExited = pyqtSignal(int)

    POLL_TIMEOUT = 25.0
    WATCH_INTERVAL = 0.6
    MAX_WATCH_FILES = 20000

    def __init__(self, project_folder, plugin, project=None, interpreter: str = "", parent=None,
                 host: str = "127.0.0.1"):
        super().__init__(parent)
        from ..model import Project
        self.folder = Path(project_folder).resolve()
        self.plugin = plugin
        if project is None and (self.folder / Project.FILE).exists():
            project = Project.load(self.folder)
        self.project = project
        self.config = web_config(project) if project is not None else {"root": ".", "start": "", "port": 0,
                                                                       "live_reload": True}
        self.root = (self.folder / self.config["root"]).resolve()
        self.interpreter = interpreter or (plugin.find_interpreter("") if plugin is not None else "")
        self.host = host
        self.port = 0
        self.backend_port = 0
        self.backend_host = "127.0.0.1"
        self.live_reload = bool(self.config.get("live_reload", True))
        self.version = 0
        self._history: list[tuple[int, str]] = []      # (version, "css" | "full")
        self._cond = threading.Condition()
        self._lock = threading.RLock()
        self._httpd: _HTTPServer | None = None
        self._proc: subprocess.Popen | None = None
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._restarting = False
        self._snapshot: dict[str, tuple[float, int]] = {}
        self._inflight: dict[int, float] = {}               # backend requests running now: key -> start time
        self._windows: collections.deque[tuple[float, float]] = collections.deque(maxlen=400)  # finished ones
        self._suppressed: dict[str, float] = {}             # changes attributed to the site itself
        self.ignored_changes = 0                            # (diagnostics / tests)
        self._backend_spec: dict | None = None
        self.backend_error = ""
        self.request_count = 0
        self.requests: collections.deque[dict] = collections.deque(maxlen=MAX_REQUESTS)

    # ------------------------------------------------------------ public API
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/" if self.port else ""

    @property
    def running(self) -> bool:
        return self._httpd is not None

    def is_ready(self) -> bool:
        return self._ready.is_set()

    def url_for(self, path="") -> str:
        """URL of a file of the site (absolute path or relative to the root) or of a URL path."""
        if not self.url:
            return ""
        p = str(path or "")
        if p.startswith(("/", "?")) and not Path(p).drive and not (os.name != "nt" and Path(p).exists()):
            return self.url.rstrip("/") + p
        fp = Path(p)
        if not fp.is_absolute():
            fp = self.root / fp
        try:
            r = fp.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return self.url
        if r == ".":
            r = ""
        if Path(r).name.lower() in ("index.php", "index.html", "index.htm") and r.count("/") == 0 and \
                self._is_index(r):
            r = ""
        return self.url + quote(r)

    def _is_index(self, rel: str) -> bool:
        for n in INDEX_FILES:
            if (self.root / n).is_file():
                return n.lower() == rel.lower()
        return False

    def start_url(self) -> str:
        start = str(self.config.get("start") or "")
        if self.plugin is not None and getattr(self.plugin, "web_kind", "") == "node":
            return self.url
        return self.url_for(start) if start else self.url

    def start(self) -> str:
        """Start serving (returns the URL at once; a backend that is still starting answers with a
        'starting' page until it listens)."""
        if self._httpd is not None:
            return self.url
        self._stop.clear()
        handler = self._make_handler()
        want = int(self.config.get("port") or 0)
        httpd = None
        for port in ([want] if want else []) + [0]:
            try:
                httpd = _HTTPServer((self.host, port), handler)
                break
            except OSError as e:
                self._emit_log(f"*** port {port} is not free ({e}); using another one")
        if httpd is None:
            raise OSError("cannot open a port for the web server")
        self._httpd = httpd
        _LIVE.add(self)
        self.port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.25}, daemon=True,
                         name="radide-devserver").start()
        spec = self.plugin.backend(self) if self.plugin is not None and hasattr(self.plugin, "backend") else None
        hook = getattr(self, "backend_hook", None)       # debug runs: Xdebug / --inspect (web_site/debug.py)
        if spec is not None and callable(hook):
            spec = hook(self, spec)
        self._backend_spec = spec
        self._snapshot = self._scan()
        threading.Thread(target=self._watch_loop, daemon=True, name="radide-devserver-watch").start()
        if spec is None:
            self._ready.set()
        else:
            threading.Thread(target=self._run_backend, args=(spec, True), daemon=True,
                             name="radide-devserver-backend").start()
        self.started.emit(self.url)
        return self.url

    def wait_ready(self, timeout: float = 30.0) -> bool:
        return self._ready.wait(timeout)

    def stop(self) -> None:
        if self._httpd is None and self._proc is None:
            return
        self._stop.set()
        with self._cond:
            self._cond.notify_all()
        httpd, self._httpd = self._httpd, None
        if httpd is not None:
            try:
                httpd.shutdown()
                httpd.server_close()
            except OSError:
                pass
        proc, self._proc = self._proc, None
        kill_tree(proc)
        self._ready.clear()
        self.stopped.emit()

    def restart_backend(self) -> None:
        """Restart the site's own server (Node) - the front server and its port stay."""
        if self._backend_spec is None or self._stop.is_set():
            return
        threading.Thread(target=self._restart, daemon=True, name="radide-devserver-restart").start()

    def notify_change(self, paths=None) -> int:
        """Files changed: bump the live-reload version (CSS-only changes -> 'css')."""
        paths = [str(p) for p in (paths or [])]
        kind = "css" if paths and all(p.lower().endswith(".css") for p in paths) else "full"
        with self._cond:
            self.version += 1
            self._history.append((self.version, kind))
            del self._history[:-200]
            v = self.version
            self._cond.notify_all()
        self.reloaded.emit(v)
        return v

    def check_now(self) -> list[str]:
        """Rescan the files now (call after a save in the IDE); returns the changed paths. The changes are the
        user's, so a source file written while a request was running still reloads."""
        return self._detect_changes(trusted=True)

    # ------------------------------------------------------------ watcher
    def _skip_dir(self, name: str) -> bool:
        if name in HIDDEN_DIRS or name in HEAVY_DIRS or name.startswith(".") or name.lower().startswith(".radide"):
            return True
        # folders the running site writes itself (only sites with their own server write anything)
        return self._backend_spec is not None and name.lower() in RUNTIME_DIRS

    @staticmethod
    def watched_file(name: str) -> bool:
        """Is a file a source / asset whose edit should reload the Preview?"""
        low = name.lower()
        if low in WATCH_NAMES:
            return True
        if low.endswith(RUNTIME_SUFFIXES) or low.startswith(("sess_", "~$", ".#")) or low == "project.radproj":
            return False
        return os.path.splitext(low)[1] in WATCH_EXT

    def _scan(self) -> dict[str, tuple[float, int]]:
        out: dict[str, tuple[float, int]] = {}
        for dirpath, dirnames, filenames in os.walk(self.folder):
            dirnames[:] = [d for d in dirnames if not self._skip_dir(d)]
            for f in filenames:
                if not self.watched_file(f):
                    continue
                p = os.path.join(dirpath, f)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                out[p] = (st.st_mtime, st.st_size)
                if len(out) >= self.MAX_WATCH_FILES:
                    return out
        return out

    def _diff(self) -> list[str]:
        with self._lock:
            new = self._scan()
            old = self._snapshot
            changed = [p for p, v in new.items() if old.get(p) != v] + [p for p in old if p not in new]
            self._snapshot = new
        return changed

    def _request_start(self, key: int) -> None:
        with self._lock:
            self._inflight[key] = time.time()

    def _request_end(self, key: int) -> None:
        with self._lock:
            start = self._inflight.pop(key, None)
            if start is not None:
                self._windows.append((start, time.time()))

    def _written_by_site(self, path: str) -> bool:
        """A change made while (or just after) the site's own server handled a request was made by the site
        (a cache file, a generated page...) - not by the user; reloading for it would loop forever."""
        if self._backend_spec is None:
            return False
        try:
            mtime = os.stat(path).st_mtime
        except OSError:
            return False
        with self._lock:
            now = time.time()
            if any(start - 0.05 <= mtime and now - start < 30 for start in self._inflight.values()):
                return True                     # (a long streaming response does not hide edits for ever)
            return any(start - 0.05 <= mtime <= end + REQUEST_SLACK for start, end in self._windows)

    def _detect_changes(self, trusted: bool = False) -> list[str]:
        changed = self._diff()
        if not changed and not (trusted and self._suppressed):
            return []
        # debounce: wait until the burst of writes is over, then reload once for all of them
        deadline = time.monotonic() + 2.0
        while changed and time.monotonic() < deadline and not trusted:
            if self._stop.wait(DEBOUNCE):
                return []
            more = self._diff()
            if not more:
                break
            changed += [p for p in more if p not in changed]
        if trusted:
            # saved in the IDE: changes the watcher attributed to a request a moment ago are the user's after all
            now = time.time()
            changed += [p for p, t in self._suppressed.items() if now - t < 10 and p not in changed]
            self._suppressed.clear()
        else:
            site = [p for p in changed if self._written_by_site(p)]
            if site:
                self.ignored_changes += len(site)
                now = time.time()
                for p in site:
                    self._suppressed[p] = now
                changed = [p for p in changed if p not in site]
        if changed:
            if self._needs_restart(changed):
                self._emit_log("Server code changed - restarting the site's server...")
                self.restart_backend()
            else:
                self.notify_change(changed)
        return changed

    def _needs_restart(self, changed: list[str]) -> bool:
        if self._backend_spec is None or not self._backend_spec.get("restart_on_change"):
            return False
        for p in changed:
            path = Path(p)
            if path.suffix.lower() not in SERVER_JS_EXT:
                continue
            try:
                parts = {x.lower() for x in path.resolve().relative_to(self.folder).parts[:-1]}
            except ValueError:
                continue
            if not parts & CLIENT_DIRS:
                return True
        return False

    def _watch_loop(self) -> None:
        while not self._stop.wait(self.WATCH_INTERVAL):
            try:
                self._detect_changes()
            except Exception as e:  # noqa: BLE001 - the watcher must keep running
                self._emit_log(f"*** file watcher: {e}")

    # ------------------------------------------------------------ backend process
    def _emit_log(self, text: str) -> None:
        if text.strip():
            self._last_line = text.strip()[-300:]          # shown on the "Starting" page
        try:
            self.log.emit(text)
        except RuntimeError:          # the QObject was deleted
            pass

    def _run_backend(self, spec: dict, first: bool) -> None:
        self._ready.clear()
        self.backend_error = ""
        cwd = str(spec.get("cwd") or self.folder)
        env = dict(os.environ)
        env.update({k: str(v) for k, v in (spec.get("env") or {}).items()})
        for cmd in (spec.get("prepare") or []) if first else []:
            if self._stop.is_set():
                return
            self._emit_log("> " + " ".join(str(c) for c in cmd))
            try:
                p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=NO_WINDOW, shell=bool(spec.get("shell")))
                adopt_process(p)
                with self._lock:
                    self._proc = p
                for raw in iter(p.stdout.readline, b""):
                    self._emit_log(raw.decode("utf-8", errors="replace").rstrip())
                p.wait()
                if p.returncode:
                    self._emit_log(f"*** exited with code {p.returncode}")
            except OSError as e:
                self._emit_log(f"*** cannot run {cmd[0]}: {e}")
        if self._stop.is_set():
            return
        self.backend_port = free_port()
        argv = [str(a).replace("{port}", str(self.backend_port)) for a in spec["argv"]]
        env = {k: v.replace("{port}", str(self.backend_port)) for k, v in env.items()}
        env.setdefault("PORT", str(self.backend_port))
        if "PORT" in (spec.get("env") or {}):
            env["PORT"] = str(self.backend_port)
        self._emit_log("> " + " ".join(f'"{a}"' if " " in a else a for a in argv))
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
        except OSError as e:
            self.backend_error = f"cannot start {argv[0]}: {e}"
            self._emit_log("*** " + self.backend_error)
            self._ready.set()
            return
        adopt_process(proc)
        with self._lock:
            self._proc = proc
        threading.Thread(target=self._read_output, args=(proc,), daemon=True, name="radide-devserver-out").start()
        t0 = time.monotonic()
        deadline = t0 + float(spec.get("timeout", 30))
        # past the deadline a server that is still running is waited for (a first start can take many minutes:
        # gems / bootsnap caches, the antivirus scanning thousands of new files) - the browser shows the
        # "Starting" page with the server's last output instead of a 502; only after hard_limit does it give up
        hard_limit = t0 + max(float(spec.get("timeout", 30)), float(spec.get("hard_timeout", 1800)))
        warned = False
        while not self._stop.is_set() and time.monotonic() < hard_limit:
            if proc.poll() is not None:
                self.backend_error = f"the server exited with code {proc.returncode}"
                break
            if not warned and time.monotonic() > deadline:
                warned = True
                self._emit_log(f"*** the site's server has not opened its port after {int(time.monotonic() - t0)} s - "
                               "still waiting (the first start can take several minutes)")
            for h in ("127.0.0.1", "::1"):
                if port_open(h, self.backend_port):
                    self.backend_host = h
                    self._ready.set()
                    self.backendReady.emit()
                    return
            time.sleep(0.1)
        if not self.backend_error and not self._stop.is_set():
            self.backend_error = f"the server did not open port {self.backend_port}"
        if self.backend_error:
            self._emit_log("*** " + self.backend_error)
        self._ready.set()                      # requests get a 502 page with the error

    def _read_output(self, proc: subprocess.Popen) -> None:
        # spec "log_filter": regex of the backend's own request-log lines (the Requests dock shows them)
        quiet = re.compile((self._backend_spec or {}).get("log_filter") or r"(?!)")
        for raw in iter(proc.stdout.readline, b""):
            line = raw.decode("utf-8", errors="replace").rstrip()
            if not line or PHP_ACCESS.match(line) or quiet.search(line):
                continue
            if PHP_STARTED.search(line):
                line = f"PHP development server ready (internal port {self.backend_port})"
            self._emit_log(line)
        code = proc.wait()
        if proc is self._proc and not self._stop.is_set() and not self._restarting:
            self.backend_error = f"the server exited with code {code}"
            self._emit_log(f"*** The site's server exited with code {code}")
            try:
                self.backendExited.emit(code)
            except RuntimeError:
                pass

    def _restart(self) -> None:
        with self._lock:
            self._restarting = True
            proc, self._proc = self._proc, None
        self._ready.clear()
        kill_tree(proc)
        self._restarting = False
        self._run_backend(self._backend_spec, False)
        if self.backend_error == "":
            self.notify_change(["(server restarted)"])

    # ------------------------------------------------------------ HTTP handler
    def _make_handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"
            server_version = "RADIDE-DevServer/1.0"

            def log_message(self, fmt, *args):     # noqa: D401 - silence the default stderr log
                pass

            def handle_one_request(self):
                try:
                    super().handle_one_request()
                except (ConnectionError, socket.timeout, OSError):
                    self.close_connection = True

            def _do(self):
                server._handle(self)

            do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_HEAD = do_OPTIONS = _do
        return Handler

    def _handle(self, h: BaseHTTPRequestHandler) -> None:
        t0 = time.perf_counter()
        path = h.path
        info = {"method": h.command, "path": path, "status": 0, "ms": 0.0, "size": 0, "type": "",
                "time": time.strftime("%H:%M:%S"), "url": self.url.rstrip("/") + path,
                "remote": h.client_address[0] if h.client_address else "",
                "req_headers": [[k, v] for k, v in h.headers.items()], "req_body": "", "req_body_size": 0,
                "req_body_binary": False, "resp_headers": [], "resp_preview": "", "reason": ""}
        if path.startswith("/__radide/"):
            self._internal(h, path)
            return
        h._radide_info = info
        try:
            if self._backend_spec is None:
                status, size, ctype = self._static(h)
            elif h.headers.get("Upgrade", "").lower() == "websocket":
                status, size, ctype = self._tunnel(h)
            else:
                key = id(h)
                self._request_start(key)
                try:
                    status, size, ctype = self._proxy(h)
                finally:
                    self._request_end(key)
        except (ConnectionError, socket.timeout, BrokenPipeError):
            status, size, ctype = 499, 0, ""
        except Exception as e:  # noqa: BLE001 - one bad request must not kill the server
            status, size, ctype = 500, 0, "text/plain"
            self._emit_log(f"*** dev server error for {path}: {e}")
            try:
                self._send_simple(h, 500, f"RAD IDE dev server error: {e}")
            except OSError:
                pass
        info.update(status=status, size=size, type=ctype.split(";")[0].strip(),
                    ms=round((time.perf_counter() - t0) * 1000, 1))
        if not info["req_body_size"] and h.command not in ("GET", "HEAD", "OPTIONS"):
            n = int(h.headers.get("Content-Length") or 0)       # a body the handler did not need (static)
            if 0 < n <= MAX_BODY and not h.headers.get("Transfer-Encoding"):
                try:
                    h.connection.settimeout(2)
                    self._capture_request_body(h, h.rfile.read(n))
                except OSError:
                    pass
        self.request_count += 1
        info["id"] = self.request_count
        self.requests.append(info)
        try:
            self.request.emit(info)
        except RuntimeError:
            pass

    # --- request details (the Requests dock)
    @staticmethod
    def _capture_request_body(h, body: bytes | None) -> None:
        info = getattr(h, "_radide_info", None)
        if info is None or not body:
            return
        info["req_body_size"] = len(body)
        info["req_body"], info["req_body_binary"] = body_text(body[:MAX_BODY], h.headers.get("Content-Type", ""))

    @staticmethod
    def _capture_response(h, status: int, reason: str, headers, ctype: str, data: bytes = b"") -> None:
        info = getattr(h, "_radide_info", None)
        if info is None:
            return
        info["reason"] = reason or ""
        info["resp_headers"] = [[str(k), str(v)] for k, v in headers]
        if data and is_text_type(ctype):
            info["resp_preview"] = data[:MAX_PREVIEW].decode("utf-8", errors="replace")

    # --- internal endpoints
    def _internal(self, h, path: str) -> None:
        parts = urlsplit(path)
        if parts.path == "/__radide/livereload.js":
            self._send_bytes(h, 200, LIVERELOAD_JS.encode(), "text/javascript; charset=utf-8",
                             {"Cache-Control": "no-store"})
        elif parts.path == "/__radide/poll":
            try:
                v = int((parse_qs(parts.query).get("v") or ["0"])[0])
            except ValueError:
                v = 0
            deadline = time.monotonic() + self.POLL_TIMEOUT
            with self._cond:
                while self.version == v and not self._stop.is_set():
                    left = deadline - time.monotonic()
                    if left <= 0:
                        break
                    self._cond.wait(min(left, 1.0))
                cur = self.version
                kinds = {k for ver, k in self._history if ver > v}
                covered = any(ver == v + 1 for ver, _ in self._history)
            kind = "css" if kinds == {"css"} and covered else "full"
            self._send_bytes(h, 200, f"{cur} {kind}".encode(), "text/plain", {"Cache-Control": "no-store"})
        elif parts.path == "/__radide/status":
            body = json.dumps({"version": self.version, "ready": self.is_ready(), "error": self.backend_error,
                               "requests": self.request_count, "root": str(self.root)}).encode()
            self._send_bytes(h, 200, body, "application/json", {"Cache-Control": "no-store"})
        else:
            self._send_simple(h, 404, "not found")

    # --- responses
    def _send_bytes(self, h, status: int, body: bytes, ctype: str, headers: dict | None = None) -> None:
        h.send_response_only(status)
        sent = [("Server", h.server_version), ("Date", h.date_time_string()), ("Content-Type", ctype),
                ("Content-Length", str(len(body)))] + list((headers or {}).items())
        for k, v in sent:
            h.send_header(k, v)
        h.end_headers()
        self._capture_response(h, status, h.responses.get(status, ("",))[0], sent, ctype, body)
        if h.command != "HEAD":
            h.wfile.write(body)

    def _send_simple(self, h, status: int, text: str) -> None:
        self._send_bytes(h, status, text.encode("utf-8"), "text/plain; charset=utf-8")

    def _error_page(self, h, status: int, title: str, message: str, refresh: int = 0) -> tuple[int, int, str]:
        import html
        meta = f'<meta http-equiv="refresh" content="{refresh}">' if refresh else ""
        body = (f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{status} {html.escape(title)}</title>"
                f"{meta}<style>body{{font-family:Segoe UI,sans-serif;margin:40px;color:#333}}"
                f"h1{{color:#1f3d7a;font-weight:400}}code{{background:#f3f3f3;padding:2px 4px}}</style></head>"
                f"<body><h1>{status} - {html.escape(title)}</h1><p>{message}</p>"
                f"<p style='color:#888;font-size:12px'>RAD IDE development server</p></body></html>").encode()
        if self.live_reload:
            body = inject_livereload(body, self.version)
        self._send_bytes(h, status, body, "text/html; charset=utf-8", {"Cache-Control": "no-store"})
        return status, len(body), "text/html"

    # --- static files (static-web)
    def _static(self, h) -> tuple[int, int, str]:
        import html
        parts = urlsplit(h.path)
        rel = unquote(parts.path).lstrip("/")
        target = (self.root / rel).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            return self._error_page(h, 403, "Forbidden", "The path is outside the web site.")
        if h.command not in ("GET", "HEAD"):
            return self._error_page(h, 405, "Method Not Allowed",
                                    "A static HTML site only answers GET requests (use a PHP or Node.js site "
                                    "for forms that post data).")
        if target.is_dir():
            if not parts.path.endswith("/"):
                loc = parts.path + "/" + (f"?{parts.query}" if parts.query else "")
                self._send_bytes(h, 301, b"", "text/plain", {"Location": loc})
                return 301, 0, "text/plain"
            for n in INDEX_FILES:
                if (target / n).is_file() and not n.endswith(".php"):
                    target = target / n
                    break
            else:
                items = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
                rows = "".join(f'<li><a href="{quote(p.name)}{"/" if p.is_dir() else ""}">{html.escape(p.name)}'
                               f'{"/" if p.is_dir() else ""}</a></li>' for p in items
                               if p.name not in HIDDEN_DIRS and p.name != "project.radproj")
                return self._error_page(h, 200, f"Index of /{rel}", f"<ul>{rows}</ul>")
        if not target.is_file():
            return self._error_page(h, 404, "Not Found", f"<code>{html.escape(parts.path)}</code> does not exist "
                                    "in the web site.")
        ext = target.suffix.lower()
        ctype = MIME.get(ext) or mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        try:
            data = target.read_bytes()
        except OSError as e:
            return self._error_page(h, 500, "Cannot read the file", html.escape(str(e)))
        if ctype.startswith("text/html") and self.live_reload:
            data = inject_livereload(data, self.version)
        self._send_bytes(h, 200, data, ctype, {"Cache-Control": "no-cache",
                                                 "Last-Modified": h.date_time_string(target.stat().st_mtime)})
        return 200, len(data), ctype

    # --- reverse proxy (php -S / node)
    def _read_body(self, h) -> bytes | None:
        te = h.headers.get("Transfer-Encoding", "").lower()
        if "chunked" in te:
            out = bytearray()
            while True:
                line = h.rfile.readline()
                size = int(line.split(b";")[0].strip() or b"0", 16)
                if size == 0:
                    while h.rfile.readline() not in (b"\r\n", b"\n", b""):
                        pass
                    break
                out += h.rfile.read(size)
                h.rfile.readline()
            return bytes(out)
        n = int(h.headers.get("Content-Length") or 0)
        return h.rfile.read(n) if n > 0 else None

    def _wait_backend(self, h) -> tuple[int, int, str] | None:
        if not self._ready.wait(60 if not self._restarting else 30):
            import html
            last = getattr(self, "_last_line", "")
            return self._error_page(h, 503, "Starting", "The site's server is still starting..." +
                                    (f"<br><br>Last output: <code>{html.escape(last)}</code>" if last else "") +
                                    "<br>(the first start can take several minutes - see the Output window)",
                                    refresh=2)
        if self.backend_error and (self._proc is None or self._proc.poll() is not None):
            import html
            return self._error_page(h, 502, "Server not running",
                                    "The site's server is not running: " + html.escape(self.backend_error) +
                                    ".<br>See the Output window for its messages.", refresh=0)
        return None

    def _backend_headers(self, h, body: bytes | None) -> list[tuple[str, str]]:
        hdrs = [(k, v) for k, v in h.headers.items()
                if k.lower() not in HOP_BY_HOP and k.lower() not in ("accept-encoding", "content-length")]
        hdrs.append(("X-Forwarded-For", h.client_address[0] if h.client_address else "127.0.0.1"))
        hdrs.append(("X-Forwarded-Host", h.headers.get("Host", f"{self.host}:{self.port}")))
        hdrs.append(("X-Forwarded-Proto", "http"))
        if body is not None or h.command in ("POST", "PUT", "PATCH"):
            hdrs.append(("Content-Length", str(len(body or b""))))
        hdrs.append(("Connection", "close"))
        return hdrs

    def _rewrite_location(self, value: str) -> str:
        for bh in ("127.0.0.1", "localhost", "[::1]"):
            value = value.replace(f"//{bh}:{self.backend_port}", f"//{self.host}:{self.port}")
        return value

    def _proxy(self, h) -> tuple[int, int, str]:
        early = self._wait_backend(h)
        if early is not None:
            return early
        body = self._read_body(h)
        self._capture_request_body(h, body)
        conn = http.client.HTTPConnection(self.backend_host, self.backend_port, timeout=600)
        try:
            conn.putrequest(h.command, h.path, skip_host=True, skip_accept_encoding=True)
            for k, v in self._backend_headers(h, body):
                conn.putheader(k, v)
            conn.endheaders(body)
            resp = conn.getresponse()
        except OSError as e:
            conn.close()
            import html
            return self._error_page(h, 502, "Bad Gateway", f"The site's server did not answer: {html.escape(str(e))}")
        try:
            status = resp.status
            ctype = resp.getheader("Content-Type", "") or ""
            headers = [(k, v) for k, v in resp.getheaders() if k.lower() not in HOP_BY_HOP]
            inject = (self.live_reload and "text/html" in ctype.lower() and h.command != "HEAD" and
                      status not in (204, 304) and not resp.getheader("Content-Encoding"))
            h.send_response_only(status, resp.reason)
            headers = [(k, self._rewrite_location(v) if k.lower() in ("location", "refresh") else v)
                       for k, v in headers]
            if inject:
                data = inject_livereload(resp.read(), self.version)
                headers = [(k, v) for k, v in headers if k.lower() != "content-length"]
                headers.append(("Content-Length", str(len(data))))
                for k, v in headers:
                    h.send_header(k, v)
                h.end_headers()
                h.wfile.write(data)
                self._capture_response(h, status, resp.reason, headers, ctype, data)
                return status, len(data), ctype
            for k, v in headers:
                h.send_header(k, v)
            h.end_headers()
            size = 0
            preview = bytearray()
            want_preview = is_text_type(ctype)
            try:
                if h.command != "HEAD" and status not in (204, 304):
                    while True:
                        chunk = resp.read1(65536)
                        if not chunk:
                            break
                        if want_preview and len(preview) < MAX_PREVIEW:
                            preview += chunk[:MAX_PREVIEW - len(preview)]
                        h.wfile.write(chunk)
                        h.wfile.flush()
                        size += len(chunk)
            finally:
                self._capture_response(h, status, resp.reason, headers, ctype, bytes(preview))
            return status, size, ctype
        finally:
            conn.close()

    def _tunnel(self, h) -> tuple[int, int, str]:
        """WebSocket upgrade: pipe the raw connection to the backend."""
        early = self._wait_backend(h)
        if early is not None:
            return early
        fam = socket.AF_INET6 if ":" in self.backend_host else socket.AF_INET
        up = socket.socket(fam, socket.SOCK_STREAM)
        up.connect((self.backend_host, self.backend_port))
        lines = [f"{h.command} {h.path} HTTP/1.1"] + [f"{k}: {v}" for k, v in h.headers.items()]
        up.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1"))
        client = h.connection
        h.close_connection = True

        def pipe(src, dst):
            try:
                while True:
                    data = src.recv(65536)
                    if not data:
                        break
                    dst.sendall(data)
            except OSError:
                pass
            finally:
                for s in (src, dst):
                    try:
                        s.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
        t = threading.Thread(target=pipe, args=(up, client), daemon=True)
        t.start()
        pipe(client, up)
        t.join(5)
        up.close()
        return 101, 0, "websocket"


__all__ = ["DevServer", "MAX_BODY", "MAX_PREVIEW", "MAX_REQUESTS", "adopt_process", "body_text", "free_port",
           "inject_livereload", "is_text_type", "kill_tree", "port_open"]
