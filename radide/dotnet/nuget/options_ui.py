"""Tools > Options > NuGet Package Manager (General, Package Sources) like Visual Studio 2022.

``options_page(dlg)`` is a radide.features.settings.PAGE_HOOKS hook; ``package_sources_dialog`` shows the
same page alone (the gear button of the NuGet document and Tools > NuGet Package Manager > Package
Manager Settings). Sources are written to the solution's nuget.config when it has one, else to the
user file %APPDATA%\\NuGet\\NuGet.Config. Credentials of private feeds are left to the dotnet CLI's
credential providers (nothing is stored here).
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
                             QTabWidget, QToolButton, QVBoxLayout, QWidget)

from . import config as C
from .projects import STYLE_PC, STYLE_PR

ROLE = Qt.ItemDataRole.UserRole


class GeneralPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        s = QSettings()
        lay = QVBoxLayout(self)
        g1 = QGroupBox("Package Restore")
        l1 = QVBoxLayout(g1)
        self.allow_restore = QCheckBox("Allow NuGet to download missing packages")
        self.allow_restore.setChecked(str(s.value("nuget/allow_restore", "true")).lower() == "true")
        self.auto_restore = QCheckBox("Automatically check for missing packages during build")
        self.auto_restore.setChecked(str(s.value("nuget/auto_restore", "true")).lower() == "true")
        l1.addWidget(self.allow_restore)
        l1.addWidget(self.auto_restore)
        lay.addWidget(g1)
        g2 = QGroupBox("Binding Redirects")
        l2 = QVBoxLayout(g2)
        self.skip_redirects = QCheckBox("Skip applying binding redirects")
        self.skip_redirects.setChecked(str(s.value("nuget/skip_binding_redirects", "false")).lower() == "true")
        l2.addWidget(self.skip_redirects)
        lay.addWidget(g2)
        g3 = QGroupBox("Package Management")
        l3 = QGridLayout(g3)
        l3.addWidget(QLabel("Default package management format:"), 0, 0)
        self.format = QComboBox()
        self.format.setObjectName("nugetDefaultFormat")
        self.format.addItem("Packages.config", STYLE_PC)
        self.format.addItem("PackageReference", STYLE_PR)
        self.format.setCurrentIndex(max(0, self.format.findData(str(s.value("nuget/default_format", STYLE_PC)))))
        l3.addWidget(self.format, 0, 1)
        self.allow_select = QCheckBox("Allow format selection on first package install")
        self.allow_select.setChecked(str(s.value("nuget/allow_format_selection", "true")).lower() == "true")
        l3.addWidget(self.allow_select, 1, 0, 1, 2)
        lay.addWidget(g3)
        row = QHBoxLayout()
        clear = QPushButton("Clear All NuGet Storage")
        clear.clicked.connect(self._clear)
        row.addWidget(clear)
        self.clear_note = QLabel("")
        row.addWidget(self.clear_note, 1)
        lay.addLayout(row)
        lay.addStretch(1)

    def _clear(self) -> None:
        from .projects import clear_local_caches
        if QMessageBox.question(self, "Clear All NuGet Storage",
                                "Clear the NuGet HTTP cache, the temp folder and the global packages folder?\n"
                                "Packages are downloaded again by the next restore.") != \
                QMessageBox.StandardButton.Yes:
            return
        lines = []
        try:
            clear_local_caches(lines.append)
            self.clear_note.setText("NuGet storage cleared.")
        except Exception as e:  # noqa: BLE001
            self.clear_note.setText(f"Could not clear: {e}")

    def apply(self) -> None:
        s = QSettings()
        s.setValue("nuget/allow_restore", "true" if self.allow_restore.isChecked() else "false")
        s.setValue("nuget/auto_restore", "true" if self.auto_restore.isChecked() else "false")
        s.setValue("nuget/skip_binding_redirects", "true" if self.skip_redirects.isChecked() else "false")
        s.setValue("nuget/default_format", self.format.currentData())
        s.setValue("nuget/allow_format_selection", "true" if self.allow_select.isChecked() else "false")


class SourcesPage(QWidget):
    """Available package sources (checkable, + / x / up / down, Name, Source, Update) and machine-wide sources."""

    def __init__(self, folder=None, parent=None):
        super().__init__(parent)
        self.folder = Path(folder) if folder else None
        self.target = C.editable_config(self.folder)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Available package sources:"), 1)
        for text, tip, slot, name in (("+", "Add", self.add, "nugetSrcAdd"), ("✕", "Remove", self.remove, "nugetSrcRemove"),
                                      ("▲", "Move Up", lambda: self.move(-1), ""),
                                      ("▼", "Move Down", lambda: self.move(1), "")):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            if name:
                b.setObjectName(name)
            b.clicked.connect(slot)
            top.addWidget(b)
        lay.addLayout(top)
        self.list = QListWidget()
        self.list.setObjectName("nugetSources")
        self.list.currentItemChanged.connect(self._pick)
        lay.addWidget(self.list, 2)
        lay.addWidget(QLabel("Machine-wide package sources:"))
        self.machine = QListWidget()
        self.machine.currentItemChanged.connect(self._pick)
        lay.addWidget(self.machine, 1)
        g = QGridLayout()
        g.addWidget(QLabel("Name:"), 0, 0)
        self.name = QLineEdit()
        self.name.setObjectName("nugetSrcName")
        g.addWidget(self.name, 0, 1, 1, 2)
        g.addWidget(QLabel("Source:"), 1, 0)
        self.url = QLineEdit()
        self.url.setObjectName("nugetSrcUrl")
        g.addWidget(self.url, 1, 1)
        browse = QPushButton("...")
        browse.setFixedWidth(30)
        browse.clicked.connect(self._browse)
        g.addWidget(browse, 1, 2)
        self.update_btn = QPushButton("Update")
        self.update_btn.setObjectName("nugetSrcUpdate")
        self.update_btn.clicked.connect(self.update_current)
        g.addWidget(self.update_btn, 1, 3)
        lay.addLayout(g)
        note = QLabel(f"Changes are saved to {self.target}. Private feeds authenticate through the dotnet "
                      f"CLI credential providers.")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray;")
        lay.addWidget(note)
        self.load()

    def load(self) -> None:
        self.list.clear()
        self.machine.clear()
        for s in C.effective_sources(self.folder):
            it = QListWidgetItem(f"{s.name}\n{s.url}")
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if s.enabled else Qt.CheckState.Unchecked)
            it.setData(ROLE, s)
            it.setToolTip(s.origin)
            (self.machine if s.machine else self.list).addItem(it)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _pick(self, item, _prev=None) -> None:
        if item is None:
            return
        s = item.data(ROLE)
        self.name.setText(s.name)
        self.url.setText(s.url)
        other = self.machine if item.listWidget() is self.list else self.list
        other.blockSignals(True)
        other.setCurrentRow(-1)
        other.blockSignals(False)

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Choose a local package source folder", self.url.text())
        if d:
            self.url.setText(d)

    def _current(self):
        return self.list.currentItem() or self.machine.currentItem()

    def add(self) -> None:
        n, k = "Package source", 1
        names = {self.list.item(i).data(ROLE).name.lower() for i in range(self.list.count())}
        while n.lower() in names:
            k += 1
            n = f"Package source {k}"
        s = C.PackageSource(n, "https://packagesource", True, "(new)")
        it = QListWidgetItem(f"{s.name}\n{s.url}")
        it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        it.setCheckState(Qt.CheckState.Checked)
        it.setData(ROLE, s)
        self.list.addItem(it)
        self.list.setCurrentItem(it)

    def add_source(self, name: str, url: str) -> None:
        self.add()
        self.name.setText(name)
        self.url.setText(url)
        self.update_current()

    def remove(self) -> None:
        it = self.list.currentItem()
        if it is None:
            return
        s = it.data(ROLE)
        if s.origin not in ("(new)", "(default)", str(self.target)) and s.origin:
            QMessageBox.information(self, "Package Sources", f"'{s.name}' is defined in {s.origin}.\n"
                                    "Uncheck it to disable it, or edit that file.")
            return
        self.list.takeItem(self.list.row(it))

    def move(self, delta: int) -> None:
        r = self.list.currentRow()
        if r < 0 or not (0 <= r + delta < self.list.count()):
            return
        it = self.list.takeItem(r)
        self.list.insertItem(r + delta, it)
        self.list.setCurrentRow(r + delta)

    def update_current(self) -> None:
        it = self._current()
        if it is None:
            return
        s = it.data(ROLE)
        name, url = self.name.text().strip(), self.url.text().strip()
        if not name or not url:
            QMessageBox.warning(self, "Package Sources", "The name and the source are required.")
            return
        s.name, s.url = name, url
        it.setText(f"{name}\n{url}")
        it.setData(ROLE, s)

    def sources(self) -> tuple[list[C.PackageSource], list[C.PackageSource]]:
        def collect(lw):
            out = []
            for i in range(lw.count()):
                it = lw.item(i)
                s = it.data(ROLE)
                s.enabled = it.checkState() == Qt.CheckState.Checked
                out.append(s)
            return out
        return collect(self.list), collect(self.machine)

    def apply(self) -> Path:
        mine, machine = self.sources()
        cf = C.ConfigFile.load(self.target, create=True)
        target = str(self.target)
        own = [s for s in mine if s.origin in ("(new)", "(default)", target, "")]
        cf.replace_sources(own)
        for s in mine + machine:
            if s not in own and not s.enabled:
                cf.enable_source(s.name, False)
        cf.save()
        try:
            from .feed import clear_feed_cache
            clear_feed_cache()
        except Exception:  # noqa: BLE001
            pass
        return self.target


class NuGetOptionsPage(QWidget):
    def __init__(self, folder=None, parent=None):
        super().__init__(parent)
        self.setObjectName("nugetOptions")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.general = GeneralPage()
        self.sources = SourcesPage(folder)
        self.tabs.addTab(self.general, "General")
        self.tabs.addTab(self.sources, "Package Sources")
        lay.addWidget(self.tabs)

    def apply(self) -> None:
        self.general.apply()
        self.sources.apply()


def _win_folder(win):
    try:
        from .context import solution_folder
        return solution_folder(win)
    except Exception:  # noqa: BLE001
        return None


def options_page(dlg):
    """settings.PAGE_HOOKS: (widget, title, apply)."""
    page = NuGetOptionsPage(_win_folder(getattr(dlg, "win", None) or dlg.parent()))
    return page, "NuGet Package Manager", page.apply


def package_sources_dialog(win, folder=None, tab: int = 1, exec_: bool = True):
    dlg = QDialog(win)
    dlg.setWindowTitle("Options - NuGet Package Manager")
    lay = QVBoxLayout(dlg)
    page = NuGetOptionsPage(folder if folder is not None else _win_folder(win))
    page.tabs.setCurrentIndex(tab)
    lay.addWidget(page)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(lambda: (page.apply(), dlg.accept()))
    box.rejected.connect(dlg.reject)
    lay.addWidget(box)
    dlg.resize(640, 560)
    dlg.page = page
    if not exec_:
        return dlg
    return bool(dlg.exec())


__all__ = ["options_page", "package_sources_dialog", "NuGetOptionsPage", "SourcesPage", "GeneralPage"]
