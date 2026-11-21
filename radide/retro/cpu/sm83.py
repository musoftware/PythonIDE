"""Sharp SM83 instruction set (Game Boy / Game Boy Color), RGBDS syntax.

``decode(data, offset, addr)`` -> ``Instr`` (operands use ``{t}`` where a label goes). Cycle counts are in
T-states (4 per machine cycle); "a/b" = taken / not taken. The eleven unused opcodes (D3 DB DD E3 E4 EB EC ED F4 FC
FD) decode as None, so the disassembler keeps them as data.
"""
from __future__ import annotations

from . import Instr

R = ["b", "c", "d", "e", "h", "l", "[hl]", "a"]
RP = ["bc", "de", "hl", "sp"]
RP2 = ["bc", "de", "hl", "af"]
CC = ["nz", "z", "nc", "c"]
ALU = ["add a,", "adc a,", "sub a,", "sbc a,", "and a,", "xor a,", "or a,", "cp a,"]
ROT = ["rlc", "rrc", "rl", "rr", "sla", "sra", "swap", "srl"]
INVALID = {0xD3, 0xDB, 0xDD, 0xE3, 0xE4, 0xEB, 0xEC, 0xED, 0xF4, 0xFC, 0xFD}

MNEMONICS = sorted({"nop", "ld", "ldh", "inc", "dec", "add", "adc", "sub", "sbc", "and", "xor", "or", "cp", "rlca",
                    "rrca", "rla", "rra", "daa", "cpl", "scf", "ccf", "halt", "stop", "jr", "jp", "call", "ret",
                    "reti", "rst", "push", "pop", "di", "ei", "rlc", "rrc", "rl", "rr", "sla", "sra", "swap", "srl",
                    "bit", "res", "set"})
REGISTERS = ["a", "b", "c", "d", "e", "h", "l", "af", "bc", "de", "hl", "sp", "hli", "hld"]
CONDITIONS = CC

FLAGS = {"add": "Z 0 H C", "adc": "Z 0 H C", "sub": "Z 1 H C", "sbc": "Z 1 H C", "cp": "Z 1 H C", "and": "Z 0 1 0",
         "or": "Z 0 0 0", "xor": "Z 0 0 0", "inc": "Z 0 H -", "dec": "Z 1 H -", "daa": "Z - 0 C", "cpl": "- 1 1 -",
         "scf": "- 0 0 1", "ccf": "- 0 0 C", "rlca": "0 0 0 C", "rrca": "0 0 0 C", "rla": "0 0 0 C",
         "rra": "0 0 0 C", "rlc": "Z 0 0 C", "rrc": "Z 0 0 C", "rl": "Z 0 0 C", "rr": "Z 0 0 C",
         "sla": "Z 0 0 C", "sra": "Z 0 0 C", "srl": "Z 0 0 C", "swap": "Z 0 0 0", "bit": "Z 0 1 -",
         "pop": "(pop af: all)"}

DOCS: dict[str, tuple[str, str]] = {
    "nop": ("No operation (4 cycles).", "لا عملية."),
    "ld": ("Load: ld dest, src. [hl+] / [hl-] also move HL; ld [n16], a / ld a, [n16] read or write memory.",
           "تحميل: نسخ المصدر إلى الوجهة."),
    "ldh": ("Load from / to the high page $FF00-$FFFF (I/O registers and HRAM) in 2 bytes: ldh [rLCDC], a.",
            "تحميل من أو إلى الصفحة العليا $FF00 (مسجلات الإدخال والإخراج)."),
    "inc": ("Increment by one (16-bit inc does not touch the flags).", "زيادة بمقدار 1."),
    "dec": ("Decrement by one.", "إنقاص بمقدار 1."),
    "add": ("Add to A (or HL / SP for 16-bit adds).", "جمع."),
    "adc": ("Add with carry.", "جمع مع الحمل."),
    "sub": ("Subtract from A.", "طرح من A."),
    "sbc": ("Subtract with carry (borrow).", "طرح مع الاستلاف."),
    "and": ("A = A AND value.", "عملية AND."), "xor": ("A = A XOR value; xor a clears A.", "عملية XOR؛ xor a تصفّر A."),
    "or": ("A = A OR value.", "عملية OR."),
    "cp": ("Compare A with value (sets the flags of A - value).", "مقارنة A بقيمة."),
    "rlca": ("Rotate A left, bit 7 to carry.", "تدوير A لليسار."), "rrca": ("Rotate A right.", "تدوير A لليمين."),
    "rla": ("Rotate A left through carry.", "تدوير A لليسار عبر الحمل."),
    "rra": ("Rotate A right through carry.", "تدوير A لليمين عبر الحمل."),
    "daa": ("Decimal adjust A after a BCD add / subtract (scores!).", "تصحيح عشري لـ A."),
    "cpl": ("A = NOT A.", "عكس بتات A."), "scf": ("Set carry.", "ضبط الحمل."), "ccf": ("Complement carry.", "عكس الحمل."),
    "halt": ("Stop the CPU until an interrupt (saves battery; the usual 'wait for VBlank').",
             "إيقاف المعالج حتى حدوث مقاطعة."),
    "stop": ("Very low power mode (also switches the CGB speed). Assembled as $10 $00.", "وضع طاقة منخفض جداً."),
    "jr": ("Relative jump (-128..127 bytes), optionally conditional.", "قفز نسبي قصير."),
    "jp": ("Absolute jump (jp hl jumps to HL).", "قفز مطلق."),
    "call": ("Call a subroutine (push the return address).", "استدعاء روتين فرعي."),
    "ret": ("Return from a subroutine (optionally conditional).", "رجوع من الروتين."),
    "reti": ("Return and enable interrupts (end of an interrupt handler).", "رجوع من المقاطعة مع تفعيلها."),
    "rst": ("One-byte call to $00 / $08 / ... / $38.", "استدعاء سريع من بايت واحد."),
    "push": ("Push a register pair.", "دفع زوج مسجلات."), "pop": ("Pop a register pair.", "سحب زوج مسجلات."),
    "di": ("Disable interrupts.", "منع المقاطعات."), "ei": ("Enable interrupts (after the next instruction).", "تفعيل المقاطعات."),
    "rlc": ("Rotate left.", "تدوير لليسار."), "rrc": ("Rotate right.", "تدوير لليمين."),
    "rl": ("Rotate left through carry.", "تدوير لليسار عبر الحمل."),
    "rr": ("Rotate right through carry.", "تدوير لليمين عبر الحمل."),
    "sla": ("Shift left arithmetic.", "إزاحة حسابية لليسار."), "sra": ("Shift right arithmetic (keeps bit 7).", "إزاحة حسابية لليمين."),
    "swap": ("Swap the two nibbles.", "تبديل نصفي البايت."), "srl": ("Shift right logical.", "إزاحة منطقية لليمين."),
    "bit": ("Test bit n: Z = 1 when it is 0.", "اختبار بت."), "res": ("Clear bit n.", "مسح بت."),
    "set": ("Set bit n.", "ضبط بت."),
}


def _cb(op: int) -> tuple[str, str, str]:
    x, y, z = op >> 6, (op >> 3) & 7, op & 7
    hl = z == 6
    if x == 0:
        return ROT[y], R[z], "16" if hl else "8"
    name = ("bit", "res", "set")[x - 1]
    return name, f"{y}, {R[z]}", ("12" if x == 1 else "16") if hl else "8"


def decode(data: bytes, offset: int, addr: int, undocumented: bool = False) -> Instr | None:
    if offset >= len(data):
        return None
    op = data[offset]
    if op in INVALID:
        return None

    def byte(i):
        return data[offset + i] if offset + i < len(data) else None

    def word():
        lo, hi = byte(1), byte(2)
        return None if lo is None or hi is None else lo | (hi << 8)

    x, y, z, p, q = op >> 6, (op >> 3) & 7, op & 7, (op >> 4) & 3, (op >> 3) & 1

    def mk(size, m, operand="", target=None, kind="", cycles="4", width=""):
        if offset + size > len(data):
            return None
        return Instr(addr, size, m, operand, target, kind, False, bytes(data[offset:offset + size]), cycles, width)

    def rel():
        d = byte(1)
        if d is None:
            return None
        return (addr + 2 + (d - 256 if d >= 128 else d)) & 0xFFFF

    if op == 0xCB:
        b = byte(1)
        if b is None:
            return None
        m, operand, cyc = _cb(b)
        return mk(2, m, operand, cycles=cyc)
    if x == 1:
        if op == 0x76:
            return mk(1, "halt")
        return mk(1, "ld", f"{R[y]}, {R[z]}", cycles="8" if 6 in (y, z) else "4")
    if x == 2:
        m = ALU[y].split()[0]
        pre = ALU[y][len(m):].strip()
        return mk(1, m, f"{pre} {R[z]}".strip(), cycles="8" if z == 6 else "4")
    if x == 0:
        if z == 0:
            if y == 0:
                return mk(1, "nop")
            if y == 1:
                w = word()
                return None if w is None else mk(3, "ld", "[{t}], sp", w, cycles="20", width="abs16")
            if y == 2:
                return mk(2, "stop", cycles="4") if byte(1) == 0x00 else None
            t = rel()
            if t is None:
                return None
            if y == 3:
                return mk(2, "jr", "{t}", t, "jump", "12")
            return mk(2, "jr", f"{CC[y - 4]}, {{t}}", t, "branch", "12/8")
        if z == 1:
            if q == 0:
                w = word()
                return None if w is None else mk(3, "ld", f"{RP[p]}, {{t}}", w, cycles="12", width="imm16")
            return mk(1, "add", f"hl, {RP[p]}", cycles="8")
        if z == 2:
            mem = ["[bc]", "[de]", "[hl+]", "[hl-]"][p]
            return mk(1, "ld", f"{mem}, a" if q == 0 else f"a, {mem}", cycles="8")
        if z == 3:
            return mk(1, "inc" if q == 0 else "dec", RP[p], cycles="8")
        if z in (4, 5):
            return mk(1, "inc" if z == 4 else "dec", R[y], cycles="12" if y == 6 else "4")
        if z == 6:
            n = byte(1)
            return None if n is None else mk(2, "ld", f"{R[y]}, ${n:02X}", cycles="12" if y == 6 else "8")
        return mk(1, ["rlca", "rrca", "rla", "rra", "daa", "cpl", "scf", "ccf"][y])
    # x == 3
    if z == 0:
        if y < 4:
            return mk(1, "ret", CC[y], kind="branchret", cycles="20/8")
        n = byte(1)
        if n is None:
            return None
        if y == 4:
            return mk(2, "ldh", "[{t}], a", 0xFF00 | n, cycles="12", width="hram")
        if y == 6:
            return mk(2, "ldh", "a, [{t}]", 0xFF00 | n, cycles="12", width="hram")
        s = f"${n:02X}" if n < 128 else f"-${256 - n:02X}"
        if y == 5:
            return mk(2, "add", f"sp, {s}", cycles="16")
        return mk(2, "ld", f"hl, sp + {s}" if n < 128 else f"hl, sp - ${256 - n:02X}", cycles="12")
    if z == 1:
        if q == 0:
            return mk(1, "pop", RP2[p], cycles="12")
        return [mk(1, "ret", kind="return", cycles="16"), mk(1, "reti", kind="return", cycles="16"),
                mk(1, "jp", "hl", kind="jumpind"), mk(1, "ld", "sp, hl", cycles="8")][p]
    if z == 2:
        if y < 4:
            w = word()
            return None if w is None else mk(3, "jp", f"{CC[y]}, {{t}}", w, "branch", "16/12", "abs16")
        if y in (4, 6):
            return mk(1, "ldh", "[c], a" if y == 4 else "a, [c]", cycles="8")
        w = word()
        if w is None:
            return None
        return mk(3, "ld", "[{t}], a" if y == 5 else "a, [{t}]", w, cycles="16", width="abs16")
    if z == 3:
        if y == 0:
            w = word()
            return None if w is None else mk(3, "jp", "{t}", w, "jump", "16", "abs16")
        return mk(1, "di" if y == 6 else "ei")
    if z == 4:
        w = word()
        return None if w is None else mk(3, "call", f"{CC[y]}, {{t}}", w, "call", "24/12", "abs16")
    if z == 5:
        if q == 0:
            return mk(1, "push", RP2[p], cycles="16")
        w = word()
        return None if w is None else mk(3, "call", "{t}", w, "call", "24", "abs16")
    if z == 6:
        n = byte(1)
        if n is None:
            return None
        m = ALU[y].split()[0]
        pre = ALU[y][len(m):].strip()
        return mk(2, m, f"{pre} ${n:02X}".strip(), cycles="8")
    return mk(1, "rst", f"${y * 8:02X}", y * 8, "call", "16", "rst")


def access(ins: Instr) -> str:
    """"r" / "w" for ld / ldh with a memory operand, else ""."""
    if ins.mnemonic in ("ld", "ldh") and "[{t}]" in ins.operand:
        return "w" if ins.operand.startswith("[") else "r"
    return ""


def mnemonic_doc(m: str) -> dict:
    m = m.lower()
    en, ar = DOCS.get(m, ("", ""))
    forms = []
    for op in range(256):
        if op == 0xCB:
            continue
        ins = decode(bytes([op, 0x00, 0xC0]), 0, 0xC000)
        if ins is not None and ins.mnemonic == m:
            forms.append((ins.operand.replace("{t}", "n16" if ins.size == 3 else "n8"), op, ins.size, ins.cycles))
    if not forms:
        for op in range(256):
            ins = decode(bytes([0xCB, op]), 0, 0)
            if ins is not None and ins.mnemonic == m:
                forms.append((ins.operand, 0xCB00 | op, 2, ins.cycles))
    return {"name": m, "en": en, "ar": ar, "modes": forms[:24], "flags": FLAGS.get(m, "-")}
