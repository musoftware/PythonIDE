"""Commodore 64 programs (cc65 / ca65, or ACME) - New Project > Retro Games > Commodore 64.

ca65 + ld65 with the project's c64.cfg (a BASIC SYS line + machine code), cl65 -t c64 for C, or ACME when it
is in PATH. F5 runs the .prg in VICE (radide/retro/emu). Details: docs/RETRO.md ("Retro development").
"""
from __future__ import annotations

from ..retro.dev.plugin import RetroPluginBase


class C64Plugin(RetroPluginBase):
    id = "retro-c64"
    display_name = "Commodore 64 (cc65 / ACME)"
    code_ext = ".s"
    system = "c64"
    cpu = "6502"
    dialect = "ca65"
    project_name_base = "C64Program"
    install_hint = "cc65 is downloaded automatically (official Windows snapshot); ACME only from PATH."


PLUGIN = C64Plugin()
