"""Visual Studio 2022 solution dialogs: Configuration Manager, Project Dependencies / Build Order,
Solution Property Pages (Startup Project: single / multiple with Start / Start without debugging),
Add a new project, Add projects from another solution (checklist), New Solution from existing folders,
Publish (folder profiles).

Every dialog can be built without being shown (``exec_=False``) - tests drive the widgets and call
``dlg.apply()``.
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
                             QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                             QPushButton, QRadioButton, QStackedWidget, QTableWidget, QTableWidgetItem,
                             QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import ops
from .model import DOTNET_EXTS, SolutionDoc

ROLE = Qt.ItemDataRole.UserRole
OFFSCREEN = os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"
NEW, EDIT = "<New...>", "<Edit...>"
STD_PLATFORMS = ["Any CPU", "x64", "x86", "ARM64", "ARM"]


def _warn(parent, title: str, text: str) -> None:
    ops._log(parent if hasattr(parent, "log") else getattr(parent, "win", parent), f"*** {title}: {text}")
    if not OFFSCREEN:
        QMessageBox.warning(parent, title, text)


def _buttons(dlg, ok=True, cancel=True, close=False):
    flags = QDialogButtonBox.StandardButton(0)
    if ok:
        flags |= QDialogButtonBox.StandardButton.Ok
    if cancel:
        flags |= QDialogButtonBox.StandardButton.Cancel
    if close:
        flags |= QDialogButtonBox.StandardButton.Close
    box = QDialogButtonBox(flags)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    return box


def _project_configs(path: Path) -> list[str]:
    from .model import _project_configs_of
    return _project_configs_of(path) or ["Debug", "Release"]


def _project_platforms(path: Path, ext: str) -> list[str]:
    from .model import project_platforms_of
    pl = project_platforms_of(path)
    if ext in DOTNET_EXTS:
        pl = ["Any CPU" if p in ("AnyCPU", "Any CPU") else p for p in pl] or ["Any CPU"]
    return pl or ["Any CPU"]


# ====================================================================== Configuration Manager
class ConfigurationManager(QDialog):
    """Build > Configuration Manager..."""

    def __init__(self, win, sln):
        super().__init__(win)
        self.win, self.sln = win, sln
        self.doc = ops.doc_of(sln)
        self.changed = False
        self.setWindowTitle("Configuration Manager")
        self.resize(760, 420)
        lay = QVBoxLayout(self)
        top = QGridLayout()
        top.addWidget(QLabel("Active solution configuration:"), 0, 0)
        top.addWidget(QLabel("Active solution platform:"), 0, 1)
        self.cfg_combo, self.plat_combo = QComboBox(), QComboBox()
        top.addWidget(self.cfg_combo, 1, 0)
        top.addWidget(self.plat_combo, 1, 1)
        lay.addLayout(top)
        lay.addWidget(QLabel("Project contexts (check the project configurations to build or deploy):"))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Project", "Configuration", "Platform", "Build", "Deploy"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        lay.addWidget(self.table)
        box = _buttons(self, ok=False, cancel=False, close=True)
        box.rejected.connect(self.reject)
        lay.addWidget(box)
        self.active_cfg, self.active_plat = sln.configuration, sln.platform
        self._fill_combos()
        self._fill_table()
        self.cfg_combo.activated.connect(lambda _i: self._combo_pick(self.cfg_combo, "cfg"))
        self.plat_combo.activated.connect(lambda _i: self._combo_pick(self.plat_combo, "plat"))
        self.finished.connect(lambda _r: self.apply())

    # ------------------------------------------------------------------ fill
    def _fill_combos(self):
        for combo, values, cur in ((self.cfg_combo, self.doc.configurations(), self.active_cfg),
                                   (self.plat_combo, self.doc.platforms(), self.active_plat)):
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(values + [NEW, EDIT])
            combo.setCurrentText(cur if cur in values else values[0])
            combo.blockSignals(False)
        self.active_cfg, self.active_plat = self.cfg_combo.currentText(), self.plat_combo.currentText()

    def sol_cfg(self) -> str:
        return f"{self.active_cfg}|{self.active_plat}"

    def _fill_table(self):
        self.table.setRowCount(0)
        sc = self.sol_cfg()
        for e in self.doc.real_projects():
            if not e.buildable:
                continue
            r = self.table.rowCount()
            self.table.insertRow(r)
            it = QTableWidgetItem(e.name)
            it.setData(ROLE, e.guid)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, 0, it)
            pf = ops.project_entry_file(self.sln, e)
            pc = self.doc.project_config(e.guid, sc)
            cfgs = _project_configs(pf)
            plats = _project_platforms(pf, e.ext)
            cur_cfg = pc.cfg if pc else ""
            cur_plat = pc.plat if pc else ""
            for col, values, cur, what in ((1, cfgs, cur_cfg, "cfg"), (2, plats, cur_plat, "plat")):
                c = QComboBox()
                vals = list(dict.fromkeys(values + ([cur] if cur else [])))
                c.addItems(vals + [NEW])
                c.setCurrentText(cur or vals[0])
                c.activated.connect(lambda _i, c=c, g=e.guid, w=what: self._project_pick(c, g, w))
                self.table.setCellWidget(r, col, c)
            for col, val, what in ((3, pc.build if pc else False, "build"), (4, pc.deploy if pc else False, "deploy")):
                cb = QCheckBox()
                cb.setChecked(bool(val))
                cb.toggled.connect(lambda on, g=e.guid, w=what: self._set(g, **{w: on}))
                holder = QWidget()
                hl = QHBoxLayout(holder)
                hl.setContentsMargins(0, 0, 0, 0)
                hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                hl.addWidget(cb)
                self.table.setCellWidget(r, col, holder)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def row_of(self, name: str) -> int:
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).text().lower() == name.lower():
                return r
        return -1

    def cell(self, name: str, col: int):
        r = self.row_of(name)
        w = self.table.cellWidget(r, col) if r >= 0 else None
        if w is not None and col >= 3:
            return w.findChild(QCheckBox)
        return w

    # ------------------------------------------------------------------ edits
    def _set(self, guid, cfg=None, plat=None, build=None, deploy=None):
        self.doc.set_project_config(guid, self.sol_cfg(), cfg, plat, build, deploy)
        self.changed = True

    def _project_pick(self, combo, guid, what):
        val = combo.currentText()
        if val == NEW:
            name, ok = QInputDialog.getText(self, "New Project Configuration" if what == "cfg" else
                                            "New Project Platform", "Name:")
            if not ok or not name.strip():
                self._fill_table()
                return
            val = name.strip()
            self._add_project_level(guid, val, what)
        self._set(guid, **{what: val})
        self._fill_table()

    def _add_project_level(self, guid, name, what):
        """A new project configuration/platform: added to <Configurations>/<Platforms> of SDK projects."""
        e = self.doc.entry(guid)
        pf = ops.project_entry_file(self.sln, e)
        if e.ext not in DOTNET_EXTS:
            return
        from ...foreign.msbuild import MSBuildProject
        ms = MSBuildProject.load(pf)
        if not ms.is_sdk:
            return
        prop = "Configurations" if what == "cfg" else "Platforms"
        cur = ms.prop(prop) or ("Debug;Release" if what == "cfg" else "AnyCPU")
        names = [c for c in cur.split(";") if c]
        val = "AnyCPU" if name == "Any CPU" else name
        if val not in names:
            from . import msprops
            msprops.set_value(ms, prop, ";".join(names + [val]))
            ms.save()

    def new_solution_configuration(self, name: str, copy_from: str = "", create_project_configs: bool = True):
        if create_project_configs:
            added = self.doc.add_configuration(name, "")
            for e in self.doc.real_projects():
                if e.buildable:
                    self._add_project_level(e.guid, name, "cfg")
            if copy_from:                                   # copy Build/Deploy flags and platforms
                for sc in added:
                    src = f"{copy_from}|{sc.split('|')[1]}"
                    for e in self.doc.real_projects():
                        b = self.doc.mapping.get((e.guid, src))
                        if b is not None:
                            self.doc.set_project_config(e.guid, sc, name, b.plat, b.build, b.deploy)
        else:
            self.doc.add_configuration(name, copy_from or self.doc.configurations()[0])
        self.changed = True
        self.active_cfg = name
        self._fill_combos()
        self._fill_table()

    def new_solution_platform(self, name: str, copy_from: str = "", create_project_platforms: bool = False):
        self.doc.add_platform(name, copy_from)
        if create_project_platforms:
            for e in self.doc.real_projects():
                if e.ext in DOTNET_EXTS:
                    self._add_project_level(e.guid, name, "plat")
                    for b in self.doc.configurations():
                        self.doc.set_project_config(e.guid, f"{b}|{name}", plat=name)
        self.changed = True
        self.active_plat = name
        self._fill_combos()
        self._fill_table()

    def _combo_pick(self, combo, what):
        val = combo.currentText()
        if val == NEW:
            self._new_dialog(what)
        elif val == EDIT:
            self._edit_dialog(what)
        else:
            if what == "cfg":
                self.active_cfg = val
            else:
                self.active_plat = val
            self._fill_table()
        self._fill_combos()

    def _new_dialog(self, what):
        d = QDialog(self)
        d.setWindowTitle("New Solution Configuration" if what == "cfg" else "New Solution Platform")
        f = QFormLayout(d)
        name = QComboBox()
        name.setEditable(True)
        if what == "plat":
            name.addItems([p for p in STD_PLATFORMS if p not in self.doc.platforms()])
        else:
            name.setEditText("")
        copy = QComboBox()
        copy.addItems(["<Empty>"] + (self.doc.configurations() if what == "cfg" else self.doc.platforms()))
        if copy.count() > 1:
            copy.setCurrentIndex(1)
        create = QCheckBox("Create new project configurations" if what == "cfg" else "Create new project platforms")
        create.setChecked(what == "cfg")
        f.addRow("Name:" if what == "cfg" else "Type or select the new platform:", name)
        f.addRow("Copy settings from:", copy)
        f.addRow(create)
        f.addRow(_buttons(d))
        if not d.exec():
            return
        src = "" if copy.currentIndex() == 0 else copy.currentText()
        try:
            if what == "cfg":
                self.new_solution_configuration(name.currentText(), src, create.isChecked())
            else:
                self.new_solution_platform(name.currentText(), src, create.isChecked())
        except ValueError as e:
            _warn(self, d.windowTitle(), str(e))

    def _edit_dialog(self, what):
        d = QDialog(self)
        d.setWindowTitle("Edit Solution Configurations" if what == "cfg" else "Edit Solution Platforms")
        lay = QHBoxLayout(d)
        lst = QListWidget()
        lst.addItems(self.doc.configurations() if what == "cfg" else self.doc.platforms())
        lay.addWidget(lst)
        col = QVBoxLayout()
        rm, ren, close = QPushButton("Remove"), QPushButton("Rename"), QPushButton("Close")
        for b in (rm, ren, close):
            col.addWidget(b)
        col.addStretch(1)
        lay.addLayout(col)

        def remove():
            it = lst.currentItem()
            if it is None:
                return
            try:
                (self.doc.remove_configuration if what == "cfg" else self.doc.remove_platform)(it.text())
                self.changed = True
                lst.takeItem(lst.row(it))
            except ValueError as e:
                _warn(d, d.windowTitle(), str(e))

        def rename():
            it = lst.currentItem()
            if it is None:
                return
            new, ok = QInputDialog.getText(d, "Rename", "New name:", text=it.text())
            if ok and new.strip() and new != it.text():
                try:
                    (self.doc.rename_configuration if what == "cfg" else self.doc.rename_platform)(it.text(), new)
                    if what == "cfg" and self.active_cfg == it.text():
                        self.active_cfg = new.strip()
                    if what == "plat" and self.active_plat == it.text():
                        self.active_plat = new.strip()
                    it.setText(new.strip())
                    self.changed = True
                except ValueError as e:
                    _warn(d, "Rename", str(e))
        rm.clicked.connect(remove)
        ren.clicked.connect(rename)
        close.clicked.connect(d.accept)
        d.exec()
        self._fill_combos()
        self._fill_table()

    def apply(self):
        if getattr(self, "_applied", False):
            return False
        self._applied = True
        if self.changed:
            ops.commit(self.win, self.sln, self.doc, "Configuration Manager: solution configurations saved to "
                                                     f"{Path(self.sln.file).name}")
        from ...foreign import vs_ui
        if self.active_cfg in self.sln.configurations() and self.active_plat in self.sln.platforms():
            vs_ui.set_configuration(self.win, self.active_cfg, self.active_plat)
        return self.changed


def configuration_manager(win, sln, exec_: bool = True):
    try:
        dlg = ConfigurationManager(win, sln)
    except ValueError as e:
        _warn(win, "Configuration Manager", str(e))
        return None
    if exec_:
        dlg.exec()
    return dlg


# ====================================================================== Project Dependencies / Build Order
def _references_by_guid(sln, doc: SolutionDoc) -> dict:
    """{guid: [guids of the projects its ProjectReference items point to]}."""
    out = {}
    for e in doc.real_projects():
        vp = ops.vs_project_by_file(sln, ops.project_entry_file(sln, e))
        if vp is None:
            continue
        refs = []
        for r in vp.ms.project_references:
            from ...foreign.msbuild import xml_unescape
            t = (vp.folder / xml_unescape(r.include).replace("\\", "/")).resolve()
            x = doc.by_file(t)
            if x is not None:
                refs.append(x.guid)
        out[e.guid] = refs
    return out


class ProjectDependencies(QDialog):
    """Project > Project Dependencies... (tabs Dependencies / Build Order)."""

    def __init__(self, win, sln, project_name: str = ""):
        super().__init__(win)
        self.win, self.sln = win, sln
        self.doc = ops.doc_of(sln)
        self.refs = _references_by_guid(sln, self.doc)
        self.deps = {e.guid: list(e.deps) for e in self.doc.real_projects()}
        self.setWindowTitle("Project Dependencies")
        self.resize(480, 460)
        lay = QVBoxLayout(self)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs)
        page = QWidget()
        pl = QVBoxLayout(page)
        pl.addWidget(QLabel("Projects:"))
        self.project_combo = QComboBox()
        for e in self.doc.real_projects():
            self.project_combo.addItem(e.name, e.guid)
        pl.addWidget(self.project_combo)
        pl.addWidget(QLabel("Depends on:"))
        self.list = QListWidget()
        pl.addWidget(self.list)
        self.tabs.addTab(page, "Dependencies")
        order_page = QWidget()
        ol = QVBoxLayout(order_page)
        ol.addWidget(QLabel("Projects build in this order:"))
        self.order = QListWidget()
        ol.addWidget(self.order)
        ol.addWidget(QLabel("Use the Dependencies tab to change the build order."))
        self.tabs.addTab(order_page, "Build Order")
        lay.addWidget(_buttons(self))
        if project_name:
            i = self.project_combo.findText(project_name)
            if i >= 0:
                self.project_combo.setCurrentIndex(i)
        self.project_combo.currentIndexChanged.connect(lambda _i: self._fill())
        self.list.itemChanged.connect(self._toggled)
        self._fill()

    def current(self) -> str:
        return self.project_combo.currentData()

    def _fill(self):
        self.list.blockSignals(True)
        self.list.clear()
        g = self.current()
        for e in self.doc.real_projects():
            if e.guid == g:
                continue
            it = QListWidgetItem(e.name)
            it.setData(ROLE, e.guid)
            via_ref = e.guid in self.refs.get(g, [])
            it.setFlags(Qt.ItemFlag.ItemIsUserCheckable | (Qt.ItemFlag(0) if via_ref else Qt.ItemFlag.ItemIsEnabled))
            it.setCheckState(Qt.CheckState.Checked if via_ref or e.guid in self.deps.get(g, [])
                             else Qt.CheckState.Unchecked)
            if via_ref:
                it.setToolTip("Referenced by a project reference (Dependencies > Projects)")
            self.list.addItem(it)
        self.list.blockSignals(False)
        self._fill_order()

    def set_dependency(self, name: str, on: bool) -> None:
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.text().lower() == name.lower():
                it.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)

    def _toggled(self, it):
        g, d = self.current(), it.data(ROLE)
        cur = self.deps.setdefault(g, [])
        if it.checkState() == Qt.CheckState.Checked and d not in cur:
            closure = self._closure(d)
            if g in closure:
                self.list.blockSignals(True)
                it.setCheckState(Qt.CheckState.Unchecked)
                self.list.blockSignals(False)
                _warn(self, "Project Dependencies", "This dependency was not added: it would create a circular "
                                                    "dependency.")
                return
            cur.append(d)
        elif it.checkState() != Qt.CheckState.Checked and d in cur:
            cur.remove(d)
        self._fill_order()

    def _closure(self, g):
        seen, stack = set(), [g]
        while stack:
            x = stack.pop()
            for d in self.deps.get(x, []) + self.refs.get(x, []):
                if d not in seen:
                    seen.add(d)
                    stack.append(d)
        return seen

    def _fill_order(self):
        tmp = SolutionDoc()
        tmp.projects = [type(e)(e.name, e.path, e.type_guid, e.guid, e.parent, list(self.deps.get(e.guid, [])))
                        for e in self.doc.projects]
        self.order.clear()
        for e in tmp.build_order(self.refs):
            self.order.addItem(e.name)

    def build_order(self) -> list[str]:
        return [self.order.item(i).text() for i in range(self.order.count())]

    def apply(self) -> bool:
        changed = False
        for e in self.doc.real_projects():
            new = self.deps.get(e.guid, [])
            if new != e.deps:
                self.doc.set_dependencies(e.guid, new)
                changed = True
        if changed:
            ops.commit(self.win, self.sln, self.doc, "Project dependencies saved (build order: "
                                                     f"{', '.join(self.build_order())})")
        return changed


def project_dependencies(win, sln, project_name: str = "", tab: int = 0, exec_: bool = True):
    try:
        dlg = ProjectDependencies(win, sln, project_name)
    except ValueError as e:
        _warn(win, "Project Dependencies", str(e))
        return None
    dlg.tabs.setCurrentIndex(tab)
    if exec_ and dlg.exec():
        dlg.apply()
    return dlg


# ====================================================================== Solution Property Pages
ACTIONS = ["None", "Start", "Start without debugging"]


class SolutionPropertyPages(QDialog):
    """Solution > Properties: Common Properties (Startup Project, Project Dependencies) and
    Configuration Properties (Configuration)."""

    def __init__(self, win, sln):
        super().__init__(win)
        self.win, self.sln = win, sln
        self.state = ops.load_state(sln)
        self.setWindowTitle(f"Solution '{sln.name}' Property Pages")
        self.resize(760, 470)
        lay = QVBoxLayout(self)
        body = QHBoxLayout()
        lay.addLayout(body)
        self.nav = QTreeWidget()
        self.nav.setHeaderHidden(True)
        self.nav.setMaximumWidth(220)
        common = QTreeWidgetItem(self.nav, ["Common Properties"])
        cfgp = QTreeWidgetItem(self.nav, ["Configuration Properties"])
        self.pages = QStackedWidget()
        body.addWidget(self.nav)
        body.addWidget(self.pages, 1)
        self._page_items = {}
        for parent, title, w in ((common, "Startup Project", self._startup_page()),
                                 (common, "Project Dependencies", self._deps_page()),
                                 (cfgp, "Configuration", self._cfg_page())):
            it = QTreeWidgetItem(parent, [title])
            it.setData(0, ROLE, self.pages.addWidget(w))
            self._page_items[title] = it
        self.nav.expandAll()
        self.nav.currentItemChanged.connect(lambda it, _p: it is not None and it.data(0, ROLE) is not None and
                                            self.pages.setCurrentIndex(it.data(0, ROLE)))
        self.nav.setCurrentItem(self._page_items["Startup Project"])
        lay.addWidget(_buttons(self))

    def show_page(self, title: str):
        self.nav.setCurrentItem(self._page_items[title])

    def _startup_page(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.rb_current = QRadioButton("Current selection")
        self.rb_single = QRadioButton("Single startup project")
        self.rb_multi = QRadioButton("Multiple startup projects:")
        grp = QButtonGroup(w)
        for b in (self.rb_current, self.rb_single, self.rb_multi):
            grp.addButton(b)
        self.single_combo = QComboBox()
        names = [e.name for e in self.sln.projects]
        self.single_combo.addItems(names)
        self.single_combo.setCurrentText(self.sln.startup)
        self.multi = QTableWidget(0, 2)
        self.multi.setHorizontalHeaderLabels(["Project", "Action"])
        self.multi.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.multi.verticalHeader().setVisible(False)
        self.multi.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        acts = self.state.get("startup_actions") or {}
        order = self.state.get("startup_order") or []
        names_sorted = sorted(names, key=lambda n: (order.index(n.lower()) if n.lower() in order else 999))
        for n in names_sorted:
            r = self.multi.rowCount()
            self.multi.insertRow(r)
            it = QTableWidgetItem(n)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.multi.setItem(r, 0, it)
            c = QComboBox()
            c.addItems(ACTIONS)
            c.setCurrentText(acts.get(n.lower(), "None"))
            self.multi.setCellWidget(r, 1, c)
        up, down = QPushButton("Move Up"), QPushButton("Move Down")
        up.clicked.connect(lambda: self._move(-1))
        down.clicked.connect(lambda: self._move(1))
        mode = self.state.get("startup_mode", "single")
        {"current": self.rb_current, "multiple": self.rb_multi}.get(mode, self.rb_single).setChecked(True)
        lay.addWidget(self.rb_current)
        lay.addWidget(self.rb_single)
        lay.addWidget(self.single_combo)
        lay.addWidget(self.rb_multi)
        row = QHBoxLayout()
        row.addWidget(self.multi, 1)
        col = QVBoxLayout()
        col.addWidget(up)
        col.addWidget(down)
        col.addStretch(1)
        row.addLayout(col)
        lay.addLayout(row)
        return w

    def _move(self, d):
        r = self.multi.currentRow()
        t = r + d
        if r < 0 or not (0 <= t < self.multi.rowCount()):
            return
        a = (self.multi.item(r, 0).text(), self.multi.cellWidget(r, 1).currentText())
        b = (self.multi.item(t, 0).text(), self.multi.cellWidget(t, 1).currentText())
        for row, (n, act) in ((r, b), (t, a)):
            self.multi.item(row, 0).setText(n)
            self.multi.cellWidget(row, 1).setCurrentText(act)
        self.multi.setCurrentCell(t, 0)

    def set_action(self, name: str, action: str):
        for r in range(self.multi.rowCount()):
            if self.multi.item(r, 0).text().lower() == name.lower():
                self.multi.cellWidget(r, 1).setCurrentText(action)

    def _deps_page(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.deps_dialog = None
        if ops.has_file(self.sln):
            self.deps_dialog = ProjectDependencies(self.win, self.sln)
            self.deps_dialog.setWindowFlags(Qt.WindowType.Widget)
            box = self.deps_dialog.findChild(QDialogButtonBox)
            if box is not None:
                box.hide()
            lay.addWidget(self.deps_dialog)
        else:
            lay.addWidget(QLabel("Save a solution file to set project dependencies."))
        return w

    def _cfg_page(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        t = QTableWidget(0, 3)
        t.setHorizontalHeaderLabels(["Project", "Configuration", "Platform"])
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        t.verticalHeader().setVisible(False)
        for p in self.sln.all_projects():
            c, pl = self.sln.project_config(p)
            r = t.rowCount()
            t.insertRow(r)
            for i, v in enumerate((self.sln.name_of(p), c, pl)):
                t.setItem(r, i, QTableWidgetItem(v))
        lay.addWidget(QLabel(f"Configuration: {self.sln.configuration}    Platform: {self.sln.platform}"))
        lay.addWidget(t)
        b = QPushButton("Configuration Manager...")
        b.clicked.connect(lambda: (self.accept(), configuration_manager(self.win, self.sln)))
        b.setEnabled(ops.has_file(self.sln))
        lay.addWidget(b, 0, Qt.AlignmentFlag.AlignRight)
        return w

    def apply(self):
        st = ops.load_state(self.sln)
        mode = "multiple" if self.rb_multi.isChecked() else ("current" if self.rb_current.isChecked() else "single")
        st["startup_mode"] = mode
        st["startup_actions"] = {self.multi.item(r, 0).text().lower(): self.multi.cellWidget(r, 1).currentText()
                                 for r in range(self.multi.rowCount())}
        st["startup_order"] = [self.multi.item(r, 0).text().lower() for r in range(self.multi.rowCount())]
        ops.save_state(self.sln, st)
        if mode == "single" and self.single_combo.currentText():
            from ...features.solution_ui import set_startup_project
            set_startup_project(self.win, self.single_combo.currentText())
        if mode == "multiple":
            first = next((n for n, a in [(self.multi.item(r, 0).text(), self.multi.cellWidget(r, 1).currentText())
                                         for r in range(self.multi.rowCount())] if a != "None"), None)
            if first:
                self.sln.startup = self.sln.entry(first).name
                self.sln.save()
        if self.deps_dialog is not None:
            self.deps_dialog.apply()
        ops.refresh(self.win)
        ops._log(self.win, f"Startup: {mode}" + (" - " + ", ".join(f"{k}: {v}" for k, v in
                                                                     st["startup_actions"].items() if v != "None")
                                                 if mode == "multiple" else f" ({self.sln.startup})"))
        return mode


def solution_property_pages(win, sln, page: str = "Startup Project", exec_: bool = True):
    dlg = SolutionPropertyPages(win, sln)
    dlg.show_page(page)
    if exec_ and dlg.exec():
        dlg.apply()
    return dlg


# ====================================================================== Add a new project
class AddNewProject(QDialog):
    def __init__(self, win, sln, folder_guid: str = ""):
        super().__init__(win)
        self.win, self.sln, self.folder_guid = win, sln, folder_guid
        self.setWindowTitle("Add a new project")
        self.resize(760, 480)
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel("Recent project templates / All templates"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search for templates (Alt+S)")
        left.addWidget(self.search)
        self.lang = QComboBox()
        self.lang.addItems(["All languages", "C#", "VB", "F#"])
        left.addWidget(self.lang)
        self.templates = QListWidget()
        for title, short in ops.TEMPLATES:
            it = QListWidgetItem(title)
            it.setData(ROLE, short)
            it.setToolTip(f"dotnet new {short}" if short != "sharedproject" else "Shared Project (.shproj)")
            self.templates.addItem(it)
        self.templates.setCurrentRow(0)
        left.addWidget(self.templates, 1)
        lay.addLayout(left, 3)
        right = QFormLayout()
        right.addRow(QLabel("<b>Configure your new project</b>"))
        self.name = QLineEdit(self._suggest())
        self.location = QLineEdit(str(sln.folder))
        browse = QPushButton("...")
        browse.clicked.connect(self._browse)
        loc = QHBoxLayout()
        loc.addWidget(self.location, 1)
        loc.addWidget(browse)
        self.language = QComboBox()
        self.language.addItems(["C#", "VB", "F#"])
        self.framework = QComboBox()
        self.framework.addItems(["(default)", "net9.0", "net8.0"])
        right.addRow("Project name:", self.name)
        right.addRow("Location:", loc)
        right.addRow("Language:", self.language)
        right.addRow("Framework:", self.framework)
        right.addRow(_buttons(self))
        lay.addLayout(right, 2)
        self.search.textChanged.connect(self._filter)

    def _suggest(self):
        i = 1
        while (Path(self.sln.folder) / f"Project{i}").exists() or self.sln.entry(f"Project{i}") is not None:
            i += 1
        return f"Project{i}"

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Location", self.location.text())
        if d:
            self.location.setText(d)

    def _filter(self, text):
        for i in range(self.templates.count()):
            it = self.templates.item(i)
            it.setHidden(bool(text) and text.lower() not in it.text().lower() and text.lower() not in
                         str(it.data(ROLE)))

    def select(self, short: str):
        for i in range(self.templates.count()):
            if self.templates.item(i).data(ROLE) == short:
                self.templates.setCurrentRow(i)

    def apply(self):
        it = self.templates.currentItem()
        fw = "" if self.framework.currentIndex() == 0 else self.framework.currentText()
        try:
            return ops.new_project(self.win, self.sln, it.data(ROLE), self.language.currentText(), self.name.text(),
                                   Path(self.location.text()), self.folder_guid, fw)
        except (OSError, ValueError) as e:
            _warn(self.win, "Add a new project", str(e))
            return None


def add_new_project(win, sln, folder_guid: str = "", exec_: bool = True):
    dlg = AddNewProject(win, sln, folder_guid)
    if exec_:
        return dlg.apply() if dlg.exec() else None
    return dlg


# ====================================================================== Add projects of another solution
class ImportSolution(QDialog):
    """Add > Existing Solution's Projects...: every project of another .sln/.slnx with a checkbox, in
    its solution folders (recreated here)."""

    def __init__(self, win, sln, other_path: Path, folder_guid: str = ""):
        super().__init__(win)
        self.win, self.sln, self.folder_guid = win, sln, folder_guid
        self.other = SolutionDoc.load(other_path)
        self.other_path = Path(other_path)
        self.setWindowTitle(f"Add Projects from {self.other_path.name}")
        self.resize(560, 480)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Projects in {self.other_path}:"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Project", "Path"])
        lay.addWidget(self.tree, 1)
        mine = ops.doc_of(sln)
        folders: dict[str, QTreeWidgetItem] = {}

        def holder(e):
            if not e.parent:
                return self.tree.invisibleRootItem()
            f = self.other.entry(e.parent)
            if f is None:
                return self.tree.invisibleRootItem()
            if f.guid not in folders:
                it = QTreeWidgetItem(holder(f), [f.name, "(solution folder)"])
                folders[f.guid] = it
            return folders[f.guid]
        for e in self.other.real_projects():
            it = QTreeWidgetItem(holder(e), [e.name, e.path])
            it.setData(0, ROLE, e.guid)
            present = mine.by_file(self.other.folder / e.path) is not None
            it.setFlags(Qt.ItemFlag.ItemIsUserCheckable | (Qt.ItemFlag(0) if present else Qt.ItemFlag.ItemIsEnabled))
            it.setCheckState(0, Qt.CheckState.Unchecked if present else Qt.CheckState.Checked)
            if present:
                it.setToolTip(0, "Already in this solution")
        self.tree.expandAll()
        self.tree.resizeColumnToContents(0)
        row = QHBoxLayout()
        a, n = QPushButton("Select All"), QPushButton("Clear All")
        a.clicked.connect(lambda: self._all(True))
        n.clicked.connect(lambda: self._all(False))
        row.addWidget(a)
        row.addWidget(n)
        row.addStretch(1)
        lay.addLayout(row)
        self.keep_folders = QCheckBox("Recreate the solution folders of the other solution")
        self.keep_folders.setChecked(True)
        lay.addWidget(self.keep_folders)
        lay.addWidget(_buttons(self))

    def items(self):
        out, stack = [], [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]
        while stack:
            it = stack.pop(0)
            if it.data(0, ROLE):
                out.append(it)
            stack.extend(it.child(i) for i in range(it.childCount()))
        return out

    def _all(self, on):
        for it in self.items():
            if it.flags() & Qt.ItemFlag.ItemIsEnabled:
                it.setCheckState(0, Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)

    def check(self, name: str, on: bool):
        for it in self.items():
            if it.text(0).lower() == name.lower():
                it.setCheckState(0, Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)

    def apply(self):
        guids = [it.data(0, ROLE) for it in self.items() if it.checkState(0) == Qt.CheckState.Checked
                 and it.flags() & Qt.ItemFlag.ItemIsEnabled]
        if not guids:
            return []
        if not self.keep_folders.isChecked():
            for e in self.other.projects:
                if not e.is_folder:
                    e.parent = ""
            self.other.projects = [e for e in self.other.projects if not e.is_folder]
        doc = ops.doc_of(self.sln)
        added = doc.import_from(self.other, guids, self.folder_guid)
        ops.commit(self.win, self.sln, doc, f"Added {len(added)} project(s) from {self.other_path.name}: "
                                            f"{', '.join(e.name for e in added)}")
        return added


def import_solution(win, sln, other_path=None, folder_guid: str = "", exec_: bool = True):
    if other_path is None:
        f, _ = QFileDialog.getOpenFileName(win, "Add Projects from Solution", str(sln.folder),
                                           "Solution files (*.sln *.slnx)")
        if not f:
            return None
        other_path = f
    try:
        dlg = ImportSolution(win, sln, Path(other_path), folder_guid)
    except (OSError, ValueError) as e:
        _warn(win, "Add Projects from Solution", str(e))
        return None
    if exec_:
        return dlg.apply() if dlg.exec() else None
    return dlg


# ====================================================================== New solution from folders
class NewSolutionFromFolders(QDialog):
    def __init__(self, win, folders: list | None = None):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("New Solution from Existing Folders")
        self.resize(620, 480)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Folders (every project file below them joins the solution):"))
        self.folders = QListWidget()
        for f in folders or []:
            self.folders.addItem(str(f))
        lay.addWidget(self.folders)
        row = QHBoxLayout()
        add, rm = QPushButton("Add Folder..."), QPushButton("Remove")
        add.clicked.connect(self._add)
        rm.clicked.connect(lambda: self.folders.takeItem(self.folders.currentRow()))
        row.addWidget(add)
        row.addWidget(rm)
        row.addStretch(1)
        lay.addLayout(row)
        self.found = QListWidget()
        lay.addWidget(QLabel("Projects found:"))
        lay.addWidget(self.found)
        form = QFormLayout()
        self.name = QLineEdit("Solution1")
        self.location = QLineEdit(str(folders[0]) if folders else "")
        self.fmt = QComboBox()
        self.fmt.addItems([".sln", ".slnx"])
        form.addRow("Solution name:", self.name)
        form.addRow("Location:", self.location)
        form.addRow("Format:", self.fmt)
        lay.addLayout(form)
        lay.addWidget(_buttons(self))
        self.folders.model().rowsInserted.connect(lambda *_: self._scan())
        self.folders.model().rowsRemoved.connect(lambda *_: self._scan())
        self._scan()

    def _add(self):
        d = QFileDialog.getExistingDirectory(self, "Add Folder")
        if d:
            self.folders.addItem(d)
            if not self.location.text():
                self.location.setText(d)

    def _scan(self):
        from .model import find_project_files
        self.found.clear()
        for i in range(self.folders.count()):
            for p in find_project_files(self.folders.item(i).text()):
                self.found.addItem(str(p))

    def target(self) -> Path:
        return Path(self.location.text() or ".") / (self.name.text().strip() + self.fmt.currentText())

    def apply(self, open_it: bool = True):
        folders = [self.folders.item(i).text() for i in range(self.folders.count())]
        try:
            return ops.new_solution_from_folders(self.win, folders, self.target(), open_it)
        except (OSError, ValueError) as e:
            _warn(self.win, "New Solution", str(e))
            return None


def new_solution_from_folders(win, folders=None, exec_: bool = True):
    dlg = NewSolutionFromFolders(win, folders)
    if exec_:
        return dlg.apply() if dlg.exec() else None
    return dlg


# ====================================================================== Publish
class PublishDialog(QDialog):
    """Project > Publish...: Folder publish profiles (.pubxml) and dotnet publish."""

    def __init__(self, win, project):
        super().__init__(win)
        from . import publish as P
        self.P = P
        self.win, self.project, self.ms = win, project, project.ms
        self.setWindowTitle(f"Publish - {project.name}")
        self.resize(600, 440)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.profile = QComboBox()
        top.addWidget(QLabel("Publish profile:"))
        top.addWidget(self.profile, 1)
        new = QPushButton("New profile...")
        new.clicked.connect(self._new_profile)
        top.addWidget(new)
        lay.addLayout(top)
        g = QGroupBox("Settings")
        f = QFormLayout(g)
        self.configuration = QComboBox()
        self.configuration.addItems(project.ms.configuration_names())
        self.framework = QComboBox()
        self.framework.addItems(project.ms.target_frameworks or ["net8.0"])
        self.mode = QComboBox()
        self.mode.addItems(["Framework-dependent", "Self-contained"])
        self.rid = QComboBox()
        self.rid.addItems(P.RIDS)
        self.location = QLineEdit()
        self.single = QCheckBox("Produce single file")
        self.r2r = QCheckBox("Enable ReadyToRun compilation")
        self.trim = QCheckBox("Trim unused code")
        f.addRow("Configuration:", self.configuration)
        f.addRow("Target framework:", self.framework)
        f.addRow("Deployment mode:", self.mode)
        f.addRow("Target runtime:", self.rid)
        f.addRow("Target location:", self.location)
        f.addRow("File publish options:", self.single)
        f.addRow("", self.r2r)
        f.addRow("", self.trim)
        lay.addWidget(g)
        row = QHBoxLayout()
        save, pub = QPushButton("Save"), QPushButton("Publish")
        close = QPushButton("Close")
        save.clicked.connect(self.save)
        pub.clicked.connect(lambda: self.publish())
        close.clicked.connect(self.accept)
        row.addStretch(1)
        for b in (save, pub, close):
            row.addWidget(b)
        lay.addLayout(row)
        self._reload_profiles()
        self.profile.currentIndexChanged.connect(lambda _i: self._load())
        self._load()

    def _reload_profiles(self, select: str = ""):
        self.profile.blockSignals(True)
        self.profile.clear()
        for p in self.P.list_profiles(self.project.folder, self.ms.language):
            self.profile.addItem(p.stem, str(p))
        if self.profile.count() == 0:
            self.profile.addItem("FolderProfile", str(self.P.profiles_dir(self.project.folder, self.ms.language) /
                                                      "FolderProfile.pubxml"))
        if select:
            self.profile.setCurrentText(select)
        self.profile.blockSignals(False)

    def path(self) -> Path:
        return Path(self.profile.currentData())

    def _load(self):
        v = self.P.read(self.path()) if self.path().is_file() else self.P.default_profile(self.ms)
        self.configuration.setCurrentText(v.get("Configuration", "Release"))
        if v.get("TargetFramework"):
            self.framework.setCurrentText(v["TargetFramework"])
        self.mode.setCurrentIndex(1 if v.get("SelfContained", "").lower() == "true" else 0)
        self.rid.setCurrentText(v.get("RuntimeIdentifier") or "portable")
        self.location.setText(v.get("PublishDir", ""))
        self.single.setChecked(v.get("PublishSingleFile", "").lower() == "true")
        self.r2r.setChecked(v.get("PublishReadyToRun", "").lower() == "true")
        self.trim.setChecked(v.get("PublishTrimmed", "").lower() == "true")

    def _new_profile(self):
        name, ok = QInputDialog.getText(self, "New profile", "Profile name:", text=f"FolderProfile{self.profile.count()}")
        if ok and name.strip():
            p = self.P.profiles_dir(self.project.folder, self.ms.language) / f"{name.strip()}.pubxml"
            self.P.write(p, self.P.default_profile(self.ms))
            self._reload_profiles(name.strip())
            self._load()

    def values(self) -> dict:
        return self.P.profile_values(self.mode.currentIndex() == 1, self.rid.currentText(), self.single.isChecked(),
                                     self.r2r.isChecked(), self.trim.isChecked(), self.framework.currentText(),
                                     self.configuration.currentText(),
                                     self.location.text() or self.P.default_profile(self.ms)["PublishDir"])

    def save(self) -> Path:
        p = self.P.write(self.path(), self.values())
        ops._log(self.win, f"{self.project.name}: publish profile saved: {p}")
        return p

    def publish(self, wait: bool = False):
        p = self.save()
        from ...foreign.msbuild import find_dotnet
        dn = find_dotnet()
        if not dn:
            _warn(self.win, "Publish", "The .NET SDK (dotnet) was not found.")
            return None
        argv = self.P.publish_argv(dn, self.ms.path, p)
        return run_tool(self.win, argv, self.project.folder, f"Publish {self.project.name} ({p.stem})", wait)


def run_tool(win, argv, cwd, title: str, wait: bool = False):
    """Run a dotnet command with its output in the Output window (wait=True: here, return the exit code)."""
    import subprocess
    env = {"DOTNET_NOLOGO": "1", "DOTNET_CLI_TELEMETRY_OPTOUT": "1"}
    ops._log(win, f"------ {title} ------\n> {' '.join(str(a) for a in argv)}")
    if wait:
        r = subprocess.run([str(a) for a in argv], cwd=str(cwd), capture_output=True, timeout=1800,
                           creationflags=ops.NO_WINDOW, env={**os.environ, **env})
        out = (r.stdout + r.stderr).decode("utf-8", "replace")
        if out.strip():
            ops._log(win, out.rstrip())
        ops._log(win, f"========== {title}: {'succeeded' if r.returncode == 0 else 'FAILED'} ==========")
        return r.returncode
    from ...foreign._others_base import ChainSession, Step
    s = ChainSession([Step(argv, Path(cwd), env, "")], None, win)
    s.output.connect(lambda t: win._append_output(t) if hasattr(win, "_append_output") else ops._log(win, t))
    s.finished.connect(lambda c: ops._log(win, f"========== {title}: {'succeeded' if c == 0 else 'FAILED'} =========="))
    win._dotnet_tool_session = s
    try:
        win.dock_output.show()
        win.dock_output.raise_()
    except Exception:  # noqa: BLE001
        pass
    s.start()
    return s


def publish_dialog(win, project, exec_: bool = True):
    dlg = PublishDialog(win, project)
    if exec_:
        dlg.exec()
    return dlg
