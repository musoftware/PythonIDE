"""Operand / encoding checks of single instructions (ASM1xx) - they need no control flow."""
from __future__ import annotations

import re

from ..asm_intel import isa
from .model import Fix, Issue
from .parse import GP, HIGH8, REG32, REG64_ONLY, REX8, SIZE_WORDS, Operand, Program, Stmt, sibling

SAME_SIZE = {"mov", "add", "adc", "sub", "sbb", "and", "or", "xor", "cmp", "test", "xchg", "cmpxchg", "xadd"} | \
    {"cmov" + c for c in ("o", "no", "b", "c", "nae", "ae", "nb", "nc", "e", "z", "ne", "nz", "be", "na", "a",
                          "nbe", "s", "ns", "p", "pe", "np", "po", "l", "nge", "ge", "nl", "le", "ng", "g", "nle")}
SHIFTS = {"shl", "shr", "sal", "sar", "rol", "ror", "rcl", "rcr"}
AMBIGUOUS = {"mov", "add", "adc", "sub", "sbb", "and", "or", "xor", "cmp", "test", "inc", "dec", "neg", "not",
             "mul", "imul", "div", "idiv", "movzx", "movsx"} | SHIFTS
WRITE_DEST = {"mov", "add", "adc", "sub", "sbb", "and", "or", "xor", "inc", "dec", "neg", "not", "lea", "movzx",
              "movsx", "movsxd", "pop", "xchg", "bsf", "bsr", "popcnt", "lzcnt", "tzcnt", "xadd", "cmpxchg", "bts",
              "btr", "btc"} | SHIFTS | {m for m in SAME_SIZE if m.startswith("cmov")} | \
    {"set" + c for c in ("o", "no", "b", "c", "nae", "ae", "nb", "nc", "e", "z", "ne", "nz", "be", "na", "a", "nbe",
                         "s", "ns", "p", "pe", "np", "po", "l", "nge", "ge", "nl", "le", "ng", "g", "nle")}
ARITH_NO_SREG = {"add", "adc", "sub", "sbb", "and", "or", "xor", "cmp", "test", "inc", "dec", "neg", "not", "mul",
                 "imul", "div", "idiv", "xchg"} | SHIFTS
OPERAND_COUNT = {
    **{m: (2, 2) for m in ("mov", "add", "adc", "sub", "sbb", "and", "or", "xor", "cmp", "test", "lea", "movzx",
                           "movsx", "movsxd", "xchg", "cmpxchg", "xadd", "bt", "bts", "btr", "btc", "bsf", "bsr")},
    **{m: (1, 1) for m in ("inc", "dec", "neg", "not", "mul", "div", "idiv", "bswap", "int", "jmp", "call",
                           "loop", "loope", "loopne", "loopz", "loopnz", "jcxz", "jecxz", "jrcxz")},
    **{m: (0, 0) for m in ("cbw", "cwde", "cdqe", "cwd", "cdq", "cqo", "clc", "stc", "cmc", "cld", "std", "cli",
                           "sti", "hlt", "pushf", "popf", "pushfd", "popfd", "pushfq", "popfq", "lahf", "sahf",
                           "leave", "pusha", "popa", "pushad", "popad", "cpuid", "rdtsc", "syscall", "int3",
                           "into", "iret", "iretd", "iretq", "aaa", "aas", "daa", "das")},
    "ret": (0, 1), "retn": (0, 1), "retf": (0, 1), "imul": (1, 3), "enter": (2, 2),
    **{m: (1, 2) for m in SHIFTS}, "shld": (3, 3), "shrd": (3, 3),
}
_JCC_ONE = {"j" + c for c in ("o", "no", "b", "c", "nae", "ae", "nb", "nc", "e", "z", "ne", "nz", "be", "na", "a",
                              "nbe", "s", "ns", "p", "pe", "np", "po", "l", "nge", "ge", "nl", "le", "ng", "g", "nle")}
I186 = {"pusha", "popa", "enter", "leave", "bound", "insb", "insw", "outsb", "outsw", "ins", "outs"}
I386 = {"movzx", "movsx", "jecxz", "cdq", "cwde", "bt", "bts", "btr", "btc", "bsf", "bsr", "shld", "shrd",
        "pushad", "popad", "pushfd", "popfd", "lfs", "lgs", "lss"} | {"set" + c for c in ("z", "nz", "e", "ne")}
DOS_INTS = {0x21: "DOS", 0x20: "DOS", 0x10: "BIOS", 0x16: "BIOS", 0x13: "BIOS", 0x1A: "BIOS", 0x33: "DOS mouse",
            0x27: "DOS"}
DOS_INTS_AR = {"DOS": "نظام DOS", "BIOS": "الـ BIOS", "DOS mouse": "الفأرة في DOS", "Linux (32-bit)": "لينكس 32 بت"}


def size_word(prog: Program, bits: int) -> str:
    w = {8: "byte", 16: "word", 32: "dword", 64: "qword", 80: "tword", 128: "oword"}.get(bits, "dword")
    if prog.dialect == "masm" or (prog.dialect == "gas" and not prog.att):
        if bits == 128:
            w = "xmmword"
        return w + " ptr"
    return w


def _n(v: int) -> str:
    return str(v) if -10 < v < 10 else f"{v} (0x{v & 0xFFFFFFFFFFFFFFFF:X})" if v >= 0 else str(v)


def _line_code(prog: Program, st: Stmt) -> str:
    return prog.lines[st.line][:st.end_col]


class OperandChecks:
    def __init__(self, prog: Program, out: list):
        self.p = prog
        self.out = out

    def add(self, rule: str, st: Stmt, col: int, end: int, fixes=None, mnem: str = "", **args) -> Issue:
        args.setdefault("mnem", (mnem or st.mnem).upper())
        it = Issue(rule, st.line, col, end, args, list(fixes or []), mnem=(mnem or st.mnem).lower())
        self.out.append(it)
        return it

    def whole(self, st: Stmt) -> tuple[int, int]:
        return st.mcol, max(st.end_col, st.mend)

    # ------------------------------------------------------------ fixes
    def fix_replace_op(self, st: Stmt, o: Operand, new: str, en: str, ar: str) -> Fix:
        return Fix(en, ar, [{"range": [st.line, o.col, st.line, o.end], "text": new}])

    def fix_replace_mnem(self, st: Stmt, new: str, en: str, ar: str, extra=None) -> Fix:
        edits = [{"range": [st.line, st.mcol, st.line, st.mend], "text": new}]
        edits += extra or []
        return Fix(en, ar, edits)

    def fix_lines(self, st: Stmt, texts: list[str], en: str, ar: str) -> Fix:
        """Replace the whole statement (labels kept) with several instruction lines."""
        code = _line_code(self.p, st)
        head = code[:st.mcol] if st.labels else ""
        ind = st.indent if not st.labels else " " * max(4, len(st.indent))
        if head.strip():
            first = head.rstrip() + " " + texts[0] if head.rstrip().endswith(":") else head + texts[0]
            rest = [ind + t for t in texts[1:]]
            new = "\n".join([first] + rest)
        else:
            new = "\n".join(ind + t for t in texts)
        return Fix(en, ar, [{"range": [st.line, 0, st.line, len(code.rstrip())], "text": new}])

    def regname(self, r: str) -> str:
        return r.upper()

    def optxt(self, o: Operand) -> str:
        return o.text

    # ------------------------------------------------------------ the checks
    def run(self) -> None:
        for st in self.p.stmts:
            if st.kind != "instr" or not st.mnem:
                continue
            try:
                self.check(st)
            except Exception:  # noqa: BLE001 - one odd line must not stop the analysis
                continue

    def check(self, st: Stmt) -> None:
        p = self.p
        m = st.mnem
        ops = st.ops
        n = len(ops)
        # ---------------------------------------------- operand count
        rng = OPERAND_COUNT.get(m) or ((1, 1) if m in _JCC_ONE else None)
        if rng and not (p.att and m in ("ret", "retq")):
            lo, hi = rng
            if m == "int" and n == 0 and st.raw.lower() == "int3":
                rng = None
            elif not lo <= n <= hi:
                exp_en = (f"{lo} operand{'s' if lo != 1 else ''}" if lo == hi else f"{lo} to {hi} operands")
                exp_ar = ("بدون معاملات" if lo == hi == 0 else f"{lo} معامل" if lo == hi else
                          f"من {lo} إلى {hi} معاملات")
                c, e = self.whole(st)
                self.add("ASM116", st, c, e, mnem=m, expected=exp_en, expected_ar=exp_ar, got=n)
                return
        regs = [o for o in ops if o.kind == "reg"]
        mems = [o for o in ops if o.kind == "mem"]
        mode = p.bits
        # ---------------------------------------------- registers that do not exist in this mode
        seen = set()
        for o in ops:
            names = [o.reg] if o.kind == "reg" else list(o.regs) if o.kind == "mem" else []
            for r in names:
                if r in seen:
                    continue
                seen.add(r)
                bad = ""
                if mode == 16 and p.cpu == "8086" and (r in REG32 or r in REG64_ONLY):
                    bad = "8086"
                elif mode in (16, 32) and r in REG64_ONLY:
                    bad = "64"
                if bad:
                    if bad == "8086":
                        why = ("The 8086 has only 16-bit registers: AX BX CX DX SI DI BP SP and the 8-bit halves AL AH "
                               "BL BH CL CH DL DH. 32-bit registers such as EAX arrived with the 80386.")
                        why_ar = ("المعالج 8086 فيه مسجلات 16 بت فقط: AX و BX و CX و DX و SI و DI و BP و SP وأنصافها "
                                  "ذات الـ 8 بت AL و AH و BL و BH و CL و CH و DL و DH. أما المسجلات 32 بت مثل EAX "
                                  "فظهرت مع المعالج 80386.")
                        regs_txt = "AX BX CX DX SI DI BP SP, AL AH ..."
                        mode_txt = "8086 (16-bit)"
                        mode_ar = "8086 (16 بت)"
                    else:
                        why = ("64-bit registers (RAX ... R15) and the byte registers SIL DIL SPL BPL R8B-R15B exist "
                               "only in 64-bit mode.")
                        why_ar = ("مسجلات 64 بت (RAX ... R15) ومسجلات البايت SIL و DIL و SPL و BPL و R8B-R15B "
                                  "موجودة في وضع 64 بت فقط.")
                        regs_txt = "EAX EBX ECX EDX ESI EDI EBP ESP" if mode == 32 else "AX BX CX DX SI DI BP SP"
                        mode_txt = f"{mode}-bit"
                        mode_ar = f"{mode} بت"
                    fix = []
                    rep = sibling(r, 16 if mode == 16 else 32, mode)
                    if rep and o.kind == "reg":
                        fix = [self.fix_replace_op(st, o, rep, f"Use {rep.upper()}", f"استخدم {rep.upper()}")]
                    self.add("ASM108", st, o.col, o.end, fix, reg=r.upper(), mode=mode_txt, mode_ar=mode_ar, why=why,
                             why_ar=why_ar,
                             regs=regs_txt)
                    return
        # ---------------------------------------------- instructions removed from 64-bit mode
        ins = isa.INSTRUCTIONS.get(m)
        if mode == 64 and ((ins is not None and ins.bits == "16/32") or m in ("lds", "les", "salc")):
            c, e = st.mcol, st.mend
            self.add("ASM115", st, c, e, mnem=m.upper())
            return
        # ---------------------------------------------- 8086 limits
        if p.cpu == "8086":
            self.check_8086(st)
        # ---------------------------------------------- addresses
        for o in mems:
            if self.check_address(st, o):
                return
        # ---------------------------------------------- segment registers / overrides
        if self.check_segments(st):
            return
        # ---------------------------------------------- immediate destination
        if ops and ops[0].kind == "imm" and (m in WRITE_DEST or m in ("cmp", "test")) and \
                not (m == "test" and n == 2 and ops[1].kind != "imm"):
            self.add("ASM109", st, ops[0].col, ops[0].end, mnem=m.upper())
            return
        if ops and ops[0].kind == "imm" and m == "test" and n == 2:
            a, b = ops[0], ops[1]
            fx = Fix("Swap the operands", "بدّل المعاملين",
                     [{"range": [st.line, a.col, st.line, a.end], "text": b.text},
                      {"range": [st.line, b.col, st.line, b.end], "text": a.text}])
            self.add("ASM109", st, a.col, a.end, [fx], mnem=m.upper())
            return
        # ---------------------------------------------- LEA
        if m == "lea" and n == 2 and ops[1].kind != "mem":
            src = ops[1]
            fixes = []
            if src.kind == "imm" and src.syms and p.dialect in ("nasm", "fasm"):
                inner = ("rel " if p.dialect == "nasm" and mode == 64 and not p.default_rel else "") + src.text
                fixes.append(self.fix_replace_op(st, src, f"[{inner}]", f"Write [{src.text}]",
                                                 f"اكتب [{src.text}]"))
                hint = f"[{src.text}]"
            elif src.kind == "reg":
                fixes.append(self.fix_replace_mnem(st, "mov", "Use MOV to copy the register", "استخدم MOV لنسخ المسجل"))
                hint = f"mov {ops[0].text}, {src.text}"
            else:
                hint = f"[{src.text}]"
            self.add("ASM112", st, src.col, src.end, fixes, hint=hint)
            return
        # ---------------------------------------------- MOVZX / MOVSX
        if m in ("movzx", "movsx") and n == 2:
            if self.check_movx(st):
                return
        # ---------------------------------------------- PUSH / POP sizes
        if m in ("push", "pop") and n >= 1:
            for o in ops:
                if self.check_push(st, o):
                    return
        # ---------------------------------------------- high byte registers with REX
        if mode == 64 and any(o.kind == "reg" and o.reg in HIGH8 for o in ops):
            h = next(o for o in ops if o.kind == "reg" and o.reg in HIGH8)
            other = ""
            for o in ops:
                if o is h:
                    continue
                if o.kind == "reg" and (o.reg in REX8 or o.reg[1:2].isdigit() and o.reg.startswith("r")):
                    other = o.reg.upper()
                elif o.kind == "mem" and any(r[1:2].isdigit() and r.startswith("r") for r in o.regs):
                    other = next(r for r in o.regs if r[1:2].isdigit()).upper()
                elif o.kind == "reg" and o.size == 64 and m in ("movzx", "movsx"):
                    other = o.reg.upper()
            if other:
                self.add("ASM113", st, h.col, h.end, reg=h.reg.upper(), other=other)
                return
        # ---------------------------------------------- MUL / DIV with an immediate
        if m in ("mul", "div", "idiv", "imul") and n == 1 and ops[0].kind == "imm":
            r = "bx" if mode == 16 else "ecx"
            v = ops[0].text
            fx = self.fix_lines(st, [f"mov {r}, {v}", f"{st.raw} {r}"],
                                f"Load {v} into {r.upper()} first", f"حمّل {v} في {r.upper()} أولاً")
            self.add("ASM117", st, ops[0].col, ops[0].end, [fx], mnem=m.upper(), reg=r, value=v)
            return
        # ---------------------------------------------- memory to memory
        if len(mems) >= 2 and m in SAME_SIZE | {"movzx", "movsx"} and m not in ("cmpxchg",):
            self.memory_to_memory(st)
            return
        # ---------------------------------------------- sizes
        if m in SAME_SIZE and n == 2:
            if self.size_mismatch(st):
                return
        if p.att and st.suffix and m not in ("movzx", "movsx", "movsxd", "lea") and m not in SHIFTS | {"in", "out"}:
            for o in regs:
                if o.size != st.suffix and o.size in (8, 16, 32, 64):
                    want = {8: "b", 16: "w", 32: "l", 64: "q"}[o.size]
                    new = st.raw[:-1] + want
                    fx = self.fix_replace_mnem(st, new, f"Use {new}", f"استخدم {new}")
                    self.add("ASM101", st, st.mcol, st.end_col, [fx], a=f"'{st.raw}'", sa=st.suffix, b=o.text,
                             sb=o.size)
                    return
        if m in AMBIGUOUS and mems:
            if self.ambiguous(st):
                return
        # ---------------------------------------------- immediate ranges
        self.immediate_range(st)
        # ---------------------------------------------- NASM / FASM: an address into a small register
        if m == "mov" and n == 2 and p.dialect in ("nasm", "fasm") and mode >= 32 and ops[0].kind == "reg" and \
                ops[1].kind == "imm" and ops[1].addr and ops[1].value is None and len(ops[1].syms) == 1:
            d = p.resolve(ops[1].syms[0], st.line, st.scope, st.proc)
            dst = ops[0]
            if d is not None and d.kind in ("data", "code", "proc") and dst.size < (64 if mode == 64 else 32):
                r64 = sibling(dst.reg, 64 if mode == 64 else 32, mode) or dst.reg
                lea = f"lea {r64}, [{'rel ' if p.dialect == 'nasm' and mode == 64 and not p.default_rel else ''}" \
                      f"{ops[1].text}]"
                fx = self.fix_lines(st, [lea], f"Use {lea}", f"استخدم {lea}")
                self.add("ASM120", st, ops[1].col, ops[1].end, [fx], sym=ops[1].syms[0], reg=dst.reg.upper(),
                         abits=mode, rbits=dst.size, hint=lea)
                return
        # ---------------------------------------------- useless instructions
        if m in ("mov", "xchg") and n == 2 and ops[0].kind == "reg" and ops[1].kind == "reg" and \
                ops[0].reg == ops[1].reg and not (mode == 64 and ops[0].size == 32):
            fx = Fix("Delete the line", "احذف السطر",
                     [{"range": [st.line, 0, st.line + 1, 0], "text": ""}]) if not st.labels else None
            what = f"{m} {ops[0].text}, {ops[1].text} copies the register onto itself"
            what_ar = f"التعليمة {m} {ops[0].text}, {ops[1].text} تنسخ المسجل إلى نفسه"
            self.add("ASM124", st, st.mcol, st.end_col, [fx] if fx else [], what=what, what_ar=what_ar)
            return
        # ---------------------------------------------- DOS / BIOS interrupts in Windows / Linux programs
        if m == "int" and n == 1 and ops[0].kind == "imm" and ops[0].value is not None and p.abi != "dos16" and \
                mode >= 32:
            v = ops[0].value
            what = DOS_INTS.get(v)
            if what is None and v == 0x80 and p.os == "windows":
                what = "Linux (32-bit)"
            if what:
                kind = {"windows": "Windows", "linux": "64-bit Linux" if mode == 64 else "Linux"}.get(p.os, p.os)
                self.add("ASM125", st, st.mcol, st.end_col, num=f"{v:X}h", what=what, what_ar=DOS_INTS_AR.get(what,
                                                                                                             what),
                         kind=kind)
                return

    # ------------------------------------------------------------ helpers of the checks
    def check_8086(self, st: Stmt) -> None:
        m, ops = st.mnem, st.ops
        what = what_ar = fix_txt = ""
        fixes = []
        if m == "push" and ops and ops[0].kind == "imm":
            what, what_ar = "push with a number", "دفع رقم مباشر (push)"
            fix_txt = f"mov ax, {ops[0].text} / push ax"
            fixes = [self.fix_lines(st, [f"mov ax, {ops[0].text}", "push ax"], "Push it through AX (changes AX)",
                                    "ادفعه عبر AX (يغيّر AX)")]
        elif m in SHIFTS and len(ops) == 2 and ops[1].kind == "imm" and ops[1].value not in (1, None):
            what = f"{m} by {ops[1].text}"
            what_ar = f"الإزاحة {m} بمقدار {ops[1].text}"
            fix_txt = f"mov cl, {ops[1].text} / {m} {ops[0].text}, cl"
            fixes = [self.fix_lines(st, [f"mov cl, {ops[1].text}", f"{st.raw} {ops[0].text}, cl"],
                                    "Shift by CL (changes CL)", "أزح بالمسجل CL (يغيّر CL)")]
        elif m in I186:
            what = what_ar = m.upper()
            fix_txt = "push / pop each register (or mov bp, sp)"
        elif m == "imul" and len(ops) >= 2:
            what, what_ar = "IMUL with 2 or 3 operands", "التعليمة IMUL بمعاملين أو ثلاثة"
            fix_txt = "mov ax, value / imul operand"
        elif m in I386:
            what = what_ar = f"{m.upper()} (80386)"
            fix_txt = "an 8086 instruction sequence"
        if what:
            self.add("ASM118", st, st.mcol, st.end_col, fixes, what=what, what_ar=what_ar, fix=fix_txt)

    def check_address(self, st: Stmt, o: Operand) -> bool:
        p = self.p
        mode = p.bits
        regs = list(o.regs)
        what = what_ar = ""
        what_rule = "ASM105"
        if o.bad == "segment-register-in-address":
            what = "a segment register cannot be part of an address (write es:[di])"
            what_ar = "مسجل المقطع لا يكون جزءاً من العنوان (اكتب es:[di])"
        elif o.bad == "too-many-registers":
            what = "at most two registers (base + index) can be used"
            what_ar = "يمكن استخدام مسجلين على الأكثر (أساس + فهرس)"
        elif o.bad == "negative-register":
            what = "a register cannot be subtracted inside an address"
            what_ar = "لا يمكن طرح مسجل داخل العنوان"
        elif any(GP[r][1] == 8 for r in regs):
            what = "8-bit registers cannot be used in an address"
            what_ar = "مسجلات الـ 8 بت لا تُستخدم في العناوين"
        if what:
            self.add(what_rule, st, o.col, o.end, op=o.text, what=what, what_ar=what_ar)
            return True
        sizes = {GP[r][1] for r in regs}
        if len(sizes) > 1:
            names = " and ".join(f"{s}-bit registers" for s in sorted(sizes))
            names_ar = " و ".join(f"مسجلات {s} بت" for s in sorted(sizes))
            self.add("ASM107", st, o.col, o.end, op=o.text, what=names, what_ar=names_ar)
            return True
        if not regs:
            return False
        asize = sizes.pop()
        if mode == 64 and asize == 16:
            self.add("ASM107", st, o.col, o.end, op=o.text, what="16-bit registers (not allowed in 64-bit code)",
                     what_ar="مسجلات 16 بت (غير مسموحة في كود 64 بت)")
            return True
        if asize == 16:
            allowed_base, allowed_index = {"bx", "bp"}, {"si", "di"}
            bad = [r for r in regs if r not in allowed_base | allowed_index]
            two_same = (len(regs) == 2 and (set(regs) <= allowed_base or set(regs) <= allowed_index))
            if bad or two_same or (o.index and o.scale not in (1,)):
                self.add("ASM106", st, o.col, o.end, op=o.text)
                return True
            return False
        if o.rel and regs:
            self.add("ASM105", st, o.col, o.end, op=o.text, what="RIP-relative addresses cannot add registers",
                     what_ar="العنوان النسبي لـ RIP لا يقبل إضافة مسجلات")
            return True
        if o.index and o.scale not in (1, 2, 4, 8, -1):
            if o.scale in (3, 5, 9) and not o.base and p.dialect in ("nasm", "fasm"):
                pass                                     # rewritten by the assembler as [r + r*2/4/8]
            else:
                self.add("ASM105", st, o.col, o.end, op=o.text,
                         what=f"the scale must be 1, 2, 4 or 8 (not {o.scale})",
                         what_ar=f"معامل الضرب يجب أن يكون 1 أو 2 أو 4 أو 8 (وليس {o.scale})")
                return True
        if o.index in ("esp", "rsp") and (o.scale not in (1,) or o.base in ("esp", "rsp")):
            self.add("ASM105", st, o.col, o.end, op=o.text, what=f"{o.index.upper()} cannot be an index register",
                     what_ar=f"المسجل {o.index.upper()} لا يمكن أن يكون مسجل فهرس")
            return True
        if mode == 64 and asize == 32 and st.mnem != "lea":
            new = o.text
            for r in regs:
                new = re.sub(r"(?<![\w%])(%?)" + r + r"\b", lambda mm, r=r: mm.group(1) + sibling(r, 64), new,
                             flags=re.I)
            fx = self.fix_replace_op(st, o, new, f"Use {new}", f"استخدم {new}")
            self.add("ASM119", st, o.col, o.end, [fx], op=o.text, hint=new)
            return True
        return False

    def check_segments(self, st: Stmt) -> bool:
        p = self.p
        m, ops = st.mnem, st.ops
        for o in ops:
            if o.bad == "override-on-register":
                self.add("ASM121", st, o.col, o.end, what=f"The segment override in {o.text} has no effect on a "
                                                           "register (it only applies to memory operands)",
                         what_ar=f"تغيير المقطع في {o.text} لا تأثير له على المسجل (يطبق على معاملات الذاكرة فقط)")
                return True
            if o.kind == "mem" and o.seg in ("cs", "ds", "es", "ss") and p.bits == 64:
                self.add("ASM121", st, o.col, o.end, what=f"The {o.seg.upper()}: override is ignored in 64-bit mode",
                         what_ar=f"تغيير المقطع {o.seg.upper()}: يتم تجاهله في وضع 64 بت")
                return True
            if o.kind == "mem" and p.bits == 16 and "bp" in o.regs and not o.seg and o.syms and m != "lea":
                d = p.resolve(o.syms[0], st.line, st.scope, st.proc)
                if d is not None and d.kind == "data":
                    self.add("ASM122", st, o.col, o.end, op=o.text)
                    return True
        sregs = [o for o in ops if o.kind == "sreg"]
        if not sregs:
            return False
        what = what_ar = ""
        fixes = []
        if m == "mov" and len(ops) == 2:
            d, s = ops
            if d.kind == "sreg" and s.kind == "imm":
                what = f"A number cannot be moved into {d.reg.upper()}"
                what_ar = f"لا يمكن نقل رقم مباشرة إلى {d.reg.upper()}"
                acc = "ax"
                fixes = [self.fix_lines(st, [f"mov {acc}, {s.text}", f"mov {d.text}, {acc}"],
                                        "Go through AX (changes AX)", "مرّ عبر AX (يغيّر AX)")]
            elif d.kind == "sreg" and s.kind == "sreg":
                what = f"{s.reg.upper()} cannot be moved directly into {d.reg.upper()}"
                what_ar = f"لا يمكن نقل {s.reg.upper()} مباشرة إلى {d.reg.upper()}"
                fixes = [self.fix_lines(st, [f"push {s.text}", f"pop {d.text}"], "Copy it with push / pop",
                                        "انسخه بـ push ثم pop")]
            elif d.kind == "sreg" and d.reg == "cs":
                what = "CS cannot be changed with MOV"
                what_ar = "لا يمكن تغيير CS بالتعليمة MOV"
        elif m == "pop" and ops and ops[0].kind == "sreg" and ops[0].reg == "cs":
            what, what_ar = "CS cannot be changed with POP", "لا يمكن تغيير CS بالتعليمة POP"
        elif m in ("push", "pop") and p.bits == 64 and ops[0].kind == "sreg" and ops[0].reg in ("cs", "ds", "es", "ss"):
            what = f"{m.upper()} {ops[0].reg.upper()} does not exist in 64-bit mode"
            what_ar = f"التعليمة {m.upper()} {ops[0].reg.upper()} غير موجودة في وضع 64 بت"
        elif m in ARITH_NO_SREG:
            what = f"{m.upper()} cannot work on the segment register {sregs[0].reg.upper()}"
            what_ar = f"التعليمة {m.upper()} لا تعمل على مسجل المقطع {sregs[0].reg.upper()}"
        elif p.cpu == "8086" and any(o.reg in ("fs", "gs") for o in sregs):
            what, what_ar = "FS and GS do not exist on the 8086", "المسجلان FS و GS غير موجودين في 8086"
        if what:
            self.add("ASM110", st, st.mcol, st.end_col, fixes, what=what, what_ar=what_ar)
            return True
        return False

    def check_movx(self, st: Stmt) -> bool:
        d, s = st.ops
        m = st.mnem
        if d.kind != "reg":
            self.add("ASM111", st, d.col, d.end, mnem=m.upper(), what="the destination must be a register",
                     what_ar="الوجهة يجب أن تكون مسجلاً")
            return True
        ss = s.size if s.kind in ("reg", "mem") else 0
        if not ss or not d.size:
            return False
        if ss >= d.size or ss == 32:
            fixes = []
            if ss == d.size:
                fixes = [self.fix_replace_mnem(st, "mov", "Use MOV", "استخدم MOV")]
                what, what_ar = "both operands have the same size", "المعاملان بنفس الحجم"
            elif ss == 32 and d.size == 64:
                if m == "movsx":
                    fixes = [self.fix_replace_mnem(st, "movsxd", "Use MOVSXD", "استخدم MOVSXD")]
                else:
                    d32 = sibling(d.reg, 32)
                    fixes = [Fix(f"Use mov {d32}, {s.text}", f"استخدم mov {d32}, {s.text}",
                                 [{"range": [st.line, st.mcol, st.line, st.mend], "text": "mov"},
                                  {"range": [st.line, d.col, st.line, d.end], "text": d32}])]
                what = "a 32-bit source needs MOVSXD (signed) or a 32-bit MOV (unsigned)"
                what_ar = "المصدر ذو الـ 32 بت يحتاج MOVSXD (بإشارة) أو MOV على 32 بت (بدون إشارة)"
            else:
                what = f"the source is {ss}-bit, the destination {d.size}-bit"
                what_ar = f"المصدر حجمه {ss} بت والوجهة {d.size} بت"
            self.add("ASM111", st, s.col, s.end, fixes, mnem=m.upper(), what=what, what_ar=what_ar)
            return True
        return False

    def check_push(self, st: Stmt, o: Operand) -> bool:
        p = self.p
        what = what_ar = ""
        fixes = []
        if o.kind == "reg" and o.size == 8:
            what, what_ar = "a byte register cannot be pushed", "لا يمكن دفع مسجل بحجم بايت"
            rep = sibling(o.reg, 64 if p.bits == 64 else 32 if p.bits == 32 else 16, p.bits)
            if rep and o.reg not in HIGH8:
                fixes = [self.fix_replace_op(st, o, rep, f"Use {rep.upper()}", f"استخدم {rep.upper()}")]
        elif o.kind == "reg" and p.bits == 64 and o.size == 32:
            what, what_ar = "32-bit registers cannot be pushed in 64-bit mode", "لا يمكن دفع مسجلات 32 بت في وضع 64 بت"
            rep = sibling(o.reg, 64)
            fixes = [self.fix_replace_op(st, o, rep, f"Use {rep.upper()}", f"استخدم {rep.upper()}")]
        elif o.kind == "mem" and o.explicit and (o.size == 8 or (p.bits == 64 and o.size == 32)):
            what = f"a {o.size}-bit memory value cannot be pushed in {p.bits}-bit mode"
            what_ar = f"لا يمكن دفع قيمة ذاكرة حجمها {o.size} بت في وضع {p.bits} بت"
        if what:
            self.add("ASM114", st, o.col, o.end, fixes, mnem=st.mnem.upper(), op=o.text, what=what, what_ar=what_ar)
            return True
        return False

    def memory_to_memory(self, st: Stmt) -> None:
        p = self.p
        d, s = st.ops[0], st.ops[1]
        size = d.size or s.size
        fixes = []
        if size in (8, 16, 32, 64) and st.mnem in ("mov", "add", "sub", "and", "or", "xor", "cmp", "adc", "sbb"):
            acc = {8: "al", 16: "ax", 32: "eax", 64: "rax"}[size]
            if not (p.bits == 16 and size > 16):
                if p.att:
                    lines = [f"mov{st.raw[-1] if st.suffix else ''} {s.text}, %{acc}",
                             f"{st.raw} %{acc}, {d.text}"]
                else:
                    lines = [f"mov {acc}, {s.text}", f"{st.raw} {d.text}, {acc}"]
                fixes = [self.fix_lines(st, lines, f"Go through {acc.upper()} (changes {acc.upper()})",
                                        f"مرّ عبر {acc.upper()} (يغيّر {acc.upper()})")]
        self.add("ASM103", st, st.mcol, st.end_col, fixes, mnem=st.mnem.upper())

    def size_mismatch(self, st: Stmt) -> bool:
        p = self.p
        d, s = st.ops
        if d.kind == "imm" or s.kind == "imm":
            return False
        if d.kind not in ("reg", "mem") or s.kind not in ("reg", "mem"):
            return False
        sd = d.size if (d.kind == "reg" or d.explicit or p.dialect in ("masm", "fasm")) else 0
        ss = s.size if (s.kind == "reg" or s.explicit or p.dialect in ("masm", "fasm")) else 0
        if not sd or not ss or sd == ss:
            return False
        if p.att and st.suffix:
            return False                                 # the suffix check reports it
        fixes = []
        m = st.mnem
        if d.kind == "reg" and s.kind == "reg":
            if m == "mov" and sd > ss and ss in (8, 16):
                fixes.append(self.fix_replace_mnem(st, "movzx", f"Use movzx {d.text}, {s.text} (unsigned)",
                                                   f"استخدم movzx {d.text}, {s.text} (بدون إشارة)"))
                fixes.append(self.fix_replace_mnem(st, "movsx", f"Use movsx {d.text}, {s.text} (signed)",
                                                   f"استخدم movsx {d.text}, {s.text} (بإشارة)"))
            elif m == "mov" and sd == 64 and ss == 32:
                fixes.append(self.fix_replace_mnem(st, "movsxd", f"Use movsxd {d.text}, {s.text} (signed)",
                                                   f"استخدم movsxd {d.text}, {s.text} (بإشارة)"))
                d32 = sibling(d.reg, 32)
                fixes.append(self.fix_replace_op(st, d, d32, f"Use mov {d32}, {s.text} (unsigned, clears the upper "
                                                             "half)", f"استخدم mov {d32}, {s.text} (بدون إشارة)"))
            rep = sibling(s.reg, sd, p.bits)
            if rep and s.reg not in HIGH8:
                prefix = "%" if p.att else ""
                fixes.append(self.fix_replace_op(st, s, prefix + rep, f"Use {rep.upper()} (same size as "
                                                                       f"{d.reg.upper()})",
                                                 f"استخدم {rep.upper()} (بنفس حجم {d.reg.upper()})"))
        elif d.kind == "mem" and s.kind == "reg" and d.explicit:
            fx = self.fix_size_word(st, d, ss)
            if fx:
                fixes.append(fx)
        elif s.kind == "mem" and d.kind == "reg":
            if s.explicit:
                fx = self.fix_size_word(st, s, sd)
                if fx:
                    fixes.append(fx)
            if m == "mov" and sd > ss and ss in (8, 16):
                fixes.append(self.fix_replace_mnem(st, "movzx", "Use MOVZX (unsigned widening)",
                                                   "استخدم MOVZX (توسيع بدون إشارة)"))
        a, b = (d, s)
        self.add("ASM101", st, st.mcol, st.end_col, fixes, a=a.text, sa=sd, b=b.text, sb=ss)
        return True

    def fix_size_word(self, st: Stmt, o: Operand, bits: int) -> Fix | None:
        line = self.p.lines[st.line]
        seg = line[o.col:o.end]
        mm = re.search(r"\b(byte|word|dword|qword|tword|oword|xmmword|ymmword)\b", seg, re.I)
        if not mm:
            return None
        new = {8: "byte", 16: "word", 32: "dword", 64: "qword"}.get(bits)
        if not new:
            return None
        return Fix(f"Change the size to {new}", f"غيّر الحجم إلى {new}",
                   [{"range": [st.line, o.col + mm.start(), st.line, o.col + mm.end()], "text": new}])

    def ambiguous(self, st: Stmt) -> bool:
        p = self.p
        m, ops = st.mnem, st.ops
        if m in ("movzx", "movsx"):
            if len(ops) != 2 or ops[1].kind != "mem":
                return False
            target = ops[1]
            if target.size:
                return False
            sizes = [8, 16]
        else:
            givers = [o for i, o in enumerate(ops) if o.kind == "reg" and not (m in SHIFTS and i == 1)]
            if givers:
                return False
            if m in ("imul",) and len(ops) > 1:
                return False
            target = next((o for o in ops if o.kind == "mem"), None)
            if target is None or target.size:
                return False
            sizes = [8, 16] if p.bits == 16 else [8, 16, 32] + ([64] if p.bits == 64 else [])
        if p.dialect in ("masm", "fasm") and target.syms:
            d = p.resolve(target.syms[0], st.line, st.scope, st.proc)
            if d is None or d.kind != "data" or not d.size:
                return False                 # a parameter / local / structure field the assembler knows the size of
        if p.att:
            if st.suffix:
                return False
            hint = f"{st.raw}b / {st.raw}w / {st.raw}l" + (f" / {st.raw}q" if p.bits == 64 else "")
            fixes = [self.fix_replace_mnem(st, st.raw + {8: "b", 16: "w", 32: "l", 64: "q"}[b],
                                           f"Use {st.raw + {8: 'b', 16: 'w', 32: 'l', 64: 'q'}[b]} ({b}-bit)",
                                           f"استخدم {st.raw + {8: 'b', 16: 'w', 32: 'l', 64: 'q'}[b]} ({b} بت)")
                     for b in self._size_order(st, sizes)]
            self.add("ASM102", st, target.col, target.end, fixes, op=target.text, hint=hint)
            return True
        words = [size_word(p, b) for b in self._size_order(st, sizes)]
        fixes = [Fix(f"{w} ({b}-bit)", f"{w} ({b} بت)",
                     [{"range": [st.line, target.col, st.line, target.col], "text": w + " "}])
                 for w, b in zip(words, self._size_order(st, sizes))]
        self.add("ASM102", st, target.col, target.end, fixes, op=target.text,
                 hint=" / ".join(f"{w} {target.text}" for w in words[:3]))
        return True

    def _size_order(self, st: Stmt, sizes: list[int]) -> list[int]:
        imm = next((o for o in st.ops if o.kind == "imm" and o.value is not None), None)
        default = 16 if self.p.bits == 16 else 32
        pref = [default] + [b for b in (16, 8, 32, 64) if b != default]
        order = [b for b in pref if b in sizes]
        if imm is not None:
            v = imm.value
            fit = [b for b in order if -(1 << (b - 1)) <= v < (1 << b)]
            order = fit + [b for b in order if b not in fit]
        return order

    def immediate_range(self, st: Stmt) -> None:
        p = self.p
        m, ops = st.mnem, st.ops
        if m == "int" and ops and ops[0].kind == "imm" and ops[0].value is not None:
            v = ops[0].value
            if not 0 <= v <= 255:
                self.add("ASM104", st, ops[0].col, ops[0].end, value=_n(v), bits=8, lo=0, hi=255)
            return
        if m in ("ret", "retn", "retf") and ops and ops[0].kind == "imm" and ops[0].value is not None:
            v = ops[0].value
            if not 0 <= v <= 0xFFFF:
                self.add("ASM104", st, ops[0].col, ops[0].end, value=_n(v), bits=16, lo=0, hi=65535)
            return
        if m in ("in", "out") and len(ops) == 2:
            port = ops[1] if m == "in" else ops[0]
            if port.kind == "imm" and port.value is not None and not 0 <= port.value <= 255:
                self.add("ASM104", st, port.col, port.end, value=_n(port.value), bits=8, lo=0, hi=255)
            return
        if m in SHIFTS and len(ops) == 2 and ops[1].kind == "imm" and ops[1].value is not None:
            c = ops[1].value
            sz = ops[0].size
            lim = 64 if sz == 64 else 32
            if c < 0 or c >= lim:
                self.add("ASM123", st, ops[1].col, ops[1].end, bits=sz or p.bits, count=c,
                         what=f"keeps only {c % lim} of it", what_ar=f"يبقي منه {c % lim} فقط")
            return
        if m == "push" and ops and ops[0].kind == "imm" and ops[0].value is not None:
            v = ops[0].value
            bits = 32 if p.bits == 64 else p.bits
            lo, hi = (-(1 << 31), (1 << 31) - 1) if p.bits == 64 else (-(1 << (bits - 1)), (1 << bits) - 1)
            if not lo <= v <= hi:
                self.add("ASM104", st, ops[0].col, ops[0].end, value=_n(v), bits=bits, lo=_n(lo), hi=_n(hi))
            return
        if len(ops) < 2 or m not in SAME_SIZE | {"imul"}:
            return
        dst = ops[0]
        imm = ops[-1]
        if imm.kind != "imm" or imm.value is None:
            return
        size = dst.size if dst.kind in ("reg", "mem") else 0
        if not size or size not in (8, 16, 32, 64):
            return
        v = imm.value
        if size == 64:
            if m == "mov" and dst.kind == "reg":
                lo, hi = -(1 << 63), (1 << 64) - 1
            else:
                lo, hi = -(1 << 31), (1 << 31) - 1
            bits = 64 if (m == "mov" and dst.kind == "reg") else 32
        else:
            lo, hi = -(1 << (size - 1)), (1 << size) - 1
            bits = size
        if lo <= v <= hi:
            return
        fixes = []
        if size == 64 and m != "mov" and -(1 << 63) <= v < (1 << 64) and not p.att:
            fixes = [self.fix_lines(st, [f"mov rax, {imm.text}", f"{st.raw} {dst.text}, rax"],
                                    "Load the constant into RAX first (changes RAX)",
                                    "حمّل الثابت في RAX أولاً (يغيّر RAX)")] if dst.reg != "rax" else []
        self.add("ASM104", st, imm.col, imm.end, fixes, value=_n(v), bits=bits,
                 lo=_n(lo) if bits < 64 else "-2^63", hi=_n(hi) if bits < 64 else "2^64-1")


def size_bits_from_word(w: str) -> int:
    return SIZE_WORDS.get(w.lower(), 0)


def check_operands(prog: Program, out: list) -> None:
    OperandChecks(prog, out).run()

