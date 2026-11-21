"""QBasic / QuickBASIC program (DOS) - New Project > DOS.

FreeBASIC ``-lang qb`` (its DOS build, run inside DOSBox-X without a window) turns the .BAS source into a real
DOS .EXE; Ctrl+F5 starts it in DOSBox-X; "Run in QBasic" runs the source in the user's own QBASIC.EXE / QB.EXE.
Old sources with line numbers build as they are. Details: radide/retro/dos, docs/RETRO.md "DOS programs".
"""
from __future__ import annotations

from ..retro.dos.plugin import DosPluginBase
from ..retro.dos.reference import QBASIC


class DosQBasicPlugin(DosPluginBase):
    id = "dos-qbasic"
    display_name = "QBasic / QuickBASIC (DOS)"
    code_ext = ".bas"
    kind = "qbasic"
    project_name_base = "QBasicApp"
    line_comments = ["'", "REM "]
    block_comment = None
    string_quotes = ['"']
    keywords = sorted({w for k in QBASIC for w in k.split()} | {"THEN", "ELSE", "ELSEIF", "END", "TO", "STEP",
                                                                "NEXT", "LOOP", "UNTIL", "WEND", "AS", "SHARED",
                                                                "INTEGER", "LONG", "SINGLE", "DOUBLE", "STRING",
                                                                "AND", "OR", "NOT", "XOR", "MOD", "CASE", "IS",
                                                                "EXIT", "CALL", "ON", "ERROR", "RESUME"})
    builtins = []

    def module_template(self, name: str) -> str:
        return f"' {name}.BAS - a QBasic module\r\nDEFINT A-Z\r\n"


PLUGIN = DosQBasicPlugin()
