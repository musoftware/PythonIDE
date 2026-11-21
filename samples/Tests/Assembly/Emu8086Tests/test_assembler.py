"""Assembler of radide/emu8086: machine code of the 8086 encodings, layout of COM / EXE programs, the source
map, macros / equ / dup, and the (English + Arabic) error messages that go to the Error List.

Run:  python samples/Tests/Assembly/Emu8086Tests/test_assembler.py      (or with pytest)
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

from radide.emu8086.assembler import assemble  # noqa: E402
from radide.emu8086.machine import run_source  # noqa: E402

# instruction -> bytes (Intel encodings; where two encodings exist the test uses the one this assembler picks)
ENCODINGS = [
    ("mov al, [bx+si+4]", "8A 40 04"),
    ("mov ax, [1234h]", "A1 34 12"),
    ("mov [1234h], al", "A2 34 12"),
    ("mov [di], ax", "89 05"),
    ("mov cx, [bp]", "8B 4E 00"),
    ("mov dx, [bp+di-2]", "8B 53 FE"),
    ("mov bx, 1234h", "BB 34 12"),
    ("mov ah, 9", "B4 09"),
    ("mov byte ptr [bx], 5", "C6 07 05"),
    ("mov word ptr [si+100h], 7", "C7 84 00 01 07 00"),
    ("mov ds, ax", "8E D8"),
    ("mov ax, es", "8C C0"),
    ("mov es:[di], al", "26 88 05"),
    ("add word ptr [bp-2], 5", "83 46 FE 05"),
    ("add ax, 1000h", "05 00 10"),
    ("add al, 1", "04 01"),
    ("add bx, 300h", "81 C3 00 03"),
    ("sub cx, 1", "83 E9 01"),
    ("cmp al, 'a'", "3C 61"),
    ("xor ax, ax", "31 C0"),
    ("and byte ptr [bx], 0Fh", "80 27 0F"),
    ("test al, 1", "A8 01"),
    ("test bx, cx", "85 CB"),
    ("inc si", "46"),
    ("dec byte ptr [di]", "FE 0D"),
    ("push es", "06"),
    ("pop ds", "1F"),
    ("push word ptr [bx]", "FF 37"),
    ("pop ax", "58"),
    ("xchg ax, cx", "91"),
    ("xchg al, [bx]", "86 07"),
    ("lea si, [bx+di+100h]", "8D B1 00 01"),
    ("les di, [bx]", "C4 3F"),
    ("int 21h", "CD 21"),
    ("int 3", "CC"),
    ("rep movsb", "F3 A4"),
    ("repne scasb", "F2 AE"),
    ("in al, dx", "EC"),
    ("out 61h, al", "E6 61"),
    ("shl ax, 1", "D1 E0"),
    ("shr bl, cl", "D2 EB"),
    ("rcr word ptr [si], 1", "D1 1C"),
    ("mul bl", "F6 E3"),
    ("idiv word ptr [bx]", "F7 3F"),
    ("neg ax", "F7 D8"),
    ("not dl", "F6 D2"),
    ("cbw", "98"),
    ("cwd", "99"),
    ("aam", "D4 0A"),
    ("ret", "C3"),
    ("ret 4", "C2 04 00"),
    ("retf", "CB"),
    ("iret", "CF"),
    ("jmp bx", "FF E3"),
    ("call word ptr [bx]", "FF 17"),
    ("lodsw", "AD"),
    ("cld", "FC"),
    ("hlt", "F4"),
]


def code_of(line: str) -> str:
    prog = assemble(f"org 100h\n    {line}\n", "enc.asm")
    assert prog.ok, (line, [str(e) for e in prog.errors])
    data = prog.listing[0][4]
    return data.hex(" ").upper()


def test_encodings():
    for src, expect in ENCODINGS:
        got = code_of(src)
        assert got == expect, f"{src}: {got} (expected {expect})"


def test_jumps_and_sizes():
    prog = assemble("""org 100h
start: jmp short fwd
    nop
fwd: jmp start
    jz start
    loop start
    call sub1
    ret
sub1: ret
""", "j.asm")
    assert prog.ok
    rows = [(r[3], r[4].hex(" ").upper()) for r in prog.listing]
    assert rows[0] == (0x100, "EB 01")               # jmp short +1 (over the nop)
    assert rows[2] == (0x103, "EB FB")               # jmp start: -5
    assert rows[3] == (0x105, "74 F9")
    assert rows[4] == (0x107, "E2 F7")
    assert rows[5] == (0x109, "E8 01 00")            # call sub1 (after the ret at 10Ch)


def test_long_conditional_jump():
    src = "org 100h\n    cmp ax, 0\n    je far_away\n" + "    nop\n" * 200 + "far_away:\n    mov bx, 1\n    int 20h\n"
    prog = assemble(src, "long.asm")
    assert prog.ok
    assert any(w.code == "W-JCC-LONG" for w in prog.warnings)
    r = run_source(src)
    assert r["reason"] == "exit" and r["machine"].cpu.r[3] == 1


def test_loop_out_of_range():
    src = "org 100h\nback:\n" + "    nop\n" * 200 + "    loop back\n    ret\n"
    prog = assemble(src, "loop.asm")
    assert [e.code for e in prog.errors] == ["E-JUMP-RANGE"]
    assert prog.errors[0].line == 203


def test_com_layout_and_source_map():
    prog = assemble("org 100h\nstart:\n    mov ah, 9\n    lea dx, msg\n    int 21h\n    ret\nmsg db 'x$'\n", "c.asm")
    assert prog.ok and prog.com
    assert (prog.entry_cs, prog.entry_ip, prog.ds, prog.sp) == (0x0700, 0x100, 0x0700, 0xFFFE)
    assert prog.chunks[0][0] == 0x7100
    assert prog.addr_line[0x7100] == ("c.asm", 3)
    assert prog.addresses_of("c.asm", 5) == [0x7100 + 2 + 4]
    v = prog.variables[0]
    assert (v.name, v.offset, v.size, v.count) == ("msg", 0x109, 1, 2)


def test_exe_layout():
    src = """.model small
.stack 200h
.data
a dw 1, 2, 3
b db 'hi$'
.code
main proc
    mov ax, @data
    mov ds, ax
    mov ax, a+2
    mov ax, 4C00h
    int 21h
main endp
end main
"""
    prog = assemble(src, "e.asm")
    assert prog.ok and not prog.com
    assert prog.ds == 0x0700                       # DS = ES = PSP at start, like DOS
    code_seg = prog.entry_cs
    assert code_seg == 0x0710                      # right after the PSP
    data = next(v for v in prog.variables if v.name == "a")
    assert data.segment > code_seg and data.offset == 0
    assert prog.sp == 0x200
    r = run_source(src)
    assert r["reason"] == "exit" and r["exit_code"] == 0
    assert r["machine"].cpu.r[0] == 0x4C00


def test_data_definitions():
    prog = assemble("""org 100h
    ret
t1 db 'AB', 0, 2 dup(1, 2), ?
t2 dw 1234h, t1
t3 db 3 dup(2 dup('x'))
t4 dd 12345678h
n  equ 10
t5 db n * 2 + 1
t6 dw 'AB'
len equ $ - t1
""", "d.asm")
    assert prog.ok, [str(e) for e in prog.errors]
    data = dict((r[5].split()[0], r[4]) for r in prog.listing if r[5].split() and r[5].split()[0].startswith("t"))
    assert data["t1"] == b"AB\x00\x01\x02\x01\x02\x00"
    assert data["t2"] == bytes([0x34, 0x12, 0x01, 0x01])         # t1 is at 101h
    assert data["t3"] == b"xxxxxx"
    assert data["t4"] == bytes([0x78, 0x56, 0x34, 0x12])
    assert data["t5"] == bytes([21])
    assert data["t6"] == bytes([0x42, 0x41])
    sym = {v.name: v for v in prog.variables}
    assert sym["t1"].count == 8 and sym["t3"].count == 6


def test_macros_and_local_labels():
    src = """
waitkey macro
    local again
again:
    mov ah, 1
    int 16h
    jz again
endm
show macro ch_
    mov dl, ch_
    mov ah, 2
    int 21h
endm
org 100h
    show 'A'
    show 'B'
    waitkey
    waitkey
    ret
"""
    prog = assemble(src, "m.asm")
    assert prog.ok, [str(e) for e in prog.errors]
    lines = sorted({ln for _f, ln in prog.addr_line.values()})
    assert lines == [15, 16, 17, 18, 19]                   # macro code maps to the call line
    r = run_source(src, keys="xy")
    assert r["output"] == "AB" and r["reason"] == "exit"


def test_text_equ_and_operators():
    src = """org 100h
arg1 equ [bp+4]
cnt  = 3
cnt  = cnt + 1
    mov ax, cnt
    mov bx, (5 shl 2) or 1
    mov cx, 17 mod 5
    mov dx, high 1234h
    mov si, low 1234h
    mov di, type buffer
    mov bp, length buffer
    ret
buffer dw 7 dup(0)
"""
    r = run_source(src)
    c = r["machine"].cpu
    assert (c.r[0], c.r[3], c.r[1], c.r[2], c.r[6], c.r[7], c.r[5]) == (4, 21, 2, 0x12, 0x34, 2, 7)


def test_emu8086_include():
    src = "include 'emu8086.inc'\norg 100h\n PRINT 'Sum: '\n MOV AX, 25\n ADD AX, -30\n CALL PRINT_NUM\n PUTC '!'\n RET\n" \
          "DEFINE_PRINT_NUM\nDEFINE_PRINT_NUM_UNS\nEND\n"
    r = run_source(src)
    assert r["output"] == "Sum: -5!", r


def test_errors():
    cases = [
        ("mov ds, 5", "E-IMM-SREG"),
        ("mov ax, [bx+cx]", "E-BAD-REGS"),
        ("mov al, bx", "E-SIZE-MISMATCH"),
        ("mov [bx], 5", "E-SIZE-UNKNOWN"),
        ("mov foo, ax", "E-UNDEF"),
        ("mov cs, ax", "E-CS-DEST"),
        ("mov 5, ax", "E-IMM-DEST"),
        ("movx ax, bx", "E-UNKNOWN-INSTR"),
        ("mov al, 300", "E-RANGE"),
        ("add [x], [x]", "E-MEM-MEM"),
        ("push al", "E-REG16"),
        ("in bl, dx", "E-ACC"),
    ]
    for line, code in cases:
        prog = assemble(f"org 100h\n    {line}\n    ret\nx dw 0\n", "err.asm")
        codes = [e.code for e in prog.errors]
        assert code in codes, f"{line}: {codes}"
        assert prog.errors[0].line == 2, (line, prog.errors[0].line)
    prog = assemble("org 100h\nx: nop\nx: nop\n", "dup.asm")
    assert [e.code for e in prog.errors] == ["E-REDEF"] and prog.errors[0].line == 3
    prog = assemble("org 100h\nmain proc\n  ret\n", "p.asm")
    assert "E-PROC-OPEN" in [e.code for e in prog.errors]


def test_arabic_messages():
    prog = assemble("org 100h\n    mov ds, 5\n", "ar.asm")
    text = prog.errors[0].text("ar")
    assert re.search(r"[؀-ۿ]", text) and "mov ax" in text
    assert "segment register" in prog.errors[0].text("en")


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_") and callable(v)]
    fails = 0
    for fn in tests:
        try:
            fn()
            print("PASS", fn.__name__)
        except AssertionError as e:
            fails += 1
            print("FAIL", fn.__name__, e)
    print(f"{len(tests)} tests ({len(ENCODINGS)} encodings); failures: {fails}")
    sys.exit(1 if fails else 0)
