"""Retro emulators in the IDE (radide/retro/emu, docs/RETRO.md "Emulators"):

* Tools > Retro > Emulators... - status of Stella, Mesen 2, FCEUX, mGBA, VICE, Atari800, DOSBox-X;
  download of the official portable builds on request; own paths.
* Tools > Retro > Run ROM in Emulator... / Debug ROM in Emulator... / Reload ROM in Emulator (Ctrl+Shift+Alt+F5).
* View > Retro Debugger - registers, memory, breakpoints and stepping through VICE's binary monitor (C64) or
  mGBA's GDB stub (GBA).
* Project > DOS Settings... for DOS Program projects (radide/languages/retro_dos.py).
* File > Open Folder: a folder of MS-DOS executables is offered as "DOS program (DOSBox-X)".
* The "Emulator" toolbar (retro game and ROM Hacking projects): which emulator F5 / Run in Emulator uses for the
  project - "Automatic" (the first installed one for the system) or a chosen one, stored in the project
  (project.radproj ``retro.emulator`` / rom.json ``emulator``).
"""
from __future__ import annotations

from pathlib import Path


def _english(a) -> str:
    t = a.text().replace("&", "")
    try:
        from ..i18n import english
        return english(a, t) or t
    except Exception:  # noqa: BLE001
        return t


def _menu(win, title: str):
    for a in win.menuBar().actions():
        if a.menu() is not None and _english(a) == title:
            return a.menu()
    return None


def _submenu(menu, title: str):
    for a in menu.actions():
        if a.menu() is not None and _english(a) == title:
            return a.menu()
    return menu.addMenu(title)


# ====================================================================== Open Folder detector
def detect_dos(folder: Path) -> list:
    """project_detect detector: a folder whose programs are MS-DOS executables (not Windows .exe files)."""
    from ..project_detect import Candidate
    from ..retro.emu.dos import looks_like_dos_program
    conf, info = looks_like_dos_program(folder)
    if conf < 0.5:
        return []
    progs = info["exes"] + info["coms"]
    start = info["start"]
    c = Candidate("dos-program", f"DOS program (DOSBox-X, {len(progs)} DOS executable{'s' if len(progs) != 1 else ''}"
                  + (f", start {start}" if start else "") + ")", "retro-dos", "app", folder, conf, progs[:3],
                  startup="", modules=(info["bats"] + progs)[:200])
    c.extra["dos"] = {"program": start, "cycles": "auto", "machine": "svga_s3", "memsize": 16, "sound": "sb16"}
    c.notes.append("Runs in DOSBox-X with a generated configuration (Project > DOS Settings). "
                   "Your files are not changed.")
    return [c]


def register_detector() -> None:
    try:
        from .. import project_detect
    except Exception:  # noqa: BLE001
        return
    if detect_dos not in project_detect.DETECTORS:
        project_detect.DETECTORS.append(detect_dos)


def _on_file_changed(win):
    """A retro build / ROM tool rewrote a file (radide/retro/filebus.py): when it is the ROM running in VICE,
    reload it in place (emulators that would have to restart are left alone: Reload ROM does that)."""
    def cb(path, _source=None):
        proc = getattr(win, "_retro_proc", None)
        try:
            if proc is not None and proc.can_hot_reload() and Path(path).resolve() == Path(proc.rom).resolve():
                from ..retro.emu import ui
                ui.hot_reload(win, str(path))
        except Exception as e:  # noqa: BLE001
            try:
                win.log(f"[retro] hot reload failed: {e}")
            except Exception:  # noqa: BLE001
                pass
    return cb


# ====================================================================== emulator per project
class EmulatorBar:
    """Toolbar combo: the emulator of the active retro / ROM Hacking project."""

    def __init__(self, win):
        from PyQt6.QtWidgets import QComboBox, QLabel, QToolBar
        self.win = win
        self._key = None
        tb = QToolBar("Retro Emulator", win)
        tb.setObjectName("RetroEmulator")
        self.label = QLabel(" Emulator: ")
        tb.addWidget(self.label)
        self.combo = QComboBox()
        self.combo.setMinimumWidth(220)
        self.combo.setToolTip("The emulator F5 and Run in Emulator use for this project (Automatic = the first "
                              "installed emulator for the system)")
        self.combo.activated.connect(self._chosen)
        tb.addWidget(self.combo)
        win.addToolBar(tb)
        tb.setVisible(False)
        self.toolbar = tb
        win.extension_points.on("actions_updated", lambda: self.update_ui(), "retro emulator")   # errors logged once

    def update_ui(self, force: bool = False) -> None:
        from ..retro.emu import ui
        project = getattr(self.win, "project", None)
        system = ui.project_system(project)
        on = bool(system) and system != "dos"
        key = (str(getattr(project, "folder", "")), system)
        if on and (force or key != self._key):
            self.refill(system, ui.project_emulator(project))
        self._key = key if on else None
        if self.toolbar.isVisible() != on:
            self.toolbar.setVisible(on)

    def refill(self, system: str, current: str) -> None:
        from ..retro.emu import ui
        choices = ui.emulator_choices(system)
        first = next((t for _i, t, ok in choices if ok), "")
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItem(f"Automatic ({first})" if first else "Automatic (none installed)", "")
        for eid, title, ok in choices:
            self.combo.addItem(title + ("" if ok else "  (not installed)"), eid)
        i = self.combo.findData(current or "")
        self.combo.setCurrentIndex(max(0, i))
        self.combo.blockSignals(False)

    def select(self, emu_id: str) -> bool:
        i = self.combo.findData(emu_id or "")
        if i < 0:
            return False
        self.combo.setCurrentIndex(i)
        self._chosen(i)
        return True

    def _chosen(self, i: int) -> None:
        from ..retro.emu import ui
        eid = self.combo.itemData(i) or ""
        if ui.set_project_emulator(getattr(self.win, "project", None), eid):
            try:
                self.win.log(f"[retro] emulator of this project: {eid or 'automatic'}")
            except Exception:  # noqa: BLE001
                pass


# ====================================================================== Mesen controller offer
MESEN_OFFER_KEY = "retro/emu/mesen_input_offered"


def mesen_input_offer(win, force: bool = False):
    """Once: when the portable Mesen 2 RAD IDE downloaded has a settings.json whose NES / SNES / Game Boy port 1
    is "None" without keys (made by an older RAD IDE), show a non-blocking bar under the status bar with
    "Apply Controller Defaults" (radide/retro/emu/inputs.py) and log it to Output. Returns the bar or None."""
    settings = getattr(win, "settings", None)
    if not force and settings is not None and str(settings.value(MESEN_OFFER_KEY, "") or "") in ("1", "true"):
        return None
    from ..retro.emu import inputs, manager
    sp = manager.mesen_settings_file()
    todo = inputs.needs_mesen_defaults(sp) if sp is not None else []
    if not todo:
        return None
    from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

    def done(apply: bool) -> None:
        if settings is not None:
            settings.setValue(MESEN_OFFER_KEY, "1")
        if apply:
            try:
                changed = inputs.apply_mesen_defaults(sp)
                msg = (f"[retro] Mesen 2: controller port 1 set for {', '.join(changed)} - arrows, X/Z = A/B, "
                       "Enter = Start, Shift/Backspace = Select (close an open Mesen window first; "
                       "Mesen > Settings > Input changes it)." if changed else "[retro] Mesen 2: nothing to change.")
            except OSError as e:
                msg = f"[retro] Mesen 2 settings could not be written: {e}"
            try:
                win.log(msg)
            except Exception:  # noqa: BLE001
                pass
        bar.hide()
        bar.deleteLater()
        win.mesen_input_bar = None

    bar = QFrame(win)
    bar.setObjectName("MesenInputBar")
    bar.setFrameShape(QFrame.Shape.StyledPanel)
    lay = QHBoxLayout(bar)
    lay.setContentsMargins(6, 1, 6, 1)
    text = (f"Mesen 2 has no controller in port 1 ({', '.join(todo)}): games cannot be played with the keyboard.")
    lay.addWidget(QLabel(text))
    b_apply = QPushButton("Apply Controller Defaults")
    b_apply.setObjectName("MesenInputApply")
    b_later = QPushButton("Not Now")
    b_apply.clicked.connect(lambda: done(True))
    b_later.clicked.connect(lambda: done(False))
    lay.addWidget(b_apply)
    lay.addWidget(b_later)
    try:
        win.statusBar().addPermanentWidget(bar)
    except Exception:  # noqa: BLE001
        pass
    win.mesen_input_bar = bar
    try:
        win.log("[retro] " + text + " Use the \"Apply Controller Defaults\" button at the bottom of the window.")
    except Exception:  # noqa: BLE001
        pass
    return bar


def _safe_offer(win) -> None:
    try:
        mesen_input_offer(win)
    except Exception:  # noqa: BLE001 - only an offer
        pass


# ====================================================================== install
def install(win) -> None:
    register_detector()
    try:     # the Mesen controller offer only once a retro project is open - not at every start of every user
        from PyQt6.QtCore import QTimer
        timer = QTimer(win)
        timer.setInterval(3000)

        def _when_retro():
            lang = str(getattr(getattr(win, "project", None), "language", "") or "")
            if lang.startswith("retro-"):
                timer.stop()
                _safe_offer(win)
        timer.timeout.connect(_when_retro)
        timer.start()
        win._mesen_offer_timer = timer
    except Exception:  # noqa: BLE001
        pass
    try:
        from ..retro.filebus import subscribe
        subscribe(win, _on_file_changed(win))
    except Exception:  # noqa: BLE001 - the shared bus is optional
        pass
    from ..retro.emu import ui
    ui.apply_settings(getattr(win, "settings", None))
    try:
        win.retro_emulator_bar = EmulatorBar(win)
    except Exception as e:  # noqa: BLE001 - the toolbar is optional
        try:
            win.log(f"[retro emulators] toolbar: {e}")
        except Exception:  # noqa: BLE001
            pass
    try:
        from PyQt6.QtGui import QAction, QKeySequence
        try:
            from ..retro.menu import retro_menu          # the shared Tools > Retro menu (docs/CONTRACTS.md 11)
            retro = retro_menu(win)
        except Exception:  # noqa: BLE001
            tools = _menu(win, "Tools")
            retro = _submenu(tools, "Retro") if tools is not None else None
        if retro is not None:
            retro.addSeparator()
            retro.addAction("Emulators...", lambda: ui.show_manager(win))
            retro.addAction("Run ROM in Emulator...", lambda: ui.run_rom_dialog(win))
            retro.addAction("Debug ROM in Emulator...", lambda: ui.run_rom_dialog(win, debug=True))
            act = QAction("Reload ROM in Emulator", win)
            act.setShortcut(QKeySequence("Ctrl+Shift+Alt+F5"))
            act.triggered.connect(lambda: ui.hot_reload(win))
            retro.addAction(act)
            win.a_retro_reload = act
        view = _menu(win, "View")
        if view is not None:
            def show_debugger():
                d = ui.ensure_debugger(win)
                d.show()
                d.raise_()
            view.addAction("Retro Debugger", show_debugger)
        project = _menu(win, "Project")
        if project is not None:
            project.addAction("DOS Settings...", lambda: ui.dos_settings(win))
    except Exception as e:  # noqa: BLE001 - menus are optional
        try:
            win.log(f"[retro emulators] menus: {e}")
        except Exception:  # noqa: BLE001
            pass
