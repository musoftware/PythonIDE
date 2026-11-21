"""Assembly (MASM) - console programs for Microsoft's ml64 / ml, linked with link.exe.

Only available when a Visual Studio with the C++ tools is installed (found through vswhere); RAD IDE never
downloads MASM. ml64 / ml write CodeView debug information (a PDB): debugging needs the Visual Studio
debugger, gdb cannot read it. Details: docs/ASSEMBLY.md.
"""
from __future__ import annotations

from .asm_base import AsmPluginBase


class MasmPlugin(AsmPluginBase):
    id = "asm-masm"
    display_name = "Assembly (MASM)"
    code_ext = ".asm"
    assembler = "masm"
    asm_dialect = "masm"
    tool_key = "ml64"
    downloadable = False
    has_forms = False
    install_hint = ("MASM (ml64.exe / ml.exe) comes with Visual Studio: install the 'Desktop development with "
                    "C++' workload.")
    keywords = AsmPluginBase.keywords + """proc endp proto invoke addr offset ptr byte word dword qword sbyte
        sword sdword sqword real4 real8 db dw dd dq dup model flat stdcall c code data const stack end extern
        externdef public include includelib local uses if else elseif endif while endw repeat until macro
        endm struct ends union equ textequ option frame""".split()

    def project_templates(self):
        from ..asm import toolchain as tc
        items = super().project_templates()
        if not tc.find_masm("x64"):
            items = [(i, t + " (needs Visual Studio)", d, ic) for i, t, d, ic in items]
        return items

    def module_template(self, name: str) -> str:
        return (f"; Module {name} (ml64): PUBLIC makes a procedure visible to the other files of the project.\n"
                f".code\n\n{name}_add proc         ; RAX = RCX + RDX\n    lea rax, [rcx + rdx]\n    ret\n"
                f"{name}_add endp\n\nend\n")


PLUGIN = MasmPlugin()
