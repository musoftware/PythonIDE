"""Assembly (GNU as) - console programs for the GNU assembler of MinGW-w64 (AT&T or Intel syntax).

``as --64 --gdwarf-3`` writes DWARF line information, so F5 debugging with gdb works by line. Linked with gcc.
Windows Forms (GUI Bridge, x64, AT&T or Intel syntax: radgui_att.inc / radgui_intel.inc). Details:
docs/ASSEMBLY.md.
"""
from __future__ import annotations

from .asm_base import AsmPluginBase


class GasPlugin(AsmPluginBase):
    id = "asm-gas"
    display_name = "Assembly (GNU as)"
    code_ext = ".s"
    assembler = "gas"
    asm_dialect = "gas"
    tool_key = "as"
    downloadable = False
    has_forms = True
    supports_forms = True               # GUI Bridge forms (AT&T: gas64, Intel: gas64i)
    form_flavor = "gas64"
    line_comments = ["#"]
    block_comment = ("/*", "*/")
    string_quotes = ['"']
    install_hint = ("GNU as comes with the MinGW-w64 toolchain of the C support (WinLibs in "
                    "%LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64).")
    keywords = AsmPluginBase.keywords + """movq movl movw movb addq addl subq subl leaq leal pushq popq cmpq cmpl
        testq testl xorq xorl andq orq incq decq imulq idivq shlq shrq sarq callq retq jmpq cltq cqto
        .text .data .bss .section .globl .global .extern .byte .short .word .long .quad .ascii .asciz .string
        .space .zero .align .p2align .balign .comm .lcomm .equ .set .intel_syntax .att_syntax noprefix .macro
        .endm .rept .endr .if .else .endif .include .file .loc .type .size .def .scl .endef""".split()

    def module_template(self, name: str) -> str:
        return (f"# Module {name}: .globl makes a label visible to the other files of the project.\n"
                f"        .text\n        .globl {name}_add\n"
                f"{name}_add:                     # %rax = %rcx + %rdx\n        leaq (%rcx,%rdx), %rax\n        ret\n")


PLUGIN = GasPlugin()
