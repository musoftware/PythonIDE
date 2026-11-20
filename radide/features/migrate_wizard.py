"""File > Migrate Project...  - convert a project of another IDE into a RAD IDE project (or another language).

Separate from File > Open Project (which opens foreign projects IN PLACE, radide/features/foreign_projects.py):
migration writes a NEW project.

Pages: source (any project the engine or the foreign_projects registry can read: VB6 .vbp/.frm, Visual Studio
.sln/.csproj/.vbproj with Windows Forms, Delphi/Lazarus, Qt Designer, ...) -> target (keep the language as a
RAD IDE project, python-tk, python-qt, vb-basic, C# bridge, VB.NET Visual Studio project, any plugin) ->
options (new folder or in place, rules / rules + AI / comments, keep the original) -> preview of the mapping
(forms, controls, events, modules, unsupported items) -> progress -> migration report (exact / rules /
approximate / AI / manual TODO with file:line); the new project and the report are opened at the end.

Engine: radide/migrate/engine.py.  Other modules can open the wizard with ``show_wizard(win, path)``.
"""
from __future__ import annotations

import traceback
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QBrush, QColor
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QProgressBar, QPushButton,
                             QRadioButton, QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWizard,
                             QWizardPage)

from ..migrate import engine

STATUS_TEXT = {"exact": "exact", "rules": "rules", "approx": "approximate", "ai": "AI", "manual": "manual TODO",
               "info": "note"}
STATUS_COLOR = {"exact": "#2E7D32", "rules": "#1565C0", "approx": "#B26A00", "ai": "#6A1B9A", "manual": "#C62828",
                "info": "#555555"}


# ============================================================================ pages
class SourcePage(QWizardPage):
    def __init__(self, wiz: "MigrateWizard"):
        super().__init__(wiz)
        self.wiz = wiz
        self.setTitle("Project to migrate")
        self.setSubTitle("Choose a project of another IDE. Migration writes a NEW RAD IDE project; to work on the "
                         "project in its own format use File > Open Project instead.")
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.path = QLineEdit()
        self.path.setPlaceholderText("project file (.vbp, .sln, .csproj, .vbproj, .dproj, .lpi, .ui ...) or folder")
        self.path.textChanged.connect(self._changed)
        b1 = QPushButton("&File...")
        b1.clicked.connect(self._browse_file)
        b2 = QPushButton("F&older...")
        b2.clicked.connect(self._browse_folder)
        row.addWidget(self.path, 1)
        row.addWidget(b1)
        row.addWidget(b2)
        lay.addLayout(row)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.info)
        kinds = QLabel("Supported: " + "; ".join(f"{d} ({p})" for d, p in engine.supported_patterns()))
        kinds.setWordWrap(True)
        kinds.setStyleSheet("color: gray;")
        lay.addWidget(kinds)
        lay.addStretch(1)

    def _browse_file(self):
        pats = engine.supported_patterns()
        allp = " ".join(p for _d, p in pats)
        filt = ";;".join([f"All supported ({allp})"] + [f"{d} ({p})" for d, p in pats] + ["All files (*)"])
        f, _ = QFileDialog.getOpenFileName(self, "Project to migrate", self.path.text(), filt)
        if f:
            self.path.setText(f)

    def _browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Folder of the project to migrate", self.path.text())
        if d:
            self.path.setText(d)

    def _changed(self):
        self.wiz.source = None
        p = engine.detect(self.path.text().strip()) if self.path.text().strip() else None
        self.info.setText(f"Found: {p}" if p else ("" if not self.path.text().strip() else "No project found."))
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        t = self.path.text().strip()
        return bool(t) and Path(t).exists()

    def validatePage(self) -> bool:
        try:
            self.wiz.source = engine.load_source(self.path.text().strip())
        except Exception as e:  # noqa: BLE001 - shown on the page
            self.wiz.source = None
            self.info.setText(f"<span style='color:#C62828'>{e}</span>")
            return False
        s = self.wiz.source
        self.info.setText(f"{s.label} <b>{s.name}</b>: {len(s.forms)} form(s), {len(s.modules)} module(s), "
                          f"code in {s.language}.")
        return True


class TargetPage(QWizardPage):
    def __init__(self, wiz: "MigrateWizard"):
        super().__init__(wiz)
        self.wiz = wiz
        self.setTitle("Target")
        self.setSubTitle("Keep the language as a RAD IDE project, or convert the project to another language.")
        lay = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(lambda _r: self.completeChanged.emit())
        lay.addWidget(self.list, 1)
        self.hint = QLabel("")
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)

    def initializePage(self):
        self.list.clear()
        src = self.wiz.source
        if src is None:
            return
        for tid, label, how in engine.targets_for(src):
            how_txt = {"exact": "code kept as it is", "rules": "code converted by rules",
                       "comments + AI": "code kept as comments (AI translation when configured)"}.get(how, how)
            it = QListWidgetItem(f"{label}    -  {how_txt}")
            it.setData(Qt.ItemDataRole.UserRole, tid)
            if how in ("rules", "exact"):
                f = it.font()
                f.setBold(True)
                it.setFont(f)
            self.list.addItem(it)
        self.list.setCurrentRow(0 if src.language not in ("vb6", "csharp", "vbnet") else 1)
        self.hint.setText("Bold targets convert the event code by rules (VB6 -> Python / VB.NET, C# -> Python, "
                          "VB.NET -> VB6 / Python). The others get the forms, one event handler per original "
                          "event and the original code as comments to translate (or AI).")

    def target(self) -> str:
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else "keep"

    def isComplete(self) -> bool:
        return self.list.currentItem() is not None


class OptionsPage(QWizardPage):
    def __init__(self, wiz: "MigrateWizard"):
        super().__init__(wiz)
        self.wiz = wiz
        self.setTitle("Options")
        lay = QFormLayout(self)
        row = QHBoxLayout()
        self.dest = QLineEdit()
        self.dest.textChanged.connect(lambda _t: self.completeChanged.emit())
        b = QPushButton("...")
        b.clicked.connect(self._browse)
        row.addWidget(self.dest, 1)
        row.addWidget(b)
        lay.addRow("New project folder:", row)
        self.copy = QRadioButton("Write the project into a new folder (recommended)")
        self.inplace = QRadioButton("In place: next to the original files (only when no file would be replaced)")
        self.copy.setChecked(True)
        grp = QButtonGroup(self)
        grp.addButton(self.copy)
        grp.addButton(self.inplace)
        self.copy.toggled.connect(lambda on: (self.dest.setEnabled(on), self.completeChanged.emit()))
        lay.addRow("Where:", self.copy)
        lay.addRow("", self.inplace)
        self.code = QComboBox()
        self.code.addItem("Convert the event code by rules", "rules")
        self.code.addItem("Rules + AI for what the rules cannot convert", "rules+ai")
        self.code.addItem("Keep the original code as comments only", "comments")
        lay.addRow("Event code:", self.code)
        self.ai_info = QLabel("")
        self.ai_info.setWordWrap(True)
        self.ai_info.setStyleSheet("color: gray;")
        lay.addRow("", self.ai_info)
        self.keep = QCheckBox("Copy the original project into _original/ for reference")
        self.keep.setChecked(True)
        lay.addRow("", self.keep)

    def initializePage(self):
        src = self.wiz.source
        tgt = self.wiz.target_page.target()
        if src is not None:
            real = engine.resolve_target(src, tgt)
            base = src.folder.parent / f"{src.name}_{real.replace('-', '_')}"
            p, i = base, 2
            while p.exists() and any(p.iterdir()):
                p = Path(f"{base}{i}")
                i += 1
            self.dest.setText(str(p))
        ok, who = engine._ai_available()
        self.ai_info.setText(f"AI: {who}" if ok else f"AI is not available ({who}) - Tools > Options > AI")
        self.code.model().item(1).setEnabled(ok)
        if not ok and self.code.currentIndex() == 1:
            self.code.setCurrentIndex(0)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Folder of the new project", self.dest.text())
        if d:
            self.dest.setText(d)

    def isComplete(self) -> bool:
        if self.inplace.isChecked():
            return True
        t = self.dest.text().strip()
        if not t:
            return False
        p = Path(t)
        return not (p.exists() and p.is_dir() and any(p.iterdir()))

    def options(self) -> engine.Options:
        mode = "inplace" if self.inplace.isChecked() else "copy"
        code = self.code.currentData()
        return engine.Options(self.wiz.target_page.target(), Path(self.dest.text().strip() or "."), mode,
                              code, self.keep.isChecked())


class PreviewPage(QWizardPage):
    def __init__(self, wiz: "MigrateWizard"):
        super().__init__(wiz)
        self.wiz = wiz
        self.setTitle("Preview of the mapping")
        self.setSubTitle("What will be converted, and how. Items marked 'manual TODO' need your attention after "
                         "the migration (the report lists them with file:line).")
        lay = QVBoxLayout(self)
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        lay.addWidget(self.summary)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Item", "Mapping", "Status"])
        self.tree.setColumnWidth(0, 230)
        self.tree.setColumnWidth(1, 380)
        lay.addWidget(self.tree, 1)

    def initializePage(self):
        self.tree.clear()
        src = self.wiz.source
        if src is None:
            return
        tgt = self.wiz.target_page.target()
        rows = engine.plan(src, tgt)
        groups: dict[str, QTreeWidgetItem] = {}
        counts: dict[str, int] = {}
        for r in rows:
            g = groups.get(r.section)
            if g is None:
                g = QTreeWidgetItem([r.section, "", ""])
                f = g.font(0)
                f.setBold(True)
                g.setFont(0, f)
                self.tree.addTopLevelItem(g)
                groups[r.section] = g
            it = QTreeWidgetItem([r.item, r.mapping, STATUS_TEXT.get(r.status, r.status)])
            it.setForeground(2, QBrush(QColor(STATUS_COLOR.get(r.status, "#555555"))))
            it.setToolTip(1, r.mapping)
            g.addChild(it)
            counts[r.status] = counts.get(r.status, 0) + 1
        for sec, g in groups.items():
            g.setText(1, f"{g.childCount()} item(s)")
            g.setExpanded(sec in ("Forms", "Code", "Modules", "Notes"))
        real = engine.resolve_target(src, tgt)
        self.summary.setText(f"<b>{src.label} '{src.name}'</b> -> <b>{real}</b>: "
                             + ", ".join(f"{n} {STATUS_TEXT.get(k, k)}" for k, n in sorted(counts.items())))


class _Worker(QThread):
    log = pyqtSignal(str)
    done = pyqtSignal(object)

    def __init__(self, src, opts):
        super().__init__()
        self.src, self.opts = src, opts

    def run(self):
        try:
            res = engine.migrate(self.src, self.opts, progress=self.log.emit)
            self.done.emit(res)
        except Exception as e:  # noqa: BLE001 - shown in the wizard
            self.log.emit(traceback.format_exc())
            self.done.emit(e)


class ProgressPage(QWizardPage):
    def __init__(self, wiz: "MigrateWizard"):
        super().__init__(wiz)
        self.wiz = wiz
        self.setTitle("Migrating")
        lay = QVBoxLayout(self)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        lay.addWidget(self.bar)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        lay.addWidget(self.text, 1)
        self.worker = None
        self.finished_ok = False

    def initializePage(self):
        self.text.clear()
        self.finished_ok = False
        self.wiz.result = None
        self.bar.setRange(0, 0)
        self.worker = _Worker(self.wiz.source, self.wiz.options_page.options())
        self.worker.log.connect(self.text.appendPlainText)
        self.worker.done.connect(self._done)
        self.worker.start()

    def _done(self, payload):
        self.bar.setRange(0, 1)
        self.bar.setValue(1)
        if isinstance(payload, Exception):
            self.text.appendPlainText(f"\nMigration failed: {payload}")
        else:
            self.wiz.result = payload
            self.finished_ok = True
            self.text.appendPlainText(f"\nProject: {payload.project_file}\nReport: {payload.report_path}")
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self.finished_ok


class ReportPage(QWizardPage):
    def __init__(self, wiz: "MigrateWizard"):
        super().__init__(wiz)
        self.wiz = wiz
        self.setTitle("Migration report")
        lay = QVBoxLayout(self)
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        lay.addWidget(self.view, 1)
        self.open_project = QCheckBox("Open the migrated project")
        self.open_project.setChecked(True)
        self.open_report = QCheckBox("Open MIGRATION_REPORT.md in the editor")
        self.open_report.setChecked(True)
        lay.addWidget(self.open_project)
        lay.addWidget(self.open_report)

    def initializePage(self):
        res = self.wiz.result
        if res is None:
            return
        try:
            from .exe_import import markdown_to_html
            self.view.setHtml(markdown_to_html(res.report))
        except Exception:  # noqa: BLE001
            self.view.setPlainText(res.report)


class MigrateWizard(QWizard):
    def __init__(self, parent=None, path: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Migrate Project")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnLastPage, True)
        self.resize(820, 600)
        self.source = None
        self.result = None
        self.source_page = SourcePage(self)
        self.target_page = TargetPage(self)
        self.options_page = OptionsPage(self)
        self.preview_page = PreviewPage(self)
        self.progress_page = ProgressPage(self)
        self.report_page = ReportPage(self)
        for p in (self.source_page, self.target_page, self.options_page, self.preview_page, self.progress_page,
                  self.report_page):
            self.addPage(p)
        self.setButtonText(QWizard.WizardButton.CommitButton, "&Migrate")
        self.preview_page.setCommitPage(True)
        if path:
            self.source_page.path.setText(str(path))

    def reject(self):
        w = self.progress_page.worker
        if w is not None and w.isRunning():
            return              # a running migration cannot be stopped half-way
        super().reject()


# ============================================================================ entry points
def show_wizard(win, path=None):
    """Open the wizard (path = a project to migrate, e.g. from the Solution Explorer of a foreign project)."""
    wiz = MigrateWizard(win, str(path or ""))
    if wiz.exec() and wiz.result is not None:
        res = wiz.result
        try:
            win.log(f"Migrated {wiz.source.path} -> {res.folder} ({res.target})")
        except Exception:  # noqa: BLE001
            pass
        if wiz.report_page.open_project.isChecked() and res.project_file is not None:
            if hasattr(win, "_confirm_close_project") and getattr(win, "project", None) is not None:
                if not win._confirm_close_project():
                    return wiz
            target = res.project_file if res.target == "vbnet" else res.folder
            try:
                win.open_project(Path(target), ask=False)
            except Exception as e:  # noqa: BLE001
                win.log(f"[migrate] could not open {target}: {e}")
        if wiz.report_page.open_report.isChecked() and res.report_path is not None:
            try:
                win.open_any_file(res.report_path)
            except Exception as e:  # noqa: BLE001
                win.log(f"[migrate] could not open the report: {e}")
    return wiz


migrate_dialog = show_wizard


def install(win) -> None:
    menu = getattr(win, "file_menu", None)
    if menu is None:
        menu = next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "File"), None)
    if menu is None:
        return
    act = QAction("&Migrate Project...", win)
    act.setStatusTip("Convert a project of another IDE (VB6, Visual Studio WinForms, Delphi, Qt ...) into a new "
                     "RAD IDE project, in the same language or another one")
    act.triggered.connect(lambda: show_wizard(win))
    imp = next((a for a in menu.actions() if a.menu() is not None and a.text().replace("&", "") == "Import"), None)
    if imp is not None:
        menu.insertAction(imp, act)
    else:
        menu.addAction(act)
    win.a_migrate_project = act
