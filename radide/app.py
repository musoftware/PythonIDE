"""Main IDE window: menus, toolbar, docks (Toolbox, Solution Explorer,
Properties, Output, Locals, Call Stack, Immediate), designer/code tabs,
run and debug."""
from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QSettings, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QKeySequence
from PyQt6.QtWidgets import (QApplication, QDockWidget, QFileDialog, QInputDialog, QLabel, QLineEdit, QListWidget,
                             QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QStyle, QTabWidget, QTreeWidget)

from .controls import CONTROL_TYPES, event_args
from .debugger import Session, StopInfo
from .designer import DesignerView
from .dialogs import AddItemDialog
from .document import FormDocument
from .editor import CodeView
from .extension_points import ExtensionPoints
from .interpreters import project_venv_python
from .immediate_window import ImmediateWindow
from .module_view import ModuleView
from .run_controller import RunController
from .solution_controller import SolutionController
from .start_page import StartPage
from .languages import code_extensions, get_plugin, language_label
from .model import FORM_LOAD_ERRORS, Form, Project, write_text_safe
from .properties import PropertiesPanel, valid_identifier
from .solution import Solution
from .toolbox import TOOL_STATE, Toolbox
from .workspace import add_module, create_form, delete_form, delete_module, rename_form
from . import __version__

from . import APP_NAME  # noqa: E402,F401 - the name in titles and message boxes (radide/__init__.py)


def ide_settings() -> QSettings:
    """The IDE's settings. Tests set QCoreApplication.setOrganizationName("RADIDE-TEST...")
    before creating the window so that they never touch the user's real "RADIDE" settings."""
    org = QCoreApplication.organizationName()
    if org.upper().startswith("RADIDE-TEST"):
        return QSettings(org, QCoreApplication.applicationName() or org)
    from .paths import qsettings      # an INI file in <install>\settings for a portable build
    return qsettings()

STYLE = """
QMainWindow, QDockWidget { background: #F0F0EA; }
QDockWidget::title { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #F6F7F9, stop:1 #D8DFEA);
                     padding: 4px; border: 1px solid #A0AFC3; font-weight: bold; }
QTabBar::tab:selected { background: #ffffff; }
QToolBar { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #FAFAFA, stop:1 #E3E3DC);
           border-bottom: 1px solid #C0C0B8; spacing: 2px; }
"""


class MainWindow(QMainWindow):
    _hub_log = pyqtSignal(str)          # RAD Hub output (emitted from its threads)
    _log_from_thread = pyqtSignal(str)  # log() called from a worker thread -> appended on the UI thread

    def __init__(self):
        super().__init__()
        self.hub = None                  # radide.runtimes.radhub.RadHub while a program runs
        self._hub_log.connect(self._append_output)
        self._log_from_thread.connect(self.log)
        self.settings = ide_settings()
        try:        # the theme's application style sheet before any widget exists: each widget is polished once
            from . import theme as _theme    # (Tools > Options applies it again at the end: then a no-op)
            _theme.apply(str(self.settings.value("options/theme", "Light") or "Light"))
        except Exception:  # noqa: BLE001 - the options code applies the theme anyway
            pass
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
        self._no_save_questions = 0      # > 0: no "Save changes?" question (see no_save_questions)
        self.temp_breakpoints: list[tuple[str, int, str]] = []   # (file, 1-based line, condition): Run to Cursor
        self.run_controller = RunController(self)       # run / debug (radide/run_controller.py)
        self.solution_controller = SolutionController(self)
        # how features take part in File > Open / Save All / Solution Explorer ... (radide/extension_points.py)
        self.extension_points = ExtensionPoints(lambda text: self.log(text))

        from . import screenfit         # every window and dialog stays on small screens / high scaling
        screenfit.install()
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

        # a layout the user arranged (saved by the workbench) wins over our default dock sizes
        self._had_saved_layout = self.settings.contains("workbench/state/vs")
        self._make_docks()
        self._make_actions()
        if self.option("show_start_page", True):
            self.tabs.addTab(StartPage(self), "Start Page")
        self._make_status()
        self._update_title()
        self._update_actions()
        from .tools import install_tools
        install_tools(self)
        from .features import install_all
        install_all(self)

    def restoreState(self, state, version: int = 0) -> bool:  # noqa: N802 - Qt API
        ok = super().restoreState(state, version)
        if hasattr(self, "extension_points"):
            self.extension_points.emit("layout_restored")      # auto-hide docks, dock tab bars ...
        return ok

    def option(self, name: str, default=None):
        """A Tools > Options value ("options/<name>"), bools and ints converted."""
        v = self.settings.value("options/" + name, default)
        if isinstance(default, bool):
            return v if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes")
        if isinstance(default, int):
            try:
                return int(v)
            except (TypeError, ValueError):
                return default
        return v

    def show_options(self):
        from .features.settings import show_options
        show_options(self)

    # ---------------------------------------------------------------- status bar
    def _make_status(self):
        sb = self.statusBar()
        self.status_ready = QLabel("Ready")
        self.status_ready.setMinimumWidth(60)
        sb.addWidget(self.status_ready, 1)
        self.status_pos = QLabel("")
        self.status_pos.setToolTip("Line and column of the cursor (Ctrl+G: Go to Line)")
        self.status_pos.setMinimumWidth(self.status_pos.fontMetrics().horizontalAdvance("Ln 99999, Col 999") + 12)
        self.status_pos.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_pos.hide()
        sb.addPermanentWidget(self.status_pos)
        from .progress import install_status_progress
        install_status_progress(self)       # background tasks (radide/progress.py)
        self._pos_timer = QTimer(self, interval=250)
        self._pos_timer.timeout.connect(self._update_cursor_pos)
        self._pos_timer.start()

    def _update_cursor_pos(self):
        """Ln / Col of the active editor (Monaco or the built-in one). The VS Code / Agent layouts show
        their own position item, so ours is hidden there."""
        lbl = self.status_pos
        wb = getattr(self, "workbench", None)
        ed = None
        if wb is None or getattr(wb, "mode", "vs") == "vs":
            w = self.tabs.currentWidget()
            ed = getattr(w, "editor", None) or w
            if not hasattr(ed, "getCursorPosition"):
                ed = None
        if ed is None:
            if lbl.isVisible():
                lbl.hide()
            return
        try:
            line, col = ed.getCursorPosition()
        except Exception:  # noqa: BLE001 - an editor being destroyed
            return
        text = f"Ln {line + 1}, Col {col + 1}"
        if lbl.text() != text:
            lbl.setText(text)
        if not lbl.isVisible():
            lbl.show()

    # ---------------------------------------------------------------- default dock sizes
    def showEvent(self, e):
        super().showEvent(e)
        if not getattr(self, "_rad_first_show", False):
            self._rad_first_show = True
            if not self._had_saved_layout:
                QTimer.singleShot(0, self.apply_default_dock_sizes)

    def apply_default_dock_sizes(self):
        """Visual Studio defaults for the window's real size: a slim Output panel, the Toolbox wide
        enough for its names, Solution Explorer above a tall Properties window."""
        wb = getattr(self, "workbench", None)
        if wb is not None and getattr(wb, "mode", "vs") != "vs":
            return
        H, V = Qt.Orientation.Horizontal, Qt.Orientation.Vertical
        out = max(140, min(180, int(self.height() * 0.18)))
        right = max(300, min(380, int(self.width() * 0.23)))
        if not self.dock_toolbox.isFloating() and self.dock_toolbox.isVisible():
            self.resizeDocks([self.dock_toolbox], [200], H)
        if not self.dock_solution.isFloating():
            self.resizeDocks([self.dock_solution], [right], H)
        if not self.dock_output.isFloating():
            self.resizeDocks([self.dock_output], [out], V)
        from .screenfit import apply_small_screen_layout
        apply_small_screen_layout(self)         # small screens only: tab group / lower Output

        def split():
            sol, props = self.dock_solution, self.dock_props
            if sol.isFloating() or props.isFloating() or not (sol.isVisible() and props.isVisible()):
                return
            if self.dockWidgetArea(sol) != self.dockWidgetArea(props):
                return
            total = sol.height() + props.height()
            top = max(170, int(total * 0.36))
            self.resizeDocks([sol, props], [top, max(200, total - top)], V)
        QTimer.singleShot(0, split)

    # ================================================================ UI setup
    def _dock(self, title: str, widget, area) -> QDockWidget:
        d = QDockWidget(title, self)
        d.setObjectName(title)
        d.setWidget(widget)
        self.addDockWidget(area, d)
        return d

    def _make_docks(self):
        self.toolbox = Toolbox()
        self.toolbox.itemDoubleClicked.connect(self._toolbox_dclick)
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
        # stable widths: opening a code editor (Monaco) must not squeeze the tool windows
        self.toolbox.setMinimumWidth(180)
        self.solution.setMinimumWidth(220)
        self.properties.setMinimumWidth(240)
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
        self.a_save.setToolTip("Save All (Ctrl+S)")
        from . import icons
        self.a_open_file = A("Open &File...", self.open_file_dialog, "Ctrl+O")
        self.a_open_file.setIcon(icons.icon("open_file"))
        self.a_new_window = A("New &Window", self.new_window, "Ctrl+Alt+N")
        self.a_new_window.setToolTip("Open another RAD IDE window (Ctrl+Alt+N)")
        self.a_open_folder = A("Open Fol&der...", self.open_folder_dialog, "Ctrl+K, Ctrl+O", SP.SP_DirIcon)
        self.a_open_folder.setToolTip("Open any folder: a RAD IDE project, a Visual Studio/VB6/... project "
                                      "or just a folder of files (Ctrl+K Ctrl+O)")
        self.a_save_file = A("&Save", self.save_current)
        self.a_save_file.setIcon(icons.icon("save"))
        self.a_close_sln = A("Close Solutio&n", self.close_solution)
        self.a_close_sln.setIcon(icons.icon("close_solution"))
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
        self.file_menu = m
        for a in (self.a_new, self.a_new_window, None, self.a_open, self.a_open_file, self.a_open_folder, None,
                  self.a_close_sln, None,
                  self.a_save_file, self.a_save, None):
            m.addSeparator() if a is None else m.addAction(a)
        self.recent_menu = m.addMenu("Recent &Projects and Solutions")
        self.recent_menu.aboutToShow.connect(self._fill_recent_menu)
        self._fill_recent_menu()
        m.addSeparator()
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
        m.aboutToShow.connect(lambda m_=m: _vs_view_menu(m_))
        m = mb.addMenu("&Project")
        m.addAction(self.a_add_form)
        m.addAction("Add &Module...", self.add_module)
        m.addAction("Add &Existing Item...", self.add_existing)
        m.addSeparator()
        m.addAction("Open Project &Folder", self.open_folder)
        m.addAction("Project &Properties...", self.project_properties)
        # Format menu (Visual Studio 2005 / 2022 WinForms designer); each command is greyed out unless it
        # applies to the selection (FormDocument.can_format)
        self.format_menu = m = mb.addMenu("F&ormat")
        self.format_actions: dict[str, QAction] = {}
        for title, items in (
                ("&Align", (("&Lefts", "left"), ("&Centers", "center_v"), ("&Rights", "right"), None,
                            ("&Tops", "top"), ("&Middles", "middle"), ("&Bottoms", "bottom"), None,
                            ("to &Grid", "to_grid"))),
                ("&Make Same Size", (("&Width", "same_width"), ("&Size to Grid", "size_to_grid"),
                                     ("&Height", "same_height"), ("&Both", "same_size"))),
                ("&Horizontal Spacing", (("&Make Equal", "hspace_equal"), ("&Increase", "hspace_inc"),
                                         ("&Decrease", "hspace_dec"), ("&Remove", "hspace_remove"))),
                ("&Vertical Spacing", (("&Make Equal", "vspace_equal"), ("&Increase", "vspace_inc"),
                                       ("&Decrease", "vspace_dec"), ("&Remove", "vspace_remove"))),
                ("&Center in Form", (("&Horizontally", "center_form_h"), ("&Vertically", "center_form_v")))):
            sub = m.addMenu(title)
            for it in items:
                if it is None:
                    sub.addSeparator()
                    continue
                self.format_actions[it[1]] = sub.addAction(it[0], lambda m_=it[1]: self._align(m_))
        m.addSeparator()
        sub = m.addMenu("&Order")
        self.a_bring_front = sub.addAction("Bring to &Front", lambda: self._order(True))
        self.a_send_back = sub.addAction("Send to &Back", lambda: self._order(False))
        m.aboutToShow.connect(self._sync_format_menu)
        m = mb.addMenu("&Debug")
        for a in (self.a_run, self.a_run_nodebug, self.a_stop, None, self.a_step_into,
                  self.a_step_over, self.a_step_out, None, self.a_bp):
            m.addSeparator() if a is None else m.addAction(a)
        m = mb.addMenu("&Tools")
        m.addAction(self.a_interp)
        m = mb.addMenu("&Help")
        m.addAction(self._act("&About", lambda: QMessageBox.about(
            self, APP_NAME,
            f"<h3>{APP_NAME} {__version__}</h3>"
            "<p>A Visual Basic 2005 style IDE for scripting languages.</p>"
            "<p>© 2026 Musoftware - <a href='https://musoftwares.com'>musoftwares.com</a></p>"
            "<p>Free and open source under the MIT License: anyone may use, copy and modify it, "
            "as long as the credit to Musoftware (musoftwares.com) is kept. "
            "See LICENSE and THIRD_PARTY_NOTICES.md.</p>")))
        m.addAction(self._act("Check for &Updates...", self.check_ide_updates))
        try:
            from .features import ide_update
            ide_update.install_menu(self, m)
            ide_update.schedule_startup_check(self)
        except Exception as e:  # noqa: BLE001 - the updater must never stop the IDE from starting
            print(f"[update] {e}", file=sys.stderr)

        tb = self.addToolBar("Standard")
        tb.setObjectName("Standard")
        tb.addActions([self.a_new, self.a_open, self.a_save])
        tb.addSeparator()
        tb.addActions([self.a_undo, self.a_redo])
        tb.addSeparator()
        tb.addActions([self.a_run, self.a_stop])
        tb2 = self.addToolBar("Debug")
        tb2.setObjectName("Debug")
        for a, text, ic in ((self.a_step_into, "Step Into", "step_into"), (self.a_step_over, "Step Over", "step_over"),
                            (self.a_step_out, "Step Out", "step_out"), (self.a_bp, "Toggle Breakpoint", "breakpoint")):
            a.setIconText(text)
            a.setIcon(icons.icon(ic))
            tb2.addAction(a)
        for a in (self.a_new, self.a_open, self.a_undo, self.a_redo, self.a_run, self.a_run_nodebug, self.a_stop,
                  self.a_step_into, self.a_step_over, self.a_step_out, self.a_bp, self.a_open_file):
            self._tip(a)

    @staticmethod
    def _tip(a: QAction) -> None:
        """Tool tip = the command name + its shortcut, e.g. "Step Over (F10)"."""
        text = a.text().replace("&", "").replace("...", "")
        keys = a.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
        a.setToolTip(f"{text} ({keys})" if keys else text)

    def _fill_recent_menu(self):
        return self.solution_controller._fill_recent_menu()

    def _refresh_recent(self):
        return self.solution_controller._refresh_recent()

    # ================================================================ project
    def recent_projects(self) -> list[str]:
        return self.solution_controller.recent_projects()

    def _remember(self, path: Path):
        return self.solution_controller._remember(path)

    def new_project(self):
        return self.solution_controller.new_project()

    def open_project_dialog(self):
        return self.solution_controller.open_project_dialog()

    def new_window(self):
        return self.solution_controller.new_window()

    def open_folder_dialog(self):
        return self.solution_controller.open_folder_dialog()

    def open_file_dialog(self):
        return self.solution_controller.open_file_dialog()

    def open_file(self, path, line: int | None = None):
        """Open a file from a link - Error List, Find Results, Go to Definition, the web Solution Explorer -
        optionally at *line* (1-based); a relative path is relative to the active project. Providers registered
        with links=True (hex view, ROM workbench, text-mode / retro graphics designers, notebooks, Flutter
        screens) take their files; everything else opens in the window's editors (CONTRACTS 8.1).
        Returns the editor (None for images / binaries)."""
        p = Path(path)
        if not p.is_absolute() and self.project is not None:
            p = Path(self.project.folder) / p
        if p.is_file():
            handled, editor = self.extension_points.open_document(p, links=True)
            if handled:
                return editor
        from .features.web_workspace import open_file as open_in_editor     # TODO(stage B): into the window
        return open_in_editor(self, path, line)

    def open_any_file(self, path: Path):
        handled, editor = self.extension_points.open_document(Path(path))    # image editor, designers ...
        if handled:
            return editor
        path = Path(path).resolve()
        from .safeio import SaveError, check_open_size
        try:
            check_open_size(path)               # a 1 GB file is never read into an editor (safeio.py)
        except SaveError as e:
            self.statusBar().showMessage(str(e).splitlines()[0], 8000)
            if not os.environ.get("RADIDE_TEST_NO_DIALOGS"):
                QMessageBox.warning(self, APP_NAME, str(e))
            return None
        if self.project is not None and callable(getattr(self, "open_file", None)):
            return self.open_file(path)                # web_workspace: project/web files, images ...
        for w in (self.tabs.widget(i) for i in range(self.tabs.count())):
            if isinstance(w, ModuleView) and Path(w.path).resolve() == path:
                self.tabs.setCurrentWidget(w)
                return w.editor
        from .languages import all_plugins
        ext = path.suffix.lower()
        plugin = next((p for p in all_plugins() if p.code_ext == ext), None) or get_plugin("python-tk")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="cp1252", errors="replace")
        except OSError as e:
            QMessageBox.warning(self, APP_NAME, f"Cannot open the file:\n{e}")
            return None
        mv = ModuleView(plugin, path)
        mv.editor.setText(text)
        mv.editor.setModified(False)
        mv.setToolTip(str(path))
        self._show_tab(mv, path.name)
        mv.editor.modificationChanged.connect(
            lambda m, v=mv: self.tabs.indexOf(v) >= 0 and self.tabs.setTabText(
                self.tabs.indexOf(v), v.path.name + ("*" if m else "")))
        return mv.editor

    def save_current(self) -> bool:
        """File > Save <file>: only the document of the current tab. A failed write (disk full, read-only,
        locked by another program) shows why and keeps the document modified; the file on disk is unchanged
        (radide/safeio.py)."""
        try:
            ok = self._save_current()
        except OSError as e:
            self.show_save_error(e)
            ok = False
        self.extension_points.emit("file_saved", ok)
        return ok

    def show_save_error(self, e: OSError) -> None:
        from .safeio import SaveError, describe
        text = str(e) if isinstance(e, SaveError) else describe(e, getattr(e, "filename", None))
        try:                                    # Arabic UI: each sentence of the message (radide/i18n)
            from .i18n import tr
            text = "\n".join(tr(line) for line in text.splitlines())
        except Exception:  # noqa: BLE001
            pass
        self.log("*** " + " ".join(text.splitlines()))
        self.statusBar().showMessage(text.splitlines()[0], 8000)
        if not os.environ.get("RADIDE_TEST_NO_DIALOGS"):
            QMessageBox.warning(self, "Save failed", text)

    def _save_current(self) -> bool:
        w = self.tabs.currentWidget()
        if w is None or isinstance(w, StartPage):
            return False
        owner = self.project_of_widget(w)
        if owner is not None and owner is not self.project:
            self.activate_project(owner)
        form = next((n for n, v in {**self.designers, **self.codeviews}.items() if v is w), None)
        mod = next((m for m, v in self.modviews.items() if v is w), None)
        if form is not None and self.project is not None:
            self._save_form(form)
            self.project.save()
            self._save_breakpoints()
            name = self.plugin_for_form(form).code_file(form)
        elif mod is not None and self.project is not None:
            if w.editor.isModified():
                writer = getattr(self.project, "write_code", None)     # foreign projects: same encoding
                if callable(writer):
                    writer(self.project.folder / mod, w.editor.text())
                else:
                    write_text_safe(self.project.folder / mod, w.editor.text())
                w.editor.setModified(False)
                self._update_module_title(mod)
            name = mod
        elif isinstance(w, ModuleView):                     # a file opened without a project
            write_text_safe(w.path, w.editor.text())
            w.editor.setModified(False)
            name = w.path.name
        elif callable(getattr(w, "save", None)):           # Design View and other documents
            w.save()
            name = self.tabs.tabText(self.tabs.currentIndex()).rstrip("*")
        else:
            return False
        self.statusBar().showMessage(f"Saved {name}", 3000)
        return True

    def close_solution(self):
        return self.solution_controller.close_solution()

    def open_project(self, folder: Path, ask: bool = True, activate=None):
        """Open a solution (.radsln), a project (project.radproj) or a folder that holds one.
        A bare project opens as a one-project solution. *activate* = folder or name of the
        project to make active (default: the startup project). Emits project_opening / project_opened
        (radide/extension_points.py)."""
        self.extension_points.emit("project_opening", Path(folder))
        result = self._open_project(folder, ask, activate)
        self.extension_points.emit("project_opened")
        return result

    def _open_project(self, folder: Path, ask: bool, activate):
        return self.solution_controller._open_project(folder, ask, activate)

    def _reset(self):
        self.extension_points.emit("projects_reset")      # language servers, diagnostics ... first
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
        return self.solution_controller._state_for(project)

    def project_states(self) -> list[dict]:
        return self.solution_controller.project_states()

    def projects(self) -> list[Project]:
        return self.solution_controller.projects()

    def activate_project(self, project) -> bool:
        """Make *project* (a Project, or a project name of the solution) the active project:
        self.project, self.plugin, docs, designers, codeviews, modviews and breakpoints then
        belong to it. Returns False when it is not part of the open solution. Emits project_activated."""
        result = self._activate_project(project)
        self.extension_points.emit("project_activated")
        return result

    def _activate_project(self, project) -> bool:
        return self.solution_controller._activate_project(project)

    def project_of_widget(self, w) -> Project | None:
        return self.solution_controller.project_of_widget(w)

    def startup_project(self) -> Project | None:
        return self.solution_controller.startup_project()

    def _forget_project(self, project) -> None:
        return self.solution_controller._forget_project(project)

    # ---------------------------------------------------------- languages (multi-language projects)
    def plugin_for_form(self, name: str):
        return self.solution_controller.plugin_for_form(name)

    def plugin_for_file(self, filename: str):
        return self.solution_controller.plugin_for_file(filename)

    def run_plugin(self):
        return self.solution_controller.run_plugin()

    def is_multi_language(self) -> bool:
        return self.solution_controller.is_multi_language()

    @contextlib.contextmanager
    def no_save_questions(self):
        """Inside this block the IDE does not ask "Save changes?" (a project opened in place without asking,
        the automation channel's forced quit)."""
        self._no_save_questions += 1
        try:
            yield
        finally:
            self._no_save_questions -= 1

    def _confirm_close_project(self) -> bool:
        if self._no_save_questions:
            return True
        ok = self._confirm_close_inner()
        if ok:              # saved or discarded on purpose: the crash recovery snapshot is not needed any more
            try:
                from .features.recovery import discard_open
                discard_open(self)
            except Exception:  # noqa: BLE001
                pass
        return ok

    def _confirm_close_inner(self) -> bool:
        if not self._any_modified():
            return True
        if not self.option("confirm_unsaved", True):      # Tools > Options: save without asking
            return bool(self.save_all())               # a failed save keeps the project open
        r = QMessageBox.question(self, APP_NAME, "Save changes to the current project?",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Cancel:
            return False
        if r == QMessageBox.StandardButton.Save:
            return bool(self.save_all())               # a failed save (disk full, locked) cancels the close
        return True

    def _any_modified(self) -> bool:
        if self.extension_points.any_modified():
            return True
        states =self._pstates.values() or [{"docs": self.docs, "codeviews": self.codeviews,
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
        self.extension_points.fill_solution()

    def _on_solution_dclick(self, item, _col):
        from .features.solution_ui import PROJECT_ROLE
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        key = item.data(0, PROJECT_ROLE)
        if key and key in self._pstates:
            self.activate_project(self._pstates[key]["project"])
        kind, name = data[0], data[1]
        if str(kind).startswith("foreign"):           # foreign project trees (radide/features/foreign_projects.py)
            from .features.foreign_projects import on_tree_activate
            on_tree_activate(self, item, kind, name)
            return
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
            loader = getattr(self.project, "load_form", None)    # foreign projects: native form file
            doc = FormDocument(loader(name) if callable(loader) else Form.load(self.project.form_path(name)),
                               self.project.form_path(name))
            doc.eventRequested.connect(lambda owner, ev, n=name: self.goto_event(n, owner, ev))
            doc.modifiedChanged.connect(lambda _m, n=name: self._update_tab_titles(n))
            doc.renamed.connect(lambda old, new, n=name: self._on_control_renamed(n, old, new))
            doc.codeRenamed.connect(lambda old, new, n=name: self._on_control_renamed(n, old, new))
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
        """Open (or show) the designer of a form. Emits designer_opening, then form_opened + designer_opened;
        a damaged .form goes to the form_load_failed handlers (radide/extension_points.py)."""
        self.extension_points.emit("designer_opening", name)
        opened, result = self._open_form_view(self._open_designer, name)
        if opened:
            self.extension_points.emit("designer_opened", name)
        return result

    def _open_form_view(self, opener, name: str):
        """(opened, result) of opener(name); a damaged .form is reported, not raised, when a feature
        handles form_load_failed (file_integrity: "Cannot open form ... the file was not changed")."""
        known = name in self.docs
        try:
            result = opener(name)
        except FORM_LOAD_ERRORS as e:
            if not self.extension_points.has_handlers("form_load_failed"):
                raise
            self.extension_points.emit("form_load_failed", name, e)
            return False, None
        self.extension_points.emit("form_opened", name, not known and name in self.docs)
        return True, result

    def _open_designer(self, name: str):
        if name not in self.docs and self.project is not None and not self.project.form_path(name).is_file():
            self.log(f"*** The form file was not found: {self.project.form_path(name)}")
            self.statusBar().showMessage(f"{name}.form is missing", 5000)
            return
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
            reader = getattr(self.project, "read_code", None)    # foreign projects: keep the file's encoding
            cv.editor.setText(reader(path) if callable(reader) else
                              (path.read_text(encoding="utf-8") if path.exists() else ""))
            cv.editor.setModified(False)
            fname = fp.code_file(name)
            cv.editor.set_breakpoints(sorted(self.breakpoints.get(fname, set())))
            cv.editor.contextMenuAboutToShow.connect(lambda m, n=name: self._editor_menu(m, n))
            cv.editor.hoverWord.connect(lambda w, pos, ed=cv.editor: self._hover(ed, w, pos))
            cv.editor.modificationChanged.connect(lambda _m, n=name: self._update_tab_titles(n))
            cv.editor.breakpointToggled.connect(lambda line, on, f=fname: self._on_bp_toggled(f, line, on))
            self.codeviews[name] = cv
        cv = self.codeviews[name]
        self.extension_points.emit("code_view_requested", name, cv)      # language servers ...
        return cv

    def open_code(self, name: str):
        """Open (or show) the code of a form (emits form_opened; a damaged .form: form_load_failed)."""
        return self._open_form_view(self._open_code, name)[1]

    def _open_code(self, name: str):
        if name not in self.docs and self.project is not None and not self.project.form_path(name).is_file():
            self.log(f"*** The form file was not found: {self.project.form_path(name)}")
            return
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
        rename = getattr(fp, "rename_control", None) or fp.rename_symbol    # code only, not strings / comments
        updated = rename(code, old, new)
        if updated != code:
            self._replace_code(cv, updated)
            self.log(f"Renamed '{old}' to '{new}' in {fp.code_file(form_name)}")

    def _on_form_rename(self, old: str, new: str):
        if callable(getattr(self.project, "load_form", None)):     # foreign project: native names stay
            QMessageBox.information(self, APP_NAME, "Renaming the form of a project opened in place is not "
                                    "supported here - rename it in its own IDE (the files keep their names).")
            self.properties.refresh()
            return
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
        self._set_title()
        if hasattr(self, "extension_points"):
            self.extension_points.emit("title_updated")

    def _set_title(self):
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
        for a in (self.a_save, self.a_add_form, self.a_code, self.a_design, self.a_close_sln):
            a.setEnabled(has)
        cur = self.tabs.currentWidget()
        title = self.tabs.tabText(self.tabs.currentIndex()).rstrip("*") if cur is not None else ""
        savable = cur is not None and not isinstance(cur, StartPage) and (
            d is not None or cv is not None or callable(getattr(cur, "save", None)))
        self.a_save_file.setEnabled(savable)
        self.a_save_file.setText(f"&Save {title}" if savable and title else "&Save")
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
        if hasattr(self, "extension_points"):
            self.extension_points.emit("actions_updated")     # features' own commands / Edit commands

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
        if d and d.doc.selection:
            d.doc.reorder(list(d.doc.selection), front)    # VS: every selected control

    def _toolbox_dclick(self, item):
        """Toolbox double-click (VS): the control is added to the shown form at once."""
        name = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        d = self._current_designer()
        if d is None or not name or name not in CONTROL_TYPES:
            return
        TOOL_STATE.set(None)
        d.add_default(name)

    def _sync_format_menu(self):
        """Grey out the Format commands that do not apply to the selection (as Visual Studio does)."""
        d = self._current_designer()
        doc = d.doc if d is not None else None
        for mode, a in getattr(self, "format_actions", {}).items():
            a.setEnabled(bool(doc is not None and doc.can_format(mode)))
        for menu in self.format_menu.findChildren(QMenu):
            acts = [a for a in menu.actions() if not a.isSeparator()]
            if acts and all(a in self.format_actions.values() for a in acts):
                menu.setEnabled(any(a.isEnabled() for a in acts))
        visual = bool(doc is not None and any(not c.ctype.nonvisual for c in doc.selection))
        for a in (getattr(self, "a_bring_front", None), getattr(self, "a_send_back", None)):
            if a is not None:
                a.setEnabled(visual)

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
        hook = getattr(self.sln, "editor_for_file", None)     # foreign solutions: nested paths, many projects
        if callable(hook):
            ed = hook(self, file)
            if ed is not None:
                return ed
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
        if getattr(self.project, "kind", "") == "website" and Path(file).is_absolute() and \
                Path(file).is_file() and callable(getattr(self, "open_file", None)):
            return self.open_file(Path(file))       # web site debugging: .php / .js files of the site
        # the debugger stopped in another source file (Step Into a client library, a designer file, the caller
        # of an event handler...): open it like Visual Studio does, so the current line is shown
        # (open_any_file -> web_workspace.open_file asks _editor_for_file again: not twice)
        if getattr(self, "_opening_debug_file", False):
            return None
        p = Path(file) if Path(file).is_absolute() else Path(self.project.folder) / file
        self._opening_debug_file = True
        try:
            if file and p.is_file() and p.suffix.lower() not in (".exe", ".dll", ".so", ".o", ".obj", ".pyc"):
                ed = self.open_any_file(p)
                return ed if hasattr(ed, "set_current_line") else None
        except OSError:
            pass
        finally:
            self._opening_debug_file = False
        return None

    @staticmethod
    def _has_file(project, filename: str) -> bool:
        from .languages import plugin_for_form
        base = filename.lower()
        if any(m.lower() == base for m in project.modules):
            return True
        return any(plugin_for_form(project, f).code_file(f).lower() == base for f in project.forms)

    def open_module(self, filename: str):
        if self.project is not None:          # a report / scene ... listed as a project file: its own editor
            handled, editor = self.extension_points.open_document(Path(self.project.folder) / filename)
            if handled:
                return editor
        if filename not in self.modviews:
            path = self.project.folder / filename
            mv = ModuleView(self.plugin_for_file(filename), path)
            reader = getattr(self.project, "read_code", None)    # foreign projects: keep the file's encoding
            mv.editor.setText(reader(path) if callable(reader) else
                              (path.read_text(encoding="utf-8") if path.exists() else ""))
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
        self.extension_points.emit("module_view_shown", filename, self.modviews[filename])

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
        if self.extension_points.show_properties(self.project):    # e.g. a VB6 mirror project's own dialog
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
        interp = QLabel(rp.find_interpreter(self._configured_interpreter(rp)) or "(not found)")
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
        try:                                    # project actions of the clicked file (features/project_menus.py)
            from .features.solution_ui import apply_menu_hooks
            apply_menu_hooks(self, item, m)
        except ImportError:
            pass
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
                al.addAction(text, lambda m_=mode: doc.align(m_)).setEnabled(doc.can_format(mode))
            m.addMenu(al)
        m.addSeparator()
        if c is None:
            m.addAction("Add Windows Form...", self.add_form)
            m.addAction("Select All", lambda: doc.select_many(doc.form.ordered()))
        m.addAction("Properties", lambda: (self.dock_props.show(), self.dock_props.raise_(),
                                           self.properties.tabs.setCurrentIndex(0)))
        self.extension_points.emit("designer_menu", form_name, m, c)     # animations, variants ...

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
        self.extension_points.emit("editor_menu", m, form_name)

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
            from .progress import run_blocking      # runs the program to read its windows: worker thread
            rep = run_blocking(self, f"Importing {src.name}", lambda r: import_python_program(src, target, interp))
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
        """Save every open document of every project of the solution (and of every DocumentProvider);
        the extension points' save listeners run before and afterwards, whatever the result. The Save All
        command and Ctrl+S call this method too: every way of saving goes through the same steps."""
        ep = self.extension_points
        ep.before_save_all()
        ok = False
        try:
            providers_ok = ep.save_documents()     # image editor, designers ... (any project)
            ok = self._save_projects(providers_ok)
            return ok
        finally:
            ep.after_save_all(ok)

    def _save_projects(self, providers_ok: bool) -> bool:
        if not self.project:             # loose files only (an image, a notebook ...): their save is the result -
            return providers_ok          # False here kept the IDE open after "Save changes?" -> Save
        active = self.project
        saved_libs = []
        try:
            for st in list(self._pstates.values()) or [None]:
                if st is not None:
                    self.activate_project(st["project"])
                if self._save_active_project() and self.project.is_library:
                    saved_libs.append(self.project)
        except OSError as e:            # disk full / read-only / locked: nothing truncated, documents stay dirty
            self.activate_project(active)
            self.show_save_error(e)
            return False
        self.activate_project(active)
        if saved_libs and self.sln is not None:   # consumers see the library's new functions
            from .features.solution_ui import refresh_consumers
            refresh_consumers(self, saved_libs)
        try:                            # everything is on disk: drop the crash recovery snapshot
            from .features.recovery import snapshot
            snapshot(self)
        except Exception:  # noqa: BLE001
            pass
        if not providers_ok:
            self.statusBar().showMessage("Some files were not saved - see the Output window", 8000)
            return False
        self.statusBar().showMessage("All files saved", 3000)
        return True

    def _save_form(self, name: str) -> bool:
        """Save one form (code file, .form and generated designer code); True when code was written.
        Emits form_saving before and form_saved(name, completed) after (format on save, resources ...)."""
        self.extension_points.emit("form_saving", name)
        completed = False
        try:
            result = self._write_form(name)
            completed = True
            return result
        finally:
            self.extension_points.emit("form_saved", name, completed)

    def _write_form(self, name: str) -> bool:
        wrote = False
        doc = self._doc(name)
        fp = self.plugin_for_form(name)
        code_path = self.project.folder / fp.code_file(name)
        saver = getattr(self.project, "save_form", None)      # foreign projects write their native files
        if callable(saver):
            cv = self.codeviews.get(name)
            code = cv.editor.text() if cv is not None else None
            changed = bool(cv is not None and cv.editor.isModified())
            new_code = saver(name, doc.form, code, changed, doc.modified)
            if cv is not None:
                if isinstance(new_code, str) and new_code != code:
                    self._replace_code(cv, new_code)
                cv.editor.setModified(False)
            doc.set_modified(False)
            self._update_tab_titles(name)
            return changed or isinstance(new_code, str)
        if name in self.codeviews:
            cv = self.codeviews[name]
            code = cv.editor.text()
            if cv.editor.isModified() or not code_path.exists():
                write_text_safe(code_path, code)
                cv.editor.setModified(False)
                wrote = True
        else:
            code = code_path.read_text(encoding="utf-8")
        doc.save()
        designer_path = self.project.folder / fp.designer_file(name)
        write_text_safe(designer_path, fp.generate_designer(doc.form, code))
        self._update_tab_titles(name)
        return wrote

    def _save_active_project(self) -> bool:
        """Save the active project's documents; True when a code file was written. Emits project_saving
        before and project_saved(completed) after (format on save, VB6 mirror write-back ...)."""
        self.extension_points.emit("project_saving")
        completed = False
        try:
            result = self._write_active_project()
            completed = True
            return result
        finally:
            self.extension_points.emit("project_saved", completed)

    def _write_active_project(self) -> bool:
        wrote = False
        names = set(self.docs) | set(self.codeviews)
        for name in names:
            wrote = self._save_form(name) or wrote
        for mod, mv in self.modviews.items():
            if mv.editor.isModified():
                writer = getattr(self.project, "write_code", None)     # foreign projects: same encoding
                if callable(writer):
                    writer(self.project.folder / mod, mv.editor.text())
                else:
                    write_text_safe(self.project.folder / mod, mv.editor.text())
                mv.editor.setModified(False)
                self._update_module_title(mod)
                wrote = True
        self.project.save()
        self._save_breakpoints()
        return wrote

    def log(self, text: str):
        import threading
        if threading.current_thread() is not threading.main_thread():
            # Qt widgets only from the UI thread: features log from worker threads (e.g. the local database
            # servers) and appendPlainText there crashed the IDE (access violation - action crawler)
            self._log_from_thread.emit(text)
            return
        self.output.appendPlainText(text)
        self._output_after_log = True        # program output starts on a new line
        self.extension_points.emit("output_logged", text)

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
        return [(f, ln + 1, conds.get((f, ln), "")) for f, lines in self.breakpoints.items() for ln in lines] + \
            list(self.temp_breakpoints)

    # ================================================================ run / debug
    def project_venv_python(self, project=None) -> str:
        """python.exe of the project's own virtual environment (<project>/.venv), or ""."""
        project = project or self.project
        if project is None:
            return ""
        return project_venv_python(Path(project.folder))

    def _configured_interpreter(self, plugin, project=None) -> str:
        """Python projects run with their .venv first, then Tools > Options / Interpreter Path."""
        if plugin is not None and plugin.id.startswith("python"):
            venv = self.project_venv_python(project)
            if venv:
                return venv
        return self.settings.value(f"interpreter/{plugin.id}", "") or "" if plugin is not None else ""

    def _interpreter(self) -> str:
        rp = self.run_plugin()
        found = rp.find_interpreter(self._configured_interpreter(rp))
        if not found:
            found = self.choose_interpreter()
        return found

    def check_ide_updates(self) -> None:
        """Help > Check for Updates: the latest GitHub release of RAD IDE (radide/features/ide_update.py)."""
        from .features.ide_update import check_for_updates
        check_for_updates(self)

    def choose_interpreter(self) -> str:
        rp = self.run_plugin()
        if not rp:
            return ""
        f, _ = QFileDialog.getOpenFileName(self, f"Locate {rp.display_name} interpreter",
                                           "", "Programs (*.exe);;All files (*)")
        if f:
            self.settings.setValue(f"interpreter/{rp.id}", f)
        return f


    def _effective_startup(self, rp) -> str | None:
        return self.run_controller._effective_startup(rp)

    def start_or_continue(self):
        if self.session is not None and self.session.paused:
            self.session.cont()
        else:
            self.run_project(debug=True)

    def run_project(self, debug: bool = True):
        """F5 / Ctrl+F5: a feature may run the project itself (Expo, flutter run, Godot's debug adapter, a VS
        Code debugger: radide/extension_points.py run handlers); otherwise the window runs it."""
        if self.extension_points.run(debug):
            return None
        return self._run_project(debug)

    def _run_project(self, debug: bool = True):
        return self.run_controller._run_project(debug)

    def _make_session(self, spec, debug, plugin, interp, startup=None):
        """The session that runs / debugs the program (emits session_created: assembly / DOS / retro tools
        add their views)."""
        s = self._create_session(spec, debug, plugin, interp, startup)
        if s is not None:
            self.extension_points.emit("session_created", s, debug, plugin)
        return s

    def _create_session(self, spec, debug, plugin, interp, startup=None):
        return self.run_controller._create_session(spec, debug, plugin, interp, startup)

    def _install_debugpy(self, python: str) -> bool:
        return self.run_controller._install_debugpy(python)

    # ---------------------------------------------------------- RAD Hub (cross-language calls)
    def _start_hub(self, spec):
        return self.run_controller._start_hub(spec)

    def _copy_clients(self):
        return self.run_controller._copy_clients()

    def _stop_hub(self):
        return self.run_controller._stop_hub()

    def _append_output(self, text: str):
        return self.run_controller._append_output(text)

    def _form_for_file(self, file: str) -> str | None:
        return self.run_controller._form_for_file(file)

    def _on_stopped(self, info: StopInfo):
        self.extension_points.emit("debug_pausing", info)
        self._show_stopped(info)
        self.extension_points.emit("debug_paused", info)      # Watch, CPU view, native windows ...

    def _show_stopped(self, info: StopInfo):
        return self.run_controller._show_stopped(info)

    def _on_frame_dclick(self, item):
        return self.run_controller._on_frame_dclick(item)

    def _clear_current_line(self):
        return self.run_controller._clear_current_line()

    def _set_run_state(self, text: str) -> None:
        return self.run_controller._set_run_state(text)

    def _on_resumed(self):
        self.extension_points.emit("debug_resuming")
        self._show_resumed()
        self.extension_points.emit("debug_resumed")

    def _show_resumed(self):
        return self.run_controller._show_resumed()

    def stop_project(self):
        return self.run_controller.stop_project()

    def _on_finished(self, code, session=None):
        if session is None:
            snd = self.sender()
            session = snd if snd is not None and hasattr(snd, "user_stopped") else None
        self._show_finished(code, session)
        self.extension_points.emit("program_finished", code, session)

    def _show_finished(self, code, session=None):
        return self.run_controller._show_finished(code, session)

    def closeEvent(self, e):
        # features first (agent tasks running, remote files ...: radide/extension_points.py), then the save question
        if not self.extension_points.confirm_close() or not self._confirm_close_project():
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
        self.extension_points.shutdown()      # language servers, terminal, layout ... (in registration order)


def _dock_on_top(d) -> bool:
    """Is the tool window really visible (not hidden behind another tab of its group, not zero-sized)?"""
    return d.isVisible() and not d.visibleRegion().isEmpty()


def _show_tool_window(d) -> None:
    """View > <tool window> like Visual Studio: always show it, bring its tab to the front, focus it.
    An auto-hidden window (features/dock_autohide) slides out of its edge instead."""
    ah = getattr(d.parentWidget(), "autohide", None)
    if ah is not None and ah.is_auto_hidden(d):
        ah.show_dock(d)
        return
    d.show()
    if d.width() < 60 or d.height() < 60:          # collapsed to nothing by an old layout
        d.resize(max(d.width(), 280), max(d.height(), 220))
    if d.isFloating():
        from PyQt6.QtGui import QGuiApplication
        if not any(s.availableGeometry().intersects(d.frameGeometry()) for s in QGuiApplication.screens()):
            mw = d.parentWidget()
            c = (mw.frameGeometry().center() if mw is not None
                 else QGuiApplication.primaryScreen().availableGeometry().center())
            d.move(c.x() - d.width() // 2, c.y() - d.height() // 2)
    d.raise_()
    if d.isFloating():
        d.activateWindow()
    w = d.widget()
    if w is not None:
        w.setFocus(Qt.FocusReason.OtherFocusReason)


def _vs_view_menu(menu) -> None:
    """Every dock toggle action of the View menu (and its submenus, also those features add later):
    a click shows + raises the window instead of toggling (Qt's toggleViewAction hid a window that was
    'visible' but covered by another tab), and the check mark means 'really on screen'."""
    from PyQt6.QtWidgets import QDockWidget
    for a in menu.actions():
        if a.menu() is not None and a.menu() is not menu:
            _vs_view_menu(a.menu())
            continue
        d = a.parent()
        if not isinstance(d, QDockWidget) or a is not d.toggleViewAction():
            continue
        if not a.property("vsShow"):
            a.setProperty("vsShow", True)
            a.triggered.connect(lambda _c=False, d_=d: QTimer.singleShot(0, lambda: _show_tool_window(d_)))
        a.blockSignals(True)
        a.setChecked(_dock_on_top(d))
        a.blockSignals(False)


def parse_command_line(args: list[str]):
    """python -m radide [path ...] [--line N] [--new-window] [--register | --unregister | --shell-status]
    [--quiet] [--desktop | --no-desktop] [--no-uninstall-entry]. Unknown options (Qt's) are ignored."""
    import argparse
    ap = argparse.ArgumentParser(prog="radide", add_help=False)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--line", "-l", type=int, default=None)
    ap.add_argument("--new-window", "-n", action="store_true")
    ap.add_argument("--register", action="store_true")
    ap.add_argument("--unregister", action="store_true")
    ap.add_argument("--shell-status", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--desktop", dest="desktop", action="store_true", default=None)
    ap.add_argument("--no-desktop", dest="desktop", action="store_false")
    ap.add_argument("--no-uninstall-entry", action="store_true")
    ap.add_argument("--shell-options", default=None)     # e.g. file_assoc,open_with,context_menu (installer tasks)
    ap.add_argument("--if-owner", action="store_true")   # --unregister only a registration of this exe (uninstaller)
    ap.add_argument("--automation", default=None)       # opt-in test automation pipe name (radide/automation)
    ns, _unknown = ap.parse_known_args(args)
    ns.paths = [p for p in ns.paths if p and Path(p).exists()]
    return ns


def main(argv=None):
    argv = sys.argv if argv is None else argv
    from . import agent_cli                  # --check / --build / --run / --publish / --info: headless (agents)
    if agent_cli.wants(list(argv[1:])):
        return agent_cli.main(list(argv[1:]))
    opts = parse_command_line(list(argv[1:]))
    if opts.register or opts.unregister or opts.shell_status:     # Windows integration, no window
        from .shell_integration import cli
        return cli(opts.register, opts.unregister, opts.shell_status, opts.quiet, opts.desktop,
                   not opts.no_uninstall_entry, opts.shell_options, opts.if_owner)
    try:                               # QtWebEngine must be imported before QApplication
        __import__("PyQt6.QtWebEngineWidgets")
    except ImportError:
        pass
    try:                              # DevTools port for debugging JavaScript in the Preview (before QApplication)
        from .web_site.browser_debug import enable_remote_debugging
        enable_remote_debugging(ide_settings())
    except Exception:  # noqa: BLE001 - optional
        pass
    app = QApplication(argv)
    try:                              # the DevTools port is the IDE's own: programs started from it must not inherit it
        from .web_site.browser_debug import seal_child_environment
        seal_child_environment()
    except Exception:  # noqa: BLE001
        pass
    if getattr(sys, "frozen", False):  # release build: children must not inherit the bundled Qt's paths
        from .paths import clean_child_environment
        clean_child_environment()
    app.setApplicationName(APP_NAME)
    test_org = os.environ.get("RADIDE_SETTINGS_ORG", "")    # automation runs from source: test settings only
    if test_org.upper().startswith("RADIDE-TEST") and os.environ.get("RADIDE_AUTOMATION"):
        app.setOrganizationName(test_org)
    app.setStyle("Fusion")
    try:      # one consistent theme: Light unless Tools > Options says Dark (not Windows' dark mode)
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    except AttributeError:
        pass
    app.setFont(QFont("Segoe UI", 9))
    win = None

    def excepthook(etype, value, tb):
        # PyQt6 aborts the whole process on an exception escaping a slot unless a hook is set:
        # report it (stderr + Output window) and keep the IDE running.
        import traceback
        text = "".join(traceback.format_exception(etype, value, tb))
        sys.__stderr__ and sys.__stderr__.write(text)
        try:
            if win is not None:
                win.log("*** Internal error (the IDE keeps running):\n" + text.rstrip())
        except Exception:  # noqa: BLE001
            pass
    sys.excepthook = excepthook
    lock = None
    single = not opts.new_window and str(ide_settings().value("options/single_instance", True)).lower() \
        not in ("false", "0", "no")
    if single:                         # one window: a later launch hands its paths over (single_instance.py)
        try:
            from .single_instance import acquire_primary, send
            lock = acquire_primary()
            if lock is None and opts.paths and send(opts.paths, opts.line):
                return 0
        except Exception as e:  # noqa: BLE001 - never stop the IDE from starting
            sys.__stderr__ and sys.__stderr__.write(f"[single instance] {e}\n")
            lock = None
    win = MainWindow()
    if lock is not None:
        try:
            from .single_instance import start_server
            start_server(win, lock)
        except Exception as e:  # noqa: BLE001
            win.log(f"[single instance] {e}")
    if opts.paths:
        from .single_instance import open_target
        for p in opts.paths:
            try:
                open_target(win, Path(p), opts.line)
            except Exception as e:  # noqa: BLE001
                win.log(f"*** cannot open {p}: {e}")
    elif win.option("reopen_last", False) and win.recent_projects():
        win.open_project(Path(win.recent_projects()[0]), ask=False)
    win.show()
    if not opts.paths:                 # unsaved work of a session that crashed / was killed (features/recovery.py)
        def _offer_recovery():
            try:
                from .features.recovery import offer_at_startup
                offer_at_startup(win)
            except Exception as e:  # noqa: BLE001
                win.log(f"[recovery] {e}")
        QTimer.singleShot(300, _offer_recovery)
    # smoke tests of release builds: run a script with win/app - only in test runs (RADIDE-TEST settings),
    # never in a normal user session
    try:                               # opt-in automation channel (RADIDE_AUTOMATION / --automation), off by default
        from .automation import maybe_start, requested
        if requested(opts.automation):
            maybe_start(win, app, opts.automation)
    except Exception as e:  # noqa: BLE001
        win.log(f"*** [automation] {e}")
    hook = os.environ.get("RADIDE_STARTUP_SCRIPT")
    if hook and Path(hook).is_file() and QCoreApplication.organizationName().upper().startswith("RADIDE-TEST"):
        QTimer.singleShot(0, lambda: exec(compile(Path(hook).read_text(encoding="utf-8"), hook, "exec"),  # noqa: S102
                                          {"win": win, "app": app, "__file__": hook}))
    return app.exec()
