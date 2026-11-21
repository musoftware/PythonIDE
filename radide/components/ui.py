"""Component package dialogs: Toolbox "Choose Items..." (VS), the Component Packages manager (install .radcomp,
uninstall, export, new package, user control -> package) and helpers used by the Extension Manager."""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QFileDialog,
                             QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QMessageBox,
                             QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import (PACKAGE_EXT, REGISTRY, SOURCE_LABEL, ComponentError, export_package, install_package, new_package,
               uninstall_package, user_components_dir)


def _project_folder(widget):
    win = widget.window()
    for w in (win, getattr(win, "parent", lambda: None)()):
        prj = getattr(w, "project", None)
        if prj is not None and getattr(prj, "folder", None):
            return Path(prj.folder)
    try:
        from PyQt6.QtWidgets import QApplication
        for top in QApplication.topLevelWidgets():
            prj = getattr(top, "project", None)
            if prj is not None and getattr(prj, "folder", None) and hasattr(top, "toolbox"):
                return Path(prj.folder)
    except Exception:  # noqa: BLE001
        pass
    return None


def _quiet() -> bool:
    return bool(os.environ.get("RADIDE_TEST_NO_DIALOGS"))


def install_package_dialog(parent, path: str | None = None, scope: str | None = None):
    """Ask for a .radcomp file (unless *path*) and install it for the user or the current project."""
    if path is None:
        path, _ = QFileDialog.getOpenFileName(parent, "Install Component Package", "",
                                              f"Component packages (*{PACKAGE_EXT} *.zip);;All files (*)")
        if not path:
            return None
    project = _project_folder(parent)
    if scope is None:
        scope = "user"
        if project is not None and not _quiet():
            box = QMessageBox(parent)
            box.setWindowTitle("Install Component Package")
            box.setText(f"Install {Path(path).name}\n\nfor all your projects, or only for the current project "
                        f"(it is then stored in {project.name}/.radide/components and travels with it)?\n\n"
                        "Component packages may contain Python code (designer and editors) that runs in the "
                        "IDE: install only packages you trust.")
            b_user = box.addButton("All Projects", QMessageBox.ButtonRole.AcceptRole)
            b_prj = box.addButton("This Project", QMessageBox.ButtonRole.AcceptRole)
            box.addButton(QMessageBox.StandardButton.Cancel)
            box.exec()
            if box.clickedButton() not in (b_user, b_prj):
                return None
            scope = "project" if box.clickedButton() is b_prj else "user"
    try:
        pkg = install_package(path, scope, project)
    except ComponentError as e:
        if "already installed" in str(e) and not _quiet() and QMessageBox.question(
                parent, "Install Component Package", f"{e}\n\nInstall the older version anyway?") \
                == QMessageBox.StandardButton.Yes:
            pkg = install_package(path, scope, project, allow_downgrade=True)
        else:
            if not _quiet():
                QMessageBox.warning(parent, "Install Component Package", str(e))
            return None
    _log(parent, f"[components] installed {pkg.name} {pkg.version} ({scope}) into {pkg.path}")
    return pkg


def _log(widget, text: str) -> None:
    win = widget.window() if widget is not None else None
    for w in (win, getattr(win, "parent", lambda: None)() if win is not None else None):
        if w is not None and hasattr(w, "log"):
            try:
                w.log(text)
                return
            except Exception:  # noqa: BLE001
                pass


# ============================================================================ Choose Items
class ChooseItemsDialog(QDialog):
    """Toolbox > Choose Items...: tick the controls the Toolbox shows (like VS's Choose Toolbox Items)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from ..toolbox import _hidden_types
        self.setWindowTitle("Choose Toolbox Items")
        self.resize(820, 480)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter")
        self.filter.textChanged.connect(self._filter)
        top.addWidget(QLabel("Filter:"))
        top.addWidget(self.filter, 1)
        lay.addLayout(top)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Name", "Group", "Version", "Source", "Publisher", "Location"])
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table, 1)
        self.info = QLabel()
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        self.table.currentCellChanged.connect(lambda r, *_: self._describe(r))
        row = QHBoxLayout()
        b = QPushButton("&Browse...")
        b.setToolTip("Install a component package (.radcomp)")
        b.clicked.connect(self._browse)
        row.addWidget(b)
        b = QPushButton("&Reset")
        b.setToolTip("Show every control again")
        b.clicked.connect(self._reset)
        row.addWidget(b)
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        row.addWidget(bb)
        lay.addLayout(row)
        self._hidden = _hidden_types()
        self.fill()

    def fill(self) -> None:
        from ..controls import CONTROL_TYPES
        from ..mobile.controls import MOBILE_CONTROL_TYPES
        from . import MISSING_CATEGORY
        self.table.setRowCount(0)
        rows = []
        for name, t in CONTROL_TYPES.items():
            if t.category == MISSING_CATEGORY:
                continue
            pkg = getattr(t, "package", None)
            if pkg is not None:
                rows.append((name, pkg.category, pkg.version, SOURCE_LABEL.get(pkg.source, pkg.source)
                             + (f" ({pkg.origin})" if pkg.source == "extension" else ""), pkg.publisher,
                             str(pkg.path or "")))
            elif name in MOBILE_CONTROL_TYPES:
                rows.append((name, "Mobile", "", "Built-in", "RAD IDE", ""))
            else:
                rows.append((name, "User Controls", "", "Project", "", ""))
        self.table.setRowCount(len(rows))
        for r, values in enumerate(rows):
            for c, v in enumerate(values):
                it = QTableWidgetItem(v)
                if c == 0:
                    it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    it.setCheckState(Qt.CheckState.Unchecked if v in self._hidden else Qt.CheckState.Checked)
                self.table.setItem(r, c, it)
        self.table.resizeColumnsToContents()
        self._filter(self.filter.text())

    def _filter(self, text: str) -> None:
        q = text.strip().lower()
        for r in range(self.table.rowCount()):
            hay = " ".join(self.table.item(r, c).text() for c in range(5)).lower()
            self.table.setRowHidden(r, bool(q) and q not in hay)

    def _describe(self, row: int) -> None:
        from ..controls import CONTROL_TYPES
        it = self.table.item(row, 0) if row >= 0 else None
        t = CONTROL_TYPES.get(it.text()) if it else None
        self.info.setText(f"<b>{it.text()}</b>: {t.description}" if t is not None else "")

    def checked(self) -> dict[str, bool]:
        return {self.table.item(r, 0).text(): self.table.item(r, 0).checkState() == Qt.CheckState.Checked
                for r in range(self.table.rowCount())}

    def set_checked(self, name: str, on: bool) -> None:
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).text() == name:
                self.table.item(r, 0).setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)

    def _reset(self) -> None:
        for r in range(self.table.rowCount()):
            self.table.item(r, 0).setCheckState(Qt.CheckState.Checked)

    def _browse(self) -> None:
        if install_package_dialog(self) is not None:
            self.fill()

    def accept(self) -> None:
        from ..toolbox import set_hidden_types
        set_hidden_types([n for n, on in self.checked().items() if not on])
        super().accept()


# ============================================================================ manager
class ComponentManagerDialog(QDialog):
    """Tools > Component Packages...: installed packages (all sources), install / uninstall / export /
    new / user control -> package, conflicts and validation errors."""

    def __init__(self, parent=None, win=None):
        super().__init__(parent)
        self.win = win
        self.setWindowTitle("Component Packages")
        self.resize(900, 520)
        lay = QVBoxLayout(self)
        note = QLabel("Every Toolbox control is a component package (component.json + optional designer.py, "
                      "editors.py, runtimes per language and help.md). Packages can contain Python code that "
                      "runs in the IDE: install only packages you trust.")
        note.setWordWrap(True)
        lay.addWidget(note)
        top = QHBoxLayout()
        self.show_builtin = QCheckBox("Show built-in controls")
        self.show_builtin.toggled.connect(lambda _on: self.refresh())
        top.addWidget(self.show_builtin)
        top.addStretch(1)
        lay.addLayout(top)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Name", "Version", "Group", "Source", "Targets", "Location"])
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.currentCellChanged.connect(lambda *_: self._details())
        lay.addWidget(self.table, 1)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(130)
        lay.addWidget(self.details)
        row = QHBoxLayout()
        for text, fn in (("&Install...", self.install), ("&Uninstall", self.uninstall),
                         ("&Export .radcomp...", self.export), ("&New Package...", self.new),
                         ("User Control -> &Package...", self.export_uc), ("Open &Folder", self.open_folder),
                         ("&Reload", self.reload)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        b = QPushButton("Close")
        b.clicked.connect(self.accept)
        row.addWidget(b)
        lay.addLayout(row)
        self.refresh()

    def refresh(self) -> None:
        pkgs = REGISTRY.all(include_builtin=self.show_builtin.isChecked())
        pkgs = sorted(pkgs, key=lambda p: (p.builtin, p.category.lower(), p.name.lower()))
        self.table.setRowCount(len(pkgs))
        self._pkgs = pkgs
        for r, p in enumerate(pkgs):
            targets = ", ".join(sorted(p.targets)) or "-"
            src = SOURCE_LABEL.get(p.source, p.source) + (f" ({p.origin})" if p.source == "extension" else "")
            for c, v in enumerate((p.display_name, p.version, p.category, src, targets, str(p.path or ""))):
                it = QTableWidgetItem(v)
                if c == 0 and p.errors:
                    it.setForeground(Qt.GlobalColor.red)
                self.table.setItem(r, c, it)
        self.table.resizeColumnsToContents()
        self._details()

    def current(self):
        r = self.table.currentRow()
        return self._pkgs[r] if 0 <= r < len(getattr(self, "_pkgs", [])) else None

    def _details(self) -> None:
        p = self.current()
        lines = []
        if p is not None:
            lines.append(f"{p.name} {p.version} - {p.description}")
            lines += [f"error: {e}" for e in p.errors]
        if REGISTRY.conflicts:
            lines += ["", "Conflicts:"] + [f"  {c}" for c in REGISTRY.conflicts]
        if REGISTRY.broken:
            lines += ["", "Packages that could not be read:"] + [f"  {f}: {e}" for f, e in REGISTRY.broken]
        self.details.setPlainText("\n".join(lines))

    def install(self):
        if install_package_dialog(self) is not None:
            self.refresh()

    def uninstall(self):
        p = self.current()
        if p is None or p.source not in ("user", "project"):
            QMessageBox.information(self, "Uninstall", "Select a package installed for you or for the project "
                                    "(built-in controls and extension packages cannot be removed here).")
            return
        if not _quiet() and QMessageBox.question(self, "Uninstall", f"Remove {p.name} {p.version}?\nForms that "
                                                 "use it keep their controls (shown as missing).") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            uninstall_package(p.name, p.source, p.origin or _project_folder(self))
        except (ComponentError, OSError) as e:
            QMessageBox.warning(self, "Uninstall", str(e))
        _log(self, f"[components] uninstalled {p.name}")
        self.refresh()

    def export(self):
        p = self.current()
        if p is None or p.path is None or p.builtin:
            QMessageBox.information(self, "Export", "Select a component package (not a built-in control).")
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Export Component Package", f"{p.name}-{p.version}{PACKAGE_EXT}",
                                              f"Component package (*{PACKAGE_EXT})")
        if dest:
            try:
                out = export_package(p.path, dest)
                _log(self, f"[components] exported {p.name} to {out}")
            except ComponentError as e:
                QMessageBox.warning(self, "Export", str(e))

    def new(self):
        name, ok = QInputDialog.getText(self, "New Component Package", "Control name (e.g. Gauge):")
        if not ok or not name.strip():
            return
        base = QFileDialog.getExistingDirectory(self, "Folder for the new package", str(user_components_dir()))
        if not base:
            return
        try:
            d = new_package(base, name.strip())
        except ComponentError as e:
            QMessageBox.warning(self, "New Component Package", str(e))
            return
        REGISTRY.discover()
        _log(self, f"[components] created {d} - edit component.json and the runtimes")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))
        self.refresh()

    def export_uc(self):
        prj = _project_folder(self)
        from ..usercontrols import USER_CONTROLS
        names = sorted(n for n, info in USER_CONTROLS.items()
                       if info.get("path") is not None and (prj is None or Path(info["path"]).parent == prj))
        if not names:
            QMessageBox.information(self, "User Control -> Package", "The project has no user control.")
            return
        name, ok = QInputDialog.getItem(self, "User Control -> Package", "User control:", names, 0, False)
        if not ok:
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Save Component Package", f"{name}{PACKAGE_EXT}",
                                              f"Component package (*{PACKAGE_EXT})")
        if not dest:
            return
        from .packaging import export_usercontrol
        try:
            out = export_usercontrol(Path(USER_CONTROLS[name]["path"]).parent, name, dest)
            _log(self, f"[components] user control {name} exported to {out}")
        except ComponentError as e:
            QMessageBox.warning(self, "User Control -> Package", str(e))

    def open_folder(self):
        p = self.current()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.path if p is not None and p.path else user_components_dir())))

    def reload(self):
        REGISTRY.discover()
        self.refresh()


__all__ = ["ChooseItemsDialog", "ComponentManagerDialog", "install_package_dialog"]
