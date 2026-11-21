"""Zilog Z80 instruction set (ZX Spectrum, MSX, Sega Master System, CP/M), sjasmplus / pasmo syntax.

``decode(data, offset, addr, undocumented)`` -> ``Instr``. Decoding follows the x/y/z/p/q fields of the opcode
byte (the classic way to read the Z80 tables), with the CB, ED, DD / FD (IX / IY) and DDCB / FDCB prefixes.
Undocumented forms (IXH / IXL, SLL, ED duplicates, DDCB register copies, OUT (C),0, IN (C)) are flagged
``undocumented``: the disassembler writes them back as ``db`` bytes with the mnemonic in a comment. A DD / FD
prefix in front of an instruction that does not use HL is kept as a one-byte ``db`` (it does nothing).
Cycle counts are T-states; "a/b" = taken / not taken.
"""
from __future__ import annotations

from . import Instr

R = ["b", "c", "d", "e", "h", "l", "(hl)", "a"]
RP = ["bc", "de", "hl", "sp"]
RP2 = ["bc", "de", "hl", "af"]
CC = ["nz", "z", "nc", "c", "po", "pe", "p", "m"]
ALU = ["add a,", "adc a,", "sub", "sbc a,", "and", "xor", "or", "cp"]
ROT = ["rlc", "rrc", "rl", "rr", "sla", "sra", "sll", "srl"]
BLOCK = {(4, 0): "ldi", (4, 1): "cpi", (4, 2): "ini", (4, 3): "outi", (5, 0): "ldd", (5, 1): "cpd",
         (5, 2): "ind", (5, 3): "outd", (6, 0): "ldir", (6, 1): "cpir", (6, 2): "inir", (6, 3): "otir",
         (7, 0): "lddr", (7, 1): "cpdr", (7, 2): "indr", (7, 3): "otdr"}

MNEMONICS = sorted({"nop", "ld", "inc", "dec", "add", "adc", "sub", "sbc", "and", "xor", "or", "cp", "rlca", "rrca",
                    "rla", "rra", "daa", "cpl", "scf", "ccf", "halt", "djnz", "jr", "jp", "call", "ret", "reti",
                    "retn", "rst", "push", "pop", "di", "ei", "ex", "exx", "out", "in", "rlc", "rrc", "rl", "rr",
                    "sla", "sra", "srl", "bit", "res", "set", "neg", "im", "rrd", "rld"} | set(BLOCK.values()))
REGISTERS = ["a", "b", "c", "d", "e", "h", "l", "f", "i", "r", "af", "bc", "de", "hl", "sp", "ix", "iy", "af'",
             "ixh", "ixl", "iyh", "iyl"]
CONDITIONS = CC

FLAGS = {"add": "S Z H P/V N C (16-bit: H N C)", "adc": "S Z H V N C", "sub": "S Z H V N C", "sbc": "S Z H V N C",
         "cp": "S Z H V N C", "and": "S Z H P N C", "or": "S Z H P N C", "xor": "S Z H P N C", "inc": "S Z H V N",
         "dec": "S Z H V N", "neg": "S Z H V N C", "daa": "S Z H P C", "cpl": "H N", "scf": "H N C",
         "ccf": "H N C", "rlca": "H N C", "rrca": "H N C", "rla": "H N C", "rra": "H N C", "bit": "S? Z H P? N",
         "ldi": "H P/V N", "ldir": "H P/V N", "cpi": "S Z H P/V N", "cpir": "S Z H P/V N", "in": "S Z H P N"}

DOCS: dict[str, tuple[str, str]] = {
    "ld": ("Load: ld dest, src (8 or 16 bit). (nn) = memory at address nn; (ix+d) = indexed.", "تحميل."),
    "inc": ("Increment by one.", "زيادة بمقدار 1."), "dec": ("Decrement by one.", "إنقاص بمقدار 1."),
    "add": ("Add (A, HL, IX, IY).", "جمع."), "adc": ("Add with carry.", "جمع مع الحمل."),
    "sub": ("Subtract from A.", "طرح من A."), "sbc": ("Subtract with carry (borrow).", "طرح مع الاستلاف."),
    "and": ("A = A AND value.", "عملية AND."), "or": ("A = A OR value.", "عملية OR."),
    "xor": ("A = A XOR value; xor a clears A.", "عملية XOR."), "cp": ("Compare with A.", "مقارنة بـ A."),
    "djnz": ("B = B - 1; jump (relative) while B is not 0 - the Z80 loop instruction.",
             "إنقاص B والقفز ما دام لم يصبح صفراً."),
    "jr": ("Relative jump (-128..127), optionally nz / z / nc / c.", "قفز نسبي."),
    "jp": ("Absolute jump, optionally conditional; jp (hl) jumps to HL.", "قفز مطلق."),
    "call": ("Call a subroutine.", "استدعاء روتين فرعي."), "ret": ("Return from a subroutine.", "رجوع."),
    "reti": ("Return from an interrupt.", "رجوع من المقاطعة."), "retn": ("Return from an NMI.", "رجوع من NMI."),
    "rst": ("One-byte call to $00 / $08 / ... / $38 (the Spectrum ROM: rst $10 prints the character in A).",
            "استدعاء سريع (rst $10 في سبكتروم يطبع الحرف الموجود في A)."),
    "push": ("Push a register pair.", "دفع زوج مسجلات."), "pop": ("Pop a register pair.", "سحب زوج مسجلات."),
    "ex": ("Exchange: ex de,hl / ex af,af' / ex (sp),hl.", "تبديل."),
    "exx": ("Swap BC DE HL with the shadow set BC' DE' HL'.", "تبديل المسجلات مع المجموعة الظل."),
    "out": ("Write a port: out (n),a / out (c),r. Spectrum: out ($FE),a sets the border colour (bits 0-2).",
            "الكتابة إلى منفذ؛ في سبكتروم out ($FE),a يغيّر لون الإطار."),
    "in": ("Read a port: in a,(n) / in r,(c). Spectrum keyboard: in a,($FE) with the half-row in A.",
           "القراءة من منفذ (لوحة مفاتيح سبكتروم عبر $FE)."),
    "halt": ("Wait for the next interrupt (50 Hz frame on the Spectrum).", "انتظار المقاطعة التالية."),
    "di": ("Disable interrupts.", "منع المقاطعات."), "ei": ("Enable interrupts.", "تفعيل المقاطعات."),
    "im": ("Interrupt mode 0 / 1 / 2.", "وضع المقاطعة."), "neg": ("A = 0 - A.", "عكس إشارة A."),
    "ldir": ("Copy BC bytes from (HL) to (DE), incrementing - memcpy.", "نسخ كتلة من الذاكرة."),
    "lddr": ("Copy BC bytes from (HL) to (DE), decrementing.", "نسخ كتلة للخلف."),
    "cpir": ("Search A in BC bytes at (HL).", "البحث عن A في كتلة."),
    "bit": ("Test bit n: Z = 1 when it is 0.", "اختبار بت."), "set": ("Set bit n.", "ضبط بت."),
    "res": ("Clear bit n.", "مسح بت."), "nop": ("No operation (4 T-states).", "لا عملية."),
    "daa": ("Decimal adjust A (BCD).", "تصحيح عشري."), "cpl": ("A = NOT A.", "عكس بتات A."),
    "scf": ("Set carry.", "ضبط الحمل."), "ccf": ("Complement carry.", "عكس الحمل."),
    "rlca": ("Rotate A left.", "تدوير A لليسار."), "rrca": ("Rotate A right.", "تدوير A لليمين."),
    "rla": ("Rotate A left through carry.", "تدوير A لليسار عبر الحمل."),
    "rra": ("Rotate A right through carry.", "تدوير A لليمين عبر الحمل."),
}


def _signed(b: int) -> int:
    return b - 256 if b >= 128 else b


def _disp(d: int) -> str:
    return f"+${d:02X}" if d >= 0 else f"-${-d:02X}"


def decode(data: bytes, offset: int, addr: int, undocumented: bool = False) -> Instr | None:
    if offset >= len(data):
        return None
    n = len(data)

    def b(i):
        return data[offset + i] if offset + i < n else None

    def out(size, m, operand="", target=None, kind="", cycles="", undoc=False, width=""):
        if offset + size > n:
            return None
        if undoc and not undocumented:
            return None
        return Instr(addr, size, m, operand, target, kind, undoc, bytes(data[offset:offset + size]), cycles, width)

    op = b(0)
    if op in (0xDD, 0xFD):
        return _indexed(data, offset, addr, "ix" if op == 0xDD else "iy", out, b)
    if op == 0xCB:
        c = b(1)
        if c is None:
            return None
        x, y, z = c >> 6, (c >> 3) & 7, c & 7
        hl = z == 6
        if x == 0:
            return out(2, ROT[y], R[z], cycles="15" if hl else "8", undoc=y == 6)
        return out(2, ("bit", "res", "set")[x - 1], f"{y},{R[z]}",
                   cycles=("12" if x == 1 else "15") if hl else "8")
    if op == 0xED:
        return _ed(b, out)
    return _main(op, b, out, addr, R, "hl", None)


def _main(op, b, out, addr, regs, hl, disp_info):
    """Unprefixed opcode (also with DD / FD: *regs* / *hl* are the indexed names, *disp_info* = (d, size bump))."""
    x, y, z, p, q = op >> 6, (op >> 3) & 7, op & 7, (op >> 4) & 3, (op >> 3) & 1
    rp = ["bc", "de", hl, "sp"]
    rp2 = ["bc", "de", hl, "af"]

    def word(i):
        lo, hi = b(i), b(i + 1)
        return None if lo is None or hi is None else lo | (hi << 8)

    if x == 1:
        if op == 0x76:
            return out(1, "halt", cycles="4")
        return out(1, "ld", f"{regs[y]},{regs[z]}", cycles="7" if 6 in (y, z) else "4")
    if x == 2:
        m = ALU[y].split()[0]
        pre = ALU[y][len(m):].strip()
        return out(1, m, f"{pre}{regs[z]}", cycles="7" if z == 6 else "4")
    if x == 0:
        if z == 0:
            if y == 0:
                return out(1, "nop", cycles="4")
            if y == 1:
                return out(1, "ex", "af,af'", cycles="4")
            d = b(1)
            if d is None:
                return None
            t = (addr + 2 + _signed(d)) & 0xFFFF
            if y == 2:
                return out(2, "djnz", "{t}", t, "branch", "13/8")
            if y == 3:
                return out(2, "jr", "{t}", t, "jump", "12")
            return out(2, "jr", f"{CC[y - 4]},{{t}}", t, "branch", "12/7")
        if z == 1:
            if q == 0:
                w = word(1)
                return None if w is None else out(3, "ld", f"{rp[p]},{{t}}", w, cycles="10", width="imm16")
            return out(1, "add", f"{hl},{rp[p]}", cycles="11")
        if z == 2:
            if p < 2:
                mem = "(bc)" if p == 0 else "(de)"
                return out(1, "ld", f"{mem},a" if q == 0 else f"a,{mem}", cycles="7")
            w = word(1)
            if w is None:
                return None
            if p == 2:
                return out(3, "ld", f"({{t}}),{hl}" if q == 0 else f"{hl},({{t}})", w, cycles="16", width="abs16")
            return out(3, "ld", "({t}),a" if q == 0 else "a,({t})", w, cycles="13", width="abs16")
        if z == 3:
            return out(1, "inc" if q == 0 else "dec", rp[p], cycles="6")
        if z in (4, 5):
            return out(1, "inc" if z == 4 else "dec", regs[y], cycles="11" if y == 6 else "4")
        if z == 6:
            v = b(1)
            return None if v is None else out(2, "ld", f"{regs[y]},${v:02X}", cycles="10" if y == 6 else "7")
        return out(1, ["rlca", "rrca", "rla", "rra", "daa", "cpl", "scf", "ccf"][y], cycles="4")
    # x == 3
    if z == 0:
        return out(1, "ret", CC[y], kind="branchret", cycles="11/5")
    if z == 1:
        if q == 0:
            return out(1, "pop", rp2[p], cycles="10")
        return [out(1, "ret", kind="return", cycles="10"), out(1, "exx", cycles="4"),
                out(1, "jp", f"({hl})", kind="jumpind", cycles="4"), out(1, "ld", f"sp,{hl}", cycles="6")][p]
    if z == 2:
        w = word(1)
        return None if w is None else out(3, "jp", f"{CC[y]},{{t}}", w, "branch", "10", width="abs16")
    if z == 3:
        if y == 0:
            w = word(1)
            return None if w is None else out(3, "jp", "{t}", w, "jump", "10", width="abs16")
        if y == 2:
            v = b(1)
            return None if v is None else out(2, "out", f"(${v:02X}),a", cycles="11")
        if y == 3:
            v = b(1)
            return None if v is None else out(2, "in", f"a,(${v:02X})", cycles="11")
        return [None, None, None, None, out(1, "ex", f"(sp),{hl}", cycles="19"), out(1, "ex", "de,hl", cycles="4"),
                out(1, "di", cycles="4"), out(1, "ei", cycles="4")][y]
    if z == 4:
        w = word(1)
        return None if w is None else out(3, "call", f"{CC[y]},{{t}}", w, "call", "17/10", width="abs16")
    if z == 5:
        if q == 0:
            return out(1, "push", rp2[p], cycles="11")
        if p == 0:
            w = word(1)
            return None if w is None else out(3, "call", "{t}", w, "call", "17", width="abs16")
        return None                       # DD / ED / FD prefixes are handled before
    if z == 6:
        v = b(1)
        if v is None:
            return None
        m = ALU[y].split()[0]
        pre = ALU[y][len(m):].strip()
        return out(2, m, f"{pre}${v:02X}", cycles="7")
    return out(1, "rst", f"${y * 8:02X}", y * 8, "call", "11", width="rst")


def _ed(b, out):
    e = b(1)
    if e is None:
        return None
    x, y, z, p, q = e >> 6, (e >> 3) & 7, e & 7, (e >> 4) & 3, (e >> 3) & 1
    if x == 1:
        if z == 0:
            return out(2, "in", "(c)" if y == 6 else f"{R[y]},(c)", cycles="12", undoc=y == 6)
        if z == 1:
            return out(2, "out", "(c),0" if y == 6 else f"(c),{R[y]}", cycles="12", undoc=y == 6)
        if z == 2:
            return out(2, "sbc" if q == 0 else "adc", f"hl,{RP[p]}", cycles="15")
        if z == 3:
            lo, hi = b(2), b(3)
            if lo is None or hi is None:
                return None
            w = lo | (hi << 8)
            return out(4, "ld", f"({{t}}),{RP[p]}" if q == 0 else f"{RP[p]},({{t}})", w, cycles="20",
                       undoc=p == 2, width="abs16")
        if z == 4:
            return out(2, "neg", cycles="8", undoc=y != 0)
        if z == 5:
            return out(2, "reti" if y == 1 else "retn", kind="return", cycles="14", undoc=y not in (0, 1))
        if z == 6:
            mode = ["0", "0", "1", "2", "0", "0", "1", "2"][y]
            return out(2, "im", mode, cycles="8", undoc=y not in (0, 2, 3))
        if y < 6:
            return out(2, ["ld", "ld", "ld", "ld", "rrd", "rld"][y], ["i,a", "r,a", "a,i", "a,r", "", ""][y],
                       cycles="9" if y < 4 else "18")
        return out(2, "nop", cycles="8", undoc=True)
    if x == 2 and z <= 3 and y >= 4:
        return out(2, BLOCK[(y, z)], cycles="21/16" if y >= 6 else "16")
    return out(2, "nop", cycles="8", undoc=True)


def _indexed(data, offset, addr, ix, out, b):
    op = b(1)
    if op is None:
        return None
    half = {"ix": ("ixh", "ixl"), "iy": ("iyh", "iyl")}[ix]
    if op == 0xCB:                                   # DDCB d op
        d, c = b(2), b(3)
        if d is None or c is None:
            return None
        x, y, z = c >> 6, (c >> 3) & 7, c & 7
        mem = f"({ix}{_disp(_signed(d))})"
        undoc = z != 6 or (x == 0 and y == 6)
        if x == 0:
            return out(4, ROT[y], mem + ("" if z == 6 else f",{R[z]}"), cycles="23", undoc=undoc)
        if x == 1:
            return out(4, "bit", f"{y},{mem}", cycles="20", undoc=z != 6)
        return out(4, ("res", "set")[x - 2], f"{y},{mem}" + ("" if z == 6 else f",{R[z]}"), cycles="23", undoc=undoc)
    if op in (0xDD, 0xFD, 0xED):
        return out(1, "nop", "", undoc=True)        # a prefix that does nothing (db)
    x, y, z = op >> 6, (op >> 3) & 7, op & 7
    uses_mem = (x == 1 and (y == 6 or z == 6) and op != 0x76) or (x == 2 and z == 6) or \
        (x == 0 and z in (4, 5, 6) and y == 6)
    uses_hl = op in (0x21, 0x22, 0x2A, 0x23, 0x2B, 0x09, 0x19, 0x29, 0x39, 0xE1, 0xE5, 0xE3, 0xE9, 0xF9)
    uses_half = not uses_mem and ((x == 1 and op != 0x76 and (y in (4, 5) or z in (4, 5))) or
                                  (x == 2 and z in (4, 5)) or (x == 0 and z in (4, 5, 6) and y in (4, 5)))
    if not (uses_mem or uses_hl or uses_half):
        return out(1, "nop", "", undoc=True)        # prefix ignored: keep it as one data byte
    regs = list(R)
    if uses_mem:
        d = b(2)
        if d is None:
            return None
        regs[6] = f"({ix}{_disp(_signed(d))})"     # ld h,(ix+d) / ld (ix+d),l keep the real H / L
        sub = _main(op, lambda i: b(i + 1) if i == 0 else b(i + 2), _shift(out, 1, 1), addr, regs, ix, (d, 1))
        if sub is None:
            return None
        if x == 0 and z == 6:                       # ld (ix+d),n : opcode, d, n
            v = b(3)
            if v is None:
                return None
            sub = out(4, "ld", f"{regs[6]},${v:02X}", cycles="19")
        return sub
    if uses_half:
        regs[4], regs[5] = half
    sub = _main(op, lambda i: b(i + 1), _shift(out, 1, 0), addr, regs, ix, None)
    if sub is not None and uses_half:
        if not _allow_undoc(out):
            return None
        sub.undocumented = True
    return sub


def _allow_undoc(out) -> bool:
    return out(1, "nop", "", undoc=True) is not None


def _shift(out, prefix: int, disp: int):
    """An ``out`` for a prefixed opcode: sizes grow by the prefix (+ displacement) bytes; the raw bytes start at
    the prefix."""
    def wrapped(size, m, operand="", target=None, kind="", cycles="", undoc=False, width=""):
        cyc = cycles
        if cycles and cycles.split("/")[0].isdigit():
            cyc = "/".join(str(int(c) + (4 if not disp else 12)) for c in cycles.split("/"))
        return out(size + prefix + disp, m, operand, target, kind, cyc, undoc, width)
    return wrapped


def access(ins: Instr) -> str:
    if ins.mnemonic == "ld" and "({t})" in ins.operand:
        return "w" if ins.operand.startswith("(") else "r"
    return ""


def mnemonic_doc(m: str) -> dict:
    m = m.lower()
    en, ar = DOCS.get(m, ("", ""))
    forms = []
    for prefix in (b"", b"\xCB", b"\xED", b"\xDD"):
        for op in range(256):
            ins = decode(prefix + bytes([op, 0x05, 0x00, 0x80]), 0, 0x8000)
            if ins is not None and ins.mnemonic == m and len(forms) < 24 and ins.operand != "":
                forms.append((ins.operand.replace("{t}", "nn"), (prefix[0] << 8 | op) if prefix else op,
                              ins.size, ins.cycles))
            elif ins is not None and ins.mnemonic == m and not forms:
                forms.append(("", op, ins.size, ins.cycles))
    return {"name": m, "en": en, "ar": ar, "modes": forms, "flags": FLAGS.get(m, "-")}
