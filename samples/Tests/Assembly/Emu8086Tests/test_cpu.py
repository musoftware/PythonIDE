"""8086 instruction semantics of radide/emu8086: results and flags compared with the values the Intel 8086
manual defines. Each case is a tiny COM program; the registers are checked when it ends (INT 20h).

Run:  python samples/Tests/Assembly/Emu8086Tests/test_cpu.py      (or with pytest)
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

from radide.emu8086.assembler import assemble  # noqa: E402
from radide.emu8086.cpu import AF, CF, OF, PF, SF, ZF  # noqa: E402
from radide.emu8086.machine import Machine  # noqa: E402

FLAGS = {"CF": CF, "PF": PF, "AF": AF, "ZF": ZF, "SF": SF, "OF": OF}
REGS16 = ("AX", "CX", "DX", "BX", "SP", "BP", "SI", "DI")


def run(code: str, keys: str = "", max_steps: int = 200_000) -> Machine:
    prog = assemble("org 100h\n" + code + "\n    int 20h\n", "t.asm")
    assert prog.ok, [str(e) for e in prog.errors]
    m = Machine()
    m.record_history = False
    m.load(prog)
    m.feed_keys(keys)
    info = m.run(max_steps)
    assert info.reason in ("exit", "error"), info
    return m


def reg(m: Machine, name: str) -> int:
    name = name.upper()
    c = m.cpu
    if name in REGS16:
        return c.r[REGS16.index(name)]
    r8 = ("AL", "CL", "DL", "BL", "AH", "CH", "DH", "BH")
    if name in r8:
        return c.get8(r8.index(name))
    raise KeyError(name)


def flags(m: Machine) -> dict:
    return {k: int(bool(m.cpu.flags & v)) for k, v in FLAGS.items()}


CASES = [
    # (name, code, expected registers, expected flags)
    ("add carry zero", "mov al, 1\n add al, 0FFh", {"AL": 0}, {"CF": 1, "ZF": 1, "AF": 1, "OF": 0, "SF": 0, "PF": 1}),
    ("add signed overflow", "mov al, 7Fh\n add al, 1", {"AL": 0x80}, {"OF": 1, "SF": 1, "CF": 0, "AF": 1, "PF": 0}),
    ("add 16", "mov ax, 0FFFFh\n add ax, 2", {"AX": 1}, {"CF": 1, "ZF": 0, "OF": 0}),
    ("adc", "stc\n mov ax, 10\n adc ax, 5", {"AX": 16}, {"CF": 0}),
    ("sub borrow", "mov al, 0\n sub al, 1", {"AL": 0xFF}, {"CF": 1, "SF": 1, "OF": 0, "ZF": 0, "AF": 1, "PF": 1}),
    ("sub overflow", "mov al, 80h\n sub al, 1", {"AL": 0x7F}, {"OF": 1, "CF": 0, "SF": 0}),
    ("sbb", "stc\n mov ax, 10\n sbb ax, 3", {"AX": 6}, {"CF": 0}),
    ("cmp less", "mov ax, 5\n mov bx, 7\n cmp ax, bx", {"AX": 5}, {"CF": 1, "ZF": 0, "SF": 1}),
    ("cmp equal", "mov cx, 1234h\n cmp cx, 1234h", {}, {"ZF": 1, "CF": 0}),
    ("inc keeps CF", "stc\n mov al, 0FFh\n inc al", {"AL": 0}, {"ZF": 1, "CF": 1, "AF": 1}),
    ("dec overflow", "mov ax, 8000h\n dec ax", {"AX": 0x7FFF}, {"OF": 1}),
    ("neg", "mov al, 5\n neg al", {"AL": 0xFB}, {"CF": 1, "SF": 1}),
    ("neg zero", "mov al, 0\n neg al", {"AL": 0}, {"CF": 0, "ZF": 1}),
    ("and clears CF OF", "stc\n mov al, 0F0h\n and al, 3Ch", {"AL": 0x30}, {"CF": 0, "OF": 0, "PF": 1}),
    ("or", "mov al, 0Fh\n or al, 0F0h", {"AL": 0xFF}, {"SF": 1, "PF": 1}),
    ("xor self", "mov ax, 1234h\n xor ax, ax", {"AX": 0}, {"ZF": 1, "PF": 1}),
    ("not keeps flags", "stc\n mov ax, 00FFh\n not ax", {"AX": 0xFF00}, {"CF": 1}),
    ("test", "mov al, 81h\n test al, 80h", {"AL": 0x81}, {"ZF": 0, "SF": 1}),
    ("mul 8", "mov al, 200\n mov bl, 2\n mul bl", {"AX": 400}, {"CF": 1, "OF": 1}),
    ("mul 8 small", "mov al, 20\n mov bl, 3\n mul bl", {"AX": 60}, {"CF": 0, "OF": 0}),
    ("mul 16", "mov ax, 0FFFFh\n mov bx, 0FFFFh\n mul bx", {"DX": 0xFFFE, "AX": 1}, {"CF": 1}),
    ("imul 8", "mov al, -2\n mov bl, 3\n imul bl", {"AX": 0xFFFA}, {"CF": 0, "OF": 0}),
    ("imul 16 overflow", "mov ax, 300\n mov bx, 300\n imul bx", {"AX": 90000 & 0xFFFF, "DX": 1}, {"CF": 1}),
    ("div 8", "mov ax, 100\n mov bl, 7\n div bl", {"AL": 14, "AH": 2}, {}),
    ("div 16", "mov dx, 1\n mov ax, 0\n mov bx, 10h\n div bx", {"AX": 0x1000, "DX": 0}, {}),
    ("idiv 16", "mov ax, -7\n cwd\n mov bx, 2\n idiv bx", {"AX": 0xFFFD, "DX": 0xFFFF}, {}),
    ("idiv 8", "mov ax, -50\n mov bl, 7\n idiv bl", {"AL": (-7) & 0xFF, "AH": (-1) & 0xFF}, {}),
    ("shl 1", "mov al, 81h\n shl al, 1", {"AL": 0x02}, {"CF": 1, "OF": 1}),
    ("shr 1", "mov al, 81h\n shr al, 1", {"AL": 0x40}, {"CF": 1, "OF": 1}),
    ("sar 1", "mov al, 81h\n sar al, 1", {"AL": 0xC0}, {"CF": 1, "OF": 0}),
    ("shl cl", "mov ax, 1234h\n mov cl, 4\n shl ax, cl", {"AX": 0x2340}, {"CF": 1}),
    ("shr cl", "mov ax, 8000h\n mov cl, 15\n shr ax, cl", {"AX": 1}, {"CF": 0}),
    ("rol", "mov al, 81h\n rol al, 1", {"AL": 0x03}, {"CF": 1}),
    ("ror", "mov al, 81h\n ror al, 1", {"AL": 0xC0}, {"CF": 1}),
    ("rcl", "clc\n mov al, 80h\n rcl al, 1", {"AL": 0x00}, {"CF": 1}),
    ("rcr", "stc\n mov al, 1\n rcr al, 1", {"AL": 0x80}, {"CF": 1}),
    ("rol 16 by cl", "mov ax, 1234h\n mov cl, 8\n rol ax, cl", {"AX": 0x3412}, {}),
    ("daa", "mov al, 15h\n add al, 27h\n daa", {"AL": 0x42}, {"CF": 0}),
    ("daa carry", "mov al, 99h\n add al, 1\n daa", {"AL": 0x00}, {"CF": 1}),
    ("das", "mov al, 42h\n sub al, 15h\n das", {"AL": 0x27}, {}),
    ("aaa", "mov ax, 0009h\n add al, 5\n aaa", {"AX": 0x0104}, {"CF": 1}),
    ("aas", "mov ax, 0102h\n sub al, 5\n aas", {"AX": 0x0007}, {"CF": 1}),
    ("aam", "mov al, 63\n aam", {"AX": 0x0603}, {}),
    ("aad", "mov ax, 0603h\n aad", {"AX": 0x003F}, {}),
    ("cbw", "mov al, 0F0h\n cbw", {"AX": 0xFFF0}, {}),
    ("cwd", "mov ax, 8000h\n cwd", {"DX": 0xFFFF}, {}),
    ("xchg", "mov ax, 1\n mov bx, 2\n xchg ax, bx", {"AX": 2, "BX": 1}, {}),
    ("xchg 8", "mov al, 1\n mov ah, 2\n xchg al, ah", {"AX": 0x0102}, {}),
    ("push pop", "mov ax, 1234h\n push ax\n pop bx", {"BX": 0x1234}, {}),
    ("pushf popf", "stc\n pushf\n clc\n popf", {}, {"CF": 1}),
    ("lahf sahf", "stc\n lahf\n clc\n sahf", {}, {"CF": 1}),
    ("lea", "mov bx, 10h\n mov si, 20h\n lea di, [bx+si+4]", {"DI": 0x34}, {}),
    ("loop count", "xor ax, ax\n mov cx, 10\nl1: inc ax\n loop l1", {"AX": 10, "CX": 0}, {}),
    ("jcxz", "mov cx, 0\n mov ax, 1\n jcxz skip\n mov ax, 2\nskip:", {"AX": 1}, {}),
    ("loopne", "mov cx, 10\n xor ax, ax\nl2: inc ax\n cmp ax, 3\n loopne l2", {"AX": 3, "CX": 7}, {}),
    ("signed jl", "mov al, -1\n cmp al, 1\n mov bx, 0\n jl yes\n mov bx, 2\nyes: inc bx", {"BX": 1}, {}),
    ("unsigned ja", "mov al, -1\n cmp al, 1\n mov bx, 0\n ja yes\n mov bx, 2\nyes: inc bx", {"BX": 1}, {}),
    ("jg not taken", "mov ax, 5\n cmp ax, 5\n mov bx, 1\n jg no\n mov bx, 7\nno:", {"BX": 7}, {}),
    ("call ret", "mov ax, 1\n call f\n inc ax\n jmp done\nf: add ax, 10\n ret\ndone:", {"AX": 12}, {}),
    ("xlat", "mov bx, offset table\n mov al, 3\n xlat\n jmp e\ntable db 10, 20, 30, 40, 50\ne:", {"AL": 40}, {}),
    ("cmc", "clc\n cmc", {}, {"CF": 1}),
    ("shl imm 186", "mov ax, 3\n shl ax, 3", {"AX": 24}, {}),
    ("push imm 186", "push 7\n pop cx", {"CX": 7}, {}),
    ("pusha popa", "mov ax, 1\n mov bx, 2\n pusha\n xor ax, ax\n xor bx, bx\n popa", {"AX": 1, "BX": 2}, {}),
]

STRING_CASES = [
    ("rep movsb", """
    push cs
    pop es
    mov si, offset src
    mov di, offset dst
    mov cx, 5
    cld
    rep movsb
    mov al, dst+4
    jmp e
src db 'HELLO'
dst db 5 dup(0)
e:""", {"AL": ord("O"), "CX": 0}),
    ("repne scasb", """
    push cs
    pop es
    mov di, offset text
    mov al, 'x'
    mov cx, 10
    cld
    repne scasb
    mov bx, di
    sub bx, offset text
    jmp e
text db 'abcxefghij'
e:""", {"BX": 4, "CX": 6}),
    ("repe cmpsb", """
    push cs
    pop es
    mov si, offset a1
    mov di, offset a2
    mov cx, 6
    cld
    repe cmpsb
    mov bx, cx
    jmp e
a1 db 'abcdef'
a2 db 'abcXef'
e:""", {"BX": 2}),
    ("stosw std", """
    push cs
    pop es
    mov di, offset buf+6
    mov ax, 0A0Bh
    mov cx, 4
    std
    rep stosw
    cld
    mov bx, word ptr buf
    jmp e
buf dw 4 dup(0)
e:""", {"BX": 0x0A0B}),
    ("lodsb loop", """
    mov si, offset nums
    mov cx, 4
    xor bx, bx
next:
    lodsb
    add bl, al
    loop next
    jmp e
nums db 1, 2, 3, 4
e:""", {"BL": 10}),
]


def test_cases():
    for name, code, regs, fl in CASES:
        m = run(code)
        for r, v in regs.items():
            assert reg(m, r) == v, f"{name}: {r} = {reg(m, r):04X}, expected {v:04X}"
        got = flags(m)
        for f, v in fl.items():
            assert got[f] == v, f"{name}: {f} = {got[f]}, expected {v} (flags {got})"


def test_strings():
    for name, code, regs in STRING_CASES:
        m = run(code)
        for r, v in regs.items():
            assert reg(m, r) == v, f"{name}: {r} = {reg(m, r):04X}, expected {v:04X}"


def test_divide_error():
    m = run("mov ax, 10\n mov bl, 0\n div bl")
    assert m.error and "divide" in m.error.lower()
    m = run("mov ax, 1000\n mov bl, 2\n div bl")           # quotient 500 does not fit in AL
    assert m.error


def test_memory_and_segments():
    m = run("""
    mov ax, 0B800h
    mov es, ax
    mov byte ptr es:[0], 'Z'
    mov byte ptr es:[1], 4Eh
    mov word ptr [var], 0BEEFh
    mov bx, offset var
    mov cx, [bx]
    jmp e
var dw 0
e:""")
    assert m.mem[0xB8000] == ord("Z") and m.mem[0xB8001] == 0x4E
    assert reg(m, "CX") == 0xBEEF


def test_far_call_and_interrupt_vector():
    src = """
code segment
    assume cs:code, ds:code
start:
    push cs
    pop ds
    ; install our own INT 60h handler, then call it
    mov ax, 0
    mov es, ax
    mov word ptr es:[60h*4], offset handler
    mov es:[60h*4+2], cs
    mov ax, 5
    int 60h
    call far ptr farproc
    mov ax, 4C00h + 0
    mov al, bl
    int 21h
handler:
    add ax, 10
    iret
farproc proc far
    mov bl, al
    add bl, 2
    ret
farproc endp
code ends
end start
"""
    prog = assemble(src, "far.asm")
    assert prog.ok, [str(e) for e in prog.errors]
    m = Machine()
    m.load(prog)
    info = m.run(10000)
    assert info.reason == "exit" and m.exit_code == 17, (info, m.exit_code)


def test_reverse_step():
    prog = assemble("org 100h\n mov ax, 1\n mov bx, 2\n mov [v], ax\n add ax, bx\n int 20h\nv dw 0\n", "r.asm")
    m = Machine()
    m.load(prog)
    for _ in range(4):
        m.step()
    v_addr = prog.variables[0].linear
    assert m.cpu.r[0] == 3 and m.mem[v_addr] == 1
    m.step_back()
    m.step_back()
    assert m.cpu.r[0] == 1 and m.mem[v_addr] == 0          # the memory write was undone too
    assert m.current_line() == ("r.asm", 4)


def test_keyboard_services():
    m = run("mov ah, 1\n int 21h\n mov bl, al\n mov ah, 0\n int 16h\n mov cx, ax", keys="ab")
    assert reg(m, "BL") == ord("a") and reg(m, "CL") == ord("b") and reg(m, "CH") == 0x30   # scan code of 'b'
    assert m.output == "a"                                 # function 01h echoes, INT 16h does not


def test_input_wait():
    prog = assemble("org 100h\n mov ah, 1\n int 21h\n mov bl, al\n int 20h\n", "w.asm")
    m = Machine()
    m.load(prog)
    info = m.run(1000)
    assert info.reason == "input"
    m.feed_keys("q")
    info = m.run(1000)
    assert info.reason == "exit" and m.cpu.get8(3) == ord("q")


if __name__ == "__main__":
    fails = 0
    for fn in (test_cases, test_strings, test_divide_error, test_memory_and_segments,
               test_far_call_and_interrupt_vector, test_reverse_step, test_keyboard_services, test_input_wait):
        try:
            fn()
            print("PASS", fn.__name__)
        except AssertionError as e:
            fails += 1
            print("FAIL", fn.__name__, e)
    print(f"{len(CASES)} instruction cases + {len(STRING_CASES)} string cases; failures: {fails}")
    sys.exit(1 if fails else 0)
