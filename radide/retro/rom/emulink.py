"""Run a ROM in an emulator - the ROM workbench's link to the emulator slice (radide/retro/emu).

Contract (docs/RETRO.md, "ROM workbench"): ``run_rom(path, system=None)`` starts *path* in the emulator for
*system* (an id of radide/retro/emu: a2600, nes, snes, gb, gbc, gba, sms, gg, c64, a8, dos, ... - or one of the
names of radide/retro/rom/detect.py, which are translated) and returns the emulator's process object. It raises
:class:`RunError` with a message for the user when no emulator is installed or the system is unknown.
With the environment variable RADIDE_RETRO_DRY_RUN=1 the emulator command is resolved but not started (tests).
"""
from __future__ import annotations

import os
from pathlib import Path

from .detect import EMU_SYSTEM, detect, emu_system


class RunError(RuntimeError):
    pass


def system_for(path) -> str:
    p = Path(path)
    try:
        return emu_system(detect(p.read_bytes(), p.name))
    except OSError:
        return ""


def run_rom(path, system: str | None = None, debug: bool = False, **kw):
    p = Path(path)
    if not p.exists():
        raise RunError(f"The file does not exist: {p}")
    sysid = EMU_SYSTEM.get(system or "", system or "") or system_for(p)
    try:
        from ..emu import run_rom as emu_run
    except ImportError as e:            # the emulator slice is not installed
        raise RunError("The retro emulator support (radide/retro/emu) is not available.") from e
    try:
        if os.environ.get("RADIDE_RETRO_DRY_RUN") == "1":       # tests: resolve the command, start nothing
            from ..emu.launch import command_for
            return command_for(str(p), sysid or None, debug, None, None, **kw)
        return emu_run(str(p), system=sysid or None, debug=debug, **kw)
    except Exception as e:  # noqa: BLE001 - EmuError and friends: one message for the user
        raise RunError(str(e) or e.__class__.__name__) from e


__all__ = ["RunError", "run_rom", "system_for"]
