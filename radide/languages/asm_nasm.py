"""Assembly (NASM) - x64 / x86 Windows console programs, the Win32 API and Windows Forms (GUI Bridge).

New Project > Assembly > NASM: Console (x64), Console (x86), Win32 API (x64), Windows Forms (NASM + GUI Bridge).
NASM is downloaded from nasm.us on the first build when it is not installed (radide/asm/toolchain.py); gcc / ld
come from the MinGW-w64 toolchain of the C support. F5 debugging uses gdb with the DWARF line information that
RAD IDE generates for NASM objects (radide/asm/dwarf.py). Details: docs/ASSEMBLY.md.
"""
from __future__ import annotations

from .asm_base import AsmPluginBase


class NasmPlugin(AsmPluginBase):
    id = "asm-nasm"
    display_name = "Assembly (NASM)"
    code_ext = ".asm"
    assembler = "nasm"
    tool_key = "nasm"
    supports_forms = True
    install_hint = ("NASM is downloaded automatically from https://www.nasm.us on the first build; the linker is "
                    "the MinGW-w64 gcc of the C support (WinLibs in %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64).")
    keywords = AsmPluginBase.keywords + """section segment global extern default rel abs bits use16 use32 use64
        db dw dd dq dt do dy resb resw resd resq rest reso times equ align alignb byte word dword qword tword
        oword yword ptr strict nosplit wrt seg incbin struc endstruc istruc iend at""".split()

    def module_template(self, name: str) -> str:
        return (f"; Module {name}: assembled and linked with the project. 'global' makes a label visible to the\n"
                f"; other files of the project; declare it there with 'extern'.\n"
                f"default rel\n\nglobal {name}_add\n\nsection .text\n\n"
                f"; long long {name}_add(long long a, long long b) - x64: a in RCX, b in RDX, result in RAX\n"
                f"{name}_add:\n    lea rax, [rcx + rdx]\n    ret\n")


PLUGIN = NasmPlugin()
