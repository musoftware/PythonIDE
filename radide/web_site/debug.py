"""Debugging of web site projects (F5 on a PHP or Node.js site).

F5 starts the site's server **and** a debugger; a page request (Preview, browser, fetch) that reaches a line
with a breakpoint (F9) pauses there: Locals / Call Stack / Watch / Immediate, F10 / F11 / Shift+F11, Stop.

- **PHP** - Xdebug (``php_xdebug-<ver>-<php>-<nts|ts>-<vs>-x86_64.dll`` from xdebug.org, loaded with
  ``-d zend_extension=...`` only for debug runs) talks DBGp to the **vscode-php-debug** adapter
  (``node phpDebug.js``, Debug Adapter Protocol on stdio) -> :class:`PhpDebugSession`.
- **Node.js** - the site's server runs as ``node --inspect-wait=127.0.0.1:<port> <start>``; the
  **vscode-js-debug** ``dapDebugServer.js`` attaches to it (DAP over TCP, the real target is a child
  session announced with ``startDebugging``) -> :class:`JsDebugSession`. When the server restarts after a
  save, js-debug re-attaches by itself (``restart: true``).

Both sessions are :class:`radide.dap.DapSession` subclasses, so the IDE drives them like any debugger
session (``win.session``). The tools live in ``%LOCALAPPDATA%\\RADIDE\\tools`` (``xdebug``, ``php-debug``,
``js-debug``); :func:`ensure_tools` downloads what is missing (official releases, no installer, no admin).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import urllib.request
import zipfile
from pathlib import Path

from PyQt6.QtCore import QTimer, pyqtSignal

from ..dap import ADAPTERS, DapSession

TRACE = bool(os.environ.get("RADIDE_DAP_TRACE"))
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
TOOLS = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share") / "RADIDE" / "tools"
XDEBUG_DIR = TOOLS / "xdebug"
PHP_DEBUG_DIR = TOOLS / "php-debug"
JS_DEBUG_DIR = TOOLS / "js-debug"
PHP_DEBUG_JS = PHP_DEBUG_DIR / "extension" / "out" / "phpDebug.js"
JS_DEBUG_JS = JS_DEBUG_DIR / "js-debug" / "src" / "dapDebugServer.js"

# known-good releases (the versions RAD IDE was tested with)
PHP_DEBUG_VERSION = "1.40.2"
PHP_DEBUG_URL = (f"https://github.com/xdebug/vscode-php-debug/releases/download/v{PHP_DEBUG_VERSION}/"
                 f"php-debug-{PHP_DEBUG_VERSION}.vsix")
JS_DEBUG_VERSION = "1.140.1"
JS_DEBUG_URL = (f"https://github.com/microsoft/vscode-js-debug/releases/download/v{JS_DEBUG_VERSION}/"
                f"js-debug-dap-v{JS_DEBUG_VERSION}.tar.gz")
XDEBUG_INDEX = "https://xdebug.org/download/historical"
XDEBUG_FILES = "https://xdebug.org/files/"

PHP_EXCEPTION_FILTERS = ["Error"]          # \Error and subclasses (TypeError, ...) = programming errors
JS_EXCEPTION_FILTERS = ["uncaught"]
JS_SKIP_FILES = ["<node_internals>/**", "**/node_modules/**"]


# ============================================================================ tools
def node_exe() -> str:
    return shutil.which("node") or shutil.which("node.exe") or ""


def _run(argv, timeout=20) -> str:
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, creationflags=NO_WINDOW,
                           stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")
        return (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired):
        return ""


_PHP_INFO: dict[str, dict] = {}


def php_info(php: str) -> dict:
    """{"version": "8.1", "ts": False, "vs": "vs16", "x64": True, "xdebug": False} of a php executable."""
    if php in _PHP_INFO:
        return _PHP_INFO[php]
    out = _run([php, "-i"])
    info = {"version": "", "ts": False, "vs": "", "x64": True, "xdebug": False}
    m = re.search(r"^PHP Version => (\d+)\.(\d+)", out, re.M)
    if m:
        info["version"] = f"{m.group(1)}.{m.group(2)}"
    m = re.search(r"^PHP Extension Build => API\d+,(NTS|TS),(V[SC]\d+)", out, re.M)
    if m:
        info["ts"] = m.group(1) == "TS"
        info["vs"] = m.group(2).lower()
    else:
        info["ts"] = bool(re.search(r"^Thread Safety => enabled", out, re.M))
    m = re.search(r"^Architecture => (\S+)", out, re.M)
    if m:
        info["x64"] = m.group(1).lower() in ("x64", "x86_64", "amd64")
    info["xdebug"] = bool(re.search(r"^xdebug support => enabled", out, re.M | re.I)) or \
        bool(re.search(r"with Xdebug v", out))
    if info["version"]:
        _PHP_INFO[php] = info
    return info


def _xdebug_regex(info: dict) -> re.Pattern:
    ts = "ts" if info["ts"] else "nts"
    arch = r"-x86_64" if info["x64"] else ""
    return re.compile(r"php_xdebug-(\d+(?:\.\d+)+)-" + re.escape(info["version"]) + "-" + ts + "-" +
                      re.escape(info["vs"]) + arch + r"\.dll$", re.I)


def _vkey(v: str):
    return tuple(int(x) for x in v.split(".") if x.isdigit())


def find_xdebug(php: str) -> str | None:
    """Path of a matching Xdebug DLL in the tools folder, "" if php already loads Xdebug, None if missing."""
    info = php_info(php)
    if info["xdebug"]:
        return ""
    if not info["version"] or not info["vs"]:
        return None
    rx = _xdebug_regex(info)
    found = [(m.group(1), p) for p in (XDEBUG_DIR.glob("php_xdebug-*.dll") if XDEBUG_DIR.is_dir() else [])
             if (m := rx.match(p.name))]
    if not found:
        return None
    return str(max(found, key=lambda t: _vkey(t[0]))[1])


def _download(url: str, target: Path, log=None) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if log:
        log(f"Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "RAD-IDE"})
    tmp = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    tmp.replace(target)
    return target


def download_xdebug(php: str, log=None) -> str:
    """Download the newest official Xdebug DLL that matches *php* into the tools folder."""
    info = php_info(php)
    if not info["version"] or not info["vs"]:
        raise RuntimeError(f"cannot read the PHP version / compiler of {php}")
    req = urllib.request.Request(XDEBUG_INDEX, headers={"User-Agent": "RAD-IDE"})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")
    rx = _xdebug_regex(info)
    names = {m.group(0) for m in re.finditer(r"php_xdebug-[\w.\-]+?\.dll", page) if rx.match(m.group(0))}
    if not names:
        raise RuntimeError(f"xdebug.org has no Xdebug build for PHP {info['version']} "
                           f"{'TS' if info['ts'] else 'NTS'} {info['vs'].upper()}")
    best = max(names, key=lambda n: _vkey(rx.match(n).group(1)))
    return str(_download(XDEBUG_FILES + best, XDEBUG_DIR / best, log))


def download_php_debug(log=None) -> str:
    vsix = _download(PHP_DEBUG_URL, TOOLS / "_download" / f"php-debug-{PHP_DEBUG_VERSION}.vsix", log)
    PHP_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(vsix) as z:
        for name in z.namelist():
            dest = (PHP_DEBUG_DIR / name).resolve()
            if not str(dest).startswith(str(PHP_DEBUG_DIR.resolve())):
                continue                       # no paths outside the folder
            if name.startswith("extension/"):
                z.extract(name, PHP_DEBUG_DIR)
    return str(PHP_DEBUG_JS)


def download_js_debug(log=None) -> str:
    import tarfile
    tgz = _download(JS_DEBUG_URL, TOOLS / "_download" / f"js-debug-dap-v{JS_DEBUG_VERSION}.tar.gz", log)
    JS_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tgz, "r:gz") as t:
        try:
            t.extractall(JS_DEBUG_DIR, filter="data")
        except TypeError:                     # Python without extraction filters
            t.extractall(JS_DEBUG_DIR)
    return str(JS_DEBUG_JS)


def missing_tools(kind: str, php: str = "") -> list[tuple[str, str, callable]]:
    """(name, size hint, download function) of the tools a debug run of a *kind* ("php"/"node") site lacks."""
    out = []
    if kind == "php":
        if php and find_xdebug(php) is None:
            out.append(("Xdebug (php_xdebug DLL from xdebug.org)", "about 0.3 MB",
                        lambda log: download_xdebug(php, log)))
        if not PHP_DEBUG_JS.is_file():
            out.append((f"PHP Debug adapter (vscode-php-debug {PHP_DEBUG_VERSION})", "about 1.8 MB",
                        download_php_debug))
    elif kind == "node":
        if not JS_DEBUG_JS.is_file():
            out.append((f"JavaScript debugger (vscode-js-debug {JS_DEBUG_VERSION})", "about 1.2 MB",
                        download_js_debug))
    return out


def node_supports_inspect_wait(node: str) -> bool:
    """--inspect-wait (wait for the debugger, no pause) exists since Node 20.15 / 22.2."""
    m = re.search(r"v(\d+)\.(\d+)", _run([node, "--version"], 10))
    if not m:
        return False
    major, minor = int(m.group(1)), int(m.group(2))
    return major > 22 or (major == 22 and minor >= 2) or (major == 20 and minor >= 15)


def free_port() -> int:
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ============================================================================ sessions
def _error_text(msg: dict) -> str:
    body = msg.get("body") or {}
    err = body.get("error") if isinstance(body, dict) else None
    if isinstance(err, dict) and err.get("format"):
        return str(err["format"]).splitlines()[0]
    return msg.get("message") or "error"


ADAPTERS.setdefault("php-xdebug", (
    lambda: [node_exe(), str(PHP_DEBUG_JS)] if node_exe() and PHP_DEBUG_JS.is_file() else None,
    lambda prog, args, cwd, env: {"type": "php", "request": "launch", "hostname": "127.0.0.1", "port": 9003,
                                  "log": False, "xdebugSettings": {"max_children": 200, "max_depth": 1,
                                                                   "max_data": 2048}}))
ADAPTERS.setdefault("js-debug", (
    lambda: [node_exe(), str(JS_DEBUG_JS)] if node_exe() and JS_DEBUG_JS.is_file() else None,
    lambda prog, args, cwd, env: {"type": "pwa-node", "request": "attach", "address": "127.0.0.1", "port": 9229,
                                  "restart": True, "continueOnAttach": True, "timeout": 30000,
                                  "skipFiles": JS_SKIP_FILES, "localRoot": cwd, "cwd": cwd}))


class _WebDapMixin:
    """Shared bits: a ``ready`` signal once the adapter listens / is attached, adapter-specific exception
    filters, readable evaluate errors."""
    exception_filters: list[str] = []

    def _filters(self):
        return list(self.exception_filters) if self.break_on_exception else []

    def set_break_on_exception(self, on: bool):
        self.break_on_exception = on
        self._request("setExceptionBreakpoints", {"filters": self._filters()})

    def evaluate(self, expr: str):
        if not self.paused:
            self.evalResult.emit("(the program must be paused at a breakpoint)")
            return
        self._request("evaluate", {"expression": expr, "frameId": self.frame_id, "context": "repl"},
                      lambda b, m: self.evalResult.emit(b.get("result", "") if m.get("success", True)
                                                        else _error_text(m)))


class PhpDebugSession(_WebDapMixin, DapSession):
    """vscode-php-debug over stdio; every page request is one Xdebug connection (= one DAP thread)."""
    ready = pyqtSignal()
    exception_filters = PHP_EXCEPTION_FILTERS

    def __init__(self, cwd, breakpoints, port: int, parent=None):
        super().__init__("php-xdebug", "", [], cwd, None, breakpoints, parent)
        self.xdebug_port = port
        self.launch_args["port"] = port

    def _on_initialize(self, body, _msg):
        def launched(_b, m):
            if m.get("success", True):
                self.ready.emit()
        self._request("launch", self.launch_args, launched)

    def _dispatch(self, msg):
        if msg.get("type") == "event" and msg.get("event") == "initialized":
            self._request("setExceptionBreakpoints", {"filters": self._filters()})
            self._send_breakpoints(lambda: self._request("configurationDone"))
            return
        if msg.get("type") == "event" and msg.get("event") == "thread" and \
                (msg.get("body") or {}).get("reason") == "exited" and self.paused and \
                (msg.get("body") or {}).get("threadId") == self.thread_id:
            self.paused = False                 # the paused request ended (e.g. the browser gave up)
            self.resumed.emit()
        super()._dispatch(msg)


class _Conn:
    """One DAP connection over TCP to js-debug's dapDebugServer."""

    def __init__(self, session, name: str, port: int):
        from PyQt6.QtNetwork import QTcpSocket
        self.session = session
        self.name = name
        self.seq = 0
        self.callbacks: dict[int, callable] = {}
        self.buf = b""
        self.sock = QTcpSocket(session)
        self.sock.readyRead.connect(self._read)
        self.sock.disconnected.connect(lambda: session._conn_closed(self))
        self.sock.connectToHost("127.0.0.1", port)
        self.closed = False

    def send(self, msg):
        if TRACE:
            print(f"[dap {self.name} >>] {json.dumps(msg)[:300]}", flush=True)
        body = json.dumps(msg).encode("utf-8")
        self.sock.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)

    def request(self, command, arguments=None, cb=None):
        self.seq += 1
        if cb is not None:
            self.callbacks[self.seq] = cb
        self.send({"seq": self.seq, "type": "request", "command": command, "arguments": arguments or {}})

    def _read(self):
        self.buf += bytes(self.sock.readAll())
        while True:
            end = self.buf.find(b"\r\n\r\n")
            if end < 0:
                return
            length = 0
            for line in self.buf[:end].split(b"\r\n"):
                if line.lower().startswith(b"content-length:"):
                    length = int(line.split(b":")[1])
            if len(self.buf) < end + 4 + length:
                return
            body, self.buf = self.buf[end + 4:end + 4 + length], self.buf[end + 4 + length:]
            try:
                msg = json.loads(body)
            except ValueError:
                continue
            if TRACE:
                print(f"[dap {self.name} <<] {json.dumps(msg)[:300]}", flush=True)
            self.session._conn_message(self, msg)

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                self.sock.abort()
            except RuntimeError:
                pass


class JsDebugSession(_WebDapMixin, DapSession):
    """vscode-js-debug ``dapDebugServer.js`` attached to ``node --inspect``. The parent connection only
    attaches; the debuggee is a child session (``startDebugging``) on a second connection - all
    breakpoints, stepping and evaluation go there. A server restart ends the child; js-debug announces a new
    one when it re-attaches."""
    ready = pyqtSignal()
    exception_filters = JS_EXCEPTION_FILTERS

    def __init__(self, cwd, breakpoints, inspect_port: int, parent=None):
        super().__init__("js-debug", "", [], cwd, None, breakpoints, parent)
        self.inspect_port = inspect_port
        self.launch_args["port"] = inspect_port
        self.dap_port = free_port()
        self.argv = (self.argv + [str(self.dap_port), "127.0.0.1"]) if self.argv else None
        self.parent_conn: _Conn | None = None
        self.child: _Conn | None = None
        self._out = b""

    # ---------------------------------------------------------------- transport
    def start(self):
        if not self.argv:
            self.failed.emit("debug adapter 'js-debug' is not installed")
            self.finished.emit(1)
            return
        self.proc.start(self.argv[0], self.argv[1:])

    def _read(self):            # the adapter's stdout: "Debug server listening at 127.0.0.1:<port>"
        self._out += bytes(self.proc.readAllStandardOutput())
        while b"\n" in self._out:
            line, self._out = self._out.split(b"\n", 1)
            text = line.decode("utf-8", "replace").strip()
            if "listening" in text.lower() and self.parent_conn is None:
                self.parent_conn = _Conn(self, "parent", self.dap_port)
                self.parent_conn.request("initialize", self._init_args(), self._on_initialize)
            elif text and not self.user_stopped:
                self.output.emit(f"[js-debug] {text}\n")

    def _init_args(self):
        return {"clientID": "radide", "adapterID": "pwa-node", "linesStartAt1": True, "columnsStartAt1": True,
                "pathFormat": "path", "supportsStartDebuggingRequest": True, "supportsRunInTerminalRequest": False,
                "supportsVariableType": True}

    def _send(self, msg):                  # Session API requests go to the debuggee (child) session
        conn = self.child
        if conn is not None and not conn.closed:
            conn.send(msg)

    def _request(self, command, arguments=None, cb=None):
        conn = self.child
        if conn is None or conn.closed:
            return                             # no debuggee yet: breakpoints are sent when it appears
        conn.request(command, arguments, cb)

    def _on_initialize(self, body, _msg):
        def attached(_b, m):
            if not m.get("success", True):
                self.failed.emit(_error_text(m))
        # js-debug answers "attach" only once node listens: start the server now, js-debug keeps trying
        self.parent_conn.request("attach", self.launch_args, attached)
        QTimer.singleShot(100, self.ready.emit)

    # ---------------------------------------------------------------- messages
    def _conn_message(self, conn: _Conn, msg: dict):
        t = msg.get("type")
        if t == "response":
            cb = conn.callbacks.pop(msg.get("request_seq"), None)
            if not msg.get("success", True) and msg.get("command") in ("attach", "initialize") \
                    and conn is self.parent_conn:
                self.failed.emit(_error_text(msg))
            if cb is not None:
                cb(msg.get("body") or {}, msg)
            return
        if t == "request":
            cmd = msg.get("command")
            ok = cmd == "startDebugging"
            conn.send({"seq": 0, "type": "response", "request_seq": msg.get("seq"), "command": cmd,
                       "success": ok, **({} if ok else {"message": "not supported"})})
            if ok:
                self._start_child((msg.get("arguments") or {}).get("configuration") or {})
            return
        if t != "event":
            return
        ev, body = msg.get("event"), msg.get("body") or {}
        if ev == "output":
            if body.get("category") not in ("telemetry",) and conn is self.child:
                self.output.emit(body.get("output", ""))
            return
        if conn is self.parent_conn:
            if ev == "initialized":
                conn.request("configurationDone")
            elif ev == "terminated":
                self._finish(0)
            return
        if conn is not self.child:
            return
        if ev == "initialized":
            self._request("setExceptionBreakpoints", {"filters": self._filters()})
            self._send_breakpoints(lambda: self._request("configurationDone"))
        elif ev == "stopped":
            self.thread_id = body.get("threadId", self.thread_id)
            self._on_stopped(body.get("reason", "step"))
        elif ev == "continued":
            if self.paused:
                self.paused = False
                self.resumed.emit()
        elif ev == "terminated":                       # the server process ended (restart / exit)
            self._drop_child()

    def _start_child(self, configuration: dict):
        self._drop_child()
        conn = _Conn(self, "child", self.dap_port)
        self.child = conn
        conn.request("initialize", self._init_args(),
                     lambda _b, _m: conn.request("attach", configuration))

    def _drop_child(self):
        child, self.child = self.child, None
        if child is not None:
            child.close()
        if self.paused:
            self.paused = False
            self.resumed.emit()

    def _conn_closed(self, conn: _Conn):
        conn.closed = True
        if conn is self.child:
            self._drop_child()
        elif conn is self.parent_conn and not self._done:
            self._finish(0)

    def running(self) -> bool:
        return super().running()

    def stop(self):
        self.user_stopped = True
        for conn in (self.child, self.parent_conn):
            if conn is not None and not conn.closed:
                conn.request("disconnect", {"terminateDebuggee": False})
                conn.sock.flush()
        if self.running():
            if not self.proc.waitForFinished(800):
                self.proc.kill()
                self.proc.waitForFinished(1500)
        for conn in (self.child, self.parent_conn):
            if conn is not None:
                conn.close()
        self._finish(0)


# ============================================================================ IDE integration
def site_kind(plugin) -> str:
    return getattr(plugin, "web_kind", "") if plugin is not None else ""


def _offscreen() -> bool:
    return os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"


def _in_background(win, fn, *args):
    """Run fn(*args) in a thread while the UI keeps painting; returns its result or raises its error."""
    from PyQt6.QtCore import QEventLoop
    from PyQt6.QtWidgets import QApplication
    box: dict = {}

    def work():
        try:
            box["result"] = fn(*args)
        except Exception as e:  # noqa: BLE001 - reported to the caller
            box["error"] = e
    t = threading.Thread(target=work, daemon=True, name="radide-webdebug-download")
    t.start()
    QApplication.setOverrideCursor(__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.CursorShape.WaitCursor)
    try:
        while t.is_alive():
            QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
            t.join(0.05)
    finally:
        QApplication.restoreOverrideCursor()
    if "error" in box:
        raise box["error"]
    return box.get("result")


def ensure_tools(win, kind: str, php: str = "") -> bool:
    """Download (after asking) what a debug run needs. False = cannot debug (run without debugger)."""
    if not node_exe():
        win.log("*** Debugging a web site needs Node.js (node.exe) for the debug adapter - "
                "install it from https://nodejs.org (the site runs without the debugger now).")
        return False
    need = missing_tools(kind, php)
    if not need:
        return True
    text = "\n".join(f"  - {n} ({size})" for n, size, _f in need)
    if not _offscreen():
        from PyQt6.QtWidgets import QMessageBox
        r = QMessageBox.question(win, "Debug Web Site",
                                 "To debug this site RAD IDE needs:\n" + text +
                                 f"\n\nDownload now into {TOOLS}?\n(official open-source releases; "
                                 "No = run the site without the debugger)")
        if r != QMessageBox.StandardButton.Yes:
            return False
    for name, _size, fn in need:
        win.statusBar().showMessage(f"Downloading {name}...")
        lines: list[str] = []
        try:
            path = _in_background(win, fn, lines.append)
        except Exception as e:  # noqa: BLE001 - network / archive errors
            for ln in lines:
                win.log(f"[debug] {ln}")
            win.log(f"*** Cannot download {name}: {e}")
            return False
        for ln in lines:
            win.log(f"[debug] {ln}")
        win.log(f"[debug] {name} -> {path}")
    win.statusBar().clearMessage()
    return not missing_tools(kind, php)


def php_backend_hook(dll: str, port: int):
    def hook(_server, spec: dict) -> dict:
        argv = list(spec["argv"])
        extra = (["-d", f"zend_extension={dll}"] if dll else []) + [
            "-d", "xdebug.mode=debug", "-d", "xdebug.start_with_request=yes", "-d", "xdebug.client_host=127.0.0.1",
            "-d", f"xdebug.client_port={port}", "-d", "xdebug.log_level=0", "-d", "xdebug.max_nesting_level=512"]
        i = argv.index("-S") if "-S" in argv else len(argv)
        return {**spec, "argv": argv[:i] + extra + argv[i:]}
    return hook


def node_backend_hook(inspect_port: int, wait: bool):
    def hook(_server, spec: dict) -> dict:
        argv = list(spec["argv"])
        flag = f"--inspect{'-wait' if wait else ''}=127.0.0.1:{inspect_port}"
        return {**spec, "argv": argv[:1] + [flag] + argv[1:], "timeout": max(60, int(spec.get("timeout", 30)))}
    return hook


def _wire(win, s) -> None:
    """The same connections MainWindow.run_project makes for a program session."""
    from .. import tools
    s.output.connect(win._append_output)
    s.stopped.connect(lambda info: win._on_stopped(info))
    s.resumed.connect(win._on_resumed)
    s.evalResult.connect(lambda txt: tools.on_eval_result(win, txt) or win.immediate.show_result(txt))
    s.finished.connect(win._on_finished)
    s.failed.connect(lambda err: win.log(f"*** Error: {err}"))


def start(win, project, path=None):
    """F5 on a web site: server + debugger. Returns the DevServer, or None when the site cannot be debugged
    (static site, custom start command, missing tools declined) - the caller then just runs it."""
    from ..languages import get_plugin
    from ..features import web_workspace as ww
    if project is None:
        return None
    plugin = get_plugin(project.language)
    kind = site_kind(plugin)
    custom = getattr(plugin, "start_debug", None)       # frameworks with their own debugger (Django/Flask/FastAPI)
    if callable(custom):
        return custom(win, project, path)
    if kind == "static":                               # JavaScript in the Preview (browser_debug.py)
        from .browser_debug import start_static
        return start_static(win, project, path)
    if kind not in ("php", "node"):
        return None
    if win.session is not None and win.session.running():
        return True                                    # already debugging
    interp = ww.server_interpreter(win, plugin, project)
    if not interp:
        return None                                    # run_website reports the missing interpreter
    if kind == "node":
        from .project import web_config
        if web_config(project).get("framework"):        # Vite / Angular: debug the app in the Preview
            from .browser_debug import start_static
            return start_static(win, project, path)
        if str(web_config(project).get("command") or ""):
            win.log("[debug] This site starts with a custom command - the debugger attaches only to sites "
                    "started as 'node <start file>'. Running without the debugger.")
            return None
    if not ensure_tools(win, kind, interp if kind == "php" else ""):
        win.log("[debug] Running the site without the debugger.")
        return None
    if getattr(win, "web_server", None) is not None:
        ww.stop_website(win)                           # restart it with the debugger enabled
    win._sync_breakpoints()
    bps = win._all_breakpoints()
    folder = Path(project.folder).resolve()
    if kind == "php":
        dll = find_xdebug(interp)
        port = free_port()
        s = PhpDebugSession(folder, bps, port, win)
        hook = php_backend_hook(dll or "", port)
        engine = f"Xdebug {Path(dll).name if dll else '(php.ini)'} + vscode-php-debug {PHP_DEBUG_VERSION}"
    else:
        node = interp
        port = free_port()
        s = JsDebugSession(folder, bps, port, win)
        hook = node_backend_hook(port, node_supports_inspect_wait(node))
        engine = f"node --inspect + vscode-js-debug {JS_DEBUG_VERSION}"
    s.break_on_exception = win.settings.value("debug/break_on_exception", True) in (True, "true")
    from .browser_debug import wrap_server_session     # + JavaScript of the pages in the Preview
    s = wrap_server_session(win, project, s)
    if s.__class__.__name__ == "CompositeDebugSession":
        engine += " + Preview JavaScript"
    win.output.clear()
    win.locals.clear()
    win.callstack.clear()
    win.dock_output.show()
    win.dock_output.raise_()
    win.log(f"------ Debug web site '{project.name}' ({engine}) ------")
    _wire(win, s)
    win.session = s
    state = {"server": None}

    def start_server():
        if win.session is not s or state["server"] is not None:
            return
        srv = ww.run_website(win, project, debug=False, path=path, backend_hook=hook)
        state["server"] = srv
        if srv is None:
            s.stop()
            return
        srv.stopped.connect(lambda: win.session is s and s.running() and QTimer.singleShot(0, s.stop))
        win.statusBar().showMessage(f"Debugging {project.name} at {srv.url} - set breakpoints with F9")

    def session_ended(_code):
        srv = state["server"]
        if srv is not None and getattr(win, "web_server", None) is srv:
            QTimer.singleShot(0, lambda: getattr(win, "web_server", None) is srv and ww.stop_website(win))
    s.ready.connect(start_server)
    s.finished.connect(session_ended)
    s.start()
    win._update_actions()
    # a server that is not reachable by the debugger is still better than nothing
    def too_slow():
        if state["server"] is None and win.session is s:
            win.log("*** The debug adapter did not start in time; running the site without it.")
            state["server"] = False
            s.stop()
            ww.run_website(win, project, debug=False, path=path)
    QTimer.singleShot(15000, too_slow)
    return True


__all__ = ["JsDebugSession", "PhpDebugSession", "TOOLS", "download_js_debug", "download_php_debug",
           "download_xdebug", "ensure_tools", "find_xdebug", "missing_tools", "php_info", "start"]
