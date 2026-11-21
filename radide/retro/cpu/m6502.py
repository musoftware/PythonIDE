"""MOS 6502 / 6507 / Ricoh 2A03 instruction set (Atari 2600 / 7800 / 8-bit, NES, Commodore 64).

``OPCODES[byte] = Op(mnemonic, mode, cycles, undocumented)``; ``decode(data, offset, addr)`` -> ``Instr``.
The NMOS undocumented ("illegal") opcodes are in the table too, flagged ``undocumented``; the disassembler only
follows them when asked (``undocumented=True``) and always writes them back as ``.byte`` data with the mnemonic in
a comment, because every assembler spells them differently.
Cycle counts: "+" = one more when a page boundary is crossed, "b" = branch (+1 taken, +2 taken to another page).
"""
from __future__ import annotations

from dataclasses import dataclass

from . import Instr


@dataclass(frozen=True)
class Op:
    mnemonic: str
    mode: str
    cycles: str
    undocumented: bool = False


SIZES = {"imp": 1, "acc": 1, "imm": 2, "zp": 2, "zpx": 2, "zpy": 2, "indx": 2, "indy": 2, "rel": 2,
         "abs": 3, "absx": 3, "absy": 3, "ind": 3}
MODE_NAMES = {"imp": "implied", "acc": "accumulator", "imm": "immediate #n", "zp": "zero page", "zpx": "zero page,X",
              "zpy": "zero page,Y", "indx": "(indirect,X)", "indy": "(indirect),Y", "rel": "relative",
              "abs": "absolute", "absx": "absolute,X", "absy": "absolute,Y", "ind": "(indirect)"}
_MODE_ORDER8 = ("imm", "zp", "zpx", "abs", "absx", "absy", "indx", "indy")

# mnemonic -> {mode: opcode} of the documented instructions
_DOC: dict[str, dict[str, int]] = {
    "adc": dict(zip(_MODE_ORDER8, (0x69, 0x65, 0x75, 0x6D, 0x7D, 0x79, 0x61, 0x71))),
    "and": dict(zip(_MODE_ORDER8, (0x29, 0x25, 0x35, 0x2D, 0x3D, 0x39, 0x21, 0x31))),
    "cmp": dict(zip(_MODE_ORDER8, (0xC9, 0xC5, 0xD5, 0xCD, 0xDD, 0xD9, 0xC1, 0xD1))),
    "eor": dict(zip(_MODE_ORDER8, (0x49, 0x45, 0x55, 0x4D, 0x5D, 0x59, 0x41, 0x51))),
    "lda": dict(zip(_MODE_ORDER8, (0xA9, 0xA5, 0xB5, 0xAD, 0xBD, 0xB9, 0xA1, 0xB1))),
    "ora": dict(zip(_MODE_ORDER8, (0x09, 0x05, 0x15, 0x0D, 0x1D, 0x19, 0x01, 0x11))),
    "sbc": dict(zip(_MODE_ORDER8, (0xE9, 0xE5, 0xF5, 0xED, 0xFD, 0xF9, 0xE1, 0xF1))),
    "sta": {"zp": 0x85, "zpx": 0x95, "abs": 0x8D, "absx": 0x9D, "absy": 0x99, "indx": 0x81, "indy": 0x91},
    "asl": {"acc": 0x0A, "zp": 0x06, "zpx": 0x16, "abs": 0x0E, "absx": 0x1E},
    "lsr": {"acc": 0x4A, "zp": 0x46, "zpx": 0x56, "abs": 0x4E, "absx": 0x5E},
    "rol": {"acc": 0x2A, "zp": 0x26, "zpx": 0x36, "abs": 0x2E, "absx": 0x3E},
    "ror": {"acc": 0x6A, "zp": 0x66, "zpx": 0x76, "abs": 0x6E, "absx": 0x7E},
    "inc": {"zp": 0xE6, "zpx": 0xF6, "abs": 0xEE, "absx": 0xFE},
    "dec": {"zp": 0xC6, "zpx": 0xD6, "abs": 0xCE, "absx": 0xDE},
    "bit": {"zp": 0x24, "abs": 0x2C},
    "cpx": {"imm": 0xE0, "zp": 0xE4, "abs": 0xEC},
    "cpy": {"imm": 0xC0, "zp": 0xC4, "abs": 0xCC},
    "ldx": {"imm": 0xA2, "zp": 0xA6, "zpy": 0xB6, "abs": 0xAE, "absy": 0xBE},
    "ldy": {"imm": 0xA0, "zp": 0xA4, "zpx": 0xB4, "abs": 0xAC, "absx": 0xBC},
    "stx": {"zp": 0x86, "zpy": 0x96, "abs": 0x8E},
    "sty": {"zp": 0x84, "zpx": 0x94, "abs": 0x8C},
    "jmp": {"abs": 0x4C, "ind": 0x6C},
    "jsr": {"abs": 0x20},
    "bpl": {"rel": 0x10}, "bmi": {"rel": 0x30}, "bvc": {"rel": 0x50}, "bvs": {"rel": 0x70},
    "bcc": {"rel": 0x90}, "bcs": {"rel": 0xB0}, "bne": {"rel": 0xD0}, "beq": {"rel": 0xF0},
}
for _m, _o in {"brk": 0x00, "php": 0x08, "clc": 0x18, "plp": 0x28, "sec": 0x38, "rti": 0x40, "pha": 0x48,
               "cli": 0x58, "rts": 0x60, "pla": 0x68, "sei": 0x78, "dey": 0x88, "txa": 0x8A, "tya": 0x98,
               "txs": 0x9A, "tay": 0xA8, "tax": 0xAA, "clv": 0xB8, "tsx": 0xBA, "iny": 0xC8, "dex": 0xCA,
               "cld": 0xD8, "inx": 0xE8, "nop": 0xEA, "sed": 0xF8}.items():
    _DOC[_m] = {"imp": _o}

_RMW7 = ("zp", "zpx", "abs", "absx", "absy", "indx", "indy")
# NMOS undocumented opcodes (names as most assemblers / references use them)
_UNDOC: dict[str, dict[str, int]] = {
    "slo": dict(zip(_RMW7, (0x07, 0x17, 0x0F, 0x1F, 0x1B, 0x03, 0x13))),
    "rla": dict(zip(_RMW7, (0x27, 0x37, 0x2F, 0x3F, 0x3B, 0x23, 0x33))),
    "sre": dict(zip(_RMW7, (0x47, 0x57, 0x4F, 0x5F, 0x5B, 0x43, 0x53))),
    "rra": dict(zip(_RMW7, (0x67, 0x77, 0x6F, 0x7F, 0x7B, 0x63, 0x73))),
    "dcp": dict(zip(_RMW7, (0xC7, 0xD7, 0xCF, 0xDF, 0xDB, 0xC3, 0xD3))),
    "isc": dict(zip(_RMW7, (0xE7, 0xF7, 0xEF, 0xFF, 0xFB, 0xE3, 0xF3))),
    "sax": {"zp": 0x87, "zpy": 0x97, "abs": 0x8F, "indx": 0x83},
    "lax": {"zp": 0xA7, "zpy": 0xB7, "abs": 0xAF, "absy": 0xBF, "indx": 0xA3, "indy": 0xB3},
    "anc": {"imm": 0x0B}, "alr": {"imm": 0x4B}, "arr": {"imm": 0x6B}, "axs": {"imm": 0xCB},
    "xaa": {"imm": 0x8B}, "lxa": {"imm": 0xAB}, "ahx": {"indy": 0x93, "absy": 0x9F}, "shy": {"absx": 0x9C},
    "shx": {"absy": 0x9E}, "tas": {"absy": 0x9B}, "las": {"absy": 0xBB},
}

_READ = {"adc", "and", "cmp", "eor", "lda", "ora", "sbc", "bit", "cpx", "cpy", "ldx", "ldy", "lax", "las", "nop"}
_STORE = {"sta", "stx", "sty", "sax", "ahx", "shx", "shy", "tas"}
_RMW = {"asl", "lsr", "rol", "ror", "inc", "dec", "slo", "rla", "sre", "rra", "dcp", "isc"}
_IMPLIED_CYC = {"brk": "7", "rti": "6", "rts": "6", "pha": "3", "php": "3", "pla": "4", "plp": "4"}


def _cycles(m: str, mode: str) -> str:
    if mode == "rel":
        return "2b"
    if m == "jmp":
        return "3" if mode == "abs" else "5"
    if m == "jsr":
        return "6"
    if mode in ("imp", "acc"):
        return _IMPLIED_CYC.get(m, "2")
    if m in _RMW:
        return {"zp": "5", "zpx": "6", "abs": "6", "absx": "7", "absy": "7", "indx": "8", "indy": "8"}[mode]
    if m in _STORE:
        return {"zp": "3", "zpx": "4", "zpy": "4", "abs": "4", "absx": "5", "absy": "5", "indx": "6",
                "indy": "6"}[mode]
    return {"imm": "2", "zp": "3", "zpx": "4", "zpy": "4", "abs": "4", "absx": "4+", "absy": "4+", "indx": "6",
            "indy": "5+"}[mode]


OPCODES: dict[int, Op] = {}
for _m, _modes in _DOC.items():
    for _mode, _o in _modes.items():
        OPCODES[_o] = Op(_m, _mode, _cycles(_m, _mode))
for _m, _modes in _UNDOC.items():
    for _mode, _o in _modes.items():
        OPCODES[_o] = Op(_m, _mode, _cycles(_m, _mode), True)
OPCODES[0xEB] = Op("sbc", "imm", "2", True)                      # duplicate of $E9
OPCODES[0x2B] = Op("anc", "imm", "2", True)                      # duplicate of $0B
for _o in (0x1A, 0x3A, 0x5A, 0x7A, 0xDA, 0xFA):
    OPCODES[_o] = Op("nop", "imp", "2", True)
for _o in (0x80, 0x82, 0x89, 0xC2, 0xE2):
    OPCODES[_o] = Op("nop", "imm", "2", True)
for _o in (0x04, 0x44, 0x64):
    OPCODES[_o] = Op("nop", "zp", "3", True)
for _o in (0x14, 0x34, 0x54, 0x74, 0xD4, 0xF4):
    OPCODES[_o] = Op("nop", "zpx", "4", True)
OPCODES[0x0C] = Op("nop", "abs", "4", True)
for _o in (0x1C, 0x3C, 0x5C, 0x7C, 0xDC, 0xFC):
    OPCODES[_o] = Op("nop", "absx", "4+", True)
for _o in (0x02, 0x12, 0x22, 0x32, 0x42, 0x52, 0x62, 0x72, 0x92, 0xB2, 0xD2, 0xF2):
    OPCODES[_o] = Op("jam", "imp", "-", True)
assert len(OPCODES) == 256

MNEMONICS = sorted(_DOC)
UNDOC_MNEMONICS = sorted(set(_UNDOC) | {"jam"})

# flags each instruction changes (N V - B D I Z C)
FLAGS: dict[str, str] = {}
for _m in ("adc", "sbc", "rra", "isc"):
    FLAGS[_m] = "N V Z C"
for _m in ("and", "eor", "ora", "lda", "ldx", "ldy", "tax", "tay", "txa", "tya", "tsx", "inx", "iny", "dex", "dey",
           "inc", "dec", "pla", "lax", "las", "xaa", "lxa"):
    FLAGS[_m] = "N Z"
for _m in ("asl", "lsr", "rol", "ror", "cmp", "cpx", "cpy", "slo", "rla", "sre", "dcp", "anc", "alr", "axs"):
    FLAGS[_m] = "N Z C"
FLAGS.update({"bit": "N V Z", "arr": "N V Z C", "clc": "C", "sec": "C", "cld": "D", "sed": "D", "cli": "I",
              "sei": "I", "clv": "V", "plp": "all", "rti": "all", "brk": "B I"})

# Our own short descriptions (English, Arabic).
DOCS: dict[str, tuple[str, str]] = {
    "adc": ("Add memory and carry to A: A = A + M + C. Clear C first (clc) for a plain add; decimal mode (sed) adds BCD.",
            "جمع الذاكرة والحمل إلى A. امسح الحمل أولاً بـ clc."),
    "and": ("A = A AND M (keep only the bits set in both).", "عملية AND بين A والذاكرة."),
    "asl": ("Shift left one bit (multiply by 2); bit 7 goes to C.", "إزاحة لليسار بتاً واحداً (ضرب في 2)."),
    "bcc": ("Branch if carry clear (C = 0) - 'below' after cmp.", "قفز إذا كان الحمل صفراً."),
    "bcs": ("Branch if carry set (C = 1) - 'greater or equal' after cmp.", "قفز إذا كان الحمل واحداً."),
    "beq": ("Branch if equal / result zero (Z = 1).", "قفز عند التساوي (Z = 1)."),
    "bit": ("Test bits: Z = (A AND M) == 0, N = bit 7 of M, V = bit 6 of M. A is unchanged. Often used to read "
            "hardware flags (e.g. the TIA collision latches).", "اختبار البتات دون تغيير A."),
    "bmi": ("Branch if minus (N = 1).", "قفز إذا كانت النتيجة سالبة."),
    "bne": ("Branch if not equal / result not zero (Z = 0).", "قفز عند عدم التساوي."),
    "bpl": ("Branch if plus (N = 0).", "قفز إذا كانت النتيجة موجبة."),
    "brk": ("Software interrupt: push PC+2 and P, jump through the IRQ/BRK vector at $FFFE.",
            "مقاطعة برمجية عبر المتجه $FFFE."),
    "bvc": ("Branch if overflow clear (V = 0).", "قفز إذا لم يحدث فيضان."),
    "bvs": ("Branch if overflow set (V = 1).", "قفز إذا حدث فيضان."),
    "clc": ("Clear carry (C = 0) - do it before adc.", "مسح علم الحمل."),
    "cld": ("Clear decimal mode (binary arithmetic). The 2A03 of the NES has no decimal mode.",
            "إلغاء الوضع العشري."),
    "cli": ("Clear interrupt disable: IRQs are allowed.", "السماح بالمقاطعات."),
    "clv": ("Clear overflow (V = 0).", "مسح علم الفيضان."),
    "cmp": ("Compare A with M: sets N Z C as for A - M (C = 1 when A >= M unsigned).", "مقارنة A بالذاكرة."),
    "cpx": ("Compare X with M.", "مقارنة X بالذاكرة."),
    "cpy": ("Compare Y with M.", "مقارنة Y بالذاكرة."),
    "dec": ("Decrement memory by one.", "إنقاص الذاكرة بمقدار 1."),
    "dex": ("X = X - 1.", "إنقاص X."),
    "dey": ("Y = Y - 1.", "إنقاص Y."),
    "eor": ("A = A XOR M (flip the bits set in M).", "عملية XOR بين A والذاكرة."),
    "inc": ("Increment memory by one.", "زيادة الذاكرة بمقدار 1."),
    "inx": ("X = X + 1.", "زيادة X."),
    "iny": ("Y = Y + 1.", "زيادة Y."),
    "jmp": ("Jump. jmp ($xxxx) reads the target from memory (NMOS bug: the high byte wraps inside the page).",
            "قفز غير مشروط."),
    "jsr": ("Call a subroutine: push the return address - 1, jump. Return with rts.", "استدعاء روتين فرعي."),
    "lda": ("Load A from memory.", "تحميل A من الذاكرة."),
    "ldx": ("Load X from memory.", "تحميل X من الذاكرة."),
    "ldy": ("Load Y from memory.", "تحميل Y من الذاكرة."),
    "lsr": ("Logical shift right (unsigned divide by 2); bit 0 goes to C.", "إزاحة منطقية لليمين."),
    "nop": ("No operation (2 cycles) - also used to burn time in display kernels.", "لا عملية."),
    "ora": ("A = A OR M (set bits).", "عملية OR بين A والذاكرة."),
    "pha": ("Push A on the stack (page 1).", "دفع A إلى المكدس."),
    "php": ("Push the status register P on the stack.", "دفع مسجل الحالة إلى المكدس."),
    "pla": ("Pull A from the stack.", "سحب A من المكدس."),
    "plp": ("Pull P from the stack.", "سحب مسجل الحالة من المكدس."),
    "rol": ("Rotate left through carry.", "تدوير لليسار عبر الحمل."),
    "ror": ("Rotate right through carry.", "تدوير لليمين عبر الحمل."),
    "rti": ("Return from interrupt: pull P, then PC.", "رجوع من المقاطعة."),
    "rts": ("Return from subroutine.", "رجوع من الروتين الفرعي."),
    "sbc": ("Subtract with borrow: A = A - M - (1 - C). Set C first (sec) for a plain subtract.",
            "طرح مع الاستلاف. اضبط الحمل أولاً بـ sec."),
    "sec": ("Set carry (C = 1) - do it before sbc.", "ضبط علم الحمل."),
    "sed": ("Set decimal mode (BCD arithmetic for adc / sbc).", "تفعيل الوضع العشري."),
    "sei": ("Set interrupt disable: IRQs are ignored (first instruction of most reset routines).",
            "منع المقاطعات."),
    "sta": ("Store A into memory (writing a hardware register does something: TIA, PPU, VIC ...).",
            "تخزين A في الذاكرة."),
    "stx": ("Store X into memory.", "تخزين X في الذاكرة."),
    "sty": ("Store Y into memory.", "تخزين Y في الذاكرة."),
    "tax": ("X = A.", "نسخ A إلى X."), "tay": ("Y = A.", "نسخ A إلى Y."),
    "tsx": ("X = stack pointer S.", "نسخ مؤشر المكدس إلى X."), "txa": ("A = X.", "نسخ X إلى A."),
    "txs": ("Stack pointer S = X (ldx #$FF / txs sets up the stack).", "نسخ X إلى مؤشر المكدس."),
    "tya": ("A = Y.", "نسخ Y إلى A."),
    "slo": ("Undocumented: ASL memory, then ORA it into A.", "تعليمة غير موثقة: ASL ثم ORA."),
    "rla": ("Undocumented: ROL memory, then AND it into A.", "تعليمة غير موثقة: ROL ثم AND."),
    "sre": ("Undocumented: LSR memory, then EOR it into A.", "تعليمة غير موثقة: LSR ثم EOR."),
    "rra": ("Undocumented: ROR memory, then ADC it to A.", "تعليمة غير موثقة: ROR ثم ADC."),
    "sax": ("Undocumented: store A AND X.", "تعليمة غير موثقة: تخزين A AND X."),
    "lax": ("Undocumented: load A and X with the same value.", "تعليمة غير موثقة: تحميل A و X معاً."),
    "dcp": ("Undocumented: DEC memory, then CMP it with A.", "تعليمة غير موثقة: DEC ثم CMP."),
    "isc": ("Undocumented: INC memory, then SBC it from A.", "تعليمة غير موثقة: INC ثم SBC."),
    "anc": ("Undocumented: AND #n, C = bit 7.", "تعليمة غير موثقة."),
    "alr": ("Undocumented: AND #n then LSR A.", "تعليمة غير موثقة."),
    "arr": ("Undocumented: AND #n then ROR A (odd flags).", "تعليمة غير موثقة."),
    "axs": ("Undocumented: X = (A AND X) - #n.", "تعليمة غير موثقة."),
    "jam": ("Undocumented: halts the CPU (only a reset recovers).", "تعليمة غير موثقة توقف المعالج."),
}

_BRANCH = {"bpl", "bmi", "bvc", "bvs", "bcc", "bcs", "bne", "beq"}


def operand_text(mode: str, value: str) -> str:
    """Assembler operand for *mode* with *value* already formatted (label or $hex)."""
    return {"imp": "", "acc": "", "imm": f"#{value}", "zp": value, "abs": value, "rel": value,
            "zpx": f"{value},x", "absx": f"{value},x", "zpy": f"{value},y", "absy": f"{value},y",
            "indx": f"({value},x)", "indy": f"({value}),y", "ind": f"({value})"}[mode]


def decode(data: bytes, offset: int, addr: int, undocumented: bool = False) -> Instr | None:
    """The instruction at data[offset] (CPU address *addr*), or None (undocumented when not allowed, or cut)."""
    if offset >= len(data):
        return None
    op = OPCODES[data[offset]]
    if op.undocumented and not undocumented:
        return None
    size = SIZES[op.mode]
    if offset + size > len(data):
        return None
    raw = bytes(data[offset:offset + size])
    target = None
    width = ""
    if size == 2:
        b = raw[1]
        if op.mode == "rel":
            target = (addr + 2 + (b - 256 if b >= 128 else b)) & 0xFFFF
        elif op.mode != "imm":
            target = b
            width = "zp"
    elif size == 3:
        target = raw[1] | (raw[2] << 8)
        width = "abs16"
    if op.mnemonic == "jmp":
        kind = "jump" if op.mode == "abs" else "jumpind"
    elif op.mnemonic == "jsr":
        kind = "call"
    elif op.mnemonic in ("rts", "rti"):
        kind = "return"
    elif op.mnemonic in ("brk", "jam"):
        kind = "stop"
    elif op.mnemonic in _BRANCH:
        kind = "branch"
    else:
        kind = ""
    ins = Instr(addr, size, op.mnemonic, operand_text(op.mode, "{t}") if (target is not None) else
                (f"#${raw[1]:02X}" if op.mode == "imm" else ""), target, kind, op.undocumented, raw, op.cycles,
                width, op.mode)
    return ins


def access(ins: Instr) -> str:
    """How the instruction uses its memory operand: "r" read, "w" write, "rw", or "" (jump / immediate)."""
    m = ins.mnemonic
    if ins.kind or ins.mode in ("imm", "imp", "acc"):
        return ""
    if m in _STORE:
        return "w"
    if m in _RMW:
        return "rw"
    return "r"


def mnemonic_doc(m: str) -> dict:
    """Hover / completion data of a mnemonic: description, modes (opcode, bytes, cycles), flags."""
    m = m.lower()
    modes = []
    for o, op in sorted(OPCODES.items()):
        if op.mnemonic == m and (not op.undocumented or m in _UNDOC or m == "jam"):
            modes.append((op.mode, o, SIZES[op.mode], op.cycles, op.undocumented))
    en, ar = DOCS.get(m, ("", ""))
    return {"name": m, "en": en, "ar": ar, "modes": modes, "flags": FLAGS.get(m, "-")}
