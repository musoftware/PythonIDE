"""Solutions in the IDE (docs/CONTRACTS.md section 7.3) - the Visual Studio model.

A solution holds several projects, each in one language. A project uses another one through
**Add Reference** and then calls the library's public functions as code of its own language
(proxy files written by ``radide.references``; RAD Hub is the hidden transport).

This module draws the Solution Explorer (Solution 'X' > projects, StartUp Project in bold >
References > forms / modules), its context menus, the Add Reference dialog (Projects /
Packages / Browse), Set as StartUp Project, Build Solution, Add New / Existing Project,
Remove from solution and Solution Properties. ``radide/app.py`` calls fill_tree,
solution_menu, prepare_run, refresh_consumers and create_project_from_dialog.
"""
from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
                             QMessageBox, QPushButton, QStyle, QTabWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)

from ..languages import get_plugin, language_label, plugin_for_form, plugin_for_module
from ..model import Project

ROLE = Qt.ItemDataRole.UserRole
PROJECT_ROLE = Qt.ItemDataRole.UserRole + 10     # normalised folder of the project an item belongs to
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

LIBRARY_CANNOT_START = ("A project with an Output Type of Class Library cannot be started directly.\n\n"
                        "In order to run this project, add an application project to this solution which "
                        "references the library project, and set the application project as the "
                        "StartUp Project (right-click it > Set as StartUp Project).")


# ============================================================================ helpers
def _log(win, text: str) -> None:
    try:
        win.log(text)
    except Exception:  # noqa: BLE001
        pass


def _icon(win, name: str):
    return win.style().standardIcon(getattr(QStyle.StandardPixmap, name))


# VS Code file icon themes (radide/vsx/contrib_icons.py): fn(name, is_dir, expanded, root, strict) -> QIcon | None
FILE_ICON_PROVIDER = None


def file_icon(win, name: str, is_dir: bool = False, fallback: str = "SP_FileIcon", expanded: bool = False,
              strict: bool = False):
    """The icon of a file / folder item: the active file icon theme's, else the IDE's own (*fallback*).
    strict = only an explicit match of the icon theme (no generic "file" icon)."""
    fn = FILE_ICON_PROVIDER
    if fn is not None:
        try:
            ic = fn(name, is_dir, expanded, False, strict)
            if ic is not None:
                return ic
        except Exception:  # noqa: BLE001 - an icon theme must never break Solution Explorer
            pass
    return _icon(win, fallback)


def _plugin(project):
    try:
        return get_plugin(project.language)
    except KeyError:
        return None


def _kind_label(project) -> str:
    if getattr(project, "kind", "") == "website":
        return "Web Site"
    return "Class Library" if project.is_library else "Application"


def _ensure_solution(win):
    """The open solution (an implicit one-project solution is fine)."""
    if win.sln is None:
        raise RuntimeError("no solution is open")
    return win.sln


def _save_solution(win) -> None:
    """Write the .radsln when the solution is (or becomes) more than one bare project."""
    sln = win.sln
    if sln is None:
        return
    if not sln.implicit or len(sln.projects) > 1:
        was_implicit = sln.implicit
        sln.save()
        if was_implicit:
            win._remember(sln.file)


# ============================================================================ Solution Explorer
def fill_tree(win) -> None:
    tree = win.solution
    tree.clear()
    sln = win.sln
    if win.project is None:
        return
    if sln is None:                       # (should not happen) - show the active project alone
        from ..solution import Solution
        sln = Solution.implicit_for(win.project.folder)
    n = len(sln.projects)
    root = QTreeWidgetItem([f"Solution '{sln.name}' ({n} project{'s' if n != 1 else ''})"])
    root.setData(0, ROLE, ("solution", sln.name))
    root.setIcon(0, _icon(win, "SP_DriveHDIcon"))
    startup = sln.startup_project()
    bold = QFont()
    bold.setBold(True)
    for entry in sln.projects:
        project = sln.project(entry.name)
        if project is None:
            it = QTreeWidgetItem(root, [f"{entry.name}  (unavailable)"])
            it.setData(0, ROLE, ("missing", entry.name))
            it.setForeground(0, Qt.GlobalColor.gray)
            it.setIcon(0, _icon(win, "SP_MessageBoxWarning"))
            it.setToolTip(0, f"The project file was not found: {sln._abs(entry.path)}")
            continue
        try:
            st = win._state_for(project)
        except KeyError:
            it = QTreeWidgetItem(root, [f"{entry.name}  (unknown language {project.language})"])
            it.setData(0, ROLE, ("missing", entry.name))
            continue
        _fill_project(win, sln, root, entry.name, project, st["plugin"], project is startup, bold)
    tree.addTopLevelItem(root)
    post = getattr(sln, "after_fill_tree", None)        # foreign solutions: solution folders, items
    if callable(post):
        try:
            post(win, root)
        except Exception as e:  # noqa: BLE001
            _log(win, f"[solution] {e}")
    tree.expandAll()
    try:                                  # website folder trees: collapse folders (CONTRACTS 8.1)
        from .web_workspace import after_fill
        after_fill(win)
    except Exception as e:  # noqa: BLE001
        _log(win, f"[web] {e}")
    for hook in list(TREE_HOOKS):         # e.g. VS Code file icon themes for foreign project trees
        try:
            hook(win, root)
        except Exception as e:  # noqa: BLE001
            _log(win, f"[solution] tree hook: {e}")


# callables(win, root_item) run after Solution Explorer was filled (radide/vsx/contrib_runtime.py)
TREE_HOOKS: list = []


def _fill_project(win, sln, root, name, project, plugin, is_startup, bold) -> None:
    key = win._pkey(project)
    label = f"{name}  [{language_label(plugin)}]" + ("  (library)" if project.is_library else "")
    pi = QTreeWidgetItem(root, [label])
    pi.setData(0, ROLE, ("project", name))
    pi.setData(0, PROJECT_ROLE, key)
    pi.setIcon(0, _icon(win, "SP_DirIcon"))
    pi.setToolTip(0, f"{_kind_label(project)} - {plugin.display_name}\n{project.folder}" +
                  ("\nStartUp Project" if is_startup else ""))
    if is_startup:
        pi.setFont(0, bold)
    if getattr(project, "kind", "") == "website":      # web site: its folder tree (CONTRACTS 8.1)
        from .web_workspace import fill_site
        fill_site(win, pi, project)
        return
    own_tree = getattr(project, "fill_solution_tree", None)   # foreign projects (radide/foreign/*): own tree
    if callable(own_tree):
        own_tree(win, pi, name)
        return
    # References
    refs = QTreeWidgetItem(pi, ["References"])
    refs.setData(0, ROLE, ("references", name))
    refs.setData(0, PROJECT_ROLE, key)
    refs.setIcon(0, _icon(win, "SP_FileLinkIcon"))
    for ref in project.references:
        lib = sln.project(ref)
        lp = _plugin(lib) if lib is not None else None
        text = f"{ref}  [{language_label(lp)}]" if lp is not None else f"{ref}  (missing)"
        ri = QTreeWidgetItem(refs, [text])
        ri.setData(0, ROLE, ("reference", ref))
        ri.setData(0, PROJECT_ROLE, key)
        ri.setIcon(0, _icon(win, "SP_FileLinkIcon" if lib is not None else "SP_MessageBoxWarning"))
        ri.setToolTip(0, f"{name} uses {ref}: call its functions as {ref}.Function(...)" if lib is not None
                      else f"'{ref}' is not in the solution")
        for rel in project.reference_files.get(ref, []):
            fi = QTreeWidgetItem(ri, [f"{rel}  (generated)"])
            fi.setData(0, ROLE, ("proxy", rel))
            fi.setData(0, PROJECT_ROLE, key)
            fi.setForeground(0, Qt.GlobalColor.gray)
    # forms and modules (each in its own language)
    langs = {plugin_for_form(project, f).id for f in project.forms} | \
            {plugin_for_module(project, m).id for m in project.modules}
    multi = len(langs) > 1
    missing_forms = set(project.missing_forms()) if hasattr(project, "missing_forms") else set()
    for form in project.forms:
        fp = plugin_for_form(project, form)
        tag = f"  [{language_label(fp)}]" if multi else ""
        if form in missing_forms:                  # listed in project.radproj, no .form file
            fi = QTreeWidgetItem(pi, [f"{form}.form{tag}  (missing)"])
            fi.setData(0, ROLE, ("missing_form", form))
            fi.setData(0, PROJECT_ROLE, key)
            fi.setForeground(0, Qt.GlobalColor.gray)
            fi.setIcon(0, _icon(win, "SP_MessageBoxWarning"))
            fi.setToolTip(0, f"The form file was not found: {project.form_path(form)}\n"
                             "Right-click > Remove from Project")
            continue
        fi = QTreeWidgetItem(pi, [f"{form}.form{tag}" + ("   (startup)" if form == project.startup else "")])
        fi.setData(0, ROLE, ("design", form))
        fi.setData(0, PROJECT_ROLE, key)
        fi.setIcon(0, _icon(win, "SP_TitleBarNormalButton"))
        ci = QTreeWidgetItem(fi, [fp.code_file(form) + tag])
        ci.setData(0, ROLE, ("code", form))
        ci.setData(0, PROJECT_ROLE, key)
        ci.setIcon(0, file_icon(win, fp.code_file(form)))
        di = QTreeWidgetItem(fi, [fp.designer_file(form) + "  (generated)"])
        di.setForeground(0, Qt.GlobalColor.gray)
        di.setData(0, ROLE, ("generated", form))
        di.setData(0, PROJECT_ROLE, key)
    for mod in project.modules:
        tag = f"  [{language_label(plugin_for_module(project, mod))}]" if multi else ""
        mi = QTreeWidgetItem(pi, [mod + tag])
        mi.setData(0, ROLE, ("module", mod))
        mi.setData(0, PROJECT_ROLE, key)
        mi.setIcon(0, file_icon(win, mod))


def tree_items(win) -> list[tuple[int, str, tuple]]:
    """(depth, text, data) of every Solution Explorer item - handy for tests and tools."""
    out = []

    def walk(it, depth):
        out.append((depth, it.text(0), tuple(it.data(0, ROLE) or ())))
        for i in range(it.childCount()):
            walk(it.child(i), depth + 1)
    for i in range(win.solution.topLevelItemCount()):
        walk(win.solution.topLevelItem(i), 0)
    return out


def find_item(win, kind: str, name: str, project: str | None = None):
    """The tree item with data (kind, name) [in project *project*]."""
    key = None
    if project is not None and win.sln is not None:
        p = win.sln.project(project)
        key = win._pkey(p) if p is not None else None
    stack = [win.solution.topLevelItem(i) for i in range(win.solution.topLevelItemCount())]
    while stack:
        it = stack.pop(0)
        data = it.data(0, ROLE)
        if data and data[0] == kind and str(data[1]).lower() == str(name).lower() and \
                (key is None or it.data(0, PROJECT_ROLE) == key):
            return it
        stack.extend(it.child(i) for i in range(it.childCount()))
    return None


# ============================================================================ context menus
def _item_project(win, item):
    key = item.data(0, PROJECT_ROLE) if item is not None else None
    st = win._pstates.get(key) if key else None
    return st["project"] if st else None


def build_menu(win, item) -> QMenu | None:
    """The Solution Explorer context menu for *item* (None = empty space = the solution).
    Returns None for form/module items (the window's basic menu handles them)."""
    data = item.data(0, ROLE) if item is not None else None
    kind, name = (data[0], data[1]) if data else ("solution", "")
    project = _item_project(win, item)
    if project is not None:
        win.activate_project(project)
    sln = win.sln
    if kind in ("webfile", "webfolder", "webplaceholder") or (kind == "project" and project is not None and
                                                             getattr(project, "kind", "") == "website"):
        from .web_workspace import build_site_menu       # CONTRACTS 8.1
        return build_site_menu(win, item, kind, name, project)
    own_menu = getattr(sln, "build_solution_menu", None) if kind == "solution" else \
        getattr(project, "build_solution_menu", None)    # foreign projects/solutions (radide/foreign/*)
    if callable(own_menu):
        m = own_menu(win, item, kind, name)
        if m is not None:
            return m
    m = QMenu(win)
    if kind == "solution":
        add = m.addMenu("Add")
        add.addAction("New Project...", lambda: new_project_in_solution(win))
        add.addAction("Existing Project...", lambda: add_existing_project(win))
        sub = m.addMenu("Set StartUp Project")
        for e in (sln.projects if sln else []):
            a = sub.addAction(e.name, lambda n=e.name: set_startup_project(win, n))
            a.setCheckable(True)
            a.setChecked(sln.startup.lower() == e.name.lower())
        m.addSeparator()
        m.addAction("Build Solution", lambda: build_solution(win))
        m.addAction("Refresh References", lambda: refresh_references(win))
        m.addSeparator()
        m.addAction(win.a_run)
        m.addAction(win.a_run_nodebug)
        m.addSeparator()
        m.addAction("Save All", win.save_all)
        m.addAction("Open Folder in File Explorer", lambda: _open_folder(sln.folder if sln else None))
        m.addSeparator()
        m.addAction("Properties", lambda: solution_properties(win))
    elif kind == "project":
        a = m.addAction("Set as StartUp Project", lambda: set_startup_project(win, name))
        a.setEnabled(sln is not None and sln.startup.lower() != name.lower())
        m.addAction("Build", lambda: build_solution(win, only=[name]))
        m.addSeparator()
        add = m.addMenu("Add")
        add.addAction("Windows Form...", win.add_form)
        add.addAction("Module...", win.add_module)
        add.addAction("Existing Item...", win.add_existing)
        add.addSeparator()
        add.addAction("Reference...", lambda: add_reference_dialog(win, project))
        if getattr(win, "a_manage_packages", None) is not None:
            m.addAction("Manage Packages...", lambda: win.a_manage_packages.trigger())
        m.addSeparator()
        m.addAction("Remove from Solution", lambda: remove_project(win, name))
        m.addAction("Open Folder in File Explorer", lambda: _open_folder(project.folder if project else None))
        m.addSeparator()
        m.addAction("Properties", win.project_properties)
    elif kind == "references":
        m.addAction("Add Reference...", lambda: add_reference_dialog(win, project))
        m.addAction("Refresh References", lambda: refresh_references(win, [project]))
    elif kind == "reference":
        m.addAction("Open", lambda: open_reference(win, name))
        m.addSeparator()
        m.addAction("Remove", lambda: remove_reference(win, project, name))
    elif kind == "proxy":
        m.addAction("View (generated)", lambda: open_proxy(win, name))
    elif kind == "missing":
        m.addAction("Remove from Solution", lambda: remove_project(win, name))
    elif kind == "missing_form":
        m.addAction("Remove from Project", lambda: remove_missing_form(win, project, name))
    else:
        m.deleteLater()
        return None
    return m


MENU_HOOKS: list = []      # hook(win, item, menu) - runs before every Solution Explorer menu opens (project_menus)


def apply_menu_hooks(win, item, m) -> None:
    for hook in list(MENU_HOOKS):
        try:
            hook(win, item, m)
        except Exception as e:  # noqa: BLE001 - a hook must not break the menu
            _log(win, f"[solution] menu hook: {e}")


def solution_menu(win, pos) -> None:
    item = win.solution.itemAt(pos)
    m = build_menu(win, item)
    if m is None:
        win._basic_solution_menu(pos)
        return
    apply_menu_hooks(win, item, m)
    m.exec(win.solution.viewport().mapToGlobal(pos))


def _open_folder(folder) -> None:
    if folder is not None and Path(folder).exists():
        os.startfile(str(folder))  # noqa: S606 - Windows Explorer


# ============================================================================ actions
def remove_missing_form(win, project, form: str) -> bool:
    """Remove a form whose .form file is missing from project.radproj (Solution Explorer)."""
    project = project or win.project
    if project is None or form not in project.forms:
        return False
    project.forms.remove(form)
    project.form_languages.pop(form, None)
    if project.startup == form:
        project.startup = project.forms[0] if project.forms else ""
    project.save()
    fill_tree(win)
    _log(win, f"Removed the missing form '{form}' from project '{project.name}'")
    return True


def set_startup_project(win, name: str) -> None:
    sln = _ensure_solution(win)
    sln.set_startup(name)
    _save_solution(win)
    fill_tree(win)
    _log(win, f"StartUp Project: {sln.startup}")


def open_reference(win, name: str) -> None:
    """Double-click on a reference: open the library's first module (or form)."""
    sln = win.sln
    lib = sln.project(name) if sln is not None else None
    if lib is None:
        return
    win.activate_project(lib)
    if lib.modules:
        win.open_module(lib.modules[0])
    elif lib.forms:
        win.open_code(lib.startup if lib.startup in lib.forms else lib.forms[0])


def open_proxy(win, rel: str) -> None:
    """Show a generated proxy file read-only."""
    from ..editor import make_editor
    path = Path(win.project.folder) / rel
    plugin = plugin_for_module(win.project, path.name)
    ed = make_editor(plugin, path)
    ed.setText(path.read_text(encoding="utf-8") if path.exists() else "")
    ed.setReadOnly(True)
    win._show_tab(ed, f"{path.name} [generated]")


def refresh_references(win, projects=None) -> dict:
    """Regenerate the proxy files of the references (all projects, or *projects*)."""
    from ..references import refresh_all, update_proxies
    sln = _ensure_solution(win)
    if projects is None:
        out = refresh_all(sln, log=lambda t: _log(win, t))
    else:
        out = {}
        for p in projects:
            if p is not None:
                files = update_proxies(sln, p, log=lambda t: _log(win, t))
                if files:
                    out[sln.name_of(p)] = files
    fill_tree(win)
    return out


def refresh_consumers(win, libraries) -> None:
    """After a library was saved: projects that reference it get fresh proxies."""
    from ..references import update_proxies
    sln = win.sln
    if sln is None:
        return
    names = {sln.name_of(lib).lower() for lib in libraries}
    changed = False
    for p in sln.all_projects():
        if any(r.lower() in names for r in p.references):
            try:
                changed |= bool(update_proxies(sln, p, log=lambda t: _log(win, t)))
            except Exception as e:  # noqa: BLE001 - saving must never fail because of a proxy
                _log(win, f"*** cannot update the references of {p.name}: {e}")
    if changed:
        fill_tree(win)


def prepare_run(win) -> bool:
    """Before Run/Debug: activate the StartUp Project and refresh the reference proxies."""
    sln = win.sln
    sp = sln.startup_project()
    if sp is None:
        _log(win, "*** The solution has no project to start")
        return False
    if sp.is_library:
        _log(win, "*** " + LIBRARY_CANNOT_START.replace("\n\n", " "))
        if os.environ.get("QT_QPA_PLATFORM", "") != "offscreen":
            QMessageBox.information(win, "RAD IDE", LIBRARY_CANNOT_START)
        return False
    win.activate_project(sp)
    try:
        from ..references import refresh_all
        if any(p.references or p.reference_files for p in sln.all_projects()):
            if refresh_all(sln, log=lambda t: _log(win, t)):
                fill_tree(win)
    except Exception as e:  # noqa: BLE001
        _log(win, f"*** cannot update the references: {e}")
    return True


# ---------------------------------------------------------------- references
def add_reference(win, project, lib: str) -> list[Path]:
    """*project* references *lib* (another project of the solution). Raises ValueError."""
    from ..workspace import add_reference as ws_add
    sln = _ensure_solution(win)
    files = ws_add(sln, project, lib, log=lambda t: _log(win, t))
    _log(win, f"{sln.name_of(project)}: added reference to {sln.name_of(lib)}" +
         (f" ({', '.join(f.name for f in files)})" if files else ""))
    fill_tree(win)
    return files


def remove_reference(win, project, lib: str) -> None:
    from ..workspace import remove_reference as ws_remove
    sln = _ensure_solution(win)
    ws_remove(sln, project, lib, log=lambda t: _log(win, t))
    _log(win, f"{sln.name_of(project)}: removed reference to {lib}")
    fill_tree(win)


class AddReferenceDialog(QDialog):
    """Reference Manager: Projects (check the projects to reference) / Packages / Browse."""

    def __init__(self, win, project):
        super().__init__(win)
        self.win, self.project = win, project
        self.sln = _ensure_solution(win)
        pname = self.sln.name_of(project)
        self.setWindowTitle(f"Reference Manager - {pname}")
        self.resize(560, 420)
        self.tabs = QTabWidget()
        # Projects
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addWidget(QLabel(f"Projects of solution '{self.sln.name}' that <b>{pname}</b> can use. Their public "
                             "functions are called as normal code of the project's language "
                             "(e.g. <code>MathLib.Add(2, 3)</code>)."))
        lay.itemAt(0).widget().setWordWrap(True)
        self.list = QListWidget()
        lay.addWidget(self.list, 1)
        self.tabs.addTab(page, "Projects")
        # Packages
        page = QWidget()
        lay = QVBoxLayout(page)
        plugin = _plugin(project)
        pm = getattr(plugin, "package_manager", None) if plugin else None
        lay.addWidget(QLabel(f"Libraries from the {pm.name} package manager are installed into the project "
                             f"({pm.manifest or 'its manifest'})." if pm else
                             f"{plugin.display_name if plugin else project.language} has no package manager."))
        self.btn_packages = QPushButton("Manage Packages...")
        self.btn_packages.setEnabled(pm is not None)
        self.btn_packages.clicked.connect(self._packages)
        lay.addWidget(self.btn_packages)
        lay.addStretch(1)
        self.tabs.addTab(page, "Packages")
        # Browse
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addWidget(QLabel("Add an existing RAD IDE project (a folder with project.radproj) to the solution "
                             "and reference it."))
        row = QHBoxLayout()
        self.browse_path = QLineEdit()
        b = QPushButton("Browse...")
        b.clicked.connect(self._browse)
        row.addWidget(self.browse_path, 1)
        row.addWidget(b)
        lay.addLayout(row)
        self.btn_add_browse = QPushButton("Add to Solution and Reference")
        self.btn_add_browse.clicked.connect(lambda: self._add_browsed())
        lay.addWidget(self.btn_add_browse)
        lay.addStretch(1)
        self.tabs.addTab(page, "Browse")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._ok)
        buttons.rejected.connect(self.reject)
        main = QVBoxLayout(self)
        main.addWidget(self.tabs, 1)
        main.addWidget(buttons)
        self._fill()

    def _fill(self):
        self.list.clear()
        for e in self.sln.projects:
            if e.name.lower() == self.sln.name_of(self.project).lower():
                continue
            p = self.sln.project(e.name)
            if p is None:
                continue
            plugin = _plugin(p)
            it = QListWidgetItem(f"{e.name}    ({plugin.display_name if plugin else p.language}, "
                                 f"{_kind_label(p)})")
            it.setData(ROLE, e.name)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            on = self.project.references_project(e.name)
            it.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
            if not on and self.sln.would_create_cycle(self.project, e.name):
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                it.setToolTip(f"{e.name} already references {self.sln.name_of(self.project)} "
                              "(circular reference)")
            self.list.addItem(it)

    # ------------------------------------------------------------ API (also used by tests)
    def names(self) -> list[str]:
        return [self.list.item(i).data(ROLE) for i in range(self.list.count())]

    def _item(self, name: str):
        for i in range(self.list.count()):
            if self.list.item(i).data(ROLE).lower() == name.lower():
                return self.list.item(i)
        return None

    def check(self, name: str, on: bool = True) -> bool:
        it = self._item(name)
        if it is None or not (it.flags() & Qt.ItemFlag.ItemIsEnabled):
            return False
        it.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
        return True

    def checked(self) -> list[str]:
        return [self.list.item(i).data(ROLE) for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.CheckState.Checked]

    def apply(self) -> tuple[list[str], list[str]]:
        """Add / remove references to match the check boxes. Returns (added, removed)."""
        want = {n.lower(): n for n in self.checked()}
        have = {r.lower(): r for r in self.project.references}
        added, removed = [], []
        for low, name in want.items():
            if low not in have:
                try:
                    add_reference(self.win, self.project, name)
                    added.append(name)
                except ValueError as e:
                    QMessageBox.warning(self, "Add Reference", str(e))
        for low, name in have.items():
            if low not in want and self.sln.entry(name) is not None:
                remove_reference(self.win, self.project, name)
                removed.append(name)
        return added, removed

    def add_browsed(self, path) -> str | None:
        """Add the project at *path* to the solution (if needed) and check it. Returns its name."""
        p = add_existing_project(self.win, Path(path), activate=False)
        if p is None:
            return None
        name = self.sln.name_of(p)
        self._fill()
        self.check(name, True)
        self.tabs.setCurrentIndex(0)
        return name

    # ------------------------------------------------------------ slots
    def _packages(self):
        self.win.activate_project(self.project)
        from .packages import manage_packages
        manage_packages(self.win)

    def _browse(self):
        f, _ = QFileDialog.getOpenFileName(self, "Add Existing Project", str(self.sln.folder),
                                           f"RAD IDE project ({Project.FILE})")
        if f:
            self.browse_path.setText(str(Path(f).parent))

    def _add_browsed(self):
        if self.browse_path.text().strip():
            self.add_browsed(self.browse_path.text().strip())

    def _ok(self):
        self.apply()
        self.accept()


def add_reference_dialog(win, project=None, exec_: bool = True):
    project = project or win.project
    if project is None or win.sln is None:
        return None
    dlg = AddReferenceDialog(win, project)
    if exec_:
        dlg.exec()
    return dlg


# ---------------------------------------------------------------- projects
def create_project_from_dialog(win, dlg):
    """Create the project chosen in the New Project dialog (new solution or the open one)."""
    from ..workspace import (add_project_to_solution, create_library_project, create_project,
                             create_solution)
    name, language, template = dlg.name.text().strip(), dlg.language(), dlg.template_id_value()
    folder = dlg.folder()
    adding = dlg.adding_to_solution() and win.sln is not None
    try:
        if getattr(get_plugin(language), "project_kind", "") == "website":     # CONTRACTS 8.1
            from ..web_site.project import create_website
            project = create_website(folder, name, language, template)
        elif callable(getattr(get_plugin(language), "create_new_project", None)):   # games (CONTRACTS 10.2)
            project = get_plugin(language).create_new_project(folder, name, template)
        elif template == "library":
            project = create_library_project(folder, name, language)
        else:
            project = create_project(folder, name, language)
            if template not in ("", "windows"):
                from .templates import apply_template
                apply_template(folder, template)
                project = Project.load(folder)
    except Exception as e:  # noqa: BLE001 - show any error
        QMessageBox.critical(win, "New Project", f"Cannot create the project:\n{e}")
        return None
    if not adding:
        sln = create_solution(dlg.solution_folder(), dlg.solution_title())
        add_project_to_solution(sln, project)
        win.open_project(sln.file)
        return win.sln.project(name) if win.sln is not None else project
    win.save_all()
    sln = win.sln
    was_implicit = sln.implicit
    project = add_project_to_solution(sln, project)
    if was_implicit:
        win._remember(sln.file)
    _open_new_project(win, project)
    _log(win, f"Added project '{project.name}' ({get_plugin(project.language).display_name}) to solution "
              f"'{sln.name}'")
    return project


def _open_new_project(win, project) -> None:
    win._state_for(project)
    win.activate_project(project)
    fill_tree(win)
    if project.forms:
        win.open_designer(project.startup if project.startup in project.forms else project.forms[0])
    elif project.modules:
        win.open_module(project.modules[0])
    win._update_actions()


def new_project_in_solution(win):
    """Solution > Add > New Project..."""
    from ..dialogs import NewProjectDialog
    dlg = NewProjectDialog(win)
    dlg.set_adding_to_solution(True)
    if not dlg.exec():
        return None
    win._pending_template = None
    return create_project_from_dialog(win, dlg)


def add_existing_project(win, path=None, activate: bool = True):
    """Solution > Add > Existing Project...: *path* = project folder or project.radproj."""
    from ..workspace import add_project_to_solution
    sln = _ensure_solution(win)
    if path is None:
        f, _ = QFileDialog.getOpenFileName(win, "Add Existing Project", str(sln.folder),
                                           f"RAD IDE project ({Project.FILE})")
        if not f:
            return None
        path = Path(f)
    path = Path(path)
    if path.is_file():
        path = path.parent
    existing = sln.project_for_folder(path)
    if existing is not None:
        return existing
    was_implicit = sln.implicit
    try:
        project = add_project_to_solution(sln, path)
        get_plugin(project.language)
    except Exception as e:  # noqa: BLE001
        QMessageBox.warning(win, "Add Existing Project", f"Cannot add the project:\n{e}")
        return None
    if was_implicit:
        win._remember(sln.file)
    if activate:
        _open_new_project(win, project)
    else:
        win._state_for(project)
        fill_tree(win)
    _log(win, f"Added existing project '{sln.name_of(project)}' to solution '{sln.name}'")
    return project


def remove_project(win, name: str, confirm: bool = True) -> bool:
    from ..workspace import remove_project_from_solution
    sln = _ensure_solution(win)
    if len(sln.projects) <= 1:
        QMessageBox.information(win, "Remove Project", "The last project of a solution cannot be removed.")
        return False
    if confirm and QMessageBox.question(
            win, "Remove Project", f"Remove '{name}' from solution '{sln.name}'?\n"
            "(The project's files stay on disk. References to it are removed.)") \
            != QMessageBox.StandardButton.Yes:
        return False
    win.save_all()
    project = sln.project(name)
    changed = remove_project_from_solution(sln, name)
    if project is not None:
        win._forget_project(project)
    fill_tree(win)
    win._update_actions()
    _log(win, f"Removed project '{name}' from the solution" +
         (f" (references removed from {', '.join(p.name for p in changed)})" if changed else ""))
    return True


# ---------------------------------------------------------------- build
def _build_commands(win, only=None) -> list[tuple[Project, object, str]]:
    sln = _ensure_solution(win)
    try:
        order = sln.build_order()
    except ValueError as e:
        _log(win, f"*** {e}")
        order = sln.all_projects()
    out = []
    names = {n.lower() for n in only} if only else None
    for p in order:
        if names is not None and sln.name_of(p).lower() not in names:
            continue
        plugin = _plugin(p)
        if plugin is None or not hasattr(plugin, "build_command"):
            out.append((p, plugin, ""))
            continue
        if not p.is_library and names is None:
            out.append((p, plugin, ""))        # applications are built when they run
            continue
        try:
            if hasattr(plugin, "prepare"):
                plugin.prepare(Path(p.folder), p)
            cmd = plugin.build_command(Path(p.folder), p) or ""
        except Exception as e:  # noqa: BLE001
            cmd = ""
            _log(win, f"*** {sln.name_of(p)}: cannot prepare the build: {e}")
        out.append((p, plugin, cmd))
    return out


def build_solution(win, only=None, wait: bool = False):
    """Build > Build Solution: save, refresh the reference proxies, then run the build command of
    every library whose plugin compiles (C#, Java, C, Rust, ...). *wait* = run in this thread and
    return {project name: exit code} (None for projects that need no build)."""
    sln = _ensure_solution(win)
    own_build = getattr(sln, "build_solution", None)      # foreign solutions (.sln: dotnet / MSBuild)
    if callable(own_build):
        return own_build(win, only=only, wait=wait)
    win.save_all()
    try:
        from ..references import refresh_all
        refresh_all(sln, log=lambda t: _log(win, t))
    except Exception as e:  # noqa: BLE001
        _log(win, f"*** cannot update the references: {e}")
    fill_tree(win)
    jobs = _build_commands(win, only)
    emit = getattr(win, "_hub_log", None)
    say = (lambda t: emit.emit(t)) if emit is not None and not wait else (lambda t: _log(win, t.rstrip("\n")))
    _log(win, f"------ Build started: solution '{sln.name}' ------")

    def run() -> dict:
        results: dict[str, int | None] = {}
        for p, plugin, cmd in jobs:
            name = sln.name_of(p)
            if not cmd:
                results[name] = None
                say(f"{name}: nothing to build ({plugin.display_name if plugin else p.language})\n")
                continue
            say(f"{name}: {cmd}\n")
            try:
                proc = subprocess.run(cmd, shell=True, cwd=str(p.folder), capture_output=True,
                                      creationflags=NO_WINDOW, timeout=600)
                text = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
                if text.strip():
                    say(text if text.endswith("\n") else text + "\n")
                results[name] = proc.returncode
            except (OSError, subprocess.TimeoutExpired) as e:
                say(f"*** {name}: {e}\n")
                results[name] = -1
        ok = sum(1 for c in results.values() if c in (0, None))
        bad = sum(1 for c in results.values() if c not in (0, None))
        say(f"========== Build: {ok} succeeded, {bad} failed ==========\n")
        return results

    if wait:
        return run()
    threading.Thread(target=run, daemon=True, name="radide-build").start()
    return None


# ---------------------------------------------------------------- properties
def solution_properties(win) -> None:
    sln = _ensure_solution(win)
    dlg = QDialog(win)
    dlg.setWindowTitle(f"Solution '{sln.name}' Properties")
    lay = QFormLayout(dlg)
    name = QLineEdit(sln.name)
    lay.addRow("Solution name:", name)
    lay.addRow("File:", QLabel(str(sln.path) + ("   (not saved yet)" if sln.implicit else "")))
    startup = QComboBox()
    startup.addItems(sln.names())
    startup.setCurrentText(sln.startup_project().name if sln.startup_project() else "")
    if sln.startup:
        startup.setCurrentText(sln.startup)
    lay.addRow("StartUp Project:", startup)
    rows = []
    for p in sln.all_projects():
        plugin = _plugin(p)
        refs = ", ".join(p.references) or "-"
        rows.append(f"<tr><td><b>{sln.name_of(p)}</b></td><td>{plugin.display_name if plugin else p.language}"
                    f"</td><td>{_kind_label(p)}</td><td>{refs}</td></tr>")
    table = QLabel("<table cellspacing=6><tr><th align=left>Project</th><th align=left>Language</th>"
                   "<th align=left>Type</th><th align=left>References</th></tr>" + "".join(rows) + "</table>")
    lay.addRow("Projects:", table)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addRow(box)
    if not dlg.exec():
        return
    new = name.text().strip()
    if new and new != sln.name:
        try:
            sln.rename(new)
        except (OSError, ValueError) as e:
            QMessageBox.warning(win, "Solution Properties", str(e))
    if startup.currentText() and startup.currentText().lower() != sln.startup.lower():
        sln.set_startup(startup.currentText())
    _save_solution(win)
    fill_tree(win)
    win._update_title()


# ============================================================================ install
def _menu(win, title: str):
    return next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == title), None)


def install(win) -> None:
    from PyQt6.QtGui import QAction, QKeySequence
    file_menu = _menu(win, "File")
    if file_menu is not None:
        add = QMenu("A&dd", file_menu)
        add.addAction("&New Project...", lambda: win.sln and new_project_in_solution(win))
        add.addAction("&Existing Project...", lambda: win.sln and add_existing_project(win))
        acts = file_menu.actions()
        anchor = acts[acts.index(win.a_open) + 1] if win.a_open in acts and acts.index(win.a_open) + 1 < len(acts) \
            else None
        file_menu.insertMenu(anchor, add)
        win.menu_add_project = add
    proj = _menu(win, "Project")
    if proj is not None:
        acts = proj.actions()
        anchor = acts[3] if len(acts) > 3 else None
        a = QAction("Add &Reference...", win)
        a.triggered.connect(lambda: add_reference_dialog(win))
        proj.insertAction(anchor, a)
        win.a_add_reference = a
        a = QAction("Set as StartUp Pro&ject", win)
        a.triggered.connect(lambda: win.project and win.sln and set_startup_project(win, win.sln.name_of(win.project)))
        proj.insertAction(anchor, a)
        win.a_set_startup_project = a
    # Build menu (before Debug)
    debug = next((a for a in win.menuBar().actions() if a.text().replace("&", "") == "Debug"), None)
    build = QMenu("&Build", win)
    a = QAction("&Build Solution", win)
    a.setShortcut(QKeySequence("Ctrl+Shift+B"))
    a.triggered.connect(lambda: win.sln and build_solution(win))
    build.addAction(a)
    win.a_build_solution = a
    a = QAction("Build &Project", win)
    a.triggered.connect(lambda: win.sln and win.project and build_solution(win, only=[win.sln.name_of(win.project)]))
    build.addAction(a)
    build.addSeparator()
    a = QAction("&Refresh References", win)
    a.triggered.connect(lambda: win.sln and refresh_references(win))
    build.addAction(a)
    win.menuBar().insertMenu(debug, build) if debug is not None else win.menuBar().addMenu(build)
    win.build_menu = build


__all__ = ["AddReferenceDialog", "PROJECT_ROLE", "add_existing_project", "add_reference", "add_reference_dialog",
           "build_menu", "build_solution", "create_project_from_dialog", "fill_tree", "find_item",
           "new_project_in_solution", "prepare_run", "refresh_consumers", "refresh_references", "remove_project",
           "remove_reference", "set_startup_project", "solution_menu", "solution_properties", "tree_items"]
