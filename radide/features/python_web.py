"""Django / Flask / FastAPI in the IDE (engine: radide/web_site/frameworks/python_web.py).

- **IntelliSense from the project** in Monaco: a second completion provider (QWebChannel object
  ``radPyWeb``) next to the language server: url names in ``reverse()`` / ``redirect()`` / ``{% url %}`` /
  ``url_for()``, template names in ``render()`` / ``render_template()`` / ``{% extends %}`` /
  ``{% include %}``, model fields and lookups after ``Model.objects.filter(``, ``settings.`` names, static
  files, Django / Jinja tags, filters and context variables. **F12** on a url / template / static name
  opens its declaration (other words go to the normal Go to Definition).
- **Template language**: ``.html`` files under ``templates/`` of a Django project open as
  ``django-html``, of Flask / FastAPI as ``jinja-html`` (HTML + ``{% %}`` / ``{{ }}`` / ``{# #}``
  highlighting; the HTML language server still serves the HTML part).
- **Framework panel** (View > Django / Flask / FastAPI, also in the Site menu and the VS Code side bar):
  manage.py commands (makemigrations, migrate, createsuperuser, startapp, shell ...), ``flask routes``,
  FastAPI ``/docs``; the URL / route list (double-click = open in the Preview, F12 = the view), models,
  templates and the command output.
"""
from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QDockWidget, QFormLayout, QHBoxLayout, QInputDialog,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit,
                             QPushButton, QTabWidget, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)

from .. import theme
from ..web_site.frameworks import python_web as pw

TEMPLATE_LANGS = ("django-html", "jinja-html")
DJANGO_KW = sorted(set(pw.DJANGO_TAGS) | set(pw.DJANGO_FILTERS) | {"in", "not", "and", "or", "is", "as", "with",
                                                                     "only", "by", "on", "off", "None", "True",
                                                                     "False"})
JINJA_KW = sorted(set(pw.JINJA_TAGS) | set(pw.JINJA_FILTERS) | {"in", "not", "and", "or", "is", "as", "with",
                                                                 "without", "context", "ignore", "missing",
                                                                 "recursive", "scoped", "none", "true", "false"})

# ---------------------------------------------------------------- JavaScript injected into Monaco pages
JS_LANGS = """(function () {
  if (window.__radTplLangs) return; window.__radTplLangs = true;
  const KW = %s;
  const L = monaco.languages;
  [['django-html', 'Django Template'], ['jinja-html', 'Jinja Template']].forEach(([id, alias]) => {
    if (!L.getLanguages().some(l => l.id === id)) L.register({ id: id, aliases: [alias], extensions: [] });
  });
  require(['vs/basic-languages/twig/twig'], function (m) {
    ['django-html', 'jinja-html'].forEach(id => {
      const lang = Object.assign({}, m.language, { tokenPostfix: '.' + id, keywords: KW[id] });
      L.setMonarchTokensProvider(id, lang);
      L.setLanguageConfiguration(id, m.conf);
    });
  });
})();"""

JS_PROVIDERS = """(function () {
  if (window.__radPyWeb) return; window.__radPyWeb = true;
  const obj = window.radChannel && window.radChannel.objects.radPyWeb;
  if (!obj) return;
  const editor = window.radEditor;
  const ask = (fn, l, c) => new Promise(res => obj[fn](l, c, r => res(r)));
  const rng = (r, pos, w) => r ? new monaco.Range(r[0] + 1, r[1] + 1, r[2] + 1, r[3] + 1)
                              : new monaco.Range(pos.lineNumber, w.startColumn, pos.lineNumber, w.endColumn);
  ['python', 'html', 'django-html', 'jinja-html'].forEach(lang => {
    monaco.languages.registerCompletionItemProvider(lang, {
      triggerCharacters: ["'", '"', '%', '{', '|', '.', ' ', ':', '/', '(', ',', '_'],
      provideCompletionItems: async (model, pos) => {
        if (model !== editor.getModel()) return { suggestions: [] };
        let items = [];
        try { items = JSON.parse(await ask('complete', pos.lineNumber - 1, pos.column - 1) || '[]'); } catch (e) {}
        const w = model.getWordUntilPosition(pos);
        return { suggestions: items.map(i => ({ label: i.label, kind: i.kind, detail: i.detail || '',
          documentation: i.documentation || '', insertText: i.insertText || i.label, range: rng(i.range, pos, w),
          sortText: i.sortText || undefined, filterText: i.filterText || undefined })) };
      } });
  });
  editor.addAction({ id: 'rad.pyweb.definition', label: 'Go to Definition', keybindings: [monaco.KeyCode.F12],
    run: ed => { const p = ed.getPosition();
      obj.definition(p.lineNumber - 1, p.column - 1, ok => {
        if (!ok) window.radChannel.objects.rad.jsDefinition(p.lineNumber - 1, p.column - 1); }); } });
})();"""


def _js_langs() -> str:
    return JS_LANGS % json.dumps({"django-html": DJANGO_KW, "jinja-html": JINJA_KW})


class EditorBridge(QObject):
    """Published to each Monaco page as ``radPyWeb``."""

    def __init__(self, editor):
        super().__init__(editor)
        self.ed = editor

    def _root(self):
        root = getattr(self.ed, "_pyweb_root", None)
        if root is None:
            root = pw.project_root_of(self.ed.path)
            self.ed._pyweb_root = root or False
        return root or None

    @pyqtSlot(int, int, result=str)
    def complete(self, line, col):
        root = self._root()
        if root is None:
            return "[]"
        try:
            return json.dumps(pw.complete(root, self.ed.path, self.ed.text(), line, col)[:500])
        except Exception as e:  # noqa: BLE001 - completion must never break typing
            print(f"[python_web] completion failed: {e}")
            return "[]"

    @pyqtSlot(int, int, result=bool)
    def definition(self, line, col):
        root = self._root()
        if root is None:
            return False
        try:
            target = pw.definition(root, self.ed.path, self.ed.text(), line, col)
        except Exception as e:  # noqa: BLE001
            print(f"[python_web] definition failed: {e}")
            return False
        if not target:
            return False
        return open_location(self.ed.window(), target[0], target[1])


def open_location(win, path, line: int) -> bool:
    opener = getattr(win, "open_file", None)
    if not callable(opener):
        return False
    try:
        opener(Path(path), int(line or 1))
        return True
    except Exception:  # noqa: BLE001
        return False


def on_editor_ready(ed) -> None:
    """Every Monaco editor: template languages; editors of Python web projects: providers + F12."""
    try:
        ed._js(_js_langs())
        root = pw.project_root_of(ed.path)
        ed._pyweb_root = root or False
        if root is None:
            return
        fw = pw.framework_for(pw.project_language(root))
        if fw is None:
            return
        ed._js(JS_PROVIDERS)
        from ..monaco_editor import language_overrides, _path_key
        if pw.is_template(ed.path) and ed.language() in ("html", "custom") and \
                not language_overrides().get(_path_key(ed.path)):
            ed.set_language(fw.template_lang, remember=False)
        QTimer.singleShot(0, lambda: pw.project_index(root, fw))       # warm the index
    except Exception as e:  # noqa: BLE001 - never break the editor
        print(f"[python_web] editor hook: {e}")


# ---------------------------------------------------------------- framework panel
def active_project(win):
    """The Python web project the panel works on (active project, else the startup project)."""
    cands = [getattr(win, "project", None)]
    sp = getattr(win, "startup_project", None)
    if callable(sp):
        try:
            cands.append(sp())
        except Exception:  # noqa: BLE001
            pass
    sln = getattr(win, "sln", None)
    cands += list(getattr(sln, "projects", []) or [])
    for p in cands:
        if p is not None and str(getattr(p, "language", "")).startswith("python-") and \
                pw.framework_for(p.language) is not None:
            return p
    return None


class CredentialsDialog(QDialog):
    def __init__(self, parent, fields: list[str], title: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        lay = QFormLayout(self)
        self.edits = {}
        for f in fields:
            e = QLineEdit()
            if f == "password":
                e.setEchoMode(QLineEdit.EchoMode.Password)
            if f == "username":
                e.setText("admin")
            lay.addRow(f.capitalize() + ":", e)
            self.edits[f] = e
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addRow(bb)

    def values(self) -> dict:
        return {k: e.text() for k, e in self.edits.items()}


class PyWebPanel(QWidget):
    runtimeDone = pyqtSignal()               # emitted by the index thread (queued to the GUI thread)

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.runtimeDone.connect(self._after_runtime)
        self.project = None
        self.fw = None
        self.proc: QProcess | None = None
        self.last_output = ""
        self.last_exit = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        top = QHBoxLayout()
        self.title = QLabel("No Django / Flask / FastAPI project")
        theme.role(self.title, "heading")
        top.addWidget(self.title, 1)
        self.refresh_btn = QToolButton()
        self.refresh_btn.setText("Refresh")
        self.refresh_btn.setToolTip("Read the URLs, models and templates from the project again")
        self.refresh_btn.clicked.connect(lambda: self.refresh(runtime=True))
        top.addWidget(self.refresh_btn)
        lay.addLayout(top)
        self.status = QLabel("")
        theme.role(self.status, "muted")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.buttons = QWidget()
        self.buttons_lay = QHBoxLayout(self.buttons)
        self.buttons_lay.setContentsMargins(0, 0, 0, 0)
        self.buttons_lay.setSpacing(4)
        lay.addWidget(self.buttons)
        self.tabs = QTabWidget()
        self.urls = QTreeWidget()
        self.urls.setHeaderLabels(["Name", "URL", "Methods", "View"])
        self.urls.setRootIsDecorated(False)
        self.urls.itemDoubleClicked.connect(lambda it, _c: self.open_url_item(it))
        self.urls.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.urls.customContextMenuRequested.connect(self._url_menu)
        self.tabs.addTab(self.urls, "URLs")
        self.models = QTreeWidget()
        self.models.setHeaderLabels(["Model / field", "Type", "Related"])
        self.models.itemDoubleClicked.connect(self._open_model)
        self.tabs.addTab(self.models, "Models")
        self.templates = QListWidget()
        self.templates.itemDoubleClicked.connect(lambda it: open_location(self.win, it.data(Qt.ItemDataRole.UserRole), 1))
        self.tabs.addTab(self.templates, "Templates")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(5000)
        self.tabs.addTab(self.output, "Output")
        lay.addWidget(self.tabs, 1)

    # ------------------------------------------------------------ state
    def sync_project(self, force: bool = False) -> None:
        p = active_project(self.win)
        if p is self.project and not force:
            return
        self.project = p
        self.fw = pw.framework_for(p.language) if p is not None else None
        self._make_buttons()
        self.refresh()

    def folder(self) -> Path | None:
        return Path(self.project.folder).resolve() if self.project is not None else None

    def _make_buttons(self) -> None:
        while self.buttons_lay.count():
            w = self.buttons_lay.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        if self.fw is None:
            self.title.setText("No Django / Flask / FastAPI project")
            dock = getattr(self.win, "dock_python_web", None)
            if dock is not None:
                dock.setWindowTitle("Python Web")
            return
        self.title.setText(f"{self.fw.title}: {self.project.name}")
        dock = getattr(self.win, "dock_python_web", None)
        if dock is not None:
            dock.setWindowTitle(self.fw.title)
        self.tabs.setTabText(0, self.fw.url_label)
        self.tabs.setTabVisible(1, self.fw.id == "django")
        cmds = self.fw.commands(self.folder(), pw.web_block(self.folder()))
        main, more = cmds[:5], cmds[5:]
        for c in main:
            b = QPushButton(c.title)
            b.setToolTip(c.tip)
            b.clicked.connect(lambda _=False, cid=c.id: self.run_command(cid))
            self.buttons_lay.addWidget(b)
        if more:
            b = QToolButton()
            b.setText("More")
            b.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            m = QMenu(b)
            for c in more:
                a = m.addAction(c.title)
                a.setToolTip(c.tip)
                a.triggered.connect(lambda _=False, cid=c.id: self.run_command(cid))
            b.setMenu(m)
            self.buttons_lay.addWidget(b)
        self.buttons_lay.addStretch(1)

    def refresh(self, runtime: bool = False) -> None:
        self.urls.clear()
        self.models.clear()
        self.templates.clear()
        if self.project is None or self.fw is None:
            self.status.setText("Open or create a Django, Flask or FastAPI project (New Project > Web).")
            return
        folder = self.folder()
        if runtime:
            self.status.setText("Reading the project...")
            pw.refresh_runtime(folder, self.fw, on_done=lambda *_a: self.runtimeDone.emit())
        idx = pw.project_index(folder, self.fw)
        for u in idx.get("urls", []):
            if u.get("name") in ("static",) and not u.get("file"):
                continue
            view = ""
            f = u.get("file") or u.get("decl_file")
            if f:
                try:
                    view = f"{Path(f).resolve().relative_to(folder).as_posix()}:{u.get('line') or u.get('decl_line')}"
                except ValueError:
                    view = Path(f).name
            pat = u.get("pattern", "")
            url = pat if pat.startswith("/") else "/" + pat
            it = QTreeWidgetItem([u.get("name", ""), url, ", ".join(u.get("methods") or []), view])
            it.setData(0, Qt.ItemDataRole.UserRole, u)
            self.urls.addTopLevelItem(it)
        for i in range(4):
            self.urls.resizeColumnToContents(i)
        for name, m in sorted((idx.get("models") or {}).items()):
            if "site-packages" in str(m.get("file") or "") and name != "User":
                continue                      # Django's own models (sessions, content types...) except User
            top = QTreeWidgetItem([name, m.get("app", ""), m.get("table", "")])
            top.setData(0, Qt.ItemDataRole.UserRole, (m.get("file"), m.get("line")))
            for f in m.get("fields", []):
                QTreeWidgetItem(top, [f["name"], f.get("type", ""), f.get("related") or ""])
            self.models.addTopLevelItem(top)
        for t in idx.get("templates", []):
            if "site-packages" in str(t.get("file", "")):
                continue
            it = QListWidgetItem(t["name"])
            it.setData(Qt.ItemDataRole.UserRole, t["file"])
            it.setToolTip(t["file"])
            self.templates.addItem(it)
        venv = pw.venv_python(folder)
        self.status.setText((f".venv: {venv}" if venv else "No .venv yet - the first run creates it.") +
                            "   |   " + pw.index_status(folder, self.fw))

    def _after_runtime(self):
        self.refresh(runtime=False)

    # ------------------------------------------------------------ URLs
    def _url_menu(self, pos):
        it = self.urls.itemAt(pos)
        if it is None:
            return
        u = it.data(0, Qt.ItemDataRole.UserRole) or {}
        m = QMenu(self)
        m.addAction("Open in Preview", lambda: self.open_url_item(it))
        if u.get("file") or u.get("decl_file"):
            m.addAction("Go to View", lambda: open_location(self.win, u.get("file") or u.get("decl_file"),
                                                            u.get("line") or u.get("decl_line") or 1))
        if u.get("decl_file"):
            m.addAction("Go to URL Declaration", lambda: open_location(self.win, u["decl_file"], u.get("decl_line", 1)))
        from PyQt6.QtWidgets import QApplication
        m.addAction("Copy Name", lambda: QApplication.clipboard().setText(u.get("name", "")))
        m.exec(self.urls.viewport().mapToGlobal(pos))

    def url_path(self, u: dict, values: dict | None = None) -> str | None:
        import re
        pat = str(u.get("pattern", ""))
        if pat.startswith("^"):
            pat = pat.lstrip("^").rstrip("$")
        args = list(u.get("args") or [])
        values = dict(values or {})
        for a in args:
            if a not in values:
                if pw_offscreen():
                    values[a] = "1"
                    continue
                v, ok = QInputDialog.getText(self, "Open URL", f"Value of <{a}>:", text="1")
                if not ok:
                    return None
                values[a] = v
        path = re.sub(r"<(?:\w+:)?(\w+)>", lambda m: str(values.get(m.group(1), "1")), pat)
        path = re.sub(r"\{(\w+)(?::\w+)?\}", lambda m: str(values.get(m.group(1), "1")), path)
        path = re.sub(r"\(\?P<(\w+)>[^)]*\)", lambda m: str(values.get(m.group(1), "1")), path)
        return path if path.startswith("/") else "/" + path

    def open_url_item(self, it, values: dict | None = None) -> str:
        u = it.data(0, Qt.ItemDataRole.UserRole) or {}
        methods = u.get("methods") or ["GET"]
        if "GET" not in methods:
            self.win.statusBar().showMessage(f"{u.get('name')} answers {', '.join(methods)} only", 5000)
        path = self.url_path(u, values)
        return self.open_path(path) if path is not None else ""

    def open_path(self, path: str) -> str:
        from . import web_workspace as ww
        srv = ww._ensure_server(self.win, self.project.folder)
        if srv is None:
            return ""
        url = srv.url_for(path)
        self.win.web_preview.open_url(url)
        return url

    def _open_model(self, it, _col):
        data = it.data(0, Qt.ItemDataRole.UserRole)
        if data and data[0]:
            open_location(self.win, data[0], data[1] or 1)

    # ------------------------------------------------------------ commands
    def command(self, cid: str):
        if self.fw is None:
            return None
        return next((c for c in self.fw.commands(self.folder(), pw.web_block(self.folder())) if c.id == cid), None)

    def run_command(self, cid: str, values: dict | None = None) -> bool:
        """Run a panel command; *values* answers its questions (tests / scripts) instead of the dialogs."""
        c = self.command(cid)
        if c is None:
            return False
        if cid == "runserver":
            from . import web_workspace as ww
            ww.run_website(self.win, self.project)
            return True
        if cid in ("admin", "docs", "redoc", "openapi"):
            self.open_path({"admin": "/admin/", "docs": "/docs", "redoc": "/redoc",
                            "openapi": "/openapi.json"}[cid])
            return True
        values = dict(values or {})
        for q in c.ask:
            if q in values:
                continue
            if c.id == "createsuperuser" and not pw_offscreen():
                dlg = CredentialsDialog(self, c.ask, "Create superuser")
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    return False
                values.update(dlg.values())
                break
            if pw_offscreen():
                return False
            v, ok = QInputDialog.getText(self, c.title, f"{q.capitalize()}:")
            if not ok or not v.strip():
                return False
            values[q] = v.strip()
        py = pw.venv_python(self.folder())
        if not py:
            QMessageBox.information(self, self.fw.title, "The project has no .venv yet - run the site once (Ctrl+F5) "
                                                         "to create it.") if not pw_offscreen() else None
            return False
        argv = []
        for a in c.argv:                     # "{name}" alone = the typed words ("showmigrations blog")
            argv += values.get("name", "").split() if a == "{name}" else [a.replace("{name}", values.get("name", ""))]
        env = self.fw.server_env(self.folder(), pw.web_block(self.folder()))
        if c.id == "createsuperuser":
            env.update({"DJANGO_SUPERUSER_USERNAME": values.get("username", ""),
                        "DJANGO_SUPERUSER_EMAIL": values.get("email", ""),
                        "DJANGO_SUPERUSER_PASSWORD": values.get("password", "")})
        if c.terminal:
            return self._in_terminal(py, argv, env)
        return self._run(py, argv, env, c, values)

    def _in_terminal(self, py: str, argv: list[str], env: dict) -> bool:
        term = getattr(self.win, "terminal", None)
        if term is None:
            return False
        from .terminal import show_terminal
        show_terminal(self.win)
        ps = "powershell" in term.shell.currentText().lower() if hasattr(term, "shell") else False
        sets = "; ".join(f"$env:{k}='{v}'" for k, v in env.items()) if ps else \
            " && ".join(f'set "{k}={v}"' for k, v in env.items())
        q = lambda s: f'"{s}"' if " " in s else s  # noqa: E731
        cd = (f"Set-Location '{self.folder()}'" if ps else f'cd /d "{self.folder()}"')
        call = ("& " if ps else "") + " ".join(q(x) for x in [py] + argv)
        sep = "; " if ps else " && "
        term.run_command(sep.join(x for x in (cd, sets, call) if x))
        return True

    def _run(self, py: str, argv: list[str], env: dict, c, values: dict) -> bool:
        if self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning:
            self.win.statusBar().showMessage("A command is still running", 4000)
            return False
        self.tabs.setCurrentWidget(self.output)
        self.output.appendPlainText(f"> {Path(py).name} {' '.join(argv)}")
        self.last_output = ""
        self.last_exit = None
        p = QProcess(self)
        p.setWorkingDirectory(str(self.folder()))
        e = QProcessEnvironment.systemEnvironment()
        for k, v in {"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", **env}.items():
            e.insert(k, v)
        p.setProcessEnvironment(e)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        def read():
            text = bytes(p.readAllStandardOutput()).decode("utf-8", "replace")
            self.last_output += text
            self.output.moveCursor(self.output.textCursor().MoveOperation.End)
            self.output.insertPlainText(text)
            self.output.ensureCursorVisible()

        def done(code, _status):
            read()
            self.last_exit = code
            self.output.appendPlainText(f"--- exit code {code} ---\n")
            self.win.log(f"[{self.fw.title}] {c.title}: exit code {code}")
            if code == 0 and c.id == "startapp":
                self._added_app(values.get("name", ""))
            if c.id in ("makemigrations", "migrate", "startapp"):
                self.refresh(runtime=True)
        p.readyReadStandardOutput.connect(read)
        p.finished.connect(done)
        self.proc = p
        p.start(py, argv)
        return True

    def wait(self, timeout: float = 120.0) -> int | None:
        """Block until the running command ends (tests); *timeout* in seconds."""
        import time
        from PyQt6.QtWidgets import QApplication
        deadline = time.monotonic() + timeout
        while self.proc is not None and self.last_exit is None and time.monotonic() < deadline:
            self.proc.waitForFinished(100)
            QApplication.processEvents()
        return self.last_exit

    def _added_app(self, app: str) -> None:
        from ..web_site.frameworks.django import add_installed_app, settings_file
        sf = settings_file(self.folder(), pw.web_block(self.folder()))
        if sf is None or not app:
            return
        text = sf.read_text(encoding="utf-8")
        new = add_installed_app(text, app)
        if new != text:
            sf.write_text(new, encoding="utf-8", newline="\n")
            self.output.appendPlainText(f"Added '{app}' to INSTALLED_APPS in {sf.name}")
        try:
            self.win._fill_solution()
        except Exception:  # noqa: BLE001
            pass


def pw_offscreen() -> bool:
    import os
    return os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"


# ---------------------------------------------------------------- install
def install(win) -> None:
    try:
        from ..monaco_editor import LANGUAGE_CHOICES, MonacoEditor
        MonacoEditor.channel_objects["radPyWeb"] = EditorBridge
        if on_editor_ready not in MonacoEditor.ready_hooks:
            MonacoEditor.ready_hooks.append(on_editor_ready)
        for item in (("Django Template", "django-html"), ("Jinja Template", "jinja-html")):
            if item not in LANGUAGE_CHOICES:
                LANGUAGE_CHOICES.append(item)
    except ImportError:                       # no QtWebEngine: the built-in editor
        pass
    try:
        from .. import icons
        icons.TEMPLATE_BADGES.setdefault("django-app", ("Dj", "#0C4B33"))
        icons.TEMPLATE_BADGES.setdefault("flask-app", ("Fk", "#2B2B2B"))
        icons.TEMPLATE_BADGES.setdefault("fastapi-app", ("FA", "#009688"))
    except Exception:  # noqa: BLE001
        pass
    panel = PyWebPanel(win)
    win.python_web = panel
    d = QDockWidget("Python Web", win)
    d.setObjectName("PythonWebPanel")
    d.setWidget(panel)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, d)
    try:
        win.tabifyDockWidget(win.dock_output, d)
    except Exception:  # noqa: BLE001
        pass
    d.hide()
    win.dock_python_web = d
    d.visibilityChanged.connect(lambda vis: vis and panel.sync_project())
    act = d.toggleViewAction()
    act.setText("Django / Flask / FastAPI Panel")
    win.a_python_web = act
    try:
        from .workbench import register_view
        register_view("python-web", "Python Web", factory=lambda w: w.dock_python_web, area="panel", order=80,
                      tooltip="Django / Flask / FastAPI: manage.py commands, URLs, models, templates")
    except Exception:  # noqa: BLE001 - the VS Code layout is optional
        pass

    def later():
        for name in ("View", "Site"):
            m = next((a.menu() for a in win.menuBar().actions() if a.menu() is not None
                      and a.text().replace("&", "") == name), None)
            if m is not None and act not in m.actions():
                m.addSeparator()
                m.addAction(act)
        sig = getattr(win, "web_signals", None)
        if sig is not None:
            sig.siteOpened.connect(lambda p: _site_opened(win, p))
    QTimer.singleShot(0, later)

    # follow the active project (cheap identity check)
    timer = QTimer(win)
    timer.setInterval(1500)
    timer.timeout.connect(lambda: d.isVisible() and panel.sync_project())
    timer.start()
    win._python_web_timer = timer


def _site_opened(win, project) -> None:
    if project is None or not str(getattr(project, "language", "")).startswith("python-"):
        return
    fw = pw.framework_for(project.language)
    if fw is None:
        return
    QTimer.singleShot(0, lambda: pw.project_index(Path(project.folder), fw))
    panel = win.python_web
    panel.sync_project(force=True)
    if not getattr(win, "_python_web_shown", False):
        win._python_web_shown = True
        win.dock_python_web.show()


__all__ = ["EditorBridge", "PyWebPanel", "active_project", "install", "on_editor_ready", "open_location"]
