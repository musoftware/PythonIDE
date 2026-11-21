"""Game Boy games (RGBDS) - New Project > Retro Games > Game Boy Game (RGBDS).

rgbasm + rgblink + rgbfix (downloaded from the official RGBDS GitHub releases on the first build); F5 runs the
.gb file in mGBA (radide/retro/emu). Editor: SM83 instructions with cycles / flags, Game Boy I/O registers.
Details: docs/RETRO.md ("Retro development").
"""
from __future__ import annotations

from ..retro.dev.plugin import RetroPluginBase


class GameBoyPlugin(RetroPluginBase):
    id = "retro-gameboy"
    display_name = "Game Boy (RGBDS)"
    code_ext = ".asm"
    system = "gameboy"
    cpu = "sm83"
    dialect = "rgbds"
    project_name_base = "GameBoyGame"
    install_hint = "RGBDS is downloaded automatically from https://github.com/gbdev/rgbds/releases."


PLUGIN = GameBoyPlugin()
