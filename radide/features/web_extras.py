"""Web extras: REST Client tab, ``.http`` files with Send Request lenses, React / Vue / Svelte / Angular
projects (Vite / Angular CLI) with Build, Database Diagrams, and JavaScript debugging in the Preview.

- **Tools > REST Client** (Ctrl+Alt+K): Postman-like tab (``radide/web_site/rest_client.py``). In an ``.http``
  / ``.rest`` file every request line has a *Send Request* lens (Monaco CodeLens); the editor menu has
  *Send Request* too. The REST Client tab shows the answer.
- **Site > New Front-end App...**: React, React + TypeScript, Vue, Svelte, vanilla (``npm create vite``) or Angular
  (``ng new``) - also in File > New Project > Web > Node.js; F5 runs the dev server in the Preview and debugs the
  app's JavaScript there; **Site > Build Production** runs ``npm run build`` / ``ng build`` in the Output window.
- **Databases** connection menu / Tools > Databases > **Database Diagram** (``radide/web_site/db_diagram.py``).
- Tools > Options > **Web**: "Debug JavaScript in the Preview" (QtWebEngine DevTools port, see
  ``radide/web_site/browser_debug.py``; read at start-up).
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSlot
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
                             QLabel, QLineEdit, QMessageBox, QPushButton, QToolBar, QVBoxLayout, QWidget)

from .. import theme

_WIN = None
HTTP_SUFFIXES = (".http", ".rest")

# Monaco: "http" language (Monarch) + a "Send Request" CodeLens on every request line
HTTP_JS = r"""
(function () {
  if (window.__radHttp) return; window.__radHttp = true;
  const ed = window.radEditor;
  if (!monaco.languages.getLanguages().some(l => l.id === 'http')) {
    monaco.languages.register({ id: 'http', extensions: ['.http', '.rest'] });
    monaco.languages.setMonarchTokensProvider('http', { tokenizer: { root: [
      [/^###.*$/, 'keyword'], [/^\s*(#|\/\/).*$/, 'comment'],
      [/^@[\w.-]+\s*=/, 'variable'],
      [/^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|TRACE|CONNECT)\b/, 'keyword'],
      [/\{\{[^}]*\}\}/, 'variable.predefined'], [/HTTP\/[\d.]+/, 'keyword'],
      [/^[\w-]+(?=\s*:)/, 'attribute.name'], [/"([^"\\]|\\.)*"/, 'string'], [/\b\d+(\.\d+)?\b/, 'number'],
    ] } });
    monaco.languages.setLanguageConfiguration('http', { comments: { lineComment: '#' },
      brackets: [['{', '}'], ['[', ']']], autoClosingPairs: [{ open: '{', close: '}' }, { open: '"', close: '"' }] });
  }
  if (ed.getModel().getLanguageId() !== 'http') monaco.editor.setModelLanguage(ed.getModel(), 'http');
  const cmd = ed.addCommand(0, function (_acc, line) {
    const o = window.radChannel && window.radChannel.objects.radHttp; if (o) o.send(line);
  }, '');
  const REQ = /^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|TRACE|CONNECT)\s+\S|^https?:\/\/\S/i;
  monaco.languages.registerCodeLensProvider('http', {
    provideCodeLenses: function (model) {
      const lenses = [];
      if (model !== ed.getModel()) return { lenses, dispose() {} };
      let start = true;
      for (let i = 1; i <= model.getLineCount(); i++) {
        const t = model.getLineContent(i).trim();
        if (t.startsWith('###')) { start = true; continue; }
        if (!start || !t || t.startsWith('#') || t.startsWith('//') || /^@[\w.-]+\s*=/.test(t)) continue;
        start = false;
        if (REQ.test(t)) lenses.push({ range: new monaco.Range(i, 1, i, 1), id: 'send' + i,
                                       command: { id: cmd, title: '▶ Send Request', arguments: [i] } });
      }
      return { lenses, dispose() {} };
    },
    resolveCodeLens: function (_m, l) { return l; }
  });
  window.radHttpLensCount = function () {          // tests
    const m = ed.getModel(); let n = 0, start = true;
    for (let i = 1; i <= m.getLineCount(); i++) { const t = m.getLineContent(i).trim();
      if (t.startsWith('###')) { start = true; continue; }
      if (!start || !t || t.startsWith('#') || t.startsWith('//') || /^@[\w.-]+\s*=/.test(t)) continue;
      start = false; if (REQ.test(t)) n++; }
    return n; };
})();
"""


# ============================================================================ REST Client
def rest_panel(win, show: bool = True):
    from ..web_site.rest_client import panel_class
    p = getattr(win, "rest_client", None)
    if p is None:
        p = panel_class()(win)
        win.rest_client = p
    else:
        p.refresh()
    if show:
        if callable(getattr(win, "_show_tab", None)):
            win._show_tab(p, "REST Client")
        else:
            i = win.tabs.indexOf(p)
            win.tabs.setCurrentIndex(i if i >= 0 else win.tabs.addTab(p, "REST Client"))
    return p


def send_from_editor(win, editor, line: int | None = None):
    """Send the request of an .http editor at 0-based *line* (default: the caret line)."""
    from ..web_site.rest_client import parse_http, request_at_line
    path = Path(getattr(editor, "path", "") or "")
    text = editor.toPlainText() if hasattr(editor, "toPlainText") else editor.text()
    if line is None:
        line = editor.getCursorPosition()[0]
    req = request_at_line(text, line)
    if req is None:
        win.statusBar().showMessage("No request here (a request starts with a line like 'GET https://...')", 6000)
        return None
    _reqs, fvars = parse_http(text, str(path))
    req.file = str(path)
    p = rest_panel(win)
    p.load_request(req, fvars)
    p.send_request(req, fvars)
    return p


class HttpBridge(QObject):
    """window.radChannel.objects.radHttp of every Monaco editor."""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    @pyqtSlot(int)
    def send(self, line: int):
        if _WIN is not None:
            send_from_editor(_WIN, self.editor, line - 1)


def _is_http(editor) -> bool:
    return str(getattr(editor, "path", "")).lower().endswith(HTTP_SUFFIXES)


def _monaco_ready(editor):
    if not _is_http(editor):
        return
    editor._js(HTTP_JS)
    try:
        editor.contextMenuAboutToShow.connect(lambda m, ed=editor: _http_menu(m, ed))
    except Exception:  # noqa: BLE001
        pass


def _http_menu(menu, editor):
    if _WIN is None:
        return
    first = menu.actions()[0] if menu.actions() else None
    a = QAction("Send Request", menu)
    a.setShortcut(QKeySequence("Ctrl+Alt+K"))
    a.triggered.connect(lambda: send_from_editor(_WIN, editor))
    menu.insertAction(first, a)
    if first is not None:
        menu.insertSeparator(first)


def _rest_shortcut(win):
    """Ctrl+Alt+K: in an .http editor send the request at the caret, elsewhere open the REST Client."""
    cur = win._current_code() if hasattr(win, "_current_code") else None
    ed = getattr(cur, "editor", None)
    if ed is not None and _is_http(ed):
        return send_from_editor(win, ed)
    return rest_panel(win)


# ============================================================================ front-end frameworks
class NewFrontendDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        from ..web_site.vite_templates import FRAMEWORKS
        self.setWindowTitle("New Front-end App")
        self.resize(560, 260)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.kind = QComboBox()
        for f in FRAMEWORKS:
            self.kind.addItem(f.title, f.id)
        self.desc = QLabel()
        self.desc.setWordWrap(True)
        theme.role(self.desc, "muted")
        self.name = QLineEdit("MyApp")
        self.loc = QLineEdit(str(Path(win.settings.value("paths/projects", "") or Path.home() / "RADProjects")))
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.loc, 1)
        row.addWidget(browse)
        form.addRow("Framework:", self.kind)
        form.addRow("", self.desc)
        form.addRow("Name:", self.name)
        form.addRow("Location:", row)
        lay.addLayout(form)
        note = QLabel("Needs Node.js (npm) and an internet connection; the official generator runs, then "
                      "npm install (about a minute).")
        note.setWordWrap(True)
        theme.role(note, "note")
        lay.addWidget(note)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Create")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.kind.currentIndexChanged.connect(self._desc)
        self._desc()

    def _desc(self):
        from ..web_site.vite_templates import get_framework
        f = get_framework(self.kind.currentData())
        self.desc.setText(f.description if f else "")

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Location", self.loc.text())
        if d:
            self.loc.setText(d)

    def folder(self) -> Path:
        return Path(self.loc.text()) / self.name.text().strip()


def create_frontend(win, fid: str, folder: Path, name: str, open_it: bool = True):
    """Create a framework project (progress window) and open it. Returns the project or None."""
    from ..web_site.project import create_website
    from ..web_site import vite_templates as V
    from ..languages import get_plugin
    if get_plugin("node-web") is None:
        QMessageBox.warning(win, "New Front-end App", "The Node.js web site plugin is not available.")
        return None
    if folder.exists() and any(folder.iterdir()):
        QMessageBox.warning(win, "New Front-end App", f"{folder} is not empty.")
        return None
    prog = _progress(win)
    V.register(prog or (lambda title, fn: fn(lambda s: win.log(s))))   # output in a progress window / Output
    try:
        project = create_website(folder, name, "node-web", fid)
    except Exception as e:  # noqa: BLE001 - npm / network errors
        win.log(f"*** New front-end app: {e}")
        if prog is not None:
            QMessageBox.warning(win, "New Front-end App", str(e))
        return None
    win.log(f"[web] created {V.get_framework(fid).title} project {folder}")
    if open_it:
        win.open_project(folder, ask=False) if "ask" in win.open_project.__code__.co_varnames else \
            win.open_project(folder)
        main = folder / (V.get_framework(fid).main_file or "")
        if main.is_file() and hasattr(win, "open_file"):
            QTimer.singleShot(200, lambda: win.open_file(main))
    return project


def new_frontend_dialog(win):
    dlg = NewFrontendDialog(win)
    if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.name.text().strip():
        return None
    return create_frontend(win, dlg.kind.currentData(), dlg.folder(), dlg.name.text().strip())


def _progress(win):
    try:
        from .app_gallery import run_with_progress
    except Exception:  # noqa: BLE001
        return None
    import os
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return None                           # tests: no modal window
    return lambda title, fn: run_with_progress(win, title, fn)


def _framework_project(win):
    from ..web_site.project import is_website, web_config
    p = win.project
    if p is None or not is_website(p):
        return None
    return p if web_config(p).get("framework") or (Path(p.folder) / "package.json").is_file() else None


def build_production(win, wait: bool = False):
    """Site > Build Production: npm run build / ng build in the Output window. Returns the QProcess."""
    from ..web_site.vite_templates import build_command
    p = _framework_project(win)
    if p is None:
        win.log("*** Build Production: open a React / Vue / Svelte / Angular (package.json) site first.")
        return None
    cmd = build_command(p)
    if not cmd:
        win.log("*** package.json has no \"build\" script.")
        return None
    proc = QProcess(win)
    proc.setWorkingDirectory(str(p.folder))
    proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    proc.readyReadStandardOutput.connect(
        lambda: win.log(bytes(proc.readAllStandardOutput()).decode("utf-8", "replace").rstrip()))

    def done(code, _st):
        from ..web_site.project import web_config
        dist = Path(p.folder) / str(web_config(p).get("dist") or "dist")
        win.log(f"------ Build {'succeeded' if code == 0 else f'failed ({code})'}"
                f"{' - output in ' + str(dist) if code == 0 else ''} ------")
        win.statusBar().showMessage("Build succeeded" if code == 0 else "Build failed", 6000)
    proc.finished.connect(done)
    win.dock_output.show()
    win.log(f"------ Build {p.name}: {cmd} ------")
    proc.start("cmd", ["/c", cmd])
    win._web_build = proc
    if wait:
        proc.waitForFinished(600000)
    return proc


# ============================================================================ database diagram
def open_db_diagram(win, cid=None):
    panel = getattr(win, "databases", None)
    if panel is None:
        return None
    from ..web_site.db_diagram import open_diagram
    if cid is not None:
        return open_diagram(panel, cid)
    box = {}
    panel._with_conn(lambda c: box.setdefault("w", open_diagram(panel, c)))
    return box.get("w")


# ============================================================================ Options page
def _options_page(dlg):
    w = QWidget()
    lay = QVBoxLayout(w)
    s = dlg.win.settings if hasattr(dlg, "win") else _WIN.settings
    cb = QCheckBox("Debug JavaScript in the Preview (F9 in .js files of a web site)")
    cb.setChecked(s.value("web/js_debug", True) not in (False, "false", "0", 0))
    lay.addWidget(cb)
    from ..web_site.browser_debug import devtools_port
    port = devtools_port()
    info = QLabel("The IDE's browser engine opens a DevTools port on 127.0.0.1 only "
                  f"({'now: port ' + str(port) if port else 'now: off'}); the vscode-js-debug adapter attaches "
                  "to the Preview through it. Changes take effect after restarting RAD IDE.")
    info.setWordWrap(True)
    theme.role(info, "muted")
    lay.addWidget(info)
    lay.addStretch(1)

    def apply():
        s.setValue("web/js_debug", cb.isChecked())
    return w, "Web", apply


# ============================================================================ install
def _menu(win, title):
    return next((a.menu() for a in win.menuBar().actions()
                 if a.menu() is not None and a.text().replace("&", "") == title), None)


def install(win) -> None:
    global _WIN
    _WIN = win
    from ..monaco_editor import MONACO_LANG, MonacoEditor
    for ext in HTTP_SUFFIXES:
        MONACO_LANG.setdefault(ext, "http")
    MONACO_LANG.setdefault(".svelte", "html")          # like .vue: HTML colouring + HTML IntelliSense
    MonacoEditor.channel_objects.setdefault("radHttp", HttpBridge)
    if _monaco_ready not in MonacoEditor.ready_hooks:
        MonacoEditor.ready_hooks.append(_monaco_ready)
    from . import settings as S
    hooks = getattr(S, "PAGE_HOOKS", None)
    if hooks is not None and _options_page not in hooks:
        hooks.append(_options_page)
    try:
        from ..web_site import vite_templates
        vite_templates.register(_progress(win))
    except Exception as e:  # noqa: BLE001
        win.log(f"[web extras] framework templates: {e}")

    a = QAction("&REST Client", win)
    a.setShortcut(QKeySequence("Ctrl+Alt+K"))
    a.setToolTip("Send HTTP requests (Postman-like); in an .http file: send the request at the caret")
    a.triggered.connect(lambda: _rest_shortcut(win))
    win.a_rest_client = a
    win.addAction(a)
    tools = _menu(win, "Tools")
    if tools is not None:
        tools.addAction(a)
        db = next((x.menu() for x in tools.actions() if x.menu() is not None and
                   x.text().replace("&", "") == "Databases"), None)
        if db is not None:
            db.addAction("Database &Diagram", lambda: open_db_diagram(win))
    win.a_new_frontend = QAction("New Front-end &App (React, Vue, Svelte, Angular)...", win)
    win.a_new_frontend.triggered.connect(lambda: new_frontend_dialog(win))
    win.a_build_production = QAction("&Build Production (npm run build)", win)
    win.a_build_production.triggered.connect(lambda: build_production(win))

    def add_to_site_menu():
        sm = getattr(win, "site_menu", None)
        if sm is None or getattr(win, "_webx_site_menu", False):
            return
        win._webx_site_menu = True
        sm.addSeparator()
        sm.addAction(win.a_new_frontend)
        sm.addAction(win.a_build_production)
        sm.addAction(a)
        sm.aboutToShow.connect(lambda: win.a_build_production.setEnabled(_framework_project(win) is not None))
    QTimer.singleShot(0, add_to_site_menu)

    # Databases panel: "Database Diagram" in the connection's right-click menu and the toolbar
    def add_to_databases():
        panel = getattr(win, "databases", None)
        if panel is None or getattr(panel, "_webx_diagram", False):
            return
        panel._webx_diagram = True
        tb = next(iter(panel.findChildren(QToolBar)), None)
        if tb is not None:
            act = tb.addAction("Diagram")
            act.setToolTip("Database Diagram: tables, columns and foreign keys; create tables and relationships")
            act.triggered.connect(lambda: open_db_diagram(win))
    QTimer.singleShot(0, add_to_databases)


__all__ = ["HTTP_JS", "build_production", "create_frontend", "install", "new_frontend_dialog", "open_db_diagram",
           "rest_panel", "send_from_editor"]
