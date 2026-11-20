"""PHP versions and Composer in the IDE (radide/web_site/php_toolchain.py does the work).

- **Tools > Composer**: Install / Update / Require Package... / Remove Package... / Dump Autoload / Validate /
  Show Outdated / Open composer.json for the current project, run with *the project's* PHP (Site Settings
  "PHP version"), output in the Output window.
- **Tools > PHP Versions...**: every PHP found on the machine, "Install PHP 8.x" (official windows.php.net
  zip, SHA256 checked) and "Install / Update Composer" (getcomposer.org, SHA256 checked).
- :class:`PhpVersionCombo` - the "PHP version" row of Site Settings (``web.php`` in project.radproj).
- The package manager pane finds the portable Composer (``packages.resolve_tool`` asks
  :func:`php_toolchain.find_composer`) and intelephense gets the project's ``phpVersion``.
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QInputDialog,
                             QLabel, QMenu, QMessageBox, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from ..web_site import php_toolchain as tc


def _offscreen() -> bool:
    return os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"


def _background(win, fn, *args):
    from ..web_site.debug import _in_background
    return _in_background(win, fn, *args)


def install_php_series(win, series: str) -> str:
    """Download PHP <series> (asks first unless offscreen); returns php.exe or ""."""
    if not _offscreen():
        r = QMessageBox.question(win, "Install PHP",
                                 f"Download the official PHP {series} (NTS x64, about 32 MB) from windows.php.net "
                                 f"into\n{tc.PHP_ROOT / series}?\n\nPortable: no installer, no admin rights, PATH "
                                 "and registry are not changed. The SHA256 published by php.net is checked.")
        if r != QMessageBox.StandardButton.Yes:
            return ""
    lines: list[str] = []
    win.statusBar().showMessage(f"Downloading PHP {series}...")
    try:
        exe = _background(win, tc.install_php, series, lines.append)
    except Exception as e:  # noqa: BLE001 - network / checksum errors
        for ln in lines:
            win.log(f"[php] {ln}")
        win.log(f"*** Cannot install PHP {series}: {e}")
        win.statusBar().clearMessage()
        return ""
    for ln in lines:
        win.log(f"[php] {ln}")
    if tc.COMPOSER_PHAR.is_file():
        tc.write_composer_shim()
    win.statusBar().showMessage(f"PHP {series} installed", 6000)
    return exe


def install_composer(win) -> str:
    lines: list[str] = []
    try:
        bat = _background(win, tc.install_composer, lines.append)
    except Exception as e:  # noqa: BLE001
        for ln in lines:
            win.log(f"[composer] {ln}")
        win.log(f"*** Cannot install Composer: {e}")
        return ""
    for ln in lines:
        win.log(f"[composer] {ln}")
    return bat


# ============================================================================ Site Settings row
class PhpVersionCombo(QComboBox):
    """auto / IDE default / each detected PHP / Install PHP 8.x... / Browse... -> the ``web.php`` value."""

    def __init__(self, win, project, current: str = "", parent=None):
        super().__init__(parent)
        self.win, self.project = win, project
        self._initial = current
        self.setToolTip("The PHP that runs, debugs and installs packages for this site (project.radproj "
                        "\"web.php\").\nAutomatic = the newest installed PHP that satisfies composer.json "
                        "\"require.php\".")
        self.setMinimumContentsLength(40)
        self._fill(current)
        self.activated.connect(self._on_activated)

    def _fill(self, current: str) -> None:
        self.blockSignals(True)
        self.clear()
        folder = getattr(self.project, "folder", None)
        auto = tc.resolve("auto", folder)
        self.addItem(f"Automatic - newest installed ({_short(auto)})", "auto")
        configured = tc.configured_php(getattr(self.win, "settings", None))
        self.addItem(f"IDE default - Tools > Options ({_short(configured)})" if configured else
                     "IDE default - Tools > Options (not set: automatic)", "")
        seen_series: set[str] = set()
        for inst in tc.detect_installs():
            if inst.source == "RAD IDE toolchain" and inst.series not in seen_series:
                value = inst.series                     # portable across machines: "8.4"
            else:
                value = inst.path
            seen_series.add(inst.series)
            self.addItem(inst.label, value)
        have = {i.series for i in tc.detect_installs() if i.source == "RAD IDE toolchain"}
        for s in tc.SERIES_OFFERED:
            if s not in have:
                self.addItem(f"Install PHP {s} (download from windows.php.net)...", f"@install:{s}")
        self.addItem("Browse for php.exe...", "@browse")
        idx = self.findData(current)
        if idx < 0 and current:
            self.insertItem(2, f"{current}  ({_short(tc.resolve(current, folder)) or 'not found'})", current)
            idx = 2
        self.setCurrentIndex(max(idx, 0) if current else 1)
        self._last = self.currentIndex()
        self.blockSignals(False)

    def _on_activated(self, idx: int) -> None:
        data = str(self.itemData(idx) or "")
        if data.startswith("@install:"):
            exe = install_php_series(self.win, data.split(":", 1)[1])
            self._fill(data.split(":", 1)[1] if exe else self.itemData(self._last))
        elif data == "@browse":
            path = "" if _offscreen() else QFileDialog.getOpenFileName(self, "PHP executable", "",
                                                                       "php.exe (php.exe);;All files (*)")[0]
            if path and tc.probe(path):
                self._fill(path)
            else:
                self.setCurrentIndex(self._last)
        else:
            self._last = idx

    def value(self) -> str:
        data = str(self.currentData() or "")
        return "" if data.startswith("@") else data

    def applied(self) -> None:
        """After Site Settings saved web.php: tell intelephense about the new phpVersion."""
        if self.value() != self._initial:
            refresh_intelephense(self.win, self.project)


def _short(php: str) -> str:
    v = tc.php_version(php) if php else ""
    return f"PHP {v}" if v else "none found"


def refresh_intelephense(win, project=None) -> None:
    try:
        from ..lsp import workspace_settings
        mgr = getattr(win, "lsp_manager", None)
        for (key, root), client in list(getattr(mgr, "clients", {}).items()):
            if key == "php" and client is not None and client.running() and (
                    project is None or Path(root).resolve() == Path(project.folder).resolve()):
                client._notify("workspace/didChangeConfiguration",
                               {"settings": workspace_settings("php", client.root)})
    except Exception as e:  # noqa: BLE001
        win.log(f"[php] intelephense not updated: {e}")


# ============================================================================ Composer runner
def project_php(win, project) -> str:
    """The PHP for Composer / tools of *project* (website: web.php; other projects: Tools > Options)."""
    if project is None:
        return tc.configured_php(getattr(win, "settings", None)) or tc.resolve("auto")
    try:
        from ..languages import get_plugin
        from . import web_workspace as ww
        plugin = get_plugin(project.language)
        if getattr(plugin, "web_kind", "") == "php":
            return ww.server_interpreter(win, plugin, project)
    except Exception:  # noqa: BLE001
        pass
    return tc.php_for_folder(project.folder, getattr(win, "settings", None))


def _current_project(win):
    try:
        from .web_workspace import _site_project
        return _site_project(win)
    except Exception:  # noqa: BLE001
        return getattr(win, "project", None)


def run_composer(win, args: list[str], project=None, folder=None, wait: bool = False) -> QProcess | None:
    """Run ``composer <args>`` in the project folder with the project's PHP; output -> Output window."""
    project = project if project is not None else _current_project(win)
    folder = Path(folder or (project.folder if project is not None else os.getcwd()))
    php = project_php(win, project)
    if not tc.find_composer():
        if _offscreen() or QMessageBox.question(
                win, "Composer", "Composer is not installed.\n\nDownload the official composer.phar from "
                f"getcomposer.org into\n{tc.COMPOSER_DIR}?\n(SHA256 checked; no PATH changes)") == \
                QMessageBox.StandardButton.Yes:
            install_composer(win)
    argv = tc.composer_argv([*args, "--no-interaction", "--ansi"] if "--no-interaction" not in args
                            else list(args), php)
    if not argv:
        win.log("*** Composer is not installed (Tools > PHP Versions... > Install Composer).")
        return None
    old = getattr(win, "_composer_proc", None)
    if old is not None and old.state() != QProcess.ProcessState.NotRunning:
        win.log("*** Composer is already running - wait for it to finish.")
        return None
    proc = QProcess(win)
    proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    proc.setWorkingDirectory(str(folder))
    env = QProcessEnvironment.systemEnvironment()
    for k, v in tc.composer_env(php).items():
        env.insert(k, v)
    env.insert("COMPOSER_NO_INTERACTION", "1")
    proc.setProcessEnvironment(env)
    win.dock_output.show()
    win.dock_output.raise_()
    win.log(f"------ composer {' '.join(args)}   (PHP {tc.php_version(php) or '?'}: {php}; in {folder}) ------")
    import re
    ansi = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

    def read():
        text = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
        win._append_output(ansi.sub("", text.replace("\r\n", "\n")))

    def done(code, _status):
        read()
        win.log(f"------ composer {args[0] if args else ''} finished (exit code {code}) ------")
        win.statusBar().showMessage(f"composer {args[0] if args else ''}: "
                                    f"{'done' if code == 0 else f'failed ({code})'}", 8000)
        if code == 0 and args and args[0] in ("install", "update", "require", "remove", "dump-autoload",
                                              "create-project"):
            try:
                from .web_workspace import _refresh
                _refresh(win)
            except Exception:  # noqa: BLE001
                pass
    proc.readyReadStandardOutput.connect(read)
    proc.finished.connect(done)
    proc.start(argv[0], argv[1:])
    win._composer_proc = proc
    if wait:
        from PyQt6.QtCore import QEventLoop
        from PyQt6.QtWidgets import QApplication
        while proc.state() != QProcess.ProcessState.NotRunning:
            QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
            proc.waitForFinished(50)
        QApplication.processEvents()
    return proc


def _ask_package(win, title: str, label: str) -> str:
    if _offscreen():
        return ""
    text, ok = QInputDialog.getText(win, title, label)
    return text.strip() if ok else ""


def composer_require(win, package: str = "", dev: bool = False):
    package = package or _ask_package(win, "Composer - Require Package",
                                      "Package (vendor/name, optional :version), e.g. monolog/monolog or "
                                      "guzzlehttp/guzzle:^7.9\nadd --dev for a development package:")
    if not package:
        return None
    parts = package.split()
    if dev and "--dev" not in parts:
        parts.append("--dev")
    return run_composer(win, ["require", *parts])


def composer_remove(win, package: str = ""):
    package = package or _ask_package(win, "Composer - Remove Package", "Package (vendor/name):")
    return run_composer(win, ["remove", *package.split()]) if package else None


def open_composer_json(win):
    project = _current_project(win)
    if project is None:
        return
    path = Path(project.folder) / "composer.json"
    if not path.exists():
        if _offscreen() or QMessageBox.question(win, "Composer", "This project has no composer.json - create "
                                                "one (composer init)?") == QMessageBox.StandardButton.Yes:
            run_composer(win, ["init", "--name=radide/" + _slug(project.name), "--type=project"], project,
                         wait=True)
    if path.exists():
        opener = getattr(win, "open_file", None) or getattr(win, "open_path", None)
        if opener:
            opener(path)


def _slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-") or "app"


# ============================================================================ PHP Versions dialog
class PhpVersionsDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("PHP Versions")
        self.resize(820, 420)
        lay = QVBoxLayout(self)
        intro = QLabel("PHP installations found on this computer (newest first). A web site uses the one "
                       "chosen in <b>Site Settings &gt; PHP version</b> (Automatic = newest that fits "
                       "composer.json).")
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Version", "Build", "Source", "Path"])
        self.tree.setRootIsDecorated(False)
        lay.addWidget(self.tree, 1)
        self.composer = QLabel()
        lay.addWidget(self.composer)
        row = QHBoxLayout()
        self.install_buttons = {}
        for s in tc.SERIES_OFFERED:
            b = QPushButton(f"Install PHP {s}")
            b.clicked.connect(lambda _c=False, s=s: self._install(s))
            row.addWidget(b)
            self.install_buttons[s] = b
        b = QPushButton("Install / Update Composer")
        b.clicked.connect(self._composer)
        row.addWidget(b)
        row.addStretch(1)
        b = QPushButton("Refresh")
        b.clicked.connect(lambda: self.fill(refresh=True))
        row.addWidget(b)
        lay.addLayout(row)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.rejected.connect(self.reject)
        lay.addWidget(box)
        self.fill()

    def fill(self, refresh: bool = False):
        self.tree.clear()
        installs = tc.detect_installs(refresh=refresh)
        for i in installs:
            it = QTreeWidgetItem([i.version, f"{'TS' if i.ts else 'NTS'} x{'64' if i.bits == 64 else '86'}",
                                  i.source, i.path])
            self.tree.addTopLevelItem(it)
        for c in range(4):
            self.tree.resizeColumnToContents(c)
        have = {i.series for i in installs if i.source == "RAD IDE toolchain"}
        for s, b in self.install_buttons.items():
            b.setText(f"Update PHP {s}" if s in have else f"Install PHP {s}")
        comp = tc.find_composer()
        self.composer.setText(f"Composer: {comp}" if comp else "Composer: not installed")

    def _install(self, series: str):
        if install_php_series(self.win, series):
            self.fill(refresh=True)

    def _composer(self):
        install_composer(self.win)
        self.fill()


def php_versions_dialog(win, exec_: bool = True):
    dlg = PhpVersionsDialog(win)
    if exec_:
        dlg.exec()
    return dlg


# ============================================================================ install
def install(win) -> None:
    tools = next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Tools" and a.menu()),
                 None)
    win.run_composer = lambda args, project=None, **kw: run_composer(win, args, project, **kw)
    win.php_versions_dialog = lambda exec_=True: php_versions_dialog(win, exec_)
    if tools is None:
        return
    menu = QMenu("Co&mposer", win)
    menu.setObjectName("menu_composer")
    items = [("Install (composer install)", lambda: run_composer(win, ["install"])),
             ("Update (composer update)", lambda: run_composer(win, ["update"])),
             ("Require Package...", lambda: composer_require(win)),
             ("Remove Package...", lambda: composer_remove(win)),
             ("Dump Autoload (composer dump-autoload)", lambda: run_composer(win, ["dump-autoload"])),
             (None, None),
             ("Validate composer.json", lambda: run_composer(win, ["validate"])),
             ("Show Outdated Packages", lambda: run_composer(win, ["outdated", "--direct"])),
             ("Open composer.json", lambda: open_composer_json(win))]
    for text, fn in items:
        if text is None:
            menu.addSeparator()
            continue
        act = QAction(text, win)
        act.triggered.connect(lambda _c=False, fn=fn: fn())
        menu.addAction(act)
    tools.addSeparator()
    tools.addMenu(menu)
    act = QAction("PHP &Versions...", win)
    act.setObjectName("act_php_versions")
    act.triggered.connect(lambda: php_versions_dialog(win))
    tools.addAction(act)
    win.menu_composer = menu
    win.act_php_versions = act
