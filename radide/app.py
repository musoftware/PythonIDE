"""Main IDE window: menus, toolbar, docks (Toolbox, Solution Explorer,
Properties, Output, Locals, Call Stack, Immediate), designer/code tabs,
run and debug."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QSettings, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QKeySequence
from PyQt6.QtWidgets import (QApplication, QDockWidget, QFileDialog, QInputDialog, QLabel,
                             QLineEdit, QListWidget, QMainWindow, QMenu, QMessageBox, QPlainTextEdit,
                             QPushButton, QStyle, QTabWidget, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

from .controls import event_args
from .debugger import Session, StopInfo
from .designer import DesignerView
from .dialogs import AddItemDialog, NewProjectDialog
from .document import FormDocument
from .editor import CodeView
from .languages import code_extensions, get_plugin, language_label
from .languages import plugin_for_form as _form_plugin
from .languages import plugin_for_module as _module_plugin
from .model import Form, Project
from .properties import PropertiesPanel, valid_identifier
from .solution import EXT as SOLUTION_EXT
from .solution import Solution
from .toolbox import TOOL_STATE, Toolbox
from .workspace import add_module, create_form, delete_form, delete_module, rename_form

APP_NAME = "RAD IDE"


def ide_settings() -> QSettings:
    """The IDE's settings. Tests set QCoreApplication.setOrganizationName("RADIDE-TEST...")
    before creating the window so that they never touch the user's real "RADIDE" settings."""
    org = QCoreApplication.organizationName()
    if org.upper().startswith("RADIDE-TEST"):
        return QSettings(org, QCoreApplication.applicationName() or org)
    return QSettings("RADIDE", "RADIDE")

STYLE = """
QMainWindow, QDockWidget { background: #F0F0EA; }
QDockWidget::title { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #F6F7F9, stop:1 #D8DFEA);
                     padding: 4px; border: 1px solid #A0AFC3; font-weight: bold; }
QTabBar::tab:selected { background: #ffffff; }
QToolBar { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #FAFAFA, stop:1 #E3E3DC);
           border-bottom: 1px solid #C0C0B8; spacing: 2px; }
"""


_REAL_PY: dict[str, str] = {}


def real_python(exe: str) -> str:
    """The real python.exe behind a Windows Store / App Execution Alias (WindowsApps) or py launcher:
    debuggers and launchers cannot start the alias itself."""
    if exe in _REAL_PY:
        return _REAL_PY[exe]
    real = exe
    low = exe.lower()
    if "windowsapps" in low or Path(low).name in ("py.exe", "py"):
        import subprocess
        try:
            out = subprocess.run([exe, "-c", "import sys; print(sys.executable)"], capture_output=True,
                                 text=True, timeout=20).stdout.strip()
            if out and Path(out).exists() and "windowsapps" not in out.lower():
                real = out
        except (OSError, subprocess.TimeoutExpired):
            pass
    _REAL_PY[exe] = real
    return real


def bring_to_front(win) -> None:
    """Raise the IDE above the paused program (Windows blocks plain
    activateWindow from background processes), and flash the taskbar."""
    if win.isMinimized():
        win.showNormal()
    win.raise_()
    win.activateWindow()
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # a synthetic Alt press lets SetForegroundWindow pass Windows'
            # focus-stealing guard without attaching to the (paused) program
            VK_MENU, KEYUP = 0x12, 0x0002
            user32.keybd_event(VK_MENU, 0, 0, 0)
            user32.keybd_event(VK_MENU, 0, KEYUP, 0)
            user32.SetForegroundWindow(int(win.winId()))
        except Exception:  # noqa: BLE001 - best effort
            pass
    QApplication.alert(win, 3000)


class StartPage(QWidget):
    def __init__(self, win: "MainWindow"):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 30, 40, 30)
        title = QLabel(f"<h1>{APP_NAME}</h1>")
        title.setProperty("radRole", "heading")
        lay.addWidget(title)
        lay.addWidget(QLabel("<p>Visual RAD environment for scripting languages</p>"))
        for text, slot in (("New Project...", win.new_project), ("Open Project...", win.open_project_dialog)):
            b = QPushButton(text)
            b.setMinimumHeight(30)
            b.clicked.connect(slot)
            lay.addWidget(b)
        lay.addWidget(QLabel("<h3>Recent Projects</h3>"))
        for folder in win.recent_projects():
            b = QPushButton(folder)
            b.setFlat(True)
            b.setProperty("radRole", "link")
            b.clicked.connect(lambda _=False, f=folder: win.open_project(Path(f)))
            lay.addWidget(b)
        lay.addStretch(1)


class ImmediateWindow(QWidget):
    def __init__(self, win: "MainWindow"):
        super().__init__()
        self.win = win
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 9))
        self.input = QLineEdit()
        self.input.setFont(QFont("Consolas", 9))
        self.input.setPlaceholderText("Type an expression and press Enter (while paused)")
        self.input.returnPressed.connect(self._run)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        lay.addWidget(self.log, 1)
        lay.addWidget(self.input)

    def _run(self):
        expr = self.input.text().strip()
        if not expr:
            return
        self.input.clear()
        self.log.appendPlainText(f"> {expr}")
        if self.win.session is None:
            self.log.appendPlainText("(no program is running)")
        else:
            self.win.session.evaluate(expr)

    def show_result(self, text: str):
        self.log.appendPlainText(text)


class ModuleView(QWidget):
    """Editor tab for a plain code module (no form)."""

    def __init__(self, plugin, path: Path):
        super().__init__()
        self.path = path
        from .editor import make_editor
        self.editor = make_editor(plugin, path)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.editor)


class MainWindow(QMainWindow):
    _hub_log = pyqtSignal(str)          # RAD Hub output (emitted from its threads)

    def __init__(self):
        super().__init__()
        self.hub = None                  # radide.runtimes.radhub.RadHub while a program runs
        self._hub_log.connect(self._append_output)
        self.settings = ide_settings()
        # A solution holds several projects; self.project / self.plugin (and docs, designers,
        # codeviews, modviews, breakpoints) always mean the *active* project - the one whose
        # document is focused. Each project keeps its own state in self._pstates.
        self.sln: Solution | None = None
        self._pstates: dict[str, dict] = {}
        self._active_key: str | None = None
        self.project: Project | None = None
        self.plugin = None
        self.docs: dict[str, FormDocument] = {}
        self.designers: dict[str, DesignerView] = {}
        self.codeviews: dict[str, CodeView] = {}
        self.modviews: dict[str, ModuleView] = {}        # module file -> view
        self.breakpoints: dict[str, set[int]] = {}      # code file name -> 0-based lines
        self.session: Session | None = None
        self.stopped_at: tuple[str, int] | None = None

        self.resize(1280, 800)
        self.setStyleSheet(STYLE)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.tabBar().customContextMenuRequested.connect(self._tab_menu)
        self.setCentralWidget(self.tabs)

        self._make_docks()
        self._make_actions()
        self.tabs.addTab(StartPage(self), "Start Page")
        self.statusBar().showMessage("Ready")
        self._update_title()
        self._update_actions()
        from .tools import install_tools
        install_tools(self)
        from .features import install_all
        install_all(self)

    # ================================================================ UI setup
    def _dock(self, title: str, widget, area) -> QDockWidget:
        d = QDockWidget(title, self)
        d.setObjectName(title)
        d.setWidget(widget)
        self.addDockWidget(area, d)
        return d

    def _make_docks(self):
        self.toolbox = Toolbox()
        self.solution = QTreeWidget()
        self.solution.setHeaderHidden(True)
        self.solution.itemDoubleClicked.connect(self._on_solution_dclick)
        self.solution.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.solution.customContextMenuRequested.connect(self._solution_menu)
        self.properties = PropertiesPanel()
        self.properties.code_provider = self._code_text
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 9))
        self.locals = QTreeWidget()
        self.locals.setHeaderLabels(["Name", "Value", "Type"])
        self.locals.setColumnWidth(0, 160)
        self.locals.setColumnWidth(1, 320)
        self.locals.setRootIsDecorated(False)
        self.callstack = QListWidget()
        self.callstack.itemDoubleClicked.connect(self._on_frame_dclick)
        self.immediate = ImmediateWindow(self)
        L, R, B = (Qt.DockWidgetArea.LeftDockWidgetArea, Qt.DockWidgetArea.RightDockWidgetArea,
                   Qt.DockWidgetArea.BottomDockWidgetArea)
        self.dock_toolbox = self._dock("Toolbox", self.toolbox, L)
        self.dock_solution = self._dock("Solution Explorer", self.solution, R)
        self.dock_props = self._dock("Properties", self.properties, R)
        self.dock_output = self._dock("Output", self.output, B)
        self.dock_locals = self._dock("Locals", self.locals, B)
        self.dock_stack = self._dock("Call Stack", self.callstack, B)
        self.dock_immediate = self._dock("Immediate", self.immediate, B)
        self.splitDockWidget(self.dock_solution, self.dock_props, Qt.Orientation.Vertical)
        self.tabifyDockWidget(self.dock_output, self.dock_locals)
        self.tabifyDockWidget(self.dock_locals, self.dock_stack)
        self.tabifyDockWidget(self.dock_stack, self.dock_immediate)
        self.dock_output.raise_()
        self.resizeDocks([self.dock_toolbox], [170], Qt.Orientation.Horizontal)
        self.resizeDocks([self.dock_solution, self.dock_props], [260, 300], Qt.Orientation.Horizontal)
        self.resizeDocks([self.dock_solution, self.dock_props], [330, 380], Qt.Orientation.Vertical)
        self.resizeDocks([self.dock_output], [170], Qt.Orientation.Vertical)

    def _act(self, text, slot, shortcut=None, icon=None) -> QAction:
        a = QAction(text, self)
        if icon is not None:
            a.setIcon(self.style().standardIcon(icon))
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.triggered.connect(slot)
        return a

    def _make_actions(self):
        SP = QStyle.StandardPixmap
        A = self._act
        self.a_new = A("&New Project...", self.new_project, "Ctrl+Shift+N", SP.SP_FileIcon)
        self.a_open = A("&Open Project...", self.open_project_dialog, "Ctrl+Shift+O", SP.SP_DirOpenIcon)
        self.a_save = A("Save &All", self.save_all, "Ctrl+S", SP.SP_DialogSaveButton)
        self.a_add_form = A("Add Windows &Form...", self.add_form)
        self.a_exit = A("E&xit", self.close)
        # edit
        self.a_undo = A("&Undo", self.edit_undo, "Ctrl+Z", SP.SP_ArrowBack)
        self.a_redo = A("&Redo", self.edit_redo, "Ctrl+Y", SP.SP_ArrowForward)
        self.a_cut = A("Cu&t", lambda: self._edit("cut"), "Ctrl+X")
        self.a_copy = A("&Copy", lambda: self._edit("copy"), "Ctrl+C")
        self.a_paste = A("&Paste", lambda: self._edit("paste"), "Ctrl+V")
        self.a_delete = A("&Delete", lambda: self._edit("delete"))
        self.a_select_all = A("Select A&ll", lambda: self._edit("select_all"), "Ctrl+A")
        # view
        self.a_code = A("&Code", self.view_code, "F7")
        self.a_design = A("&Designer", self.view_designer, "Shift+F7")
        # debug
        self.a_run = A("&Start Debugging / Continue", self.start_or_continue, "F5", SP.SP_MediaPlay)
        self.a_run_nodebug = A("Start &Without Debugging", lambda: self.run_project(debug=False), "Ctrl+F5")
        self.a_stop = A("Stop &Debugging", self.stop_project, "Shift+F5", SP.SP_MediaStop)
        self.a_step_into = A("Step &Into", lambda: self.session and self.session.step_into(), "F11")
        self.a_step_over = A("Step &Over", lambda: self.session and self.session.step_over(), "F10")
        self.a_step_out = A("Step O&ut", lambda: self.session and self.session.step_out(), "Shift+F11")
        self.a_bp = A("Toggle &Breakpoint", self.toggle_breakpoint, "F9")
        self.a_interp = A("&Interpreter Path...", self.choose_interpreter)
        for a in (self.a_cut, self.a_copy, self.a_paste, self.a_delete, self.a_select_all,
                  self.a_undo, self.a_redo):
            a.setShortcutContext(Qt.ShortcutContext.WindowShortcut)

        mb = self.menuBar()
        m = mb.addMenu("&File")
        for a in (self.a_new, self.a_open, None, self.a_save, None):
            m.addSeparator() if a is None else m.addAction(a)
        imp = m.addMenu("&Import")
        imp.addAction("Python GUI Program (Tkinter / Qt)...", self.import_python)
        imp.addAction("Visual Basic 6 Project (.vbp / .frm)...", self.import_vb6)
        m.addSeparator()
        m.addAction(self.a_exit)
        m = mb.addMenu("&Edit")
        for a in (self.a_undo, self.a_redo, None, self.a_cut, self.a_copy, self.a_paste,
                  self.a_delete, None, self.a_select_all):
            m.addSeparator() if a is None else m.addAction(a)
        m = mb.addMenu("&View")
        m.addActions([self.a_code, self.a_design])
        m.addSeparator()
        for d in (self.dock_toolbox, self.dock_solution, self.dock_props, self.dock_output,
                  self.dock_locals, self.dock_stack, self.dock_immediate):
            m.addAction(d.toggleViewAction())
        m = mb.addMenu("&Project")
        m.addAction(self.a_add_form)
        m.addAction("Add &Module...", self.add_module)
        m.addAction("Add &Existing Item...", self.add_existing)
        m.addSeparator()
        m.addAction("Open Project &Folder", self.open_folder)
        m.addAction("Project &Properties...", self.project_properties)
        self.format_menu = m = mb.addMenu("F&ormat")
        sub = m.addMenu("&Align")
        for text, mode in (("Lefts", "left"), ("Centers", "center_v"), ("Rights", "right"), (None, None),
                           ("Tops", "top"), ("Middles", "middle"), ("Bottoms", "bottom")):
            sub.addSeparator() if text is None else sub.addAction(text, lambda m_=mode: self._align(m_))
        sub = m.addMenu("&Make Same Size")
        for text, mode in (("Width", "same_width"), ("Height", "same_height"), ("Both", "same_size")):
            sub.addAction(text, lambda m_=mode: self._align(m_))
        sub = m.addMenu("&Center in Form")
        sub.addAction("Horizontally", lambda: self._align("center_form_h"))
        sub.addAction("Vertically", lambda: self._align("center_form_v"))
        m.addSeparator()
        m.addAction("Bring to &Front", lambda: self._order(True))
        m.addAction("Send to &Back", lambda: self._order(False))
        m = mb.addMenu("&Debug")
        for a in (self.a_run, self.a_run_nodebug, self.a_stop, None, self.a_step_into,
                  self.a_step_over, self.a_step_out, None, self.a_bp):
            m.addSeparator() if a is None else m.addAction(a)
        m = mb.addMenu("&Tools")
        m.addAction(self.a_interp)
        m = mb.addMenu("&Help")
        m.addAction(self._act("&About", lambda: QMessageBox.about(
            self, APP_NAME, f"{APP_NAME}\nA Visual Basic 2005 style IDE for scripting languages.")))

        tb = self.addToolBar("Standard")
        tb.setObjectName("Standard")
        tb.addActions([self.a_new, self.a_open, self.a_save])
        tb.addSeparator()
        tb.addActions([self.a_undo, self.a_redo])
        tb.addSeparator()
        tb.addActions([self.a_run, self.a_stop])
        tb2 = self.addToolBar("Debug")
        tb2.setObjectName("Debug")
        for a, text in ((self.a_step_into, "Step Into"), (self.a_step_over, "Step Over"),
                        (self.a_step_out, "Step Out"), (self.a_bp, "Breakpoint")):
            a.setIconText(text)
            tb2.addAction(a)

    # ================================================================ project
    def recent_projects(self) -> list[str]:
        """Recent solutions (.radsln files) and bare projects (folders), newest first."""
        items = self.settings.value("recent", []) or []
        if isinstance(items, str):
            items = [items]
        tmp = str(Path(os.environ.get("TEMP", "~"))).lower()

        def ok(p: str) -> bool:
            path = Path(p)
            if p.lower().startswith(tmp):
                return False
            if path.suffix.lower() == SOLUTION_EXT:
                return path.is_file()
            return (path / Project.FILE).exists()
        return [p for p in items if ok(p)][:8]

    def _remember(self, path: Path):
        items = [str(path)] + [p for p in self.recent_projects() if p.lower() != str(path).lower()]
        self.settings.setValue("recent", items[:8])

    def new_project(self):
        """File > New Project: create a project in a new solution or add it to the open one."""
        dlg = NewProjectDialog(self)
        if not dlg.exec():
            return None
        self._pending_template = None           # templates are applied here (also Class Library)
        from .features.solution_ui import create_project_from_dialog
        return create_project_from_dialog(self, dlg)

    def open_project_dialog(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Open Project/Solution", "",
            f"RAD IDE solution or project (*{SOLUTION_EXT} {Project.FILE});;All files (*)")
        if f:
            self.open_project(Path(f))

    def open_project(self, folder: Path, ask: bool = True, activate=None):
        """Open a solution (.radsln), a project (project.radproj) or a folder that holds one.
        A bare project opens as a one-project solution. *activate* = folder or name of the
        project to make active (default: the startup project)."""
        path = Path(folder).resolve()
        if ask and not self._confirm_close_project():
            return
        try:
            sln = Solution.open_any(path)
            projects = sln.all_projects()
            if not projects:
                raise ValueError(f"solution '{sln.name}' has no project that can be opened")
            for p in projects:
                get_plugin(p.language)
        except Exception as e:  # noqa: BLE001 - show any load error to the user
            QMessageBox.critical(self, APP_NAME, f"Cannot open project:\n{e}")
            return
        self.stop_project()
        self._reset()
        self.sln = sln
        for p in projects:
            self._state_for(p)
        target = None
        if activate is not None:
            target = sln.project(activate) if isinstance(activate, str) else sln.project_for_folder(Path(activate))
        if target is None and path.is_dir() and (path / Project.FILE).exists():
            target = sln.project_for_folder(path)          # the project the user asked for
        target = target or sln.startup_project() or projects[0]
        self.activate_project(target)
        self._remember(sln.file if sln.file is not None else Path(target.folder).resolve())
        self._fill_solution()
        project = self.project
        if project.forms:
            self.open_designer(project.startup if project.startup in project.forms else project.forms[0])
        elif project.modules:
            self.open_module(project.modules[0])
        self._update_title()
        self._update_actions()
        if len(projects) > 1 or not sln.implicit:
            self.log(f"Opened solution '{sln.name}' ({len(projects)} project{'s' if len(projects) != 1 else ''})")
        else:
            self.log(f"Opened project '{project.name}' ({self.plugin.display_name})")
        missing = [e.name for e in sln.projects if sln.project(e.name) is None]
        if missing:
            self.log(f"*** Projects that could not be loaded: {', '.join(missing)}")
        from .tools import offer_restore
        offer_restore(self)

    def _reset(self):
        self.properties.set_document(None, None)
        while self.tabs.count():
            w = self.tabs.widget(0)
            self.tabs.removeTab(0)
            w.deleteLater()
        self._pstates = {}
        self._active_key = None
        self.docs, self.designers, self.codeviews, self.modviews = {}, {}, {}, {}
        self.breakpoints = {}

    # ---------------------------------------------------------- solution: projects and the active one
    @staticmethod
    def _pkey(project) -> str:
        return os.path.normcase(str(Path(project.folder).resolve()))

    def _state_for(self, project) -> dict:
        key = self._pkey(project)
        st = self._pstates.get(key)
        if st is None:
            st = {"project": project, "plugin": get_plugin(project.language), "docs": {}, "designers": {},
                  "codeviews": {}, "modviews": {}, "breakpoints": None}
            self._pstates[key] = st
        return st

    def project_states(self) -> list[dict]:
        """State of every open project: {"project", "plugin", "docs", "designers", "codeviews", ...}."""
        return list(self._pstates.values())

    def projects(self) -> list[Project]:
        return [st["project"] for st in self._pstates.values()]

    def activate_project(self, project) -> bool:
        """Make *project* (a Project, or a project name of the solution) the active project:
        self.project, self.plugin, docs, designers, codeviews, modviews and breakpoints then
        belong to it. Returns False when it is not part of the open solution."""
        if isinstance(project, str):
            project = self.sln.project(project) if self.sln is not None else None
        if project is None:
            return False
        key = self._pkey(project)
        if key == self._active_key and self.project is not None:
            return True
        st = self._state_for(project)
        self._active_key = key
        self.project, self.plugin = st["project"], st["plugin"]
        self.docs, self.designers = st["docs"], st["designers"]
        self.codeviews, self.modviews = st["codeviews"], st["modviews"]
        if st["breakpoints"] is None:
            self._load_breakpoints()
            st["breakpoints"] = self.breakpoints
        else:
            self.breakpoints = st["breakpoints"]
        self._update_title()
        return True

    def project_of_widget(self, w) -> Project | None:
        key = w.property("radProject") if w is not None else None
        st = self._pstates.get(key) if key else None
        return st["project"] if st else None

    def startup_project(self) -> Project | None:
        return self.sln.startup_project() if self.sln is not None else self.project

    def _forget_project(self, project) -> None:
        """Close the tabs of a project and drop its state (Remove from solution)."""
        key = self._pkey(project)
        for i in reversed(range(self.tabs.count())):
            w = self.tabs.widget(i)
            if w.property("radProject") == key:
                self.tabs.removeTab(i)
                w.deleteLater()
        self._pstates.pop(key, None)
        if key == self._active_key:
            self._active_key, self.project = None, None
            nxt = self.startup_project()
            if nxt is not None and self._pkey(nxt) in self._pstates:
                self.activate_project(nxt)
            elif self._pstates:
                self.activate_project(next(iter(self._pstates.values()))["project"])
            else:
                self.plugin = None
                self.docs, self.designers, self.codeviews, self.modviews = {}, {}, {}, {}
                self.breakpoints = {}

    # ---------------------------------------------------------- languages (multi-language projects)
    def plugin_for_form(self, name: str):
        """Language plugin of a form (project.form_languages, else the project language)."""
        return _form_plugin(self.project, name) if self.project else self.plugin

    def plugin_for_file(self, filename: str):
        """Language plugin of a code file of the project (form code, designer or module)."""
        if not self.project:
            return self.plugin
        base = Path(filename).name.lower()
        for name in self.project.forms:
            fp = self.plugin_for_form(name)
            if base in (fp.code_file(name).lower(), fp.designer_file(name).lower()):
                return fp
        return _module_plugin(self.project, base)

    def run_plugin(self):
        """The startup form's plugin: it runs and debugs the program."""
        if not self.project:
            return self.plugin
        return self.plugin_for_form(self.project.startup) if self.project.startup else self.plugin

    def is_multi_language(self) -> bool:
        if not self.project:
            return False
        ids = {self.plugin_for_form(f).id for f in self.project.forms}
        ids |= {self.plugin_for_file(m).id for m in self.project.modules}
        return len(ids) > 1

    def _confirm_close_project(self) -> bool:
        if not self._any_modified():
            return True
        r = QMessageBox.question(self, APP_NAME, "Save changes to the current project?",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Cancel:
            return False
        if r == QMessageBox.StandardButton.Save:
            self.save_all()
        return True

    def _any_modified(self) -> bool:
        states = self._pstates.values() or [{"docs": self.docs, "codeviews": self.codeviews,
                                              "modviews": self.modviews}]
        return any(any(d.modified for d in st["docs"].values()) or
                   any(cv.editor.isModified() for cv in st["codeviews"].values()) or
                   any(mv.editor.isModified() for mv in st["modviews"].values()) for st in states)

    def add_form(self):
        if not self.project:
            return
        i = len(self.project.forms) + 1
        while f"Form{i}" in self.project.forms:
            i += 1
        dlg = AddItemDialog(self, "Add Windows Form", f"Form{i}", self.plugin.id, forms=True)
        if not dlg.exec():
            return
        name, language = dlg.name(), dlg.language()
        if not valid_identifier(name) or name.lower() in (f.lower() for f in self.project.forms) or \
                name.lower() in (os.path.splitext(m)[0].lower() for m in self.project.modules):
            QMessageBox.warning(self, APP_NAME, f"'{name}' is not a valid new form name.")
            return
        self.save_all()
        create_form(self.project, name, language)
        self._reload_startup_code()        # the startup file may now import/load the new form
        self._fill_solution()
        self.open_designer(name)

    def _fill_solution(self):
        """Solution Explorer: Solution 'X' > projects (startup bold) > References > forms/modules
        (radide/features/solution_ui.py)."""
        from .features.solution_ui import fill_tree
        fill_tree(self)

    def _on_solution_dclick(self, item, _col):
        from .features.solution_ui import PROJECT_ROLE
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        key = item.data(0, PROJECT_ROLE)
        if key and key in self._pstates:
            self.activate_project(self._pstates[key]["project"])
        kind, name = data[0], data[1]
        if kind == "reference":
            from .features.solution_ui import open_reference
            open_reference(self, name)
            return
        if kind == "proxy":
            from .features.solution_ui import open_proxy
            open_proxy(self, name)
            return
        if kind in ("webfile", "webfolder"):              # website folder tree (CONTRACTS 8.1)
            from .features.web_workspace import on_tree_activate
            on_tree_activate(self, kind, name)
            return
        if kind == "design":
            self.open_designer(name)
        elif kind == "code":
            self.open_code(name)
        elif kind == "module":
            self.open_module(name)
        elif kind == "generated":
            self.open_generated(name)

    # ================================================================ documents
    def _doc(self, name: str) -> FormDocument:
        if name not in self.docs:
            doc = FormDocument(Form.load(self.project.form_path(name)), self.project.form_path(name))
            doc.eventRequested.connect(lambda owner, ev, n=name: self.goto_event(n, owner, ev))
            doc.modifiedChanged.connect(lambda _m, n=name: self._update_tab_titles(n))
            doc.renamed.connect(lambda old, new, n=name: self._on_control_renamed(n, old, new))
            doc.formRenameRequested.connect(self._on_form_rename)
            doc.undoStateChanged.connect(self._update_actions)
            doc.selectionChanged.connect(lambda _c: self._update_actions())
            self.docs[name] = doc
        return self.docs[name]

    def _show_tab(self, widget, title: str):
        idx = self.tabs.indexOf(widget)
        if idx < 0:
            if self._active_key and widget.property("radProject") is None:
                widget.setProperty("radProject", self._active_key)      # the project it belongs to
                if self.project is not None and len(self._pstates) > 1:
                    widget.setToolTip(f"{self.project.name}: {title}")
            idx = self.tabs.addTab(widget, title)
            if self.project is not None and len(self._pstates) > 1:
                self.tabs.setTabToolTip(idx, f"{title}  ({self.project.name})")
        self.tabs.setCurrentIndex(idx)

    def open_designer(self, name: str):
        doc = self._doc(name)
        if name not in self.designers:
            self.designers[name] = DesignerView(doc)
            self.designers[name].contextActions.connect(lambda m, c, n=name: self._designer_menu(n, m, c))
        self._show_tab(self.designers[name], f"{name}.form [Design]")
        self._update_tab_titles(name)
        self.designers[name].overlay.setFocus()

    def _codeview(self, name: str) -> CodeView:
        if name not in self.codeviews:
            fp = self.plugin_for_form(name)
            path = self.project.folder / fp.code_file(name)
            cv = CodeView(self._doc(name), fp, path)
            cv.editor.setText(path.read_text(encoding="utf-8") if path.exists() else "")
            cv.editor.setModified(False)
            fname = fp.code_file(name)
            cv.editor.set_breakpoints(sorted(self.breakpoints.get(fname, set())))
            cv.editor.contextMenuAboutToShow.connect(lambda m, n=name: self._editor_menu(m, n))
            cv.editor.hoverWord.connect(lambda w, pos, ed=cv.editor: self._hover(ed, w, pos))
            cv.editor.modificationChanged.connect(lambda _m, n=name: self._update_tab_titles(n))
            cv.editor.breakpointToggled.connect(lambda line, on, f=fname: self._on_bp_toggled(f, line, on))
            self.codeviews[name] = cv
        return self.codeviews[name]

    def open_code(self, name: str):
        cv = self._codeview(name)
        self._show_tab(cv, self.plugin_for_form(name).code_file(name))
        self._update_tab_titles(name)
        cv.editor.setFocus()

    def goto_event(self, form_name: str, owner, event: str):
        """Double-click on a control: jump to (or create) its event handler."""
        doc = self._doc(form_name)
        cv = self._codeview(form_name)
        self.open_code(form_name)
        if not event:
            return
        fp = self.plugin_for_form(form_name)
        handler = fp.handler_for(doc.form, owner, event)
        code = cv.editor.text()
        line = fp.find_handler(code, handler)
        if line < 0:
            args = None if owner is not None and owner.type in ("MenuStrip", "ToolStrip") else event_args(event)
            code, line = fp.add_handler(code, handler, doc.form, args)
            self._replace_code(cv, code)
            doc.set_modified()   # designer code must be regenerated (Ring binds events)
        else:
            line += 1
        cv.editor.goto_line(line)

    @staticmethod
    def _replace_code(cv: CodeView, code: str):
        ed = cv.editor
        line, col = ed.getCursorPosition()
        ed.beginUndoAction()
        ed.selectAll()
        ed.replaceSelectedText(code)
        ed.endUndoAction()
        ed.setCursorPosition(min(line, ed.lines() - 1), col)

    def _on_control_renamed(self, form_name: str, old: str, new: str):
        cv = self._codeview(form_name)
        code = cv.editor.text()
        fp = self.plugin_for_form(form_name)
        updated = fp.rename_symbol(code, old, new)
        if updated != code:
            self._replace_code(cv, updated)
            self.log(f"Renamed '{old}' to '{new}' in {fp.code_file(form_name)}")

    def _on_form_rename(self, old: str, new: str):
        if not valid_identifier(new) or new.lower() in (f.lower() for f in self.project.forms if f != old):
            QMessageBox.warning(self, APP_NAME, f"'{new}' is not a valid form name.")
            self.properties.refresh()
            return
        if QMessageBox.question(self, APP_NAME, f"Rename form '{old}' to '{new}'?\n"
                                "All files are saved and renamed.") != QMessageBox.StandardButton.Yes:
            self.properties.refresh()
            return
        self.save_all()
        rename_form(self.project, old, new)
        self.breakpoints.pop(old, None)
        self.open_project(self.solution_path(), ask=False, activate=self.project.folder)
        self.open_designer(new)
        self.log(f"Form '{old}' renamed to '{new}'")

    def _current_form(self) -> str | None:
        w = self.tabs.currentWidget()
        for name, d in self.designers.items():
            if d is w:
                return name
        for name, c in self.codeviews.items():
            if c is w:
                return name
        return None

    def _current_designer(self) -> DesignerView | None:
        w = self.tabs.currentWidget()
        return w if isinstance(w, DesignerView) else None

    def _current_code(self) -> CodeView | None:
        w = self.tabs.currentWidget()
        return w if isinstance(w, (CodeView, ModuleView)) else None

    def view_code(self):
        name = self._current_form()
        if name:
            self.open_code(name)

    def view_designer(self):
        name = self._current_form()
        if name:
            self.open_designer(name)

    def _on_tab_changed(self, _idx):
        owner = self.project_of_widget(self.tabs.currentWidget())
        if owner is not None and owner is not self.project:
            self.activate_project(owner)          # the focused document decides the active project
        d = self._current_designer()
        if d is not None and self.project is not None:
            self.properties.set_document(d.doc, self.plugin_for_form(d.doc.form.name)
                                         if d.doc.form.name in self.project.forms else self.plugin)
            self.toolbox.setEnabled(True)
        else:
            self.toolbox.setEnabled(False)
            TOOL_STATE.set(None)
        self._update_actions()

    def _close_tab(self, idx: int):
        w = self.tabs.widget(idx)
        if hasattr(w, "maybe_close") and not w.maybe_close():     # e.g. Design View: "Save changes?"
            return
        self.tabs.removeTab(idx)
        if isinstance(w, StartPage):
            w.deleteLater()

    def _update_tab_titles(self, name: str):
        doc = self.docs.get(name)
        if name in self.designers:
            i = self.tabs.indexOf(self.designers[name])
            if i >= 0:
                self.tabs.setTabText(i, f"{name}.form [Design]" + ("*" if doc and doc.modified else ""))
        if name in self.codeviews:
            cv = self.codeviews[name]
            i = self.tabs.indexOf(cv)
            if i >= 0:
                self.tabs.setTabText(i, self.plugin_for_form(name).code_file(name) +
                                     ("*" if cv.editor.isModified() else ""))

    def _update_title(self):
        title = f"{self.project.name} - {APP_NAME}" if self.project else APP_NAME
        if self.project and self.sln is not None and (len(self.sln.projects) > 1 or not self.sln.implicit) \
                and self.sln.name != self.project.name:
            title = f"{self.project.name} - Solution '{self.sln.name}' - {APP_NAME}"
        if self.session is not None:
            title += " [break]" if self.session.paused else " [run]"
        self.setWindowTitle(title)

    def _update_actions(self):
        has = self.project is not None
        d, cv = self._current_designer(), self._current_code()
        running = self.session is not None and self.session.running()
        paused = running and self.session.paused
        for a in (self.a_save, self.a_add_form, self.a_code, self.a_design):
            a.setEnabled(has)
        self.a_run.setEnabled(has and (not running or paused))
        self.a_run_nodebug.setEnabled(has and not running)
        self.a_stop.setEnabled(running or getattr(self, "web_server", None) is not None)
        for a in (self.a_step_into, self.a_step_over, self.a_step_out):
            a.setEnabled(paused)
        cvp = getattr(getattr(cv, "editor", None), "plugin", None) or self.plugin
        self.a_bp.setEnabled(cv is not None and cvp is not None and cvp.supports_debug)
        self.a_undo.setEnabled(bool(d and d.doc.can_undo()) or cv is not None)
        self.a_redo.setEnabled(bool(d and d.doc.can_redo()) or cv is not None)
        sel = bool(d and d.doc.selection)
        for a in (self.a_cut, self.a_copy, self.a_delete):
            a.setEnabled(sel or cv is not None)
        self.a_paste.setEnabled(d is not None or cv is not None)
        self.a_select_all.setEnabled(d is not None or cv is not None)
        self.format_menu.setEnabled(d is not None)
        self._update_title()

    # ================================================================ edit
    @staticmethod
    def _focused_text_widget():
        """A plain text field with focus (Properties cell, Immediate input...)
        gets the Edit commands instead of the designer/editor."""
        w = QApplication.focusWidget()
        if isinstance(w, (QLineEdit, QPlainTextEdit)):
            return w
        return None

    def edit_undo(self):
        tw = self._focused_text_widget()
        if tw is not None:
            return tw.undo()
        d, cv = self._current_designer(), self._current_code()
        if d:
            d.doc.undo()
        elif cv:
            cv.editor.undo()

    def edit_redo(self):
        tw = self._focused_text_widget()
        if tw is not None:
            return tw.redo()
        d, cv = self._current_designer(), self._current_code()
        if d:
            d.doc.redo()
        elif cv:
            cv.editor.redo()

    def _edit(self, op: str):
        tw = self._focused_text_widget()
        if tw is not None:
            fn = {"cut": "cut", "copy": "copy", "paste": "paste", "select_all": "selectAll",
                  "delete": "del_" if isinstance(tw, QLineEdit) else "cut"}[op]
            if hasattr(tw, fn):
                getattr(tw, fn)()
            return
        d, cv = self._current_designer(), self._current_code()
        if d is not None:
            doc = d.doc
            if op == "cut":
                doc.cut()
            elif op == "copy":
                doc.copy()
            elif op == "paste":
                doc.paste()
            elif op == "delete":
                doc.remove_controls(list(doc.selection))
            elif op == "select_all":
                doc.select_many(doc.form.ordered())
            self._update_actions()
        elif cv is not None:
            ed = cv.editor
            {"cut": ed.cut, "copy": ed.copy, "paste": ed.paste,
             "delete": ed.removeSelectedText, "select_all": ed.selectAll}[op]()

    def _align(self, mode: str):
        d = self._current_designer()
        if d:
            d.doc.align(mode)

    def _order(self, front: bool):
        d = self._current_designer()
        if d and d.doc.selected and not d.doc.selected.ctype.nonvisual:
            d.doc.reorder(d.doc.selected, front)

    # ================================================================ files & menus
    def _code_text(self, form_name: str) -> str:
        if form_name in self.codeviews:
            return self.codeviews[form_name].editor.text()
        if self.project:
            p = self.project.folder / self.plugin_for_form(form_name).code_file(form_name)
            if p.exists():
                return p.read_text(encoding="utf-8")
        return ""

    def _editor_for_file(self, file: str):
        """Open the editor of a code file (a name of the active project, or a path of any project
        of the solution - that project becomes active)."""
        if self.project is None:
            return None
        if len(self._pstates) > 1:
            p = Path(file)
            owner = None
            if p.is_absolute():
                owner = next((st["project"] for st in self._pstates.values()
                              if self._pkey(st["project"]) == os.path.normcase(str(p.resolve().parent))), None)
            elif not self._has_file(self.project, p.name):
                owner = next((st["project"] for st in self._pstates.values()
                              if self._has_file(st["project"], p.name)), None)
            if owner is not None and owner is not self.project:
                self.activate_project(owner)
        base = Path(file).name.lower()
        for name in self.project.forms:
            if self.plugin_for_form(name).code_file(name).lower() == base:
                self.open_code(name)
                return self.codeviews[name].editor
        for mod in self.project.modules:
            if mod.lower() == base:
                self.open_module(mod)
                return self.modviews[mod].editor
        return None

    @staticmethod
    def _has_file(project, filename: str) -> bool:
        from .languages import plugin_for_form
        base = filename.lower()
        if any(m.lower() == base for m in project.modules):
            return True
        return any(plugin_for_form(project, f).code_file(f).lower() == base for f in project.forms)

    def open_module(self, filename: str):
        if filename not in self.modviews:
            path = self.project.folder / filename
            mv = ModuleView(self.plugin_for_file(filename), path)
            mv.editor.setText(path.read_text(encoding="utf-8") if path.exists() else "")
            mv.editor.setModified(False)
            mv.editor.set_breakpoints(sorted(self.breakpoints.get(filename, set())))
            mv.editor.modificationChanged.connect(lambda _m, f=filename: self._update_module_title(f))
            mv.editor.breakpointToggled.connect(lambda line, on, f=filename: self._on_bp_toggled(f, line, on))
            mv.editor.contextMenuAboutToShow.connect(lambda m: self._editor_menu(m, None))
            mv.editor.hoverWord.connect(lambda w, pos, ed=mv.editor: self._hover(ed, w, pos))
            self.modviews[filename] = mv
        self._show_tab(self.modviews[filename], filename)
        self._update_module_title(filename)
        self.modviews[filename].editor.setFocus()

    def _hover(self, editor, word, pos):
        from .tools import hover_value
        hover_value(self, editor, word, pos)

    def _update_module_title(self, filename: str):
        mv = self.modviews.get(filename)
        if mv is not None:
            i = self.tabs.indexOf(mv)
            if i >= 0:
                self.tabs.setTabText(i, filename + ("*" if mv.editor.isModified() else ""))

    def open_generated(self, form_name: str):
        """Show the generated designer code read-only."""
        self.save_all()
        fp = self.plugin_for_form(form_name)
        path = self.project.folder / fp.designer_file(form_name)
        from .editor import make_editor
        ed = make_editor(fp, path)
        ed.setText(path.read_text(encoding="utf-8") if path.exists() else "")
        ed.setReadOnly(True)
        self._show_tab(ed, path.name + " [read-only]")

    def add_module(self):
        if not self.project:
            return
        i = 1
        stems = {os.path.splitext(m)[0].lower() for m in self.project.modules}
        while f"module{i}" in stems:
            i += 1
        dlg = AddItemDialog(self, "Add Module", f"Module{i}", self.plugin.id, forms=False)
        if not dlg.exec():
            return
        name, language = dlg.name(), dlg.language()
        if not valid_identifier(name) or name.lower() in (f.lower() for f in self.project.forms) or \
                name.lower() in stems:
            QMessageBox.warning(self, APP_NAME, f"'{name}' is not a valid new module name.")
            return
        self.save_all()
        path = add_module(self.project, name, language)
        self._reload_startup_code()
        self._fill_solution()
        self.open_module(path.name)

    def add_existing(self):
        if not self.project:
            return
        files, _ = QFileDialog.getOpenFileNames(self, "Add Existing Item", str(self.project.folder),
                                                "Code files (" + " ".join(f"*{e}" for e in code_extensions()) +
                                                ");;All files (*)")
        if not files:
            return
        import shutil
        self.save_all()
        for f in files:
            src = Path(f)
            dst = self.project.folder / src.name
            if src.resolve() != dst.resolve():
                if dst.exists():
                    QMessageBox.warning(self, APP_NAME, f"'{src.name}' already exists in the project folder.")
                    continue
                shutil.copy2(src, dst)
            if src.stem not in self.project.forms:
                add_module(self.project, src.stem, filename=src.name)
        self._reload_startup_code()
        self._fill_solution()

    def _reload_startup_code(self):
        startup = self.project.startup
        if startup in self.codeviews:
            path = self.project.folder / self.plugin_for_form(startup).code_file(startup)
            if path.exists():
                self.codeviews[startup].editor.setText(path.read_text(encoding="utf-8"))
                self.codeviews[startup].editor.setModified(False)

    def delete_form_dialog(self, name: str):
        if QMessageBox.question(self, APP_NAME, f"Delete form '{name}' and its code?\n"
                                "(The files are moved to the project's _deleted folder.)") \
                != QMessageBox.StandardButton.Yes:
            return
        self.save_all()
        for d in (self.designers.pop(name, None), self.codeviews.pop(name, None)):
            if d is not None:
                i = self.tabs.indexOf(d)
                if i >= 0:
                    self.tabs.removeTab(i)
                d.deleteLater()
        if self.properties.doc is self.docs.get(name):
            self.properties.set_document(None, None)
        self.docs.pop(name, None)
        self.breakpoints.pop(self.plugin_for_form(name).code_file(name), None)
        delete_form(self.project, name)
        self._reload_startup_code()
        self._fill_solution()
        self.log(f"Deleted form '{name}'")

    def delete_module_dialog(self, filename: str):
        if QMessageBox.question(self, APP_NAME, f"Delete '{filename}'?\n"
                                "(The file is moved to the project's _deleted folder.)") \
                != QMessageBox.StandardButton.Yes:
            return
        self.save_all()
        mv = self.modviews.pop(filename, None)
        if mv is not None:
            i = self.tabs.indexOf(mv)
            if i >= 0:
                self.tabs.removeTab(i)
            mv.deleteLater()
        delete_module(self.project, filename)
        self._reload_startup_code()
        self._fill_solution()

    def rename_form_dialog(self, name: str):
        new, ok = QInputDialog.getText(self, "Rename Form", "New name:", text=name)
        if ok and new and new != name:
            self._on_form_rename(name, new)

    def set_startup(self, name: str):
        self.project.startup = name
        self.project.save()
        self._fill_solution()
        self.log(f"Startup form: {name}")

    def open_folder(self):
        if self.project:
            import os
            os.startfile(str(self.project.folder))  # noqa: S606 - Windows Explorer

    def project_properties(self):
        if not self.project:
            return
        if getattr(self.project, "kind", "") == "website":
            from .features.web_workspace import site_settings
            site_settings(self, self.project)
            return
        from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout
        dlg = QDialog(self)
        dlg.setWindowTitle(f"{self.project.name} Properties")
        lay = QFormLayout(dlg)
        lay.addRow("Project name:", QLabel(self.project.name))
        lay.addRow("Language:", QLabel(self.plugin.display_name))
        lay.addRow("Folder:", QLabel(str(self.project.folder)))
        lay.addRow("Output type:", QLabel("Class Library" if self.project.is_library else "Application"))
        lay.addRow("References:", QLabel(", ".join(self.project.references) or "(none)"))
        if self.sln is not None and len(self.sln.projects) > 1:
            lay.addRow("Solution:", QLabel(f"{self.sln.name}   (StartUp Project: {self.sln.startup or '-'})"))
        startup = QComboBox()
        startup.addItems(self.project.forms)
        startup.setCurrentText(self.project.startup)
        lay.addRow("Startup form:", startup)
        rp = self.run_plugin()
        if self.is_multi_language():
            used = sorted({language_label(self.plugin_for_form(f)) for f in self.project.forms} |
                          {language_label(self.plugin_for_file(m)) for m in self.project.modules})
            lay.addRow("Languages used:", QLabel(", ".join(used)))
        interp = QLabel(rp.find_interpreter(
            self.settings.value(f"interpreter/{rp.id}", "") or "") or "(not found)")
        lay.addRow(f"Interpreter ({language_label(rp)}):", interp)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(dlg.accept)
        box.rejected.connect(dlg.reject)
        lay.addRow(box)
        if dlg.exec() and startup.currentText():
            self.set_startup(startup.currentText())

    def _solution_menu(self, pos):
        try:
            from .features.solution_ui import solution_menu
        except ImportError:
            solution_menu = None
        if solution_menu is not None and self.project:
            return solution_menu(self, pos)
        self._basic_solution_menu(pos)

    def _basic_solution_menu(self, pos):
        if not self.project:
            m = QMenu(self)
            m.addAction(self.a_new)
            m.addAction(self.a_open)
            m.exec(self.solution.viewport().mapToGlobal(pos))
            return
        item = self.solution.itemAt(pos)
        data = item.data(0, Qt.ItemDataRole.UserRole) if item else ("project", "")
        kind, name = data or ("project", "")
        m = QMenu(self)
        if kind == "project":
            add = m.addMenu("Add")
            add.addAction("Windows Form...", self.add_form)
            add.addAction("Module...", self.add_module)
            add.addAction("Existing Item...", self.add_existing)
            m.addSeparator()
            m.addAction(self.a_run)
            m.addAction(self.a_run_nodebug)
            m.addSeparator()
            m.addAction("Save All", self.save_all)
            m.addAction("Open Folder in File Explorer", self.open_folder)
            m.addSeparator()
            m.addAction("Properties", self.project_properties)
        elif kind in ("design", "code", "generated"):
            m.addAction("Open (Designer)", lambda: self.open_designer(name))
            m.addAction("View Code", lambda: self.open_code(name))
            m.addAction("View Generated Code", lambda: self.open_generated(name))
            m.addSeparator()
            a = m.addAction("Set as Startup Form", lambda: self.set_startup(name))
            a.setEnabled(name != self.project.startup)
            m.addSeparator()
            m.addAction("Rename...", lambda: self.rename_form_dialog(name))
            m.addAction("Delete", lambda: self.delete_form_dialog(name))
            m.addSeparator()
            m.addAction("Add Windows Form...", self.add_form)
        elif kind == "module":
            m.addAction("Open", lambda: self.open_module(name))
            m.addSeparator()
            m.addAction("Delete", lambda: self.delete_module_dialog(name))
        m.exec(self.solution.viewport().mapToGlobal(pos))

    def _tab_menu(self, pos):
        bar = self.tabs.tabBar()
        idx = bar.tabAt(pos)
        if idx < 0:
            return
        w = self.tabs.widget(idx)
        m = QMenu(self)
        m.addAction("Close", lambda: self._close_tab(self.tabs.indexOf(w)))
        m.addAction("Close All But This", lambda: self._close_others(w))
        m.addAction("Close All", lambda: self._close_others(None))
        form = next((n for n, d in {**self.designers, **self.codeviews}.items() if d is w), None)
        if form:
            m.addSeparator()
            m.addAction("View Code", lambda: self.open_code(form))
            m.addAction("View Designer", lambda: self.open_designer(form))
        m.exec(bar.mapToGlobal(pos))

    def _close_others(self, keep):
        for i in reversed(range(self.tabs.count())):
            if self.tabs.widget(i) is not keep:
                self._close_tab(i)

    def _designer_menu(self, form_name: str, m, c):
        """Extra items for the designer's right-click menu."""
        doc = self._doc(form_name)
        code = self._code_text(form_name)
        fp = self.plugin_for_form(form_name)
        events = fp.events_for(c)
        if events:
            sub = QMenu("Events", m)
            bold = QFont()
            bold.setBold(True)
            for ev in events:
                handler = fp.handler_for(doc.form, c, ev)
                label = f"{ev}.Click" if c is not None and c.type in ("MenuStrip", "ToolStrip") else ev
                a = sub.addAction(label, lambda e=ev: doc.eventRequested.emit(c, e))
                if fp.find_handler(code, handler) >= 0:
                    a.setFont(bold)
            m.insertMenu(m.actions()[1] if len(m.actions()) > 1 else None, sub)
        if c is not None and not c.ctype.nonvisual and len(doc.selection) > 1:
            al = QMenu("Align", m)
            for text, mode in (("Lefts", "left"), ("Centers", "center_v"), ("Rights", "right"),
                               ("Tops", "top"), ("Middles", "middle"), ("Bottoms", "bottom"),
                               ("Same Size", "same_size")):
                al.addAction(text, lambda m_=mode: doc.align(m_))
            m.addMenu(al)
        m.addSeparator()
        if c is None:
            m.addAction("Add Windows Form...", self.add_form)
            m.addAction("Select All", lambda: doc.select_many(doc.form.ordered()))
        m.addAction("Properties", lambda: (self.dock_props.show(), self.dock_props.raise_(),
                                           self.properties.tabs.setCurrentIndex(0)))

    def _editor_menu(self, m, form_name):
        first = m.actions()[0] if m.actions() else None
        extra = []
        if form_name:
            extra.append(("View Designer", lambda: self.open_designer(form_name)))
        if self.run_plugin() is not None and self.run_plugin().supports_debug:
            extra.append(("Toggle Breakpoint", self.toggle_breakpoint))
        extra.append(("Run (F5)", self.start_or_continue))
        for text, slot in extra:
            a = QAction(text, m)
            a.triggered.connect(slot)
            m.insertAction(first, a)
        if first is not None:
            m.insertSeparator(first)

    # ================================================================ import
    def _ask_import_target(self, src: Path, suffix: str) -> Path | None:
        default = src.parent / f"{src.stem}{suffix}"
        d = QFileDialog.getExistingDirectory(self, "Folder for the new RAD IDE project", str(src.parent))
        if not d:
            return None
        target = Path(d) / f"{src.stem}{suffix}"
        if target.exists() and any(target.iterdir()):
            QMessageBox.warning(self, APP_NAME, f"The folder already exists and is not empty:\n{target}")
            return None
        return target if d else default

    def _show_import_report(self, rep, title: str):
        self.log(rep.text())
        if rep.project is None:
            QMessageBox.warning(self, title, rep.text())
            return
        QMessageBox.information(self, title, rep.text() + f"\n\nProject: {rep.project.folder}")
        self.open_project(rep.project.folder, ask=False)

    def import_python(self):
        if not self._confirm_close_project():
            return
        f, _ = QFileDialog.getOpenFileName(self, "Import Python GUI Program", "", "Python files (*.py *.pyw)")
        if not f:
            return
        src = Path(f)
        target = self._ask_import_target(src, "_RAD")
        if target is None:
            return
        from .importers.python_import import detect_toolkit, import_python_program
        src_text = src.read_text(encoding="utf-8-sig", errors="replace")
        interp = sys.executable
        if detect_toolkit(src_text) == "qt":
            interp = QFileDialog.getOpenFileName(
                self, "Python interpreter that has PySide6/PyQt installed (Cancel = use the IDE's)",
                str(src.parent), "python.exe (python*.exe)")[0] or sys.executable
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.statusBar().showMessage(f"Importing {src.name} (running it to read its windows)...")
        try:
            rep = import_python_program(src, target, interp)
        finally:
            QApplication.restoreOverrideCursor()
            self.statusBar().clearMessage()
        self._show_import_report(rep, "Import Python Program")

    def import_vb6(self):
        if not self._confirm_close_project():
            return
        f, _ = QFileDialog.getOpenFileName(self, "Import Visual Basic 6 Project", "",
                                           "VB6 project or form (*.vbp *.frm)")
        if not f:
            return
        src = Path(f)
        target = self._ask_import_target(src, "_RAD")
        if target is None:
            return
        from .languages import all_plugins
        from .importers.vb6_import import import_vb6
        langs = [p.display_name for p in all_plugins()]
        ids = [p.id for p in all_plugins()]
        default = ids.index("vb-basic") if "vb-basic" in ids else 0
        choice, ok = QInputDialog.getItem(self, "Import VB6", "Target language:", langs, default, False)
        if not ok:
            return
        rep = import_vb6(src, target, ids[langs.index(choice)])
        self._show_import_report(rep, "Import VB6 Project")

    # ================================================================ save
    def save_all(self) -> bool:
        """Save every open document of every project of the solution."""
        if not self.project:
            return False
        active = self.project
        saved_libs = []
        for st in list(self._pstates.values()) or [None]:
            if st is not None:
                self.activate_project(st["project"])
            if self._save_active_project() and self.project.is_library:
                saved_libs.append(self.project)
        self.activate_project(active)
        if saved_libs and self.sln is not None:   # consumers see the library's new functions
            from .features.solution_ui import refresh_consumers
            refresh_consumers(self, saved_libs)
        self.statusBar().showMessage("All files saved", 3000)
        return True

    def _save_active_project(self) -> bool:
        """Save the active project's documents; True when a code file was written."""
        wrote = False
        names = set(self.docs) | set(self.codeviews)
        for name in names:
            doc = self._doc(name)
            fp = self.plugin_for_form(name)
            code_path = self.project.folder / fp.code_file(name)
            if name in self.codeviews:
                cv = self.codeviews[name]
                code = cv.editor.text()
                if cv.editor.isModified() or not code_path.exists():
                    code_path.write_text(code, encoding="utf-8")
                    cv.editor.setModified(False)
                    wrote = True
            else:
                code = code_path.read_text(encoding="utf-8")
            doc.save()
            designer_path = self.project.folder / fp.designer_file(name)
            designer_path.write_text(fp.generate_designer(doc.form, code), encoding="utf-8")
            self._update_tab_titles(name)
        for mod, mv in self.modviews.items():
            if mv.editor.isModified():
                (self.project.folder / mod).write_text(mv.editor.text(), encoding="utf-8")
                mv.editor.setModified(False)
                self._update_module_title(mod)
                wrote = True
        self.project.save()
        self._save_breakpoints()
        return wrote

    def log(self, text: str):
        self.output.appendPlainText(text)
        self._output_after_log = True        # program output starts on a new line

    # ================================================================ breakpoints
    def _bp_key(self) -> str:
        return "breakpoints/" + str(self.project.folder).replace("\\", "/").replace("/", "|")

    def _load_breakpoints(self):
        raw = self.settings.value(self._bp_key(), "") or ""
        self.breakpoints = {}
        for part in filter(None, str(raw).split(";")):
            form, _, line = part.rpartition(":")
            if line.isdigit():
                self.breakpoints.setdefault(form, set()).add(int(line))

    def _save_breakpoints(self):
        if not self.project:
            return
        self._sync_breakpoints()
        raw = ";".join(f"{f}:{ln}" for f, lines in self.breakpoints.items() for ln in sorted(lines))
        self.settings.setValue(self._bp_key(), raw)

    def toggle_breakpoint(self):
        cv = self._current_code()
        if cv is not None:
            cv.editor.toggle_breakpoint()

    def _sync_breakpoints(self):
        for name, cv in self.codeviews.items():
            self.breakpoints[self.plugin_for_form(name).code_file(name)] = set(cv.editor.breakpoints())
        for mod, mv in self.modviews.items():
            self.breakpoints[mod] = set(mv.editor.breakpoints())

    def _on_bp_toggled(self, filename: str, line: int, on: bool):
        lines = self.breakpoints.setdefault(filename, set())
        (lines.add if on else lines.discard)(line)
        if self.session is not None:
            self.session.set_breakpoint(filename, line + 1, on,
                                        getattr(self, "bp_conditions", {}).get((filename, line), ""))

    def _all_breakpoints(self) -> list[tuple[str, int]]:
        self._sync_breakpoints()
        conds = getattr(self, "bp_conditions", {})
        return [(f, ln + 1, conds.get((f, ln), "")) for f, lines in self.breakpoints.items() for ln in lines]

    # ================================================================ run / debug
    def _interpreter(self) -> str:
        rp = self.run_plugin()
        key = f"interpreter/{rp.id}"
        found = rp.find_interpreter(self.settings.value(key, "") or "")
        if not found:
            found = self.choose_interpreter()
        return found

    def choose_interpreter(self) -> str:
        rp = self.run_plugin()
        if not rp:
            return ""
        f, _ = QFileDialog.getOpenFileName(self, f"Locate {rp.display_name} interpreter",
                                           "", "Programs (*.exe);;All files (*)")
        if f:
            self.settings.setValue(f"interpreter/{rp.id}", f)
        return f

    def start_or_continue(self):
        if self.session is not None and self.session.paused:
            self.session.cont()
        else:
            self.run_project(debug=True)

    def run_project(self, debug: bool = True):
        if not self.project or (self.session is not None and self.session.running()):
            return
        self.save_all()
        if self.sln is not None:                 # a solution runs its StartUp Project
            from .features.solution_ui import prepare_run
            if not prepare_run(self):
                return
        if getattr(self.project, "kind", "") == "website":      # web site: DevServer + Preview (CONTRACTS 8.1)
            from .features.web_workspace import run_website
            run_website(self, self.project, debug=debug)
            return
        interp = self._interpreter()
        if not interp:
            self.log("No interpreter configured (Tools > Interpreter Path...)")
            return
        rp = self.run_plugin()
        if rp.id.startswith("python"):
            interp = real_python(interp)        # not the Windows Store alias
        debug = debug and rp.supports_debug
        try:
            if debug:
                spec = rp.debug_spec(self.project.folder, self.project.startup, interp,
                                     self._all_breakpoints())
            else:
                spec = rp.run_spec(self.project.folder, self.project.startup, interp)
        except Exception as e:  # noqa: BLE001 - show plugin errors instead of crashing
            self.log(f"*** Cannot start the program: {e}")
            return
        spec = self._start_hub(spec)
        self.output.clear()
        self.locals.clear()
        self.callstack.clear()
        self.dock_output.show()
        self.dock_output.raise_()
        self.log(f"------ {'Debug' if debug else 'Run'}: {spec.program} {' '.join(spec.args)} ------")
        s = self._make_session(spec, debug, rp, interp)
        s.output.connect(self._append_output)
        s.stopped.connect(self._on_stopped)
        s.resumed.connect(self._on_resumed)
        from .tools import on_eval_result
        s.evalResult.connect(lambda txt: on_eval_result(self, txt) or self.immediate.show_result(txt))
        s.finished.connect(self._on_finished)
        s.failed.connect(lambda err: self.log(f"*** Error: {err}"))
        self.session = s
        s.start()
        self.statusBar().showMessage("Running...")
        self._update_actions()

    def _make_session(self, spec, debug, plugin, interp):
        """Python debugging uses debugpy (DAP) when installed: conditional breakpoints and
        break on exception come ready-made. Everything else uses the plugin's own agent."""
        import importlib.util
        if debug and plugin.id.startswith("python") and importlib.util.find_spec("debugpy") is not None \
                and self.settings.value("debug/python_engine", "debugpy") == "debugpy":
            from .dap import DapSession
            program = str(self.project.folder / plugin.code_file(self.project.startup))
            s = DapSession("debugpy", program, [], self.project.folder.resolve(), spec.env,
                           self._all_breakpoints(), self)
            s.launch_args["python"] = [real_python(interp)]
            s.break_on_exception = self.settings.value("debug/break_on_exception", True) in (True, "true")
            return s
        return Session(spec, debug, self)

    # ---------------------------------------------------------- RAD Hub (cross-language calls)
    def _start_hub(self, spec):
        """Start a RAD Hub for this run and give the program RAD_HUB / RAD_PROJECT."""
        import os as _os

        from .runtimes.radhub import RadHub
        self._stop_hub()

        def interp_for(plugin):
            return plugin.find_interpreter(self.settings.value(f"interpreter/{plugin.id}", "") or "")
        search = []
        if self.sln is not None:   # modules of referenced projects (transitively) are found too
            search = [Path(p.folder) for p in self.sln.referenced_projects(self.project)]
        try:
            self.hub = RadHub(self.project.folder, log=self._hub_log.emit, interpreter_for=interp_for,
                              search_folders=search)
        except TypeError:          # older RadHub without solution support
            self.hub = RadHub(self.project.folder, log=self._hub_log.emit, interpreter_for=interp_for)
        try:
            self.hub.start()
        except OSError as e:
            self.log(f"*** RAD Hub could not start ({e}); cross-language calls are disabled")
            self.hub = None
            return spec
        self._copy_clients()
        spec.env = self.hub.child_env(base=spec.env if spec.env is not None else dict(_os.environ))
        return spec

    def _copy_clients(self):
        """radcall clients that a language loads from the project folder."""
        folder = self.project.folder
        try:
            if any("radcall" in f.read_text(encoding="utf-8", errors="replace")
                   for f in folder.glob("*.ring") if f.name != "radcall.ring"):
                from .languages.ring_qt import copy_ring_client
                copy_ring_client(folder)
        except OSError as e:
            self.log(f"*** cannot copy radcall.ring: {e}")
        try:                     # Python: also on PYTHONPATH; the copy helps IntelliSense and EXE builds
            if any("radcall" in f.read_text(encoding="utf-8", errors="replace")
                   for f in folder.glob("*.py") if f.name != "radcall.py"):
                from .runtimes.radhub import CLIENTS
                src = (CLIENTS / "python" / "radcall.py").read_bytes()
                target = folder / "radcall.py"
                if not target.exists() or target.read_bytes() != src:
                    target.write_bytes(src)
        except OSError as e:
            self.log(f"*** cannot copy radcall.py: {e}")

    def _stop_hub(self):
        hub, self.hub = getattr(self, "hub", None), None
        if hub is not None:
            hub.stop()

    def _append_output(self, text: str):
        self.output.moveCursor(self.output.textCursor().MoveOperation.End)
        if getattr(self, "_output_after_log", False) and not self.output.document().isEmpty():
            text = "\n" + text
        self._output_after_log = False
        self.output.insertPlainText(text)
        self.output.ensureCursorVisible()

    def _form_for_file(self, file: str) -> str | None:
        base = Path(file).name.lower()
        for name in self.project.forms:
            if self.plugin_for_form(name).code_file(name).lower() == base:
                return name
        return None

    def _on_stopped(self, info: StopInfo):
        self._clear_current_line()
        ed = self._editor_for_file(info.file)
        if ed is not None:
            ed.set_current_line(info.line - 1)
            self.stopped_at = (ed, info.line - 1)
        where = f"{Path(info.file).name} line {info.line}"
        self.statusBar().showMessage(f"Paused ({info.reason}) at {where}")
        if info.reason == "error":
            self.log(f"\n*** Error at {where}")
        self.locals.clear()
        for name, typ, value in info.variables:
            QTreeWidgetItem(self.locals, [name, value, typ])
        self.callstack.clear()
        for func, file, line in info.frames:
            self.callstack.addItem(f"{func}()   {Path(file).name}: line {line}")
            self.callstack.item(self.callstack.count() - 1).setData(Qt.ItemDataRole.UserRole, (file, line))
        self.dock_locals.show()
        self.dock_locals.raise_()
        bring_to_front(self)
        self._update_actions()

    def _on_frame_dclick(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            ed = self._editor_for_file(data[0])
            if ed is not None:
                ed.goto_line(int(data[1]) - 1)

    def _clear_current_line(self):
        if self.stopped_at:
            try:
                self.stopped_at[0].set_current_line(None)
            except RuntimeError:     # editor already closed
                pass
        self.stopped_at = None

    def _on_resumed(self):
        self._clear_current_line()
        self.statusBar().showMessage("Running...")
        self._update_actions()

    def stop_project(self):
        if self.session is not None:
            self.session.stop()
        if getattr(self, "web_server", None) is not None:    # web site dev server (CONTRACTS 8.1)
            from .features.web_workspace import stop_website
            stop_website(self)

    def _on_finished(self, code):
        self._clear_current_line()
        if self.session is not None and self.session.user_stopped:
            self.log("\n------ Debugging stopped ------")
        else:
            self.log(f"\n------ Program exited with code {code} ------")
        self.session = None
        self._stop_hub()
        self.statusBar().showMessage("Ready")
        self._update_actions()

    def closeEvent(self, e):
        if not self._confirm_close_project():
            e.ignore()
            return
        active = self.project
        for st in list(self._pstates.values()):
            self.activate_project(st["project"])
            self._save_breakpoints()
        if active is not None:
            self.activate_project(active)
        self.stop_project()
        self._stop_hub()
        e.accept()


def main(argv=None):
    try:                               # QtWebEngine must be imported before QApplication
        __import__("PyQt6.QtWebEngineWidgets")
    except ImportError:
        pass
    argv = sys.argv if argv is None else argv
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    try:      # one consistent theme: Light unless Tools > Options says Dark (not Windows' dark mode)
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    except AttributeError:
        pass
    app.setFont(QFont("Segoe UI", 9))
    win = MainWindow()
    if len(argv) > 1 and Path(argv[1]).exists():
        win.open_project(Path(argv[1]))
    win.show()
    return app.exec()
