"""Web workspace in the IDE (docs/CONTRACTS.md 8.1) - WebMatrix / Expression Web style.

- Solution Explorer shows the **folder tree** of website projects (folders first; node_modules / vendor are
  filled when expanded) with New File / New Folder / Add Existing / Rename / Delete / Open in Browser /
  View in Preview / Open in Design View / Set as Start Page / Copy URL.
- ``win.open_file(path, line=None)`` opens any file in an editor tab (language by extension, images in an
  image tab) - used by the explorer, the Requests dock and other features (reports, find results ...).
- **Run (F5 / Ctrl+F5)** of a website starts ``DevServer`` and shows the **Preview** dock
  (``win.web_preview``: address bar, back / forward / reload, device sizes, rotate, open in external
  browser, live reload); the **Requests** dock lists every request (method, path, status, time, size).
  Stop (Shift+F5) stops the server.
- Site menu (``win.site_menu``) and Site Settings (root, start page, port, live reload, router/command).

Hooks for other features: ``win.web_server`` (DevServer or None), ``win.web_preview``, ``win.web_requests``,
``win.web_signals`` (siteOpened(project), serverStarted(server), serverStopped(), request(dict),
reloaded(int)), ``win.run_website(project=None)``, ``win.stop_website()``, ``win.open_file(path, line)``.
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from PyQt6.QtCore import QObject, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QDesktopServices, QFont, QKeySequence, QPixmap
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget,
                             QFileDialog, QFormLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMenu, QMessageBox, QScrollArea, QSpinBox, QStyle, QToolBar,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..web_site.project import (DESIGNABLE_EXT, HEAVY_DIRS, IMAGE_EXT, children, file_for_url, file_plugin,
                                is_website, new_file_content, rel, safe_name, set_web_config, site_root,
                                start_page, web_config)

ROLE = Qt.ItemDataRole.UserRole
PATH_ROLE = Qt.ItemDataRole.UserRole + 11
DEVICES = [("Responsive (fit)", 0, 0), ("Phone (375 x 667)", 375, 667), ("Phone large (414 x 896)", 414, 896),
           ("Tablet (768 x 1024)", 768, 1024), ("Laptop (1366 x 768)", 1366, 768),
           ("Desktop (1920 x 1080)", 1920, 1080)]
FILE_TYPES = [("PHP Page", ".php", "page"), ("HTML Page", ".html", "page"), ("CSS Style Sheet", ".css", "style"),
              ("JavaScript", ".js", "script"), ("JSON File", ".json", "data"), ("Text File", ".txt", "text"),
              ("Markdown", ".md", "readme"), ("XML File", ".xml", "data"), ("SQL Script", ".sql", "schema")]
STATIC_TYPES = {"text/css", "text/javascript", "application/javascript", "image/png", "image/jpeg", "image/gif",
                "image/svg+xml", "image/x-icon", "image/webp", "font/woff", "font/woff2", "font/ttf"}


def _offscreen() -> bool:
    return os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"


def _icon(win, name: str):
    return win.style().standardIcon(getattr(QStyle.StandardPixmap, name))


class WebSignals(QObject):
    siteOpened = pyqtSignal(object)        # Project
    serverStarted = pyqtSignal(object)     # DevServer
    serverStopped = pyqtSignal()
    request = pyqtSignal(dict)
    reloaded = pyqtSignal(int)


# ============================================================================ Preview dock
class PreviewPane(QWidget):
    """Browser preview of the running site (QWebEngineView created on first use)."""

    def __init__(self, win):
        super().__init__()
        self.win = win
        self._view = None
        self._size = (0, 0)
        tb = QToolBar()
        tb.setIconSize(QSize(16, 16))
        SP = QStyle.StandardPixmap
        st = self.style()
        self.a_back = tb.addAction(st.standardIcon(SP.SP_ArrowBack), "Back", lambda: self.view and self.view.back())
        self.a_fwd = tb.addAction(st.standardIcon(SP.SP_ArrowForward), "Forward",
                                  lambda: self.view and self.view.forward())
        self.a_reload = tb.addAction(st.standardIcon(SP.SP_BrowserReload), "Reload (F5 in the page)", self.reload)
        self.address = QLineEdit()
        self.address.setPlaceholderText("Start the site (F5) or type a URL")
        self.address.setMinimumWidth(220)
        from PyQt6.QtWidgets import QSizePolicy
        self.address.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.address.returnPressed.connect(lambda: self.open_url(self._normalise(self.address.text())))
        tb.addWidget(self.address)
        self.device = QComboBox()
        for title, w, h in DEVICES:
            self.device.addItem(title, (w, h))
        self.device.currentIndexChanged.connect(lambda _i: self._apply_device())
        tb.addWidget(self.device)
        self.a_rotate = tb.addAction("Rotate", self._rotate)
        self.a_rotate.setToolTip("Swap width and height (portrait / landscape)")
        self.live = QCheckBox("Live reload")
        self.live.setChecked(True)
        self.live.setToolTip("Reload the page when a file of the site is saved")
        self.live.toggled.connect(self._live_toggled)
        tb.addWidget(self.live)
        self.a_external = tb.addAction(st.standardIcon(SP.SP_DesktopIcon), "Open in Browser", self.open_external)
        self.a_external.setToolTip("Open this page in the default web browser")
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.holder = QWidget()
        self.holder_lay = QVBoxLayout(self.holder)
        self.holder_lay.setContentsMargins(0, 0, 0, 0)
        self.placeholder = QLabel("<p style='color:#666'>Press <b>F5</b> to run the web site here.</p>")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.holder_lay.addWidget(self.placeholder)
        self.scroll.setWidget(self.holder)
        self.status = QLabel("")
        self.status.setProperty("radRole", "muted")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(tb)
        lay.addWidget(self.scroll, 1)
        lay.addWidget(self.status)

    # ------------------------------------------------------------ view
    @staticmethod
    def available() -> bool:
        import importlib.util
        return importlib.util.find_spec("PyQt6.QtWebEngineWidgets") is not None

    @property
    def view(self):
        """The QWebEngineView (None when PyQt6-WebEngine is missing)."""
        if self._view is None and self.available():
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            v = QWebEngineView()
            v.urlChanged.connect(lambda u: self.address.setText(u.toString()))
            v.titleChanged.connect(self._title)
            v.loadFinished.connect(lambda ok: self.status.setText("Done" if ok else "Could not load the page"))
            v.loadStarted.connect(lambda: self.status.setText("Loading..."))
            self.placeholder.hide()
            self.holder_lay.addWidget(v, 1)
            self._view = v
            self._apply_device()
        return self._view

    def _title(self, t: str):
        dock = getattr(self.win, "dock_web_preview", None)
        if dock is not None:
            dock.setWindowTitle(f"Preview - {t}" if t else "Preview")

    def _normalise(self, text: str) -> str:
        t = text.strip()
        if t and "://" not in t:
            srv = getattr(self.win, "web_server", None)
            t = srv.url_for(t if t.startswith("/") else "/" + t) if srv is not None and srv.url else "http://" + t
        return t

    def open_url(self, url: str, show: bool = True) -> None:
        self.address.setText(url)
        v = self.view
        if v is None:
            self.placeholder.setText(f"<p>PyQt6-WebEngine is not installed - <a href='{url}'>open {url} in the "
                                     "browser</a>.</p>")
            self.placeholder.setOpenExternalLinks(True)
        else:
            v.load(QUrl(url))
        if show:
            self.show_dock()

    def current_url(self) -> str:
        if self._view is not None:
            return self._view.url().toString()
        return self.address.text()

    def reload(self) -> None:
        if self._view is not None:
            self._view.reload()

    def show_dock(self) -> None:
        dock = getattr(self.win, "dock_web_preview", None)
        if dock is not None:
            first = not dock.isVisible() and not getattr(self, "_sized", False)
            dock.show()
            dock.raise_()
            if first:
                self._sized = True
                try:
                    self.win.resizeDocks([dock], [max(480, self.win.width() // 3)], Qt.Orientation.Horizontal)
                except Exception:  # noqa: BLE001
                    pass

    def open_external(self) -> None:
        url = self.current_url()
        if url:
            QDesktopServices.openUrl(QUrl(url))

    # ------------------------------------------------------------ devices
    def set_device(self, width: int, height: int) -> None:
        for i in range(self.device.count()):
            if self.device.itemData(i) == (width, height):
                self.device.setCurrentIndex(i)
                return
        self.device.addItem(f"Custom ({width} x {height})", (width, height))
        self.device.setCurrentIndex(self.device.count() - 1)

    def _rotate(self):
        w, h = self._size
        if w and h:
            self._size = (h, w)
            self._apply_size()

    def _apply_device(self):
        self._size = tuple(self.device.currentData() or (0, 0))
        self._apply_size()

    def _apply_size(self):
        w, h = self._size
        v = self._view
        if not w or not h:
            self.scroll.setWidgetResizable(True)
            if v is not None:
                v.setMinimumSize(0, 0)
                v.setMaximumSize(16777215, 16777215)
            return
        self.scroll.setWidgetResizable(False)
        if v is not None:
            v.setFixedSize(w, h)
        self.holder.setFixedSize(w, h)
        self.status.setText(f"{w} x {h}")

    def _live_toggled(self, on: bool):
        srv = getattr(self.win, "web_server", None)
        if srv is not None:
            srv.live_reload = on


# ============================================================================ Requests dock
def _size_text(n) -> str:
    n = int(n or 0)
    return f"{n / 1024:.1f} KB" if n >= 1024 else f"{n} B"


def _header(headers, name: str) -> str:
    low = name.lower()
    return next((str(v) for k, v in headers or [] if str(k).lower() == low), "")


def decode_form(ctype: str, body: str) -> list[tuple[str, str]] | None:
    """Fields of a form body (urlencoded or multipart/form-data); None for other bodies."""
    from urllib.parse import parse_qsl
    c = (ctype or "").lower()
    if "application/x-www-form-urlencoded" in c:
        return parse_qsl(body, keep_blank_values=True)
    if c.startswith("multipart/form-data"):
        import re
        m = re.search(r'boundary="?([^";]+)"?', ctype, re.I)
        if not m:
            return None
        out = []
        for part in body.split("--" + m.group(1))[1:]:
            if part.startswith("--"):
                break
            head, _, value = part.lstrip("\r\n").partition("\r\n\r\n")
            if not _:
                head, _, value = part.lstrip("\n").partition("\n\n")
            disp = next((ln for ln in head.splitlines() if ln.lower().startswith("content-disposition")), "")
            name = re.search(r'\bname="([^"]*)"', disp)
            fname = re.search(r'\bfilename="([^"]*)"', disp)
            value = value[:-2] if value.endswith("\r\n") else value.rstrip("\n")
            if fname is not None:
                ptype = next((ln.split(":", 1)[1].strip() for ln in head.splitlines()
                              if ln.lower().startswith("content-type")), "")
                value = f"(file '{fname.group(1)}', {ptype or 'unknown type'}, {_size_text(len(value.encode()))})"
            out.append((name.group(1) if name else "?", value))
        return out
    return None


def curl_command(info: dict) -> str:
    """The request as a curl command line (bash quoting)."""
    def q(t: str) -> str:
        return "'" + str(t).replace("'", "'\\''") + "'"
    method = str(info.get("method") or "GET")
    parts = ["curl"]
    if method not in ("GET", "POST") or (method == "POST" and not info.get("req_body")):
        parts += ["-X", method]
    parts.append(q(info.get("url", "")))
    for k, v in info.get("req_headers") or []:
        if str(k).lower() not in ("host", "content-length", "connection", "accept-encoding"):
            parts += ["-H", q(f"{k}: {v}")]
    body = info.get("req_body") or ""
    if body and not info.get("req_body_binary"):
        parts += ["--data-raw", q(body)]
    return " ".join(parts)


class RequestsPane(QWidget):
    """WebMatrix's Requests view: every request the site answered, with its details
    (general, request headers / body, response headers / preview) for the selected row."""
    COLUMNS = ["Time", "Method", "Path", "Status", "ms", "Size", "Type"]
    LIMIT = 500

    def __init__(self, win):
        super().__init__()
        from PyQt6.QtWidgets import QPlainTextEdit, QSplitter, QTabWidget
        self.win = win
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(self.COLUMNS)
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setAlternatingRowColors(True)
        for i, w in enumerate((64, 56, 260, 52, 50, 64, 120)):
            self.tree.setColumnWidth(i, w)
        self.tree.itemDoubleClicked.connect(lambda it, _c: self._open(it))
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        self.tree.currentItemChanged.connect(lambda cur, _prev: self.show_details(
            cur.data(0, ROLE) if cur is not None else None))
        tb = QToolBar()
        tb.setIconSize(QSize(16, 16))
        tb.addAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton), "Clear", self.clear)
        self.hide_static = QCheckBox("Hide images / CSS / JS")
        self.hide_static.toggled.connect(lambda _on: self._apply_filter())
        tb.addWidget(self.hide_static)
        self.errors_only = QCheckBox("Errors only")
        self.errors_only.toggled.connect(lambda _on: self._apply_filter())
        tb.addWidget(self.errors_only)
        self.summary = QLabel("")
        self.summary.setProperty("radRole", "muted")
        tb.addWidget(self.summary)
        # details
        mono = QFont("Consolas", 9)

        def kv_tree():
            t = QTreeWidget()
            t.setHeaderLabels(["Name", "Value"])
            t.setRootIsDecorated(False)
            t.setColumnWidth(0, 150)
            t.setAlternatingRowColors(True)
            t.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            t.customContextMenuRequested.connect(lambda pos, w=t: self._kv_menu(w, pos))
            return t

        def text_box():
            e = QPlainTextEdit()
            e.setReadOnly(True)
            e.setFont(mono)
            e.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
            return e
        self.details = QTabWidget()
        self.details.setDocumentMode(True)
        self.general = kv_tree()
        self.req_headers = kv_tree()
        self.form_fields = kv_tree()
        self.req_raw = text_box()
        body = QSplitter(Qt.Orientation.Vertical)
        body.addWidget(self.form_fields)
        body.addWidget(self.req_raw)
        self.req_body = body
        self.resp_headers = kv_tree()
        self.preview = text_box()
        self.preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        for w, title in ((self.general, "General"), (self.req_headers, "Request Headers"),
                         (body, "Request Body"), (self.resp_headers, "Response Headers"),
                         (self.preview, "Response")):
            self.details.addTab(w, title)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.tree)
        split.addWidget(self.details)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setChildrenCollapsible(False)
        self.splitter = split
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(tb)
        lay.addWidget(split, 1)
        self.entries: list[dict] = []
        self.current: dict | None = None
        self.show_details(None)

    def clear(self):
        self.tree.clear()
        self.entries.clear()
        self.summary.setText("")
        self.show_details(None)

    def add(self, info: dict) -> None:
        self.entries.append(info)
        it = QTreeWidgetItem([str(info.get("time", "")), str(info.get("method", "")), str(info.get("path", "")),
                              str(info.get("status", "")), f"{float(info.get('ms') or 0):.0f}",
                              _size_text(info.get("size")), str(info.get("type", ""))])
        it.setData(0, ROLE, info)
        status = int(info.get("status") or 0)
        if status >= 400:
            for c in range(len(self.COLUMNS)):
                it.setForeground(c, Qt.GlobalColor.red)
        elif 300 <= status < 400:
            it.setForeground(3, Qt.GlobalColor.blue)
        for c in (3, 4, 5):
            it.setTextAlignment(c, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        it.setToolTip(2, info.get("url", ""))
        self.tree.addTopLevelItem(it)
        it.setHidden(self._hidden(info))
        while self.tree.topLevelItemCount() > self.LIMIT:
            self.tree.takeTopLevelItem(0)
            self.entries.pop(0)
        if not it.isHidden() and self.tree.currentItem() is None:
            self.tree.scrollToItem(it)
        errors = sum(1 for e in self.entries if int(e.get("status") or 0) >= 400)
        self.summary.setText(f"{len(self.entries)} requests" + (f", {errors} errors" if errors else ""))

    # ------------------------------------------------------------ details
    @staticmethod
    def _fill_kv(tree, rows) -> None:
        tree.clear()
        for k, v in rows:
            it = QTreeWidgetItem([str(k), str(v)])
            it.setToolTip(1, str(v)[:2000])
            tree.addTopLevelItem(it)

    def show_details(self, info: dict | None) -> None:
        """Show the details of a request (None clears the details pane)."""
        from urllib.parse import parse_qsl, urlsplit
        self.current = info
        if not info:
            self._fill_kv(self.general, [("", "Select a request to see its details.")])
            for t in (self.req_headers, self.form_fields, self.resp_headers):
                t.clear()
            self.req_raw.setPlainText("")
            self.preview.setPlainText("")
            return
        rh = info.get("req_headers") or []
        sh = info.get("resp_headers") or []
        status = f"{info.get('status', '')} {info.get('reason') or ''}".strip()
        general = [("URL", info.get("url", "")), ("Method", info.get("method", "")), ("Status", status),
                   ("Time", info.get("time", "")), ("Duration", f"{float(info.get('ms') or 0):.1f} ms"),
                   ("Size", f"{_size_text(info.get('size'))} ({int(info.get('size') or 0):,} bytes)"),
                   ("Content type", _header(sh, "Content-Type") or info.get("type", "")),
                   ("Remote address", info.get("remote", ""))]
        query = urlsplit(str(info.get("path", ""))).query
        for k, v in parse_qsl(query, keep_blank_values=True):
            general.append((f"Query: {k}", v))
        self._fill_kv(self.general, general)
        self._fill_kv(self.req_headers, rh)
        self._fill_kv(self.resp_headers, sh)
        body = info.get("req_body") or ""
        size = int(info.get("req_body_size") or 0)
        ctype = _header(rh, "Content-Type")
        fields = decode_form(ctype, body) if body else None
        self._fill_kv(self.form_fields, fields or [])
        self.form_fields.setVisible(bool(fields))
        if info.get("req_body_binary"):
            raw = f"(binary body, {size:,} bytes)"
        elif not size:
            raw = "(no request body)"
        else:
            raw = body
            if size > len(body.encode("utf-8", errors="replace")):
                raw += f"\n\n... (truncated - the body is {size:,} bytes)"
        self.req_raw.setPlainText(raw)
        preview = info.get("resp_preview") or ""
        if not preview:
            preview = "(no preview - binary or empty response)" if int(info.get("size") or 0) else "(empty response)"
        elif int(info.get("size") or 0) > len(preview.encode("utf-8", errors="replace")):
            preview += f"\n\n... (preview truncated - the response is {_size_text(info.get('size'))})"
        self.preview.setPlainText(preview)

    def _kv_menu(self, tree, pos):
        it = tree.itemAt(pos)
        m = QMenu(self)
        if it is not None:
            m.addAction("Copy Value", lambda: QApplication.clipboard().setText(it.text(1)))
            m.addAction("Copy Name: Value", lambda: QApplication.clipboard().setText(f"{it.text(0)}: {it.text(1)}"))
        m.addAction("Copy All", lambda: QApplication.clipboard().setText("\n".join(
            f"{tree.topLevelItem(i).text(0)}: {tree.topLevelItem(i).text(1)}"
            for i in range(tree.topLevelItemCount()))))
        m.exec(tree.viewport().mapToGlobal(pos))

    def _hidden(self, info: dict) -> bool:
        if self.errors_only.isChecked() and int(info.get("status") or 0) < 400:
            return True
        return self.hide_static.isChecked() and info.get("type", "") in STATIC_TYPES

    def _apply_filter(self):
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            it.setHidden(self._hidden(it.data(0, ROLE) or {}))

    def _open(self, it):
        info = it.data(0, ROLE) or {}
        open_request_file(self.win, info.get("path", ""))

    def copy_url(self, info: dict) -> None:
        QApplication.clipboard().setText(info.get("url", ""))

    def copy_curl(self, info: dict) -> str:
        cmd = curl_command(info)
        QApplication.clipboard().setText(cmd)
        return cmd

    def _menu(self, pos):
        it = self.tree.itemAt(pos)
        m = QMenu(self)
        if it is not None:
            info = it.data(0, ROLE) or {}
            m.addAction("Copy URL", lambda: self.copy_url(info))
            m.addAction("Copy as curl", lambda: self.copy_curl(info))
            m.addSeparator()
            m.addAction("Open in Preview", lambda: self.win.web_preview.open_url(info.get("url", "")))
            m.addAction("Open in Browser", lambda: QDesktopServices.openUrl(QUrl(info.get("url", ""))))
            m.addAction("Open File", lambda: open_request_file(self.win, info.get("path", "")))
            m.addSeparator()
        m.addAction("Clear", self.clear)
        m.exec(self.tree.viewport().mapToGlobal(pos))


def open_request_file(win, url_path: str):
    srv = getattr(win, "web_server", None)
    project = getattr(srv, "project", None) if srv is not None else None
    project = project or win.project
    if project is None or not is_website(project):
        return None
    f = file_for_url(project, url_path)
    if f is None:
        win.statusBar().showMessage(f"No file for {url_path}", 4000)
        return None
    return open_file(win, f)


# ============================================================================ Solution Explorer
def fill_site(win, pi, project) -> None:
    """Fill a website project's node with its folder tree (called by solution_ui._fill_project)."""
    from .solution_ui import PROJECT_ROLE
    key = win._pkey(project)
    pi.setIcon(0, _icon(win, "SP_DriveNetIcon"))
    try:
        cfg = web_config(project)
        pi.setToolTip(0, pi.toolTip(0) + f"\nWeb site - start page: {cfg['start']}")
    except Exception:  # noqa: BLE001
        cfg = {"start": ""}
    start = (site_root(project) / start_page(project)).resolve() if cfg.get("start") else None
    win._web_filling = True               # fill_tree's expandAll() must not fill lazy folders (after_fill resets)
    _fill_dir(win, pi, Path(project.folder), key, PROJECT_ROLE, start)
    seen = win.__dict__.setdefault("_web_seen", set())
    if key not in seen:
        seen.add(key)
        QTimer.singleShot(0, lambda p=project: _site_opened(win, p))


def _fill_dir(win, parent_item, folder: Path, key, project_role, start, lazy: bool = False) -> None:
    """Items for the entries of *folder*. Heavy folders (node_modules, vendor...) and - with *lazy* -
    every sub-folder get a placeholder child and are filled when expanded."""
    bold = QFont()
    bold.setBold(True)
    for p in children(folder):
        it = QTreeWidgetItem(parent_item, [p.name])
        it.setData(0, project_role, key)
        it.setData(0, PATH_ROLE, str(p))
        if p.is_dir():
            it.setData(0, ROLE, ("webfolder", str(p)))
            it.setIcon(0, _icon(win, "SP_DirIcon"))
            if lazy or p.name in HEAVY_DIRS:
                ph = QTreeWidgetItem(it, ["(expand to load)"])
                ph.setData(0, ROLE, ("webplaceholder", str(p)))
                ph.setForeground(0, Qt.GlobalColor.gray)
                it.setForeground(0, Qt.GlobalColor.darkGray)
            else:
                _fill_dir(win, it, p, key, project_role, start)
        else:
            it.setData(0, ROLE, ("webfile", str(p)))
            it.setIcon(0, _icon(win, "SP_FileIcon"))
            if start is not None and p.resolve() == start:
                it.setFont(0, bold)
                it.setToolTip(0, "Start page (F5 opens it)")


def after_fill(win) -> None:
    """After Solution Explorer was filled: collapse website folders except the remembered ones."""
    expanded = win.__dict__.setdefault("_web_expanded", set())
    keys = set(getattr(win, "_pstates", {}).keys())
    seen = win.__dict__.setdefault("_web_seen", set())
    seen &= keys
    tree = win.solution
    stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    win._web_filling = True
    try:
        while stack:
            it = stack.pop()
            data = it.data(0, ROLE)
            if data and data[0] == "webfolder":
                want = os.path.normcase(data[1]) in expanded
                if want:
                    _fill_lazy(win, it)
                it.setExpanded(want)
            stack.extend(it.child(i) for i in range(it.childCount()))
    finally:
        win._web_filling = False


def _fill_lazy(win, it) -> None:
    data = it.data(0, ROLE)
    if it.childCount() == 1 and (it.child(0).data(0, ROLE) or ("",))[0] == "webplaceholder":
        from .solution_ui import PROJECT_ROLE
        it.takeChild(0)
        _fill_dir(win, it, Path(data[1]), it.data(0, PROJECT_ROLE), PROJECT_ROLE, None, lazy=True)


def _on_expanded(win, it) -> None:
    data = it.data(0, ROLE)
    if not data or data[0] != "webfolder" or getattr(win, "_web_filling", False):
        return
    win._web_expanded.add(os.path.normcase(data[1]))
    _fill_lazy(win, it)


def _on_collapsed(win, it) -> None:
    data = it.data(0, ROLE)
    if data and data[0] == "webfolder" and not getattr(win, "_web_filling", False):
        win._web_expanded.discard(os.path.normcase(data[1]))


def _site_opened(win, project) -> None:
    try:
        win.web_signals.siteOpened.emit(project)
    except RuntimeError:
        return
    if win.project is not project:
        return
    key = win._pkey(project)
    if any(win.tabs.widget(i).property("radProject") == key for i in range(win.tabs.count())):
        return
    try:
        f = site_root(project) / start_page(project)
        if f.is_file():
            open_file(win, f)
        win.log(f"Web site '{project.name}' ({win.plugin.display_name}): press F5 to run it in the Preview.")
    except Exception as e:  # noqa: BLE001
        win.log(f"[web] {e}")


def on_tree_activate(win, kind: str, path: str) -> None:
    """Double-click on a website file / folder in Solution Explorer."""
    if kind == "webfile":
        open_file(win, Path(path))


def project_of_path(win, path) -> object | None:
    """The open project whose folder contains *path* (the deepest one)."""
    p = os.path.normcase(str(Path(path).resolve()))
    best, best_len = None, -1
    for st in getattr(win, "_pstates", {}).values():
        f = os.path.normcase(str(Path(st["project"].folder).resolve()))
        if (p == f or p.startswith(f.rstrip("\\/") + os.sep)) and len(f) > best_len:
            best, best_len = st["project"], len(f)
    return best


# ============================================================================ open_file
class ImageView(QScrollArea):
    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pm = QPixmap(str(path))
        if pm.isNull():
            lbl.setText(f"Cannot show {path.name}")
        else:
            lbl.setPixmap(pm)
            lbl.setToolTip(f"{path.name}: {pm.width()} x {pm.height()} px, {path.stat().st_size:,} bytes")
        self.setWidget(lbl)
        self.setWidgetResizable(True)


def open_file(win, path, line: int | None = None):
    """Open any file in an editor tab (CONTRACTS 8.1). Returns the editor (None for images/binaries).
    Code files of normal projects open their usual editor; *line* is 1-based."""
    p = Path(path)
    if not p.is_absolute() and win.project is not None:
        p = Path(win.project.folder) / p
    p = p.resolve()
    if not p.is_file():
        win.statusBar().showMessage(f"File not found: {p}", 5000)
        return None
    owner = project_of_path(win, p)
    if owner is not None and owner is not win.project:
        win.activate_project(owner)
    project = win.project
    ext = p.suffix.lower()
    if ext in IMAGE_EXT - {".svg"}:
        images = win.__dict__.setdefault("_web_images", {})
        view = images.get(str(p))
        if view is None or win.tabs.indexOf(view) < 0:
            view = ImageView(p)
            images[str(p)] = view
        win._show_tab(view, p.name)
        return None
    if owner is not None and not is_website(owner) and p.parent == Path(owner.folder).resolve():
        ed = win._editor_for_file(p.name)          # a form's code file or a module of a normal project
        if ed is not None:
            if line:
                ed.goto_line(line - 1)
            return ed
    if project is None:
        win.statusBar().showMessage("Open a project first", 4000)
        return None
    r = rel(project, p) if owner is not None else ""
    key = r or str(p)
    mv = win.modviews.get(key)
    if mv is None:
        from ..app import ModuleView
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = p.read_text(encoding="cp1252")
            except UnicodeDecodeError:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
                return None
        mv = ModuleView(file_plugin(p, project), p)
        mv.editor.setText(text)
        mv.editor.setModified(False)
        mv.editor.modificationChanged.connect(lambda _m, k=key: win._update_module_title(k))
        mv.editor.contextMenuAboutToShow.connect(lambda m, f=p: _editor_menu(win, m, f))
        mv.setToolTip(str(p))
        win.modviews[key] = mv
    win.open_module(key)                     # shows the tab (and lets features attach to the editor)
    i = win.tabs.indexOf(mv)
    if i >= 0:
        win.tabs.setTabToolTip(i, str(p))
    if line:
        mv.editor.goto_line(line - 1)
    return mv.editor


def _editor_menu(win, m, path: Path):
    first = m.actions()[0] if m.actions() else None
    acts = []
    if is_website(win.project):
        acts.append(("View in Preview", lambda: view_in_preview(win, path)))
        acts.append(("Open in Browser", lambda: open_in_browser(win, path)))
        if path.suffix.lower() in DESIGNABLE_EXT:
            acts.append(("Open in Design View", lambda: open_design(win, path)))
    acts.append(("Run (F5)", win.start_or_continue))
    for text, slot in acts:
        a = QAction(text, m)
        a.triggered.connect(slot)
        m.insertAction(first, a)
    if first is not None:
        m.insertSeparator(first)


# ============================================================================ run / stop
def _site_project(win, project=None):
    if project is not None:
        return project
    if win.project is not None and is_website(win.project):
        return win.project
    sp = win.startup_project() if hasattr(win, "startup_project") else None
    return sp if sp is not None and is_website(sp) else win.project


def server_interpreter(win, plugin) -> str:
    if not getattr(plugin, "needs_interpreter", False):
        return ""
    s = win.settings
    configured = s.value(f"interpreter/{plugin.id}", "") or ""
    if not configured and plugin.id == "php-web":
        configured = s.value("interpreter/php", "") or ""
    return plugin.find_interpreter(configured)


def run_website(win, project=None, debug: bool = False, open_preview: bool = True, path=None):
    """Start the DevServer of a website project and show it in the Preview dock. Returns the server."""
    from ..languages import get_plugin
    from ..web_site.server import DevServer
    project = _site_project(win, project)
    if project is None or not is_website(project):
        return None
    srv = getattr(win, "web_server", None)
    if srv is not None and Path(srv.folder) == Path(project.folder).resolve() and srv.running:
        if open_preview:
            win.web_preview.open_url(srv.url_for(path) if path else srv.start_url())
        return srv
    if srv is not None:
        stop_website(win)
    plugin = get_plugin(project.language)
    interp = server_interpreter(win, plugin)
    if getattr(plugin, "needs_interpreter", False) and not interp:
        msg = (f"{plugin.display_name}: {', '.join(getattr(plugin, 'tool_names', []) or ['the interpreter'])} "
               f"was not found. {getattr(plugin, 'install_hint', '')}")
        win.log("*** " + msg)
        if not _offscreen():
            if QMessageBox.question(win, "Run Web Site", msg + "\n\nLocate it now?") == \
                    QMessageBox.StandardButton.Yes:
                interp = win.choose_interpreter()
        if not interp:
            return None
    srv = DevServer(project.folder, plugin, project=project, interpreter=interp, parent=win)
    srv.request.connect(win.web_requests.add)
    srv.request.connect(win.web_signals.request.emit)
    srv.reloaded.connect(win.web_signals.reloaded.emit)
    srv.log.connect(lambda t: win.log(f"[web] {t}"))
    srv.backendExited.connect(lambda code: win.statusBar().showMessage(f"The site's server exited ({code})", 8000))
    srv.reloaded.connect(lambda v: _reload_preview(win, srv, v))
    srv.live_reload = win.web_preview.live.isChecked() and bool(web_config(project).get("live_reload", True))
    try:
        url = srv.start()
    except OSError as e:
        win.log(f"*** Cannot start the web server: {e}")
        srv.deleteLater()
        return None
    win.web_server = srv
    win.web_requests.clear()
    win.dock_output.show()
    kind = {"php": f"PHP built-in server ({Path(interp).name})", "node": f"Node.js ({Path(interp).name})",
            "static": "static files"}.get(getattr(plugin, "web_kind", ""), plugin.display_name)
    win.log(f"------ Web server for '{project.name}': {url}   ({kind}, root {srv.root}) ------")
    if open_preview:
        win.web_preview.open_url(srv.url_for(path) if path else srv.start_url())
    win.dock_web_requests.show()
    win.statusBar().showMessage(f"Web site running at {url}")
    win._update_actions()
    win.web_signals.serverStarted.emit(srv)
    return srv


def _reload_preview(win, srv, _version):
    """Live reload without the injected script (live reload off in the page): reload the Preview."""
    if srv.live_reload or win.web_server is not srv:
        return
    cur = win.web_preview.current_url()
    if cur.startswith(srv.url) and win.web_preview.live.isChecked():
        win.web_preview.reload()


def stop_website(win) -> None:
    srv = getattr(win, "web_server", None)
    if srv is None:
        return
    win.web_server = None
    try:
        srv.stop()
    finally:
        srv.deleteLater()
    win.log("------ Web server stopped ------")
    win.statusBar().showMessage("Web server stopped", 4000)
    win._update_actions()
    win.web_signals.serverStopped.emit()


def restart_website(win) -> None:
    srv = getattr(win, "web_server", None)
    project = getattr(srv, "project", None) or _site_project(win)
    url = win.web_preview.current_url() if srv is not None else ""
    stop_website(win)
    new = run_website(win, project, open_preview=not url)
    if new is not None and url:
        from urllib.parse import urlsplit
        parts = urlsplit(url)
        win.web_preview.open_url(new.url.rstrip("/") + (parts.path or "/") + (f"?{parts.query}" if parts.query
                                                                              else ""))


def _ensure_server(win, path=None):
    project = project_of_path(win, path) if path is not None else None
    project = project if project is not None and is_website(project) else _site_project(win)
    srv = getattr(win, "web_server", None)
    if srv is not None and srv.running and (project is None or
                                            Path(srv.folder) == Path(project.folder).resolve()):
        return srv
    return run_website(win, project, open_preview=False)


def view_in_preview(win, path=None):
    srv = _ensure_server(win, path)
    if srv is not None:
        win.web_preview.open_url(srv.url_for(path) if path else srv.start_url())


def open_in_browser(win, path=None):
    srv = _ensure_server(win, path)
    if srv is not None:
        url = srv.url_for(path) if path else srv.start_url()
        QDesktopServices.openUrl(QUrl(url))
        return url
    return None


def open_design(win, path):
    """Open an HTML/PHP page in the Design View (radide/web_site/design.py, CONTRACTS 8.2)."""
    try:
        from ..web_site import design
    except ImportError:
        QMessageBox.information(win, "Design View", "The Design View is not available in this version.")
        return None
    fn = getattr(design, "open_design_view", None) or getattr(design, "open_design", None)
    if fn is not None:
        return fn(win, Path(path))
    cls = getattr(design, "DesignView", None)
    if cls is None:
        QMessageBox.information(win, "Design View", "The Design View is not available in this version.")
        return None
    view = cls(win, Path(path))
    win._show_tab(view, f"{Path(path).name} [Design]")
    return view


# ============================================================================ file operations
def _refresh(win):
    win._fill_solution()


def create_file(win, folder, name: str, content: str | None = None) -> Path:
    """New File in a website folder (content from the file type unless given). Raises ValueError."""
    folder = Path(folder)
    if not safe_name(name):
        raise ValueError(f"'{name}' is not a valid file name")
    path = folder / name
    if path.exists():
        raise ValueError(f"'{name}' already exists")
    folder.mkdir(parents=True, exist_ok=True)
    project = project_of_path(win, folder)
    path.write_text(new_file_content(path, project) if content is None else content, encoding="utf-8")
    _refresh(win)
    return path


def create_folder(win, parent, name: str) -> Path:
    if not safe_name(name):
        raise ValueError(f"'{name}' is not a valid folder name")
    path = Path(parent) / name
    if path.exists():
        raise ValueError(f"'{name}' already exists")
    path.mkdir(parents=True)
    win.__dict__.setdefault("_web_expanded", set()).add(os.path.normcase(str(Path(parent))))
    _refresh(win)
    return path


def _views_under(win, path: Path):
    """(project state, key, view) of open file tabs at/under *path*."""
    target = os.path.normcase(str(path.resolve()))
    out = []
    for st in getattr(win, "_pstates", {}).values():
        for key, mv in list(st["modviews"].items()):
            vp = os.path.normcase(str(Path(getattr(mv, "path", "")).resolve()))
            if vp == target or vp.startswith(target.rstrip("\\/") + os.sep):
                out.append((st, key, mv))
    return out


def rename_path(win, path, new_name: str) -> Path:
    path = Path(path)
    if not safe_name(new_name):
        raise ValueError(f"'{new_name}' is not a valid name")
    dst = path.with_name(new_name)
    if dst.exists() and dst.resolve() != path.resolve():
        raise ValueError(f"'{new_name}' already exists")
    views = _views_under(win, path)
    for st, key, mv in views:
        if mv.editor.isModified():
            Path(mv.path).write_text(mv.editor.text(), encoding="utf-8")
            mv.editor.setModified(False)
    path.rename(dst)
    for st, key, mv in views:
        old = Path(mv.path).resolve()
        new_path = dst / old.relative_to(path.resolve()) if old != path.resolve() else dst
        st["modviews"].pop(key, None)
        project = st["project"]
        new_key = rel(project, new_path) or str(new_path)
        mv.path = new_path
        mv.editor.path = new_path
        st["modviews"][new_key] = mv
        i = win.tabs.indexOf(mv)
        if i >= 0:
            win.tabs.setTabText(i, new_key)
            win.tabs.setTabToolTip(i, str(new_path))
        try:
            mv.editor.modificationChanged.disconnect()
        except TypeError:
            pass
        mv.editor.modificationChanged.connect(lambda _m, k=new_key: win._update_module_title(k))
    project = project_of_path(win, dst)
    if project is not None and is_website(project):
        start = (site_root(project) / start_page(project)).resolve()
        if start == path.resolve():
            set_web_config(project, start=(dst.resolve().relative_to(site_root(project))).as_posix())
    _refresh(win)
    return dst


def delete_path(win, path) -> Path:
    """Move a file/folder into the project's .radide_deleted folder (hidden from the tree and the server)."""
    path = Path(path).resolve()
    project = project_of_path(win, path)
    for st, key, mv in _views_under(win, path):
        st["modviews"].pop(key, None)
        i = win.tabs.indexOf(mv)
        if i >= 0:
            win.tabs.removeTab(i)
        mv.deleteLater()
    base = Path(project.folder) if project is not None else path.parent
    trash = base / ".radide_deleted" / time.strftime("%Y%m%d-%H%M%S")
    r = rel(project, path) if project is not None else path.name
    dst = trash / (r or path.name)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(dst))
    _refresh(win)
    return dst


def add_existing_files(win, folder, files=None) -> list[Path]:
    if files is None:
        files, _ = QFileDialog.getOpenFileNames(win, "Add Existing Files", str(folder), "All files (*)")
    out = []
    for f in files or []:
        src = Path(f)
        dst = Path(folder) / src.name
        if src.resolve() == dst.resolve():
            continue
        if dst.exists():
            QMessageBox.warning(win, "Add Existing Files", f"'{src.name}' already exists in {folder}")
            continue
        (shutil.copytree if src.is_dir() else shutil.copy2)(src, dst)
        out.append(dst)
    if out:
        _refresh(win)
    return out


class NewFileDialog(QDialog):
    """WebMatrix's 'Choose a File Type' dialog."""

    def __init__(self, win, folder: Path, project):
        super().__init__(win)
        self.setWindowTitle("New File")
        self.resize(440, 380)
        self.folder = folder
        self.list = QListWidget()
        prefer = ".php" if getattr(project, "language", "") == "php-web" else ".html"
        types = sorted(FILE_TYPES, key=lambda t: t[1] != prefer)
        if getattr(project, "language", "") != "php-web":
            types = [t for t in types if t[1] != ".php"] + [t for t in types if t[1] == ".php"]
        for title, ext, base in types:
            it = QListWidgetItem(f"{title}   (*{ext})")
            it.setData(ROLE, (ext, base))
            self.list.addItem(it)
        self.name = QLineEdit()
        self.list.currentItemChanged.connect(lambda *_: self._suggest())
        form = QFormLayout()
        form.addRow("Name:", self.name)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Choose a file type (in {folder.name or folder}):"))
        lay.addWidget(self.list, 1)
        lay.addLayout(form)
        lay.addWidget(box)
        self.list.setCurrentRow(0)

    def _suggest(self):
        it = self.list.currentItem()
        if it is None:
            return
        ext, base = it.data(ROLE)
        cur = self.name.text()
        if not cur or getattr(self, "_auto", True):
            i = 1
            name = f"{base}{ext}" if not (self.folder / f"{base}{ext}").exists() else ""
            while not name:
                i += 1
                if not (self.folder / f"{base}{i}{ext}").exists():
                    name = f"{base}{i}{ext}"
            self.name.setText(name)
            self.name.setSelection(0, len(Path(name).stem))
            self._auto = True

    def file_name(self) -> str:
        n = self.name.text().strip()
        it = self.list.currentItem()
        if n and "." not in n and it is not None:
            n += it.data(ROLE)[0]
        return n


def new_file_dialog(win, folder=None):
    project = _site_project(win)
    if project is None:
        return None
    folder = Path(folder) if folder else Path(project.folder)
    dlg = NewFileDialog(win, folder, project)
    if not dlg.exec():
        return None
    try:
        path = create_file(win, folder, dlg.file_name())
    except (ValueError, OSError) as e:
        QMessageBox.warning(win, "New File", str(e))
        return None
    open_file(win, path)
    return path


def new_folder_dialog(win, parent=None):
    project = _site_project(win)
    if project is None:
        return None
    parent = Path(parent) if parent else Path(project.folder)
    name, ok = QInputDialog.getText(win, "New Folder", f"Folder name (in {parent.name}):", text="NewFolder")
    if not ok or not name.strip():
        return None
    try:
        return create_folder(win, parent, name.strip())
    except (ValueError, OSError) as e:
        QMessageBox.warning(win, "New Folder", str(e))
        return None


def rename_dialog(win, path):
    path = Path(path)
    name, ok = QInputDialog.getText(win, "Rename", "New name:", text=path.name)
    if not ok or not name.strip() or name.strip() == path.name:
        return None
    try:
        return rename_path(win, path, name.strip())
    except (ValueError, OSError) as e:
        QMessageBox.warning(win, "Rename", str(e))
        return None


def delete_dialog(win, path):
    path = Path(path)
    what = "folder" if path.is_dir() else "file"
    if QMessageBox.question(win, "Delete", f"Delete the {what} '{path.name}'?\n(It is moved to the project's "
                            ".radide_deleted folder.)") != QMessageBox.StandardButton.Yes:
        return None
    try:
        return delete_path(win, path)
    except OSError as e:
        QMessageBox.warning(win, "Delete", str(e))
        return None


def set_start_page(win, path) -> None:
    project = project_of_path(win, path)
    if project is None or not is_website(project):
        return
    try:
        r = Path(path).resolve().relative_to(site_root(project)).as_posix()
    except ValueError:
        QMessageBox.warning(win, "Start Page", "The start page must be inside the site's root folder.")
        return
    set_web_config(project, start=r)
    win.log(f"Start page of '{project.name}': {r}")
    _refresh(win)


# ============================================================================ context menu
def build_site_menu(win, item, kind: str, name: str, project):
    """Solution Explorer menu for a website project / folder / file."""
    from . import solution_ui as su
    m = QMenu(win)
    if kind == "webplaceholder":
        kind = "webfolder"
    if project is None:
        project = _site_project(win)
    path = Path(name) if kind in ("webfile", "webfolder") else Path(project.folder)
    folder = path if path.is_dir() else path.parent
    if kind == "webfile":
        m.addAction("Open", lambda: open_file(win, path))
        if path.suffix.lower() in DESIGNABLE_EXT:
            m.addAction("Open in Design View", lambda: open_design(win, path))
        m.addAction("View in Preview", lambda: view_in_preview(win, path))
        m.addAction("Open in Browser", lambda: open_in_browser(win, path))
        m.addSeparator()
        if path.suffix.lower() in (".php", ".html", ".htm"):
            m.addAction("Set as Start Page", lambda: set_start_page(win, path))
        m.addAction("Copy URL", lambda: _copy_url(win, path))
        m.addAction("Copy Full Path", lambda: QApplication.clipboard().setText(str(path)))
        m.addSeparator()
        m.addAction("Rename...", lambda: rename_dialog(win, path))
        m.addAction("Delete", lambda: delete_dialog(win, path))
        m.addSeparator()
        m.addAction("Open Containing Folder", lambda: _startfile(path.parent))
        return m
    add = m.addMenu("Add")
    add.addAction("New File...", lambda: new_file_dialog(win, folder))
    add.addAction("New Folder...", lambda: new_folder_dialog(win, folder))
    add.addAction("Existing Files...", lambda: add_existing_files(win, folder))
    m.addSeparator()
    if kind == "webfolder":
        m.addAction("View in Preview", lambda: view_in_preview(win, path))
        m.addAction("Open in Browser", lambda: open_in_browser(win, path))
        m.addSeparator()
        m.addAction("Rename...", lambda: rename_dialog(win, path))
        m.addAction("Delete", lambda: delete_dialog(win, path))
        m.addSeparator()
        m.addAction("Open Folder in File Explorer", lambda: _startfile(path))
        return m
    # the project node
    m.addAction(win.a_run)
    m.addAction("View in Preview", lambda: view_in_preview(win))
    m.addAction("Open in Browser", lambda: open_in_browser(win))
    if getattr(win, "web_server", None) is not None:
        m.addAction("Restart Web Server", lambda: restart_website(win))
        m.addAction("Stop Web Server", lambda: stop_website(win))
    m.addSeparator()
    sln = win.sln
    a = m.addAction("Set as StartUp Project", lambda: su.set_startup_project(win, name))
    a.setEnabled(sln is not None and sln.startup.lower() != str(name).lower())
    if getattr(win, "a_manage_packages", None) is not None and getattr(get_plugin_safe(project), "package_manager",
                                                                       None) is not None:
        m.addAction("Manage Packages...", lambda: win.a_manage_packages.trigger())
    m.addAction("Refresh", lambda: _refresh(win))
    m.addSeparator()
    m.addAction("Remove from Solution", lambda: su.remove_project(win, name))
    m.addAction("Open Folder in File Explorer", lambda: _startfile(Path(project.folder)))
    m.addSeparator()
    m.addAction("Site Settings...", lambda: site_settings(win, project))
    return m


def get_plugin_safe(project):
    from ..languages import get_plugin
    try:
        return get_plugin(project.language)
    except KeyError:
        return None


def _copy_url(win, path):
    srv = getattr(win, "web_server", None)
    project = project_of_path(win, path)
    if srv is not None and srv.running:
        url = srv.url_for(path)
    else:
        from ..web_site.project import url_path_for
        url = url_path_for(project, path) or ""
    QApplication.clipboard().setText(url)
    win.statusBar().showMessage(f"Copied {url}", 3000)


def _startfile(path):
    if Path(path).exists():
        os.startfile(str(path))  # noqa: S606 - Windows Explorer


# ============================================================================ Site Settings
def site_settings(win, project=None, exec_: bool = True):
    project = _site_project(win, project)
    if project is None or not is_website(project):
        return None
    cfg = web_config(project)
    dlg = QDialog(win)
    dlg.setWindowTitle(f"Site Settings - {project.name}")
    lay = QFormLayout(dlg)
    plugin = get_plugin_safe(project)
    lay.addRow("Site type:", QLabel(plugin.display_name if plugin else project.language))
    lay.addRow("Folder:", QLabel(str(project.folder)))
    root = QLineEdit(cfg["root"])
    root.setToolTip("Folder served as '/' (relative to the project folder, e.g. '.' or 'public')")
    lay.addRow("Web root:", root)
    start = QComboBox()
    start.setEditable(True)
    try:
        r = site_root(project)
        pages = sorted({p.relative_to(r).as_posix() for p in r.rglob("*")
                        if p.suffix.lower() in (".php", ".html", ".htm", ".js") and "node_modules" not in p.parts
                        and "vendor" not in p.parts})[:300]
    except (OSError, ValueError):
        pages = []
    start.addItems(pages)
    start.setCurrentText(cfg["start"])
    lay.addRow("Start page:" if getattr(plugin, "web_kind", "") != "node" else "Start file:", start)
    port = QSpinBox()
    port.setRange(0, 65535)
    port.setValue(int(cfg.get("port") or 0))
    port.setSpecialValueText("automatic")
    lay.addRow("Port:", port)
    live = QCheckBox("Reload the browser when a file is saved (live reload)")
    live.setChecked(bool(cfg.get("live_reload", True)))
    lay.addRow("", live)
    extra = None
    if getattr(plugin, "web_kind", "") == "php":
        extra = QLineEdit(str(cfg.get("router") or ""))
        extra.setPlaceholderText("optional router script, e.g. server.php")
        lay.addRow("Router script:", extra)
    elif getattr(plugin, "web_kind", "") == "node":
        extra = QLineEdit(str(cfg.get("command") or ""))
        extra.setPlaceholderText("optional command instead of node <start file>, e.g. npm run dev")
        lay.addRow("Start command:", extra)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addRow(box)
    dlg.fields = {"root": root, "start": start, "port": port, "live": live, "extra": extra}

    def apply():
        changes = {"root": root.text().strip() or ".", "start": start.currentText().strip(),
                   "port": port.value(), "live_reload": live.isChecked()}
        if extra is not None:
            changes["router" if getattr(plugin, "web_kind", "") == "php" else "command"] = extra.text().strip()
        set_web_config(project, **changes)
        _refresh(win)
        srv = getattr(win, "web_server", None)
        if srv is not None and Path(srv.folder) == Path(project.folder).resolve():
            restart_website(win)
    dlg.apply = apply
    if not exec_:
        return dlg
    if dlg.exec():
        apply()
    return dlg


# ============================================================================ designer docks
DESIGNER_DOCKS = ("dock_toolbox", "dock_props", "dock_data", "dock_states", "dock_timeline")
HIDDEN_DOCKS_KEY = "web/designer_docks_hidden"     # docks hidden for a web site (survives an IDE restart)


def update_designer_docks(win) -> None:
    """A solution made only of web sites has no forms: hide the form-designer docks - Toolbox, Properties and
    the Blend panels (Data, States, Objects and Timeline) - and show them again, as they were, when a solution
    with a normal project is opened."""
    projects = win.projects() if hasattr(win, "projects") else []
    web_only = bool(projects) and all(is_website(p) for p in projects)
    settings = getattr(win, "settings", None)
    if web_only == (getattr(win, "_web_docks_hidden", None) is not None):
        if not web_only and projects and settings is not None:
            # the IDE was closed while a web site was open: its saved layout has these docks hidden
            names = settings.value(HIDDEN_DOCKS_KEY, None)
            if names:
                settings.remove(HIDDEN_DOCKS_KEY)
                names = {str(n) for n in (names if isinstance(names, (list, tuple)) else [names])}
                for n in DESIGNER_DOCKS:
                    d = getattr(win, n, None)
                    if d is not None and d.objectName() in names:
                        d.show()
                _raise_props(win)
        return
    docks = [d for d in (getattr(win, n, None) for n in DESIGNER_DOCKS) if d is not None]
    if web_only:
        win._web_docks_hidden = {d.objectName(): not d.isHidden() for d in docks}
        for d in docks:
            d.hide()
        if settings is not None:
            settings.setValue(HIDDEN_DOCKS_KEY, [n for n, vis in win._web_docks_hidden.items() if vis])
    else:
        saved = win._web_docks_hidden or {}
        win._web_docks_hidden = None
        for d in docks:
            if saved.get(d.objectName(), True):
                d.show()
        if settings is not None:
            settings.remove(HIDDEN_DOCKS_KEY)
        _raise_props(win)


def _raise_props(win) -> None:
    props = getattr(win, "dock_props", None)
    if props is not None and props.isVisible():
        props.raise_()                      # Properties in front of the Blend panels tabbed with it


# ============================================================================ install
def _menu(win, title: str):
    return next((a for a in win.menuBar().actions() if a.text().replace("&", "") == title), None)


def install(win) -> None:
    win.web_server = None
    win.web_signals = WebSignals(win)
    win._web_seen, win._web_expanded = set(), set()
    # docks
    win.web_preview = PreviewPane(win)
    d = QDockWidget("Preview", win)
    d.setObjectName("Preview")
    d.setWidget(win.web_preview)
    # its own full-height column on the right (not stacked under Solution Explorer / Properties)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, d, Qt.Orientation.Horizontal)
    d.hide()
    win.dock_web_preview = d
    win.web_requests = RequestsPane(win)
    d = QDockWidget("Requests", win)
    d.setObjectName("Requests")
    d.setWidget(win.web_requests)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, d)
    win.tabifyDockWidget(win.dock_output, d)
    d.hide()
    win.dock_web_requests = d
    win.dock_output.raise_()
    # API on the window
    win.open_file = lambda path, line=None: open_file(win, path, line)
    win.run_website = lambda project=None, **kw: run_website(win, project, **kw)
    win.stop_website = lambda: stop_website(win)
    # Solution Explorer: lazy folders + remembered expansion
    win.solution.itemExpanded.connect(lambda it: _on_expanded(win, it))
    win.solution.itemCollapsed.connect(lambda it: _on_collapsed(win, it))
    # Toolbox / Properties follow the kind of the open solution (web sites only -> hidden)
    win._web_docks_hidden = None
    orig_fill = win._fill_solution

    def fill_solution(*args, **kw):
        r = orig_fill(*args, **kw)
        try:
            update_designer_docks(win)
        except Exception as e:  # noqa: BLE001 - never break Solution Explorer
            win.log(f"[web] {e}")
        return r
    win._fill_solution = fill_solution
    # live reload right after Save All (the watcher would see it a moment later anyway)
    win.a_save.triggered.connect(lambda: win.web_server is not None and QTimer.singleShot(
        0, lambda: win.web_server is not None and win.web_server.check_now()))
    # menus
    view = _menu(win, "View")
    if view is not None and view.menu() is not None:
        view.menu().addSeparator()
        view.menu().addAction(win.dock_web_preview.toggleViewAction())
        view.menu().addAction(win.dock_web_requests.toggleViewAction())
    site = QMenu("&Site", win)
    win.site_menu = site
    a = QAction("&Run Site in Preview", win)
    a.triggered.connect(lambda: run_website(win))
    site.addAction(a)
    win.a_site_run = a
    a = QAction("Open in &Browser", win)
    a.setShortcut(QKeySequence("Ctrl+Alt+B"))
    a.triggered.connect(lambda: open_in_browser(win))
    site.addAction(a)
    win.a_site_browser = a
    a = QAction("R&estart Web Server", win)
    a.triggered.connect(lambda: restart_website(win))
    site.addAction(a)
    win.a_site_restart = a
    a = QAction("S&top Web Server", win)
    a.triggered.connect(lambda: stop_website(win))
    site.addAction(a)
    win.a_site_stop = a
    site.addSeparator()
    site.addAction("New &File...", lambda: new_file_dialog(win))
    site.addAction("New F&older...", lambda: new_folder_dialog(win))
    site.addSeparator()
    site.addAction(win.dock_web_preview.toggleViewAction())
    site.addAction(win.dock_web_requests.toggleViewAction())
    site.addSeparator()
    site.addAction("Site &Settings...", lambda: site_settings(win))

    def update_site_menu():
        web = _site_project(win) is not None and is_website(_site_project(win))
        running = win.web_server is not None
        for act in (win.a_site_run, win.a_site_browser):
            act.setEnabled(web)
        win.a_site_restart.setEnabled(running)
        win.a_site_stop.setEnabled(running)
    site.aboutToShow.connect(update_site_menu)
    anchor = _menu(win, "Debug") or _menu(win, "Tools")
    if anchor is not None:
        win.menuBar().insertMenu(anchor, site)
    else:
        win.menuBar().addMenu(site)
    try:
        QApplication.instance().aboutToQuit.connect(lambda: stop_website(win) if win.web_server else None)
    except Exception:  # noqa: BLE001
        pass


__all__ = ["ImageView", "NewFileDialog", "PreviewPane", "RequestsPane", "WebSignals", "add_existing_files",
           "after_fill", "build_site_menu", "create_file", "create_folder", "delete_path", "fill_site",
           "curl_command", "decode_form", "on_tree_activate", "open_design", "open_file", "open_in_browser",
           "project_of_path", "rename_path", "restart_website", "run_website", "set_start_page", "site_settings",
           "stop_website", "update_designer_docks", "view_in_preview"]
