"""The emulators RAD IDE can drive (no Qt in here).

Every entry is a free emulator published by its own team; RAD IDE never bundles one. On request
(Tools > Retro Emulators...) the pinned portable Windows build is downloaded from the project's OFFICIAL
GitHub releases page into ``%LOCALAPPDATA%\\RADIDE\\tools\\<id>`` - no installer, no admin rights, no winget.
The SHA-256 of every archive is pinned below (taken from the GitHub release "digest" where GitHub publishes
one, otherwise measured when this version of RAD IDE was written); a changed file is refused and the user is
sent to the official page. GPL emulators are only started as separate programs.

System ids used everywhere in radide/retro: ``a2600`` (Atari 2600), ``a8`` (Atari 400/800/XL/XE),
``nes``, ``snes``, ``gb``, ``gbc``, ``gba``, ``pce`` (PC Engine / TurboGrafx-16), ``sms``, ``gg``,
``c64`` (Commodore 64), ``dos`` (MS-DOS programs).
"""
from __future__ import annotations

from dataclasses import dataclass, field

SYSTEM_TITLES = {
    "a2600": "Atari 2600", "a8": "Atari 8-bit (400/800/XL/XE)", "nes": "NES / Famicom", "snes": "SNES / Super Famicom",
    "gb": "Game Boy", "gbc": "Game Boy Color", "gba": "Game Boy Advance", "pce": "PC Engine / TurboGrafx-16",
    "sms": "Sega Master System", "gg": "Sega Game Gear", "c64": "Commodore 64", "dos": "MS-DOS program",
}


@dataclass(frozen=True)
class Emulator:
    id: str
    title: str
    systems: tuple                 # system ids, in order of preference for this emulator
    licence: str
    homepage: str
    page: str                      # official download page (shown when the download fails)
    version: str
    url: str                       # pinned portable Windows build (official release asset)
    sha256: str
    archive: str                   # "zip" | "7z"
    exe_names: tuple               # executables looked up inside the install folder (first hit wins)
    path_names: tuple = ()         # names looked up in PATH
    debug: str = ""                # what RAD IDE uses for debugging: "vice-monitor" | "gdb-rsp" | "builtin" | ""
    notes: str = ""
    extra_exes: dict = field(default_factory=dict)    # role -> exe names (e.g. VICE "x64sc", mGBA "sdl")


EMULATORS: dict[str, Emulator] = {e.id: e for e in [
    Emulator("stella", "Stella", ("a2600",), "GPL-2.0", "https://stella-emu.github.io/",
             "https://github.com/stella-emu/stella/releases", "7.0c",
             "https://github.com/stella-emu/stella/releases/download/7.0/Stella-7.0c-windows.zip",
             "44102ccf8af74b021cf143db346e561c5d6ed2a2e91d79ee6d3c99d7c42f4653", "zip",
             ("Stella.exe",), ("stella",), "builtin",
             "Atari 2600. -debug opens Stella's debugger; DASM .sym / .lst files next to the ROM give it labels."),
    Emulator("mesen", "Mesen 2", ("nes", "snes", "gb", "gbc", "pce", "sms", "gg"), "GPL-3.0", "https://www.mesen.ca/",
             "https://github.com/SourMesen/Mesen2/releases", "2.1.1",
             "https://github.com/SourMesen/Mesen2/releases/download/2.1.1/Mesen_2.1.1_Windows.zip",
             "23ccc2bc060b663c68dad3a8c5d6da7d23a50f872d04f135bafa2b04ff7d5cbe", "zip",
             ("Mesen.exe",), ("mesen",), "builtin",
             "NES, SNES, Game Boy, PC Engine, SMS / GG. Needs the .NET 8 Desktop Runtime. Loads ca65/ld65 .dbg, "
             "RGBDS .sym and .mlb label files that sit next to the ROM; a .lua script can be passed on the "
             "command line."),
    Emulator("fceux", "FCEUX", ("nes",), "GPL-2.0", "https://fceux.com/",
             "https://github.com/TASEmulators/fceux/releases", "2.7.0",
             "https://github.com/TASEmulators/fceux/releases/download/fceux-2.7.0/fceux-2.7.0-win64.zip",
             "f851d608fc21bc7d289d25ef92cb29ca6c96a21c3df28f82aab2a8328df1f9ff", "zip",
             ("fceux64.exe", "fceux.exe"), ("fceux",), "builtin",
             "NES fallback when Mesen 2 cannot run (no .NET 8). Debugger, PPU / name table viewers, Lua (-lua)."),
    Emulator("mgba", "mGBA", ("gba", "gbc", "gb"), "MPL-2.0", "https://mgba.io/",
             "https://github.com/mgba-emu/mgba/releases", "0.10.5",
             "https://github.com/mgba-emu/mgba/releases/download/0.10.5/mGBA-0.10.5-win64.7z",
             "b497a57c7d9093834dadc64f33a90f7c411439c21fdb8a0143255a45ea37563a", "7z",
             ("mGBA.exe",), ("mgba-qt", "mgba"), "gdb-rsp",
             "Game Boy / Color / Advance. -g starts its GDB stub (port 2345): RAD IDE's Retro Debugger reads "
             "registers and memory through it (GBA).", {"sdl": ("mgba-sdl.exe",)}),
    Emulator("vice", "VICE (x64sc)", ("c64",), "GPL-2.0", "https://vice-emu.sourceforge.io/",
             "https://github.com/VICE-Team/svn-mirror/releases", "3.10",
             "https://github.com/VICE-Team/svn-mirror/releases/download/3.10.0/GTK3VICE-3.10-win64.7z",
             "7af868188b4f9e66279ed8fdc2a13210241bb30fca3eb4faa303214be432245a", "7z",
             ("x64sc.exe",), ("x64sc",), "vice-monitor",
             "Commodore 64. RAD IDE talks to VICE's binary monitor (TCP) for breakpoints, stepping, registers, "
             "memory and hot reload (autostart)."),
    Emulator("atari800", "Atari800", ("a8",), "GPL-2.0", "https://atari800.github.io/",
             "https://github.com/atari800/atari800/releases", "7.2.1",
             "https://github.com/atari800/atari800/releases/download/ATARI800_7_2_1/atari800-7.2.1-win64.zip",
             "82eb30836613a03b3a82d594da71b47667f2eef844d9cd808e3a367f250613ab", "zip",
             ("atari800.exe",), ("atari800",), "builtin",
             "Atari 400/800/XL/XE. Uses its built-in free (AltirraOS) ROMs when no original OS ROMs are set. "
             "Altirra (also free) is used instead when it is on PATH or in tools\\altirra, but it is not "
             "downloaded automatically."),
    Emulator("dosbox-x", "DOSBox-X", ("dos",), "GPL-2.0", "https://dosbox-x.com/",
             "https://github.com/joncampbell123/dosbox-x/releases", "2026.10.01",
             "https://github.com/joncampbell123/dosbox-x/releases/download/dosbox-x-v2026.10.01/"
             "dosbox-x-vsbuild-win64-2026.10.01-portable.zip",
             "3c50915e63aefe35777d65ebb4391a06b4a2c2342e4c75cbee6bbda4c6916e33", "zip",
             ("dosbox-x.exe",), ("dosbox-x",), "builtin",
             "MS-DOS programs and games (the user's own), and old DOS compilers. RAD IDE writes a .conf per "
             "project (mount, CPU cycles, memory, sound card)."),
]}

# system -> emulators in order of preference (the first installed one runs the ROM)
PREFERRED: dict[str, list[str]] = {}
for _e in EMULATORS.values():
    for _s in _e.systems:
        PREFERRED.setdefault(_s, []).append(_e.id)
PREFERRED["gb"] = ["mgba", "mesen"]
PREFERRED["gbc"] = ["mgba", "mesen"]
PREFERRED["nes"] = ["mesen", "fceux"]


def emulators_for(system: str) -> list[Emulator]:
    return [EMULATORS[i] for i in PREFERRED.get(system, [])]


__all__ = ["EMULATORS", "Emulator", "PREFERRED", "SYSTEM_TITLES", "emulators_for"]
