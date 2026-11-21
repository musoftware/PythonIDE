"""Pure helpers of the CPU view and of the live source editor (no Qt, unit-testable).

Source text (any dialect radide/asm_intel knows: nasm / masm / fasm / gas, Intel or AT&T):

* ``source_jumps(text, dialect)``   jmp / jcc / loop / call -> target label lines (jump arrows in the gutter)
* ``register_refs(text, dialect)``  every register token with "r" / "w" / "rw" (highlight reads and writes)
* ``proc_ranges(text, dialect)``    (first, last) line of every procedure / global label body
* ``inline_values(line, ...)``      "rax=0x5  rbx=0x7  ZF=1" for one executed line

Machine code (capstone, x86 16 / 32 / 64-bit):

* ``decode(data, address, bits)`` / ``decode_window(...)``  instructions with jump targets, kinds and memory operands
* ``jump_taken(mnemonic, flags, regs, bits)``  will this conditional jump / loop be taken?
* ``effective_address(ins, regs, ...)``  [rbx+8] -> 0x...
* ``is_return_address(before, bits)`` / ``string_at(data)``  stack annotations
* ``assemble_native(text, address, bits)`` / ``assemble_8086(text, cs, ip)``  one instruction -> bytes
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .. import isa
from ..index import mask, parse

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# x86 flag bits (EFLAGS / the 8086 FLAGS word)
FLAG_BITS = {"CF": 0, "PF": 2, "AF": 4, "ZF": 6, "SF": 7, "TF": 8, "IF": 9, "DF": 10, "OF": 11}
FLAG_ORDER = ("CF", "PF", "AF", "ZF", "SF", "TF", "IF", "DF", "OF")

_CONDS: dict[str, str] = {}               # every condition spelling -> canonical (isa.CONDITIONS)
for _c, _d, _f, _aliases in isa.CONDITIONS:
    _CONDS[_c] = _c
    for _a in _aliases:
        _CONDS[_a] = _c
JCC = {"j" + c for c in _CONDS}
LOOPS = {"loop", "loope", "loopz", "loopne", "loopnz", "jcxz", "jecxz", "jrcxz"}
JUMPS = {"jmp", "call"} | JCC | LOOPS
SIZE_WORDS = {"short", "near", "far", "ptr", "byte", "word", "dword", "qword", "tword", "rel", "abs", "strict", "dq",
              "offset", "large", "small"}

_LABEL = re.compile(r"^\s*([A-Za-z_.?@$][\w.?@$]*)\s*:(?!=)")
_WORD = re.compile(r"%?[A-Za-z_.?@$][\w.?@$]*")


def flag(flags: int, name: str) -> int:
    return (int(flags) >> FLAG_BITS[name]) & 1


# ====================================================================== instruction splitting (source)
@dataclass
class SrcIns:
    line: int
    mnemonic: str             # lower case, prefixes (rep / lock) removed
    mn_col: int
    operands: list[tuple[str, int]]    # (text, start column) of each top-level operand


def split_operands(text: str, start: int) -> list[tuple[str, int]]:
    """'eax, [ebx+4], 3' -> [('eax', s), ('[ebx+4]', s+5), ('3', s+14)] (commas inside [] / () kept)."""
    out, depth, cur0 = [], 0, 0
    for i, ch in enumerate(text + ","):
        if ch in "[(":
            depth += 1
        elif ch in "])":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            piece = text[cur0:i]
            lead = len(piece) - len(piece.lstrip())
            if piece.strip():
                out.append((piece.strip(), start + cur0 + lead))
            cur0 = i + 1
    return out


def instruction_of(masked: str, line: int) -> SrcIns | None:
    """The instruction of one masked source line (labels and prefixes skipped), or None."""
    pos = 0
    while True:
        m = _LABEL.match(masked, pos)
        if not m:
            break
        pos = m.end()
    m = _WORD.search(masked, pos)
    if not m or masked[pos:m.start()].strip():
        return None
    mn = m.group().lower()
    while mn in ("rep", "repe", "repz", "repne", "repnz", "lock", "data16", "addr32"):
        m2 = _WORD.search(masked, m.end())
        if not m2:
            break
        m, mn = m2, m2.group().lower()
    if mn.startswith(".") or mn in ("db", "dw", "dd", "dq", "dt", "resb", "resw", "resd", "resq", "equ", "proc",
                                    "endp", "segment", "ends", "section", "global", "extern", "times"):
        return None
    rest = masked[m.end():]
    if re.match(r"\s*(proc|endp|equ|db|dw|dd|dq|dt|label|struc|ends|macro|=)\b", rest, re.I):
        return None          # "name proc" / "name db 5" (MASM): the first word was a name
    return SrcIns(line, mn, m.start(), split_operands(rest, m.end()))


def instructions(text: str, dialect: str) -> list[SrcIns]:
    out = []
    for i, ln in enumerate(mask(text, dialect)):
        ins = instruction_of(ln, i)
        if ins is not None:
            out.append(ins)
    return out


# ====================================================================== jump arrows in the source
@dataclass
class Jump:
    src: int                 # 0-based line of the jump
    dst: int                 # 0-based line of the target label
    kind: str                # jmp | jcc | loop | call
    mnemonic: str
    label: str


def _label_target(op: str, att: bool) -> str:
    words = [w for w in re.split(r"\s+", op.strip()) if w]
    while words and words[0].lower() in SIZE_WORDS:
        words.pop(0)
    if len(words) != 1:
        return ""
    w = words[0]
    if att and w.startswith(("*", "%", "$")):
        return ""
    if w.startswith("[") or isa.register(w) is not None or not re.fullmatch(r"[A-Za-z_.?@$][\w.?@$]*", w):
        return ""
    return w


def _resolver(text: str, dialect: str):
    mod = parse(text, dialect)
    exact: dict[str, list] = {}
    for s in mod.symbols:
        if s.kind in ("label", "local", "proc"):
            exact.setdefault(s.name.lower() if dialect != "nasm" else s.name, []).append(s)
    globals_ = sorted((s.line, s.name) for s in mod.symbols if s.kind in ("label", "proc"))

    def parent_at(line: int) -> str:
        cur = ""
        for ln, name in globals_:
            if ln > line:
                break
            cur = name
        return cur

    def resolve(name: str, line: int) -> int | None:
        key = name if dialect == "nasm" else name.lower()
        cands = exact.get(key) or []
        if not cands and dialect == "nasm" and "." in name.lstrip("."):        # main.next -> .next of main
            parent, _dot, local = name.partition(".")
            cands = [s for s in exact.get("." + local, []) if s.parent == parent]
        if not cands:
            return None
        if name.startswith(".") or (dialect != "nasm" and len(cands) > 1):
            par = parent_at(line)
            own = [s for s in cands if s.parent == par]
            if own:
                return own[0].line
        return cands[0].line
    return resolve


def source_jumps(text: str, dialect: str = "nasm") -> list[Jump]:
    """Every jmp / jcc / loop / call whose target is a label of the same file."""
    att = dialect == "gas" and not re.search(r"^\s*\.intel_syntax", text, re.M)
    resolve = _resolver(text, dialect)
    out = []
    for ins in instructions(text, dialect):
        mn = ins.mnemonic
        if att and mn not in JUMPS and mn[:-1] in JUMPS and mn[-1] in "lqw":
            mn = mn[:-1]              # callq / jmpq
        if mn not in JUMPS or len(ins.operands) != 1:
            continue
        name = _label_target(ins.operands[0][0], att)
        if not name:
            continue
        dst = resolve(name, ins.line)
        if dst is None:
            continue
        kind = "jmp" if mn == "jmp" else "call" if mn == "call" else "loop" if mn in LOOPS else "jcc"
        out.append(Jump(ins.line, dst, kind, mn, name))
    return out


def arrow_lanes(jumps: list[Jump]) -> list[tuple[Jump, int]]:
    """A lane (0 = closest to the code) per jump so that overlapping arrows do not share a column."""
    spans = sorted(jumps, key=lambda j: abs(j.dst - j.src))
    lanes: list[list[tuple[int, int]]] = []
    out = []
    for j in spans:
        lo, hi = min(j.src, j.dst), max(j.src, j.dst)
        for k, used in enumerate(lanes):
            if all(hi < a or lo > b for a, b in used):
                used.append((lo, hi))
                out.append((j, k))
                break
        else:
            lanes.append([(lo, hi)])
            out.append((j, len(lanes) - 1))
    return out


# ====================================================================== register reads / writes
@dataclass
class RegRef:
    line: int
    col: int
    end: int
    name: str                # as written (lower case, no %)
    family: str              # rax for al / ax / eax / rax ...
    kind: str                # r | w | rw


WRITE_ONLY = {"mov", "movzx", "movsx", "movsxd", "lea", "pop", "in", "movd", "movq", "movss", "movsd", "movaps",
              "movups", "movapd", "movupd", "movdqa", "movdqu", "cvtsi2sd", "cvtsi2ss", "cvttsd2si", "cvttss2si",
              "cvtsd2si", "cvtss2si", "lds", "les", "lfs", "lgs", "lss", "rdtsc", "cpuid", "lahf"}
READ_ONLY = {"cmp", "test", "push", "out", "jmp", "call", "bt", "ucomiss", "ucomisd", "comiss", "comisd", "mul",
             "div", "idiv", "int", "ret", "retn", "retf", "enter", "ptest", "loop", "loope", "loopz", "loopne",
             "loopnz", "jcxz", "jecxz", "jrcxz"} | JCC
BOTH_RW = {"xchg", "xadd", "cmpxchg"}
SINGLE_RW = {"inc", "dec", "neg", "not", "bswap"}


def _dest_kind(mn: str, n_ops: int) -> str:
    if mn in READ_ONLY:
        return "r"
    if mn in WRITE_ONLY or mn.startswith(("set", "cmov")):
        return "w"
    if mn == "imul" and n_ops == 3:
        return "w"
    if mn == "imul" and n_ops == 1:
        return "r"
    if n_ops == 1:
        return "rw" if mn in SINGLE_RW else "r"
    return "rw"


def register_refs(text: str, dialect: str = "nasm") -> list[RegRef]:
    att = dialect == "gas" and not re.search(r"^\s*\.intel_syntax", text, re.M)
    out = []
    for ins in instructions(text, dialect):
        mn = ins.mnemonic
        if att and mn not in isa.INSTRUCTIONS and mn[:-1] in isa.INSTRUCTIONS:
            mn = mn[:-1]
        ops = list(ins.operands)
        n = len(ops)
        dest_i = (n - 1) if att else 0
        dkind = _dest_kind(mn, n)
        zero_idiom = mn in ("xor", "sub", "pxor", "xorps") and n == 2 and ops[0][0].lower() == ops[1][0].lower()
        for i, (op, start) in enumerate(ops):
            depth = 0
            for m in re.finditer(r"[\[\]()]|%?[A-Za-z][A-Za-z0-9]*", op):
                tok = m.group()
                if tok in "[(":
                    depth += 1
                    continue
                if tok in "])":
                    depth = max(0, depth - 1)
                    continue
                reg = isa.register(tok)
                if reg is None or reg.name in ("st",):
                    continue
                if depth:
                    kind = "r"                                # an address: always read
                elif zero_idiom:
                    kind = "w"                                # xor eax, eax: the old value does not matter
                elif mn in BOTH_RW:
                    kind = "rw"
                elif i == dest_i:
                    kind = dkind
                else:
                    kind = "r"
                out.append(RegRef(ins.line, start + m.start(), start + m.end(), reg.name, reg.family, kind))
    return out


def refs_in_range(refs: list[RegRef], family: str, first: int, last: int) -> list[RegRef]:
    return [r for r in refs if r.family == family and first <= r.line <= last]


def proc_ranges(text: str, dialect: str = "nasm") -> list[tuple[int, int, str]]:
    """(first line, last line, name) of every procedure (PROC .. ENDP) and global label body."""
    mod = parse(text, dialect)
    n_lines = text.count("\n") + 1
    heads = sorted((s.line, s.name, s.kind, s.end_line) for s in mod.symbols if s.kind in ("label", "proc"))
    sections = sorted(s.line for s in mod.symbols if s.kind == "section")
    out = []
    for k, (line, name, kind, end) in enumerate(heads):
        nxt = heads[k + 1][0] - 1 if k + 1 < len(heads) else n_lines - 1
        sec = next((s - 1 for s in sections if s > line), n_lines - 1)
        last = end if kind == "proc" and end >= line else min(nxt, sec)
        out.append((line, max(line, last), name))
    return out


def proc_at(ranges, line: int) -> tuple[int, int]:
    best = None
    for a, b, _n in ranges:
        if a <= line <= b and (best is None or b - a < best[1] - best[0]):
            best = (a, b)
    return best or (0, 1 << 30)


# ====================================================================== live values
def normalize_registers(regs: dict) -> dict[str, int]:
    """{'RAX': 5, 'eflags': 0x246, 'AX': ...} -> {'rax': 5, 'rflags': 0x246} keyed by register family."""
    out: dict[str, int] = {}
    sizes: dict[str, int] = {}
    for name, val in (regs or {}).items():
        if val is None:
            continue
        r = isa.register(str(name))
        if r is None:
            continue
        if r.name in ("ah", "bh", "ch", "dh", "al", "bl", "cl", "dl"):
            continue
        if r.size >= sizes.get(r.family, 0):
            out[r.family] = int(val)
            sizes[r.family] = r.size
    return out


def sub_value(name: str, fam_values: dict[str, int]) -> int | None:
    r = isa.register(name)
    if r is None or r.family not in fam_values:
        return None
    v = fam_values[r.family]
    if r.name in ("ah", "bh", "ch", "dh"):
        return (v >> 8) & 0xFF
    if r.size >= 64:
        return v & ((1 << r.size) - 1)
    return v & ((1 << r.size) - 1)


def flags_written(mnemonic: str) -> list[str]:
    ins = isa.instruction(mnemonic)
    if ins is None:
        return []
    out, kind = [], "w"
    for part in (ins.flags or "").split():
        if ":" in part:
            kind, part = part.split(":", 1)
        if kind in ("w", "0", "1") and part in FLAG_BITS and part not in out:
            out.append(part)
    return [f for f in FLAG_ORDER if f in out and f not in ("AF", "PF")] or [f for f in FLAG_ORDER if f in out]


def fmt_hex(v: int) -> str:
    return f"0x{v:X}"


def inline_values(line_text: str, dialect: str, fam_values: dict[str, int], flags: int | None = None,
                  limit: int = 6) -> str:
    """'add rax, rbx' + values -> 'rax=0x5  rbx=0x7  ZF=0 CF=0' (empty when the line has no instruction)."""
    masked = mask(line_text, dialect)[0]
    ins = instruction_of(masked, 0)
    if ins is None:
        return ""
    seen, parts = set(), []
    for m in re.finditer(r"%?[A-Za-z][A-Za-z0-9]*", masked[ins.mn_col + len(ins.mnemonic):]):
        tok = m.group().lstrip("%").lower()
        if tok in seen or isa.register(tok) is None:
            continue
        seen.add(tok)
        v = sub_value(tok, fam_values)
        if v is not None:
            parts.append(f"{tok}={fmt_hex(v)}")
        if len(parts) >= limit:
            break
    if flags is not None:
        mn = ins.mnemonic
        fl = flags_written(mn)
        if mn in JCC or mn in LOOPS:
            cond = _CONDS.get(mn[1:]) if mn in JCC else None
            fl = [f for c, _d, fs, _a in isa.CONDITIONS if c == cond for f in fs.split()] if cond else []
        if fl:
            parts.append(" ".join(f"{f}={flag(flags, f)}" for f in fl))
    return "  ".join(parts)


def value_formats(v: int, bits: int) -> dict[str, str]:
    """hex / unsigned / signed / char texts of a register value (hover)."""
    bits = max(8, int(bits or 64))
    v &= (1 << bits) - 1
    signed = v - (1 << bits) if v >> (bits - 1) else v
    chars = []
    for k in range(min(bits // 8, 8)):
        b = (v >> (8 * k)) & 0xFF
        chars.append(chr(b) if 32 <= b < 127 else ".")
    return {"hex": f"0x{v:0{bits // 4}X}", "dec": str(v), "signed": str(signed),
            "char": "'" + "".join(chars).rstrip(".")[:8] + "'" if any(c != "." for c in chars) else "-"}


# ====================================================================== conditional jumps
def condition_of(mnemonic: str) -> str | None:
    mn = mnemonic.lower()
    if mn in JCC:
        return _CONDS[mn[1:]]
    return None


def jump_taken(mnemonic: str, flags: int, fam_values: dict[str, int] | None = None, bits: int = 64) -> bool | None:
    """True / False for a conditional jump or LOOP with these flags / counter, None when not conditional."""
    mn = mnemonic.lower()
    f = lambda n: flag(flags, n)  # noqa: E731
    cond = condition_of(mn)
    if cond is not None:
        return {
            "o": f("OF") == 1, "no": f("OF") == 0, "b": f("CF") == 1, "ae": f("CF") == 0,
            "e": f("ZF") == 1, "ne": f("ZF") == 0, "be": f("CF") == 1 or f("ZF") == 1,
            "a": f("CF") == 0 and f("ZF") == 0, "s": f("SF") == 1, "ns": f("SF") == 0, "p": f("PF") == 1,
            "np": f("PF") == 0, "l": f("SF") != f("OF"), "ge": f("SF") == f("OF"),
            "le": f("ZF") == 1 or f("SF") != f("OF"), "g": f("ZF") == 0 and f("SF") == f("OF")}[cond]
    if mn in LOOPS:
        rcx = (fam_values or {}).get("rcx")
        if rcx is None:
            return None
        if mn == "jrcxz":
            return rcx == 0
        if mn == "jecxz":
            return rcx & 0xFFFFFFFF == 0
        width = 16 if bits == 16 else 32 if bits == 32 else 64
        if mn == "jcxz":
            return rcx & 0xFFFF == 0
        after = (rcx - 1) & ((1 << width) - 1)
        if mn in ("loope", "loopz"):
            return after != 0 and f("ZF") == 1
        if mn in ("loopne", "loopnz"):
            return after != 0 and f("ZF") == 0
        return after != 0
    return None


def condition_text(mnemonic: str) -> str:
    cond = condition_of(mnemonic)
    for c, desc, _f, _a in isa.CONDITIONS:
        if c == cond:
            return desc
    return ""


# ====================================================================== machine code (capstone)
@dataclass
class Ins:
    address: int             # linear address
    size: int
    raw: bytes
    mnemonic: str
    op_str: str
    kind: str = ""           # jmp | jcc | loop | call | ret | int | ''
    target: int | None = None
    mems: list = field(default_factory=list)       # [(segment, base, index, scale, disp)] lower-case names
    imms: list = field(default_factory=list)
    rip_next: int = 0        # address of the next instruction (rip-relative operands)

    @property
    def text(self) -> str:
        return f"{self.mnemonic} {self.op_str}".strip()

    @property
    def hexbytes(self) -> str:
        return self.raw.hex(" ").upper()


_CS: dict[int, object] = {}


def capstone_ok() -> bool:
    import importlib.util
    return importlib.util.find_spec("capstone") is not None


def _cs(bits: int):
    if bits not in _CS:
        from capstone import CS_ARCH_X86, CS_MODE_16, CS_MODE_32, CS_MODE_64, Cs
        md = Cs(CS_ARCH_X86, {16: CS_MODE_16, 32: CS_MODE_32}.get(bits, CS_MODE_64))
        md.detail = True
        md.skipdata = True
        _CS[bits] = md
    return _CS[bits]


def _convert(ci, bits: int, seg_base: int) -> Ins:
    from capstone import CS_GRP_CALL, CS_GRP_INT, CS_GRP_JUMP, CS_GRP_RET
    from capstone import x86_const as X
    mn = ci.mnemonic.lower()
    lin = seg_base + ci.address if bits == 16 else ci.address
    ins = Ins(lin, ci.size, bytes(ci.bytes), mn, ci.op_str, rip_next=ci.address + ci.size)
    if mn.startswith("."):           # skipdata
        ins.mnemonic, ins.op_str = "db", ", ".join(f"0x{b:02X}" for b in ci.bytes)
        return ins
    try:
        groups = set(ci.groups)
        ops = list(ci.operands)
    except Exception:  # noqa: BLE001 - no detail for this instruction
        return ins
    if CS_GRP_RET in groups:
        ins.kind = "ret"
    elif CS_GRP_CALL in groups:
        ins.kind = "call"
    elif CS_GRP_JUMP in groups:
        ins.kind = "jmp" if mn in ("jmp", "ljmp") else "loop" if mn in LOOPS else "jcc"
    elif CS_GRP_INT in groups:
        ins.kind = "int"
    if not ins.kind:                 # capstone does not put LOOP / JCXZ in the jump group
        if mn in LOOPS:
            ins.kind = "loop"
        elif mn in JCC:
            ins.kind = "jcc"
        elif mn == "jmp":
            ins.kind = "jmp"
    for op in ops:
        if op.type == X.X86_OP_IMM:
            ins.imms.append(op.imm)
        elif op.type == X.X86_OP_MEM:
            m = op.mem
            name = lambda r: ci.reg_name(r) if r else ""  # noqa: E731
            ins.mems.append((name(m.segment), name(m.base), name(m.index), m.scale, m.disp))
    if ins.kind in ("jmp", "jcc", "loop", "call") and ops:
        if len(ops) == 2 and all(o.type == X.X86_OP_IMM for o in ops):          # far ptr seg:off
            ins.target = ((ops[0].imm << 4) + ops[1].imm) & 0xFFFFF
        elif ops[0].type == X.X86_OP_IMM:
            t = ops[0].imm
            ins.target = (seg_base + (t & 0xFFFF)) if bits == 16 else t
    return ins


def decode(data: bytes, address: int, bits: int = 64, seg_base: int = 0, count: int = 0) -> list[Ins]:
    """Instructions of *data* loaded at *address* (linear). 16-bit code: offsets inside the segment at
    *seg_base* (jump targets are converted back to linear addresses)."""
    md = _cs(bits)
    start = (address - seg_base) & 0xFFFF if bits == 16 else address
    out = []
    for ci in md.disasm(bytes(data), start):
        out.append(_convert(ci, bits, seg_base))
        if count and len(out) >= count:
            break
    return out


def decode_window(data: bytes, start: int, pc: int, bits: int = 64, seg_base: int = 0) -> list[Ins]:
    """Decode *data* (loaded at *start*, covering bytes before *pc*) so that one instruction starts exactly at
    *pc*: the earliest start offset whose linear decoding lands on *pc* wins (x86 cannot be decoded backwards)."""
    back = pc - start
    if back <= 0:
        return decode(data, start, bits, seg_base)
    for off in range(0, min(back, 64) + 1):
        lead = decode(data[off:back + 16], start + off, bits, seg_base)
        a = start + off
        ok = False
        for ins in lead:
            if a == pc:
                ok = True
                break
            if a > pc:
                break
            a += ins.size
        if ok and not any(i.mnemonic == "db" for i in lead if i.address < pc):
            full = decode(data[off:], start + off, bits, seg_base)
            return full
    return decode(data[back:], pc, bits, seg_base)


_REG16 = {"bx", "bp", "si", "di"}


def effective_address(ins: Ins, fam_values: dict[str, int], bits: int = 64, segs: dict[str, int] | None = None
                      ) -> int | None:
    """The address of the first memory operand of *ins* with these register values (None: none / unknown)."""
    if not ins.mems:
        return None
    seg, base, index, scale, disp = ins.mems[0]
    a = disp
    for r, mul in ((base, 1), (index, scale or 1)):
        if not r:
            continue
        if r in ("rip", "eip"):
            a += ins.rip_next
            continue
        v = sub_value(r, fam_values)
        if v is None:
            return None
        a += v * mul
    if bits == 16:
        segs = segs or {}
        s = seg or ("ss" if base in ("bp", "sp") else "ds")
        return ((segs.get(s, 0) << 4) + (a & 0xFFFF)) & 0xFFFFF
    return a & ((1 << (32 if bits == 32 else 64)) - 1)


def is_return_address(before: bytes, bits: int = 64) -> bool:
    """True when the bytes just before an address end with a CALL instruction (the address is a return
    address pushed by that call)."""
    if not capstone_ok():
        return False
    md = _cs(bits)
    for k in (5, 2, 3, 6, 7, 4):
        if len(before) < k:
            continue
        chunk = bytes(before[-k:])
        try:
            got = list(md.disasm(chunk, 0, 1))
        except Exception:  # noqa: BLE001
            continue
        if got and got[0].size == k and got[0].mnemonic.lower().startswith(("call", "lcall")):
            return True
    return False


def string_at(data: bytes, min_len: int = 4) -> tuple[str, str] | None:
    """('ASCII', text) / ('UNICODE', text) when *data* starts with a printable string."""
    def printable(b):
        return 32 <= b < 127 or b in (9, 10, 13)
    n = 0
    while n < len(data) and printable(data[n]):
        n += 1
    if n >= min_len and (n == len(data) or data[n] == 0 or n >= 16):
        return "ASCII", data[:n].decode("ascii", "replace")
    chars = []
    for i in range(0, len(data) - 1, 2):
        lo, hi = data[i], data[i + 1]
        if hi == 0 and printable(lo):
            chars.append(chr(lo))
        else:
            break
    if len(chars) >= min_len:
        return "UNICODE", "".join(chars)
    return None


def esc(text: str, limit: int = 40) -> str:
    t = text.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
    return t[:limit] + ("..." if len(t) > limit else "")


# ====================================================================== one-line assemblers
def _nasm() -> str:
    try:
        from ...nativedbg import find_nasm
        return find_nasm()
    except Exception:  # noqa: BLE001
        return ""


def gdb_to_nasm(text: str) -> str:
    """gdb's Intel syntax -> NASM: 'QWORD PTR [rip+0x10]' -> 'qword [rip+0x10]', 'BYTE PTR ds:...'."""
    t = re.sub(r"\bptr\b", "", text, flags=re.I)
    t = re.sub(r"\b(ds|es|ss|cs):\[", r"[\1:", t, flags=re.I)
    t = re.sub(r"\s*#.*$", "", t)
    t = re.sub(r"\s*<[^>]*>", "", t)
    return re.sub(r"\s{2,}", " ", t).strip()


def assemble_native(text: str, address: int, bits: int = 64) -> tuple[bytes | None, str]:
    """Assemble one or more NASM instructions (';' or newlines between them) for *address* -> (bytes, error)."""
    nasm = _nasm()
    if not nasm:
        return None, "NASM was not found (Tools > Assembly Toolchains)."
    lines = [gdb_to_nasm(x) for x in re.split(r"[\n;]", text) if x.strip()]
    if not lines:
        return None, "empty"
    rip = re.compile(r"\[\s*rip\s*([+-])\s*(0x[0-9a-fA-F]+|\d+)\s*\]", re.I)
    if bits == 64 and len(lines) == 1 and rip.search(lines[0]):
        # [rip+disp] is relative to the NEXT instruction; NASM wants the target ([rel address]). The length of the
        # instruction does not depend on the target: assemble once to learn it, then again with the real target.
        def to_rel(size):
            def sub(m):
                disp = int(m.group(2), 0) * (1 if m.group(1) == "+" else -1)
                off = size + disp                  # target - org; $$ (= org) keeps it relocatable for 'rel'
                return f"[rel $$ {'+' if off >= 0 else '-'} 0x{abs(off):X}]"
            return rip.sub(sub, lines[0])
        first, err = _nasm_bin(nasm, [to_rel(7)], address, bits)
        if first is None:
            return None, err
        return _nasm_bin(nasm, [to_rel(len(first))], address, bits)
    return _nasm_bin(nasm, lines, address, bits)


def _nasm_bin(nasm: str, lines: list[str], address: int, bits: int) -> tuple[bytes | None, str]:
    d = Path(tempfile.mkdtemp(prefix="radide_cpuasm_"))
    src, out = d / "a.asm", d / "a.bin"
    src.write_text(f"bits {bits}\norg 0x{address:X}\n" + "\n".join(lines) + "\n", encoding="utf-8")
    try:
        r = subprocess.run([nasm, "-f", "bin", "-o", str(out), str(src)], capture_output=True, text=True,
                           timeout=20, creationflags=NO_WINDOW, errors="replace")
        if r.returncode != 0 or not out.exists():
            msg = " ".join(re.sub(r"^.*?:\d+:\s*", "", ln) for ln in (r.stderr or r.stdout).splitlines() if ln.strip())
            return None, msg or "assembly failed"
        return out.read_bytes(), ""
    except (OSError, subprocess.SubprocessError) as e:
        return None, str(e)
    finally:
        for p in (src, out):
            try:
                p.unlink()
            except OSError:
                pass
        try:
            os.rmdir(d)
        except OSError:
            pass


def assemble_8086(text: str, cs: int, ip: int, lang: str = "en") -> tuple[bytes | None, str]:
    """Assemble instructions with the 8086 emulator's assembler at CS:IP -> (bytes, error)."""
    from ...emu8086.assembler import assemble
    lines = [x.strip() for x in re.split(r"[\n;]", text) if x.strip()]
    if not lines:
        return None, "empty"
    prog = assemble(f"org {ip:X}h\n" + "\n".join(lines) + "\n", "cpu_assemble.asm")
    if not prog.ok:
        e = prog.errors[0]
        return None, e.text(lang) if hasattr(e, "text") else str(e)
    data = b"".join(b for _a, b in sorted(prog.chunks))
    return data, ""
