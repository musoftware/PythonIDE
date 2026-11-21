"""The retro systems of the game projects (no Qt in here)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class System:
    id: str                 # our id (project.radproj "retro.system")
    title: str
    cpu: str                # 6502 | sm83 | z80
    dialect: str            # dasm | ca65 | rgbds | sjasmplus (the assembler the sources are written for)
    rom_ext: str            # output file extension
    emu_system: str         # system id of the emulator slice (radide/retro/emu), "" = none there
    plugin: str             # language plugin id


SYSTEMS: dict[str, System] = {
    "atari2600": System("atari2600", "Atari 2600", "6502", "dasm", ".bin", "a2600", "retro-atari2600"),
    "nes": System("nes", "NES / Famicom", "6502", "ca65", ".nes", "nes", "retro-nes"),
    "gameboy": System("gameboy", "Game Boy", "sm83", "rgbds", ".gb", "gb", "retro-gameboy"),
    "c64": System("c64", "Commodore 64", "6502", "ca65", ".prg", "c64", "retro-c64"),
    "zx": System("zx", "ZX Spectrum", "z80", "sjasmplus", ".tap", "", "retro-zx"),
}

PLUGIN_SYSTEM = {s.plugin: s.id for s in SYSTEMS.values()}


def system_of(project) -> System | None:
    """The System of a retro project (project.extra["retro"]["system"], else from its language)."""
    if project is None:
        return None
    sid = (getattr(project, "extra", {}) or {}).get("retro", {}).get("system") or \
        PLUGIN_SYSTEM.get(getattr(project, "language", ""), "")
    return SYSTEMS.get(sid)


def is_retro_project(project) -> bool:
    return system_of(project) is not None
