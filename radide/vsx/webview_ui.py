"""VS Code webviews inside RAD IDE.

The Node extension host (host/webview.js) owns the extension-side objects; this module shows every
webview (sidebar WebviewView or editor WebviewPanel) in a QWebEngineView dock and relays messages:

    page  acquireVsCodeApi().postMessage(m)  -> QWebChannel -> webview/message -> webview.onDidReceiveMessage
    ext   webview.postMessage(m)             -> webview/postMessage -> window 'message' event in the page

Pages and their local resources are served by a tiny HTTP server bound to 127.0.0.1 under a random
token (ES module scripts do not load from file://). Only files below the roots the extension declared
(its own folder + localResourceRoots) are served. The page gets the --vscode-* colour variables and
the vscode-light / vscode-dark body classes of the current IDE theme.
"""
from __future__ import annotations

import json
import mimetypes
import os
import secrets
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QDockWidget, QLabel

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/ttf", ".ttf")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/wasm", ".wasm")


# ============================================================================ resource server
class ResourceServer:
    """http://127.0.0.1:<port>/<token>/f/<absolute path>   a local file below an allowed root
       http://127.0.0.1:<port>/<token>/page/<handle>        the html of a webview"""

    def __init__(self):
        self.token = secrets.token_hex(12)
        self.roots: set[Path] = set()
        self.pages: dict[str, str] = {}
        self._lock = threading.Lock()
        srv = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_a):        # quiet
                pass

            def do_GET(self):  # noqa: N802
                srv._serve(self)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, name="vsx-webview-http", daemon=True).start()

    @property
    def origin(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def base(self) -> str:
        return f"{self.origin}/{self.token}"

    def allow(self, root) -> None:
        if not root:
            return
        try:
            with self._lock:
                self.roots.add(Path(root).resolve())
        except OSError:
            pass

    def set_page(self, handle: str, html: str) -> None:
        with self._lock:
            self.pages[handle] = html

    def drop_page(self, handle: str) -> None:
        with self._lock:
            self.pages.pop(handle, None)

    def page_url(self, handle: str, rev: int) -> QUrl:
        return QUrl(f"{self.base}/page/{handle}?v={rev}")

    def _allowed(self, p: Path) -> bool:
        with self._lock:
            roots = list(self.roots)
        for r in roots:
            try:
                p.relative_to(r)
                return True
            except ValueError:
                continue
        return False

    def _serve(self, h: BaseHTTPRequestHandler) -> None:
        path = urllib.parse.urlsplit(h.path).path
        prefix = f"/{self.token}/"
        if not path.startswith(prefix):
            h.send_error(404)
            return
        rest = path[len(prefix):]
        if rest.startswith("page/"):
            with self._lock:
                html = self.pages.get(rest[5:])
            if html is None:
                h.send_error(404)
                return
            self._send(h, html.encode("utf-8"), "text/html; charset=utf-8")
            return
        if rest.startswith("f/"):
            raw = urllib.parse.unquote(rest[2:])
            if len(raw) > 2 and raw[0] == "/" and raw[2] == ":":      # /d:/x -> d:/x
                raw = raw[1:]
            try:
                p = Path(raw).resolve()
            except OSError:
                h.send_error(404)
                return
            if not self._allowed(p) or not p.is_file():
                h.send_error(404)
                return
            ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            try:
                data = p.read_bytes()
            except OSError:
                h.send_error(404)
                return
            self._send(h, data, ctype)
            return
        h.send_error(404)

    @staticmethod
    def _send(h, data: bytes, ctype: str) -> None:
        try:
            h.send_response(200)
            h.send_header("Content-Type", ctype)
            h.send_header("Content-Length", str(len(data)))
            h.send_header("Cache-Control", "no-cache")
            h.send_header("Access-Control-Allow-Origin", "*")
            h.end_headers()
            h.wfile.write(data)
        except (ConnectionError, OSError):
            pass

    def close(self) -> None:
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:  # noqa: BLE001
            pass


# ============================================================================ theme -> --vscode-* vars
def vscode_vars() -> tuple[dict, bool]:
    try:
        from .. import theme as TH
        t = TH.current()
        dark = TH.is_dark()
    except Exception:  # noqa: BLE001
        t, dark = {}, True

    def g(k, d):
        return t.get(k) or d
    bg = g("base", "#1e1e1e" if dark else "#ffffff")
    fg = g("text", "#cccccc" if dark else "#333333")
    side = g("window", "#252526" if dark else "#f3f3f3")
    border = g("border", "#3c3c3c" if dark else "#d4d4d4")
    accent = g("accent", "#0e639c")
    accent_fg = g("accent_text", "#ffffff")
    muted = g("muted", "#9d9d9d" if dark else "#717171")
    hl = g("highlight", "#04395e" if dark else "#0060c0")
    hl_fg = g("highlight_text", "#ffffff")
    link = g("link", "#3794ff" if dark else "#006ab1")
    err = g("error", "#f48771" if dark else "#a1260d")
    alt = g("alt_base", "#2d2d2d" if dark else "#f8f8f8")
    tip = g("tooltip", "#252526" if dark else "#f3f3f3")
    tip_fg = g("tooltip_text", fg)
    font = "'Segoe UI', system-ui, -apple-system, sans-serif"
    mono = "Consolas, 'Courier New', monospace"
    v = {
        "font-family": font, "font-size": "13px", "font-weight": "normal",
        "editor-font-family": mono, "editor-font-size": "13px", "editor-font-weight": "normal",
        "foreground": fg, "descriptionForeground": muted, "disabledForeground": muted, "errorForeground": err,
        "icon-foreground": fg, "focusBorder": accent, "contrastBorder": "transparent", "widget-border": border,
        "widget-shadow": "rgba(0,0,0,.36)" if dark else "rgba(0,0,0,.16)", "selection-background": hl,
        "editor-background": bg, "editor-foreground": fg, "editorWidget-background": side,
        "editorWidget-foreground": fg, "editorWidget-border": border, "editorGroup-border": border,
        "editorGroupHeader-tabsBackground": side, "editor-selectionBackground": hl,
        "editor-inactiveSelectionBackground": alt, "editor-lineHighlightBackground": alt,
        "editorLineNumber-foreground": muted, "editorCursor-foreground": fg,
        "editorHoverWidget-background": tip, "editorHoverWidget-foreground": tip_fg, "editorHoverWidget-border": border,
        "editorSuggestWidget-background": side, "editorSuggestWidget-foreground": fg,
        "editorSuggestWidget-border": border, "editorSuggestWidget-selectedBackground": hl,
        "editorError-foreground": err, "editorWarning-foreground": "#cca700", "editorInfo-foreground": link,
        "sideBar-background": side, "sideBar-foreground": fg, "sideBar-border": border,
        "sideBarTitle-foreground": fg, "sideBarSectionHeader-background": alt, "sideBarSectionHeader-foreground": fg,
        "panel-background": bg, "panel-border": border, "panelTitle-activeForeground": fg,
        "panelTitle-inactiveForeground": muted, "panelTitle-activeBorder": accent,
        "input-background": alt, "input-foreground": fg, "input-border": border,
        "input-placeholderForeground": muted, "inputOption-activeBorder": accent,
        "inputOption-activeBackground": hl, "inputValidation-errorBackground": alt,
        "inputValidation-errorBorder": err, "inputValidation-warningBorder": "#cca700",
        "dropdown-background": alt, "dropdown-foreground": fg, "dropdown-border": border, "dropdown-listBackground": side,
        "checkbox-background": alt, "checkbox-foreground": fg, "checkbox-border": border,
        "button-background": accent, "button-foreground": accent_fg, "button-hoverBackground": accent,
        "button-border": "transparent", "button-separator": "rgba(255,255,255,.4)",
        "button-secondaryBackground": alt, "button-secondaryForeground": fg, "button-secondaryHoverBackground": border,
        "badge-background": accent, "badge-foreground": accent_fg,
        "activityBarBadge-background": accent, "activityBarBadge-foreground": accent_fg,
        "progressBar-background": accent,
        "list-activeSelectionBackground": hl, "list-activeSelectionForeground": hl_fg,
        "list-inactiveSelectionBackground": alt, "list-inactiveSelectionForeground": fg,
        "list-hoverBackground": alt, "list-hoverForeground": fg, "list-focusBackground": hl,
        "list-focusOutline": accent, "list-highlightForeground": link, "list-dropBackground": alt,
        "list-errorForeground": err, "list-warningForeground": "#cca700",
        "tree-indentGuidesStroke": border,
        "scrollbar-shadow": "rgba(0,0,0,.3)" if dark else "rgba(0,0,0,.1)",
        "scrollbarSlider-background": "rgba(121,121,121,.4)", "scrollbarSlider-hoverBackground": "rgba(100,100,100,.7)",
        "scrollbarSlider-activeBackground": "rgba(191,191,191,.4)",
        "textLink-foreground": link, "textLink-activeForeground": link,
        "textPreformat-foreground": "#d7ba7d" if dark else "#a31515", "textPreformat-background": alt,
        "textBlockQuote-background": alt, "textBlockQuote-border": accent,
        "textCodeBlock-background": alt, "textSeparator-foreground": border,
        "toolbar-hoverBackground": alt, "toolbar-activeBackground": border,
        "menu-background": g("menu", side), "menu-foreground": g("menu_text", fg), "menu-border": g("menu_border", border),
        "menu-selectionBackground": g("menu_sel", hl), "menu-selectionForeground": g("menu_sel_text", hl_fg),
        "menu-separatorBackground": border,
        "quickInput-background": side, "quickInput-foreground": fg,
        "quickInputList-focusBackground": hl, "quickInputList-focusForeground": hl_fg,
        "keybindingLabel-background": alt, "keybindingLabel-foreground": fg, "keybindingLabel-border": border,
        "keybindingLabel-bottomBorder": border, "notifications-background": side, "notifications-foreground": fg,
        "notifications-border": border, "statusBar-background": accent, "statusBar-foreground": accent_fg,
        "titleBar-activeBackground": side, "titleBar-activeForeground": fg,
        "tab-activeBackground": bg, "tab-activeForeground": fg, "tab-inactiveBackground": side,
        "tab-inactiveForeground": muted, "tab-border": border,
        "diffEditor-insertedTextBackground": "rgba(156,204,44,.2)", "diffEditor-removedTextBackground": "rgba(255,0,0,.2)",
        "diffEditor-insertedLineBackground": "rgba(155,185,85,.2)", "diffEditor-removedLineBackground": "rgba(255,0,0,.2)",
        "gitDecoration-addedResourceForeground": "#81b88b", "gitDecoration-modifiedResourceForeground": "#e2c08d",
        "gitDecoration-deletedResourceForeground": "#c74e39", "gitDecoration-untrackedResourceForeground": "#73c991",
        "charts-foreground": fg, "charts-lines": muted, "charts-red": "#f14c4c", "charts-blue": "#3794ff",
        "charts-yellow": "#cca700", "charts-orange": "#d18616", "charts-green": "#89d185", "charts-purple": "#b180d7",
        "terminal-background": bg, "terminal-foreground": fg,
        "chat-requestBackground": alt, "chat-slashCommandBackground": alt, "chat-slashCommandForeground": link,
        "sash-hoverBorder": accent,
    }
    return v, dark


def theme_script() -> str:
    v, dark = vscode_vars()
    css = ";".join(f"--vscode-{k}:{val}" for k, val in v.items())
    kind = "vscode-dark" if dark else "vscode-light"
    return ("(function(){var css=%s,kind=%s;"
            "function root(){var d=document.documentElement;if(!d)return;"
            "d.setAttribute('style',css+';color-scheme:'+(kind==='vscode-dark'?'dark':'light'));}"
            "function body(){root();var b=document.body;if(!b)return;b.classList.remove('vscode-light','vscode-dark',"
            "'vscode-high-contrast');b.classList.add(kind);b.setAttribute('data-vscode-theme-kind',kind);"
            "b.setAttribute('data-vscode-theme-id',kind==='vscode-dark'?'Default Dark Modern':'Default Light Modern');}"
            "window.__radApplyTheme=function(c,k){css=c;kind=k;root();body();};"
            "try{root();}catch(e){}"
            "if(document.body)body();else document.addEventListener('DOMContentLoaded',body);})();"
            ) % (json.dumps(css), json.dumps(kind))


_DEFAULT_CSS = """
html{scrollbar-color:var(--vscode-scrollbarSlider-background) transparent}
body{margin:0;padding:0 20px;color:var(--vscode-foreground);font-family:var(--vscode-font-family);
 font-size:var(--vscode-font-size);background-color:transparent}
img,video{max-width:100%;max-height:100%}
a,a code{color:var(--vscode-textLink-foreground)}
code{font-family:var(--vscode-editor-font-family);color:var(--vscode-textPreformat-foreground)}
button,input,select,textarea{font-family:inherit;font-size:inherit}
"""


def _shim(state) -> str:
    return """
(function(){
  if (window.acquireVsCodeApi) return;
  var queue = [], bridge = null, state = %s, api = null;
  function send(kind, payload){ var s = JSON.stringify(payload === undefined ? null : payload);
    if (bridge) bridge[kind](s); else queue.push([kind, s]); }
  function start(){
    if (typeof QWebChannel === 'undefined' || !window.qt || !qt.webChannelTransport) { setTimeout(start, 20); return; }
    new QWebChannel(qt.webChannelTransport, function(ch){
      bridge = ch.objects.radBridge;
      bridge.toPage.connect(function(s){ var d; try { d = JSON.parse(s); } catch(e) { return; }
        window.dispatchEvent(new MessageEvent('message', {data: d, origin: location.origin})); });
      bridge.themeChanged.connect(function(css, kind){ if (window.__radApplyTheme) window.__radApplyTheme(css, kind); });
      var q = queue; queue = []; q.forEach(function(it){ bridge[it[0]](it[1]); });
      bridge.ready();
    });
  }
  window.acquireVsCodeApi = function(){
    if (api) return api;
    api = Object.freeze({
      postMessage: function(m){ send('post', m); },
      getState: function(){ return state; },
      setState: function(s){ state = s; send('setState', s); return s; }
    });
    return api;
  };
  // links: command: URIs go to the extension host, http(s) open in the system browser
  document.addEventListener('click', function(e){
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var h = a.getAttribute('href') || '';
    if (/^(https?:|mailto:|command:|vscode:)/i.test(h) && h.indexOf(location.origin) !== 0) {
      e.preventDefault(); send('openLink', h);
    }
  }, true);
  function styles(){
    if (document.getElementById('_defaultStyles')) return;
    var host = document.head || document.documentElement;
    if (!host) return false;
    var st = document.createElement('style'); st.id = '_defaultStyles'; st.textContent = %s;
    host.prepend(st);
  }
  start();
  if (styles() === false) document.addEventListener('DOMContentLoaded', styles);
})();
""" % (json.dumps(state), json.dumps(_DEFAULT_CSS))


# ============================================================================ page bridge
class _Bridge(QObject):
    toPage = pyqtSignal(str)
    themeChanged = pyqtSignal(str, str)

    def __init__(self, view: "WebviewView"):
        super().__init__()
        self.view = view

    @pyqtSlot(str)
    def post(self, s):
        try:
            msg = json.loads(s)
        except ValueError:
            return
        self.view.mgr.to_host("webview/message", {"handle": self.view.handle, "message": msg})

    @pyqtSlot(str)
    def setState(self, s):  # noqa: N802
        try:
            self.view.state = json.loads(s)
        except ValueError:
            pass

    @pyqtSlot(str)
    def openLink(self, s):  # noqa: N802
        try:
            href = json.loads(s)
        except ValueError:
            return
        self.view.mgr.open_link(str(href))

    @pyqtSlot()
    def ready(self):
        self.view.page_ready()


class WebviewView:
    """One webview: a dock holding a QWebEngineView (created lazily)."""

    def __init__(self, mgr: "WebviewManager", p: dict):
        self.mgr = mgr
        self.handle = p["handle"]
        self.kind = p.get("kind", "panel")
        self.view_type = p.get("viewType", "")
        self.title = p.get("title") or self.view_type
        self.options = p.get("options") or {}
        self.ext = p.get("ext", "")
        self.state = None
        self.html = ""
        self.rev = 0
        self._ready = False
        self._pending: list[str] = []
        self.web = None
        self.bridge = None
        self.dock = mgr.dock_for(self)
        self._build()

    def _build(self):
        try:
            from PyQt6.QtWebChannel import QWebChannel
            from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineScript, QWebEngineSettings
            from PyQt6.QtWebEngineWidgets import QWebEngineView
        except Exception as e:  # noqa: BLE001
            self.dock.setWidget(QLabel(f"Qt WebEngine is not available: {e}"))
            return
        mgr = self.mgr

        class Page(QWebEnginePage):
            def acceptNavigationRequest(self, url, nav_type, is_main):  # noqa: N802
                u = url.toString()
                if is_main and not u.startswith(mgr.server.origin) and u not in ("about:blank",) \
                        and nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
                    mgr.open_link(u)
                    return False
                return super().acceptNavigationRequest(url, nav_type, is_main)

            def createWindow(self, _type):  # noqa: N802 - window.open -> system browser
                tmp = QWebEnginePage(self)
                tmp.urlChanged.connect(lambda u, t=tmp: (mgr.open_link(u.toString()), t.deleteLater()))
                return tmp

            def javaScriptConsoleMessage(self, level, msg, line, src):  # noqa: N802
                lv = int(level.value if hasattr(level, "value") else level)
                if os.environ.get("RADIDE_WEBVIEW_DEBUG"):
                    print(f"[webview {view.view_type}] L{lv} {msg} ({src}:{line})", flush=True)
                if lv >= 2:
                    mgr.svc.log(f"[webview {view.view_type}] {msg} ({src}:{line})")

        view = self
        self.web = QWebEngineView()
        page = Page(self.web)
        self.web.setPage(page)
        s = page.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)
        self.bridge = _Bridge(self)
        ch = QWebChannel(page)
        ch.registerObject("radBridge", self.bridge)
        page.setWebChannel(ch)
        self._channel = ch
        scripts = page.scripts()
        for name, src, point in (("qwebchannel", _qwebchannel_js(), QWebEngineScript.InjectionPoint.DocumentCreation),
                                 ("vscodeTheme", theme_script(), QWebEngineScript.InjectionPoint.DocumentCreation),
                                 ("vscodeApi", None, QWebEngineScript.InjectionPoint.DocumentCreation)):
            sc = QWebEngineScript()
            sc.setName(name)
            sc.setInjectionPoint(point)
            sc.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            sc.setRunsOnSubFrames(False)
            sc.setSourceCode(src if src is not None else _shim(None))
            scripts.insert(sc)
        self.web.loadStarted.connect(self._load_started)
        self.dock.setWidget(self.web)

    def _load_started(self):
        self._ready = False
        try:
            from PyQt6.QtWebEngineCore import QWebEngineScript  # noqa: F401
            sc = self.web.page().scripts().find("vscodeApi")
            for s in sc:
                self.web.page().scripts().remove(s)
                s.setSourceCode(_shim(self.state))
                self.web.page().scripts().insert(s)
        except Exception:  # noqa: BLE001
            pass

    def set_html(self, html: str):
        self.html = html
        self.rev += 1
        self.mgr.server.set_page(self.handle, html)
        if self.web is not None:
            self._ready = False
            self.web.setUrl(self.mgr.server.page_url(self.handle, self.rev))

    def post(self, message):
        s = json.dumps(message)
        if self._ready and self.bridge is not None:
            self.bridge.toPage.emit(s)
        else:
            self._pending.append(s)

    def page_ready(self):
        self._ready = True
        pend, self._pending = self._pending, []
        for s in pend:
            self.bridge.toPage.emit(s)

    def theme_changed(self):
        if self.bridge is not None:
            v, dark = vscode_vars()
            self.bridge.themeChanged.emit(";".join(f"--vscode-{k}:{val}" for k, val in v.items()),
                                          "vscode-dark" if dark else "vscode-light")
            try:
                for s in self.web.page().scripts().find("vscodeTheme"):
                    self.web.page().scripts().remove(s)
                    s.setSourceCode(theme_script())
                    self.web.page().scripts().insert(s)
            except Exception:  # noqa: BLE001
                pass

    def set_title(self, title: str):
        self.title = title or self.title
        self.dock.setWindowTitle(self.title)

    def reveal(self):
        self.dock.show()
        self.dock.raise_()

    def dispose(self):
        self.mgr.server.drop_page(self.handle)
        try:
            if self.web is not None:
                self.web.setUrl(QUrl("about:blank"))
        except RuntimeError:
            pass


_QWC = None


def _qwebchannel_js() -> str:
    global _QWC
    if _QWC is None:
        from PyQt6.QtCore import QFile, QIODevice
        f = QFile(":/qtwebchannel/qwebchannel.js")
        _QWC = bytes(f.readAll()).decode("utf-8") if f.open(QIODevice.OpenModeFlag.ReadOnly) else ""
    return _QWC


# ============================================================================ manager
class WebviewManager(QObject):
    """Owned by the extension-host service (host_ide.ExtensionHostService)."""

    def __init__(self, svc):
        super().__init__(svc)
        self.svc = svc
        self.server = ResourceServer()
        self.items: dict[str, WebviewView] = {}
        self.view_docks: dict[str, QDockWidget] = {}     # viewId -> dock (sidebar views survive re-resolve)
        self.view_handles: dict[str, str] = {}           # viewId -> handle
        self.providers: set[str] = set()
        try:
            from .. import theme as TH
            TH.changed.connect(lambda *_a: [w.theme_changed() for w in list(self.items.values())])
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------ plumbing
    def to_host(self, method: str, params: dict):
        if self.svc.host.running():
            self.svc.host.notify(method, params)

    def open_link(self, href: str):
        from PyQt6.QtGui import QDesktopServices
        if href.startswith("command:"):
            rest = href[8:]
            cmd, _, q = rest.partition("?")
            args = []
            if q:
                try:
                    a = json.loads(urllib.parse.unquote(q))
                    args = a if isinstance(a, list) else [a]
                except ValueError:
                    args = []
            self.svc.execute(cmd, args)
        else:
            QDesktopServices.openUrl(QUrl(href))

    def dock_for(self, v: WebviewView) -> QDockWidget:
        win = self.svc.win
        if v.kind == "view" and v.view_type in self.view_docks:
            d = self.view_docks[v.view_type]
            d.setWindowTitle(v.title)
            return d
        import re
        d = QDockWidget(v.title, win)
        d.setObjectName("vsxWebview_" + re.sub(r"\W+", "_", v.view_type or v.handle))
        area = Qt.DockWidgetArea.RightDockWidgetArea
        win.addDockWidget(area, d)
        # stack panels of the same area as tabs, like editor tabs
        others = [x.dock for x in self.items.values() if x.dock is not d and x.dock.isVisible()
                  and win.dockWidgetArea(x.dock) == area]
        if others:
            win.tabifyDockWidget(others[-1], d)
        if v.kind == "view":
            d.visibilityChanged.connect(lambda vis, vt=v.view_type: self._visible(self.view_handles.get(vt), vis))
        else:
            d.visibilityChanged.connect(lambda vis, h=v.handle: self._visible(h, vis))
        if v.kind == "view":
            self.view_docks[v.view_type] = d
        else:
            d.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
            d.installEventFilter(self)
            d.setProperty("vsxHandle", v.handle)
        d.resize(460, 700)
        d.show()
        d.raise_()
        return d

    def eventFilter(self, obj, ev):  # noqa: N802 - closing a panel dock disposes the panel
        from PyQt6.QtCore import QEvent
        if ev.type() == QEvent.Type.Close:
            h = obj.property("vsxHandle")
            if h and h in self.items:
                w = self.items.pop(h)
                w.dispose()
                self.to_host("webview/closed", {"handle": h})
                obj.deleteLater()
        return False

    def _visible(self, handle: str, vis: bool):
        if handle in self.items:
            self.to_host("webview/visible", {"handle": handle, "visible": bool(vis)})

    # ------------------------------------------------------------ host -> IDE
    def handle(self, method: str, p: dict) -> bool:
        fn = getattr(self, "_n_" + method.replace("/", "_"), None)
        if fn is None:
            return False
        fn(p)
        return True

    def _n_webview_create(self, p):
        if p.get("extPath"):
            self.server.allow(p["extPath"])
        for r in p.get("roots") or []:
            self.server.allow(r)
        w = WebviewView(self, p)
        self.items[w.handle] = w
        if w.kind == "view":
            self.view_handles[w.view_type] = w.handle

    def _n_webview_html(self, p):
        w = self.items.get(p.get("handle"))
        if w is not None:
            w.set_html(p.get("html") or "")

    def _n_webview_options(self, p):
        w = self.items.get(p.get("handle"))
        if w is not None:
            w.options = p.get("options") or {}

    def _n_webview_postMessage(self, p):  # noqa: N802
        w = self.items.get(p.get("handle"))
        if w is not None:
            w.post(p.get("message"))

    def _n_webview_title(self, p):
        w = self.items.get(p.get("handle"))
        if w is not None:
            w.set_title(p.get("title") or "")

    def _n_webview_reveal(self, p):
        w = self.items.get(p.get("handle"))
        if w is not None:
            w.reveal()

    def _n_webview_dispose(self, p):
        w = self.items.pop(p.get("handle"), None)
        if w is not None:
            w.dispose()
            if w.kind == "panel":
                w.dock.removeEventFilter(self)
                w.dock.close()
                w.dock.deleteLater()

    def _n_webviewView_registered(self, p):  # noqa: N802
        vid = p.get("viewId")
        if vid:
            self.providers.add(vid)
            d = self.view_docks.get(vid)
            if d is not None and d.isVisible() and vid not in self.view_handles:
                self.show_view(vid)

    # ------------------------------------------------------------ IDE actions
    def show_view(self, view_id: str):
        h = self.view_handles.get(view_id)
        if h and h in self.items:
            self.items[h].reveal()
            return

        def got(res):
            if not res or not res.get("handle"):
                self.svc.status((res or {}).get("error") or f"{view_id}: no webview", 6000)
        self.svc.host.request("webviewView/resolve", {"viewId": view_id}, got, timeout_ms=30000)

    def reset(self):
        """The host stopped: every webview is gone with it."""
        for h, w in list(self.items.items()):
            w.dispose()
            if w.kind == "panel":
                try:
                    w.dock.removeEventFilter(self)
                    w.dock.close()
                    w.dock.deleteLater()
                except RuntimeError:
                    pass
        self.items.clear()
        self.view_handles.clear()
        self.providers.clear()

    def close(self):
        self.reset()
        self.server.close()
