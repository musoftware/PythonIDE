"""Turbo C-style program (DOS) - New Project > DOS.

Open Watcom v2 (wcl, 16-bit small / large model) builds a real DOS .EXE on Windows; RAD IDE's include folder adds
tcconio.h (clrscr, gotoxy, textcolor ...) and a BGI subset (graphics.h / tcgraph.h) for old Turbo C sources.
DJGPP (32-bit protected mode) or the user's own Turbo C can be chosen in the DOS settings.
"""
from __future__ import annotations

from ..retro.dos.plugin import DosPluginBase
from ..retro.dos.reference import C_FUNCS, C_KEYWORDS


class DosCPlugin(DosPluginBase):
    id = "dos-c"
    display_name = "Turbo C-style (DOS)"
    code_ext = ".c"
    kind = "c"
    project_name_base = "TurboCApp"
    case_sensitive = True
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ['"', "'"]
    keywords = C_KEYWORDS
    builtins = sorted(C_FUNCS)

    def module_template(self, name: str) -> str:
        return f"/* {name}.C - another source file of the program (built together with MAIN.C) */\r\n" \
               f"#include <stdio.h>\r\n\r\nvoid {name.lower()}_hello(void)\r\n{{\r\n    printf(\"Hello from {name}\n\");\r\n}}\r\n"


PLUGIN = DosCPlugin()
