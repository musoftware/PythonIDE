"""RAD IDE's own 8086 emulator for learning 16-bit assembly (the "8086 Assembly (Emulator)" project type).

Pure Python, no Qt in the core modules:

    assembler   MASM / TASM / emu8086 dialect -> memory image + source map + Error List diagnostics
    cpu         the 8086 instruction set (+ the 80186 extras courses use)
    machine     PC around the CPU: DOS INT 21h, BIOS INT 10h / 16h / 1Ah, text screen 80x25, mode 13h,
                breakpoints, step / step over / step out / reverse step
    includes    a built-in emu8086.inc-compatible helper library (PRINT, PUTC, GOTOXY, SCAN_NUM ...)
    messages    English / Arabic messages
    ui          Qt widgets: screen, registers, memory, stack, variables, the debugger dock and the IDE session

Headless use (tests, tutorials):

    from radide.emu8086 import run_source
    r = run_source(open("main.asm").read(), keys="5\\r")
    r["output"], r["screen"], r["exit_code"]

Command line: ``python -m radide.emu8086 main.asm [--keys "text"] [--screen]``.
"""
from __future__ import annotations

from .assembler import Program, assemble
from .machine import Machine, run_source

__all__ = ["Program", "assemble", "Machine", "run_source"]
