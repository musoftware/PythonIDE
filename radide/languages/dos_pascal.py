"""Turbo Pascal-style program (DOS) - New Project > DOS.

Free Pascal's i8086-msdos cross compiler (TP mode, Crt / Dos / Graph units) builds a real 16-bit DOS .EXE on
Windows; Ctrl+F5 starts it in DOSBox-X. The user's own Turbo Pascal (TPC.EXE) can be chosen in the DOS settings.
"""
from __future__ import annotations

from ..retro.dos.plugin import DosPluginBase
from ..retro.dos.reference import PASCAL, PASCAL_KEYWORDS


class DosPascalPlugin(DosPluginBase):
    id = "dos-pascal"
    display_name = "Turbo Pascal-style (DOS)"
    code_ext = ".pas"
    kind = "pascal"
    project_name_base = "PascalApp"
    line_comments = ["//"]
    block_comment = ("{", "}")
    string_quotes = ["'"]
    keywords = PASCAL_KEYWORDS
    builtins = sorted(PASCAL)

    def module_template(self, name: str) -> str:
        return (f"{{ {name}.PAS - a unit: add it to the uses clause of MAIN.PAS }}\r\n{{$mode tp}}\r\n"
                f"unit {name};\r\n\r\ninterface\r\n\r\nprocedure Hello;\r\n\r\nimplementation\r\n\r\n"
                f"procedure Hello;\r\nbegin\r\n  WriteLn('Hello from unit {name}');\r\nend;\r\n\r\nend.\r\n")


PLUGIN = DosPascalPlugin()
