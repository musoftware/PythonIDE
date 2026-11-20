"""Framework tools for ASP.NET Core, Spring Boot, Ruby on Rails / Sinatra and NestJS web sites
(radide/web_site/frameworks/aspnet.py, spring.py, rails.py, nestjs.py).

- **Framework** dock (View > Framework Tools, Site > Framework Tools; a Panel view in the VS Code layout):
  *Routes* (method, path, handler, file:line - double-click opens the code, right-click opens a GET route in the
  Preview), *CLI* (dotnet ef / mvnw / rails g / nest g presets with a Name box, any command line, output, Stop),
  *Tools* (what is installed: SDK, debugger, language server, DevKit ... with Install buttons).
- **IntelliSense** inside strings: view / action / controller / page / route names from the framework
  (``View("``, ``asp-action="``, ``return "`` in a Spring controller, ``th:href="@{``, ``render "``, ``redirect_to``
  ``*_path``, ``fetch('`` ...) - Ctrl+Space; everything else goes to the normal completion (LSP).
- .razor / .erb files open in Monaco as Razor / HTML; csharp-ls installed by the Tools tab is given to the C# LSP.
- Spring Boot: saving a .java file while the site runs compiles it (``mvnw -o compile``) so devtools restarts.
"""
from __future__ import annotations

import json
import os
import threading
import weakref
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QApplication, QComboBox, QDockWidget, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMenu, QPlainTextEdit, QPushButton, QTabWidget, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

from .. import theme

_WIN = None          # weakref to the main window (for the completion hook)


def framework_plugin(project):
    """The FrameworkPlugin of a project, or None."""
    if project is None:
        return None
    try:
        from ..languages import get_plugin
        from ..web_site.frameworks.backend_common import FrameworkPlugin
        p = get_plugin(project.language)
    except Exception:  # noqa: BLE001
        return None
    return p if isinstance(p, FrameworkPlugin) else None


def _site_project(win):
    try:
        from .web_workspace import _site_project
        return _site_project(win)
    except Exception:  # noqa: BLE001
        return getattr(win, "project", None)


class _Signals(QObject):
    routes = pyqtSignal(object, object)       # (project folder, list[Route] | Exception)
    tool_log = pyqtSignal(str)
    tool_done = pyqtSignal(str, bool)


# ============================================================================ panel
class FrameworkPanel(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.project = None
        self.plugin = None
        self.sig = _Signals(self)
        self.sig.routes.connect(self._routes_ready)
        self.sig.tool_log.connect(lambda t: self._append(t))
        self.sig.tool_done.connect(self._tool_done)
        self.routes: list = []
        self.proc: QProcess | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        top = QHBoxLayout()
        self.title = QLabel("No framework web site is open")
        f = self.title.font()
        f.setBold(True)
        self.title.setFont(f)
        top.addWidget(self.title, 1)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        top.addWidget(self.refresh_btn)
        lay.addLayout(top)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        # --- routes
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 4, 0, 0)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter routes (path, method, handler)")
        self.filter.textChanged.connect(self._apply_filter)
        v.addWidget(self.filter)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Method", "Path", "Handler", "Location"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.itemDoubleClicked.connect(lambda it, _c: self._open_route(it))
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._route_menu)
        v.addWidget(self.tree, 1)
        self.route_info = QLabel("")
        theme.role(self.route_info, "muted")
        v.addWidget(self.route_info)
        self.tabs.addTab(w, "Routes")
        # --- CLI
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 4, 0, 0)
        row = QHBoxLayout()
        self.preset = QComboBox()
        self.preset.setMinimumWidth(220)
        self.preset.currentIndexChanged.connect(self._preset_changed)
        row.addWidget(self.preset, 1)
        row.addWidget(QLabel("Name:"))
        self.name = QLineEdit()
        self.name.setPlaceholderText("{name}")
        self.name.setMaximumWidth(200)
        self.name.textChanged.connect(lambda _t: self._preset_changed())
        row.addWidget(self.name)
        v.addLayout(row)
        row = QHBoxLayout()
        self.command = QLineEdit()
        self.command.setPlaceholderText("command line, e.g. dotnet ef migrations add Initial")
        self.command.returnPressed.connect(self.run_command)
        row.addWidget(self.command, 1)
        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self.run_command)
        row.addWidget(self.run_btn)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_command)
        row.addWidget(self.stop_btn)
        v.addLayout(row)
        self.out = QPlainTextEdit()
        self.out.setReadOnly(True)
        self.out.setFont(QFont("Consolas", 9))
        self.out.setMaximumBlockCount(5000)
        v.addWidget(self.out, 1)
        self.tabs.addTab(w, "CLI")
        # --- tools
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 4, 0, 0)
        self.tools = QTreeWidget()
        self.tools.setHeaderLabels(["Tool", "Status", "Used for", ""])
        self.tools.setRootIsDecorated(False)
        self.tools.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        v.addWidget(self.tools, 1)
        self.tools_info = QLabel("Tools are installed per user under %LOCALAPPDATA%\\RADIDE (no admin rights).")
        theme.role(self.tools_info, "muted")
        self.tools_info.setWordWrap(True)
        v.addWidget(self.tools_info)
        self.tabs.addTab(w, "Tools")
        self._busy_tool = ""

    # ------------------------------------------------------------ project
    def set_project(self, project, force: bool = False) -> None:
        plugin = framework_plugin(project)
        if not force and project is self.project and plugin is self.plugin:
            return
        self.project, self.plugin = (project, plugin) if plugin is not None else (None, None)
        self.preset.blockSignals(True)
        self.preset.clear()
        if self.plugin is None:
            self.title.setText("No framework web site is open (ASP.NET Core, Spring Boot, Rails, NestJS)")
            self.tree.clear()
            self.tools.clear()
            self.preset.blockSignals(False)
            return
        self.title.setText(f"{self.plugin.framework_title} - {project.name}")
        self.preset.addItem("(choose a command)", "")
        for label, cmd in self.plugin.cli_presets(project):
            self.preset.addItem(label, cmd)
        self.preset.blockSignals(False)
        self.tabs.setTabText(1, self.plugin.cli_title)
        self.refresh()

    def refresh(self) -> None:
        if self.plugin is None:
            return
        self.route_info.setText("Reading routes...")
        project, plugin = self.project, self.plugin
        folder = str(project.folder)

        def work():
            try:
                res = plugin.routes(project)
            except Exception as e:  # noqa: BLE001
                res = e
            try:
                self.sig.routes.emit(folder, res)
            except RuntimeError:
                pass
        threading.Thread(target=work, daemon=True, name="radide-routes").start()
        self._fill_tools()

    def _routes_ready(self, folder, res) -> None:
        if self.project is None or str(self.project.folder) != folder:
            return
        if isinstance(res, Exception):
            self.route_info.setText(f"Cannot read the routes: {res}")
            return
        self.routes = res
        self.tree.clear()
        base = Path(folder)
        for r in res:
            loc = ""
            if r.file:
                try:
                    loc = Path(r.file).resolve().relative_to(base.resolve()).as_posix()
                except ValueError:
                    loc = Path(r.file).name
                loc += f":{r.line}" if r.line else ""
            it = QTreeWidgetItem([r.method, r.path, r.handler, loc])
            it.setData(0, Qt.ItemDataRole.UserRole, r)
            it.setToolTip(1, r.path + (f"   ({r.name})" if r.name else ""))
            self.tree.addTopLevelItem(it)
        for c in (0, 2, 3):
            self.tree.resizeColumnToContents(c)
        self.route_info.setText(f"{len(res)} route(s)")
        self._apply_filter()

    def _apply_filter(self) -> None:
        q = self.filter.text().strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            it.setHidden(bool(q) and not any(q in it.text(c).lower() for c in range(4)))

    def _open_route(self, it) -> None:
        r = it.data(0, Qt.ItemDataRole.UserRole) if it is not None else None
        if r is None or not r.file:
            return
        opener = getattr(self.win, "open_file", None)
        if callable(opener):
            opener(r.file, r.line or None)

    def _preview_route(self, r) -> None:
        srv = getattr(self.win, "web_server", None)
        if srv is None or not srv.running:
            run = getattr(self.win, "run_website", None)
            srv = run(self.project, open_preview=False) if callable(run) else None
        if srv is not None:
            self.win.web_preview.open_url(srv.url.rstrip("/") + r.url_path())

    def _route_menu(self, pos) -> None:
        it = self.tree.itemAt(pos)
        r = it.data(0, Qt.ItemDataRole.UserRole) if it is not None else None
        if r is None:
            return
        m = QMenu(self)
        if r.file:
            m.addAction("Go to Code", lambda: self._open_route(it))
        if r.method in ("GET", "ANY"):
            m.addAction("Open in Preview", lambda: self._preview_route(r))
        m.addAction("Copy Path", lambda: QApplication.clipboard().setText(r.path))
        m.exec(self.tree.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------ CLI
    def _preset_changed(self, *_):
        cmd = self.preset.currentData() or ""
        if cmd:
            self.command.setText(cmd.replace("{name}", self.name.text().strip() or "{name}"))

    def _append(self, text: str) -> None:
        self.out.appendPlainText(text.rstrip("\n"))

    def run_command(self, command: str | None = None) -> bool:
        """Run a CLI command in the project folder (output in the panel). Returns False when it cannot start."""
        if self.plugin is None or self.project is None:
            return False
        cmd = (command if isinstance(command, str) else self.command.text()).strip()
        if not cmd or "{name}" in cmd:
            self._append("*** fill in the Name box first" if "{name}" in cmd else "*** type a command")
            return False
        if self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning:
            self._append("*** a command is still running")
            return False
        self.tabs.setCurrentIndex(1)
        self._append(f"> {cmd}")
        try:
            if self.plugin.cli_internal(self.project, cmd, self._append):
                self.refresh()
                return True
        except Exception as e:  # noqa: BLE001
            self._append(f"*** {e}")
            return False
        argv = self.plugin.cli_argv(self.project, cmd)
        if not argv:
            return False
        p = QProcess(self)
        p.setWorkingDirectory(str(self.project.folder))
        env = QProcessEnvironment.systemEnvironment()
        for k, v in (self.plugin.cli_env(self.project) or {}).items():
            env.insert(k, str(v))
        p.setProcessEnvironment(env)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(lambda: self._append(
            bytes(p.readAllStandardOutput()).decode("utf-8", "replace")))
        p.finished.connect(lambda code, _s: self._finished(code))
        p.errorOccurred.connect(lambda err: err == QProcess.ProcessError.FailedToStart and
                                self._append(f"*** cannot start {argv[0]}") and self._finished(-1))
        self.proc = p
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        p.start(argv[0], argv[1:])
        return True

    def _finished(self, code: int) -> None:
        self._append(f"--- exited with code {code}")
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.refresh()                       # generators add routes / views
        try:
            from .web_workspace import _refresh
            _refresh(self.win)               # Solution Explorer shows the new files
        except Exception:  # noqa: BLE001
            pass

    def stop_command(self) -> None:
        p = self.proc
        if p is not None and p.state() != QProcess.ProcessState.NotRunning:
            try:
                import subprocess
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.processId())], capture_output=True,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except OSError:
                p.kill()

    def wait_command(self, ms: int = 600000) -> bool:
        p = self.proc
        return p is None or p.waitForFinished(ms)

    # ------------------------------------------------------------ tools
    def _fill_tools(self) -> None:
        self.tools.clear()
        if self.plugin is None:
            return
        ok, bad = theme.color("success"), theme.color("error")
        from PyQt6.QtGui import QColor
        for t in self.plugin.tool_status():
            it = QTreeWidgetItem([t.name, t.path or f"not installed - {t.hint}", t.purpose, ""])
            it.setForeground(1, QColor(ok if t.path else bad))
            it.setToolTip(1, t.path or t.hint)
            self.tools.addTopLevelItem(it)
            if t.installer and not t.path:
                b = QPushButton("Install" if self._busy_tool != t.installer else "Installing...")
                b.setEnabled(not self._busy_tool)
                b.clicked.connect(lambda _c=False, tid=t.installer: self.install_tool(tid))
                self.tools.setItemWidget(it, 3, b)
        for c in (0, 2):
            self.tools.resizeColumnToContents(c)

    def install_tool(self, tool_id: str) -> None:
        if self.plugin is None or self._busy_tool:
            return
        self._busy_tool = tool_id
        self._fill_tools()
        self.tabs.setCurrentIndex(1)
        self._append(f"> install {tool_id}")
        plugin = self.plugin

        def work():
            try:
                ok = plugin.install_tool(tool_id, lambda t: self.sig.tool_log.emit(t))
            except Exception as e:  # noqa: BLE001
                self.sig.tool_log.emit(f"*** {e}")
                ok = False
            self.sig.tool_done.emit(tool_id, bool(ok))
        threading.Thread(target=work, daemon=True, name="radide-install-tool").start()

    def _tool_done(self, tool_id: str, ok: bool) -> None:
        self._busy_tool = ""
        self._append(f"--- {tool_id}: {'installed' if ok else 'FAILED'}")
        if ok:
            register_language_servers()
        self._fill_tools()


# ============================================================================ completion hook
def _framework_completions(editor, line: int, col: int):
    win = _WIN() if _WIN is not None else None
    path = getattr(editor, "path", None)
    if win is None or not path:
        return None
    try:
        from .web_workspace import project_of_path
        project = project_of_path(win, path)
    except Exception:  # noqa: BLE001
        project = None
    plugin = framework_plugin(project)
    if plugin is None:
        return None
    lines = (getattr(editor, "_text", "") or "").split("\n")
    if line >= len(lines):
        return None
    before = lines[line][:col]
    items = plugin.completion_items(project, Path(path), before)
    if items is None:
        return None
    from ..monaco_editor import KIND
    from ..web_site.frameworks.backend_common import string_context
    ctx = string_context(before)
    typed = ctx[1] if ctx is not None else ""
    if ctx is None:
        import re
        m = re.search(r"[\w:]*$", before)
        typed = m.group(0) if m else ""
        typed = typed.lstrip(":")
    out = []
    for label, kind, detail in items[:300]:
        out.append({"label": label, "kind": KIND.get(kind, 18 if kind == "file" else 12), "detail": detail,
                    "insertText": label, "filterText": label, "range": [line, col - len(typed), line, col],
                    "sortText": "0" + label})
    return out


def install_completion_hook() -> None:
    from .. import monaco_editor as me
    if getattr(me.MonacoEditor._complete, "_radide_frameworks", False):
        return
    orig = me.MonacoEditor._complete

    def _complete(self, req, line, col):
        try:
            items = _framework_completions(self, line, col)
        except Exception:  # noqa: BLE001 - completion must never break typing
            items = None
        if items is not None:
            self._js(f"radResolve({req}, {json.dumps(items)});")
            return
        return orig(self, req, line, col)
    _complete._radide_frameworks = True
    me.MonacoEditor._complete = _complete


def register_language_servers() -> None:
    """csharp-ls installed by the Tools tab (tools\\csharp-ls) is used for C# files."""
    try:
        from .. import lsp
        from ..web_site.frameworks.aspnet import CSHARP_LS_DIR
        exe = CSHARP_LS_DIR / "csharp-ls.exe"
        cands = lsp.SERVERS.get("csharp", ([], ""))[0]
        if exe.exists() and not any(c and c[0] == str(exe) for c in cands):
            cands.insert(0, [str(exe)])
    except Exception:  # noqa: BLE001
        pass


def _monaco_languages() -> None:
    try:
        from .. import monaco_editor as me
        for ext, lang in ((".razor", "razor"), (".erb", "html"), (".rhtml", "html"), (".cshtml", "razor")):
            me.MONACO_LANG.setdefault(ext, lang)
    except Exception:  # noqa: BLE001
        pass


# ============================================================================ Spring / Sinatra: after a save
class _SpringCompiler(QObject):
    """Spring: compile saved .java files (devtools restarts); Sinatra: restart after a .rb change."""
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.stamp: dict[str, float] = {}
        self.proc: QProcess | None = None

    def _java_mtime(self, folder: Path) -> float:
        best = 0.0
        for dirpath, _dirs, files in os.walk(folder / "src" / "main" / "java"):
            for f in files:
                if f.endswith((".java", ".kt")):
                    try:
                        best = max(best, os.stat(os.path.join(dirpath, f)).st_mtime)
                    except OSError:
                        pass
        return best

    @staticmethod
    def _ruby_mtime(folder: Path) -> float:
        best = 0.0
        for dirpath, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d not in ("vendor", "public", "views", "tmp", "log", ".bundle", ".git")]
            for f in files:
                if f.endswith(".rb"):
                    try:
                        best = max(best, os.stat(os.path.join(dirpath, f)).st_mtime)
                    except OSError:
                        pass
        return best

    def check(self) -> None:
        srv = getattr(self.win, "web_server", None)
        project = getattr(srv, "project", None) if srv is not None else None
        plugin = framework_plugin(project)
        if plugin is None or not srv.running:
            return
        folder = Path(project.folder)
        key = str(folder)
        if plugin.framework == "rails" and plugin.kind_of(project) == "sinatra":
            m = self._ruby_mtime(folder)            # Sinatra does not reload code: restart its server
            old = self.stamp.setdefault(key, m)
            if m > old and srv.is_ready():
                self.stamp[key] = m
                self.win.log("[sinatra] .rb saved - restarting the server")
                srv.restart_backend()
            return
        if plugin.framework != "spring":
            return
        m = self._java_mtime(folder)
        if key not in self.stamp:
            self.stamp[key] = m
            return
        if m <= self.stamp[key] or (self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning):
            return
        self.stamp[key] = m
        argv = plugin.compile_argv(folder)
        p = QProcess(self)
        p.setWorkingDirectory(key)
        env = QProcessEnvironment.systemEnvironment()
        for k, v in plugin.env().items():
            env.insert(k, v)
        p.setProcessEnvironment(env)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(lambda: self.win.log(
            "[spring] " + bytes(p.readAllStandardOutput()).decode("utf-8", "replace").rstrip()))
        p.finished.connect(lambda code, _s: self.win.log(f"[spring] compile finished ({code}) - devtools restarts the "
                                                         "application" if code == 0 else
                                                         f"[spring] compile failed ({code})"))
        self.proc = p
        self.win.log("[spring] .java saved - compiling (mvnw -o compile)...")
        p.start(argv[0], argv[1:])


# ============================================================================ install
def install(win) -> None:
    global _WIN
    _WIN = weakref.ref(win)
    _monaco_languages()
    register_language_servers()
    install_completion_hook()
    panel = FrameworkPanel(win)
    win.framework_panel = panel
    d = QDockWidget("Framework", win)
    d.setObjectName("FrameworkTools")
    d.setWidget(panel)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, d)
    dock_output = getattr(win, "dock_output", None)
    if dock_output is not None:
        win.tabifyDockWidget(dock_output, d)
        dock_output.raise_()
    d.hide()
    win.dock_framework = d
    toggle = d.toggleViewAction()
    toggle.setText("Framework Tools")

    def show(tab: int = 0):
        panel.set_project(_site_project(win), force=True)
        d.show()
        d.raise_()
        panel.tabs.setCurrentIndex(tab)
    win.show_framework_tools = show
    # menus: View > Framework Tools, Site > Framework Tools (Routes / CLI / Tools)
    for title in ("View",):
        a = next((x for x in win.menuBar().actions() if x.text().replace("&", "") == title), None)
        if a is not None and a.menu() is not None:
            a.menu().addAction(toggle)
    site = getattr(win, "site_menu", None)
    if site is not None:
        sub = site.addMenu("Framework Tools")
        sub.addAction("Routes", lambda: show(0))
        sub.addAction("CLI / Generators", lambda: show(1))
        sub.addAction("Tools (SDK, debugger, IntelliSense)", lambda: show(2))
        site.aboutToShow.connect(lambda: sub.setEnabled(framework_plugin(_site_project(win)) is not None))
    try:
        from . import workbench
        workbench.register_view("framework", "Framework", icon="globe", factory=lambda w: w.dock_framework,
                                modes=("vscode", "agent"), area="panel", order=60,
                                tooltip="Routes, CLI and tools of ASP.NET Core / Spring / Rails / NestJS sites")
    except Exception:  # noqa: BLE001 - the VS Code layout is optional
        pass
    # follow the active project; show the dock the first time a framework site is opened
    state = {"seen": set()}
    compiler = _SpringCompiler(win)
    win._spring_compiler = compiler

    def poll():
        project = _site_project(win)
        plugin = framework_plugin(project)
        if plugin is not None:
            panel.set_project(project)
            key = str(project.folder)
            if key not in state["seen"]:
                state["seen"].add(key)
                if not d.isVisible() and os.environ.get("QT_QPA_PLATFORM") != "offscreen":
                    d.show()
                    if dock_output is not None:
                        dock_output.raise_()
        elif panel.project is not None:
            panel.set_project(None)
        compiler.check()
    t = QTimer(win)
    t.timeout.connect(poll)
    t.start(1500)
    win._framework_timer = t
