"""ZX Spectrum programs in Z80 assembly (sjasmplus) - New Project > Retro Games > ZX Spectrum (sjasmplus).

sjasmplus (downloaded from its official GitHub releases on the first build) assembles the code; RAD IDE wraps it
in a .tap with a BASIC loader (radide/retro/dev/tapfile.py). Editor: Z80 instructions with T-states / flags,
ROM routines and system variables. Details: docs/RETRO.md ("Retro development").
"""
from __future__ import annotations

from ..retro.dev.plugin import RetroPluginBase


class ZxPlugin(RetroPluginBase):
    id = "retro-zx"
    display_name = "ZX Spectrum (sjasmplus)"
    code_ext = ".asm"
    system = "zx"
    cpu = "z80"
    dialect = "sjasmplus"
    project_name_base = "ZxProgram"
    install_hint = "sjasmplus is downloaded automatically from https://github.com/z00m128/sjasmplus/releases."


PLUGIN = ZxPlugin()
