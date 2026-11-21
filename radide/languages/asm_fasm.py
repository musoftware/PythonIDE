"""Assembly (FASM) - console programs written with the flat assembler (format PE / PE64: no linker).

FASM is downloaded from flatassembler.net on the first build when it is not installed; RAD IDE points the
INCLUDE environment variable at FASM's INCLUDE folder (win32a.inc / win64a.inc). A source with
``format MS64 COFF`` / ``format MS COFF`` is linked with gcc / ld instead. Details: docs/ASSEMBLY.md.
"""
from __future__ import annotations

from .asm_base import AsmPluginBase


class FasmPlugin(AsmPluginBase):
    id = "asm-fasm"
    display_name = "Assembly (FASM)"
    code_ext = ".asm"
    assembler = "fasm"
    asm_dialect = "fasm"
    tool_key = "fasm"
    has_forms = False
    install_hint = "FASM is downloaded automatically from https://flatassembler.net on the first build."
    keywords = AsmPluginBase.keywords + """format entry include section data code readable writeable executable
        import library invoke cinvoke stdcall ccall proc endp local locals endl macro struc virtual end if else
        repeat while db dw dd dq du rb rw rd rq file label equ fix align use16 use32 use64 PE PE64 console GUI
        DLL MS COFF MS64 ELF ELF64 byte word dword qword ptr""".split()

    def module_template(self, name: str) -> str:
        return (f"; {name}: include it from the main file with   include '{name}.asm'\n"
                f"; (FASM assembles one file; the others are included).\n\n"
                f"{name}_add:                ; RAX = RCX + RDX\n    lea rax, [rcx + rdx]\n    ret\n")


PLUGIN = FasmPlugin()
