"""CodeIgniter 4 in the IDE (engine: radide/web_site/frameworks/codeigniter.py).

- **New Project > Web > "CodeIgniter 4 App"**: ``composer create-project codeigniter4/appstarter`` with progress,
  ``.env`` (development, SQLite3 ``writable/database.db`` or the local MariaDB / PostgreSQL server), web root
  ``public/``, ``web.framework = "codeigniter"``.
- **Run / Debug**: the normal website F5 / Ctrl+F5 (DevServer + ``php -S`` with CodeIgniter's ``rewrite.php``,
  Preview, Requests, live reload, Xdebug breakpoints) - the router / base URL come from the engine's
  ``backend_spec`` (called by ``languages/php_web.py``).
- **CodeIgniter panel** (View > CodeIgniter, Site menu, VS Code side panel): *Spark* - every ``php spark list``
  command; double-click opens a form built from ``php spark help <command>`` (make:controller, make:model,
  make:migration, migrate, db:seed ... - created files open in the editor); *Routes* - ``php spark routes``
  (double-click = the controller method, Open in Preview for GET routes); *Output*.
- **IntelliSense from the project** in Monaco (QWebChannel object ``radCI``, next to intelephense): view /
  route / lang / config / helper / service / model / field / rule / section / env names, refreshed when the
  project changes; **F12** on such a string opens its declaration (other words go to the normal Go to Definition).
- Opening a CodeIgniter site without ``vendor/`` offers ``composer install`` (+ ``.env`` and migrate / seed).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget, QFormLayout,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QMessageBox, QPlainTextEdit,
                             QPushButton, QTabWidget, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)

from ..web_site.frameworks import codeigniter as ci

ROLE = Qt.ItemDataRole.UserRole
QUICK = [("migrate", "Migrate", "php spark migrate --all"),
         ("db:seed", "Seed...", "php spark db:seed <Seeder>"),
         ("make:controller", "Controller...", "php spark make:controller"),
         ("make:model", "Model...", "php spark make:model"),
         ("make:migration", "Migration...", "php spark make:migration")]


def _offscreen() -> bool:
    return os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"


# ---------------------------------------------------------------- JavaScript injected into Monaco pages
JS_PROVIDERS = """(function () {
  if (window.__radCI) return; window.__radCI = true;
  const obj = window.radChannel && window.radChannel.objects.radCI;
  if (!obj) return;
  const editor = window.radEditor;
  const ask = (fn, l, c) => new Promise(res => obj[fn](l, c, r => res(r)));
  ['php', 'html'].forEach(lang => {
    monaco.languages.registerCompletionItemProvider(lang, {
      triggerCharacters: ["'", '"', '.', '/', '>', '|', ':', '\\\\'],
      provideCompletionItems: async (model, pos) => {
        if (model !== editor.getModel()) return { suggestions: [] };
        let items = [];
        try { items = JSON.parse(await ask('complete', pos.lineNumber - 1, pos.column - 1) || '[]'); } catch (e) {}
        return { suggestions: items.map(i => ({ label: i.label, kind: i.kind, detail: i.detail || '',
          documentation: i.documentation || '', insertText: i.insertText || i.label,
          range: new monaco.Range(i.range[0] + 1, i.range[1] + 1, i.range[2] + 1, i.range[3] + 1),
          sortText: i.sortText || undefined, filterText: i.filterText || undefined })) };
      } });
  });
  editor.addAction({ id: 'rad.ci.definition', label: 'Go to Definition', keybindings: [monaco.KeyCode.F12],
    run: ed => { const p = ed.getPosition();
      obj.definition(p.lineNumber - 1, p.column - 1, ok => {
        if (!ok) window.radChannel.objects.rad.jsDefinition(p.lineNumber - 1, p.column - 1); }); } });
})();"""


class EditorBridge(QObject):
    """Published to each Monaco page as ``radCI`` (active only in CodeIgniter projects)."""

    def __init__(self, editor):
        super().__init__(editor)
        self.ed = editor

    def _root(self):
        return ci.project_root_of(self.ed.path)

    @pyqtSlot(int, int, result=str)
    def complete(self, line, col):
        root = self._root()
        if root is None:
            return "[]"
        try:
            return json.dumps(ci.complete(root, self.ed.path, self.ed.text(), line, col))
        except Exception as e:  # noqa: BLE001 - completion must never break typing
            print(f"[codeigniter] completion failed: {e}")
            return "[]"

    @pyqtSlot(int, int, result=bool)
    def definition(self, line, col):
        root = self._root()
        if root is None:
            return False
        try:
            target = ci.definition(root, self.ed.path, self.ed.text(), line, col)
        except Exception as e:  # noqa: BLE001
            print(f"[codeigniter] definition failed: {e}")
            return False
        return bool(target) and open_location(self.ed.window(), target[0], target[1])


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
    try:
        if ci.project_root_of(ed.path) is None:
            return
        ed._js(JS_PROVIDERS)
        root = ci.project_root_of(ed.path)
        QTimer.singleShot(0, lambda: ci.index(root))          # warm the index
    except Exception as e:  # noqa: BLE001 - never break the editor
        print(f"[codeigniter] editor hook: {e}")


# ---------------------------------------------------------------- helpers
def ci_projects(win) -> list:
    cands = [getattr(win, "project", None)]
    sp = getattr(win, "startup_project", None)
    if callable(sp):
        try:
            cands.append(sp())
        except Exception:  # noqa: BLE001
            pass
    cands += list(getattr(getattr(win, "sln", None), "projects", []) or [])
    out = []
    for p in cands:
        folder = getattr(p, "folder", None)          # (solution entries without a loaded project have none)
        if folder and p not in out and ci.is_ci_project(folder):
            out.append(p)
    return out


def active_project(win):
    ps = ci_projects(win)
    return ps[0] if ps else None


def created_file(output: str, root: Path) -> Path | None:
    """The file a make:* command reports ("File created: APPPATH\\Controllers\\Foo.php")."""
    m = re.search(r"File (?:created|overwritten):\s*(\S+)", output)
    if not m:
        return None
    rel = m.group(1).strip().replace("\\", "/")
    for prefix, base in (("APPPATH/", root / "app"), ("ROOTPATH/", root), ("WRITEPATH/", root / "writable")):
        if rel.upper().startswith(prefix):
            p = base / rel[len(prefix):]
            return p if p.is_file() else None
    p = Path(rel) if Path(rel).is_absolute() else root / rel
    return p if p.is_file() else None


# ---------------------------------------------------------------- Spark command form
class SparkForm(QDialog):
    """A form for one spark command, built from ``php spark help <command>``."""

    def __init__(self, parent, root: Path, command: str, info: ci.SparkHelp, seeders=()):
        super().__init__(parent)
        self.root = root
        self.command = command
        self.info = info
        self.setWindowTitle(f"php spark {command}")
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        desc = QLabel(info.description or command)
        desc.setWordWrap(True)
        lay.addWidget(desc)
        form = QFormLayout()
        self.args: list[tuple[str, QWidget]] = []
        self.opts: list[tuple[str, str, QWidget]] = []
        for name, help_text in info.arguments:
            if command == "db:seed" and name == "seeder_name" or (command == "db:seed" and len(info.arguments) == 1):
                w = QComboBox()
                w.setEditable(True)
                w.addItems(list(seeders) or ["DatabaseSeeder"])
                if "DatabaseSeeder" in seeders:
                    w.setCurrentText("DatabaseSeeder")
            else:
                w = QLineEdit()
                w.setPlaceholderText(help_text)
            w.setToolTip(help_text)
            form.addRow(f"{name}:", w)
            self.args.append((name, w))
        for opt, help_text in info.options:
            kind, choices, default = info.option_kind(opt)
            if kind == "choice":
                w = QComboBox()
                w.addItem("")
                w.addItems(choices)
            elif kind == "value":
                w = QLineEdit()
                w.setPlaceholderText(default or help_text[:60])
            else:
                w = QCheckBox(help_text[:90])
            w.setToolTip(help_text)
            form.addRow(opt + ":", w)
            self.opts.append((opt, kind, w))
        self.extra = QLineEdit()
        self.extra.setPlaceholderText("more arguments (optional)")
        form.addRow("Extra:", self.extra)
        lay.addLayout(form)
        self.preview = QLabel()
        self.preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.preview.setStyleSheet("font-family: Consolas, monospace;")
        lay.addWidget(self.preview)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Run")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        for _n, w in self.args:
            (w.currentTextChanged if isinstance(w, QComboBox) else w.textChanged).connect(self._update)
        for _o, _k, w in self.opts:
            if isinstance(w, QCheckBox):
                w.toggled.connect(self._update)
            elif isinstance(w, QComboBox):
                w.currentTextChanged.connect(self._update)
            else:
                w.textChanged.connect(self._update)
        self.extra.textChanged.connect(self._update)
        self._update()

    def set_value(self, name: str, value) -> None:
        for n, w in self.args:
            if n == name:
                w.setCurrentText(value) if isinstance(w, QComboBox) else w.setText(value)
        for o, _k, w in self.opts:
            if o == name:
                if isinstance(w, QCheckBox):
                    w.setChecked(bool(value))
                elif isinstance(w, QComboBox):
                    w.setCurrentText(value)
                else:
                    w.setText(value)
        self._update()

    def argv(self) -> list[str]:
        out = [self.command]
        for _n, w in self.args:
            v = (w.currentText() if isinstance(w, QComboBox) else w.text()).strip()
            if v:
                out.append(v)
        for opt, kind, w in self.opts:
            if kind == "flag" and w.isChecked():
                out.append(opt)
            elif kind == "choice" and w.currentText():
                out += [opt, w.currentText()]
            elif kind == "value" and w.text().strip():
                out += [opt, w.text().strip()]
        if self.extra.text().strip():
            out += self.extra.text().split()
        return out

    def _update(self, *_a):
        self.preview.setText("php spark " + " ".join(f'"{a}"' if " " in a else a for a in self.argv()))


# ---------------------------------------------------------------- the panel
class CodeIgniterPanel(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.project = None
        self.proc: QProcess | None = None
        self.routes_proc: QProcess | None = None
        self.last_output = ""
        self.last_exit: int | None = None
        self.last_created: Path | None = None
        self.commands: list[ci.SparkCommand] = []
        self.routes: list[ci.Route] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        top = QHBoxLayout()
        self.title = QLabel("No CodeIgniter project")
        f = self.title.font()
        f.setBold(True)
        self.title.setFont(f)
        top.addWidget(self.title, 1)
        self.buttons: dict[str, QPushButton] = {}
        for cmd, text, tip in QUICK:
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, c=cmd: self.open_form(c))
            top.addWidget(b)
            self.buttons[cmd] = b
        more = QToolButton()
        more.setText("More")
        more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        m = QMenu(more)
        m.addAction("composer install", lambda: self.composer(["install"]))
        m.addAction("composer update", lambda: self.composer(["update"]))
        m.addSeparator()
        m.addAction("Open .env", lambda: self.open_rel(".env"))
        m.addAction("Open app/Config/Routes.php", lambda: self.open_rel("app/Config/Routes.php"))
        m.addAction("Open Database in the Databases workspace", self.show_database)
        m.addSeparator()
        m.addAction("Run a spark command...", self.run_typed)
        more.setMenu(m)
        top.addWidget(more)
        self.refresh_btn = QToolButton()
        self.refresh_btn.setText("Refresh")
        self.refresh_btn.setToolTip("Read the commands and routes from the project again")
        self.refresh_btn.clicked.connect(lambda: self.refresh(force=True))
        top.addWidget(self.refresh_btn)
        lay.addLayout(top)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.tabs = QTabWidget()
        self.spark_tree = QTreeWidget()
        self.spark_tree.setHeaderLabels(["Command", "Description"])
        self.spark_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.spark_tree.itemDoubleClicked.connect(self._spark_activated)
        self.tabs.addTab(self.spark_tree, "Spark")
        self.routes_tree = QTreeWidget()
        self.routes_tree.setHeaderLabels(["Method", "Route", "Name", "Handler", "Filters"])
        self.routes_tree.setRootIsDecorated(False)
        self.routes_tree.itemDoubleClicked.connect(lambda it, _c: self.open_route(it))
        self.routes_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.routes_tree.customContextMenuRequested.connect(self._route_menu)
        self.tabs.addTab(self.routes_tree, "Routes")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(5000)
        self.tabs.addTab(self.output, "Output")
        lay.addWidget(self.tabs, 1)

    # ------------------------------------------------------------ state
    def folder(self) -> Path | None:
        return Path(self.project.folder).resolve() if self.project is not None else None

    def php(self) -> str:
        return ci.php_for(self.project) if self.project is not None else ""

    def sync_project(self, force: bool = False) -> None:
        p = active_project(self.win)
        if p is self.project and not force:
            return
        self.project = p
        self.refresh(force=True)

    def refresh(self, force: bool = False) -> None:
        self.spark_tree.clear()
        self.routes_tree.clear()
        on = self.project is not None
        for b in self.buttons.values():
            b.setEnabled(on)
        if not on:
            self.title.setText("No CodeIgniter project")
            self.status.setText("Open or create a CodeIgniter 4 site (New Project > Web > CodeIgniter 4 App).")
            return
        root = self.folder()
        ver = ci.framework_version(root)
        self.title.setText(f"CodeIgniter {ver or '4'}: {self.project.name}")
        if not (root / "vendor" / "autoload.php").is_file():
            self.status.setText("vendor/ is missing - More > composer install (Spark needs it).")
            return
        php = self.php()
        try:
            from ..web_site.php_toolchain import php_version
            pv = php_version(php)
        except Exception:  # noqa: BLE001
            pv = ""
        self.status.setText(f"PHP {pv or '?'} ({php})  -  double-click a command for its form, a route for its "
                            "controller method")
        if force or not self.commands:
            self.commands = ci.spark_commands(root, php)
        groups: dict[str, QTreeWidgetItem] = {}
        for c in self.commands:
            g = groups.get(c.group)
            if g is None:
                g = QTreeWidgetItem([c.group or "Commands", ""])
                g.setFlags(g.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                self.spark_tree.addTopLevelItem(g)
                g.setExpanded(c.group in ("Database", "Generators", "CodeIgniter"))
                groups[c.group] = g
            it = QTreeWidgetItem([c.name, c.description])
            it.setData(0, ROLE, c.name)
            it.setToolTip(1, c.description)
            g.addChild(it)
        self.fill_routes([r for r in ci.static_routes(root)], static=True)
        self.load_routes()

    # ------------------------------------------------------------ routes
    def load_routes(self) -> None:
        root = self.folder()
        if root is None or (self.routes_proc is not None and
                            self.routes_proc.state() != QProcess.ProcessState.NotRunning):
            return
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.setWorkingDirectory(str(root))
        argv = ci.spark_argv(root, ["routes", "--no-ansi"], self.php())
        p.finished.connect(lambda code, _s, proc=p: self._routes_done(proc, code))
        self.routes_proc = p
        p.start(argv[0], argv[1:])

    def _routes_done(self, proc: QProcess, code: int) -> None:
        text = bytes(proc.readAll()).decode("utf-8", "replace")
        self.routes_proc = None
        routes = ci.parse_spark_routes(text) if code == 0 else []
        if not routes:
            return
        static = ci.static_routes(self.folder())
        for r in routes:
            for s in static:
                if s.path.strip("/") == re.sub(r"\(\[0-9\]\+\)", "(:num)", r.path).strip("/"):
                    r.file, r.line = s.file, s.line
                    break
        self.fill_routes(routes, static=False)

    def fill_routes(self, routes: list[ci.Route], static: bool) -> None:
        self.routes = routes
        self.routes_tree.clear()
        for r in routes:
            it = QTreeWidgetItem([r.method, "/" + r.path.strip("/"), r.name if r.name != r.path else "",
                                  r.handler, r.filters])
            it.setData(0, ROLE, r)
            self.routes_tree.addTopLevelItem(it)
        for i in range(4):
            self.routes_tree.resizeColumnToContents(i)
        self.tabs.setTabText(1, f"Routes ({len(routes)})" + (" - Routes.php" if static else ""))

    def open_route(self, it) -> bool:
        r = it.data(0, ROLE) if it is not None else None
        if r is None or self.folder() is None:
            return False
        loc = ci.handler_location(self.folder(), r.handler)
        if loc is None and r.file:
            loc = (r.file, r.line)
        return bool(loc) and open_location(self.win, loc[0], loc[1])

    def preview_route(self, r: ci.Route) -> None:
        try:
            from .web_workspace import _ensure_server
            srv = _ensure_server(self.win, self.folder() / "spark")
            if srv is not None:
                self.win.web_preview.open_url(srv.url.rstrip("/") + r.url_path())
        except Exception as e:  # noqa: BLE001
            self.win.log(f"[codeigniter] preview: {e}")

    def _route_menu(self, pos):
        it = self.routes_tree.itemAt(pos)
        if it is None:
            return
        r = it.data(0, ROLE)
        m = QMenu(self)
        m.addAction("Go to Controller Method", lambda: self.open_route(it))
        if r.file:
            m.addAction("Go to Routes.php", lambda: open_location(self.win, r.file, r.line))
        if r.method in ("GET", "ANY"):
            m.addAction("Open in Preview", lambda: self.preview_route(r))
        m.exec(self.routes_tree.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------ spark
    def _spark_activated(self, it, _col=0):
        name = it.data(0, ROLE)
        if name:
            self.open_form(name)

    def make_form(self, command: str) -> SparkForm | None:
        root = self.folder()
        if root is None:
            return None
        info = ci.spark_help(root, command, self.php())
        seeders = ci.index(root).seeders
        return SparkForm(self, root, command, info, seeders)

    def open_form(self, command: str, values: dict | None = None, exec_: bool = True):
        form = self.make_form(command)
        if form is None:
            return None
        if command == "migrate":
            form.set_value("--all", True)
        for k, v in (values or {}).items():
            form.set_value(k, v)
        if not exec_:
            return form
        if form.exec():
            return self.run_spark(form.argv())
        return None

    def run_typed(self):
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "Spark", "php spark", text="")
        if ok and text.strip():
            self.run_spark(text.split())

    def run_spark(self, args: list[str], on_done=None) -> QProcess | None:
        root = self.folder()
        if root is None:
            return None
        if self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning:
            self.win.log("*** a spark command is still running")
            return None
        argv = ci.spark_argv(root, [*args, "--no-ansi"] if "--no-ansi" not in args else args, self.php())
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.setWorkingDirectory(str(root))
        env = QProcessEnvironment.systemEnvironment()
        env.insert("NO_COLOR", "1")
        p.setProcessEnvironment(env)
        self.proc = p
        self.last_output = ""
        self.last_exit = None
        self.last_created = None
        self.tabs.setCurrentWidget(self.output)
        line = "php spark " + " ".join(args)
        self.output.appendPlainText(f"> {line}")
        self.win.log(f"------ {line} ({self.project.name}) ------")

        def read():
            text = bytes(p.readAllStandardOutput()).decode("utf-8", "replace").replace("\r\n", "\n")
            if text:
                self.last_output += text
                self.output.appendPlainText(text.rstrip("\n"))
                self.win.log(text.rstrip("\n"))

        def done(code, _status):
            read()
            self.last_exit = code
            self.output.appendPlainText(f"(exit code {code})\n")
            self.proc = None
            ci.invalidate(root)
            cmd = args[0] if args else ""
            if cmd.startswith("make:") and code == 0:
                f = created_file(self.last_output, root)
                self.last_created = f
                if f is not None:
                    open_location(self.win, f, 1)
                    self._refresh_explorer()
            if cmd.startswith(("migrate", "db:")):
                self._refresh_databases()
            if cmd in ("routes",) or cmd.startswith("make:"):
                self.load_routes()
            if on_done is not None:
                on_done(code, self.last_output)
        p.readyReadStandardOutput.connect(read)
        p.finished.connect(done)
        p.start(argv[0], argv[1:])
        return p

    def _refresh_explorer(self):
        fn = getattr(self.win, "_fill_solution", None) or getattr(self.win, "fill_solution", None)
        try:
            if callable(fn):
                fn()
        except Exception:  # noqa: BLE001
            pass

    def _refresh_databases(self):
        db = getattr(self.win, "databases", None)
        f = ci.database_file(self.folder()) if self.folder() is not None else None
        try:
            if db is not None and f is not None and f.is_file():
                db.add_sqlite(f, self.project, name=f"{self.project.name} (SQLite)")
            elif db is not None:
                db.refresh()
        except Exception as e:  # noqa: BLE001
            self.win.log(f"[codeigniter] databases: {e}")

    def show_database(self):
        self._refresh_databases()
        dock = getattr(self.win, "dock_databases", None)
        if dock is not None:
            dock.show()
            dock.raise_()

    def composer(self, args: list[str], on_done=None):
        rc = getattr(self.win, "run_composer", None)
        if not callable(rc) or self.project is None:
            self.win.log("*** Composer support is not available")
            return None
        proc = rc(args, self.project)
        if proc is not None:
            proc.finished.connect(lambda code, _s: (self.refresh(force=True), on_done and on_done(code)))
        return proc

    def open_rel(self, rel: str):
        if self.folder() is not None:
            open_location(self.win, self.folder() / rel, 1)


# ---------------------------------------------------------------- opening a site
def site_opened(win, project) -> None:
    """A CodeIgniter site was opened: dependencies, .env, database connection, panel."""
    try:
        if project is None or not ci.is_ci_project(project.folder):
            return
    except Exception:  # noqa: BLE001
        return
    root = Path(project.folder).resolve()
    panel = getattr(win, "codeigniter", None)
    if ci.ensure_env(root):
        win.log(f"[codeigniter] .env created from the template ({project.name})")
    if not (root / "vendor" / "autoload.php").is_file():
        win.log(f"[codeigniter] {project.name}: vendor/ is missing - run Tools > Composer > Install "
                "(or the CodeIgniter panel > More > composer install).")
        if _offscreen() or getattr(win, "_ci_asked", {}).get(str(root)):
            return
        win.__dict__.setdefault("_ci_asked", {})[str(root)] = True
        if QMessageBox.question(win, "CodeIgniter", f"'{project.name}' needs its Composer packages (vendor/).\n\n"
                                "Run 'composer install' now?") == QMessageBox.StandardButton.Yes:
            if panel is not None:
                panel.project = project
                panel.composer(["install"], on_done=lambda code: code == 0 and first_run_setup(win, project))
            elif callable(getattr(win, "run_composer", None)):
                proc = win.run_composer(["install"], project)
                if proc is not None:
                    proc.finished.connect(lambda code, _s: code == 0 and first_run_setup(win, project))
        return
    db = ci.database_file(root)
    if db is not None and db.is_file() and getattr(win, "databases", None) is not None:
        try:
            win.databases.add_sqlite(db, project, name=f"{project.name} (SQLite)")
        except Exception:  # noqa: BLE001
            pass


def first_run_setup(win, project) -> None:
    """After composer install: offer migrate + seed when the SQLite database does not exist yet."""
    root = Path(project.folder).resolve()
    db = ci.database_file(root)
    panel = getattr(win, "codeigniter", None)
    if panel is None or db is None or db.is_file():
        return
    has_mig = any((root / "app" / "Database" / "Migrations").glob("*.php"))
    if not has_mig:
        return
    if QMessageBox.question(win, "CodeIgniter", "Create the database now?\n\nphp spark migrate --all, then "
                            "php spark db:seed DatabaseSeeder") != QMessageBox.StandardButton.Yes:
        return
    panel.project = project
    seed = (root / "app" / "Database" / "Seeds" / "DatabaseSeeder.php").is_file()
    panel.run_spark(["migrate", "--all"],
                    on_done=lambda code, _o: code == 0 and seed and panel.run_spark(["db:seed", "DatabaseSeeder"]))


# ---------------------------------------------------------------- New Project template
class DatabaseChoice(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CodeIgniter 4 App - database")
        lay = QFormLayout(self)
        self.box = QComboBox()
        self.box.addItem("SQLite3 (writable/database.db) - no server needed", "sqlite")
        self.box.addItem("MariaDB / MySQL - the IDE's local server", "mysql")
        self.box.addItem("PostgreSQL - the IDE's local server", "postgresql")
        lay.addRow("Database:", self.box)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addRow(bb)


def _db_connection(kind: str, log) -> dict | None:
    """Start the IDE's local MariaDB / PostgreSQL server and return its login for .env (None = failed)."""
    try:
        from ..web_site.dbservers import servers
        srv = servers(log=log)[kind]
        if not srv.available:
            log(f"*** {srv.title} is not installed ({srv.install_hint}) - using SQLite instead")
            return None
        info = srv.start()
        return {"host": info.host, "port": info.port, "user": info.user, "database": info.database,
                "password": srv.password()}
    except Exception as e:  # noqa: BLE001
        log(f"*** local database server: {e} - using SQLite instead")
        return None


def create_site(folder: Path, name: str) -> dict:
    """SiteTemplate.create for "CodeIgniter 4 App" (New Project dialog)."""
    db = os.environ.get("RADIDE_CI_DB", "")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    interactive = isinstance(app, QApplication) and not _offscreen() and os.environ.get("RADIDE_CI_NO_UI") != "1"
    if not db:
        db = "sqlite"
        if interactive:
            dlg = DatabaseChoice(QApplication.activeWindow())
            if dlg.exec():
                db = dlg.box.currentData()

    def work(log):
        conn = None
        kind = db
        if db in ("mysql", "postgresql"):
            conn = _db_connection(db, log)
            if conn is None:
                kind = "sqlite"
        from ..web_site import php_toolchain as tc
        php = tc.resolve("8.4") or tc.resolve("auto")
        return ci.create_project(folder, name, kind, log=log, php=php, conn=conn)
    if interactive:
        from .app_gallery import run_with_progress
        return run_with_progress(QApplication.activeWindow(), "Creating CodeIgniter 4 App", work)
    return work(lambda s: print(s, flush=True))


def register_template() -> None:
    try:
        from ..web_site.project import SiteTemplate, register_template as reg
    except Exception:  # noqa: BLE001
        return
    reg(SiteTemplate("codeigniter4", "CodeIgniter 4 App",
                     "CodeIgniter 4 (latest stable) via 'composer create-project codeigniter4/appstarter': web root "
                     "public/, .env for development, SQLite3 database (or the local MariaDB / PostgreSQL), Spark "
                     "panel, routes, IntelliSense for views / routes / lang / config / models. Needs internet.",
                     ("php-web",), create_site, order=75, icon="SP_ComputerIcon",
                     extra={"category": "Applications", "needs": ["php", "composer", "internet"], "heavy": True,
                            "framework": "codeigniter", "root": "public"}))


# ---------------------------------------------------------------- install
def install(win) -> None:
    try:
        from ..monaco_editor import MonacoEditor
        # normally features/php_frameworks.py serves Monaco for every PHP framework (complete_items() merged
        # with intelephense + its F12 action); this module's own provider is only the fallback without it
        import importlib.util
        shared = importlib.util.find_spec(f"{__package__}.php_frameworks") is not None and \
            hasattr(MonacoEditor, "completion_providers") and os.environ.get("RADIDE_CI_OWN_PROVIDER") != "1"
        if not shared:
            MonacoEditor.channel_objects["radCI"] = EditorBridge
            if on_editor_ready not in MonacoEditor.ready_hooks:
                MonacoEditor.ready_hooks.append(on_editor_ready)
    except ImportError:                       # no QtWebEngine: the built-in editor
        pass
    register_template()
    try:
        from .. import icons
        icons.TEMPLATE_BADGES.setdefault("codeigniter4", ("CI", "#DD4814"))
    except Exception:  # noqa: BLE001
        pass
    panel = CodeIgniterPanel(win)
    win.codeigniter = panel
    d = QDockWidget("CodeIgniter", win)
    d.setObjectName("CodeIgniterPanel")
    d.setWidget(panel)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, d)
    try:
        win.tabifyDockWidget(win.dock_output, d)
    except Exception:  # noqa: BLE001
        pass
    d.hide()
    win.dock_codeigniter = d
    d.visibilityChanged.connect(lambda vis: vis and panel.sync_project())
    act = d.toggleViewAction()
    act.setText("CodeIgniter Panel (Spark, Routes)")
    win.a_codeigniter = act
    try:
        from .workbench import register_view
        # (return the dock itself: a bare widget would be moved into a second "wb.view.*" dock)
        register_view("codeigniter", "CodeIgniter", factory=lambda w: w.dock_codeigniter, area="panel", order=83,
                      tooltip="CodeIgniter 4: Spark commands, routes")
    except Exception:  # noqa: BLE001 - the VS Code layout is optional
        pass
    try:
        from . import command_palette as cp

        def show(tab: int = 0, cmd: str = ""):
            d.show()
            d.raise_()
            panel.sync_project(force=True)
            panel.tabs.setCurrentIndex(tab)
            if cmd:
                panel.open_form(cmd)

        def active() -> bool:            # only while a CodeIgniter project is open (project_actions detection)
            try:
                return any(p.id == "codeigniter" for p in win.project_menus.providers())
            except Exception:  # noqa: BLE001
                return True
        cp.register_command("codeigniter.spark", "CodeIgniter: Spark Commands", lambda: show(0),
                            category="CodeIgniter", enabled=active)
        cp.register_command("codeigniter.routes", "CodeIgniter: Show Routes", lambda: show(1), category="CodeIgniter",
                            enabled=active)
        for cmd in ("make:controller", "make:model", "make:migration", "migrate", "db:seed"):
            cp.register_command(f"codeigniter.{cmd}", f"CodeIgniter: spark {cmd}...",
                                lambda c=cmd: show(0, c), category="CodeIgniter", enabled=active)
    except Exception:  # noqa: BLE001 - the palette is optional
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
            sig.siteOpened.connect(lambda p: QTimer.singleShot(0, lambda: site_opened(win, p)))
    QTimer.singleShot(0, later)
    timer = QTimer(win)
    timer.setInterval(1500)
    timer.timeout.connect(lambda: d.isVisible() and panel.sync_project())
    timer.start()
    win._codeigniter_timer = timer
    win.codeigniter_spark = lambda args, on_done=None: panel.run_spark(list(args), on_done)


__all__ = ["CodeIgniterPanel", "EditorBridge", "SparkForm", "create_site", "created_file", "install",
           "site_opened"]
