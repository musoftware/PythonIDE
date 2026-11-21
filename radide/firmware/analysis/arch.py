"""Guess the CPU architecture and the load (base) address of a raw firmware image.

CPU: statistics of instruction patterns that are typical for each family (return / prologue / epilogue / call
encodings, counted at the instruction alignment and corrected for how often they would occur in random bytes),
plus checks of vector tables and boot headers (Cortex-M vector table, MPC5xxx RCHW, AURIX boot mode header,
C166 JMPS trap table, HC12 / S12 vectors at the end of the image, SH / 68K reset vectors, V850 JR table, 8051
LJMP at 0) and - for byte-coded CPUs - whether absolute call targets land right after a return instruction.

Base address: the vector table / boot header suggests candidates; every candidate is scored by how many
pointer-sized words of the image point exactly at the start of a string or at a vector entry when the image is
loaded there (the method of tools like basefind), so the right base stands out.

All results carry a confidence (0..1) and the evidence; they are hints for the user, not facts.
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field

# id -> label, endianness, pointer size, Ghidra language id, instruction alignment
ARCH_INFO: dict[str, dict] = {
    "arm-thumb": dict(label="ARM Cortex-M (Thumb / Thumb-2)", endian="little", psize=4, ghidra="ARM:LE:32:Cortex",
                      align=2),
    "arm": dict(label="ARM (A32, ARM7 / ARM9 / Cortex-R)", endian="little", psize=4, ghidra="ARM:LE:32:v7", align=4),
    "ppc": dict(label="PowerPC (Book E / e200 / MPC5xx)", endian="big", psize=4, ghidra="PowerPC:BE:32:e500",
                align=4),
    "ppc-vle": dict(label="PowerPC e200 VLE (MPC55xx / 56xx / 57xx / SPC5)", endian="big", psize=4,
                    ghidra="PowerPC:BE:64:VLE-32addr", align=2),
    "tricore": dict(label="Infineon TriCore (AUDO / AURIX)", endian="little", psize=4,
                    ghidra="tricore:LE:32:default", align=2),
    "c166": dict(label="Infineon C166 / ST10 / XC16x", endian="little", psize=2, ghidra="", align=2),
    "hc12": dict(label="Freescale HC12 / S12(X)", endian="big", psize=2, ghidra="HCS12:BE:24:default", align=1),
    "sh2": dict(label="Renesas SuperH SH-2 / SH-2A / SH-4 (big endian)", endian="big", psize=4,
                ghidra="SuperH:BE:32:SH-2A", align=2),
    "v850": dict(label="Renesas V850 / RH850", endian="little", psize=4, ghidra="V850:LE:32:default", align=2),
    "m68k": dict(label="Motorola 68K / CPU32 (683xx)", endian="big", psize=4, ghidra="68000:BE:32:CPU32", align=2),
    "8051": dict(label="Intel 8051 / MCS-51", endian="big", psize=2, ghidra="8051:BE:16:default", align=1),
}

# (arch, regex, alignment, weight, probability in uniform random bytes, description)
_SIGS: list[tuple[str, bytes, int, float, float, str]] = [
    ("arm-thumb", rb"\x70\x47", 2, 3.0, 1 / 65536, "BX LR"),
    ("arm-thumb", rb"[\x00-\xff]\xb5", 2, 0.6, 1 / 256, "PUSH {..,LR}"),
    ("arm-thumb", rb"[\x00-\xff]\xbd", 2, 0.6, 1 / 256, "POP {..,PC}"),
    ("arm-thumb", rb"\x2d\xe9[\x00-\xff][\x40-\x5f]", 2, 3.0, 32 / 256 ** 3, "PUSH.W {..,LR}"),
    ("arm-thumb", rb"\xbd\xe8[\x00-\xff][\x80-\x9f]", 2, 3.0, 32 / 256 ** 3, "POP.W {..,PC}"),
    ("arm-thumb", rb"[\x00-\xff][\xf0-\xf7][\x00-\xff][\xf8-\xff]", 2, 0.4, (8 / 256) * (8 / 256), "BL"),
    ("arm", rb"\x1e\xff\x2f\xe1", 4, 4.0, 256 ** -4, "BX LR"),
    ("arm", rb"[\x00-\xff][\x40-\x5f]\x2d\xe9", 4, 2.0, 32 / 256 ** 3, "STMFD SP!,{..,LR}"),
    ("arm", rb"[\x00-\xff][\x80-\x9f]\xbd\xe8", 4, 2.0, 32 / 256 ** 3, "LDMFD SP!,{..,PC}"),
    ("arm", rb"[\x00-\xff]{3}[\xe0-\xef]", 4, 0.08, 1 / 16, "condition AL"),
    ("ppc", rb"\x4e\x80\x00\x20", 4, 4.0, 256 ** -4, "BLR"),
    ("ppc", rb"\x7c\x08\x02\xa6", 4, 4.0, 256 ** -4, "MFLR r0"),
    ("ppc", rb"\x7c\x08\x03\xa6", 4, 4.0, 256 ** -4, "MTLR r0"),
    ("ppc", rb"\x94\x21[\x80-\xff]", 4, 3.0, 128 / 256 ** 3, "STWU r1,-x(r1)"),
    ("ppc", rb"\x38\x21\x00", 4, 2.0, 256 ** -3, "ADDI r1,r1,x"),
    ("ppc-vle", rb"\x00\x04", 2, 0.8, 1 / 65536, "se_blr"),
    ("ppc-vle", rb"\x00\x80", 2, 0.8, 1 / 65536, "se_mflr r0"),
    ("ppc-vle", rb"\x00\x90", 2, 0.5, 1 / 65536, "se_mtlr r0"),
    ("ppc-vle", rb"\x18\x21\x06[\x80-\xff]", 2, 5.0, 128 / 256 ** 4, "e_stwu r1,-x(r1)"),
    ("ppc-vle", rb"\x54\x01\x00[\x00-\x7f]", 2, 1.5, 128 / 256 ** 4, "e_stw r0,x(r1)"),
    ("tricore", rb"\x00\x90", 2, 2.0, 1 / 65536, "RET"),
    ("tricore", rb"\x91[\x00-\xff]{3}\xd9", 2, 3.0, 1 / 65536, "MOVH.A + LEA"),
    ("tricore", rb"\x6d", 2, 0.25, 1 / 256, "CALL"),
    ("tricore", rb"\xda", 2, 0.15, 1 / 256, "MOV D15,#c"),
    ("c166", rb"\xcb\x00", 2, 3.0, 1 / 65536, "RET"),
    ("c166", rb"\xdb\x00", 2, 2.0, 1 / 65536, "RETS"),
    ("c166", rb"\xec[\xf0-\xff]", 2, 1.5, 16 / 65536, "PUSH Rn"),
    ("c166", rb"\xfc[\xf0-\xff]", 2, 1.5, 16 / 65536, "POP Rn"),
    ("c166", rb"\xca\x00", 2, 1.5, 1 / 65536, "CALLA cc_UC"),
    ("c166", rb"\xe6[\xf0-\xff]", 2, 0.6, 16 / 65536, "MOV Rw,#data16"),
    ("hc12", rb"\x30\x3d", 1, 2.0, 1 / 65536, "PULX; RTS"),
    ("hc12", rb"\x3a\x3d", 1, 2.0, 1 / 65536, "PULD; RTS"),
    ("hc12", rb"\x3d[\x34\x3b\x1b]", 1, 1.5, 3 / 65536, "RTS; PSHx / LEAS"),
    ("sh2", rb"\x00\x0b", 2, 3.0, 1 / 65536, "RTS"),
    ("sh2", rb"\x4f\x22", 2, 3.0, 1 / 65536, "STS.L PR,@-R15"),
    ("sh2", rb"\x4f\x26", 2, 3.0, 1 / 65536, "LDS.L @R15+,PR"),
    ("sh2", rb"\x00\x09", 2, 1.0, 1 / 65536, "NOP"),
    ("sh2", rb"\x2f[\x86-\xe6]", 2, 0.5, 7 / 65536, "MOV.L Rn,@-R15"),
    ("v850", rb"\x7f\x00", 2, 4.0, 1 / 65536, "JMP [LP]"),
    ("v850", rb"\x63\xff", 2, 3.0, 1 / 65536, "ST.W LP,x[SP]"),
    ("v850", rb"\x23\xff", 2, 3.0, 1 / 65536, "LD.W x[SP],LP"),
    ("v850", rb"[\x80-\xbf]\xff", 2, 0.5, 64 / 65536, "JARL disp22,LP"),
    ("m68k", rb"\x4e\x75", 2, 3.0, 1 / 65536, "RTS"),
    ("m68k", rb"\x4e\x56", 2, 3.0, 1 / 65536, "LINK A6"),
    ("m68k", rb"\x4e\x5e", 2, 3.0, 1 / 65536, "UNLK A6"),
    ("m68k", rb"\x48\xe7", 2, 2.0, 1 / 65536, "MOVEM.L -(SP)"),
    ("m68k", rb"\x4c\xdf", 2, 2.0, 1 / 65536, "MOVEM.L (SP)+"),
    ("m68k", rb"\x4e\xb9", 2, 2.0, 1 / 65536, "JSR abs.l"),
    ("m68k", rb"\x4e\xba", 2, 1.0, 1 / 65536, "JSR (d16,PC)"),
    ("8051", rb"\xc0\xe0", 1, 1.5, 1 / 65536, "PUSH ACC"),
    ("8051", rb"\xd0\xe0", 1, 1.5, 1 / 65536, "POP ACC"),
    ("8051", rb"\x90[\x00-\xff]{2}\xe4\x93", 1, 4.0, 256 ** -3, "MOV DPTR,#; CLR A; MOVC"),
    ("8051", rb"\xd0\xe0\x22", 1, 3.0, 256 ** -3, "POP ACC; RET"),
]
_SIGS = [s for s in _SIGS if s[3] > 0]
_COMPILED = [(a, re.compile(rx, re.S), al, w, p, d) for a, rx, al, w, p, d in _SIGS]


@dataclass
class ArchGuess:
    arch: str
    confidence: float
    score: float
    evidence: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return ARCH_INFO.get(self.arch, {}).get("label", self.arch)


@dataclass
class BaseGuess:
    base: int
    confidence: float
    reason: str
    hits: int = 0


@dataclass
class Detection:
    arches: list[ArchGuess]
    bases: list[BaseGuess]
    vectors: dict = field(default_factory=dict)     # arch -> info of the table found

    @property
    def best(self) -> ArchGuess | None:
        return self.arches[0] if self.arches else None

    @property
    def base(self) -> BaseGuess | None:
        return self.bases[0] if self.bases else None


# ============================================================================ helpers
def _active_kb(data: bytes) -> float:
    """KB of bytes that are not erased-flash fill (0xFF / 0x00 runs of 16+)."""
    fill = sum(len(m.group()) for m in re.finditer(rb"\xff{16,}|\x00{16,}", data))
    return max(1.0, (len(data) - fill) / 1024)


def _count(rx: re.Pattern, data: bytes, align: int) -> int:
    if align == 1:
        return sum(1 for _ in rx.finditer(data))
    n = 0
    pos = 0
    ln = len(data)
    # overlapping matches at the alignment: search from every aligned position after a misaligned hit
    while pos < ln:
        m = rx.search(data, pos)
        if m is None:
            break
        s = m.start()
        if s % align == 0:
            n += 1
            pos = s + align
        else:
            pos = s + 1
    return n


def _u32(data: bytes, off: int, endian: str) -> int:
    return int.from_bytes(data[off:off + 4], endian) if off + 4 <= len(data) else 0


# ============================================================================ vector tables / boot headers
def _cortex_m_table(data: bytes, off: int) -> dict | None:
    if off + 64 > len(data):
        return None
    w = struct.unpack_from("<16I", data, off)
    sp, reset = w[0], w[1]
    ram = (0x1FF00000 <= sp <= 0x20400000) or (0x10000000 <= sp <= 0x10100000) or (0x20000000 <= sp <= 0x30100000) \
        or (0x00200000 <= sp <= 0x00500000) or (0x24000000 <= sp <= 0x24100000)
    if not ram or sp & 3 or not reset & 1 or reset < 0x100:
        return None
    vecs = [v for v in w[1:16] if v]
    odd = [v for v in vecs if v & 1]
    if len(odd) < 4 or len(odd) < len(vecs) - 4:
        return None
    hi = reset & 0xFFF00000
    near = [v for v in odd if (v & 0xFFF00000) == hi]
    if len(near) < len(odd) * 0.7:
        return None
    return {"offset": off, "sp": sp, "reset": reset & ~1, "vectors": sorted({v & ~1 for v in odd})}


def find_vector_tables(data: bytes) -> dict:
    """Vector tables / boot headers found, by arch."""
    out: dict = {}
    # Cortex-M: at 0 or at a 1 KB boundary (application after a bootloader)
    for off in [0] + list(range(0x400, min(len(data) - 64, 0x80000), 0x400)):
        t = _cortex_m_table(data, off)
        if t:
            out.setdefault("arm-thumb", []).append(t)
            if len(out["arm-thumb"]) >= 4:
                break
    # ARM A32 vector table: 8 branch / LDR PC instructions
    if len(data) >= 32:
        ws = struct.unpack_from("<8I", data, 0)
        armv = sum(1 for x in ws if (x & 0xFF000000) == 0xEA000000 or (x & 0xFFFFF000) == 0xE59FF000)
        if armv >= 6:
            out["arm"] = [{"offset": 0, "count": armv}]
    # MPC55xx / 56xx RCHW (0x5A boot identifier) at the BAM search blocks; 57xx boot header 0x5AA5
    for off in (0, 0x4000, 0x8000, 0x10000, 0x18000, 0x20000, 0x30000, 0x40000, 0x60000):
        if off + 8 <= len(data):
            w0 = _u32(data, off, "big")
            if (w0 & 0x00FF0000) == 0x005A0000 and (w0 & 0xFF00FFFF) == 0:
                vle = bool(w0 & 0x01000000)
                out.setdefault("ppc-vle" if vle else "ppc", []).append(
                    {"offset": off, "rchw": w0 >> 16, "reset": _u32(data, off + 4, "big"), "vle": vle})
            elif (w0 >> 16) == 0x5AA5:
                out.setdefault("ppc-vle", []).append({"offset": off, "boot_header": w0, "vle": True,
                                                      "reset": _u32(data, off + 0x10, "big")})
    # AURIX boot mode header: BMHDID 0xB359 (LE halfword at +2), start address at +4
    for off in (0, 0x20000, 0x40000, 0x60000):
        if off + 8 <= len(data):
            bmi, ident, stad = struct.unpack_from("<HHI", data, off)
            if ident == 0xB359 and 0x80000000 <= stad < 0xB0000000:
                out.setdefault("tricore", []).append({"offset": off, "reset": stad, "bmi": bmi})
    # C166: JMPS seg,addr in the trap table (every 4 bytes from 0)
    if len(data) >= 0x40:
        jm = sum(1 for i in range(0, 0x40, 4) if data[i] == 0xFA)
        if jm >= 8:
            t = data[0:4]
            out["c166"] = [{"offset": 0, "count": jm, "reset": (t[1] << 16) | t[2] | (t[3] << 8)}]
    # HC12 / S12: 16-bit vectors in the last 128 bytes, reset at the very end
    if 0x100 <= len(data):
        tail = data[-0x80:]
        vals = [int.from_bytes(tail[i:i + 2], "big") for i in range(0, 0x80, 2)]
        good = [v for v in vals if 0x4000 <= v < 0xFF00]
        reset = vals[-1]
        if len(good) >= 40 and 0x4000 <= reset < 0xFF00 and len(set(good)) < len(good):
            out["hc12"] = [{"offset": len(data) - 0x80, "reset": reset, "count": len(good)}]
    # SH-2: power-on PC, SP, manual-reset PC, SP (big endian)
    if len(data) >= 16:
        pc0, sp0, pc1, sp1 = struct.unpack_from(">4I", data, 0)
        if pc0 == pc1 and sp0 == sp1 and not pc0 & 1 and not sp0 & 3 and pc0 < 0x01000000 and \
                (sp0 >= 0xFFFF0000 or 0x00400000 <= sp0 < 0x10000000):
            out["sh2"] = [{"offset": 0, "reset": pc0, "sp": sp0}]
    # 68K: initial SSP, initial PC, then many equal vectors
    if len(data) >= 256:
        v = struct.unpack_from(">64I", data, 0)
        if not v[0] & 1 and not v[1] & 1 and 0x400 <= v[1] < max(len(data), 0x01000000) and v[0] > 0x1000:
            common = max(set(v[2:]), key=v[2:].count)
            if v[2:].count(common) >= 20 and not common & 1:
                out["m68k"] = [{"offset": 0, "reset": v[1], "ssp": v[0]}]
    # V850: JR disp22 every 16 bytes from 0
    if len(data) >= 0x80:
        jr = 0
        for i in range(0, 0x80, 0x10):
            h = int.from_bytes(data[i:i + 2], "little")
            if (h & 0xFFC0) == 0x0780:
                jr += 1
        if jr >= 6:
            out["v850"] = [{"offset": 0, "count": jr}]
    # 8051: LJMP at 0 and LJMP / RETI / fill at the interrupt vectors
    if len(data) >= 0x30 and data[0] == 0x02:
        vecs = sum(1 for v in (0x03, 0x0B, 0x13, 0x1B, 0x23) if data[v] in (0x02, 0x32, 0xFF, 0x00))
        target = (data[1] << 8) | data[2]
        if vecs >= 4 and 0x30 <= target < max(0x30, min(len(data), 0x10000)):
            out["8051"] = [{"offset": 0, "reset": target}]
    return out


def _call_target_ratio(data: bytes, opcode: bytes, addr_len: int, endian: str, rets: bytes, base: int,
                       align: int = 1) -> tuple[int, int]:
    """(calls, calls whose target follows a return opcode) for absolute calls '<opcode><addr>'."""
    rx = re.compile(re.escape(opcode) + rb"[\x00-\xff]{%d}" % addr_len, re.S)
    calls = good = 0
    n = len(data)
    for m in rx.finditer(data):
        if m.start() % align:
            continue
        t = int.from_bytes(m.group()[len(opcode):], endian) - base
        if 1 <= t < n:
            calls += 1
            if data[t - 1] in rets:
                good += 1
    return calls, good


# ============================================================================ CPU guess
def guess_arch(data: bytes, vectors: dict | None = None) -> list[ArchGuess]:
    data = bytes(data)
    kb = _active_kb(data)
    scores: dict[str, float] = {a: 0.0 for a in ARCH_INFO}
    evidence: dict[str, list[str]] = {a: [] for a in ARCH_INFO}
    for arch, rx, align, w, prob, desc in _COMPILED:
        hits = _count(rx, data, align)
        expected = (len(data) / align) * prob
        extra = max(0.0, hits - 2 * expected)
        if extra > 0:
            s = w * extra / kb
            scores[arch] += s
            if hits >= 3:
                evidence[arch].append(f"{desc}: {hits}x")
    vectors = find_vector_tables(data) if vectors is None else vectors
    bonus = {"arm-thumb": 25, "arm": 12, "ppc": 25, "ppc-vle": 25, "tricore": 25, "c166": 12, "hc12": 12,
             "sh2": 12, "m68k": 12, "v850": 10, "8051": 10}
    for arch, tabs in vectors.items():
        scores[arch] += bonus.get(arch, 10)
        t = tabs[0]
        what = {"arm-thumb": "Cortex-M vector table", "arm": "ARM exception vectors", "ppc": "RCHW boot word 0x5A",
                "ppc-vle": "RCHW / boot header with VLE", "tricore": "AURIX boot mode header 0xB359",
                "c166": "JMPS trap table", "hc12": "16-bit vectors at the end", "sh2": "reset PC/SP vectors",
                "m68k": "68K reset SSP/PC + vector table", "v850": "JR vector table", "8051": "LJMP at 0 + vectors"}
        evidence[arch].insert(0, f"{what.get(arch, 'vector table')} at offset 0x{t['offset']:X}")
    # byte-coded CPUs: absolute calls that land right after a return
    n = len(data)
    for arch, opcode, alen, endian, rets, bases, align in (
            ("hc12", b"\x16", 2, "big", b"\x3d\x0a", sorted({max(0, 0x10000 - n), 0x8000, 0x4000, 0xC000, 0}), 1),
            ("8051", b"\x12", 2, "big", b"\x22\x32", [0], 1),
            ("m68k", b"\x4e\xb9", 4, "big", b"\x75", [0], 2),
            ("c166", b"\xca\x00", 2, "little", b"\x00", [0], 2)):
        if n > 0x10000 and alen == 2 and arch != "c166":
            continue
        best = (0, 0)
        for b in bases:
            calls, good = _call_target_ratio(data, opcode, alen, endian, rets, b, align)
            if calls and good / calls > (best[1] / best[0] if best[0] else 0):
                best = (calls, good)
        calls, good = best
        if calls >= 10:
            ratio = good / calls
            if ratio > 0.15:
                scores[arch] += 30 * ratio * min(1.0, calls / 40)
                evidence[arch].append(f"{good} of {calls} absolute calls land after a return")
    # VLE images contain no classic PPC BLR; classic PPC code has many "00 04" halfwords (offsets)
    if scores["ppc"] > 0 and scores["ppc-vle"] > 0:
        if scores["ppc"] > scores["ppc-vle"] * 1.5 and "ppc-vle" not in vectors:
            scores["ppc-vle"] *= 0.3
        elif scores["ppc-vle"] > scores["ppc"] and "ppc" not in vectors:
            scores["ppc"] *= 0.5
    # Thumb and A32 share the ARM family: a Cortex-M vector table settles it
    if "arm-thumb" in vectors:
        scores["arm"] *= 0.3
    total = sum(scores.values())
    out = []
    for a, s in scores.items():
        if s <= 0.05:
            continue
        conf = s / (total + 4.0)
        out.append(ArchGuess(a, round(min(0.99, conf), 3), round(s, 2), evidence[a][:6]))
    out.sort(key=lambda g: -g.score)
    return out


# ============================================================================ base address
DEFAULT_BASES = {
    "arm-thumb": [0x08000000, 0x00000000, 0x00400000, 0x10000000, 0x1A000000, 0x00800000, 0x08008000],
    "arm": [0x00000000, 0x00100000, 0x80000000],
    "ppc": [0x00000000, 0x00800000, 0x01000000, 0x00400000],
    "ppc-vle": [0x00000000, 0x00800000, 0x01000000, 0x00FC0000, 0x00400000],
    "tricore": [0x80000000, 0xA0000000, 0x80080000, 0x80000000],
    "c166": [0x000000, 0xC00000, 0x080000, 0x010000],
    "hc12": [0x8000, 0x4000, 0xC000, 0x0000],
    "sh2": [0x00000000, 0x00020000],
    "v850": [0x00000000],
    "m68k": [0x00000000, 0x00040000],
    "8051": [0x0000],
}


def _pointer_values(data: bytes, psize: int, endian: str, align: int | None = None):
    import numpy as np
    align = psize if align is None else align
    dt = {2: ">u2" if endian == "big" else "<u2", 4: ">u4" if endian == "big" else "<u4"}[psize]
    out = []
    for phase in range(0, psize, align):
        n = (len(data) - phase) // psize
        if n > 0:
            out.append(np.frombuffer(data, dtype=dt, count=n, offset=phase).astype(np.int64))
    return np.concatenate(out) if out else np.zeros(0, dtype=np.int64)


def guess_base(data: bytes, arch: str, vectors: dict | None = None, string_offsets: list[int] | None = None,
               max_candidates: int = 400) -> list[BaseGuess]:
    """Candidate base addresses for *data* as code of *arch*, best first."""
    import numpy as np
    data = bytes(data)
    info = ARCH_INFO.get(arch, {"endian": "little", "psize": 4})
    endian, psize = info["endian"], info["psize"]
    n = len(data)
    vectors = find_vector_tables(data) if vectors is None else vectors
    reasons: dict[int, str] = {}
    cands: list[int] = []

    def add(b: int, why: str):
        if b < 0 or b > (0xFFFFFFFF if psize == 4 else 0xFFFFFF):
            return
        if b not in reasons:
            cands.append(b)
            reasons[b] = why
    targets: list[int] = []
    for t in vectors.get(arch, []):
        if arch == "arm-thumb":
            targets += t.get("vectors", [])
        r = t.get("reset")
        if r is not None:
            targets.append(r)
            for k in (12, 14, 16, 18, 20, 22, 24):
                b = (r & ~((1 << k) - 1)) - (t["offset"] if k < 12 else 0)
                if 0 <= r - b < n:
                    add(b, f"reset vector 0x{r:X} at offset 0x{t['offset']:X}")
                b2 = (r & ~((1 << k) - 1)) - t["offset"]
                if 0 <= r - b2 < n:
                    add(b2, f"reset vector 0x{r:X}, table at offset 0x{t['offset']:X}")
    if arch == "hc12" and n <= 0x10000:
        add(0x10000 - n, "image ends at 0xFFFF (vectors at the end)")
    for b in DEFAULT_BASES.get(arch, [0]):
        add(b, "usual flash start of this CPU family")
    vals = _pointer_values(data, psize, endian, 2 if psize == 4 and info.get("align", 4) <= 2 else None)
    vals = np.unique(vals)          # a value repeated by identical instructions counts once
    if psize == 4 and len(vals):
        # pages that many words point into -> base candidates below them
        page_bits = 16
        pages = vals >> page_bits
        uniq, counts = np.unique(pages, return_counts=True)
        order = np.argsort(-counts)[:10]
        span_pages = max(1, n >> page_bits) + 1
        for i in order:
            if counts[i] < 8 or uniq[i] == 0 or uniq[i] >= 0xFFFF:
                continue
            top = int(uniq[i]) << page_bits
            for k in range(0, min(span_pages, 64)):
                add(top - (k << page_bits), "many pointers into this area")
                if len(cands) > max_candidates:
                    break
    # targets: string starts, vector entries
    strs = string_offsets
    if strs is None:
        # NUL-terminated text with letters, starting after a NUL / non-printable byte
        strs = [m.start(1) for m in re.finditer(rb"(?<![\x20-\x7e])([\x20-\x7e]{5,})\x00", data)
                if sum(1 for c in m.group(1) if 65 <= c <= 90 or 97 <= c <= 122) >= 3]
    tgt = np.zeros(n + 1, dtype=bool)
    if strs:
        tgt[np.asarray(strs, dtype=np.int64)] = True
    scored = []
    vec_targets = np.asarray(sorted(set(targets)), dtype=np.int64) if targets else None
    for b in cands:
        idx = vals - b
        ok = (idx >= 0) & (idx < n)
        hits = int(tgt[idx[ok]].sum()) if ok.any() else 0
        inrange = int(ok.sum())
        vt = 0
        if vec_targets is not None:
            off = vec_targets - b
            vt = int(((off >= 0) & (off < n)).sum())
        score = hits * 3 + vt * 2 + inrange * 0.001
        scored.append((score, hits, vt, b))
    scored.sort(key=lambda x: (-x[0], x[3]))
    if not scored:
        return [BaseGuess(0, 0.1, "no candidates")]
    out = []
    best = scored[0][0]
    second = scored[1][0] if len(scored) > 1 else 0.0
    for i, (score, hits, vt, b) in enumerate(scored[:8]):
        if i == 0:
            conf = 0.35 if best <= 0 else min(0.99, 0.5 + 0.5 * (best - second) / max(best, 1e-9))
            if hits < 3 and vt == 0:
                conf = min(conf, 0.4)
        else:
            conf = min(0.9, 0.5 * score / max(best, 1e-9))
        why = reasons.get(b, "")
        detail = f"{hits} pointers to strings" + (f", {vt} vector targets inside" if vt else "")
        out.append(BaseGuess(b, round(conf, 3), f"{why}; {detail}" if why else detail, hits))
    return out


def detect(data: bytes, arch: str = "") -> Detection:
    """CPU guesses + base guesses for the best (or the given) CPU."""
    data = bytes(data)
    vectors = find_vector_tables(data)
    arches = guess_arch(data, vectors)
    a = arch or (arches[0].arch if arches else "")
    bases = guess_base(data, a, vectors) if a else []
    return Detection(arches, bases, vectors)
