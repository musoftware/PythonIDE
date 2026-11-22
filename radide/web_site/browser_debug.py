"""Client-side JavaScript debugging of the pages shown in the Preview dock.

When the user turned it on (Tools > Options > Web "Debug JavaScript in the Preview", off by default: any local
program could drive the IDE's pages through the port), the IDE's own Chromium (QtWebEngine) is started with a
DevTools port on 127.0.0.1 (``QTWEBENGINE_REMOTE_DEBUGGING``, set by :func:`enable_remote_debugging` before
QApplication exists; :func:`seal_child_environment` then removes it from the environment so programs started
from the IDE do not inherit it). On F5
the **vscode-js-debug** adapter attaches to it in ``pwa-chrome`` *attach* mode, limited by ``urlFilter`` to
the site's DevServer URL (the IDE's own pages - Monaco editors, designer, AI chats - are never touched).
F9 breakpoints in ``.js`` files (and in ``<script>`` blocks of .html pages) of a static, PHP or Node.js site then
pause when the Preview runs them: Locals / Call Stack / Watch / Immediate, F10 / F11 / Shift+F11, Continue.

- static sites: :func:`start_static` - the browser session is the IDE's debug session;
- PHP / Node.js sites: :class:`CompositeDebugSession` joins the server-side session (Xdebug / node) and the
  browser session - whichever pauses is the one that F10 / F5 / Immediate drive.

Turn it on with Tools > Options > Web "Debug JavaScript in the Preview" (QSettings ``web/js_debug``, default off,
read at start-up) or ``RADIDE_JS_DEBUG=1``; ``RADIDE_NO_JS_DEBUG=1`` always keeps it off.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .debug import JS_DEBUG_VERSION, JsDebugSession, ensure_tools, free_port, node_exe

ENV = "QTWEBENGINE_REMOTE_DEBUGGING"
BROWSER_SKIP_FILES = ["**/node_modules/**", "**/__radide/**"]


# ============================================================================ the DevTools port
_PORT = 0                       # this process' DevTools port (the environment variable is removed after start-up)


def js_debug_enabled(settings=None) -> bool:
    """The user's choice (Tools > Options > Web): off unless turned on (or RADIDE_JS_DEBUG=1)."""
    if os.environ.get("RADIDE_NO_JS_DEBUG"):
        return False
    if os.environ.get("RADIDE_JS_DEBUG", "") not in ("", "0"):
        return True
    if settings is None:
        return False
    try:
        return settings.value("web/js_debug", False) in (True, "true", "1", 1)
    except Exception:  # noqa: BLE001 - settings are optional here
        return False


def enable_remote_debugging(settings=None) -> int:
    """Called by radide.app.main() before QApplication with the IDE settings: give QtWebEngine a DevTools port on
    127.0.0.1 only when the user turned JavaScript debugging in the Preview on. A call without settings (tests that
    debug the Preview) turns it on. Returns the port (0 = disabled). An existing QTWEBENGINE_REMOTE_DEBUGGING value
    is kept."""
    global _PORT
    if os.environ.get("RADIDE_NO_JS_DEBUG"):
        return 0
    cur = os.environ.get(ENV, "")
    if cur:
        _PORT = _parse_port(cur)
        return _PORT
    if settings is not None and not js_debug_enabled(settings):
        return 0
    port = free_port()
    os.environ[ENV] = f"127.0.0.1:{port}"
    _PORT = port
    return port


def seal_child_environment() -> None:
    """Right after QApplication: start QtWebEngine's context (it reads QTWEBENGINE_REMOTE_DEBUGGING and the
    --remote-debugging-* flags of QTWEBENGINE_CHROMIUM_FLAGS once), then remove them from the environment so that
    programs started from the IDE (a user's PyQt / Electron / Chromium program, terminals, tools) never open a
    DevTools port of their own or learn the IDE's."""
    global _PORT
    from ..paths import clean_webengine_debug_environment, webengine_debug_flags
    cur = os.environ.get(ENV, "")
    if cur and not _PORT:
        _PORT = _parse_port(cur)
    if cur or webengine_debug_flags(os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")):
        try:
            from PyQt6.QtWebEngineCore import QWebEngineProfile
            QWebEngineProfile.defaultProfile()              # creates the WebEngine context now
        except Exception:  # noqa: BLE001 - no QtWebEngine: nothing reads the variables anyway
            pass
    clean_webengine_debug_environment(os.environ)


def _parse_port(v: str) -> int:
    try:
        return int(v.rsplit(":", 1)[-1]) if v else 0
    except ValueError:
        return 0


def devtools_port() -> int:
    """The DevTools port of this process' QtWebEngine, 0 when remote debugging is off."""
    return _PORT or _parse_port(os.environ.get(ENV, ""))


def devtools_targets(port: int | None = None, timeout: float = 2.0) -> list[dict]:
    """The page targets the DevTools port lists (/json/list); [] when unreachable."""
    port = port or devtools_port()
    if not port:
        return []
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except (OSError, ValueError):
        return []


def available() -> bool:
    return bool(devtools_port()) and bool(node_exe())


# ============================================================================ the session
class BrowserJsDebugSession(JsDebugSession):
    """js-debug attached to the IDE's QtWebEngine (``pwa-chrome`` attach). Every matching page is a child
    session announced by ``startDebugging``. ``pageAttached`` fires once the first page has its breakpoints
    (the caller then reloads the Preview so that code running on page load stops too)."""
    pageAttached = pyqtSignal()
    exception_filters = ["uncaught"]

    def __init__(self, cwd, breakpoints, url: str, web_root=None, port: int | None = None, parent=None):
        super().__init__(cwd, breakpoints, 0, parent)
        self.url = url.rstrip("/")
        root = str(Path(web_root or cwd).resolve())
        self.launch_args = {"type": "pwa-chrome", "request": "attach", "address": "127.0.0.1",
                            "port": port or devtools_port(), "webRoot": root, "urlFilter": self.url + "/*",
                            "targetSelection": "automatic", "skipFiles": BROWSER_SKIP_FILES, "sourceMaps": True,
                            "timeout": 15000, "pauseForSourceMap": False,
                            "resolveSourceMapLocations": [root.replace("\\", "/") + "/**", "!**/node_modules/**"]}
        self._attached_once = False

    def _init_args(self):
        args = super()._init_args()
        args["adapterID"] = "pwa-chrome"
        return args

    def _conn_message(self, conn, msg):
        if conn is self.child and msg.get("type") == "event" and msg.get("event") == "initialized":
            self._request("setExceptionBreakpoints", {"filters": self._filters()})
            self._send_breakpoints(lambda: self._request("configurationDone", None, self._configured))
            return
        super()._conn_message(conn, msg)

    def _configured(self, _b, _m):
        if not self._attached_once:
            self._attached_once = True
            self.pageAttached.emit()

    def stop(self):                      # never close the IDE's browser: disconnect only
        super().stop()


class CompositeDebugSession(QObject):
    """Two debug sessions as one ``win.session``: the site's server (PHP / Node) and the Preview's JavaScript.
    Breakpoints go to both (each adapter ignores files it does not run); the paused one gets the commands."""
    output = pyqtSignal(str)
    stopped = pyqtSignal(object)
    resumed = pyqtSignal()
    evalResult = pyqtSignal(str)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)
    ready = pyqtSignal()

    def __init__(self, server_session, parent=None):
        super().__init__(parent)
        self.debug = True
        self.server = server_session
        self.browser: BrowserJsDebugSession | None = None
        self.active = server_session
        self.user_stopped = False
        self._done = False
        self._hook(server_session)
        if hasattr(server_session, "ready"):
            server_session.ready.connect(self.ready.emit)
        server_session.finished.connect(self._server_finished)

    @property
    def break_on_exception(self):
        return self.server.break_on_exception

    @break_on_exception.setter
    def break_on_exception(self, on):
        self.server.break_on_exception = on
        if self.browser is not None:
            self.browser.break_on_exception = on

    def _hook(self, s):
        s.output.connect(self.output.emit)
        s.failed.connect(self.failed.emit)
        s.evalResult.connect(self.evalResult.emit)
        s.stopped.connect(lambda info, s=s: self._on_stopped(s, info))
        s.resumed.connect(lambda s=s: self._on_resumed(s))

    def add_browser(self, b: BrowserJsDebugSession):
        self.browser = b
        b.break_on_exception = self.server.break_on_exception
        self._hook(b)
        b.finished.connect(lambda _c: setattr(self, "browser", None) if self.browser is b else None)
        b.start()

    def _on_stopped(self, s, info):
        self.active = s
        self.stopped.emit(info)

    def _on_resumed(self, s):
        if s is self.active:
            other = self.browser if s is self.server else self.server
            if other is not None and other.paused:
                self.active = other          # the other side is still paused: show it again
                return
            self.resumed.emit()

    @property
    def paused(self) -> bool:
        return bool(self.active is not None and self.active.paused)

    def running(self) -> bool:
        return self.server.running() and not self._done

    def start(self):
        self.server.start()

    def cont(self):
        self.active.cont()

    def step_into(self):
        self.active.step_into()

    def step_over(self):
        self.active.step_over()

    def step_out(self):
        self.active.step_out()

    def evaluate(self, expr: str):
        if not self.active.paused:
            self.evalResult.emit("(the program must be paused at a breakpoint)")
            return
        self.active.evaluate(expr)

    def set_breakpoint(self, filename: str, line: int, on: bool, cond: str = ""):
        for s in (self.server, self.browser):
            if s is not None:
                s.set_breakpoint(filename, line, on, cond)

    def set_break_on_exception(self, on: bool):
        for s in (self.server, self.browser):
            if s is not None:
                s.set_break_on_exception(on)

    def stop(self):
        self.user_stopped = True
        b, self.browser = self.browser, None
        if b is not None:
            b.stop()
        self.server.stop()
        self._server_finished(0)

    def _server_finished(self, code):
        if self._done:
            return
        self._done = True
        b, self.browser = self.browser, None
        if b is not None:
            b.stop()
        self.finished.emit(code)


# ============================================================================ IDE integration
def _web_root(project) -> Path:
    from .project import web_config
    folder = Path(project.folder).resolve()
    cfg = web_config(project)
    root = (folder / str(cfg.get("root") or ".")).resolve()
    if project.language == "node-web" and not cfg.get("framework") and root == folder:
        for d in ("public", "static", "www", "wwwroot", "client"):    # Express: app.use(express.static(...))
            if (folder / d).is_dir():
                return folder / d
    return root


def has_client_breakpoints(win) -> bool:
    try:
        return any(str(bp[0]).lower().endswith((".js", ".mjs", ".html", ".htm", ".jsx", ".ts", ".tsx", ".vue",
                                                ".svelte"))
                   for bp in win._all_breakpoints())
    except Exception:  # noqa: BLE001
        return False


def make_browser_session(win, project, srv) -> BrowserJsDebugSession | None:
    """A browser session for the running DevServer *srv*; it reloads the Preview once it is attached."""
    if not available():
        return None
    folder = Path(project.folder).resolve()
    win._sync_breakpoints()
    b = BrowserJsDebugSession(folder, win._all_breakpoints(), srv.url, _web_root(project), parent=win)

    def attached():
        cur = win.web_preview.current_url()
        if cur.startswith(srv.url):
            win.web_preview.reload()           # run page-load code again, now with breakpoints
        win.log(f"[debug] JavaScript debugger attached to the Preview ({srv.url})")
    b.pageAttached.connect(attached)
    return b


def attach_after_server(win, project, composite: CompositeDebugSession) -> None:
    """For PHP / Node sites: once the DevServer runs, add the browser session to *composite*."""
    if not available() or not ensure_tools(win, "node"):
        return

    def on_started(srv):
        try:
            win.web_signals.serverStarted.disconnect(on_started)
        except (TypeError, RuntimeError):
            pass
        if win.session is not composite or composite._done:
            return
        b = make_browser_session(win, project, srv)
        if b is not None:
            composite.add_browser(b)
    win.web_signals.serverStarted.connect(on_started)


def wrap_server_session(win, project, s):
    """Called by web_site.debug.start(): returns *s* or a composite session that also debugs the Preview."""
    if not available():
        return s
    if not os.path.isfile(str(_js_debug_js())) and not has_client_breakpoints(win):
        return s                                   # do not download js-debug only for this
    c = CompositeDebugSession(s, win)
    attach_after_server(win, project, c)
    return c


def _js_debug_js():
    from .debug import JS_DEBUG_JS
    return JS_DEBUG_JS


def start_static(win, project, path=None):
    """F5 on a static (HTML / CSS / JS) site: DevServer + Preview + JavaScript debugger. Returns True when
    the debugger runs, None when it cannot (the caller runs the site without it)."""
    from ..features import web_workspace as ww
    if not available():
        if not devtools_port():
            win.log("[debug] JavaScript debugging in the Preview is off - running without the debugger. Turn on "
                    "Tools > Options > Web > \"Debug JavaScript in the Preview\" and restart RAD IDE (it opens a "
                    "DevTools port on 127.0.0.1 for the IDE's browser engine).")
        return None
    if win.session is not None and win.session.running():
        return True
    if not ensure_tools(win, "node"):
        return None
    srv = ww.run_website(win, project, debug=False, path=path, open_preview=True)
    if srv is None:
        return True                                # run_website reported why
    b = make_browser_session(win, project, srv)
    if b is None:
        return True
    b.break_on_exception = win.settings.value("debug/break_on_exception", True) in (True, "true")
    from .debug import _wire
    win.locals.clear()
    win.callstack.clear()
    win.log(f"------ Debug web site '{project.name}' (Preview + vscode-js-debug {JS_DEBUG_VERSION}) ------")
    _wire(win, b)
    win.session = b
    srv.stopped.connect(lambda: win.session is b and b.running() and QTimer.singleShot(0, b.stop))

    def ended(_code):
        if getattr(win, "web_server", None) is srv:
            QTimer.singleShot(0, lambda: getattr(win, "web_server", None) is srv and ww.stop_website(win))
    b.finished.connect(ended)
    b.start()
    win._update_actions()
    win.statusBar().showMessage(f"Debugging {project.name} at {srv.url} - F9 in .js files pauses the Preview")
    return True


__all__ = ["BrowserJsDebugSession", "CompositeDebugSession", "available", "devtools_port", "devtools_targets",
           "enable_remote_debugging", "js_debug_enabled", "seal_child_environment", "start_static",
           "wrap_server_session"]
