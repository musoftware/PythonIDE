"""Retro emulators in the IDE (radide/retro/emu, docs/RETRO.md "Emulators"):

* Tools > Retro > Emulators... - status of Stella, Mesen 2, FCEUX, mGBA, VICE, Atari800, DOSBox-X;
  download of the official portable builds on request; own paths.
* Tools > Retro > Run ROM in Emulator... / Debug ROM in Emulator... / Reload ROM in Emulator (Ctrl+Shift+Alt+F5).
* View > Retro Debugger - registers, memory, breakpoints and stepping through VICE's binary monitor (C64) or
  mGBA's GDB stub (GBA).
* Project > DOS Settings... for DOS Program projects (radide/languages/retro_dos.py).
* File > Open Folder: a folder of MS-DOS executables is offered as "DOS program (DOSBox-X)".
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


# ====================================================================== install
def install(win) -> None:
    register_detector()
    try:
        from ..retro.filebus import subscribe
        subscribe(win, _on_file_changed(win))
    except Exception:  # noqa: BLE001 - the shared bus is optional
        pass
    from ..retro.emu import ui
    ui.apply_settings(getattr(win, "settings", None))
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
