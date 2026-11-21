"""Disassembly of firmware with Capstone: a navigable listing (labels, branch targets, data references) and an
index of cross references, e.g. "which instructions use the calibration table at 0x0800A1C0".

Supported through Capstone 5: ARM (A32), Thumb / Thumb-2 (Cortex-M), PowerPC (32-bit Book E; VLE is not in
Capstone - use "Analyze in Ghidra"), TriCore, M68K / CPU32, SuperH, HC12 / S12 (M680X CPU12), MIPS, x86.
C166 / ST10, V850 / RH850 and 8051 have no Capstone module: the listing says so and Ghidra is offered instead
(V850, 8051 and VLE are Ghidra languages).

Data references are recovered without full analysis: immediates / absolute operands that fall inside the image,
ARM / Thumb literal-pool loads (LDR rX,[PC,#n] -> the word in the pool), SuperH PC-relative MOV.L, PowerPC
LIS + ADDI / ORI / load-store pairs and TriCore MOVH.A + LEA / LD pairs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..formats.memmap import MemoryMap

try:
    import capstone as _cs
except ImportError:                     # pragma: no cover - capstone is a dependency of the EXE importer
    _cs = None


def _spec(arch: str):
    if _cs is None:
        return None
    c = _cs
    table = {
        "arm-thumb": (c.CS_ARCH_ARM, c.CS_MODE_THUMB | c.CS_MODE_MCLASS),
        "thumb": (c.CS_ARCH_ARM, c.CS_MODE_THUMB),
        "arm": (c.CS_ARCH_ARM, c.CS_MODE_ARM),
        "arm-be": (c.CS_ARCH_ARM, c.CS_MODE_ARM | c.CS_MODE_BIG_ENDIAN),
        "ppc": (c.CS_ARCH_PPC, c.CS_MODE_32 | c.CS_MODE_BIG_ENDIAN),
        "tricore": (c.CS_ARCH_TRICORE, getattr(c, "CS_MODE_TRICORE_162", 0)) if hasattr(c, "CS_ARCH_TRICORE")
        else None,
        "m68k": (c.CS_ARCH_M68K, c.CS_MODE_M68K_040 | c.CS_MODE_BIG_ENDIAN) if hasattr(c, "CS_ARCH_M68K") else None,
        "sh2": (c.CS_ARCH_SH, c.CS_MODE_SH2A | c.CS_MODE_BIG_ENDIAN) if hasattr(c, "CS_ARCH_SH") else None,
        "sh4-le": (c.CS_ARCH_SH, c.CS_MODE_SH4) if hasattr(c, "CS_ARCH_SH") else None,
        "hc12": (c.CS_ARCH_M680X, c.CS_MODE_M680X_CPU12) if hasattr(c, "CS_ARCH_M680X") else None,
        "mips": (c.CS_ARCH_MIPS, c.CS_MODE_MIPS32 | c.CS_MODE_BIG_ENDIAN),
        "mips-le": (c.CS_ARCH_MIPS, c.CS_MODE_MIPS32),
        "x86": (c.CS_ARCH_X86, c.CS_MODE_32),
        "x86-16": (c.CS_ARCH_X86, c.CS_MODE_16),
        "x86-64": (c.CS_ARCH_X86, c.CS_MODE_64),
        "arm64": (c.CS_ARCH_ARM64, c.CS_MODE_ARM),
    }
    return table.get(ALIASES.get(arch, arch))


ALIASES = {"sh": "sh2", "superh": "sh2", "cortex-m": "arm-thumb", "powerpc": "ppc", "68k": "m68k", "cpu32": "m68k",
           "s12": "hc12", "hcs12": "hc12"}


def supported(arch: str) -> bool:
    return _spec(arch) is not None


def unsupported_reason(arch: str) -> str:
    if _cs is None:
        return "Capstone is not installed (pip install capstone)."
    if arch == "ppc-vle":
        return "Capstone has no PowerPC VLE decoder. Use Analyze in Ghidra (language PowerPC VLE)."
    if arch in ("v850", "8051"):
        return f"Capstone has no {arch.upper()} decoder. Use Analyze in Ghidra."
    if arch == "c166":
        return "Neither Capstone nor Ghidra ships a C166 / ST10 decoder; use the hex view and the strings / maps."
    return f"No disassembler for '{arch}'."


ALIGN = {"arm-thumb": 2, "thumb": 2, "arm": 4, "arm-be": 4, "ppc": 4, "tricore": 2, "m68k": 2, "sh2": 2,
         "sh4-le": 2, "hc12": 1, "mips": 4, "mips-le": 4, "x86": 1, "x86-16": 1, "x86-64": 1, "arm64": 4}
ENDIAN = {"arm-thumb": "little", "thumb": "little", "arm": "little", "arm-be": "big", "ppc": "big",
          "tricore": "little", "m68k": "big", "sh2": "big", "sh4-le": "little", "hc12": "big", "mips": "big",
          "mips-le": "little", "x86": "little", "x86-16": "little", "x86-64": "little", "arm64": "little"}

CALLS = {"bl", "blx", "call", "calla", "calli", "fcall", "fcalla", "jsr", "bsr", "bsr.w", "bsr.b", "bsr.l", "jal",
         "jalr", "bgezal", "bltzal", "lcall", "acall", "jarl", "bla", "bctrl", "blrl", "lbsr", "callq", "jsr.l"}
NOT_BRANCH = {"bic", "bics", "bfc", "bfi", "bkpt", "bxj", "btst", "bset", "bclr", "bchg", "bita", "bitb", "bfextu",
              "bfexts", "bfins", "bfset", "bfclr", "bftst", "bfffo", "bgnd", "bmski", "bisect", "bsplit"}

_HEX = re.compile(r"(?:#?-?0x[0-9a-fA-F]+|\$[0-9a-fA-F]+(?:\.[lw])?|#?-?(?<![\w.])\d+\b)")


def _num(tok: str) -> int | None:
    t = tok.lstrip("#")
    neg = t.startswith("-")
    t = t.lstrip("-")
    try:
        if t.startswith("0x"):
            v = int(t, 16)
        elif t.startswith("$"):
            v = int(t[1:].split(".")[0], 16)
        else:
            v = int(t)
    except ValueError:
        return None
    return -v if neg else v


def is_branch(arch: str, mnem: str) -> bool:
    m = mnem.lower().split(".")[0] if arch not in ("m68k",) else mnem.lower()
    base = m.split(".")[0]
    if base in NOT_BRANCH or m in NOT_BRANCH:
        return False
    if arch in ("tricore",):
        return base.startswith(("j", "call", "loop", "fcall"))
    if arch.startswith("x86"):
        return base.startswith(("j", "call", "loop"))
    if arch in ("m68k",):
        return base.startswith(("b", "jsr", "jmp", "db"))
    if arch == "hc12":
        return base.startswith(("b", "lb", "jsr", "jmp", "call", "dbeq", "dbne", "ibeq", "ibne", "tbeq", "tbne"))
    if arch in ("sh2", "sh4-le"):
        return base in ("bt", "bf", "bra", "bsr", "jsr", "jmp", "bt/s", "bf/s", "braf", "bsrf") or \
            m in ("bt/s", "bf/s")
    if arch.startswith("mips"):
        return base.startswith(("b", "j"))
    return base.startswith(("b", "cb"))      # ARM / PPC


def is_call(arch: str, mnem: str) -> bool:
    m = mnem.lower()
    if arch.startswith("arm") or arch == "thumb":
        return m in ("bl", "blx") or m.startswith(("bl.", "blx."))
    return m in CALLS or m.split(".")[0] in CALLS


def is_return(arch: str, mnem: str, ops: str) -> bool:
    m = mnem.lower()
    o = ops.lower().replace(" ", "")
    if arch.startswith("arm") or arch == "thumb":
        return (m == "bx" and o == "lr") or (m.startswith("pop") and "pc" in o) or \
            (m.startswith("ldm") and "pc" in o)
    return m in ("ret", "rets", "reti", "rts", "rtc", "rte", "rtd", "rtr", "blr", "se_blr", "rfi", "rfe", "retn",
                 "retf", "iret", "jr") and (m != "jr" or o in ("$ra", "ra"))


@dataclass
class Line:
    address: int
    size: int
    raw: bytes
    mnemonic: str
    ops: str
    target: int | None = None           # branch / call target
    call: bool = False
    ret: bool = False
    refs: list[int] = field(default_factory=list)      # data addresses used
    comment: str = ""

    def text(self, labels: dict[int, str] | None = None, width: int = 8) -> str:
        labels = labels or {}
        hx = self.raw.hex()
        cmt = self.comment
        if self.target is not None and self.target in labels:
            cmt = (cmt + "; " if cmt else "") + ("call " if self.call else "-> ") + labels[self.target]
        for r in self.refs[:3]:
            if r in labels:
                cmt = (cmt + "; " if cmt else "") + "ref " + labels[r]
            else:
                cmt = (cmt + "; " if cmt else "") + f"ref 0x{r:X}"
        s = f"{self.address:0{width}X}  {hx:<16s} {self.mnemonic} {self.ops}".rstrip()
        return f"{s:<64s} ; {cmt}" if cmt else s


class _Tracker:
    """Register pairs that build 32-bit addresses (PPC LIS, TriCore MOVH.A, V850-like)."""
    def __init__(self):
        self.hi: dict[str, int] = {}

    def reset(self):
        self.hi.clear()


_PPC_LO = re.compile(r"^(addi|addic|ori|la)$")
_PPC_MEM = re.compile(r"(-?0x[0-9a-f]+|-?\d+)\((r\d+)\)")
_TC_MEM = re.compile(r"\[(a\d+)\]\s*#?(-?0x[0-9a-f]+|-?\d+)")
_PCREL = re.compile(r"\[pc,\s*#(-?0x[0-9a-f]+|-?\d+)\]")


def _sx16(v: int) -> int:
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def _refs(arch: str, ins, mm: MemoryMap, tr: _Tracker, lo: int, hi: int) -> list[int]:
    out: list[int] = []
    m, ops = ins.mnemonic.lower(), ins.op_str.lower()

    def inside(v):
        return lo <= v < hi
    if arch in ("arm-thumb", "thumb", "arm", "arm-be"):
        pm = _PCREL.search(ops)
        if pm and m.startswith(("ldr", "vldr", "adr")):
            disp = _num(pm.group(1)) or 0
            pc = (ins.address + (4 if arch in ("arm-thumb", "thumb") else 8)) & ~3
            lit = pc + disp
            if inside(lit):
                out.append(lit)
                if m.startswith("ldr") and not m.startswith(("ldrb", "ldrh", "ldrsb", "ldrsh", "ldrd")):
                    try:
                        val = int.from_bytes(mm.read(lit, 4), ENDIAN.get(arch, "little"))
                        if inside(val & ~1):
                            out.append(val & ~1 if val & 1 and inside(val - 1) else val)
                    except KeyError:
                        pass
        return out
    if arch == "ppc":
        parts = [p.strip() for p in ops.split(",")]
        if m == "lis" and len(parts) == 2:
            v = _num(parts[1])
            if v is not None:
                tr.hi[parts[0]] = (v & 0xFFFF) << 16
            return out
        if _PPC_LO.match(m) and len(parts) == 3 and parts[1] in tr.hi:
            v = _num(parts[2])
            if v is not None:
                addr = (tr.hi[parts[1]] + (_sx16(v) if m != "ori" else (v & 0xFFFF))) & 0xFFFFFFFF
                if inside(addr):
                    out.append(addr)
                tr.hi[parts[0]] = addr          # rd now holds the full address (later 0(rd) loads use it)
            return out
        mm_ = _PPC_MEM.search(ops)
        if mm_ and mm_.group(2) in tr.hi:
            addr = (tr.hi[mm_.group(2)] + _sx16(_num(mm_.group(1)) or 0)) & 0xFFFFFFFF
            if inside(addr):
                out.append(addr)
            if parts and parts[0] == mm_.group(2) and m.startswith("l"):
                tr.hi.pop(parts[0], None)
            return out
        if parts and parts[0] in tr.hi and m not in ("cmpwi", "cmplwi", "cmpw", "stw", "stb", "sth"):
            tr.hi.pop(parts[0], None)
        return out
    if arch == "tricore":
        parts = [p.strip() for p in ops.split(",")]
        if m in ("movh.a", "movh") and len(parts) == 2:
            v = _num(parts[1])
            if v is not None:
                tr.hi[parts[0]] = (v & 0xFFFF) << 16
            return out
        tm = _TC_MEM.search(ops)
        if tm and tm.group(1) in tr.hi:
            addr = (tr.hi[tm.group(1)] + _sx16(_num(tm.group(2)) or 0)) & 0xFFFFFFFF
            if inside(addr):
                out.append(addr)
            if m == "lea" and parts:
                tr.hi[parts[0]] = addr          # aX now holds the full address
            elif parts and parts[0] in tr.hi:
                tr.hi.pop(parts[0], None)
            return out
        if parts and parts[0] in tr.hi and not m.startswith("st"):
            tr.hi.pop(parts[0], None)
        return out
    # generic: absolute / immediate operands inside the image (SH literal addresses, 68K abs.l, HC12 ext / #imm)
    for tok in _HEX.findall(ops):
        v = _num(tok)
        if v is not None and v < 0 and hi <= 0x10000:
            v &= 0xFFFF                 # 16-bit CPUs print immediates signed ("ldx #-12544")
        if v is None or v < 0x100:
            continue
        if inside(v):
            out.append(v)
            if arch in ("sh2", "sh4-le") and m.startswith("mov.l") and "@" not in ops.split(",")[0] and tok.startswith("0x"):
                try:
                    val = int.from_bytes(mm.read(v, 4), ENDIAN.get(arch, "big"))
                    if inside(val):
                        out.append(val)
                except KeyError:
                    pass
    return out


def disassemble(mm: MemoryMap, arch: str, start: int, length: int = 0x400, max_lines: int = 20000) -> list[Line]:
    """Linear sweep of [start, start+length): undecodable units become '.byte' / '.short' lines."""
    arch = ALIASES.get(arch, arch)
    spec = _spec(arch)
    if spec is None:
        raise ValueError(unsupported_reason(arch))
    md = _cs.Cs(*spec)
    md.detail = False
    if hasattr(md, "skipdata"):
        md.skipdata = False
    al = ALIGN.get(arch, 1)
    lo, hi = mm.min_address, mm.max_address
    end = min(start + length, hi)
    out: list[Line] = []
    tr = _Tracker()
    a = start
    while a < end and len(out) < max_lines:
        seg = mm.segment_at(a)
        if seg is None:
            nxt = min((s.address for s in mm.segments if s.address > a), default=end)
            a = nxt
            tr.reset()
            continue
        chunk_end = min(seg.end, end)
        buf = bytes(seg.data[a - seg.address:chunk_end - seg.address])
        pos = 0
        for ins in md.disasm(buf, a):
            raw = bytes(ins.bytes)
            ln = Line(ins.address, ins.size, raw, ins.mnemonic, ins.op_str)
            if is_branch(arch, ins.mnemonic):
                nums = [_num(t) for t in _HEX.findall(ins.op_str)]
                nums = [n for n in nums if n is not None and n >= 0]
                if nums and not re.search(r"\[|@|\(", ins.op_str.split(",")[-1]):
                    ln.target = nums[-1]
                ln.call = is_call(arch, ins.mnemonic)
                if not ln.call:
                    tr.reset()
            ln.ret = is_return(arch, ins.mnemonic, ins.op_str)
            if ln.ret:
                tr.reset()
            ln.refs = [r for r in _refs(arch, ins, mm, tr, lo, hi) if r != ln.target]
            out.append(ln)
            pos = ins.address + ins.size - a
            if len(out) >= max_lines:
                break
        a += pos
        if a < chunk_end and len(out) < max_lines:
            # an undecodable unit
            n = min(al, chunk_end - a) or 1
            raw = bytes(seg.data[a - seg.address:a - seg.address + n])
            out.append(Line(a, n, raw, ".byte" if n == 1 else ".short" if n == 2 else ".word",
                            ", ".join(f"0x{b:02x}" for b in raw)))
            a += n
            tr.reset()
        elif a >= chunk_end:
            a = chunk_end
    return out


def auto_labels(lines: list[Line], symbols: dict[int, str] | None = None) -> dict[int, str]:
    labels = dict(symbols or {})
    for ln in lines:
        if ln.target is not None and ln.target not in labels:
            labels[ln.target] = (f"sub_{ln.target:X}" if ln.call else f"loc_{ln.target:X}")
    return labels


def listing(mm: MemoryMap, arch: str, start: int, length: int = 0x400, symbols: dict[int, str] | None = None,
            ) -> str:
    lines = disassemble(mm, arch, start, length)
    labels = auto_labels(lines, symbols)
    width = 8 if mm.max_address > 0xFFFF else 4
    out = []
    for ln in lines:
        if ln.address in labels:
            out.append(f"\n{labels[ln.address]}:")
        out.append("    " + ln.text(labels, width))
    return "\n".join(out).lstrip("\n")


@dataclass
class XrefIndex:
    """target address -> [(instruction address, 'call' | 'jump' | 'data')]"""
    refs: dict[int, list[tuple[int, str]]] = field(default_factory=dict)
    instructions: int = 0

    def to(self, addr: int, size: int = 1) -> list[tuple[int, str]]:
        out = []
        for a in range(addr, addr + max(1, size)):
            out += self.refs.get(a, [])
        return sorted(set(out))

    def add(self, target: int, src: int, kind: str):
        self.refs.setdefault(target, []).append((src, kind))


def build_xrefs(mm: MemoryMap, arch: str, ranges: list[tuple[int, int]] | None = None,
                max_bytes: int = 8 << 20) -> XrefIndex:
    """Cross references over *ranges* (address ranges of code; default: the whole image)."""
    idx = XrefIndex()
    arch = ALIASES.get(arch, arch)
    if not supported(arch):
        return idx
    ranges = ranges or [(s.address, s.end) for s in mm.segments]
    done = 0
    for a, b in ranges:
        if done >= max_bytes:
            break
        n = min(b - a, max_bytes - done)
        for ln in disassemble(mm, arch, a, n, max_lines=10 ** 7):
            idx.instructions += 1
            if ln.target is not None:
                idx.add(ln.target, ln.address, "call" if ln.call else "jump")
            for r in ln.refs:
                idx.add(r, ln.address, "data")
        done += n
    return idx


def code_ranges(mm: MemoryMap, regions, offset_base: int | None = None, min_size: int = 256) -> list[tuple[int, int]]:
    """Address ranges of the entropy regions classed as code (radide.firmware.analysis.entropy.classify)."""
    base = mm.min_address if offset_base is None else offset_base
    out = []
    for r in regions:
        if r.kind == "code" and r.size >= min_size:
            out.append((base + r.start, base + r.end))
    return out
