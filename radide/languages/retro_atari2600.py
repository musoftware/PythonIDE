"""Atari 2600 games in 6502 assembly (DASM) - New Project > Retro Games > Atari 2600 Game (DASM).

F5 builds a 4K cartridge with DASM (downloaded from its official GitHub releases on the first build) and runs it
in Stella (radide/retro/emu). Editor: 6502 mnemonics with cycles / flags / addressing modes, TIA / RIOT registers.
Details: docs/RETRO.md ("Retro development").
"""
from __future__ import annotations

from ..retro.dev.plugin import RetroPluginBase


class Atari2600Plugin(RetroPluginBase):
    id = "retro-atari2600"
    display_name = "Atari 2600 (DASM)"
    code_ext = ".asm"
    system = "atari2600"
    cpu = "6502"
    dialect = "dasm"
    project_name_base = "Atari2600Game"
    install_hint = "DASM is downloaded automatically from https://github.com/dasm-assembler/dasm/releases."


PLUGIN = Atari2600Plugin()
