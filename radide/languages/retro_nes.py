"""NES / Famicom games (cc65 / ca65) - New Project > Retro Games > NES Game (assembly or C).

ca65 + ld65 with the project's own linker configuration (nes.cfg), or cl65 -t nes for C. cc65 is downloaded
from the official Windows snapshot on the first build; F5 runs the .nes file in Mesen (radide/retro/emu).
Details: docs/RETRO.md ("Retro development").
"""
from __future__ import annotations

from ..retro.dev.plugin import RetroPluginBase


class NesPlugin(RetroPluginBase):
    id = "retro-nes"
    display_name = "NES (cc65 / ca65)"
    code_ext = ".s"
    system = "nes"
    cpu = "6502"
    dialect = "ca65"
    project_name_base = "NesGame"
    install_hint = "cc65 is downloaded automatically (official Windows snapshot, https://cc65.github.io)."


PLUGIN = NesPlugin()
