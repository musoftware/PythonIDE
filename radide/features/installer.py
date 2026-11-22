"""Build > Publish / Create Installer... (VB 2005 "Publish" / Setup project, made simple).

One dialog edits the project's publish.json (radide/deploy/config.py): name, version, publisher, icon, license,
install for the current user (no admin) or all users, shortcuts, setup languages (English, Arabic, ...), file
association, optional code signing and update check. Publish then runs in the background with its log in the
Output window:  build the program (PyInstaller / VB runtime / GUI Bridge / ring2exe / Flutter / a ready folder)
-> Inno Setup setup.exe (+ portable zip) in <project>\\Publish.  Inno Setup is downloaded once, portably, into
%LOCALAPPDATA%\\RADIDE\\tools\\innosetup when it is missing (radide/deploy/tools.py).
"""
from __future__ import annotations

import os
import subprocess
import threading
import traceback
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                             QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMenu, QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget)

from .. import theme as T
from ..deploy import config as C
from ..deploy import tools as DT

KIND_LABELS = [("auto", "Automatic (from the startup form's language)"), ("pyinstaller", "Python program (PyInstaller)"),
               ("vbrun", "VB6 / BASIC program"), ("bridge", "GUI Bridge language (C, C#, Java, Go, ...)"),
               ("ring2exe", "Ring program (ring2exe)"), ("flutter", "Flutter Windows app"),
               ("folder", "An already built program folder")]


class _Signals(QObject):
    line = pyqtSignal(str)
    done = pyqtSignal(object, str)


def _browse_row(edit: QLineEdit, folder: Path, title: str, filt: str, directory: bool = False) -> QWidget:
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.addWidget(edit, 1)
    b = QPushButton("...")
    b.setFixedWidth(32)

    def pick():
        if directory:
            p = QFileDialog.getExistingDirectory(w, title, str(folder))
        else:
            p, _ = QFileDialog.getOpenFileName(w, title, str(folder), filt)
        if p:
            try:
                p = str(Path(p).resolve().relative_to(folder.resolve()))
            except ValueError:
                pass
            edit.setText(p)
    b.clicked.connect(pick)
    h.addWidget(b)
    return w


class PublishDialog(QDialog):
    """Edits publish.json; Publish (OK) saves and starts the build."""

    def __init__(self, win, folder: Path, project_name: str):
        super().__init__(win)
        self.win, self.folder = win, Path(folder)
        self.cfg = C.load(self.folder, project_name)
        self.setWindowTitle(f"Publish {self.cfg.app_name}")
        self.resize(640, 560)
        cfg = self.cfg
        lay = QVBoxLayout(self)
        intro = QLabel("Builds the program and a Windows setup (Inno Setup) into the project's Publish folder. "
                       "Users install it with a normal setup wizard; it appears in Apps & features with an "
                       "uninstaller.")
        intro.setWordWrap(True)
        T.role(intro, "muted")
        lay.addWidget(intro)
        tabs = QTabWidget()
        lay.addWidget(tabs, 1)

        # ---- Application
        page = QWidget()
        f = QFormLayout(page)
        self.e_name = QLineEdit(cfg.app_name)
        self.e_version = QLineEdit(cfg.version)
        self.e_version.setPlaceholderText("1.0.0")
        self.e_publisher = QLineEdit(cfg.publisher)
        self.e_url = QLineEdit(cfg.url)
        self.e_url.setPlaceholderText("https://example.com")
        self.e_exe = QLineEdit(cfg.exe_name)
        self.e_exe.setPlaceholderText(cfg.exe_base() + "  (default: the name without spaces)")
        self.e_icon = QLineEdit(cfg.icon)
        self.e_icon.setPlaceholderText(".ico or .png (converted)")
        self.kind = QComboBox()
        for k, label in KIND_LABELS:
            self.kind.addItem(label, k)
        self.kind.setCurrentIndex(max(0, self.kind.findData(cfg.build_kind)))
        self.console = QCheckBox("Show a console window (command-line programs)")
        self.console.setChecked(cfg.console)
        self.dotnet = QComboBox()           # native C# builds (deploy/native/dotnet_winforms.py)
        for k, label in (("standalone", "Standalone - one exe, nothing to install (largest)"),
                         ("framework", "Small - needs the .NET Desktop Runtime"),
                         ("netfx", "Tiny - for the .NET Framework 4.8 of Windows")):
            self.dotnet.addItem(label, k)
        self.dotnet.setCurrentIndex(max(0, self.dotnet.findData(getattr(cfg, "dotnet_target", "standalone"))))
        self.dotnet.setToolTip("How a C# program is published by the native build (no Python inside)")
        self.e_prebuilt = QLineEdit(cfg.prebuilt_dir)
        self.e_prebuilt_exe = QLineEdit(cfg.prebuilt_exe)
        f.addRow("Application &name:", self.e_name)
        f.addRow("&Version:", self.e_version)
        f.addRow("&Publisher:", self.e_publisher)
        f.addRow("Web site:", self.e_url)
        f.addRow("Program file name:", self.e_exe)
        f.addRow("&Icon:", _browse_row(self.e_icon, self.folder, "Icon", "Icons (*.ico *.png *.jpg *.bmp)"))
        f.addRow("&Build as:", self.kind)
        f.addRow("", self.console)
        f.addRow("C# program:", self.dotnet)
        self.prebuilt_rows = [_browse_row(self.e_prebuilt, self.folder, "Program folder", "", directory=True),
                              self.e_prebuilt_exe]
        f.addRow("Program folder:", self.prebuilt_rows[0])
        f.addRow("Main exe in it:", self.e_prebuilt_exe)
        self.kind.currentIndexChanged.connect(self._kind_changed)
        self._kind_changed()
        tabs.addTab(page, "Application")

        # ---- Setup
        page = QWidget()
        f = QFormLayout(page)
        self.per_user = QComboBox()
        self.per_user.addItem("Current user only (no administrator rights needed)", True)
        self.per_user.addItem("All users (asks for administrator rights)", False)
        self.per_user.setCurrentIndex(0 if cfg.per_user else 1)
        self.desktop = QCheckBox("Desktop shortcut (the user can untick it)")
        self.desktop.setChecked(cfg.desktop_icon)
        self.start_menu = QCheckBox("Start menu shortcut + uninstall shortcut")
        self.start_menu.setChecked(cfg.start_menu)
        self.run_after = QCheckBox("Offer to start the program at the end of the setup")
        self.run_after.setChecked(cfg.run_after_install)
        self.langs = QListWidget()
        self.langs.setMaximumHeight(120)
        iscc = DT.find_iscc()
        names = DT.inno_languages(iscc) if iscc else ["English", "Arabic", "French", "German", "Spanish", "Turkish"]
        chosen = {n.lower() for n in (cfg.languages or ["English"])}
        for n in names:
            it = QListWidgetItem(n)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if n.lower() in chosen else Qt.CheckState.Unchecked)
            self.langs.addItem(it)
        self.e_license = QLineEdit(cfg.license_file)
        self.e_readme = QLineEdit(cfg.readme_file)
        self.e_ext = QLineEdit(cfg.file_ext)
        self.e_ext.setPlaceholderText(".mydoc  (optional: double-clicking such files opens the program)")
        self.e_extdesc = QLineEdit(cfg.file_desc)
        self.e_out = QLineEdit(cfg.output_dir)
        self.zip = QCheckBox("Also make a portable .zip of the program")
        self.zip.setChecked(cfg.make_zip)
        self.make_setup = QCheckBox("Make the setup (uncheck to build the program folder only)")
        self.make_setup.setChecked(cfg.make_installer)
        f.addRow("Install for:", self.per_user)
        f.addRow("", self.desktop)
        f.addRow("", self.start_menu)
        f.addRow("", self.run_after)
        f.addRow("Setup languages:", self.langs)
        f.addRow("License file:", _browse_row(self.e_license, self.folder, "License", "Text (*.txt *.rtf);;All (*)"))
        f.addRow("Read-me before install:", _browse_row(self.e_readme, self.folder, "Read me",
                                                         "Text (*.txt *.rtf);;All (*)"))
        f.addRow("File type:", self.e_ext)
        f.addRow("File type description:", self.e_extdesc)
        f.addRow("Output folder:", self.e_out)
        f.addRow("", self.make_setup)
        f.addRow("", self.zip)
        tabs.addTab(page, "Setup")

        # ---- Signing + updates
        page = QWidget()
        v = QVBoxLayout(page)
        g = QGroupBox("Code signing (optional)")
        gf = QFormLayout(g)
        self.sign = QCheckBox("Sign the program and the setup with signtool")
        self.sign.setChecked(cfg.sign.enabled)
        self.e_pfx = QLineEdit(cfg.sign.pfx)
        self.e_thumb = QLineEdit(cfg.sign.thumbprint)
        self.e_thumb.setPlaceholderText("or the SHA1 thumbprint of a certificate in your store")
        self.sign_note = QLabel("")
        self.sign_note.setWordWrap(True)
        T.role(self.sign_note, "muted")
        gf.addRow("", self.sign)
        gf.addRow("Certificate (.pfx):", _browse_row(self.e_pfx, self.folder, "Certificate", "Certificates (*.pfx *.p12)"))
        gf.addRow("Thumbprint:", self.e_thumb)
        gf.addRow("", self.sign_note)
        v.addWidget(g)
        g = QGroupBox("Update check (optional)")
        gf = QFormLayout(g)
        self.upd = QCheckBox("The program checks a version.json on the web for a newer version")
        self.upd.setChecked(cfg.update.enabled)
        self.e_upd = QLineEdit(cfg.update.url)
        self.e_upd.setPlaceholderText("https://example.com/myapp/version.json")
        self.upd_start = QCheckBox("Check when the program starts")
        self.upd_start.setChecked(cfg.update.check_on_start)
        gf.addRow("", self.upd)
        gf.addRow("version.json URL:", self.e_upd)
        gf.addRow("", self.upd_start)
        v.addWidget(g)
        v.addStretch(1)
        tabs.addTab(page, "Signing and Updates")
        for w in (self.sign, self.e_pfx, self.e_thumb):
            (w.toggled if isinstance(w, QCheckBox) else w.textChanged).connect(self._sign_status)
        self._sign_status()

        self.tool_note = QLabel()
        self.tool_note.setWordWrap(True)
        if iscc:
            self.tool_note.setText(f"Inno Setup: {iscc}")
            T.role(self.tool_note, "muted")
        else:
            self.tool_note.setText("Inno Setup is not installed yet: Publish downloads it once (about 7 MB, "
                                   "official release from GitHub, installed portably for RAD IDE only).")
            T.role(self.tool_note, "note")
        lay.addWidget(self.tool_note)
        bb = QDialogButtonBox()
        self.b_publish = bb.addButton("&Publish", QDialogButtonBox.ButtonRole.AcceptRole)
        self.b_save = bb.addButton("&Save Settings", QDialogButtonBox.ButtonRole.ApplyRole)
        bb.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.b_publish.setDefault(True)
        bb.accepted.connect(self._publish)
        bb.rejected.connect(self.reject)
        self.b_save.clicked.connect(lambda: (self.collect(), C.save(self.folder, self.cfg),
                                             self.win.statusBar().showMessage("Publish settings saved", 3000)))
        lay.addWidget(bb)

    def _kind_changed(self):
        folder_kind = self.kind.currentData() == "folder"
        for w in self.prebuilt_rows:
            w.setEnabled(folder_kind)
        self.console.setEnabled(self.kind.currentData() in ("auto", "pyinstaller", "vbrun", "bridge"))

    def _sign_status(self, *_):
        from ..deploy import sign as S
        self.collect()
        if not self.sign.isChecked():
            self.sign_note.setText("Unsigned programs work, but Windows SmartScreen may warn on first start.")
            return
        ok, why = S.status(self.folder, self.cfg.sign)
        self.sign_note.setText(why)

    def collect(self) -> C.PublishConfig:
        c = self.cfg
        c.app_name = self.e_name.text().strip() or self.folder.name
        c.version = self.e_version.text().strip() or "1.0.0"
        c.publisher, c.url = self.e_publisher.text().strip(), self.e_url.text().strip()
        c.exe_name, c.icon = self.e_exe.text().strip(), self.e_icon.text().strip()
        c.build_kind, c.console = self.kind.currentData(), self.console.isChecked()
        c.dotnet_target = self.dotnet.currentData()
        c.prebuilt_dir, c.prebuilt_exe = self.e_prebuilt.text().strip(), self.e_prebuilt_exe.text().strip()
        c.per_user = bool(self.per_user.currentData())
        c.desktop_icon, c.start_menu = self.desktop.isChecked(), self.start_menu.isChecked()
        c.run_after_install = self.run_after.isChecked()
        c.languages = [self.langs.item(i).text() for i in range(self.langs.count())
                       if self.langs.item(i).checkState() == Qt.CheckState.Checked] or ["English"]
        c.license_file, c.readme_file = self.e_license.text().strip(), self.e_readme.text().strip()
        c.file_ext, c.file_desc = self.e_ext.text().strip(), self.e_extdesc.text().strip()
        c.output_dir = self.e_out.text().strip() or "Publish"
        c.make_zip, c.make_installer = self.zip.isChecked(), self.make_setup.isChecked()
        c.sign.enabled, c.sign.pfx, c.sign.thumbprint = (self.sign.isChecked(), self.e_pfx.text().strip(),
                                                         self.e_thumb.text().strip())
        c.update.enabled, c.update.url = self.upd.isChecked(), self.e_upd.text().strip()
        c.update.check_on_start = self.upd_start.isChecked()
        return c

    def _publish(self):
        self.collect()
        if self.cfg.update.enabled and not self.cfg.update.url.startswith(("https://", "http://")):
            QMessageBox.warning(self, "Publish", "Enter the web address of version.json for the update check, "
                                                 "or turn the update check off.")
            return
        C.save(self.folder, self.cfg)
        self.accept()


class Publisher:
    """Runs deploy.inno.publish in a thread; log lines go to the Output window."""

    def __init__(self, win):
        self.win = win
        self.running = False
        self.last = None
        self.sig = _Signals()
        self.sig.line.connect(self._line)
        self.sig.done.connect(self._done)

    def _line(self, text: str):
        try:
            self.win.log(text)
        except RuntimeError:
            pass

    def project_folder(self):
        p = getattr(self.win, "project", None)
        return (Path(p.folder), p.name) if p is not None else (None, "")

    def open_dialog(self):
        folder, name = self.project_folder()
        if folder is None:
            QMessageBox.information(self.win, "Publish", "Open a project first (File > Open Project).")
            return
        if self.running:
            QMessageBox.information(self.win, "Publish", "Publish is already running - see the Output window.")
            return
        dlg = PublishDialog(self.win, folder, name)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.start(folder, dlg.cfg)

    def start(self, folder: Path, cfg, wait: bool = False):
        """Publish *folder* with *cfg* (saves open files first). wait=True blocks (tests)."""
        from ..deploy import inno
        try:
            self.win.save_all()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.win.dock_output.show()
            self.win.dock_output.raise_()
        except Exception:  # noqa: BLE001
            pass
        self.running = True
        self.win.log(f"========== Publish {cfg.app_name} {cfg.version} ==========")
        self.win.statusBar().showMessage("Publishing... (see the Output window)")
        sig = self.sig

        def work():
            res, err = None, ""
            try:
                res = inno.publish(folder, cfg, log=lambda s: sig.line.emit(str(s)))
            except Exception as ex:  # noqa: BLE001 - BuildError / SetupError / anything: shown to the user
                err = str(ex) or type(ex).__name__
                if not isinstance(ex, (inno.SetupError,)) and type(ex).__name__ != "BuildError":
                    sig.line.emit(traceback.format_exc())
            try:
                sig.done.emit(res, err)
            except RuntimeError:            # the IDE was closed meanwhile
                pass
        t = threading.Thread(target=work, daemon=True, name="publish")
        t.start()
        if wait:
            from PyQt6.QtWidgets import QApplication
            while t.is_alive():
                QApplication.processEvents()
                t.join(0.05)
            QApplication.processEvents()
        return t

    def _done(self, res, err: str):
        self.running = False
        self.last = (res, err)
        if err:
            self.win.log(f"========== Publish failed: {err} ==========")
            self.win.statusBar().showMessage("Publish failed", 5000)
            if not getattr(self.win, "_rad_quiet_publish", False):
                QMessageBox.warning(self.win, "Publish failed", err)
            return
        target = res.setup or (res.dist / res.exe)
        self.win.log(f"========== Publish succeeded: {target} ==========")
        self.win.statusBar().showMessage(f"Published: {Path(target).name}", 8000)
        if getattr(self.win, "_rad_quiet_publish", False):
            return
        box = QMessageBox(self.win)
        box.setWindowTitle("Publish succeeded")
        box.setIcon(QMessageBox.Icon.Information)
        what = f"Setup: {res.setup.name}" if res.setup else f"Program: {res.dist / res.exe}"
        box.setText(f"{what}\n\nFolder: {Path(target).parent}")
        b_open = box.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
        b_run = box.addButton("Run Setup", QMessageBox.ButtonRole.ActionRole) if res.setup else None
        box.addButton(QMessageBox.StandardButton.Close)
        box.exec()
        if box.clickedButton() is b_open:
            os.startfile(str(Path(target).parent)) if os.name == "nt" else None
        elif b_run is not None and box.clickedButton() is b_run:
            subprocess.Popen([str(res.setup)])

    def open_output(self):
        folder, name = self.project_folder()
        if folder is None:
            return
        out = folder / (C.load(folder, name).output_dir or "Publish")
        out.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(out))


def _build_menu(win) -> QMenu | None:
    for a in win.menuBar().actions():
        if a.menu() is not None and a.text().replace("&", "").strip().lower() == "build":
            return a.menu()
    return None


def _attach(win, pub: Publisher) -> None:
    menu = _build_menu(win)
    if menu is None:                         # no Build menu (other layouts): put it under Project
        menu = next((a.menu() for a in win.menuBar().actions()
                     if a.menu() is not None and a.text().replace("&", "") == "Project"), None)
    if menu is None:
        return
    menu.addSeparator()
    a = QAction("P&ublish / Create Installer...", win)
    a.setShortcut(QKeySequence("Ctrl+Alt+F5"))
    a.setToolTip("Build the program and a Windows setup (Inno Setup) into the project's Publish folder")
    a.triggered.connect(lambda _c=False: pub.open_dialog())
    menu.addAction(a)
    win.a_publish = a
    b = QAction("Open Publish &Folder", win)
    b.triggered.connect(lambda _c=False: pub.open_output())
    menu.addAction(b)
    try:
        from .command_palette import register_command
        register_command("build.publish", "Build: Publish / Create Installer...", pub.open_dialog, "Build")
    except Exception:  # noqa: BLE001
        pass


def install(win) -> None:
    pub = Publisher(win)
    win.publisher = pub
    QTimer.singleShot(0, lambda: _attach(win, pub))     # the Build menu is made by later features


__all__ = ["PublishDialog", "Publisher", "install"]
