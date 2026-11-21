"""IDE glue of the "8086 Assembly (Emulator)" projects (radide/languages/emu8086.py, radide/emu8086):

* the assembler's errors join the Error List on save / Check for Errors (tools.run_checks diag provider);
* Debug > "8086: Stop at First Instruction" (on by default): F5 opens the emulator paused on the first line;
* View > 8086 Emulator shows the emulator dock (created on first use).
"""
from __future__ import annotations

from pathlib import Path


def _is_emu_project(win) -> bool:
    p = getattr(win, "project", None)
    return p is not None and getattr(p, "language", "") == "emu8086"


def diag_provider(win) -> list:
    """Assemble the startup file (unsaved editor text wins) and return tools.Diag rows."""
    if not _is_emu_project(win):
        return []
    from ..emu8086.assembler import assemble
    from ..emu8086.messages import ui_language
    from ..languages import get_plugin
    from ..tools import Diag
    p = win.project
    folder = Path(p.folder)
    startup = get_plugin("emu8086")._startup_file(folder, p.startup)
    texts = {}
    for mod, view in getattr(win, "modviews", {}).items():
        try:
            texts[Path(mod).name.lower()] = view.editor.text()
        except Exception:  # noqa: BLE001
            pass
    src = texts.get(startup.lower())
    if src is None:
        try:
            src = (folder / startup).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

    def reader(name: str):
        return texts.get(Path(name).name.lower())
    prog = assemble(src, startup, include_dir=folder, read_include=reader)
    lang = ui_language()
    win._emu8086_err_keys = set()          # run_checks rebuilds the whole list
    return [Diag(d.severity, d.text(lang), Path(d.file).name, d.line) for d in list(prog.errors) + list(prog.warnings)]


def install(win) -> None:
    providers = getattr(win, "diag_providers", None)
    if providers is None:
        providers = []
        win.diag_providers = providers
    if diag_provider not in providers:
        providers.append(diag_provider)
    try:
        from PyQt6.QtGui import QAction
        debug_menu = next(a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Debug")
        act = QAction("8086: Stop at First Instruction", win, checkable=True)
        v = win.settings.value("emu8086/stop_at_entry", True)
        act.setChecked(v in (True, "true", "1", 1))
        act.toggled.connect(lambda on: win.settings.setValue("emu8086/stop_at_entry", on))
        debug_menu.addSeparator()
        debug_menu.addAction(act)
        win.a_emu8086_stop_at_entry = act
        view_menu = next(a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "View")

        def show_emulator():
            from ..emu8086.ui import ensure_panel
            ensure_panel(win)
            win._emu8086_dock.show()
            win._emu8086_dock.raise_()
        view_menu.addAction("8086 Emulator", show_emulator)
    except (StopIteration, AttributeError):
        pass
