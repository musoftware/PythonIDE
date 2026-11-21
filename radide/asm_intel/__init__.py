"""Assembly editor intelligence for RAD IDE (NASM, MASM, FASM, GNU as - Intel and AT&T syntax).

Modules (no Qt in any of them):

    isa         x86 / x86-64 instructions (general purpose, x87, MMX, SSE..SSE4.2, AES, AVX, AVX2, FMA3, BMI)
                and registers, with short original descriptions, operand forms and affected flags
    directives  directives / pseudo-instructions / macro keywords of each assembler
    apis        Win32 API and C runtime signatures + calling-convention helpers (Win64, System V, cdecl, stdcall)
    index       dialect detection and the source parser (labels, procs, macros, constants, data, structs,
                sections, externs, includes) with a project-wide cache
    engine      completions, signature help, hover, Go to Definition, Find References, outline, folding
    snippets    code snippets per dialect / ABI
    monarch     Monaco syntax highlighting (Monarch) + language configuration per dialect
    plugin      AsmIntelMixin (for assembly language plugins) and AsmPluginOverlay (any other plugin)
    lsp         optional asm-lsp language server

The IDE side is radide/features/asm_ide.py; see docs/ASSEMBLY.md ("Editor intelligence").
"""
from __future__ import annotations

from .engine import (AsmCompletion, calltip, completions, definition, document_symbols, folding_ranges, hover,
                     references)
from .index import detect_dialect, is_asm_path
from .plugin import AsmIntelMixin, AsmPluginOverlay, overlay_for

__all__ = ["AsmCompletion", "AsmIntelMixin", "AsmPluginOverlay", "calltip", "completions", "definition",
           "detect_dialect", "document_symbols", "folding_ranges", "hover", "is_asm_path", "overlay_for",
           "references"]
