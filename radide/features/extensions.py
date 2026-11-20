"""Tools > Extensions...: the Extension Manager (install from a folder / .zip / git URL, enable, disable,
uninstall, add an extension's toolbox control to the project). The engine is radide/extensions; the
format and the API are documented in docs/PLUGIN_API.md."""
from __future__ import annotations

import os
import threading
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QDesktopServices
from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog, QHBoxLayout, QInputDialog, QLabel,
                             QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton,
                             QSplitter, QVBoxLayout, QWidget)

from .. import extensions as X
from .. import theme

DOCS = Path(__file__).resolve().parents[2] / "docs" / "PLUGIN_API.md"


def _run_bg(fn, done):
    """Run fn() on a worker thread; done(result, error) on the UI thread."""
    box = {}

    def work():
        try:
            box["r"] = fn()
        except Exception as e:  # noqa: BLE001
            box["e"] = e

    t = threading.Thread(target=work, daemon=True)
    t.start()
    timer = QTimer()

    def poll():
        if not t.is_alive():
            timer.stop()
            done(box.get("r"), box.get("e"))
    timer.timeout.connect(poll)
    timer.start(100)
    return timer


class ExtensionsDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Extensions")
        self.resize(860, 540)
        lay = QVBoxLayout(self)
        warn = QLabel("Extensions run Python code with your permissions. Install only extensions from "
                      "sources you trust. Changes apply at once; start the IDE with RADIDE_SAFE_MODE=1 to "
                      "skip all extensions.")
        warn.setWordWrap(True)
        theme.role(warn, "banner")
        lay.addWidget(warn)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.list = QListWidget()
        self.list.setAccessibleName("Installed extensions")
        self.list.setMinimumWidth(240)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.list.currentItemChanged.connect(lambda *_: self._show_details())
        split.addWidget(self.list)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        self.title = QLabel()
        theme.role(self.title, "heading")
        f = self.title.font()
        f.setPointSize(f.pointSize() + 3)
        f.setBold(True)
        self.title.setFont(f)
        self.meta = QLabel()
        theme.role(self.meta, "muted")
        self.desc = QLabel()
        self.desc.setWordWrap(True)
        self.contrib = QLabel()
        self.contrib.setWordWrap(True)
        self.where = QLabel()
        self.where.setWordWrap(True)
        self.where.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        theme.role(self.where, "muted")
        self.errors = QPlainTextEdit()
        self.errors.setReadOnly(True)
        self.errors.setPlaceholderText("No errors")
        self.errors.setAccessibleName("Extension errors")
        for w in (self.title, self.meta, self.desc, self.contrib, self.where):
            rl.addWidget(w)
        self.err_label = QLabel("Errors:")
        theme.role(self.err_label, "error")
        rl.addWidget(self.err_label)
        rl.addWidget(self.errors, 1)
        row = QHBoxLayout()
        self.b_toggle = QPushButton("Disable")
        self.b_toggle.clicked.connect(self._toggle)
        self.b_remove = QPushButton("Uninstall")
        self.b_remove.clicked.connect(self._uninstall)
        self.b_folder = QPushButton("Open Folder")
        self.b_folder.clicked.connect(self._open_folder)
        self.b_control = QPushButton("Add Control to Project...")
        self.b_control.clicked.connect(self._add_control)
        for b in (self.b_toggle, self.b_remove, self.b_folder, self.b_control):
            row.addWidget(b)
        row.addStretch(1)
        rl.addLayout(row)
        split.addWidget(right)
        split.setSizes([280, 580])
        lay.addWidget(split, 1)

        bottom = QHBoxLayout()
        for text, fn in (("Install from &Folder...", self._install_folder),
                         ("Install from &Zip...", self._install_zip),
                         ("Install from &Git URL...", self._install_git)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            bottom.addWidget(b)
        bottom.addStretch(1)
        b = QPushButton("Extensions Folder")
        b.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(X.extensions_dir()))))
        bottom.addWidget(b)
        b = QPushButton("Plugin API")
        b.clicked.connect(self._docs)
        bottom.addWidget(b)
        b = QPushButton("Close")
        b.clicked.connect(self.accept)
        bottom.addWidget(b)
        lay.addLayout(bottom)
        self._timer = None
        self.refresh()

    # ------------------------------------------------------------ list
    def refresh(self, select: str | None = None):
        cur = select or (self.current().id if self.current() else None)
        self.list.clear()
        exts = X.scan()
        for ext in exts:
            state = "error" if ext.errors else ("enabled" if ext.enabled else "disabled")
            it = QListWidgetItem(f"{ext.name}   {ext.version}   [{state}]")
            it.setData(Qt.ItemDataRole.UserRole, ext.id)
            it.setToolTip(ext.description or ext.id)
            self.list.addItem(it)
            if ext.id == cur:
                self.list.setCurrentItem(it)
        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)
        if not exts:
            self._show_details()

    def current(self):
        it = self.list.currentItem()
        return X.get(it.data(Qt.ItemDataRole.UserRole)) if it is not None else None

    def _show_details(self):
        ext = self.current()
        has = ext is not None
        for b in (self.b_toggle, self.b_remove, self.b_folder):
            b.setEnabled(has)
        if not has:
            self.title.setText("No extensions installed")
            self.meta.setText("")
            self.desc.setText("Install one from a folder, a .zip file or a git URL. Examples: "
                              "samples/Tests/Extensions.")
            self.contrib.setText("")
            self.where.setText(str(X.extensions_dir()))
            self.errors.setPlainText("")
            self.b_control.setEnabled(False)
            return
        self.title.setText(ext.name)
        self.meta.setText(f"{ext.id}  -  version {ext.version}" + (f"  -  by {ext.author}" if ext.author else "")
                          + ("  -  enabled" if ext.enabled else "  -  disabled")
                          + ("  -  running" if ext.active else ""))
        self.desc.setText(ext.description)
        self.contrib.setText(f"Contributes: {ext.summary()}")
        src = ""
        try:
            src = (ext.path / ".installed-from").read_text(encoding="utf-8")
        except OSError:
            pass
        self.where.setText(f"Folder: {ext.path}" + (f"\nInstalled from: {src}" if src else ""))
        self.errors.setPlainText("\n\n".join(ext.errors))
        self.err_label.setVisible(bool(ext.errors))
        self.b_toggle.setText("Disable" if ext.enabled else "Enable")
        self.b_control.setEnabled(bool(X.toolbox_items(ext)) and ext.enabled)

    # ------------------------------------------------------------ actions
    def _err(self, title, e):
        QMessageBox.warning(self, title, str(e))

    def _toggle(self):
        ext = self.current()
        if ext is None:
            return
        try:
            X.set_enabled(ext.id, not ext.enabled, self.win)
        except Exception as e:  # noqa: BLE001
            self._err("Extensions", e)
        self.refresh(ext.id)

    def _uninstall(self):
        ext = self.current()
        if ext is None:
            return
        if QMessageBox.question(self, "Uninstall", f"Uninstall {ext.name} {ext.version}?\n\n{ext.path} "
                                "will be deleted.") != QMessageBox.StandardButton.Yes:
            return
        try:
            X.uninstall(ext.id)
            self.win.log(f"[extensions] {ext.name} uninstalled")
        except Exception as e:  # noqa: BLE001
            self._err("Uninstall", e)
        self.refresh()

    def _open_folder(self):
        ext = self.current()
        if ext is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(ext.path)))

    def _add_control(self):
        ext = self.current()
        items = X.toolbox_items(ext) if ext else []
        if not items:
            return
        names = [i.get("name", "?") for i in items]
        name, ok = QInputDialog.getItem(self, "Add Control to Project", "Control:", names, 0, False)
        if not ok:
            return
        try:
            X.add_toolbox_control(self.win, ext, items[names.index(name)])
            self.win.log(f"[extensions] {name} added to the project - it is in the Toolbox")
        except Exception as e:  # noqa: BLE001
            self._err("Add Control", e)

    def _docs(self):
        if hasattr(self.win, "open_file") and DOCS.exists():
            try:
                self.win.open_file(str(DOCS))
                return
            except Exception:  # noqa: BLE001
                pass
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(DOCS)))

    def _confirm(self, folder: Path) -> bool:
        try:
            data = X.read_manifest(X._find_root(folder))
        except Exception as e:  # noqa: BLE001
            self._err("Install", e)
            return False
        tmp = X.Extension(data["id"], data["name"], data["version"], folder, data)
        old = X.get(data["id"])
        text = (f"{data['name']} {data['version']}\n{data['id']}\n\n{data.get('description', '')}\n\n"
                f"Contributes: {tmp.summary()}\n\n"
                + (f"This replaces the installed version {old.version}.\n\n" if old else "")
                + "Extensions run Python code with your permissions. Install it?")
        return QMessageBox.question(self, "Install Extension", text) == QMessageBox.StandardButton.Yes

    def _installed(self, ext, err):
        QApplication.restoreOverrideCursor()
        self._timer = None
        if err is not None:
            self._err("Install", err)
            return
        X.load(ext.id, self.win)
        self.win.log(f"[extensions] installed {ext.name} {ext.version} into {ext.path}")
        self.refresh(ext.id)

    def _install_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Extension folder (with radide-extension.json)")
        if d and self._confirm(Path(d)):
            try:
                self._installed(X.install_from_folder(d), None)
            except Exception as e:  # noqa: BLE001
                self._installed(None, e)

    def _install_zip(self):
        path, _ = QFileDialog.getOpenFileName(self, "Extension package", "", "Extension (*.zip *.radext)")
        if not path:
            return
        if QMessageBox.question(self, "Install Extension", f"Install the extension in\n{path}?\n\n"
                                "Extensions run Python code with your permissions.") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            self._installed(X.install_from_zip(path), None)
        except Exception as e:  # noqa: BLE001
            self._installed(None, e)

    def _install_git(self):
        url, ok = QInputDialog.getText(self, "Install from Git", "Repository URL (https://... or git@...):")
        if not ok or not url.strip():
            return
        if QMessageBox.question(self, "Install Extension", f"Clone and install\n{url}?\n\n"
                                "Extensions run Python code with your permissions.") \
                != QMessageBox.StandardButton.Yes:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self._timer = _run_bg(lambda: X.install_from_git(url), self._installed)


def show_extensions(win):
    dlg = ExtensionsDialog(win)
    win._extensions_dialog = dlg
    dlg.exec()


def install(win) -> None:
    act = QAction("E&xtensions...", win)
    act.setStatusTip("Install, enable, disable and uninstall IDE extensions")
    act.triggered.connect(lambda: show_extensions(win))
    win.a_extensions = act
    for a in win.menuBar().actions():
        if a.text().replace("&", "") == "Tools" and a.menu() is not None:
            m = a.menu()
            acts = m.actions()
            opts = next((x for x in acts if x.text().replace("&", "").startswith("Options")), None)
            if opts is not None:
                m.insertAction(opts, act)
            else:
                m.addAction(act)
            break
    else:
        win.menuBar().addMenu("&Tools").addAction(act)
    if os.environ.get("RADIDE_SAFE_MODE"):
        win.log("[extensions] safe mode (RADIDE_SAFE_MODE): no extension was loaded")
