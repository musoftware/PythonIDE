"""Retro emulators (slice "emu" of radide/retro, see docs/RETRO.md).

Public API for the other retro slices and the IDE::

    from radide.retro.emu import run_rom, detect_system, find_emulator
    proc = run_rom("game.nes", system=None, debug=False, symbols=None)   # -> RetroProcess (or raises EmuError)
    proc.alive(); proc.stop(); proc.reload("game.nes")                    # hot reload or restart

The emulators are downloaded only on request (Tools > Retro Emulators...) - see manager.py / catalog.py.
"""
from __future__ import annotations

from .catalog import EMULATORS, PREFERRED, SYSTEM_TITLES, emulators_for
from .manager import config_dir, ensure, find, install, status
from .systems import detect_system


def find_emulator(system: str) -> tuple[str, str]:
    """(emulator id, exe) of the first installed emulator for *system*; ("", "") when none is installed."""
    for e in emulators_for(system):
        exe = find(e.id)
        if exe:
            return e.id, exe
    return "", ""


def run_rom(path, system=None, debug=False, symbols=None, emulator=None, **kw):
    """Start *path* in the right emulator; see launch.run_rom."""
    from .launch import run_rom as _run
    return _run(path, system=system, debug=debug, symbols=symbols, emulator=emulator, **kw)


__all__ = ["EMULATORS", "PREFERRED", "SYSTEM_TITLES", "config_dir", "detect_system", "emulators_for", "ensure",
           "find", "find_emulator", "install", "run_rom", "status"]
