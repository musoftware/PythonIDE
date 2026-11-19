"""App Gallery (WebMatrix "Site from Template" / "App Gallery", docs/CONTRACTS.md 8.5).

File > App Gallery... (and Site > App Gallery..., Start Page button) opens a dialog listing the web
templates of ``radide.web_site.gallery``: PHP Empty / Starter / PHP + SQLite Data App, HTML Bootstrap,
Node.js Express, Laravel (composer) and WordPress (+ SQLite). The project is created in a worker
thread with its progress in the dialog (downloads, composer, npm), then opened (or added to the open
solution). The same templates appear in File > New Project (Web group) through
``web_site.project.register_template``; for the slow ones (downloads / composer / npm) this module
wraps their creator so the New Project route shows a progress window instead of freezing the IDE."""
from __future__ import annotations

import threading
from pathlib import Path

from PyQt6.QtCore import QEventLoop, QObject, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit,
                             QProgressBar, QPushButton, QSplitter, QStyle, QVBoxLayout)

from ..web_site import gallery

CATEGORIES = ["All", "PHP", "HTML", "Node.js", "Applications"]


class _Relay(QObject):
    line = pyqtSignal(str)
    done = pyqtSignal(object, object)      # result, error


def run_in_thread(fn, on_line, on_done):
    """Run fn(log) in a thread; on_line(str) / on_done(result, error) are called in the GUI thread."""
    relay = _Relay()
    relay.line.connect(on_line)
    relay.done.connect(on_done)

    def work():
        try:
            result = fn(relay.line.emit)
        except BaseException as e:  # noqa: BLE001 - reported to the GUI
            relay.done.emit(None, e)
        else:
            relay.done.emit(result, None)
    t = threading.Thread(target=work, daemon=True, name="app-gallery")
    t._relay = relay                      # keep the QObject alive while the thread runs
    t.start()
    return t


def run_with_progress(parent, title: str, fn):
    """Run fn(log) in a thread while a modal window shows its output; return its result or raise."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.resize(640, 360)
    lay = QVBoxLayout(dlg)
    lay.addWidget(QLabel(f"<b>{title}</b> - please wait..."))
    bar = QProgressBar()
    bar.setRange(0, 0)
    lay.addWidget(bar)
    out = QPlainTextEdit()
    out.setReadOnly(True)
    out.setFont(QFont("Consolas", 9))
    lay.addWidget(out, 1)
    box = {}
    loop = QEventLoop()

    def finished(result, error):
        box["result"], box["error"] = result, error
        loop.quit()
    run_in_thread(fn, out.appendPlainText, finished)
    dlg.setModal(True)
    dlg.show()
    if "error" not in box:
        loop.exec()
    dlg.close()
    dlg.deleteLater()
    if box.get("error") is not None:
        raise box["error"]
    return box.get("result")


class AppGalleryDialog(QDialog):
    def __init__(self, win, preselect: str = ""):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("App Gallery")
        self.resize(980, 640)
        self._checks: dict[str, tuple[bool, str]] = {}
        self._thread = None
        self.created: Path | None = None
        from ..dialogs import default_location

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search templates (php, sqlite, wordpress, bootstrap, node ...)")
        self.search.textChanged.connect(self._filter)

        self.cats = QListWidget()
        self.cats.addItems(CATEGORIES)
        self.cats.setMaximumWidth(170)
        self.cats.currentRowChanged.connect(lambda _r: self._filter())

        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setIconSize(QSize(40, 40))
        self.list.setGridSize(QSize(160, 92))
        self.list.setMovement(QListWidget.Movement.Static)
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setWordWrap(True)
        for t in gallery.TEMPLATES:
            icon = self.style().standardIcon(getattr(QStyle.StandardPixmap, gallery.ICONS.get(t.id, "SP_FileIcon")))
            it = QListWidgetItem(icon, t.title)
            it.setData(Qt.ItemDataRole.UserRole, t.id)
            it.setToolTip(t.description)
            self.list.addItem(it)
        self.list.currentItemChanged.connect(lambda *_: self._selected())
        self.list.itemDoubleClicked.connect(lambda *_: self._create())

        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.TextFormat.RichText)
        self.details.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.details.setMinimumWidth(250)
        self.details.setStyleSheet("padding:10px; background: palette(base); border: 1px solid palette(mid);")

        split = QSplitter()
        split.addWidget(self.cats)
        split.addWidget(self.list)
        split.addWidget(self.details)
        split.setSizes([150, 480, 300])

        self.name = QLineEdit()
        self.location = QLineEdit(str(default_location()))
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        loc = QHBoxLayout()
        loc.addWidget(self.location, 1)
        loc.addWidget(browse)
        self.add_to_sln = QCheckBox()
        sln = getattr(win, "sln", None)
        if sln is not None and not getattr(sln, "implicit", True):
            self.add_to_sln.setText(f"Add to solution '{sln.name}'")
        else:
            self.add_to_sln.setVisible(False)
        self.where = QLabel()
        self.where.setStyleSheet("color: palette(mid);")
        self.name.textChanged.connect(self._update_where)
        self.location.textChanged.connect(self._update_where)
        self.add_to_sln.toggled.connect(self._update_where)
        form = QFormLayout()
        form.addRow("Site name:", self.name)
        form.addRow("Location:", loc)
        form.addRow("", self.add_to_sln)
        form.addRow("", self.where)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 9))
        self.log.setMaximumHeight(140)
        self.log.hide()

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.create_btn = self.buttons.addButton("Create", QDialogButtonBox.ButtonRole.AcceptRole)
        self.create_btn.setDefault(True)
        self.buttons.accepted.connect(self._create)
        self.buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(self.search)
        lay.addWidget(split, 1)
        lay.addLayout(form)
        lay.addWidget(self.progress)
        lay.addWidget(self.log)
        lay.addWidget(self.buttons)

        self.cats.setCurrentRow(0)
        row = next((i for i in range(self.list.count())
                    if self.list.item(i).data(Qt.ItemDataRole.UserRole) == (preselect or "php-sqlite-app")), 0)
        self.list.setCurrentRow(row)

    # ------------------------------------------------------------------ helpers
    def template(self) -> gallery.WebTemplate | None:
        it = self.list.currentItem()
        return gallery.get_template(it.data(Qt.ItemDataRole.UserRole)) if it is not None else None

    def folder(self) -> Path:
        name = self.name.text().strip()
        if self.add_to_sln.isVisible() and self.add_to_sln.isChecked():
            return Path(self.win.sln.folder) / name
        return Path(self.location.text().strip()) / name

    def _update_where(self, *_):
        self.where.setText(f"The site will be created in {self.folder()}")

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Location", self.location.text())
        if d:
            self.location.setText(d)

    def _filter(self, *_):
        q = self.search.text().strip().lower()
        cat = CATEGORIES[max(0, self.cats.currentRow())]
        for i in range(self.list.count()):
            it = self.list.item(i)
            t = gallery.get_template(it.data(Qt.ItemDataRole.UserRole))
            hay = " ".join([t.title, t.description, t.category, t.language, *t.features]).lower()
            it.setHidden(not ((cat == "All" or t.category == cat) and (not q or q in hay)))

    def _check(self, t) -> tuple[bool, str]:
        if t.id not in self._checks:
            self._checks[t.id] = gallery.check(t.id)
        return self._checks[t.id]

    def _unique_name(self, base: str) -> str:
        loc = Path(self.location.text().strip() or ".")
        i = 1
        while (loc / f"{base}{i}").exists():
            i += 1
        return f"{base}{i}"

    def _selected(self):
        t = self.template()
        if t is None:
            return
        ok, msg = self._check(t)
        cur = self.name.text().strip()
        if not cur or any(cur.startswith(x.default_name) and cur[len(x.default_name):].isdigit()
                          for x in gallery.TEMPLATES):
            self.name.setText(self._unique_name(t.default_name))
        from html import escape
        feats = "".join(f"<li>{escape(f)}</li>" for f in t.features)
        color = "#2E9E4F" if ok else "#D93025"
        lang = {"php-web": "PHP Web Site", "static-web": "HTML / CSS / JavaScript Site",
                "node-web": "Node.js Web Site"}.get(t.language, t.language)
        self.details.setText(
            f"<h3 style='margin-top:0'>{escape(t.title)}</h3><p>{escape(t.description)}</p>"
            + (f"<ul>{feats}</ul>" if feats else "")
            + f"<p><b>Project type:</b> {escape(lang)}<br><b>Web root:</b> {escape(t.root)}"
              f"<br><b>Start page:</b> {escape(t.start)}</p>"
              f"<p style='color:{color}'><b>{'Ready' if ok else 'Not available'}:</b> {escape(msg)}</p>")
        self.create_btn.setEnabled(ok and self._thread is None)
        self._update_where()

    # ------------------------------------------------------------------ create
    def _create(self):
        t = self.template()
        if t is None or self._thread is not None:
            return
        name = self.name.text().strip()
        from ..web_site.project import safe_name
        if not name or not safe_name(name):
            QMessageBox.warning(self, "App Gallery", "Enter a valid site name (no \\ / : * ? \" < > |).")
            return
        ok, msg = self._check(t)
        if not ok:
            QMessageBox.warning(self, "App Gallery", msg)
            return
        folder = self.folder()
        if folder.exists() and any(folder.iterdir()):
            QMessageBox.warning(self, "App Gallery", f"The folder {folder} already exists and is not empty.")
            return
        self.log.clear()
        self.log.show()
        self.progress.show()
        for w in (self.create_btn, self.list, self.name, self.location, self.cats, self.search):
            w.setEnabled(False)
        self._thread = run_in_thread(lambda log: gallery.create(t.id, folder, name, log=log),
                                     self.log.appendPlainText, self._finished)

    def _finished(self, result, error):
        self._thread = None
        self.progress.hide()
        for w in (self.create_btn, self.list, self.name, self.location, self.cats, self.search):
            w.setEnabled(True)
        if error is not None:
            self.log.appendPlainText(f"ERROR: {error}")
            QMessageBox.critical(self, "App Gallery", f"The site could not be created:\n{error}")
            return
        self.created = Path(result)
        self.accept()

    def reject(self):
        if self._thread is not None:
            QMessageBox.information(self, "App Gallery", "Please wait until the site has been created.")
            return
        super().reject()


# ===================================================================== IDE integration
def open_created(win, folder: Path, add_to_solution: bool) -> None:
    """Open the new site (a one-project solution) or add it to the open solution."""
    if add_to_solution and getattr(win, "sln", None) is not None:
        from ..workspace import add_project_to_solution
        from ..model import Project
        win.save_all()
        project = add_project_to_solution(win.sln, Project.load(folder))
        try:
            from .solution_ui import _open_new_project
            _open_new_project(win, project)
        except Exception:  # noqa: BLE001
            win.open_project(win.sln.file, ask=False, activate=folder)
    else:
        win.open_project(folder)
    win.log(f"[App Gallery] created {folder}")


def show_app_gallery(win, preselect: str = "") -> Path | None:
    dlg = AppGalleryDialog(win, preselect)
    if dlg.exec() and dlg.created is not None:
        open_created(win, dlg.created, dlg.add_to_sln.isVisible() and dlg.add_to_sln.isChecked())
        return dlg.created
    return None


def _wrap_heavy_templates(win) -> None:
    """New Project route: show a progress window for templates that download / run composer / npm."""
    try:
        from ..web_site.project import SiteTemplate, get_template, register_template
    except Exception:  # noqa: BLE001
        return
    for t in gallery.TEMPLATES:
        if not gallery.is_heavy(t):
            continue
        st = get_template(t.id)
        if st is None or not st.extra.get("gallery"):
            continue
        inner = gallery.site_creator(t)

        def create(folder, name, _inner=inner, _t=t):
            def work(log):
                old = gallery.progress_log
                gallery.progress_log = log
                try:
                    return _inner(folder, name)
                finally:
                    gallery.progress_log = old
            return run_with_progress(win, f"Creating {_t.title}", work)
        register_template(SiteTemplate(st.id, st.title, st.description, st.plugin_ids, create, st.order,
                                       st.icon, dict(st.extra)))


def _add_site_menu(win, action) -> None:
    menu = getattr(win, "site_menu", None)
    if menu is not None and action not in menu.actions():
        menu.addSeparator()
        menu.addAction(action)


def _start_page_button(win) -> None:
    try:
        from ..app import StartPage
    except Exception:  # noqa: BLE001
        return
    for i in range(win.tabs.count()):
        page = win.tabs.widget(i)
        if isinstance(page, StartPage) and not getattr(page, "_rad_gallery", False):
            b = QPushButton("App Gallery... (PHP, WordPress, Laravel, Bootstrap, Node.js sites)")
            b.setMinimumHeight(30)
            b.clicked.connect(lambda _=False: show_app_gallery(win))
            lay = page.layout()
            lay.insertWidget(min(3, lay.count()), b)
            page._rad_gallery = True


def install(win) -> None:
    gallery.progress_log = lambda s: win.log(s)
    act = QAction("App &Gallery...", win)
    act.setToolTip("Create a web site from a template: PHP + SQLite app, WordPress, Laravel, Bootstrap, Node.js")
    act.setIcon(win.style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon))
    act.triggered.connect(lambda: show_app_gallery(win))
    win.a_app_gallery = act
    win.show_app_gallery = lambda preselect="": show_app_gallery(win, preselect)
    file_menu = next((a.menu() for a in win.menuBar().actions() if a.menu() is not None
                      and a.text().replace("&", "") == "File"), None)
    if file_menu is not None:
        before = getattr(win, "a_open", None)
        if before is not None and before in file_menu.actions():
            file_menu.insertAction(before, act)
        else:
            file_menu.addAction(act)
    _wrap_heavy_templates(win)
    try:
        _start_page_button(win)
    except Exception as e:  # noqa: BLE001
        win.log(f"[App Gallery] start page: {e}")
    # the Site menu is created by features/web_workspace.py, which is installed after this module
    QTimer.singleShot(0, lambda: _add_site_menu(win, act))


__all__ = ["AppGalleryDialog", "install", "run_in_thread", "run_with_progress", "show_app_gallery"]
