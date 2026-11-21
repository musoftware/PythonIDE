"""Retro game development in the IDE (radide/retro/dev, radide/languages/retro_*.py, docs/RETRO.md).

* Error List: after Build / F5 the rows of the last build (DASM, ca65 / ld65 / cc65, RGBDS, sjasmplus messages,
  radide/retro/dev/errors.py) replace the old ones; double-click opens file:line.
* Editors of retro sources keep their own IntelliSense (6502 / SM83 / Z80): the x86 assembly overlay of
  radide/features/asm_ide.py is kept away from them.
* Tools > Retro > Retro Development: Disassemble ROM into Project..., Re-disassemble with Hints, Rebuild Check,
  Retro Toolchains... (DASM, cc65, RGBDS, sjasmplus: status and one-click download).
"""
from __future__ import annotations

import threading
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)


def _is_retro(project) -> bool:
    try:
        from ..retro.dev.systems import is_retro_project
        return is_retro_project(project)
    except Exception:  # noqa: BLE001
        return False


def _tr(text: str) -> str:
    try:
        from .. import i18n
        return i18n.tr(text)
    except Exception:  # noqa: BLE001
        return text


# ============================================================================ editor overlay guard
def keep_retro_plugin(plugin, path):
    """MonacoEditor.plugin_overlays entry (first in the list): a retro plugin stays itself, so the x86 assembly
    overlay that comes after it never replaces its 6502 / SM83 / Z80 IntelliSense."""
    if plugin is not None and getattr(plugin, "retro_dev", False):
        return plugin
    return None


# ============================================================================ Error List
def diag_provider(win) -> list:
    project = getattr(win, "project", None)
    if not _is_retro(project):
        return []
    from ..retro.dev.build import read_diagnostics
    from ..tools import Diag
    data = read_diagnostics(Path(project.folder))
    if not data or data.get("ok"):
        return []
    return [Diag(x["severity"], x["message"], x.get("file", ""), max(1, int(x.get("line") or 1)))
            for x in data.get("diags", [])]


def render_build_rows(win) -> None:
    from PyQt6.QtWidgets import QTreeWidgetItem
    project = getattr(win, "project", None)
    el = getattr(win, "error_list", None)
    if el is None or not _is_retro(project):
        return
    from ..retro.dev.build import read_diagnostics
    data = read_diagnostics(Path(project.folder))
    if not data:
        return
    for i in reversed(range(el.topLevelItemCount())):
        it = el.topLevelItem(i)
        if it.text(0) in ("Error", "Warning"):
            el.takeTopLevelItem(i)
    for x in data.get("diags", []):
        it = QTreeWidgetItem([x["severity"], x["message"], x.get("file", ""), str(max(1, int(x.get("line") or 1)))])
        colour = {"Error": Qt.GlobalColor.darkRed, "Warning": Qt.GlobalColor.darkYellow}.get(x["severity"])
        if colour is not None:
            it.setForeground(0, colour)
        el.addTopLevelItem(it)
    errors = sum(x["severity"] == "Error" for x in data.get("diags", []))
    warnings = sum(x["severity"] == "Warning" for x in data.get("diags", []))
    try:
        win.dock_errors.setWindowTitle(f"{_tr('Error List')} ({errors} errors, {warnings} warnings)")
        if not data.get("ok"):
            win.dock_errors.show()
            win.dock_errors.raise_()
    except Exception:  # noqa: BLE001
        pass


def _attach_session(win, s) -> None:
    state = {"buf": "", "done": False}

    def on_output(text: str) -> None:
        if state["done"]:
            return
        state["buf"] = (state["buf"] + text)[-4000:]
        if "Build succeeded" in state["buf"] or "Build failed" in state["buf"]:
            state["done"] = True
            QTimer.singleShot(0, lambda: render_build_rows(win))

    try:
        s.output.connect(on_output)
        s.finished.connect(lambda *_a: None if state["done"] else render_build_rows(win))
    except Exception:  # noqa: BLE001 - another kind of session
        pass


# ============================================================================ worker relay
class _Relay(QObject):
    log = pyqtSignal(str)
    done = pyqtSignal(object)


# ============================================================================ Disassemble ROM dialog
class DisassembleDialog(QDialog):
    """Pick a ROM (the user's own file), the system, where the project goes; disassemble + rebuild check."""

    SYSTEM_ITEMS = [("", "Detect from the file"), ("atari2600", "Atari 2600 (.bin / .a26)"),
                    ("nes", "NES (.nes)"), ("gameboy", "Game Boy (.gb / .gbc)"), ("c64", "Commodore 64 (.prg)"),
                    ("zx", "ZX Spectrum (.tap, or raw code + load address)")]

    def __init__(self, win, rom: str = ""):
        super().__init__(win)
        self.win = win
        self.result_obj = None
        self.setWindowTitle(_tr("Disassemble ROM into Project"))
        self.resize(720, 560)
        lay = QVBoxLayout(self)
        intro = QLabel(_tr("Turns a ROM or program file that you own into a project you can edit and rebuild: "
                           "the code is traced from the reset / interrupt vectors, hardware registers get their "
                           "names, and the new source is assembled again and compared with the original byte "
                           "for byte."))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        form = QFormLayout()
        self.rom = QLineEdit(rom)
        b = QPushButton(_tr("Browse..."))
        b.clicked.connect(self.browse)
        row = QHBoxLayout()
        row.addWidget(self.rom, 1)
        row.addWidget(b)
        w = QWidget()
        w.setLayout(row)
        form.addRow(_tr("ROM file:"), w)
        self.system = QComboBox()
        for sid, title in self.SYSTEM_ITEMS:
            self.system.addItem(_tr(title), sid)
        form.addRow(_tr("System:"), self.system)
        self.base = QLineEdit()
        self.base.setPlaceholderText(_tr("raw ZX code only, e.g. 8000"))
        form.addRow(_tr("Load address (hex):"), self.base)
        self.entry = QLineEdit()
        self.entry.setPlaceholderText(_tr("optional, hex"))
        form.addRow(_tr("Entry point (hex):"), self.entry)
        self.undoc = QCheckBox(_tr("Follow undocumented 6502 opcodes"))
        form.addRow("", self.undoc)
        self.folder = QLineEdit()
        fb = QPushButton(_tr("Browse..."))
        fb.clicked.connect(self.browse_folder)
        row2 = QHBoxLayout()
        row2.addWidget(self.folder, 1)
        row2.addWidget(fb)
        w2 = QWidget()
        w2.setLayout(row2)
        form.addRow(_tr("Project folder:"), w2)
        lay.addLayout(form)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        lay.addWidget(self.log, 1)
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.summary)
        self.buttons = QDialogButtonBox()
        self.go = self.buttons.addButton(_tr("Disassemble"), QDialogButtonBox.ButtonRole.ActionRole)
        self.open_btn = self.buttons.addButton(_tr("Open Project"), QDialogButtonBox.ButtonRole.AcceptRole)
        self.open_btn.setEnabled(False)
        self.buttons.addButton(QDialogButtonBox.StandardButton.Close)
        self.go.clicked.connect(self.run)
        self.open_btn.clicked.connect(self.open_project)
        self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)
        self.relay = _Relay()
        self.relay.log.connect(self.log.appendPlainText)
        self.relay.done.connect(self.finished)
        if rom:
            self._suggest_folder()

    def browse(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, _tr("ROM file"), "", "ROM / program files (*.bin *.a26 *.nes *.gb "
                                           "*.gbc *.prg *.tap);;All files (*)")
        if f:
            self.rom.setText(f)
            self._suggest_folder()

    def browse_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(self, _tr("Project folder"), self.folder.text())
        if d:
            self.folder.setText(d)

    def _suggest_folder(self) -> None:
        p = Path(self.rom.text())
        if p.name and not self.folder.text():
            try:
                from ..dialogs import default_location
                base = default_location()
            except Exception:  # noqa: BLE001
                base = Path.home()
            self.folder.setText(str(base / f"{p.stem}_disasm"))
        try:
            from ..retro.cpu.romfmt import detect
            sid = detect(p, p.read_bytes() if p.is_file() and p.stat().st_size < 16_000_000 else b"")
            i = self.system.findData(sid)
            if i >= 0 and self.system.currentIndex() == 0:
                self.system.setCurrentIndex(i)
        except OSError:
            pass

    @staticmethod
    def _hex(text: str):
        t = text.strip().lstrip("$").replace("0x", "")
        return int(t, 16) if t else None

    def run(self) -> None:
        rom, folder = self.rom.text().strip(), self.folder.text().strip()
        if not rom or not Path(rom).is_file() or not folder:
            QMessageBox.warning(self, self.windowTitle(), _tr("Choose a ROM file and a project folder."))
            return
        try:
            base, entry = self._hex(self.base.text()), self._hex(self.entry.text())
        except ValueError:
            QMessageBox.warning(self, self.windowTitle(), _tr("Addresses are hexadecimal numbers, e.g. 8000."))
            return
        system = self.system.currentData() or None
        undoc = self.undoc.isChecked()
        self.go.setEnabled(False)
        self.log.clear()
        self.summary.setText(_tr("Working..."))

        def work():
            from ..retro.dev.fromrom import create_project
            try:
                res = create_project(rom, folder, None, system, base, entry, undoc, log=self.relay.log.emit)
            except Exception as e:  # noqa: BLE001 - shown to the user
                res = e
            self.relay.done.emit(res)
        threading.Thread(target=work, daemon=True).start()

    def finished(self, res) -> None:
        self.go.setEnabled(True)
        if isinstance(res, Exception):
            self.summary.setText(f"{_tr('Could not disassemble')}: {res}")
            return
        self.result_obj = res
        txt = res.summary()
        same = (res.identical or {}).get("same")
        colour = "#1B7F1B" if same else "#B00020"
        self.summary.setText(f"<span style='color:{colour}'>" + txt.replace("\n", "<br>") + "</span>")
        self.open_btn.setEnabled(True)

    def open_project(self) -> None:
        if self.result_obj is not None:
            folder = self.result_obj.folder
            self.accept()
            try:
                self.win.open_project(folder)
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(self.win, _tr("Open Project"), str(e))


def show_disassemble(win, rom: str = "") -> None:
    DisassembleDialog(win, rom).exec()


def redisassemble(win) -> None:
    project = getattr(win, "project", None)
    s = ((getattr(project, "extra", {}) or {}).get("retro") or {}) if project is not None else {}
    if not s.get("disassembly"):
        QMessageBox.information(win, _tr("Re-disassemble with Hints"),
                                _tr("The active project was not made with 'Disassemble ROM into Project'."))
        return
    if QMessageBox.question(win, _tr("Re-disassemble with Hints"),
                            _tr("Disassemble the original ROM again with hints.json? The main source is saved "
                                "as a .bak file first and then replaced.")) != QMessageBox.StandardButton.Yes:
        return
    try:
        from ..retro.dev.fromrom import redisassemble as redo
        res = redo(project.folder, log=win.log)
    except Exception as e:  # noqa: BLE001
        QMessageBox.warning(win, _tr("Re-disassemble with Hints"), str(e))
        return
    win.log(res.summary())
    try:
        for i in range(win.tabs.count()):
            w = win.tabs.widget(i)
            if hasattr(w, "path") and Path(str(w.path)).name == res.main and hasattr(w, "setText"):
                w.setText((Path(project.folder) / res.main).read_text(encoding="utf-8"))
                if hasattr(w, "setModified"):
                    w.setModified(False)
    except Exception:  # noqa: BLE001
        pass
    QMessageBox.information(win, _tr("Re-disassemble with Hints"), res.summary())


def rebuild_check(win) -> None:
    project = getattr(win, "project", None)
    if not _is_retro(project):
        QMessageBox.information(win, _tr("Rebuild Check"), _tr("Open a retro game project first."))
        return
    from ..retro.dev.build import Builder
    lines: list[str] = []
    b = Builder(Path(project.folder), project, log=lines.append)
    ok = b.build()
    render_build_rows(win)
    for ln in lines:
        win.log(ln)
    if not ok:
        QMessageBox.warning(win, _tr("Rebuild Check"), _tr("The build failed - see the Error List."))
        return
    if not b.s.get("original"):
        QMessageBox.information(win, _tr("Rebuild Check"), f"{_tr('Built')} {b.out_path.name}")
        return
    from ..retro.dev.build import read_diagnostics
    same = (read_diagnostics(Path(project.folder)) or {}).get("identical") or {}
    msg = (_tr("Byte-identical to the original ROM.") if same.get("same") else
           f"{_tr('Different from the original ROM')}: {same.get('reason', '')}")
    QMessageBox.information(win, _tr("Rebuild Check"), msg)


# ============================================================================ toolchains dialog
class RetroToolchainsDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.setWindowTitle(_tr("Retro Toolchains"))
        self.resize(780, 420)
        lay = QVBoxLayout(self)
        intro = QLabel(_tr("Assemblers of the retro game projects. They are downloaded from their official "
                           "release pages into the IDE's tools folder (no admin rights, no PATH change); the "
                           "SHA-256 of each archive is checked and recorded."))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([_tr("Tool"), _tr("Path"), ""])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        lay.addWidget(self.table, 1)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(130)
        lay.addWidget(self.log)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.relay = _Relay()
        self.relay.log.connect(self.log.appendPlainText)
        self.relay.done.connect(lambda _r: self.refresh())
        self.refresh()

    def refresh(self) -> None:
        from ..retro.dev import toolchain as tc
        rows = tc.status()
        self.table.setRowCount(len(rows))
        for i, (tool, title, path) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(title))
            self.table.setItem(i, 1, QTableWidgetItem(path or _tr("not found")))
            if not path and tool in tc.RELEASES:
                b = QPushButton(_tr("Download"))
                b.clicked.connect(lambda _c=False, t=tool: self.download(t))
                self.table.setCellWidget(i, 2, b)
            else:
                self.table.setCellWidget(i, 2, None)
                self.table.setItem(i, 2, QTableWidgetItem(_tr("ready") if path else "-"))
        self.table.resizeColumnToContents(0)

    def download(self, tool: str) -> None:
        from ..retro.dev import toolchain as tc

        def work():
            tc.install(tool, self.relay.log.emit)
            self.relay.done.emit(None)
        threading.Thread(target=work, daemon=True).start()


def show_toolchains(win) -> None:
    RetroToolchainsDialog(win).exec()


# ============================================================================ install
def install(win) -> None:
    try:
        from ..monaco_editor import MonacoEditor
        if keep_retro_plugin not in MonacoEditor.plugin_overlays:
            MonacoEditor.plugin_overlays.insert(0, keep_retro_plugin)
    except Exception:  # noqa: BLE001 - the plain editor has no overlays
        pass
    providers = getattr(win, "diag_providers", None)
    if providers is None:
        win.diag_providers = providers = []
    providers.append(diag_provider)

    orig = getattr(win, "_make_session", None)
    if callable(orig):
        def make_session(spec, debug, plugin, interp, startup=None):
            s = orig(spec, debug, plugin, interp, startup)
            try:
                if s is not None and getattr(plugin, "retro_dev", False):
                    _attach_session(win, s)
            except Exception:  # noqa: BLE001 - never stop F5
                pass
            return s
        win._make_session = make_session

    win.show_retro_disassemble = lambda rom="": show_disassemble(win, rom)
    win.show_retro_toolchains = lambda: show_toolchains(win)
    try:
        from ..retro.menu import section
        m = section(win, "Retro &Development")
    except Exception:  # noqa: BLE001
        m = None
    if m is None:
        return
    a = m.addAction("Disassemble ROM into Project...")
    a.setStatusTip("Turn a ROM you own (2600, NES, Game Boy, C64, ZX) into a project that rebuilds byte-identical")
    a.triggered.connect(lambda: show_disassemble(win))
    win.a_retro_disassemble = a
    m.addAction("Re-disassemble with Hints").triggered.connect(lambda: redisassemble(win))
    m.addAction("Rebuild Check (compare with the original)").triggered.connect(lambda: rebuild_check(win))
    m.addSeparator()
    m.addAction("Retro Toolchains...").triggered.connect(lambda: show_toolchains(win))
