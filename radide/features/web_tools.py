"""Web tools (docs/CONTRACTS.md 8.4): Publish (profiles dialog, FTP/FTPS/SFTP/folder, incremental,
dry run), Reports (SEO crawler dock + HTML export, Lighthouse) and SuperPreview.

Menu entries go into the web workspace's "Site" menu (win.site_menu) when it exists, otherwise into
a "Site" menu created here. Main-window hooks added: win.web_tools (WebTools), win.dock_reports."""
from __future__ import annotations

import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QKeySequence
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget, QFileDialog,
                             QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
                             QMenu, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSpinBox,
                             QSplitter, QStyle, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..web_site import publish as pub
from ..web_site import reports as rep


# ====================================================================== helpers
def _is_website(project) -> bool:
    try:
        from ..web_site.project import is_website
        return is_website(project)
    except Exception:  # noqa: BLE001
        return project is not None and str((project.extra or {}).get("kind", "")) == "website"


def _settings(win):
    s = getattr(win, "settings", None)
    if s is not None:
        return s
    from ..app import ide_settings
    return ide_settings()


def _site_project(win):
    """The website project to work on: the active one if it is a website, else the first website of
    the solution, else the active project."""
    p = getattr(win, "project", None)
    if p is not None and _is_website(p):
        return p
    try:
        for q in win.projects():
            if _is_website(q):
                return q
    except Exception:  # noqa: BLE001
        pass
    return p


class _Signals(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int, str)
    done = pyqtSignal(object)
    hostkey = pyqtSignal(object)            # HostKeyUnknown
    message = pyqtSignal(str)


# ====================================================================== Publish dialog
class PublishDialog(QDialog):
    """WebMatrix-style Publish Settings + Publish Preview + Publish."""
    published = pyqtSignal(object)           # PublishResult

    def __init__(self, win, project, parent=None):
        super().__init__(parent or win)
        self.win = win
        self.project = project
        self.setWindowTitle(f"Publish - {project.name}")
        self.resize(980, 680)
        self.profiles = pub.load_profiles(project) or [self._new_profile("Default")]
        self._publisher: pub.Publisher | None = None
        self._busy = False
        self._preview_profile = ""
        self.sig = _Signals()
        self.sig.log.connect(self._log)
        self.sig.progress.connect(self._on_progress)
        self.sig.done.connect(self._on_done)
        self.sig.hostkey.connect(self._on_hostkey)
        self.sig.message.connect(self._on_message)

        # ---------- profile list
        self.list = QListWidget()
        b_new, b_dup, b_del = QPushButton("New"), QPushButton("Duplicate"), QPushButton("Delete")
        left = QVBoxLayout()
        left.addWidget(QLabel("<b>Publish profiles</b>"))
        left.addWidget(self.list, 1)
        row = QHBoxLayout()
        for b in (b_new, b_dup, b_del):
            row.addWidget(b)
        left.addLayout(row)
        lw = QWidget()
        lw.setLayout(left)

        # ---------- settings form
        self.f_name = QLineEdit()
        self.f_kind = QComboBox()
        for k in pub.KINDS:
            self.f_kind.addItem(pub.KIND_LABELS[k], k)
        if not pub.paramiko_available():
            i = self.f_kind.findData("sftp")
            self.f_kind.setItemText(i, pub.KIND_LABELS["sftp"] + " - needs paramiko")
        self.f_host = QLineEdit(placeholderText="ftp.example.com")
        self.f_port = QSpinBox(minimum=0, maximum=65535, specialValueText="default")
        self.f_user = QLineEdit()
        self.f_pass = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.f_savepw = QCheckBox("Save password")
        self.f_savepw.setToolTip("Saved obfuscated (not encrypted) in your user settings - never in the "
                                 "project folder. Untick to be asked every time.")
        self.f_remote = QLineEdit(placeholderText="/public_html")
        self.b_browse = QPushButton("Browse...")
        self.f_siteurl = QLineEdit(placeholderText="https://www.example.com/")
        self.f_local = QLineEdit(placeholderText="(web root; the whole site folder when the root is a sub-folder)")
        self.f_passive = QCheckBox("Passive mode")
        self.f_verify = QCheckBox("Verify the server certificate")
        self.f_keyfile = QLineEdit(placeholderText="(optional) private key file")
        self.f_hostkey = QLineEdit(readOnly=True, placeholderText="(trusted on first connection)")
        self.b_clearkey = QPushButton("Forget")
        self.f_delete = QCheckBox("Delete remote files that were removed locally")
        self.f_excl = QPlainTextEdit()
        self.f_excl.setPlaceholderText("one pattern per line: .git, *.bak, uploads/tmp ...")
        self.f_excl.setMaximumHeight(110)
        form = QFormLayout()
        form.addRow("Profile name:", self.f_name)
        form.addRow("Method:", self.f_kind)
        self.lbl_host = QLabel("Server:")
        form.addRow(self.lbl_host, self.f_host)
        self.lbl_port = QLabel("Port:")
        form.addRow(self.lbl_port, self.f_port)
        self.lbl_user = QLabel("User name:")
        form.addRow(self.lbl_user, self.f_user)
        pw = QHBoxLayout()
        pw.addWidget(self.f_pass, 1)
        pw.addWidget(self.f_savepw)
        self.lbl_pass = QLabel("Password:")
        form.addRow(self.lbl_pass, pw)
        rr = QHBoxLayout()
        rr.addWidget(self.f_remote, 1)
        rr.addWidget(self.b_browse)
        self.lbl_remote = QLabel("Site path:")
        form.addRow(self.lbl_remote, rr)
        form.addRow("Destination URL:", self.f_siteurl)
        form.addRow("Local folder:", self.f_local)
        opts = QHBoxLayout()
        opts.addWidget(self.f_passive)
        opts.addWidget(self.f_verify)
        opts.addStretch(1)
        form.addRow("", opts)
        self.lbl_key = QLabel("Key file:")
        form.addRow(self.lbl_key, self.f_keyfile)
        hk = QHBoxLayout()
        hk.addWidget(self.f_hostkey, 1)
        hk.addWidget(self.b_clearkey)
        self.lbl_hostkey = QLabel("Host key:")
        form.addRow(self.lbl_hostkey, hk)
        form.addRow("", self.f_delete)
        form.addRow("Exclude:", self.f_excl)
        self.pw_note = QLabel()
        self.pw_note.setWordWrap(True)
        self.pw_note.setStyleSheet("color: #8a6d00")
        form.addRow("", self.pw_note)

        # ---------- preview / progress
        self.changes = QTreeWidget()
        self.changes.setHeaderLabels(["File", "Action", "Size"])
        self.changes.setColumnWidth(0, 380)
        self.changes.setRootIsDecorated(False)
        self.preview_label = QLabel("Press Preview to see which files will be published.")
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.status = QLabel("")
        self.status.setWordWrap(True)
        right = QVBoxLayout()
        right.addLayout(form)
        right.addWidget(self.preview_label)
        right.addWidget(self.changes, 1)
        right.addWidget(self.progress)
        right.addWidget(self.status)
        rw = QWidget()
        rw.setLayout(right)
        split = QSplitter()
        split.addWidget(lw)
        split.addWidget(rw)
        split.setSizes([200, 780])

        self.b_test = QPushButton("Test Connection")
        self.b_preview = QPushButton("Preview")
        self.b_preview.setToolTip("Dry run: list the files that would be uploaded / deleted")
        self.b_publish = QPushButton("Publish")
        self.b_publish.setDefault(True)
        self.b_force = QCheckBox("Upload all files")
        self.b_force.setToolTip("Ignore the record of what was published before")
        self.b_reset = QPushButton("Forget publish history")
        self.b_cancel = QPushButton("Cancel")
        self.b_cancel.setEnabled(False)
        self.b_open = QPushButton("Open site")
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        bottom = QHBoxLayout()
        for b in (self.b_test, self.b_preview, self.b_publish, self.b_force, self.b_cancel, self.b_reset,
                  self.b_open):
            bottom.addWidget(b)
        bottom.addStretch(1)
        bottom.addWidget(bb)
        lay = QVBoxLayout(self)
        lay.addWidget(split, 1)
        lay.addLayout(bottom)

        b_new.clicked.connect(self.add_profile)
        b_dup.clicked.connect(self.duplicate_profile)
        b_del.clicked.connect(self.delete_profile)
        self.list.currentRowChanged.connect(self._on_select)
        self.f_kind.currentIndexChanged.connect(self._update_fields)
        self.b_browse.clicked.connect(self._browse)
        self.b_clearkey.clicked.connect(lambda: self.f_hostkey.clear())
        self.b_test.clicked.connect(self.test_connection)
        self.b_preview.clicked.connect(lambda: self.start(dry_run=True))
        self.b_publish.clicked.connect(lambda: self.start(dry_run=False))
        self.b_cancel.clicked.connect(self.cancel)
        self.b_reset.clicked.connect(self.forget_history)
        self.b_open.clicked.connect(self.open_site)
        self._cur = -1
        self._fill_list()
        self.list.setCurrentRow(0)

    # ---------------------------------------------------------------- profiles
    def _new_profile(self, name: str) -> pub.PublishProfile:
        return pub.PublishProfile(name=name)

    def _fill_list(self):
        self.list.blockSignals(True)
        self.list.clear()
        for p in self.profiles:
            self.list.addItem(f"{p.name}  ({p.kind.upper()})")
        self.list.blockSignals(False)

    def _unique(self, base: str) -> str:
        names = {p.name for p in self.profiles}
        if base not in names:
            return base
        i = 2
        while f"{base} {i}" in names:
            i += 1
        return f"{base} {i}"

    def add_profile(self):
        self._store()
        self.profiles.append(self._new_profile(self._unique("Profile")))
        self._fill_list()
        self.list.setCurrentRow(len(self.profiles) - 1)

    def duplicate_profile(self):
        p = self.current()
        if p is None:
            return
        self._store()
        q = pub.PublishProfile.from_dict(p.to_dict())
        q.name = self._unique(p.name + " copy")
        self.profiles.append(q)
        self._fill_list()
        self.list.setCurrentRow(len(self.profiles) - 1)

    def delete_profile(self):
        p = self.current()
        if p is None or len(self.profiles) <= 1:
            return
        if QMessageBox.question(self, "Publish", f"Delete the profile '{p.name}'?") != \
                QMessageBox.StandardButton.Yes:
            return
        pub.set_password(_settings(self.win), self.project.folder, p.name, None)
        self.profiles.remove(p)
        self._cur = -1
        self._fill_list()
        self.list.setCurrentRow(0)
        self.save_profiles()

    def current(self) -> pub.PublishProfile | None:
        return self.profiles[self._cur] if 0 <= self._cur < len(self.profiles) else None

    def _on_select(self, row: int):
        self._store()
        self._cur = row
        p = self.current()
        if p is None:
            return
        self.f_name.setText(p.name)
        self.f_kind.setCurrentIndex(max(0, self.f_kind.findData(p.kind)))
        self.f_host.setText(p.host)
        self.f_port.setValue(int(p.port or 0))
        self.f_user.setText(p.user)
        stored = pub.get_password(_settings(self.win), self.project.folder, p.name)
        self.f_pass.setText(stored or "")
        self.f_savepw.setChecked(p.save_password)
        self.f_remote.setText(p.remote_dir)
        self.f_siteurl.setText(p.site_url)
        self.f_local.setText(p.local_dir)
        self.f_passive.setChecked(p.passive)
        self.f_verify.setChecked(p.verify_tls)
        self.f_keyfile.setText(p.key_file)
        self.f_hostkey.setText(p.host_key)
        self.f_delete.setChecked(p.delete_removed)
        self.f_excl.setPlainText("\n".join(p.excludes))
        self._update_fields()
        self.changes.clear()
        self.preview_label.setText("Press Preview to see which files will be published.")

    def _store(self):
        """Copy the form into the current profile (and the password into the user settings)."""
        p = self.current()
        if p is None:
            return
        old_name = p.name
        name = self.f_name.text().strip() or p.name
        if name != old_name and name in {q.name for q in self.profiles if q is not p}:
            name = self._unique(name)
        p.name = name
        p.kind = self.f_kind.currentData()
        p.host = self.f_host.text().strip()
        p.port = self.f_port.value()
        p.user = self.f_user.text().strip()
        p.remote_dir = self.f_remote.text().strip() or ("/" if p.kind != "folder" else "")
        p.site_url = self.f_siteurl.text().strip()
        p.local_dir = self.f_local.text().strip()
        p.passive = self.f_passive.isChecked()
        p.verify_tls = self.f_verify.isChecked()
        p.key_file = self.f_keyfile.text().strip()
        p.host_key = self.f_hostkey.text().strip()
        p.delete_removed = self.f_delete.isChecked()
        p.excludes = [x.strip() for x in self.f_excl.toPlainText().splitlines() if x.strip()]
        p.save_password = self.f_savepw.isChecked()
        st = _settings(self.win)
        if old_name != p.name:
            pub.set_password(st, self.project.folder, old_name, None)
        if p.kind != "folder":
            pub.set_password(st, self.project.folder, p.name,
                             self.f_pass.text() if p.save_password else None)
        item = self.list.item(self._cur)
        if item is not None:
            item.setText(f"{p.name}  ({p.kind.upper()})")

    def save_profiles(self):
        self._store()
        pub.save_profiles(self.project, self.profiles)

    def _update_fields(self):
        kind = self.f_kind.currentData()
        remote = kind != "folder"
        for w in (self.lbl_host, self.f_host, self.lbl_port, self.f_port, self.lbl_user, self.f_user,
                  self.lbl_pass, self.f_pass, self.f_savepw):
            w.setVisible(remote)
        self.f_passive.setVisible(kind in ("ftp", "ftps"))
        self.f_verify.setVisible(kind == "ftps")
        for w in (self.lbl_key, self.f_keyfile, self.lbl_hostkey, self.f_hostkey, self.b_clearkey):
            w.setVisible(kind == "sftp")
        self.b_browse.setVisible(not remote)
        self.lbl_remote.setText("Site path:" if remote else "Destination folder:")
        self.f_remote.setPlaceholderText("/public_html" if remote else r"D:\inetpub\wwwroot\MySite")
        self.b_test.setEnabled(not self._busy)
        if kind == "sftp" and not pub.paramiko_available():
            self.pw_note.setText("SFTP needs the paramiko package: .venv\\Scripts\\python -m pip install paramiko")
        elif remote:
            self.pw_note.setText("Passwords are never written to the project. With 'Save password' they are "
                                 "kept obfuscated (not encrypted) in your Windows user settings.")
        else:
            self.pw_note.setText("")

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Destination folder", self.f_remote.text())
        if d:
            self.f_remote.setText(d)

    # ---------------------------------------------------------------- running
    def _password(self, p: pub.PublishProfile) -> str | None:
        if p.kind == "folder":
            return None
        pw = self.f_pass.text()
        if pw or p.key_file:
            return pw
        pw, ok = QInputDialog.getText(self, "Publish", f"Password for {p.user}@{p.host}:",
                                      QLineEdit.EchoMode.Password)
        return pw if ok else None

    def _log(self, text: str):
        self.status.setText(text.strip().splitlines()[-1] if text.strip() else "")
        try:
            self.win.log(f"[publish] {text}")
        except Exception:  # noqa: BLE001
            pass

    def _on_progress(self, done: int, total: int, rel: str):
        self.progress.setMaximum(max(1, total))
        self.progress.setValue(min(done, total))
        self.progress.setFormat(f"%p%  {pub.fmt_size(done)} / {pub.fmt_size(total)}  {rel}")

    def _set_busy(self, busy: bool):
        self._busy = busy
        for b in (self.b_test, self.b_preview, self.b_publish, self.b_reset, self.list):
            b.setEnabled(not busy)
        self.b_cancel.setEnabled(busy)

    def _publisher_for(self, p: pub.PublishProfile, password) -> pub.Publisher:
        root = pub.local_root(self.project, p)
        return pub.Publisher(p, root, pub.cache_file_for(self.project.folder, p.name), password)

    def start(self, dry_run: bool = False, wait: bool = False):
        """Preview (dry run) or publish the current profile in a worker thread."""
        if self._busy:
            return
        self.save_profiles()
        p = self.current()
        if p is None:
            return
        if p.kind == "folder" and not p.remote_dir:
            QMessageBox.warning(self, "Publish", "Choose a destination folder first.")
            return
        if p.kind != "folder" and not p.host:
            QMessageBox.warning(self, "Publish", "Enter the server name first.")
            return
        password = None
        if not dry_run:
            password = self._password(p)
            if password is None and p.kind != "folder":
                return
        publisher = self._publisher_for(p, password)
        self._publisher = publisher
        force = self.b_force.isChecked()
        only = None
        if not dry_run and self._preview_profile == p.name and self.changes.topLevelItemCount():
            only = {self.changes.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole)
                    for i in range(self.changes.topLevelItemCount())
                    if self.changes.topLevelItem(i).checkState(0) == Qt.CheckState.Checked}
        self._set_busy(True)
        self.progress.setValue(0)
        if dry_run:
            self.changes.clear()
        sig = self.sig

        def work():
            try:
                if dry_run:
                    plan = publisher.plan(force)
                    sig.done.emit(("plan", p.name, plan))
                    return
                res = publisher.run(dry_run=False, force=force, only=only, log=sig.log.emit,
                                    progress=sig.progress.emit)
                sig.done.emit(("result", p.name, res))
            except pub.HostKeyUnknown as e:
                sig.hostkey.emit((e, dry_run))
            except Exception as e:  # noqa: BLE001
                r = pub.PublishResult(ok=False, error=str(e))
                sig.done.emit(("result", p.name, r))
        th = threading.Thread(target=work, daemon=True)
        th.start()
        if wait:
            th.join()

    def _on_done(self, payload):
        kind, name, obj = payload
        self._set_busy(False)
        if kind == "plan":
            self._show_plan(name, obj)
            return
        res: pub.PublishResult = obj
        self.last_result = res
        self.progress.setValue(self.progress.maximum() if res.ok else self.progress.value())
        self.status.setText(res.summary())
        if res.ok:
            self._preview_profile = ""
            self.changes.clear()
            self.preview_label.setText(res.summary())
        self.published.emit(res)

    def _show_plan(self, name: str, plan: pub.Plan):
        self._preview_profile = name
        self.changes.clear()
        style = self.style()
        icons = {"add": style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
                 "change": style.standardIcon(QStyle.StandardPixmap.SP_FileIcon),
                 "delete": style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon)}
        for rel in plan.uploads:
            action = "add" if rel in plan.new else "change"
            it = QTreeWidgetItem([rel, "Add" if action == "add" else "Update",
                                  pub.fmt_size(plan.local[rel]["size"])])
            it.setIcon(0, icons[action])
            it.setData(0, Qt.ItemDataRole.UserRole, rel)
            it.setCheckState(0, Qt.CheckState.Checked)
            self.changes.addTopLevelItem(it)
        for rel in plan.deletes:
            it = QTreeWidgetItem([rel, "Delete", ""])
            it.setIcon(0, icons["delete"])
            it.setData(0, Qt.ItemDataRole.UserRole, rel)
            it.setCheckState(0, Qt.CheckState.Checked)
            self.changes.addTopLevelItem(it)
        self.last_plan = plan
        msg = "Publish preview: " + plan.summary() + (". Untick files you do not want to publish now."
                                                      if plan.uploads or plan.deletes else ". Nothing to publish.")
        self.preview_label.setText(msg)
        self._log(msg)

    def _on_hostkey(self, payload):
        e, dry_run = payload
        self._set_busy(False)
        p = self.current()
        ans = QMessageBox.question(
            self, "Unknown SSH host",
            f"The server {p.host} is not known yet.\n\nKey fingerprint:\n{e.fingerprint}\n\n"
            "Trust this server and continue?")
        if ans == QMessageBox.StandardButton.Yes:
            self.f_hostkey.setText(e.key)
            self.save_profiles()
            if dry_run == "test":
                self.test_connection()
            else:
                self.start(dry_run=bool(dry_run))

    def _on_message(self, text: str):
        self._set_busy(False)
        self.status.setText(text)
        self._log(text)

    def cancel(self):
        if self._publisher is not None:
            self._publisher.cancel()
            self.status.setText("Cancelling after the current file ...")

    def test_connection(self):
        self.save_profiles()
        p = self.current()
        if p is None:
            return
        password = self._password(p)
        if password is None and p.kind != "folder":
            return
        self._set_busy(True)
        sig = self.sig

        def work():
            try:
                sig.message.emit(pub.test_connection(p, password))
            except pub.HostKeyUnknown as e:
                sig.hostkey.emit((e, "test"))
            except Exception as e:  # noqa: BLE001
                sig.message.emit(f"Connection failed: {e}")
        threading.Thread(target=work, daemon=True).start()

    def forget_history(self):
        p = self.current()
        if p is None:
            return
        self._publisher_for(p, None).forget()
        self.changes.clear()
        self._log(f"Publish history of '{p.name}' cleared: the next publish uploads every file.")

    def open_site(self):
        p = self.current()
        if p is None:
            return
        url = p.site_url or (QUrl.fromLocalFile(p.remote_dir).toString() if p.kind == "folder" else "")
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def done(self, r):  # noqa: D401 - QDialog.done: keep the profiles when closing
        if self._busy and self._publisher is not None:
            self._publisher.cancel()
        try:
            self.save_profiles()
        except Exception:  # noqa: BLE001
            pass
        super().done(r)


# ====================================================================== Reports dock
SEV_ICON = {"error": QStyle.StandardPixmap.SP_MessageBoxCritical,
            "warning": QStyle.StandardPixmap.SP_MessageBoxWarning,
            "info": QStyle.StandardPixmap.SP_MessageBoxInformation}


class ReportsPanel(QWidget):
    """Results of the SEO / site report (WebMatrix Reports workspace)."""
    finished = pyqtSignal(object)            # radide.web_site.reports.Report
    lighthouse_done = pyqtSignal(bool, str)

    def __init__(self, tools: "WebTools"):
        super().__init__()
        self.tools = tools
        self.report: rep.Report | None = None
        self._cancel = False
        self._busy = False
        self.sig = _Signals()
        self.sig.done.connect(self._on_done)
        self.sig.progress.connect(lambda n, _t, url: self.summary.setText(f"Checking ({n}) {url}"))
        self.sig.message.connect(lambda t: self.summary.setText(t))

        self.url = QLineEdit(placeholderText="Site address (empty = start the site's dev server)")
        self.b_run = QPushButton("Run SEO Report")
        self.b_stop = QPushButton("Stop")
        self.b_stop.setEnabled(False)
        self.b_export = QPushButton("Export HTML...")
        self.b_export.setEnabled(False)
        self.b_lh = QPushButton("Lighthouse")
        self.b_lh.setToolTip("Performance / accessibility / best practices / SEO audit with Google Lighthouse "
                             "(needs Node.js; downloaded by npx on first use)")
        self.ext = QCheckBox("Check external links")
        self.filter = QComboBox()
        self.filter.addItems(["All", "Errors", "Warnings", "Info"])
        self.search = QLineEdit(placeholderText="Filter...")
        self.search.setMaximumWidth(180)
        top = QHBoxLayout()
        top.setContentsMargins(2, 2, 2, 2)
        top.addWidget(self.url, 1)
        for w in (self.b_run, self.b_stop, self.ext, self.filter, self.search, self.b_export, self.b_lh):
            top.addWidget(w)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Issue", "Page", "Details"])
        self.tree.setColumnWidth(0, 380)
        self.tree.setColumnWidth(1, 220)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.summary = QLabel("Run a report to check titles, descriptions, headings, image alt texts, broken "
                              "links, page size and speed of every page.")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(top)
        lay.addWidget(self.tree, 1)
        lay.addWidget(self.summary)
        self.b_run.clicked.connect(lambda: self.run())
        self.b_stop.clicked.connect(self.stop)
        self.b_export.clicked.connect(lambda: self.export())
        self.b_lh.clicked.connect(lambda: self.lighthouse())
        self.filter.currentIndexChanged.connect(self._fill)
        self.search.textChanged.connect(self._fill)
        self.tree.itemDoubleClicked.connect(self._open_item)
        self.tree.customContextMenuRequested.connect(self._menu)
        self.lighthouse_done.connect(self._on_lighthouse)

    # ---------------------------------------------------------------- run
    def run(self, url: str | None = None, wait: bool = False, max_pages: int | None = None):
        if self._busy:
            return
        url = (url or self.url.text()).strip()
        server = None
        if not url:
            url, server = self.tools.site_url(purpose="report")
            if not url:
                return
        self.url.setText(url)
        self._busy = True
        self._cancel = False
        self.b_run.setEnabled(False)
        self.b_stop.setEnabled(True)
        self.summary.setText(f"Crawling {url} ...")
        self.tools.win.log(f"[reports] SEO report for {url}")
        sig = self.sig
        ext = self.ext.isChecked()
        dev = getattr(self.tools.win, "web_server", None)

        def work():
            try:
                if dev is not None and hasattr(dev, "wait_ready") and server is None:
                    try:
                        dev.wait_ready(30)
                    except Exception:  # noqa: BLE001
                        pass
                r = rep.crawl(url, max_pages=max_pages, check_external=ext,
                              progress=lambda n, u: sig.progress.emit(n, 0, u),
                              cancelled=lambda: self._cancel)
                sig.done.emit(r)
            except Exception as e:  # noqa: BLE001
                sig.done.emit(e)
            finally:
                if server is not None:
                    server.stop()
        th = threading.Thread(target=work, daemon=True)
        th.start()
        if wait:
            th.join()

    def stop(self):
        self._cancel = True

    def _on_done(self, r):
        self._busy = False
        self.b_run.setEnabled(True)
        self.b_stop.setEnabled(False)
        if isinstance(r, Exception):
            self.summary.setText(f"Report failed: {r}")
            self.tools.win.log(f"[reports] failed: {r}")
            return
        self.report = r
        self.b_export.setEnabled(True)
        self._fill()
        self.summary.setText(r.summary())
        self.tools.win.log(f"[reports] {r.summary()}")
        self.finished.emit(r)

    # ---------------------------------------------------------------- view
    def _fill(self):
        self.tree.clear()
        r = self.report
        if r is None:
            return
        want = {0: None, 1: "error", 2: "warning", 3: "info"}[self.filter.currentIndex()]
        needle = self.search.text().strip().lower()
        groups: dict[tuple[str, str], QTreeWidgetItem] = {}
        style = self.style()
        for i in r.issues:
            if want and i.severity != want:
                continue
            if needle and needle not in f"{i.rule} {i.url} {i.message} {i.detail}".lower():
                continue
            key = (i.severity, i.rule)
            g = groups.get(key)
            if g is None:
                g = QTreeWidgetItem([i.rule, "", ""])
                g.setIcon(0, style.standardIcon(SEV_ICON[i.severity]))
                f = g.font(0)
                f.setBold(True)
                g.setFont(0, f)
                self.tree.addTopLevelItem(g)
                groups[key] = g
            it = QTreeWidgetItem([i.message, rep._short(i.url, r.start_url), i.detail])
            it.setIcon(0, style.standardIcon(SEV_ICON[i.severity]))
            it.setToolTip(2, i.detail)
            it.setData(0, Qt.ItemDataRole.UserRole, i)
            g.addChild(it)
        for (sev, rule), g in groups.items():
            g.setText(0, f"{rule}  ({g.childCount()})")
            g.setText(2, sev)
            g.setExpanded(sev == "error" or len(groups) <= 4)

    def _issue(self, item) -> rep.Issue | None:
        return item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None

    def _open_item(self, item, _col=0):
        i = self._issue(item)
        if i is not None:
            self.tools.open_page_source(i.url) or self.tools.preview_url(i.url)

    def _menu(self, pos):
        i = self._issue(self.tree.itemAt(pos))
        if i is None:
            return
        m = QMenu(self)
        m.addAction("Open source file", lambda: self.tools.open_page_source(i.url, warn=True))
        m.addAction("Show page in Preview", lambda: self.tools.preview_url(i.url))
        m.addAction("Open page in browser", lambda: QDesktopServices.openUrl(QUrl(i.url)))
        m.exec(self.tree.viewport().mapToGlobal(pos))

    # ---------------------------------------------------------------- export / lighthouse
    def export(self, path: str | None = None) -> str | None:
        if self.report is None:
            return None
        if path is None:
            proj = _site_project(self.tools.win)
            start = str(Path(proj.folder) / "seo-report.html") if proj is not None else "seo-report.html"
            path, _ = QFileDialog.getSaveFileName(self, "Export report", start, "HTML (*.html)")
            if not path:
                return None
        Path(path).write_text(rep.report_html(self.report), encoding="utf-8")
        self.tools.win.log(f"[reports] exported {path}")
        return path

    def lighthouse(self, url: str | None = None, wait: bool = False, out: Path | None = None):
        url = (url or self.url.text()).strip()
        server = None
        if not url:
            url, server = self.tools.site_url(purpose="report")
            if not url:
                return
        if rep.npx_path() is None:
            QMessageBox.information(self, "Lighthouse", "Lighthouse needs Node.js (npx was not found).\n"
                                    "Install Node.js from nodejs.org, then try again.")
            return
        if out is None:
            proj = _site_project(self.tools.win)
            folder = (Path(proj.folder) / ".radide" / "reports") if proj is not None else Path.home()
            folder.mkdir(parents=True, exist_ok=True)
            out = folder / f"lighthouse-{time.strftime('%Y%m%d-%H%M%S')}.html"
        self.b_lh.setEnabled(False)
        self.summary.setText(f"Lighthouse is auditing {url} (the first run downloads it, this can take a "
                             "minute) ...")
        log = self.tools.log_threadsafe

        def work():
            try:
                ok = rep.run_lighthouse(url, out, log=log)
            finally:
                if server is not None:
                    server.stop()
            self.lighthouse_done.emit(ok, str(out))
        th = threading.Thread(target=work, daemon=True)
        th.start()
        if wait:
            th.join()

    def _on_lighthouse(self, ok: bool, path: str):
        self.b_lh.setEnabled(True)
        if ok:
            self.summary.setText(f"Lighthouse report: {path}")
            self.tools.preview_url(QUrl.fromLocalFile(path).toString())
        else:
            self.summary.setText("Lighthouse failed - see the Output window.")


# ====================================================================== the feature object
class WebTools(QObject):
    _log = pyqtSignal(str)

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self._log.connect(lambda t: win.log(t))
        self.servers: list[rep.LocalSiteServer] = []      # fallback servers we started
        self.superpreview = None
        self.panel = ReportsPanel(self)
        dock = QDockWidget("Reports", win)
        dock.setObjectName("Reports")
        dock.setWidget(self.panel)
        win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        try:
            win.tabifyDockWidget(win.dock_output, dock)
        except Exception:  # noqa: BLE001
            pass
        dock.hide()
        self.dock = dock
        win.dock_reports = dock

    def eventFilter(self, obj, event):  # noqa: N802 - stop our helper servers when the IDE closes
        if obj is self.win and event.type() == QEvent.Type.Close:
            QTimer.singleShot(0, lambda: None if self.win.isVisible() else self.shutdown())
        return False

    def log_threadsafe(self, text: str):
        self._log.emit(text)

    # ---------------------------------------------------------------- site address
    def site_url(self, purpose: str = "") -> tuple[str, rep.LocalSiteServer | None]:
        """(url, temporary server or None). Uses the running dev server, starts it, or falls back to
        a private php -S / http.server for the site folder; asks for an address otherwise."""
        win = self.win
        srv = getattr(win, "web_server", None)
        if srv is not None and getattr(srv, "running", False) and getattr(srv, "url", ""):
            return srv.url, None
        proj = _site_project(win)
        if proj is not None and _is_website(proj) and callable(getattr(win, "run_website", None)):
            try:
                win.run_website(proj)
            except TypeError:
                win.run_website()
            except Exception as e:  # noqa: BLE001
                win.log(f"[web tools] could not start the dev server: {e}")
            srv = getattr(win, "web_server", None)
            if srv is not None and getattr(srv, "url", ""):
                return srv.url, None
        if proj is not None:
            root = pub.site_root(proj)
            if root.is_dir() and (any(root.glob("*.htm*")) or any(root.glob("*.php"))):
                server = rep.LocalSiteServer(root)
                try:
                    url = server.start()
                    win.log(f"[web tools] serving {root} at {url} ({server.kind})")
                    if purpose != "report":
                        self.servers.append(server)
                    return url, server if purpose == "report" else None
                except Exception as e:  # noqa: BLE001
                    win.log(f"[web tools] {e}")
        url, ok = QInputDialog.getText(win, "Site address", "Address of the site:", text="http://127.0.0.1:8000/")
        return (url.strip(), None) if ok and url.strip() else ("", None)

    def preview_url(self, url: str) -> bool:
        pv = getattr(self.win, "web_preview", None)
        if pv is not None:
            for name in ("open_url", "navigate", "load"):
                fn = getattr(pv, name, None)
                if callable(fn):
                    fn(url)
                    if callable(getattr(pv, "show_dock", None)):
                        pv.show_dock()
                    return True
        QDesktopServices.openUrl(QUrl(url))
        return False

    def open_page_source(self, url: str, warn: bool = False) -> bool:
        proj = _site_project(self.win)
        if proj is None:
            return False
        path = None
        try:
            from ..web_site.project import file_for_url
            path = file_for_url(proj, urlparse(url).path or "/")
        except Exception:  # noqa: BLE001
            path = None
        if path is None:
            path = rep.file_for_url(url, pub.site_root(proj))
        if path is None:
            if warn:
                QMessageBox.information(self.win, "Reports", f"No source file was found for {url}")
            return False
        opener = getattr(self.win, "open_file", None)
        if callable(opener):
            opener(Path(path))
            return True
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        return True

    # ---------------------------------------------------------------- commands
    def publish(self) -> PublishDialog | None:
        proj = _site_project(self.win)
        if proj is None:
            QMessageBox.information(self.win, "Publish", "Open a web site project first.")
            return None
        dlg = PublishDialog(self.win, proj)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dlg.show()
        return dlg

    def publish_preview(self):
        dlg = self.publish()
        if dlg is not None:
            QTimer.singleShot(0, lambda: dlg.start(dry_run=True))

    def seo_report(self):
        self.dock.show()
        self.dock.raise_()
        self.panel.url.clear()
        self.panel.run()

    def lighthouse(self):
        self.dock.show()
        self.dock.raise_()
        self.panel.lighthouse()

    def open_superpreview(self, url: str | None = None):
        from ..web_site.superpreview import SuperPreview
        if not url:
            pv = getattr(self.win, "web_preview", None)
            view = getattr(pv, "view", None)
            cur = view.url().toString() if view is not None else ""
            url = cur if cur.startswith("http") else self.site_url(purpose="superpreview")[0]
        if not url:
            return None
        if self.superpreview is None:
            self.superpreview = SuperPreview(url)
            self.superpreview.destroyed.connect(lambda *_: setattr(self, "superpreview", None))
            self.superpreview.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        else:
            self.superpreview.go(url)
        self.superpreview.show()
        self.superpreview.raise_()
        self.superpreview.activateWindow()
        return self.superpreview

    def open_in_browser(self, name: str):
        from ..web_site.superpreview import open_in_browser
        url, _ = self.site_url(purpose="browser")
        if url:
            try:
                open_in_browser(name, url)
            except (OSError, FileNotFoundError) as e:
                QMessageBox.warning(self.win, "Open in browser", str(e))

    def shutdown(self):
        for s in self.servers:
            s.stop()
        self.servers.clear()
        if self.superpreview is not None:
            self.superpreview.close()

    # ---------------------------------------------------------------- menu
    def build_menu(self):
        win = self.win
        menu = getattr(win, "site_menu", None)
        if menu is None:
            menu = QMenu("&Site", win)
            mb = win.menuBar()
            before = next((a for a in mb.actions() if a.text().replace("&", "") in ("Tools", "Help")), None)
            mb.insertMenu(before, menu) if before is not None else mb.addMenu(menu)
            win.site_menu = menu
        menu.addSeparator()
        a = menu.addAction("&Publish...", self.publish)
        a.setShortcut(QKeySequence("Ctrl+Alt+P"))
        menu.addAction("Publish Pre&view (dry run)...", self.publish_preview)
        menu.addSeparator()
        menu.addAction("&SEO Report", self.seo_report)
        menu.addAction("&Lighthouse Report", self.lighthouse)
        menu.addAction(self.dock.toggleViewAction())
        menu.addSeparator()
        a = menu.addAction("Super&Preview...", self.open_superpreview)
        a.setShortcut(QKeySequence("Ctrl+Alt+B"))
        # the web workspace may already have an "Open in Browser" entry; ours lists each browser
        has_open = any(a.text().replace("&", "") == "Open in Browser" for a in menu.actions())
        sub = menu.addMenu("Open in Installed &Browser" if has_open else "Open in &Browser")
        sub.aboutToShow.connect(lambda: self._fill_browsers(sub))
        self.menu = menu

    def _fill_browsers(self, sub: QMenu):
        from ..web_site.superpreview import detect_browsers
        sub.clear()
        found = detect_browsers()
        for name in found:
            sub.addAction(name, lambda n=name: self.open_in_browser(n))
        if not found:
            sub.addAction("(no browser found)").setEnabled(False)
        sub.addSeparator()
        sub.addAction("Default browser", lambda: (lambda u: u and QDesktopServices.openUrl(QUrl(u)))(
            self.site_url(purpose="browser")[0]))


def install(win) -> None:
    tools = WebTools(win)
    win.web_tools = tools
    # after every feature is installed, so that the web workspace's Site menu exists
    QTimer.singleShot(0, tools.build_menu)
    win.installEventFilter(tools)
