"""Jupyter notebooks in the IDE (radide/notebook).

* .ipynb files opened from File > Open File, Solution Explorer, Quick Open ... open in the notebook editor.
* File > New Notebook: blank notebook, Data Science starter (pandas + matplotlib + a sample CSV),
  open a notebook, import a ``# %%`` Python script as a notebook.
* Notebook menu (shown while a notebook is the current tab): run / run all / run above / run below,
  interrupt, restart, clear outputs, export to .py / HTML, kernel picker, Variables window.
* View > Other Windows > Notebook Variables: the variables of the current notebook's kernel (name, type,
  size, value); double-click shows a variable (DataFrames as a table) in a new cell.
* IntelliSense in cells: the kernel's runtime completions + pylsp over all the notebook's code cells.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QDockWidget, QFileDialog, QLabel, QMessageBox, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

from .. import theme

NB_EXT = ".ipynb"


def _is_nb(path) -> bool:
    try:
        return Path(path).suffix.lower() == NB_EXT
    except TypeError:
        return False


class NotebookFeature:
    def __init__(self, win):
        self.win = win
        self.views: dict[str, object] = {}           # resolved lower-case path -> NotebookView
        self.dock: QDockWidget | None = None
        self.vars_tree: QTreeWidget | None = None
        self._bound = None
        self._make_menus()
        self._wrap()
        self._make_dock()
        win.tabs.currentChanged.connect(self._on_tab)
        try:
            from . import workbench
            workbench.register_view("notebook.variables", "Variables", icon="variables",
                                    factory=lambda w: getattr(w, "notebook_feature", None) and
                                    w.notebook_feature.dock, modes=("vscode", "agent"), area="panel", order=80,
                                    tooltip="Notebook Variables")
        except Exception:  # noqa: BLE001 - the workbench is optional
            pass

    # ------------------------------------------------------------------ menus
    def _menu(self, title: str):
        return next((a.menu() for a in self.win.menuBar().actions() if a.menu() is not None and
                     a.text().replace("&", "") == title), None)

    def _make_menus(self) -> None:
        win = self.win
        fm = getattr(win, "file_menu", None) or self._menu("File")
        if fm is not None:
            sub = fm.addMenu("New &Notebook")
            anchor = next((a for a in fm.actions() if a.menu() is not None and
                           a.text().replace("&", "").startswith("Recent")), None)
            if anchor is not None:
                fm.insertMenu(anchor, sub)
            sub.addAction("Blank Notebook (.ipynb)...", lambda: self.new_notebook("blank"))
            sub.addAction("Data Science Starter (pandas + matplotlib)...", lambda: self.new_notebook("datascience"))
            sub.addSeparator()
            sub.addAction("Open Notebook...", self.open_dialog)
            sub.addAction("Import Python Script as Notebook...", self.import_py)
        m = win.menuBar().addMenu("Note&book")
        self.menu = m
        m.menuAction().setVisible(False)
        A = m.addAction

        def cur(fn):
            return lambda: (lambda v: v is not None and fn(v))(self.current())
        A("Run Cell and Select Below\tShift+Enter", cur(lambda v: v.run_cell(v.selected, advance=True)))
        A("Run All", cur(lambda v: v.run_all()))
        A("Run Above", cur(lambda v: v.run_above()))
        A("Run Selected and Below", cur(lambda v: v.run_below()))
        m.addSeparator()
        A("Interrupt Kernel", cur(lambda v: v.interrupt()))
        A("Restart Kernel", cur(lambda v: v.restart(ask=True)))
        A("Restart Kernel and Run All", cur(lambda v: v.restart(ask=True, run_all=True)))
        A("Select Kernel...", cur(lambda v: (v.kernel_combo.setFocus(), v.kernel_combo.showPopup())))
        m.addSeparator()
        A("Insert Code Cell Below", cur(lambda v: v.add_cell("code")))
        A("Insert Markdown Cell Below", cur(lambda v: v.add_cell("markdown")))
        A("Clear All Outputs", cur(lambda v: v.clear_all_outputs()))
        m.addSeparator()
        A("Export as Python Script...", cur(lambda v: v.export_py()))
        A("Export as HTML...", cur(lambda v: v.export_html()))
        A("Save Notebook As...", cur(lambda v: v.save_as()))
        m.addSeparator()
        A("Variables Window", self.show_variables)
        vm = self._menu("View")
        if vm is not None:
            other = next((a.menu() for a in vm.actions() if a.menu() is not None and
                          a.text().replace("&", "").startswith("Other Windows")), None)
            (other or vm).addAction("Notebook &Variables", self.show_variables)

    # ------------------------------------------------------------------ window wrapping
    def _wrap(self) -> None:
        win = self.win
        orig_any = win.open_any_file
        orig_save_all = win.save_all
        orig_any_modified = win._any_modified

        def open_any_file(path, *a, **k):
            if _is_nb(path):
                return self.open_notebook(Path(path))
            return orig_any(path, *a, **k)
        win.open_any_file = open_any_file

        def save_all(*a, **k):
            self.save_all()
            return orig_save_all(*a, **k)
        win.save_all = save_all

        def any_modified(*a, **k):
            return any(v.is_modified() for v in self._views()) or orig_any_modified(*a, **k)
        win._any_modified = any_modified

        orig_close = win.closeEvent

        def close_event(e):
            orig_close(e)
            if e.isAccepted():
                self.shutdown_all()
        win.closeEvent = close_event
        win.open_notebook = self.open_notebook
        win.notebook_feature = self
        if getattr(win, "a_save_file", None) is not None:
            win.a_save_file.triggered.connect(lambda _c=False: self._save_current())
        for attr, op in (("a_undo", "undo"), ("a_redo", "redo"), ("a_cut", "cut"), ("a_copy", "copy"),
                         ("a_paste", "paste"), ("a_select_all", "select_all")):
            act = getattr(win, attr, None)
            if act is not None:
                act.triggered.connect(lambda _c=False, op=op: self._edit(op))
        QTimer.singleShot(0, self._wrap_open_file)      # after web_workspace installed win.open_file

    def _wrap_open_file(self) -> None:
        win = self.win
        orig = getattr(win, "open_file", None)
        if not callable(orig) or getattr(orig, "_rad_nb", False):
            return

        def open_file(path, *a, **k):
            p = Path(path)
            if not p.is_absolute() and getattr(win, "project", None) is not None:
                p = Path(win.project.folder) / p
            if _is_nb(p):
                return self.open_notebook(p)
            return orig(path, *a, **k)
        open_file._rad_nb = True
        win.open_file = open_file

    # ------------------------------------------------------------------ documents
    @staticmethod
    def _alive(w) -> bool:
        try:
            w.isVisible()
            return True
        except RuntimeError:
            return False

    def _views(self):
        return [v for v in self.views.values() if self._alive(v)]

    def current(self):
        from ..notebook.view import NotebookView
        try:
            w = self.win.tabs.currentWidget()
        except RuntimeError:
            return None
        return w if isinstance(w, NotebookView) else None

    def open_notebook(self, path: Path):
        from ..notebook.view import NotebookView
        win = self.win
        path = Path(path).resolve()
        key = str(path).lower()
        v = self.views.get(key)
        if v is not None and (not self._alive(v) or win.tabs.indexOf(v) < 0):
            if self._alive(v) and v.kernel is not None:
                v.shutdown_kernel()
            self.views.pop(key, None)
            v = None
        if v is None:
            try:
                v = NotebookView(path)
            except (OSError, ValueError) as e:
                QMessageBox.warning(win, "Notebook", f"Cannot open {path.name}:\n{e}")
                return None
            v.setToolTip(str(path))
            v.modifiedChanged.connect(lambda _m, v=v: self._title(v))
            v.saved.connect(lambda v=v: self._title(v))
            v.log.connect(win.log)
            v.variablesChanged.connect(lambda vars_, v=v: self._show_vars(v, vars_))
            v.kernelStatusChanged.connect(lambda s, v=v: self._status(v, s))
            self.views[key] = v
        win._show_tab(v, path.name)
        self._title(v)
        self._on_tab()
        return v

    def _title(self, v) -> None:
        i = self.win.tabs.indexOf(v)
        if i >= 0:
            self.win.tabs.setTabText(i, v.title() + ("*" if v.is_modified() else ""))
            self.win.tabs.setTabToolTip(i, str(v.path or ""))
        if v.path is not None:
            key = str(Path(v.path).resolve()).lower()
            if self.views.get(key) is not v:
                for k, vv in list(self.views.items()):
                    if vv is v:
                        self.views.pop(k)
                self.views[key] = v

    def _status(self, v, s: str) -> None:
        if v is self.current():
            self.win.statusBar().showMessage(f"Kernel {v.choice.label if v.choice else ''}: {s}", 3000)

    def save_all(self) -> None:
        for v in self._views():
            if v.is_modified() and v.path is not None:
                v.save()

    def _save_current(self) -> None:
        v = self.current()
        if v is not None:
            v.save()

    def _edit(self, op: str) -> None:
        v = self.current()
        if v is not None:
            v.edit_op(op)

    def shutdown_all(self) -> None:
        for v in self._views():
            try:
                v.shutdown_kernel()
            except Exception:  # noqa: BLE001
                pass

    def _on_tab(self, *_a) -> None:
        v = self.current()
        try:
            self.menu.menuAction().setVisible(v is not None)
        except RuntimeError:
            return
        if v is not None:
            self._show_vars(v, v.variables)

    # ------------------------------------------------------------------ commands
    def _ask_path(self, title: str, default_name: str) -> Path | None:
        start = Path(self.win.project.folder) if getattr(self.win, "project", None) is not None else Path.home()
        f, _ = QFileDialog.getSaveFileName(self.win, title, str(start / default_name), "Jupyter Notebook (*.ipynb)")
        if not f:
            return None
        p = Path(f)
        return p if p.suffix.lower() == NB_EXT else p.with_suffix(NB_EXT)

    def new_notebook(self, kind: str = "blank", path: Path | None = None):
        from ..notebook.model import SAMPLE_CSV, Notebook, data_science_starter
        if path is None:
            path = self._ask_path("New Notebook", "Analysis.ipynb" if kind == "datascience" else "Untitled.ipynb")
            if path is None:
                return None
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if kind == "datascience":
            nb = data_science_starter(path)
            csv = path.parent / "sales.csv"
            if not csv.exists():
                csv.write_text(SAMPLE_CSV, encoding="utf-8")
        else:
            nb = Notebook.new(path)
        nb.save(path)
        self.win.log(f"[notebook] created {path}")
        return self.open_notebook(path)

    def open_dialog(self) -> None:
        start = str(self.win.project.folder) if getattr(self.win, "project", None) is not None else ""
        f, _ = QFileDialog.getOpenFileName(self.win, "Open Notebook", start, "Jupyter Notebook (*.ipynb)")
        if f:
            self.open_notebook(Path(f))

    def import_py(self, src: Path | None = None, target: Path | None = None):
        from ..notebook.model import Notebook
        if src is None:
            f, _ = QFileDialog.getOpenFileName(self.win, "Import Python Script as Notebook", "", "Python (*.py)")
            if not f:
                return None
            src = Path(f)
        target = target or Path(src).with_suffix(NB_EXT)
        if target.exists() and QMessageBox.question(self.win, "Notebook", f"{target.name} exists. Replace it?") \
                != QMessageBox.StandardButton.Yes:
            return None
        nb = Notebook.from_py(Path(src).read_text(encoding="utf-8"), target)
        nb.save(target)
        return self.open_notebook(target)

    # ------------------------------------------------------------------ variables window
    def _make_dock(self) -> None:
        win = self.win
        dock = QDockWidget("Notebook Variables", win)
        dock.setObjectName("dock_notebook_variables")
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.vars_label = QLabel("Run a notebook cell to see its variables.")
        theme.role(self.vars_label, "muted")
        self.vars_label.setContentsMargins(6, 3, 6, 3)
        lay.addWidget(self.vars_label)
        t = QTreeWidget()
        t.setHeaderLabels(["Name", "Type", "Size", "Value"])
        t.setRootIsDecorated(False)
        t.setAlternatingRowColors(True)
        t.setSortingEnabled(True)
        t.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        t.setColumnWidth(0, 120)
        t.setColumnWidth(1, 90)
        t.setColumnWidth(2, 70)
        t.setAccessibleName("Notebook variables")
        t.itemDoubleClicked.connect(self._on_var_dclick)
        t.setToolTip("Double-click a variable to show it in a new cell (DataFrames as a table)")
        lay.addWidget(t, 1)
        dock.setWidget(w)
        self.vars_tree = t
        self.dock = dock
        win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        out = getattr(win, "dock_output", None)
        if out is not None:
            try:
                win.tabifyDockWidget(out, dock)
                out.raise_()
            except Exception:  # noqa: BLE001
                pass
        dock.hide()
        win.dock_notebook_variables = dock

    def show_variables(self) -> None:
        if self.dock is not None:
            self.dock.show()
            self.dock.raise_()
            v = self.current()
            if v is not None:
                v.refresh_variables()

    def _show_vars(self, v, vars_: list) -> None:
        if v is not self.current() or self.vars_tree is None:
            return
        t = self.vars_tree
        t.setSortingEnabled(False)
        t.clear()
        for name, typ, size, value in vars_ or []:
            it = QTreeWidgetItem([str(name), str(typ), str(size), str(value)])
            it.setToolTip(3, str(value))
            t.addTopLevelItem(it)
        t.setSortingEnabled(True)
        kernel = v.choice.label if v.choice else "no kernel"
        self.vars_label.setText(f"{v.title()} - {kernel}: {len(vars_ or [])} variables")

    def _on_var_dclick(self, item, _col) -> None:
        v = self.current()
        if v is not None:
            v.inspect_variable(item.text(0))


def _lsp_for_view(win):
    def factory(view):
        mgr = getattr(win, "lsp_manager", None)
        if mgr is None:
            return None
        root = Path(win.project.folder) if getattr(win, "project", None) is not None else \
            (view.path.parent if view.path else Path.cwd())
        return mgr.client_for("python", root)
    return factory


def install(win) -> None:
    try:
        from PyQt6 import QtWebEngineWidgets      # the notebook page needs QtWebEngine
        assert QtWebEngineWidgets
    except ImportError:
        win.log("[notebook] PyQt6-WebEngine is missing: Jupyter notebooks are not available")
        return
    from ..notebook.view import NotebookView
    NotebookView.lsp_factory = _lsp_for_view(win)
    NotebookFeature(win)
