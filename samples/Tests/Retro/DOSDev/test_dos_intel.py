"""DOS IntelliSense: interrupt hovers (INT 21h / 10h / 16h / 33h / 1Ah with the function from the registers set
above), QBasic / Crt / conio hovers, completions, signature help, outline, Go to Definition, error parsers."""
from __future__ import annotations

import sys
from pathlib import Path

from _common import check, summary

from radide.languages import get_plugin
from radide.retro.dos import errors, intel, reference as R


def main() -> int:
    asm = get_plugin("dos-asm")
    code = "        mov ah, 09h\n        mov dx, offset msg\n        int 21h\n        mov ax, 4C00h\n        int 21h\n"
    h = asm.hover(code, 2, 13, Path("MAIN.ASM"))
    check("asm: hover INT 21h after mov ah, 09h -> Print string", "INT 21h" in h and "Print string" in h, h)
    h = asm.hover(code, 4, 13, Path("MAIN.ASM"))
    check("asm: mov ax, 4C00h -> AH=4Ch Exit program", "Exit program" in h, h)
    code10 = "    mov ax, 0013h\n    int 10h\n"
    check("asm: INT 10h AX=0013h -> Set video mode", "Set video mode" in asm.hover(code10, 1, 9, Path("A.ASM")))
    code33 = "    mov ax, 3\n    int 33h\n"
    check("asm: INT 33h AX=3 -> Position and buttons", "Position and buttons" in asm.hover(code33, 1, 9, Path("A")))
    code1a = "    mov ah, 0\n    int 1Ah\n"
    check("asm: INT 1Ah -> tick counter", "tick counter" in asm.hover(code1a, 1, 9, Path("A")))
    check("asm: hover instruction (mov)", "copy" in asm.hover(code, 0, 9, Path("A")).lower())
    comps = {c.name for c in asm.completions("    int ", 0, 8, Path("A"))}
    check("asm: completions after 'int ' list 21h / 10h / 16h / 33h / 1Ah",
          {"21h", "10h", "16h", "33h", "1Ah"} <= comps, comps)
    check("asm: calltip shows registers", "DS:DX" in asm.calltip(code, 2, 15, Path("A")))
    pas = get_plugin("dos-pascal")
    pcode = "uses Dos;\nvar R: Registers;\nbegin\n  R.AH := $2C;\n  Intr($21, R);\nend.\n"
    check("pascal: Intr($21) after R.AH := $2C -> Get time", "Get time" in pas.hover(pcode, 4, 4, Path("A.PAS")))
    check("pascal: hover GotoXY (Crt)", "Crt" in pas.hover("  GotoXY(1, 2);", 0, 4, Path("A.PAS")))
    check("pascal: signature help", "X, Y: Byte" in pas.calltip("  GotoXY(", 0, 9, Path("A.PAS")))
    c = get_plugin("dos-c")
    ccode = "    r.h.ah = 0x00;\n    int86(0x16, &r, &r);\n"
    check("C: int86(0x16) after r.h.ah = 0x00 -> Wait for key", "Wait for key" in c.hover(ccode, 1, 6, Path("A.C")))
    check("C: hover gotoxy (tcconio.h)", "tcconio.h" in c.hover("gotoxy(1,1);", 0, 2, Path("A.C")))
    check("C: completions include cprintf / int86 / MK_FP",
          {"cprintf", "int86", "MK_FP"} <= {x.name for x in c.completions("", 0, 0, Path("A.C"))})
    qb = get_plugin("dos-qbasic")
    qcode = "10 GOSUB 1000\n20 END\n1000 LOCATE 5, 10\nSUB Hello\nEND SUB\n"
    check("QBasic: hover LOCATE", "LOCATE [row]" in qb.hover(qcode, 2, 6, Path("A.BAS")))
    check("QBasic: hover LINE INPUT", "whole line" in qb.hover("LINE INPUT a$", 0, 1, Path("A.BAS")))
    check("QBasic: F12 on GOSUB 1000 -> line 1000", qb.definition(qcode, 0, 10, Path("A.BAS")) == ("A.BAS", 2))
    check("QBasic: outline has SUB Hello", any(s["name"] == "Hello" for s in qb.document_symbols(qcode)))
    bat = get_plugin("dos-batch")
    check("batch: hover CHOICE", "ERRORLEVEL" in bat.hover("CHOICE /C:123", 0, 2, Path("A.BAT")))
    check("batch: outline labels", [s["name"] for s in bat.document_symbols("@echo off\n:MENU\ngoto MENU\n:END\n")]
          == ["MENU", "END"])
    check("reference: every interrupt function has in/out/description",
          all(f.inputs and f.outputs and f.en for it in R.INTERRUPTS.values() for f in it.functions.values()))
    check("reference: Arabic for every interrupt function",
          all(f.ar for it in R.INTERRUPTS.values() for f in it.functions.values()))
    check("interrupt_at: no function when another INT is between",
          intel.interrupt_at(["mov ah, 9", "int 21h", "int 21h"], 2) == (0x21, None))
    # error parsers
    fb = errors.parse_freebasic("MAIN.BAS(3) error 9: Expected expression\nMAIN.BAS() error 48: Undefined label, 50\n")
    check("FreeBASIC parser", fb[0].line == 3 and fb[0].severity == "Error" and fb[1].line == 0, fb)
    fpc = errors.parse_fpc("MAIN.PAS(10,3) Error: Identifier not found \"x\"\nMAIN.PAS(12) Fatal: There were 1 errors\n")
    check("Free Pascal parser", len(fpc) == 1 and (fpc[0].line, fpc[0].col) == (10, 3), fpc)
    ow = errors.parse_watcom("MAIN.C(8): Error! E1011: Symbol 'x' has not been declared\nError! E2028: _f_ is an "
                             "undefined reference\n")
    check("Open Watcom parser (compiler + linker)", ow[0].line == 8 and ow[1].tool == "wlink", ow)
    jw = errors.parse_jwasm("MAIN.ASM(11) : Error A2209: Syntax error: movv\n")
    check("JWasm parser", jw and jw[0].line == 11 and "A2209" in jw[0].message, jw)
    tp = errors.parse_turbo_pascal("MAIN.PAS(10): Error 3: Unknown identifier.\n")
    check("Turbo Pascal parser", tp and tp[0].line == 10, tp)
    tc = errors.parse_turbo_c("Error MAIN.C 5: Undefined symbol 'x' in function main\n")
    check("Turbo C parser", tc and tc[0].line == 5 and tc[0].file == "MAIN.C", tc)
    gcc = errors.parse_gcc("main.c:5:3: error: 'x' undeclared\n")
    check("DJGPP gcc parser", gcc and (gcc[0].line, gcc[0].col) == (5, 3), gcc)
    return summary()


if __name__ == "__main__":
    sys.exit(main())
