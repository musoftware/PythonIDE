"""Plain-words explanations of x86 instructions with their concrete effect (English + Arabic).

``explain_step(ins_text, before, after, ...)`` turns one executed instruction (the registers before and after,
the memory it read / wrote) into:

* ``what``     - what the instruction does, in words, with its operands ("Add EBX to EAX: EAX = EAX + EBX");
* ``changes``  - every register / memory location that changed, before -> after (hex and decimal);
* ``flags``    - every status flag the instruction sets, with the reason ("ZF=0 because the result 12 is not
  zero", "CF=1 because 5 < 7 as unsigned numbers: the subtraction needed a borrow");
* ``jump``     - for a conditional jump / SETcc / CMOVcc (or the next one after a CMP / TEST): whether it is
  taken and why, in terms of the compared values ("jle .done is NOT taken: RCX = 5 is greater than 0").

``condition_text(mnemonic, eflags)`` and ``flag_table(eflags)`` are reused by the runner (endless loops) and
the What-if console. Texts are original; the reference link of every instruction comes from radide/asm_intel.
"""
from __future__ import annotations

import re

CF, PF, AF, ZF, SF, TF, IF, DF, OF = 0x1, 0x4, 0x10, 0x40, 0x80, 0x100, 0x200, 0x400, 0x800
FLAG_BITS = {"CF": CF, "PF": PF, "AF": AF, "ZF": ZF, "SF": SF, "DF": DF, "OF": OF}

FLAG_INFO = {
    "CF": ("Carry flag: 1 when an unsigned result did not fit (carry out of the top bit, or a borrow).",
           "علم الحمل: يصبح 1 عندما لا يتسع الناتج بدون إشارة (حمل خارج أعلى بت، أو استلاف في الطرح)."),
    "ZF": ("Zero flag: 1 when the result is zero (after CMP: the two values are equal).",
           "علم الصفر: يصبح 1 عندما يكون الناتج صفراً (بعد CMP: القيمتان متساويتان)."),
    "SF": ("Sign flag: a copy of the top bit of the result (1 = negative as a signed number).",
           "علم الإشارة: نسخة من أعلى بت في الناتج (1 = سالب إذا اعتبرنا الرقم بإشارة)."),
    "OF": ("Overflow flag: 1 when a signed result did not fit (e.g. two positives gave a negative).",
           "علم الفيضان: يصبح 1 عندما لا يتسع الناتج بإشارة (مثلاً جمع موجبين أعطى سالباً)."),
    "PF": ("Parity flag: 1 when the lowest byte of the result has an even number of 1 bits.",
           "علم التكافؤ: يصبح 1 عندما يحتوي أدنى بايت في الناتج على عدد زوجي من البتات 1."),
    "AF": ("Auxiliary carry: carry out of bit 3 (used only by BCD instructions).",
           "علم الحمل المساعد: حمل خارج البت 3 (تستخدمه تعليمات BCD فقط)."),
    "DF": ("Direction flag: 0 = string instructions go forward (CLD), 1 = backward (STD).",
           "علم الاتجاه: 0 = تعليمات النصوص تتقدم للأمام (CLD)، 1 = للخلف (STD)."),
}

# condition suffix -> (test(flags dict) , symbol, signed?, en meaning, ar meaning, flags text)
_COND = {
    "e": (lambda f: f["ZF"], "==", None, "equal / zero", "يساوي / صفر", "ZF=1"),
    "ne": (lambda f: not f["ZF"], "!=", None, "not equal / not zero", "لا يساوي / ليس صفراً", "ZF=0"),
    "l": (lambda f: f["SF"] != f["OF"], "<", True, "less (signed)", "أصغر (بإشارة)", "SF≠OF"),
    "le": (lambda f: f["ZF"] or f["SF"] != f["OF"], "<=", True, "less or equal (signed)", "أصغر أو يساوي (بإشارة)",
           "ZF=1 or SF≠OF"),
    "g": (lambda f: not f["ZF"] and f["SF"] == f["OF"], ">", True, "greater (signed)", "أكبر (بإشارة)",
          "ZF=0 and SF=OF"),
    "ge": (lambda f: f["SF"] == f["OF"], ">=", True, "greater or equal (signed)", "أكبر أو يساوي (بإشارة)", "SF=OF"),
    "b": (lambda f: f["CF"], "<", False, "below (unsigned)", "أقل (بدون إشارة)", "CF=1"),
    "be": (lambda f: f["CF"] or f["ZF"], "<=", False, "below or equal (unsigned)", "أقل أو يساوي (بدون إشارة)",
           "CF=1 or ZF=1"),
    "a": (lambda f: not f["CF"] and not f["ZF"], ">", False, "above (unsigned)", "أعلى (بدون إشارة)",
          "CF=0 and ZF=0"),
    "ae": (lambda f: not f["CF"], ">=", False, "above or equal (unsigned)", "أعلى أو يساوي (بدون إشارة)", "CF=0"),
    "s": (lambda f: f["SF"], None, None, "negative (sign set)", "سالب (علم الإشارة 1)", "SF=1"),
    "ns": (lambda f: not f["SF"], None, None, "not negative", "ليس سالباً", "SF=0"),
    "o": (lambda f: f["OF"], None, None, "overflow", "فيضان", "OF=1"),
    "no": (lambda f: not f["OF"], None, None, "no overflow", "لا فيضان", "OF=0"),
    "p": (lambda f: f["PF"], None, None, "parity even", "تكافؤ زوجي", "PF=1"),
    "np": (lambda f: not f["PF"], None, None, "parity odd", "تكافؤ فردي", "PF=0"),
}
_ALIAS = {"z": "e", "nz": "ne", "nge": "l", "ng": "le", "nle": "g", "nl": "ge", "c": "b", "nae": "b", "na": "be",
          "nbe": "a", "nb": "ae", "nc": "ae", "pe": "p", "po": "np"}

SIZE_OF = {}
for _n in ("rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "rip"):
    SIZE_OF[_n] = 64
for _n in range(8, 16):
    SIZE_OF[f"r{_n}"] = 64
    SIZE_OF[f"r{_n}d"] = 32
    SIZE_OF[f"r{_n}w"] = 16
    SIZE_OF[f"r{_n}b"] = 8
for _n in ("eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp", "eip"):
    SIZE_OF[_n] = 32
for _n in ("ax", "bx", "cx", "dx", "si", "di", "bp", "sp", "ip"):
    SIZE_OF[_n] = 16
for _n in ("al", "bl", "cl", "dl", "ah", "bh", "ch", "dh", "sil", "dil", "bpl", "spl"):
    SIZE_OF[_n] = 8


def _family(reg: str) -> str:
    from .x86run import family
    return family(reg)


def cond_suffix(mn: str) -> str | None:
    mn = mn.lower()
    for pre in ("cmov", "set", "j"):
        if mn.startswith(pre) and mn not in ("jmp", "jcxz", "jecxz", "jrcxz"):
            suf = mn[len(pre):]
            suf = _ALIAS.get(suf, suf)
            if suf in _COND:
                return suf
    return None


def flags_of(eflags: int) -> dict:
    return {k: bool(eflags & v) for k, v in FLAG_BITS.items()}


def condition_text(mn: str, eflags: int) -> dict | None:
    """{"taken": bool, "en": "...", "ar": "..."} for a Jcc / SETcc / CMOVcc with these flags."""
    suf = cond_suffix(mn)
    if suf is None:
        return None
    test, _sym, _signed, en_m, ar_m, ftext = _COND[suf]
    f = flags_of(eflags)
    taken = bool(test(f))
    shown = " ".join(f"{k}={int(f[k])}" for k in ("ZF", "SF", "OF", "CF") if k in ftext or
                     (k in ("SF", "OF") and "SF" in ftext))
    if taken:
        return {"taken": True, "en": f"the condition '{en_m}' ({ftext}) holds: {shown}",
                "ar": f"الشرط '{ar_m}' ({ftext}) متحقق: {shown}"}
    return {"taken": False, "en": f"the condition '{en_m}' ({ftext}) does not hold: {shown}",
            "ar": f"الشرط '{ar_m}' ({ftext}) غير متحقق: {shown}"}


def flag_table(eflags: int) -> list[tuple[str, int, str, str]]:
    """[(flag, value, english meaning, arabic meaning)] of the status flags."""
    return [(k, int(bool(eflags & FLAG_BITS[k])), FLAG_INFO[k][0], FLAG_INFO[k][1])
            for k in ("CF", "ZF", "SF", "OF", "PF", "AF", "DF")]


# ============================================================================ operands
def split_instruction(text: str) -> tuple[str, list[str]]:
    """'rep movsb' / 'add eax, [ebx+4]' -> (mnemonic, operands). Comments and labels are removed."""
    s = re.split(r"\s;|^;", text, maxsplit=1)[0].strip()
    s = re.sub(r"^[A-Za-z_.?$@][\w.?$@]*:\s*", "", s)
    m = re.match(r"^((?:rep[a-z]*|lock)\s+)?([A-Za-z][\w.]*)\s*(.*)$", s)
    if not m:
        return "", []
    prefix = (m.group(1) or "").strip().lower()
    mn = m.group(2).lower()
    ops, depth, cur = [], 0, ""
    for ch in m.group(3):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "," and depth == 0:
            ops.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        ops.append(cur.strip())
    return (prefix + " " + mn).strip() if prefix else mn, ops


def _is_reg(op: str) -> bool:
    return op.lower() in SIZE_OF


def _imm(op: str) -> int | None:
    t = op.strip().lower()
    t = re.sub(r"^(byte|word|dword|qword)\s+", "", t)
    try:
        if re.fullmatch(r"[-+]?0x[0-9a-f]+", t):
            return int(t, 16)
        if re.fullmatch(r"[-+]?[0-9][0-9a-f]*h", t):
            return int(t[:-1], 16)
        if re.fullmatch(r"[-+]?[01]+b", t):
            return int(t[:-1], 2)
        if re.fullmatch(r"[-+]?\d+", t):
            return int(t)
        if re.fullmatch(r"'.'", op.strip()):
            return ord(op.strip()[1])
    except ValueError:
        return None
    return None


def _mask(bits: int) -> int:
    return (1 << bits) - 1


def _signed(v: int, bits: int) -> int:
    v &= _mask(bits)
    return v - (1 << bits) if v >> (bits - 1) else v


def _reg_value(regs: dict, name: str) -> int | None:
    if not regs:
        return None
    n = name.lower()
    if n in regs:
        return regs[n]
    fam = _family(n)
    base = regs.get(fam)
    if base is None:
        # 32-bit snapshots: eax for ax / al
        alt = {"rax": "eax", "rbx": "ebx", "rcx": "ecx", "rdx": "edx", "rsi": "esi", "rdi": "edi", "rbp": "ebp",
               "rsp": "esp"}.get(fam)
        base = regs.get(alt) if alt else None
        if base is None:
            alt16 = {"rax": "ax", "rbx": "bx", "rcx": "cx", "rdx": "dx", "rsi": "si", "rdi": "di", "rbp": "bp",
                     "rsp": "sp"}.get(fam)
            base = regs.get(alt16) if alt16 else None
        if base is None:
            return None
    if n in ("ah", "bh", "ch", "dh"):
        return (base >> 8) & 0xFF
    return base & _mask(SIZE_OF.get(n, 64))


def _fmt(v: int | None, bits: int = 32) -> str:
    if v is None:
        return "?"
    v &= _mask(bits)
    s = _signed(v, bits)
    if v < 10:
        return str(v)
    if s < 0:
        return f"{v:#x} ({v} / {s})"
    return f"{v:#x} ({v})"


def _op_size(ops: list[str], bits_default: int) -> int:
    for o in ops:
        if _is_reg(o):
            return SIZE_OF[o.lower()]
    for o in ops:
        m = re.match(r"\s*(byte|word|dword|qword)\b", o, re.I)
        if m:
            return {"byte": 8, "word": 16, "dword": 32, "qword": 64}[m.group(1).lower()]
    return 32 if bits_default != 16 else 16


# ============================================================================ words
def _what(mn: str, ops: list[str]) -> tuple[str, str]:
    a = ops[0] if ops else ""
    b = ops[1] if len(ops) > 1 else ""
    c = ops[2] if len(ops) > 2 else ""
    A, B, Cc = a.upper() if _is_reg(a) else a, b.upper() if _is_reg(b) else b, c
    base = mn.split()[-1]
    suf = cond_suffix(base)
    T = {
        "mov": (f"Copy {B} into {A}.", f"انسخ {B} إلى {A}."),
        "movzx": (f"Copy {B} into the bigger {A} and fill the upper bits with zeros.",
                  f"انسخ {B} إلى {A} الأكبر واملأ البتات العليا بأصفار."),
        "movsx": (f"Copy {B} into the bigger {A} and repeat its sign bit in the upper bits.",
                  f"انسخ {B} إلى {A} الأكبر وكرّر بت الإشارة في البتات العليا."),
        "movsxd": (f"Sign-extend the 32-bit {B} into {A}.", f"وسّع {B} (32 بت) إلى {A} مع الحفاظ على الإشارة."),
        "lea": (f"Compute the address {B} and put it in {A} (no memory is read).",
                f"احسب العنوان {B} وضعه في {A} (لا تُقرأ الذاكرة)."),
        "xchg": (f"Swap {A} and {B}.", f"بادل قيمتي {A} و {B}."),
        "push": (f"Put {A} on top of the stack (the stack pointer goes down first).",
                 f"ضع {A} في قمة المكدس (ينقص مؤشر المكدس أولاً)."),
        "pop": (f"Take the value on top of the stack into {A} (the stack pointer goes up).",
                f"خذ القيمة التي في قمة المكدس إلى {A} (يزيد مؤشر المكدس)."),
        "add": (f"{A} = {A} + {B}.", f"‏{A} = {A} + {B}."),
        "adc": (f"{A} = {A} + {B} + CF (add with the carry of the previous addition).",
                f"‏{A} = {A} + {B} + CF (جمع مع حمل الجمع السابق)."),
        "sub": (f"{A} = {A} - {B}.", f"‏{A} = {A} - {B}."),
        "sbb": (f"{A} = {A} - {B} - CF (subtract with the borrow of the previous subtraction).",
                f"‏{A} = {A} - {B} - CF (طرح مع استلاف الطرح السابق)."),
        "inc": (f"{A} = {A} + 1 (CF is not changed).", f"‏{A} = {A} + 1 (لا يتغير CF)."),
        "dec": (f"{A} = {A} - 1 (CF is not changed).", f"‏{A} = {A} - 1 (لا يتغير CF)."),
        "neg": (f"{A} = 0 - {A} (change the sign).", f"‏{A} = 0 - {A} (عكس الإشارة)."),
        "cmp": (f"Compare {A} with {B}: compute {A} - {B} only to set the flags (nothing is stored).",
                f"قارن {A} مع {B}: يُحسب {A} - {B} لضبط الأعلام فقط (لا يُخزَّن شيء)."),
        "test": (f"Compute {A} AND {B} only to set the flags (nothing is stored).",
                 f"احسب {A} AND {B} لضبط الأعلام فقط (لا يُخزَّن شيء)."),
        "and": (f"{A} = {A} AND {B} (keep only the bits that are 1 in both).",
                f"‏{A} = {A} AND {B} (تبقى البتات التي قيمتها 1 في الاثنين فقط)."),
        "or": (f"{A} = {A} OR {B} (a bit is 1 if it is 1 in either).",
               f"‏{A} = {A} OR {B} (البت يصبح 1 إذا كان 1 في أي منهما)."),
        "xor": ((f"{A} = 0 (XOR of a register with itself is the usual way to clear it)." if a.lower() == b.lower()
                 else f"{A} = {A} XOR {B} (a bit is 1 where the two differ)."),
                (f"‏{A} = 0 (XOR للمسجل مع نفسه هو الطريقة المعتادة لتصفيره)." if a.lower() == b.lower()
                 else f"‏{A} = {A} XOR {B} (البت يصبح 1 حيث يختلفان).")),
        "not": (f"Invert every bit of {A}.", f"اقلب كل بتات {A}."),
        "shl": (f"Shift {A} left by {B or 1} bit(s) (= multiply by 2^{B or 1}); the last bit out goes to CF.",
                f"أزح {A} لليسار {B or 1} بت (= ضرب في 2 أس {B or 1})؛ آخر بت خارج يذهب إلى CF."),
        "sal": (f"Shift {A} left by {B or 1} bit(s); the last bit out goes to CF.",
                f"أزح {A} لليسار {B or 1} بت؛ آخر بت خارج يذهب إلى CF."),
        "shr": (f"Shift {A} right by {B or 1} bit(s), filling with zeros (= unsigned divide by 2^{B or 1}).",
                f"أزح {A} لليمين {B or 1} بت مع إدخال أصفار (= قسمة بدون إشارة على 2 أس {B or 1})."),
        "sar": (f"Shift {A} right by {B or 1} bit(s), repeating the sign bit (= signed divide by 2^{B or 1}).",
                f"أزح {A} لليمين {B or 1} بت مع تكرار بت الإشارة (= قسمة بإشارة على 2 أس {B or 1})."),
        "rol": (f"Rotate {A} left by {B or 1} bit(s).", f"دوّر {A} لليسار {B or 1} بت."),
        "ror": (f"Rotate {A} right by {B or 1} bit(s).", f"دوّر {A} لليمين {B or 1} بت."),
        "mul": (f"Unsigned multiply the accumulator (AL/AX/EAX/RAX) by {A}; the double-size result goes to "
                f"(E/R)DX:(E/R)AX.",
                f"اضرب المجمّع (AL/AX/EAX/RAX) في {A} بدون إشارة؛ الناتج مزدوج الحجم يذهب إلى DX:AX (أو EDX:EAX / RDX:RAX)."),
        "imul": ((f"Signed multiply the accumulator by {A} (result in DX:AX / EDX:EAX / RDX:RAX)." if len(ops) == 1
                  else f"{A} = {A} * {B} (signed)." if len(ops) == 2 else f"{A} = {B} * {Cc} (signed)."),
                 (f"اضرب المجمّع في {A} بإشارة (الناتج في DX:AX أو EDX:EAX أو RDX:RAX)." if len(ops) == 1
                  else f"‏{A} = {A} × {B} (بإشارة)." if len(ops) == 2 else f"‏{A} = {B} × {Cc} (بإشارة).")),
        "div": (f"Unsigned divide (E/R)DX:(E/R)AX by {A}: quotient in (E/R)AX, remainder in (E/R)DX "
                f"(for a byte: AX / {A}, AL = quotient, AH = remainder).",
                f"قسمة بدون إشارة لـ EDX:EAX (أو RDX:RAX / DX:AX) على {A}: الخارج في EAX والباقي في EDX "
                f"(وللبايت: AX ÷ {A}، الخارج في AL والباقي في AH)."),
        "idiv": (f"Signed divide (E/R)DX:(E/R)AX by {A}: quotient in (E/R)AX, remainder in (E/R)DX.",
                 f"قسمة بإشارة لـ EDX:EAX (أو RDX:RAX) على {A}: الخارج في EAX والباقي في EDX."),
        "cdq": ("Copy the sign bit of EAX into every bit of EDX (prepares EDX:EAX for IDIV).",
                "انسخ بت الإشارة في EAX إلى كل بتات EDX (يجهّز EDX:EAX لـ IDIV)."),
        "cqo": ("Copy the sign bit of RAX into every bit of RDX (prepares RDX:RAX for IDIV).",
                "انسخ بت الإشارة في RAX إلى كل بتات RDX (يجهّز RDX:RAX لـ IDIV)."),
        "cwd": ("Copy the sign bit of AX into DX.", "انسخ بت الإشارة في AX إلى DX."),
        "cbw": ("Sign-extend AL into AX.", "وسّع AL إلى AX مع الإشارة."),
        "cwde": ("Sign-extend AX into EAX.", "وسّع AX إلى EAX مع الإشارة."),
        "cdqe": ("Sign-extend EAX into RAX.", "وسّع EAX إلى RAX مع الإشارة."),
        "jmp": (f"Always continue at {A}.", f"تابع التنفيذ دائماً عند {A}."),
        "call": (f"Push the return address (the next instruction) and jump to {A}.",
                 f"ادفع عنوان الرجوع (التعليمة التالية) إلى المكدس ثم اقفز إلى {A}."),
        "ret": ((f"Take the return address from the top of the stack, jump there and remove {A} more bytes of "
                 f"arguments." if a else "Take the return address from the top of the stack and jump there."),
                (f"خذ عنوان الرجوع من قمة المكدس واقفز إليه ثم أزل {A} بايت إضافية من المعاملات." if a
                 else "خذ عنوان الرجوع من قمة المكدس واقفز إليه.")),
        "leave": ("Undo the stack frame: mov rsp, rbp then pop rbp (esp / ebp in 32-bit code).",
                  "ألغِ إطار المكدس: mov rsp, rbp ثم pop rbp (أو esp / ebp في 32 بت)."),
        "enter": (f"Create a stack frame with {A} bytes of locals: push rbp / mov rbp, rsp / sub rsp, {A}.",
                  f"أنشئ إطار مكدس بمساحة {A} بايت للمتغيرات المحلية: push rbp ثم mov rbp, rsp ثم sub rsp, {A}."),
        "loop": (f"Decrease (E/R)CX by 1; jump to {A} if it is not zero yet.",
                 f"أنقص ECX (أو RCX) بواحد، واقفز إلى {A} إذا لم يصبح صفراً بعد."),
        "nop": ("Do nothing (one byte of padding).", "لا تفعل شيئاً (بايت حشو)."),
        "int": (f"Call interrupt {A} (an operating-system / BIOS service).",
                f"استدعِ المقاطعة {A} (خدمة من نظام التشغيل أو BIOS)."),
        "syscall": ("Call the operating system: RAX selects the service, arguments in RDI, RSI, RDX, R10, R8, R9.",
                    "استدعِ نظام التشغيل: RAX يحدد الخدمة، والمعاملات في RDI و RSI و RDX و R10 و R8 و R9."),
        "cld": ("Clear DF: string instructions move forward.", "صفّر DF: تعليمات النصوص تتقدم للأمام."),
        "std": ("Set DF: string instructions move backward.", "اجعل DF = 1: تعليمات النصوص ترجع للخلف."),
        "clc": ("Clear CF.", "صفّر CF."),
        "stc": ("Set CF to 1.", "اجعل CF = 1."),
        "cmc": ("Invert CF.", "اقلب قيمة CF."),
        "hlt": ("Stop the CPU until an interrupt (not allowed in normal programs).",
                "أوقف المعالج حتى تأتي مقاطعة (غير مسموح في البرامج العادية)."),
        "bswap": (f"Reverse the byte order of {A}.", f"اعكس ترتيب بايتات {A}."),
        "bt": (f"Copy bit {B} of {A} into CF.", f"انسخ البت رقم {B} من {A} إلى CF."),
    }
    if base in T:
        return T[base]
    if suf is not None:
        en_m, ar_m = _COND[suf][3], _COND[suf][4]
        if base.startswith("j"):
            return (f"Jump to {A} if the last comparison gave '{en_m}'; otherwise continue with the next line.",
                    f"اقفز إلى {A} إذا كانت نتيجة آخر مقارنة '{ar_m}'؛ وإلا تابع بالسطر التالي.")
        if base.startswith("set"):
            return (f"{A} = 1 if '{en_m}', else 0.", f"‏{A} = 1 إذا كان '{ar_m}'، وإلا 0.")
        return (f"Copy {B} into {A} only if '{en_m}'.", f"انسخ {B} إلى {A} فقط إذا كان '{ar_m}'.")
    if base.startswith(("movs", "stos", "lods", "cmps", "scas")) and len(base) <= 5:
        unit = {"b": "byte", "w": "word", "d": "dword", "q": "qword"}.get(base[-1], "item")
        rep = "rep" in mn
        en = {"movs": f"copy one {unit} from [RSI] to [RDI]", "stos": f"store AL/AX/EAX/RAX as one {unit} at [RDI]",
              "lods": f"load one {unit} from [RSI] into the accumulator",
              "cmps": f"compare the {unit} at [RSI] with the one at [RDI]",
              "scas": f"compare the accumulator with the {unit} at [RDI]"}[base[:4]]
        ar = {"movs": f"انسخ {unit} واحداً من [RSI] إلى [RDI]", "stos": f"خزّن المجمّع كـ {unit} عند [RDI]",
              "lods": f"حمّل {unit} من [RSI] إلى المجمّع", "cmps": f"قارن الـ {unit} عند [RSI] مع الذي عند [RDI]",
              "scas": f"قارن المجمّع مع الـ {unit} عند [RDI]"}[base[:4]]
        tail_en = "; RSI / RDI move to the next item" + ("; repeated RCX times (RCX counts down)" if rep else "")
        tail_ar = "؛ ينتقل RSI و RDI إلى العنصر التالي" + ("؛ ويتكرر RCX مرة (RCX يتناقص)" if rep else "")
        return (en[0].upper() + en[1:] + tail_en + ".", ar + tail_ar + ".")
    try:
        from ..asm_intel import isa
        ins = isa.instruction(base)
        if ins is not None:
            return (ins.doc, f"{ins.doc} (الشرح العربي التفصيلي غير متوفر لهذه التعليمة)")
    except Exception:  # noqa: BLE001
        pass
    return (f"{mn} {', '.join(ops)}", f"{mn} {', '.join(ops)}")


# ============================================================================ flags
def _parity(v: int) -> bool:
    return bin(v & 0xFF).count("1") % 2 == 0


def _flag_reasons(mn: str, a: int | None, b: int | None, result: int | None, bits: int, f_after: dict,
                  f_before: dict) -> list[tuple[str, int, str, str]]:
    """[(flag, value, english reason, arabic reason)] for the flags *mn* sets."""
    base = mn.split()[-1]
    out = []
    if result is None:
        return out
    r = result & _mask(bits)
    sr = _signed(r, bits)
    top = bits - 1

    def zf():
        if f_after["ZF"]:
            out.append(("ZF", 1, "the result is zero" if base not in ("cmp",) else f"the two values are equal ({a} = {b})",
                        "الناتج صفر" if base != "cmp" else f"القيمتان متساويتان ({a} = {b})"))
        else:
            out.append(("ZF", 0, f"the result {sr} is not zero" if base != "cmp" else "the two values are different",
                        f"الناتج {sr} ليس صفراً" if base != "cmp" else "القيمتان مختلفتان"))

    def sf():
        if f_after["SF"]:
            out.append(("SF", 1, f"the top bit (bit {top}) of the result is 1: negative ({sr}) as a signed number",
                        f"أعلى بت (البت {top}) في الناتج = 1: سالب ({sr}) إذا اعتبرناه بإشارة"))
        else:
            out.append(("SF", 0, f"the top bit (bit {top}) of the result is 0: the result is positive or zero",
                        f"أعلى بت (البت {top}) في الناتج = 0: الناتج موجب أو صفر"))

    def pf():
        n = bin(r & 0xFF).count("1")
        out.append(("PF", int(f_after["PF"]), f"the low byte {r & 0xFF:#04x} has {n} bit(s) set "
                    f"({'even' if n % 2 == 0 else 'odd'})",
                    f"البايت الأدنى {r & 0xFF:#04x} فيه {n} بت قيمتها 1 ({'زوجي' if n % 2 == 0 else 'فردي'})"))

    known = a is not None and (b is not None or base in ("inc", "dec", "neg"))
    if base in ("add", "adc", "sub", "sbb", "cmp") and not known:
        zf()
        sf()
        cf, of = int(f_after["CF"]), int(f_after["OF"])
        out.append(("CF", cf, ("an unsigned carry / borrow happened" if cf else "no unsigned carry or borrow"),
                    ("حدث حمل أو استلاف بدون إشارة" if cf else "لا يوجد حمل ولا استلاف بدون إشارة")))
        out.append(("OF", of, ("the signed result did not fit" if of else "the signed result fits"),
                    ("الناتج بإشارة لم يتسع" if of else "الناتج بإشارة يتسع")))
        pf()
    elif base in ("add", "adc", "inc", "xadd"):
        zf()
        sf()
        if base != "inc":
            ua, ub = (a or 0) & _mask(bits), (b if b is not None else 1) & _mask(bits)
            true = ua + ub + (1 if base == "adc" and f_before.get("CF") else 0)
            if f_after["CF"]:
                out.append(("CF", 1, f"unsigned carry: {ua} + {ub} = {true} does not fit in {bits} bits",
                            f"حمل بدون إشارة: {ua} + {ub} = {true} لا يتسع في {bits} بت"))
            else:
                out.append(("CF", 0, f"no carry: the unsigned sum {true} fits in {bits} bits",
                            f"لا يوجد حمل: المجموع بدون إشارة {true} يتسع في {bits} بت"))
        else:
            out.append(("CF", int(f_after["CF"]), "INC does not change CF", "التعليمة INC لا تغيّر CF"))
        sa, sb = _signed(a or 0, bits), _signed(b if b is not None else 1, bits)
        if f_after["OF"]:
            out.append(("OF", 1, f"signed overflow: {sa} + {sb} = {sa + sb} is outside the signed {bits}-bit range",
                        f"فيضان بإشارة: {sa} + {sb} = {sa + sb} خارج مدى الأعداد بإشارة في {bits} بت"))
        else:
            out.append(("OF", 0, f"no signed overflow: {sa} + {sb} = {sa + sb} fits",
                        f"لا فيضان بإشارة: {sa} + {sb} = {sa + sb} يتسع"))
        pf()
    elif base in ("sub", "sbb", "cmp", "dec", "neg"):
        zf()
        sf()
        ua = (a or 0) & _mask(bits)
        ub = (b if b is not None else 1) & _mask(bits)
        if base == "neg":
            ua, ub = 0, (a or 0) & _mask(bits)
        sa, sb = _signed(ua, bits), _signed(ub, bits)
        if base != "dec":
            if f_after["CF"]:
                out.append(("CF", 1, f"borrow: {ua} < {ub} as unsigned numbers",
                            f"استلاف: {ua} < {ub} كأرقام بدون إشارة"))
            else:
                out.append(("CF", 0, f"no borrow: {ua} >= {ub} as unsigned numbers",
                            f"لا يوجد استلاف: {ua} >= {ub} كأرقام بدون إشارة"))
        else:
            out.append(("CF", int(f_after["CF"]), "DEC does not change CF", "التعليمة DEC لا تغيّر CF"))
        if f_after["OF"]:
            out.append(("OF", 1, f"signed overflow: {sa} - {sb} = {sa - sb} is outside the signed {bits}-bit range",
                        f"فيضان بإشارة: {sa} - {sb} = {sa - sb} خارج مدى الأعداد بإشارة في {bits} بت"))
        else:
            out.append(("OF", 0, f"no signed overflow: {sa} - {sb} = {sa - sb} fits",
                        f"لا فيضان بإشارة: {sa} - {sb} = {sa - sb} يتسع"))
        pf()
    elif base in ("and", "or", "xor", "test"):
        zf()
        sf()
        out.append(("CF", 0, f"{base.upper()} always clears CF", f"التعليمة {base.upper()} تصفّر CF دائماً"))
        out.append(("OF", 0, f"{base.upper()} always clears OF", f"التعليمة {base.upper()} تصفّر OF دائماً"))
        pf()
    elif base in ("shl", "sal", "shr", "sar", "rol", "ror"):
        if base not in ("rol", "ror"):
            zf()
            sf()
        out.append(("CF", int(f_after["CF"]), f"CF = the last bit shifted out ({int(f_after['CF'])})",
                    f"CF = آخر بت خرج بالإزاحة ({int(f_after['CF'])})"))
    elif base in ("mul", "imul"):
        out.append(("CF", int(f_after["CF"]), "CF=OF=1 when the upper half of the result is needed (the result "
                    "does not fit in the lower half)" if f_after["CF"] else "CF=OF=0: the result fits in the lower half",
                    "CF=OF=1 عندما يحتاج الناتج النصف العلوي (لا يتسع في النصف السفلي)" if f_after["CF"]
                    else "CF=OF=0: الناتج يتسع في النصف السفلي"))
    return out


# ============================================================================ main entry
def explain_step(ins_text: str, before: dict | None, after: dict | None = None, writes=(), reads=(),
                 bits: int = 64, next_ins: str = "", describe_addr=None) -> dict:
    """Explain one executed instruction. *before* / *after*: register dicts (rax.. or eax.., ``eflags``)."""
    mn, ops = split_instruction(ins_text)
    base = mn.split()[-1] if mn else ""
    size = _op_size(ops, bits)
    what_en, what_ar = _what(mn, ops)
    res = {"mnemonic": mn, "operands": ops, "what_en": what_en, "what_ar": what_ar, "changes": [], "flags": [],
           "jump": None, "ref": base, "summary_en": "", "summary_ar": ""}
    try:
        from ..asm_intel import isa
        ins = isa.instruction(base)
        if ins is not None:
            res["ref_doc"] = ins.doc
            res["ref_url"] = isa.SDM_URL
            res["flags_spec"] = isa.flags_text(ins.flags) if ins.flags and ins.flags != "-" else ""
    except Exception:  # noqa: BLE001
        pass
    if before is None:
        return res
    # operand values before
    mem_val = reads[0][2] if reads else None

    def val(op: str):
        if not op:
            return None
        if _is_reg(op):
            return _reg_value(before, op)
        im = _imm(op)
        if im is not None:
            return im
        if "[" in op:
            return mem_val
        return None

    a_v = val(ops[0]) if ops else None
    b_v = val(ops[1]) if len(ops) > 1 else None
    if b_v is None and len(ops) > 1 and after and _is_reg(ops[0]) and a_v is not None and             base in ("add", "sub"):
        r_after = _reg_value(after, ops[0])
        if r_after is not None:                     # the memory operand, derived from the result
            b_v = (r_after - a_v if base == "add" else a_v - r_after) & _mask(SIZE_OF[ops[0].lower()])
    # register changes
    if after:
        shown = set()
        used = [o.lower() for o in ops if _is_reg(o)]
        for name in list(after.keys()):
            if name in ("eflags",) or name in ("rip", "eip", "ip"):
                continue
            b0, a0 = before.get(name), after.get(name)
            if b0 is None or a0 is None or b0 == a0:
                continue
            disp = next((u for u in used if _family(u) == _family(name)), name)
            if disp in ("ah", "bh", "ch", "dh"):
                disp = name
            w = SIZE_OF.get(disp, 64 if name.startswith("r") else 32)
            vb, va = _reg_value(before, disp), _reg_value(after, disp)
            if vb == va:
                disp, w, vb, va = name, SIZE_OF.get(name, 64), b0, a0
            if disp in shown:
                continue
            shown.add(disp)
            res["changes"].append({"name": disp.upper(), "before": vb, "after": va, "bits": w,
                                   "text": f"{disp.upper()}: {_fmt(vb, w)} -> {_fmt(va, w)}"})
    for addr, n, old, new in writes:
        oldv = int.from_bytes(old, "little") if old else None
        where = describe_addr(addr) if describe_addr else f"{addr:#x}"
        res["changes"].append({"name": f"[{where}]", "before": oldv, "after": new & _mask(8 * n), "bits": 8 * n,
                               "text": f"[{where}] ({n} byte{'s' if n > 1 else ''}): {_fmt(oldv, 8 * n)} -> "
                                       f"{_fmt(new, 8 * n)}"})
    # result value for the flag reasons
    result = None
    if after:
        fb, fa = flags_of(before.get("eflags", 0)), flags_of(after.get("eflags", 0))
        if base in ("cmp", "test"):
            if a_v is not None and b_v is not None:
                result = (a_v - b_v) if base == "cmp" else (a_v & b_v)
        elif base == "neg" and a_v is not None:
            result = -a_v
        elif ops and _is_reg(ops[0]):
            result = _reg_value(after, ops[0])
        elif ops and "[" in ops[0] and writes:
            result = writes[-1][3]
        if base in ("mul", "imul", "div", "idiv"):
            result = 0
        res["flags"] = [{"flag": fl, "value": v, "en": en, "ar": ar}
                        for fl, v, en, ar in _flag_reasons(mn, a_v, b_v, result, size, fa, fb)]
        flags_line = " ".join(f"{x['flag']}={x['value']}" for x in res["flags"] if x["flag"] in ("ZF", "SF", "CF", "OF"))
        ch = "; ".join(c["text"] for c in res["changes"][:4])
        res["summary_en"] = f"{ins_text.strip()}: " + "; ".join(x for x in (ch, flags_line) if x)
        res["summary_ar"] = f"{ins_text.strip()}: " + "؛ ".join(x for x in (ch, flags_line) if x)
        if not ch and not flags_line:
            res["summary_en"] += "no register or flag changed"
            res["summary_ar"] += "لم يتغير أي مسجل أو علم"
        if res["flags"]:
            short = [x for x in res["flags"] if x["flag"] in ("ZF", "SF", "CF", "OF")]
            res["summary_en"] += " because " + ", ".join(x["en"] for x in short[:3]) if short else ""
            res["summary_ar"] += " لأن " + "، و".join(x["ar"] for x in short[:3]) if short else ""
    # jump / condition
    flags_now = (after or before).get("eflags", 0) if base not in ("jmp",) else None
    target = None
    if cond_suffix(base) is not None and base.startswith(("j", "set", "cmov")):
        c = condition_text(base, before.get("eflags", 0))
        if c:
            target = ops[0] if ops else ""
            res["jump"] = _jump_words(base, target, c)
    elif next_ins and flags_now is not None:
        nmn, nops = split_instruction(next_ins)
        if cond_suffix(nmn) is not None and nmn.startswith("j"):
            c = condition_text(nmn, flags_now)
            if c:
                res["jump"] = _jump_words(nmn, nops[0] if nops else "", c, cmp=(base, ops, a_v, b_v, size))
    elif base == "loop" and before is not None:
        cx = _reg_value(before, "rcx" if bits == 64 else "ecx")
        if cx is not None:
            taken = (cx - 1) & _mask(64 if bits == 64 else 32) != 0
            res["jump"] = {"taken": taken,
                           "en": f"'loop {ops[0] if ops else ''}' is {'TAKEN' if taken else 'NOT taken'}: the counter "
                                 f"becomes {cx - 1}" + ("" if taken else " (zero), so the loop ends"),
                           "ar": f"'loop {ops[0] if ops else ''}' {'سيقفز' if taken else 'لن يقفز'}: يصبح العداد "
                                 f"{cx - 1}" + ("" if taken else " (صفر)، فتنتهي الحلقة")}
    return res


def _jump_words(mn: str, target: str, c: dict, cmp=None) -> dict:
    suf = cond_suffix(mn)
    sym, signed = _COND[suf][1], _COND[suf][2]
    verb_en = "be TAKEN" if c["taken"] else "NOT be taken"
    verb_ar = "سيقفز" if c["taken"] else "لن يقفز"
    kind = "jump" if mn.startswith("j") else "move" if mn.startswith("cmov") else "set"
    head_en = f"'{mn} {target}' will {verb_en}" if kind == "jump" else f"'{mn}' condition is {'true' if c['taken'] else 'false'}"
    head_ar = f"'{mn} {target}' {verb_ar}" if kind == "jump" else f"شرط '{mn}' {'صحيح' if c['taken'] else 'خاطئ'}"
    extra_en = extra_ar = ""
    if cmp is not None and sym:
        base, ops, a_v, b_v, size = cmp
        if base in ("cmp", "sub") and a_v is not None and b_v is not None and len(ops) >= 2:
            if signed is False:
                x, y = a_v & _mask(size), b_v & _mask(size)
            else:
                x, y = _signed(a_v, size), _signed(b_v, size)
            rel = {"==": x == y, "!=": x != y, "<": x < y, "<=": x <= y, ">": x > y, ">=": x >= y}[sym]
            kind_en = "" if signed is None else (" (signed)" if signed else " (unsigned)")
            kind_ar = "" if signed is None else (" (بإشارة)" if signed else " (بدون إشارة)")
            extra_en = f" - it asks whether {ops[0]} {sym} {ops[1]}{kind_en}: {x} {sym} {y} is {'true' if rel else 'false'}"
            extra_ar = f" - السؤال هو هل {ops[0]} {sym} {ops[1]}{kind_ar}: {x} {sym} {y} {'صحيح' if rel else 'خطأ'}"
        elif base == "test" and len(ops) >= 2 and ops[0].lower() == ops[1].lower() and a_v is not None:
            extra_en = f" - 'test {ops[0]}, {ops[0]}' checks {ops[0]} itself: {ops[0]} = {_signed(a_v, size)}"
            extra_ar = f" - 'test {ops[0]}, {ops[0]}' تفحص {ops[0]} نفسه: {ops[0]} = {_signed(a_v, size)}"
    return {"taken": c["taken"], "en": f"{head_en} because {c['en']}{extra_en}.",
            "ar": f"{head_ar} لأن {c['ar']}{extra_ar}."}


def to_html(info: dict, lang: str = "en", both: bool = True) -> str:
    """HTML for the Explain panel (the UI language first, the other language after it when *both*)."""
    import html as H

    def block(lg: str) -> str:
        rtl = lg == "ar"
        k = "ar" if rtl else "en"
        out = [f"<div dir='{'rtl' if rtl else 'ltr'}' style='margin-bottom:10px'>"]
        out.append(f"<p><b>{H.escape(info.get('mnemonic', ''))} {H.escape(', '.join(info.get('operands', [])))}</b>"
                   f" &mdash; {H.escape(info['what_' + k])}</p>")
        if info.get("changes"):
            out.append("<p><b>" + ("ما الذي تغيّر:" if rtl else "What changed:") + "</b><br>")
            out.append("<br>".join(f"<code>{H.escape(c['text'])}</code>" for c in info["changes"]) + "</p>")
        if info.get("flags"):
            out.append("<p><b>" + ("الأعلام:" if rtl else "Flags:") + "</b><br>")
            out.append("<br>".join(f"<code>{x['flag']}={x['value']}</code> " +
                                   ("لأن " if rtl else "because ") + H.escape(x[k]) for x in info["flags"]) + "</p>")
        if info.get("jump"):
            j = info["jump"]
            color = "#2e7d32" if j["taken"] else "#c62828"
            out.append(f"<p style='color:{color}'><b>{H.escape(j[k])}</b></p>")
        out.append("</div>")
        return "".join(out)

    parts = [block(lang)]
    if both:
        parts.append("<hr>" + block("en" if lang == "ar" else "ar"))
    if info.get("ref_url"):
        parts.append(f"<p><a href='{info['ref_url']}'>Intel SDM: {H.escape(info.get('ref', '').upper())}</a>"
                     f" &mdash; {H.escape(info.get('ref_doc', ''))}</p>")
    return "".join(parts)
