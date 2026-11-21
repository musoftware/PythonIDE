"""Thin adapters to the other retro slices (graphics, toolchains, emulators, DOS) with small fallbacks, so the
designers keep working even when one of those packages is missing or changes shape.

* palettes / tile codecs   -> radide.retro.gfx.palettes / radide.retro.gfx.codecs
* toolchain executables    -> radide.retro.dev.toolchain.find / ensure (DASM, ca65 / ld65, RGBDS), NASM from
                              radide.asm.toolchain, FreeBASIC / OpenWatcom from radide.retro.dos (when present)
* emulators                -> radide.retro.emu.run_rom (Stella, Mesen / FCEUX, mGBA, DOSBox-X)

``RADIDE_RETRO_TOOLPATH`` (os.pathsep separated folders) is searched too - the tests point it at portable copies.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

RGB = tuple


# ------------------------------------------------------------------ palettes
def _fallback_vga() -> list:
    from ....emu8086.machine import vga_palette     # the 8086 emulator's mode 13h default palette
    return vga_palette()


def system_palette(key: str) -> list:
    """RGB list of a system palette: a2600ntsc / a2600pal (128), nes (64), gb (4), vga (256)."""
    if key == "vga":
        return _fallback_vga()
    try:
        from ...gfx import palettes as gp
        return list(gp.palette(key))
    except Exception:  # noqa: BLE001 - the graphics slice is optional
        pass
    if key == "gb":
        return [(0x9B, 0xBC, 0x0F), (0x8B, 0xAC, 0x0F), (0x30, 0x62, 0x30), (0x0F, 0x38, 0x0F)]
    n = {"a2600ntsc": 128, "a2600pal": 128, "nes": 64}.get(key, 16)
    return [((i * 37) % 256, (i * 91) % 256, (i * 53) % 256) for i in range(n)]


# ------------------------------------------------------------------ tile codecs
def encode_tile(fmt: str, pixels) -> bytes:
    """8x8 tile (64 values 0-3) -> NES CHR ("nes", planes) or Game Boy ("gb", interleaved) bytes."""
    px = [int(p) & 3 for p in pixels]
    try:
        from ...gfx.codecs import get_format
        return bytes(get_format(fmt).encode(px))
    except Exception:  # noqa: BLE001
        pass
    out = bytearray(16)
    for y in range(8):
        lo = hi = 0
        for i in range(8):
            p = px[y * 8 + i]
            lo |= (p & 1) << (7 - i)
            hi |= ((p >> 1) & 1) << (7 - i)
        if fmt == "nes":
            out[y], out[y + 8] = lo, hi
        else:
            out[2 * y], out[2 * y + 1] = lo, hi
    return bytes(out)


def half_to_bytes(bits) -> tuple[int, int, int]:
    """20 Atari 2600 playfield bits (left to right) -> (PF0, PF1, PF2)."""
    try:
        from ...gfx.atari2600 import half_to_bytes as h2b
        return h2b([1 if b else 0 for b in bits])
    except Exception:  # noqa: BLE001
        pass
    pf0 = pf1 = pf2 = 0
    for i, b in enumerate(bits):
        if not b:
            continue
        if i < 4:
            pf0 |= 1 << (4 + i)
        elif i < 12:
            pf1 |= 1 << (7 - (i - 4))
        else:
            pf2 |= 1 << (i - 12)
    return pf0, pf1, pf2


# ------------------------------------------------------------------ toolchains
def _extra_dirs() -> list[Path]:
    return [Path(p) for p in os.environ.get("RADIDE_RETRO_TOOLPATH", "").split(os.pathsep) if p.strip()]


def _search_extra(exe: str) -> str:
    name = exe + (".exe" if os.name == "nt" else "")
    for d in _extra_dirs():
        for cand in (d / name, d / "bin" / name):
            if cand.is_file():
                return str(cand)
        if d.is_dir():
            for cand in d.rglob(name):
                if cand.is_file():
                    return str(cand)
    return ""


def find_tool(exe: str) -> str:
    """Path of a build tool: dasm, ca65, ld65, rgbasm, rgblink, rgbfix, nasm, fbc, wcl, wcl386. "" = missing."""
    hit = _search_extra(exe)
    if hit:
        return hit
    if exe in ("dasm", "ca65", "ld65", "cc65", "cl65", "rgbasm", "rgblink", "rgbfix"):
        try:
            from ...dev import toolchain as tc
            hit = tc.find(exe)
        except Exception:  # noqa: BLE001
            hit = ""
    elif exe == "nasm":
        try:
            from ....asm.toolchain import find_nasm
            hit = find_nasm()
        except Exception:  # noqa: BLE001
            hit = ""
    else:
        hit = _dos_tool(exe)
    return hit or shutil.which(exe) or ""


def _dos_tool(exe: str) -> str:
    """FreeBASIC / OpenWatcom through the DOS development slice (radide.retro.dos), when it is installed."""
    try:
        __import__("radide.retro.dos")
    except Exception:  # noqa: BLE001
        return ""
    for modname in ("toolchains", "toolchain", "tools"):
        try:
            mod = __import__(f"radide.retro.dos.{modname}", fromlist=["x"])
        except Exception:  # noqa: BLE001
            continue
        for fn in ("find", "find_tool", "find_exe"):
            f = getattr(mod, fn, None)
            if callable(f):
                try:
                    r = f(exe)
                except Exception:  # noqa: BLE001
                    continue
                if isinstance(r, str) and r:
                    return r
                if isinstance(r, Path):
                    return str(r)
    return ""


def ensure_tool(exe: str, log=print, download: bool = True) -> str:
    """Like find_tool, but lets the owning slice download its official portable build when missing."""
    hit = find_tool(exe)
    if hit or not download:
        return hit
    try:
        if exe in ("dasm", "ca65", "ld65", "rgbasm", "rgblink", "rgbfix"):
            from ...dev import toolchain as tc
            return tc.ensure(exe, log=log, download=True)
        if exe == "nasm":
            from ....asm import toolchain as atc
            return atc.ensure("nasm", log=log)
        for modname in ("toolchains", "toolchain", "tools"):
            try:
                mod = __import__(f"radide.retro.dos.{modname}", fromlist=["x"])
            except Exception:  # noqa: BLE001
                continue
            f = getattr(mod, "ensure", None)
            if callable(f):
                r = f(exe, log=log)
                return str(r) if r else ""
    except Exception as e:  # noqa: BLE001
        log(f"{exe}: {e}")
    return ""


# ------------------------------------------------------------------ emulators
def run_in_emulator(path, system: str, log=print):
    """Start *path* in the emulator for *system* (a2600 / nes / gb / dos). Returns the process object or None."""
    try:
        from ...emu import run_rom
    except Exception as e:  # noqa: BLE001
        log(f"The retro emulator manager is not available: {e}")
        return None
    try:
        return run_rom(str(path), system=system)
    except Exception as e:  # noqa: BLE001
        log(f"Could not start the emulator: {e}")
        return None
