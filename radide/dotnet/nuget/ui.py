"""The "NuGet Package Manager" document of Visual Studio 2022 (project and solution level).

    Browse | Installed | Updates (n) | Consolidate (n)          NuGet Package Manager: ConsoleApp
    [Search (Ctrl+L)        ] [refresh] [x] Include prerelease    Package source: [nuget.org v] [gear]
    +------------------------------------+---------------------------------------------------------+
    | [icon] Newtonsoft.Json  by James...|  [icon] Newtonsoft.Json   nuget.org   (verified)         |
    |        Json.NET is a popular ...   |  ! deprecated / vulnerable banners                       |
    |                          13.0.3    |  (solution) [x] Project      Version                     |
    |                                    |  Installed: 13.0.1  [Uninstall]                          |
    |                                    |  Version:  [Latest stable 13.0.4 v]  [Install|Update]     |
    |                                    |  > Options (preview window, dependency behavior)         |
    |                                    |  Package Details | README                                |
    +------------------------------------+---------------------------------------------------------+

``open_manager(win, project=None, solution=False)`` opens (or focuses) the document tab.
All network / dotnet work runs in worker threads (radide.dotnet.nuget.qtasync).
"""
from __future__ import annotations

import html
import os
from dataclasses import dataclass, field
from datetime import datetime

from PyQt6.QtCore import QSettings, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QKeySequence, QPainter, QPixmap, QShortcut
from PyQt6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                             QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSplitter, QTabWidget,
                             QTextBrowser, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import context as CX
from . import http
from . import projects as P
from .config import PackageSource, effective_sources, global_packages_folder
from .feed import AggregateFeed, LocalFeed, PackageMetadata, SearchResult, feed_for, package_page
from .qtasync import alive, run_async, thread_log
from .versions import NuGetVersion, VersionRange, is_newer, sort_versions

OFFSCREEN = os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"
PAGE = 25
_ICONS: dict[str, QPixmap] = {}


# ====================================================================== records
@dataclass
class Record:
    id: str
    latest: str = ""
    description: str = ""
    authors: str = ""
    downloads: int = -1
    icon_url: str = ""
    verified: bool = False
    versions: list = field(default_factory=list)
    installed: dict = field(default_factory=dict)          # project name -> version
    transitive: bool = False
    header: str = ""                                       # a section title row
    deprecated: bool = False
    vulnerable: bool = False
    source: str = ""
    projects_versions: list = field(default_factory=list)  # consolidate / updates [(project, version)]

    @staticmethod
    def from_search(r: SearchResult) -> "Record":
        return Record(r.id, r.version, r.description or r.summary, ", ".join(r.authors), r.total_downloads,
                      r.icon_url, r.verified, r.version_list, {}, False, "", r.deprecated, r.vulnerable, r.source)

    @property
    def installed_version(self) -> str:
        vs = list(dict.fromkeys(self.installed.values()))
        return vs[0] if len(vs) == 1 else ("Multiple" if vs else "")


def fmt_downloads(n: int) -> str:
    if n < 0:
        return ""
    for div, suf in ((10 ** 9, "B"), (10 ** 6, "M"), (10 ** 3, "K")):
        if n >= div:
            v = n / div
            return f"{v:.1f}{suf}".replace(".0" + suf, suf)
    return str(n)


def default_icon(size: int = 32) -> QPixmap:
    key = f"__default{size}"
    if key in _ICONS:
        return _ICONS[key]
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#004880"))
    p.drawRoundedRect(2, 2, size - 4, size - 4, 5, 5)
    p.setBrush(QColor("#ffffff"))
    r = size // 6
    p.drawEllipse(size // 4 - r // 2, size // 4 - r // 2, r * 2 // 1, r * 2 // 1)
    p.setBrush(QColor("#7ab8ff"))
    p.drawRoundedRect(size // 2 - 2, size // 2 - 2, size // 3, size // 3, 3, 3)
    p.end()
    _ICONS[key] = pm
    return pm


def load_icon(url: str, size: int, done) -> None:
    """Icon from the cache or (async) the network; done(QPixmap) on the GUI thread."""
    if not url:
        done(default_icon(size))
        return
    key = f"{url}|{size}"
    if key in _ICONS:
        done(_ICONS[key])
        return

    def fetch():
        return http.get(url, ttl=7 * 24 * 3600, timeout=15)

    def got(data, err):
        pm = QPixmap()
        if err is None and data and pm.loadFromData(data):
            pm = pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        else:
            pm = default_icon(size)
        _ICONS[key] = pm
        done(pm)
    run_async(fetch, got)


# ====================================================================== list row
class PackageRow(QWidget):
    def __init__(self, rec: Record, show_check: bool = False, parent=None):
        super().__init__(parent)
        self.rec = rec
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 8, 4)
        self.check = QCheckBox()
        self.check.setVisible(show_check)
        lay.addWidget(self.check, 0, Qt.AlignmentFlag.AlignTop)
        self.icon = QLabel()
        self.icon.setFixedSize(32, 32)
        self.icon.setPixmap(default_icon(32))
        lay.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        mid = QVBoxLayout()
        mid.setSpacing(1)
        head = QLabel()
        head.setTextFormat(Qt.TextFormat.RichText)
        by = f" by {html.escape(rec.authors)}" if rec.authors else ""
        dl = f", {fmt_downloads(rec.downloads)} downloads" if rec.downloads >= 0 else ""
        badge = " <span style='color:#1a7f37'>&#10004;</span>" if rec.verified else ""
        warn = " <span style='color:#b35900'>&#9888;</span>" if (rec.deprecated or rec.vulnerable) else ""
        head.setText(f"<b>{html.escape(rec.id)}</b>{badge}{warn}<span style='color:gray'>{html.escape(by + dl)}</span>")
        mid.addWidget(head)
        desc = QLabel(_elide(rec.description, 160))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray;")
        mid.addWidget(desc)
        lay.addLayout(mid, 1)
        right = QVBoxLayout()
        right.setSpacing(1)
        inst = rec.installed_version
        if inst:
            v = QLabel(f"v{inst}" if inst != "Multiple" else "Multiple")
            v.setAlignment(Qt.AlignmentFlag.AlignRight)
            right.addWidget(v)
            if rec.latest and inst != "Multiple" and is_newer(rec.latest, inst):
                up = QLabel(f"&#8593; v{html.escape(rec.latest)}")
                up.setTextFormat(Qt.TextFormat.RichText)
                up.setStyleSheet("color:#0e70c0")
                up.setAlignment(Qt.AlignmentFlag.AlignRight)
                right.addWidget(up)
        elif rec.latest:
            v = QLabel(f"v{rec.latest}")
            v.setAlignment(Qt.AlignmentFlag.AlignRight)
            right.addWidget(v)
        right.addStretch(1)
        lay.addLayout(right)
        load_icon(rec.icon_url, 32, lambda pm: alive(self.icon) and self.icon.setPixmap(pm))


def _elide(s: str, n: int) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


# ====================================================================== dialogs
def license_dialog(parent, metas: list[PackageMetadata]) -> bool:
    """VS 'License Acceptance': I Accept / I Decline."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("License Acceptance")
    lay = QVBoxLayout(dlg)
    lay.addWidget(QLabel("The following package(s) require that you accept their license terms before installing."))
    body = QTextBrowser()
    body.setOpenExternalLinks(True)
    rows = []
    for m in metas:
        link = m.license_link or package_page(m.id, m.version)
        rows.append(f"<p><b>{html.escape(m.id)}</b> {html.escape(m.version)}<br>Author(s): {html.escape(m.authors)}"
                    f"<br><a href='{html.escape(link)}'>View License</a></p>")
    body.setHtml("".join(rows))
    lay.addWidget(body, 1)
    lay.addWidget(QLabel("By clicking \"I Accept,\" you agree to the license terms for the package(s) listed above. "
                         "If you do not agree to the license terms, click \"I Decline.\""))
    box = QDialogButtonBox()
    box.addButton("I Accept", QDialogButtonBox.ButtonRole.AcceptRole)
    box.addButton("I Decline", QDialogButtonBox.ButtonRole.RejectRole)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addWidget(box)
    dlg.resize(560, 380)
    return bool(dlg.exec())


def preview_dialog(parent, changes: list[tuple[str, list[str]]]) -> bool:
    """VS 'Preview Changes': per project, the packages that will be installed / updated / uninstalled."""
    dlg = QDialog(parent)
    dlg.setWindowTitle("Preview Changes")
    lay = QVBoxLayout(dlg)
    lay.addWidget(QLabel("Visual Studio is about to make changes to this solution. Click OK to proceed with the "
                         "changes listed below.".replace("Visual Studio", "RAD IDE")))
    t = QPlainTextEdit()
    t.setReadOnly(True)
    t.setPlainText("\n\n".join(f"{proj}\n" + "\n".join("    " + c for c in rows) for proj, rows in changes))
    lay.addWidget(t, 1)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addWidget(box)
    dlg.resize(520, 340)
    return bool(dlg.exec())


# ====================================================================== the document
class PackageManagerView(QWidget):
    TABS = ("browse", "installed", "updates", "consolidate")

    def __init__(self, win, projects: list[P.NuGetProject], solution: bool = False, title: str = ""):
        super().__init__(win if win is not None else None)
        self.setObjectName("nugetPackageManager")
        self.win = win
        self.projects = projects
        self.solution = solution
        self.title = title or (projects[0].name if projects else "")
        self.tab = "browse"
        self.records: list[Record] = []
        self.current: Record | None = None
        self.metas: dict[str, PackageMetadata] = {}
        self.busy = 0
        self._gen = 0
        self._skip = 0
        self._total = 0
        self._more = False
        self.update_count = 0
        self.consolidate_count = 0
        self.settings = QSettings()
        self.show_preview = str(self.settings.value("nuget/show_preview", "true")).lower() == "true"
        # hooks (tests replace them)
        self.confirm_licenses = lambda metas: license_dialog(self, metas)
        self.confirm_preview = lambda changes: preview_dialog(self, changes)
        self._build()
        self._fill_sources()
        QTimer.singleShot(0, self.refresh)
        QTimer.singleShot(0, self.refresh_badges)

    # ------------------------------------------------------------------ layout
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        top = QHBoxLayout()
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        self.tab_buttons: dict[str, QToolButton] = {}
        self.badges: dict[str, QLabel] = {}
        names = {"browse": "Browse", "installed": "Installed", "updates": "Updates", "consolidate": "Consolidate"}
        for key in self.TABS:
            if key == "consolidate" and not self.solution:
                continue
            b = QToolButton()
            b.setText(names[key])
            b.setCheckable(True)
            b.setAutoRaise(True)
            b.setObjectName(f"nugetTab_{key}")
            b.setStyleSheet("QToolButton{font-size:11pt;padding:2px 6px;border:none;}"
                            "QToolButton:checked{font-weight:bold;border-bottom:2px solid #0e70c0;}")
            b.clicked.connect(lambda _c=False, k=key: self.set_tab(k))
            self.tab_group.addButton(b)
            self.tab_buttons[key] = b
            top.addWidget(b)
            if key in ("updates", "consolidate"):
                badge = QLabel("")
                badge.setObjectName(f"nugetBadge_{key}")
                badge.setStyleSheet("QLabel{background:#0e70c0;color:white;border-radius:7px;padding:0 5px;"
                                    "font-size:8pt;}")
                badge.setVisible(False)
                self.badges[key] = badge
                top.addWidget(badge)
            top.addSpacing(8)
        self.tab_buttons["browse"].setChecked(True)
        top.addStretch(1)
        self.header = QLabel()
        f = QFont(self.header.font())
        f.setPointSize(f.pointSize() + 3)
        self.header.setFont(f)
        self.header.setText("Manage Packages for Solution" if self.solution else
                            f"NuGet Package Manager: {self.title}")
        top.addWidget(self.header)
        root.addLayout(top)

        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setObjectName("nugetSearch")
        self.search.setPlaceholderText("Search (Ctrl+L)")
        self.search.setClearButtonEnabled(True)
        self.search.returnPressed.connect(self.refresh)
        self.search.textChanged.connect(self._on_text)
        row.addWidget(self.search, 2)
        self.refresh_btn = QToolButton()
        self.refresh_btn.setText("⟳")
        self.refresh_btn.setToolTip("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_all)
        row.addWidget(self.refresh_btn)
        self.prerelease = QCheckBox("Include prerelease")
        self.prerelease.setObjectName("nugetPrerelease")
        self.prerelease.toggled.connect(lambda _v: (self.refresh(), self.refresh_badges()))
        row.addWidget(self.prerelease)
        self.select_all = QCheckBox("Select all packages")
        self.select_all.setVisible(False)
        self.select_all.toggled.connect(self._check_all)
        row.addWidget(self.select_all)
        self.update_btn = QPushButton("Update")
        self.update_btn.setObjectName("nugetUpdateSelected")
        self.update_btn.setVisible(False)
        self.update_btn.clicked.connect(self.update_checked)
        row.addWidget(self.update_btn)
        row.addStretch(1)
        row.addWidget(QLabel("Package source:"))
        self.source = QComboBox()
        self.source.setObjectName("nugetSource")
        self.source.setMinimumContentsLength(14)
        self.source.currentIndexChanged.connect(lambda _i: self.refresh())
        row.addWidget(self.source)
        gear = QToolButton()
        gear.setText("⚙")
        gear.setToolTip("Package Manager Settings")
        gear.clicked.connect(self.open_settings)
        row.addWidget(gear)
        root.addLayout(row)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=lambda: (self.search.setFocus(), self.search.selectAll()))

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.setObjectName("nugetList")
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list.currentItemChanged.connect(self._on_current)
        self.list.verticalScrollBar().valueChanged.connect(self._on_scroll)
        ll.addWidget(self.list, 1)
        self.status = QLabel("")
        self.status.setStyleSheet("color: gray;")
        ll.addWidget(self.status)
        split.addWidget(left)
        split.addWidget(self._build_details())
        split.setSizes([520, 560])
        root.addWidget(split, 1)

    def _build_details(self) -> QWidget:
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 4, 4, 4)
        head = QHBoxLayout()
        self.d_icon = QLabel()
        self.d_icon.setFixedSize(48, 48)
        head.addWidget(self.d_icon)
        self.d_title = QLabel()
        self.d_title.setObjectName("nugetDetailTitle")
        self.d_title.setTextFormat(Qt.TextFormat.RichText)
        self.d_title.setOpenExternalLinks(True)
        f = QFont(self.d_title.font())
        f.setPointSize(f.pointSize() + 4)
        self.d_title.setFont(f)
        head.addWidget(self.d_title, 1)
        lay.addLayout(head)
        self.d_warn = QLabel()
        self.d_warn.setObjectName("nugetWarning")
        self.d_warn.setWordWrap(True)
        self.d_warn.setTextFormat(Qt.TextFormat.RichText)
        self.d_warn.setOpenExternalLinks(True)
        self.d_warn.setVisible(False)
        lay.addWidget(self.d_warn)

        self.d_projects = QTreeWidget()
        self.d_projects.setObjectName("nugetProjects")
        self.d_projects.setHeaderLabels(["Project", "Version"])
        self.d_projects.setRootIsDecorated(False)
        self.d_projects.setMaximumHeight(150)
        self.d_projects.setVisible(self.solution)
        self.d_projects.itemChanged.connect(lambda *_: self._update_buttons())
        lay.addWidget(self.d_projects)

        r1 = QHBoxLayout()
        self.d_inst_label = QLabel("Installed:")
        r1.addWidget(self.d_inst_label)
        self.d_installed = QLineEdit()
        self.d_installed.setReadOnly(True)
        self.d_installed.setObjectName("nugetInstalled")
        r1.addWidget(self.d_installed, 1)
        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.setObjectName("nugetUninstall")
        self.uninstall_btn.clicked.connect(self.uninstall)
        r1.addWidget(self.uninstall_btn)
        lay.addLayout(r1)
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Version:"))
        self.d_version = QComboBox()
        self.d_version.setObjectName("nugetVersion")
        self.d_version.currentIndexChanged.connect(self._on_version)
        r2.addWidget(self.d_version, 1)
        self.install_btn = QPushButton("Install")
        self.install_btn.setObjectName("nugetInstall")
        self.install_btn.clicked.connect(self.install)
        r2.addWidget(self.install_btn)
        lay.addLayout(r2)

        self.opt_toggle = QToolButton()
        self.opt_toggle.setText("Options")
        self.opt_toggle.setCheckable(True)
        self.opt_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.opt_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.opt_toggle.setAutoRaise(True)
        lay.addWidget(self.opt_toggle)
        self.opt_box = QWidget()
        ol = QVBoxLayout(self.opt_box)
        ol.setContentsMargins(16, 0, 0, 0)
        self.opt_preview = QCheckBox("Show preview window")
        self.opt_preview.setChecked(self.show_preview)
        self.opt_preview.toggled.connect(self._set_preview)
        ol.addWidget(self.opt_preview)
        dr = QHBoxLayout()
        dr.addWidget(QLabel("Dependency behavior:"))
        self.opt_deps = QComboBox()
        for b in P.DEPENDENCY_BEHAVIORS:
            self.opt_deps.addItem({"IgnoreDependencies": "Ignore Dependencies", "HighestPatch": "Highest Patch",
                                   "HighestMinor": "Highest Minor"}.get(b, b), b)
        dr.addWidget(self.opt_deps, 1)
        ol.addLayout(dr)
        self.opt_deps_row_note = QLabel("Dependency behavior applies to packages.config projects.")
        self.opt_deps_row_note.setStyleSheet("color: gray;")
        ol.addWidget(self.opt_deps_row_note)
        self.opt_box.setVisible(False)
        self.opt_toggle.toggled.connect(lambda on: (self.opt_box.setVisible(on), self.opt_toggle.setArrowType(
            Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow)))
        lay.addWidget(self.opt_box)

        self.d_tabs = QTabWidget()
        self.d_details = QTextBrowser()
        self.d_details.setObjectName("nugetDetails")
        self.d_details.setOpenExternalLinks(True)
        self.d_readme = QTextBrowser()
        self.d_readme.setObjectName("nugetReadme")
        self.d_readme.setOpenExternalLinks(True)
        self.d_tabs.addTab(self.d_details, "Package Details")
        self.d_tabs.addTab(self.d_readme, "README")
        self.d_tabs.currentChanged.connect(lambda i: i == 1 and self._load_readme())
        lay.addWidget(self.d_tabs, 1)
        sa.setWidget(w)
        self._detail_widgets = [self.d_installed, self.uninstall_btn, self.d_version, self.install_btn]
        self._clear_details()
        return sa

    # ------------------------------------------------------------------ helpers
    def log(self, text: str) -> None:
        try:
            self.win.log(text)
        except Exception:  # noqa: BLE001
            print(text)

    def _busy(self, delta: int) -> None:
        self.busy = max(0, self.busy + delta)
        if alive(self.progress):
            self.progress.setVisible(self.busy > 0)

    def solution_folder(self):
        return self.projects[0].solution_folder if self.projects else None

    def _fill_sources(self) -> None:
        self.source.blockSignals(True)
        cur = self.source.currentText()
        self.source.clear()
        srcs = [s for s in effective_sources(self.solution_folder()) if s.enabled]
        if len(srcs) > 1:
            self.source.addItem("All", "__all__")
        for s in srcs:
            self.source.addItem(s.name, s)
        self.source.addItem("Global packages folder (offline)", "__global__")
        default = str(self.settings.value("nuget/source", "") or "")
        i = self.source.findText(cur or default)
        if i < 0:
            i = self.source.findText("nuget.org")
        self.source.setCurrentIndex(max(0, i))
        self.source.blockSignals(False)

    def feed(self):
        d = self.source.currentData()
        if d == "__all__":
            return AggregateFeed([feed_for(s) for s in effective_sources(self.solution_folder()) if s.enabled])
        if d == "__global__":
            return LocalFeed(global_packages_folder(self.solution_folder()), "Global packages folder")
        if isinstance(d, PackageSource):
            return feed_for(d)
        return feed_for(PackageSource("nuget.org", "https://api.nuget.org/v3/index.json"))

    def selected_projects(self) -> list[P.NuGetProject]:
        if not self.solution:
            return list(self.projects)
        out = []
        for i in range(self.d_projects.topLevelItemCount()):
            it = self.d_projects.topLevelItem(i)
            if it.checkState(0) == Qt.CheckState.Checked:
                out.append(it.data(0, Qt.ItemDataRole.UserRole))
        return out

    # ------------------------------------------------------------------ tabs / loading
    def set_tab(self, key: str) -> None:
        self.tab = key
        b = self.tab_buttons.get(key)
        if b is not None and not b.isChecked():
            b.setChecked(True)
        up = key == "updates"
        self.select_all.setVisible(up)
        self.update_btn.setVisible(up)
        self.refresh()

    def _on_text(self, _t: str) -> None:
        if self.tab != "browse":
            self._apply_filter()

    def refresh_all(self) -> None:
        http_cache_ttl_reset()
        self.refresh()
        self.refresh_badges()

    def refresh(self) -> None:
        self._gen += 1
        self.list.clear()
        self.records = []
        self._clear_details()
        if self.tab == "browse":
            self._skip = 0
            self._search()
        elif self.tab == "installed":
            self._load_installed()
        elif self.tab == "updates":
            self._load_updates()
        else:
            self._load_consolidate()

    def _search(self, more: bool = False) -> None:
        gen, q, pre, feed = self._gen, self.search.text().strip(), self.prerelease.isChecked(), self.feed()
        skip = self._skip
        installed = self._installed_map()
        self._busy(1)
        self.status.setText("Loading...")

        def got(res, err):
            self._busy(-1)
            if not alive(self) or gen != self._gen:
                return
            if err is not None:
                self.status.setText(f"Error: {err}")
                self.log(f"[NuGet] search failed: {err}")
                return
            rows, total = res
            recs = []
            for r in rows:
                rec = Record.from_search(r)
                rec.installed = installed.get(r.id.lower(), {})
                recs.append(rec)
            self._total = total
            self._skip = skip + len(rows)
            self._more = len(rows) >= PAGE and self._skip < total
            self._add_records(recs)
            self.status.setText(f"{len(self.records)} of {total} packages" if total else "No packages found")
            if not more and self.list.count() and self.list.currentRow() < 0:
                self.list.setCurrentRow(0)
        run_async(feed.search, got, q, pre, skip, PAGE)

    def _on_scroll(self, value: int) -> None:
        sb = self.list.verticalScrollBar()
        if self.tab == "browse" and self._more and not self.busy and value >= sb.maximum() - 4:
            self._more = False
            self._search(more=True)

    def _installed_map(self) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = {}
        for p in self.projects:
            try:
                for ip in p.installed():
                    out.setdefault(ip.id.lower(), {})[p.name] = ip.version
            except Exception as e:  # noqa: BLE001
                self.log(f"[NuGet] {p.name}: {e}")
        return out

    def _load_installed(self) -> None:
        gen, feed, pre = self._gen, self.feed(), self.prerelease.isChecked()
        projects = list(self.projects)
        self._busy(1)

        def work():
            top: dict[str, Record] = {}
            trans: dict[str, Record] = {}
            for p in projects:
                for ip in p.installed(include_transitive=not self.solution):
                    bucket = trans if ip.transitive else top
                    rec = bucket.setdefault(ip.id.lower(), Record(ip.id, transitive=ip.transitive))
                    rec.installed[p.name] = ip.version
            for rec in list(top.values()) + list(trans.values()):
                _enrich(rec, feed, pre)
            return sorted(top.values(), key=lambda r: r.id.lower()), sorted(trans.values(), key=lambda r: r.id.lower())

        def got(res, err):
            self._busy(-1)
            if not alive(self) or gen != self._gen:
                return
            if err is not None:
                self.status.setText(f"Error: {err}")
                return
            top, trans = res
            recs = []
            if trans:
                recs.append(Record("", header="Top-level packages"))
            recs += top
            if trans:
                recs.append(Record("", header="Transitive packages"))
                recs += trans
            self._add_records(recs)
            self._apply_filter()
            self.status.setText(f"{len(top)} installed package(s)")
            self._select_first()
        run_async(work, got)

    def _load_updates(self) -> None:
        gen, feed, pre = self._gen, self.feed(), self.prerelease.isChecked()
        projects = list(self.projects)
        self._busy(1)

        def work():
            ups = P.updates(projects, feed, pre)
            recs = []
            for pid, (latest, rows) in sorted(ups.items(), key=lambda kv: kv[0].lower()):
                rec = Record(pid, latest, installed={p.name: v for p, v in rows}, projects_versions=rows)
                _enrich(rec, feed, pre, keep_latest=True)
                recs.append(rec)
            return recs

        def got(recs, err):
            self._busy(-1)
            if not alive(self) or gen != self._gen:
                return
            if err is not None:
                self.status.setText(f"Error: {err}")
                return
            self._add_records(recs, checks=True)
            self._apply_filter()
            self._set_badge("updates", len(recs))
            self.status.setText(f"{len(recs)} update(s) available" if recs else "All packages are up to date.")
            self._select_first()
        run_async(work, got)

    def _load_consolidate(self) -> None:
        gen, feed, pre = self._gen, self.feed(), self.prerelease.isChecked()
        projects = list(self.projects)
        self._busy(1)

        def work():
            recs = []
            for pid, rows in sorted(P.consolidation(projects).items(), key=lambda kv: kv[0].lower()):
                rec = Record(pid, installed={p.name: v for p, v in rows}, projects_versions=rows)
                _enrich(rec, feed, pre)
                recs.append(rec)
            return recs

        def got(recs, err):
            self._busy(-1)
            if not alive(self) or gen != self._gen:
                return
            if err is not None:
                self.status.setText(f"Error: {err}")
                return
            self._add_records(recs)
            self._apply_filter()
            self._set_badge("consolidate", len(recs))
            self.status.setText(f"{len(recs)} package(s) to consolidate" if recs else
                                "No packages found that need consolidation.")
            self._select_first()
        run_async(work, got)

    def refresh_badges(self) -> None:
        feed, pre, projects = self.feed(), self.prerelease.isChecked(), list(self.projects)

        def work():
            return len(P.updates(projects, feed, pre)), len(P.consolidation(projects)) if self.solution else 0

        def got(res, err):
            if err is None and alive(self):
                self._set_badge("updates", res[0])
                self._set_badge("consolidate", res[1])
        run_async(work, got)

    def _set_badge(self, key: str, n: int) -> None:
        if key == "updates":
            self.update_count = n
        else:
            self.consolidate_count = n
        b = self.badges.get(key)
        if b is not None:
            b.setText(str(n))
            b.setVisible(n > 0)

    def _add_records(self, recs: list[Record], checks: bool = False) -> None:
        for rec in recs:
            it = QListWidgetItem()
            if rec.header:
                it.setText(rec.header)
                f = QFont(it.font())
                f.setBold(True)
                it.setFont(f)
                it.setFlags(Qt.ItemFlag.NoItemFlags)
                self.list.addItem(it)
            else:
                row = PackageRow(rec, checks)
                it.setSizeHint(QSize(100, max(row.sizeHint().height(), 52)))
                it.setData(Qt.ItemDataRole.UserRole, rec)
                self.list.addItem(it)
                self.list.setItemWidget(it, row)
            self.records.append(rec)

    def _apply_filter(self) -> None:
        q = self.search.text().strip().lower()
        for i in range(self.list.count()):
            it = self.list.item(i)
            rec = it.data(Qt.ItemDataRole.UserRole)
            if rec is None:
                continue
            it.setHidden(bool(q) and q not in rec.id.lower() and q not in rec.description.lower())

    def _select_first(self) -> None:
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(Qt.ItemDataRole.UserRole) is not None and not it.isHidden():
                self.list.setCurrentRow(i)
                return

    def _check_all(self, on: bool) -> None:
        for i in range(self.list.count()):
            w = self.list.itemWidget(self.list.item(i))
            if isinstance(w, PackageRow):
                w.check.setChecked(on)

    def checked_records(self) -> list[Record]:
        out = []
        for i in range(self.list.count()):
            w = self.list.itemWidget(self.list.item(i))
            if isinstance(w, PackageRow) and w.check.isChecked() and not self.list.item(i).isHidden():
                out.append(w.rec)
        return out

    def select_package(self, package_id: str) -> bool:
        for i in range(self.list.count()):
            rec = self.list.item(i).data(Qt.ItemDataRole.UserRole)
            if rec is not None and rec.id.lower() == package_id.lower():
                self.list.setCurrentRow(i)
                return True
        return False

    # ------------------------------------------------------------------ details
    def _clear_details(self) -> None:
        self.current = None
        self.d_title.setText("")
        self.d_icon.clear()
        self.d_warn.setVisible(False)
        self.d_details.setHtml("")
        self.d_readme.setHtml("")
        self.d_version.clear()
        self.d_installed.clear()
        self.d_projects.clear()
        for w in self._detail_widgets:
            w.setEnabled(False)

    def _on_current(self, item, _prev=None) -> None:
        rec = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if rec is None:
            return
        self.current = rec
        self.metas = {}
        self.d_title.setText(f"<b>{html.escape(rec.id)}</b> &nbsp;<a style='font-size:9pt' "
                             f"href='{package_page(rec.id)}'>nuget.org</a>"
                             + (" <span style='color:#1a7f37;font-size:9pt'>&#10004;</span>" if rec.verified else ""))
        load_icon(rec.icon_url, 48, lambda pm: alive(self.d_icon) and self.current is rec and self.d_icon.setPixmap(pm))
        self._fill_projects(rec)
        self.d_installed.setText(rec.installed_version if not self.solution else
                                 ", ".join(sorted(set(rec.installed.values()))))
        self._fill_versions(rec, rec.versions)
        self._load_details(rec)

    def _fill_projects(self, rec: Record) -> None:
        self.d_projects.blockSignals(True)
        self.d_projects.clear()
        if self.solution:
            for p in self.projects:
                it = QTreeWidgetItem([p.name, rec.installed.get(p.name, "")])
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(0, Qt.CheckState.Checked if (self.tab in ("updates", "consolidate") and
                                                              p.name in rec.installed) else Qt.CheckState.Unchecked)
                it.setData(0, Qt.ItemDataRole.UserRole, p)
                it.setToolTip(0, f"{p.path}\n{p.style_display}")
                self.d_projects.addTopLevelItem(it)
            self.d_projects.resizeColumnToContents(0)
        self.d_projects.blockSignals(False)

    def _fill_versions(self, rec: Record, versions: list[str]) -> None:
        pre = self.prerelease.isChecked()
        vs = [v for v in sort_versions(versions) if pre or not NuGetVersion.parse(v).is_prerelease or
              v in rec.installed.values()]
        cur = self.d_version.currentData()
        self.d_version.blockSignals(True)
        self.d_version.clear()
        if vs:
            stable = [v for v in vs if not NuGetVersion.parse(v).is_prerelease]
            top = (stable or vs)[0] if not pre else vs[0]
            self.d_version.addItem(f"Latest {'prerelease' if NuGetVersion.parse(top).is_prerelease else 'stable'} "
                                   f"{top}", top)
            for v in vs:
                label = v + ("  (installed)" if v in rec.installed.values() else "")
                self.d_version.addItem(label, v)
        target = cur if cur in vs else (rec.latest if self.tab in ("updates",) and rec.latest in vs else None)
        if target:
            i = next((k for k in range(1, self.d_version.count()) if self.d_version.itemData(k) == target), 0)
            self.d_version.setCurrentIndex(i)
        self.d_version.blockSignals(False)
        self._update_buttons()

    def _load_details(self, rec: Record) -> None:
        feed, gen = self.feed(), self._gen
        self._busy(1)

        def work():
            allm = feed.all_metadata(rec.id)
            versions = list(allm.keys()) or feed.versions(rec.id)
            return allm, versions

        def got(res, err):
            self._busy(-1)
            if not alive(self) or self.current is not rec or gen != self._gen:
                return
            if err is not None:
                self.d_details.setPlainText(f"Could not read the package details: {err}")
                return
            allm, versions = res
            self.metas = allm
            listed = [v for v, m in allm.items() if m.listed] or versions
            rec.versions = sort_versions(set(listed) | set(rec.installed.values()))
            if not rec.latest and rec.versions:
                rec.latest = rec.versions[0]
            self._fill_versions(rec, rec.versions)
            self._show_meta()
        run_async(work, got)

    def chosen_version(self) -> str:
        return self.d_version.currentData() or ""

    def _on_version(self, _i: int) -> None:
        self._update_buttons()
        self._show_meta()
        if self.d_tabs.currentIndex() == 1:
            self._load_readme()

    def _meta_for(self, version: str) -> PackageMetadata | None:
        want = NuGetVersion.try_parse(version)
        for v, m in self.metas.items():
            if NuGetVersion.try_parse(v) == want:
                return m
        return None

    def _show_meta(self) -> None:
        rec = self.current
        if rec is None:
            return
        m = self._meta_for(self.chosen_version())
        if m is None:
            self.d_details.setHtml(f"<h3>Description</h3><p>{html.escape(rec.description)}</p>")
            self.d_warn.setVisible(False)
            return
        warn = []
        if m.vulnerabilities:
            links = " ".join(f"<a href='{html.escape(v['url'])}'>advisory</a>" for v in m.vulnerabilities if v.get("url"))
            warn.append(f"<span style='color:#c42b1c'>&#9888; {html.escape(m.vulnerability_text())}</span> {links}")
        if m.deprecation:
            warn.append(f"<span style='color:#b35900'>&#9888; {html.escape(m.deprecation_text())}</span>")
        self.d_warn.setText("<br>".join(warn))
        self.d_warn.setVisible(bool(warn))
        self.d_details.setHtml(details_html(m, rec))

    def _load_readme(self) -> None:
        rec, ver, feed = self.current, self.chosen_version(), self.feed()
        if rec is None or not ver:
            return
        self.d_readme.setPlainText("Loading README...")

        def got(text, err):
            if not alive(self) or self.current is not rec:
                return
            if err is not None or not text:
                self.d_readme.setPlainText("This package does not have a README.")
            else:
                self.d_readme.setMarkdown(text)
        run_async(feed.readme, got, rec.id, ver)

    def _update_buttons(self) -> None:
        rec, ver = self.current, self.chosen_version()
        has = rec is not None and bool(ver)
        self.d_version.setEnabled(rec is not None and self.d_version.count() > 0)
        if self.solution:
            sel = self.selected_projects()
            can_install = has and any(rec.installed.get(p.name) != ver for p in sel)
            can_remove = rec is not None and any(p.name in rec.installed for p in sel)
            self.install_btn.setText("Install")
        else:
            inst = rec.installed_version if rec is not None else ""
            can_install = has and inst != ver
            can_remove = bool(inst) and not rec.transitive
            self.install_btn.setText("Update" if inst and not rec.transitive else "Install")
        self.install_btn.setEnabled(bool(can_install) and not self._running)
        self.uninstall_btn.setEnabled(bool(can_remove) and not self._running)
        self.d_installed.setEnabled(rec is not None)
        style = any(p.style == P.STYLE_PC for p in self.projects)
        self.opt_deps.setEnabled(style)

    _running = False

    def _set_preview(self, on: bool) -> None:
        self.show_preview = on
        self.settings.setValue("nuget/show_preview", "true" if on else "false")

    def open_settings(self) -> None:
        from .options_ui import package_sources_dialog
        if package_sources_dialog(self.win, self.solution_folder()):
            self._fill_sources()
            self.refresh()

    # ------------------------------------------------------------------ operations
    def install(self) -> None:
        rec, ver = self.current, self.chosen_version()
        if rec is None or not ver:
            return
        targets = self.selected_projects()
        if self.solution and not targets:
            QMessageBox.information(self, "NuGet Package Manager", "Select one or more projects first.")
            return
        ops = []
        for p in targets:
            cur = rec.installed.get(p.name, "")
            if cur == ver:
                continue
            ops.append((p, "update" if cur else "install", rec.id, ver))
        if not ops:
            return
        m = self._meta_for(ver)
        if m is not None and m.require_license_acceptance and not self.confirm_licenses([m]):
            self.log(f"[NuGet] License for {rec.id} {ver} declined: nothing was installed.")
            return
        self.run_ops(ops)

    def uninstall(self) -> None:
        rec = self.current
        if rec is None:
            return
        ops = [(p, "uninstall", rec.id, "") for p in self.selected_projects() if p.name in rec.installed]
        if ops:
            self.run_ops(ops)

    def update_checked(self) -> None:
        recs = self.checked_records()
        ops = []
        for rec in recs:
            for p, v in rec.projects_versions:
                if is_newer(rec.latest, v):
                    ops.append((p, "update", rec.id, rec.latest))
        if ops:
            self.run_ops(ops)

    def run_ops(self, ops: list[tuple], done=None) -> None:
        if self._running:
            return
        if self.show_preview:
            changes: dict[str, list[str]] = {}
            for p, verb, pid, ver in ops:
                cur = p.installed_version(pid)
                text = {"install": f"Installing: {pid}.{ver}", "uninstall": f"Uninstalling: {pid}.{cur}",
                        "update": f"Updating: {pid}.{cur} -> {pid}.{ver}"}[verb]
                changes.setdefault(p.name, []).append(text)
            if not self.confirm_preview(list(changes.items())):
                return
        behavior = self.opt_deps.currentData() or "Lowest"
        self._running = True
        self._update_buttons()
        self._busy(1)
        log = thread_log(self.log)
        self.log("========== Starting NuGet package operation ==========")

        def work():
            errors = []
            for p, verb, pid, ver in ops:
                try:
                    if verb == "install":
                        p.install(pid, ver, log, dependency_behavior=behavior)
                    elif verb == "update":
                        p.update(pid, ver, log)
                    else:
                        p.uninstall(pid, log)
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{p.name}: {e}")
                    log(f"[NuGet] {p.name}: {e}")
            return errors

        def got(errors, err):
            self._busy(-1)
            self._running = False
            errors = list(errors or []) + ([str(err)] if err else [])
            self.log("========== Finished ==========" if not errors else "========== Failed ==========")
            for p in {id(o[0]): o[0] for o in ops}.values():
                CX.reload_in_ide(self.win, p)
            if not alive(self):
                return
            if errors:
                QMessageBox.warning(self, "NuGet Package Manager", "\n".join(errors)[:3000])
            keep = self.current.id if self.current else ""
            self.refresh()
            self.refresh_badges()
            if keep:
                self._reselect = keep
                self._wait_reselect()
            if done:
                done(errors)
        run_async(work, got)

    _reselect = ""

    def _wait_reselect(self, tries: int = 60) -> None:
        if not alive(self) or not self._reselect:
            return
        if self.busy and tries > 0:
            QTimer.singleShot(100, lambda: self._wait_reselect(tries - 1))
            return
        self.select_package(self._reselect)
        self._reselect = ""


def http_cache_ttl_reset() -> None:
    """Refresh button: forget the in-memory registration data of the feeds (the disk cache has a TTL)."""
    try:
        from .feed import _FEEDS
        for f in _FEEDS.values():
            if hasattr(f, "_reg"):
                f._reg.clear()
            if hasattr(f, "_index") and isinstance(f, LocalFeed):
                f._index = None
    except Exception:  # noqa: BLE001
        pass


def _enrich(rec: Record, feed, prerelease: bool, keep_latest: bool = False) -> None:
    """Fill description / icon / latest version of an installed package (worker thread)."""
    try:
        m = feed.metadata(rec.id)
    except Exception:  # noqa: BLE001
        m = None
    if m is not None:
        rec.description = rec.description or m.description or m.summary
        rec.icon_url = rec.icon_url or m.icon_url
        rec.authors = rec.authors or m.authors
        rec.deprecated = rec.deprecated or bool(m.deprecation)
    if not keep_latest:
        try:
            rec.latest = feed.latest(rec.id, prerelease) or rec.latest
        except Exception:  # noqa: BLE001
            pass


def _date(s: str) -> str:
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return s
    return f"{d:%A, %B} {d.day}, {d.year} ({d.month}/{d.day}/{d.year})"


def details_html(m: PackageMetadata, rec: Record | None = None) -> str:
    from ...i18n import tr as _tr                    # labels inside HTML are not seen by the widget translator

    def row(k, v):
        return f"<tr><td style='padding-right:12px;color:gray' valign='top'><b>{_tr(k)}:</b></td><td>{v}</td></tr>"
    rows = [row("Version", html.escape(m.version))]
    if m.authors:
        rows.append(row("Author(s)", html.escape(m.authors)))
    if m.license_text:
        rows.append(row("License", f"<a href='{html.escape(m.license_link)}'>{html.escape(m.license_text)}</a>"
                        if m.license_link else html.escape(m.license_text)))
    if m.require_license_acceptance:
        rows.append(row("License acceptance", _tr("required")))
    if rec is not None and rec.downloads >= 0:
        rows.append(row("Downloads", f"{rec.downloads:,}"))
    if m.published and m.listed:
        rows.append(row("Date published", html.escape(_date(m.published))))
    if m.project_url:
        rows.append(row("Project URL", f"<a href='{html.escape(m.project_url)}'>{html.escape(m.project_url)}</a>"))
    if m.source and "nuget.org" in m.source.lower():
        abuse = f"https://www.nuget.org/packages/{m.id}/{m.version}/ReportAbuse"
        rows.append(row("Report Abuse", f"<a href='{abuse}'>{abuse}</a>"))
    if m.tags:
        rows.append(row("Tags", html.escape(m.tags)))
    deps = []
    for g in m.dependency_groups:
        from .versions import parse_tfm
        title = parse_tfm(g.framework).display() if g.framework else _tr("(any framework)")
        items = "".join(f"<li>{html.escape(d.id)} ({html.escape(VersionRange.parse(d.range).pretty() if d.range else '')})"
                        f"</li>" for d in g.dependencies) or f"<li style='color:gray'>{_tr('No dependencies')}</li>"
        deps.append(f"<p style='margin:4px 0 0 0'><b>{html.escape(title)}</b></p><ul style='margin-top:0'>{items}</ul>")
    desc = html.escape(m.description or m.summary).replace("\n", "<br>")
    return (f"<h3 style='margin-bottom:2px'>{_tr('Description')}</h3><p>{desc}</p><table>{''.join(rows)}</table>"
            f"<h3 style='margin-bottom:2px'>{_tr('Dependencies')}</h3>" +
            ("".join(deps) or f"<p style='color:gray'>{_tr('No dependencies')}</p>"))


# ====================================================================== open as a document
def open_manager(win, project=None, solution: bool = False) -> PackageManagerView | None:
    projects = CX.dotnet_projects(win)
    if not projects:
        QMessageBox.information(win, "NuGet Package Manager", "Open a .NET project or solution first.")
        return None
    if solution:
        targets, title, tab = projects, CX.solution_name(win), "NuGet - Solution"
    else:
        np = None
        if project is not None:
            path = getattr(getattr(project, "ms", None), "path", None)
            for p in projects:
                if (path is not None and os.path.normcase(str(p.path)) == os.path.normcase(str(path))) or \
                        p.ide_project is project:
                    np = p
                    break
        np = np or CX.current_project(win, projects)
        if np is None:
            return None
        targets, title, tab = [np], np.name, f"NuGet: {np.name}"
    tabs = getattr(win, "tabs", None)
    if tabs is not None:
        for i in range(tabs.count()):
            w = tabs.widget(i)
            if isinstance(w, PackageManagerView) and w.solution == solution and \
                    [p.path for p in w.projects] == [p.path for p in targets]:
                tabs.setCurrentIndex(i)
                return w
    view = PackageManagerView(win, targets, solution, title)
    if tabs is not None:
        tabs.setCurrentIndex(tabs.addTab(view, tab))
    else:
        view.show()
    win._nuget_view = view
    return view


__all__ = ["PackageManagerView", "open_manager", "license_dialog", "preview_dialog", "details_html", "Record"]
