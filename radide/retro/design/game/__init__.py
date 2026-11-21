"""Visual screen / level designers for retro game projects (slice "gamedesign" of radide/retro, see docs/RETRO.md).

    from radide.retro.design.game import new_design, load, SYSTEMS, generate, build
    d = new_design("nes", "Level1", screens=3)         # a2600 | nes | gb | dos13h
    d.save("Level1.nesscr")
    info = generate(d, "gen/Level1")                   # data + program files for the system's toolchain
    res = build(d, "gen/Level1")                       # {"ok", "rom", "log", "warnings", "checks"}

Designers (each module is pure Python - the Qt editor is ``ui.GameDesigner``):

=========  ==========  =====================================================================================
system     extension   generates
=========  ==========  =====================================================================================
a2600      .a26scr     DASM one-line kernel (per-line playfield / colours, players, missiles, ball) -> 4K ROM
nes        .nesscr     ca65 data + NROM loader (palettes, column streaming for multi-screen levels, OAM)
gb         .gbmap      RGBDS data (tiles, BG map, window, OAM) + a ROM that shows it
dos13h     .m13scr     .pal / .bg / .rle / .spr data + FreeBASIC, OpenWatcom C and NASM .COM programs
=========  ==========  =====================================================================================
"""
from __future__ import annotations

from pathlib import Path

from . import atari2600, gameboy, mode13h, nes
from .model import Design, Layer, ident

SYSTEMS = {m.SYSTEM: m for m in (atari2600, nes, gameboy, mode13h)}
EXTS = {m.EXT: m.SYSTEM for m in SYSTEMS.values()}
TITLES = {s: m.TITLE for s, m in SYSTEMS.items()}
EMU_SYSTEM = {"a2600": "a2600", "nes": "nes", "gb": "gb", "dos13h": "dos"}


def module_for(system: str):
    return SYSTEMS[system]


def new_design(system: str, name: str = "", **kw) -> Design:
    m = SYSTEMS[system]
    name = name or {"a2600": "Screen1", "nes": "Level1", "gb": "Map1", "dos13h": "Screen1"}[system]
    if system == "a2600":
        return m.new_design(name, kw.get("tv", "NTSC"))
    if system == "nes":
        return m.new_design(name, kw.get("screens", 2))
    return m.new_design(name)


def is_design_file(path) -> bool:
    return Path(path).suffix.lower() in EXTS


def load(path) -> Design:
    d = Design.load(path)
    if d.system not in SYSTEMS:
        raise ValueError(f"unknown system '{d.system}'")
    return d


def gen_dir(design_path) -> Path:
    """Where the generated files of a design file go: ``<folder>/gen/<name>/``, or ``<folder>/gen/<name>_<system>/``
    when a design of another system has the same name there (Screen1.a26scr next to Screen1.m13scr: the DASM
    ``Screen1.asm`` and the NASM ``SCREEN1.ASM`` are the same file on Windows)."""
    p = Path(design_path)
    if any(e != p.suffix.lower() and (p.parent / (p.stem + e)).exists() for e in EXTS):
        return p.parent / "gen" / f"{ident(p.stem)}_{EXTS.get(p.suffix.lower(), 'design')}"
    return p.parent / "gen" / ident(p.stem)


def generate(d: Design, outdir) -> dict:
    return SYSTEMS[d.system].generate(d, outdir)


def build(d: Design, outdir, log=print, download: bool = False) -> dict:
    from .build import build as _build
    return _build(d, outdir, log=log, download=download)


__all__ = ["Design", "EMU_SYSTEM", "EXTS", "Layer", "SYSTEMS", "TITLES", "build", "gen_dir", "generate",
           "is_design_file", "load", "module_for", "new_design"]
