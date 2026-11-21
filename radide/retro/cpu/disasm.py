"""Code / data separation and re-assemblable source output (no Qt in here).

1. ``analyze(segments, cpu, system, hints)`` traces the code recursively from the entry points (reset / NMI / IRQ
   vectors, RST / interrupt vectors, the user's hints): every reachable instruction becomes code, everything else
   stays data. Jump / call / branch targets and data references get labels; hardware registers get their names
   (radide/retro/cpu/hwregs.py); 2600 zero-page RAM gets ``ram_XX``.
2. ``Disassembly.render_segment(seg, dialect)`` writes one segment as source for ``dasm``, ``ca65``, ``rgbds`` or
   ``sjasmplus`` such that the assembler produces the *same bytes*: absolute operands below $100 are forced to
   16 bits (``lda.w`` / ``lda a:``), undocumented opcodes and odd encodings are written as bytes with the
   mnemonic in a comment, labels only go where a line starts.

Hints (``hints.json`` in a disassembly project, all optional)::

    {"code": ["F123", ...], "data": [["F800", "F8FF"], ...], "labels": {"F000": "Start"},
     "comments": {"F000": "entry"}, "undocumented": false}
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import Instr, decoder, hwregs


@dataclass
class Segment:
    name: str
    base: int                                   # CPU address of data[0]
    data: bytes
    bank: int = 0
    entries: list = field(default_factory=list)        # [(addr, name)] code entry points
    vectors: list = field(default_factory=list)        # [(addr, name)] 16-bit little-endian vector words
    mirror: int = 0                             # 2600: addresses with bit 12 set mirror the ROM (mask = size - 1)
    trace: bool = True                          # False = pure data (iNES header, CHR ROM)
    fixed: bool = True                          # labels of this segment can be used from the other segments
    prefix: str = ""                            # label prefix ("B1_" for bank 1 ...)

    @property
    def end(self) -> int:
        return self.base + len(self.data)

    def exact(self, addr: int) -> int | None:
        """Offset of *addr* when it is inside the segment at its own address (labels), else None."""
        return addr - self.base if self.base <= addr < self.end else None

    def offset(self, addr: int) -> int | None:
        """Offset of *addr* for tracing (follows the 2600 mirrors), else None."""
        off = self.exact(addr)
        if off is not None:
            return off
        if self.mirror and addr & 0x1000:
            return (addr & self.mirror) % max(1, len(self.data))
        return None


@dataclass
class Hints:
    code: list = field(default_factory=list)
    data: list = field(default_factory=list)            # [(start, end inclusive)]
    labels: dict = field(default_factory=dict)          # addr -> name
    comments: dict = field(default_factory=dict)        # addr -> text
    undocumented: bool = False

    @classmethod
    def load(cls, path) -> "Hints":
        try:
            d = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        h = lambda v: int(str(v).lstrip("$").replace("0x", ""), 16) if isinstance(v, str) else int(v)   # noqa: E731
        return cls([h(a) for a in d.get("code", [])], [(h(a), h(b)) for a, b in d.get("data", [])],
                   {h(k): str(v) for k, v in d.get("labels", {}).items()},
                   {h(k): str(v) for k, v in d.get("comments", {}).items()}, bool(d.get("undocumented")))

    def is_data(self, addr: int) -> bool:
        return any(a <= addr <= b for a, b in self.data)


DIALECTS = {
    "dasm": {"byte": ".byte", "word": ".word", "equ": "{n} = {v}", "label": "{n}", "force16": "{m}.w"},
    "ca65": {"byte": ".byte", "word": ".word", "equ": "{n} = {v}", "label": "{n}:", "force16": "{m} a:"},
    "rgbds": {"byte": "db", "word": "dw", "equ": "DEF {n} EQU {v}", "label": "{n}:", "force16": ""},
    "sjasmplus": {"byte": "db", "word": "dw", "equ": "{n} EQU {v}", "label": "{n}:", "force16": ""},
}
DIALECT_CPU = {"dasm": "6502", "ca65": "6502", "rgbds": "sm83", "sjasmplus": "z80"}


def hex8(v: int) -> str:
    return f"${v & 0xFF:02X}"


def hex16(v: int) -> str:
    return f"${v & 0xFFFF:04X}"


class Disassembly:
    def __init__(self, segments: list[Segment], cpu: str, system: str = "", hints: Hints | None = None):
        self.segments = segments
        self.cpu = cpu
        self.system = system
        self.hints = hints or Hints()
        self.dec = decoder(cpu)
        self.code: dict[int, dict[int, Instr]] = {id(s): {} for s in segments}     # seg -> offset -> Instr
        self.owner: dict[int, dict[int, int]] = {id(s): {} for s in segments}      # seg -> byte offset -> instr off
        self.labels: dict[tuple[int, int], str] = {}                                # (seg id, offset) -> name
        self.equates: dict[str, int] = {}                                           # name -> value
        self.equate_docs: dict[str, str] = {}
        self.refs: dict[tuple[int, int], tuple[str, str]] = {}                      # (seg, instr off) -> (name, k)
        self.conflicts: list[str] = []

    # ------------------------------------------------------------------ tracing
    def _trace(self, seg: Segment, start: int, undocumented: bool) -> None:
        code, owner = self.code[id(seg)], self.owner[id(seg)]
        work = [start]
        while work:
            addr = work.pop()
            off = seg.offset(addr)
            while off is not None and seg.trace:
                if off in code:
                    break
                if off in owner:                         # lands inside another instruction
                    self.conflicts.append(f"{seg.name}: jump into the middle of an instruction at {hex16(addr)}")
                    break
                cpu_addr = seg.base + off
                if self.hints.is_data(cpu_addr):
                    break
                ins = self.dec.decode(seg.data, off, cpu_addr, undocumented)
                if ins is None:
                    break
                if any((off + i) in owner or (off + i) in code for i in range(1, ins.size)):
                    self.conflicts.append(f"{seg.name}: overlapping instructions at {hex16(cpu_addr)}")
                    break
                code[off] = ins
                for i in range(ins.size):
                    owner[off + i] = off
                if ins.target is not None and ins.kind in ("jump", "branch", "call"):
                    for s2 in self._segments_for(seg, ins.target):
                        if s2 is seg:
                            work.append(ins.target)
                        elif s2.trace:
                            self._pending.append((s2, ins.target))
                if ins.is_flow_end:
                    break
                off += ins.size
                if off >= len(seg.data):
                    break

    def _segments_for(self, seg: Segment, addr: int) -> list[Segment]:
        """Segments a target address can be in when seen from *seg*: itself, else the fixed ones."""
        if seg.offset(addr) is not None:
            return [seg]
        return [s for s in self.segments if s.fixed and s.trace and s is not seg and s.exact(addr) is not None][:1]

    def run(self, undocumented: bool | None = None) -> "Disassembly":
        undoc = self.hints.undocumented if undocumented is None else undocumented
        self._pending: list[tuple[Segment, int]] = []
        for seg in self.segments:
            if not seg.trace:
                continue
            starts = [a for a, _n in seg.entries]
            for vaddr, _name in seg.vectors:
                off = seg.exact(vaddr)
                if off is not None and off + 1 < len(seg.data):
                    starts.append(seg.data[off] | (seg.data[off + 1] << 8))
            starts += [a for a in self.hints.code if seg.exact(a) is not None]
            for a in starts:
                self._trace(seg, a, undoc)
        while self._pending:
            s2, a = self._pending.pop()
            self._trace(s2, a, undoc)
        self._make_labels()
        return self

    # ------------------------------------------------------------------ labels
    def _label_name(self, seg: Segment, addr: int) -> str:
        return f"{seg.prefix}L{addr & 0xFFFF:04X}"

    def _line_start(self, seg: Segment, off: int) -> bool:
        owner = self.owner[id(seg)]
        return off not in owner or owner[off] == off

    def _make_labels(self) -> None:
        names_used: set[str] = set()

        def add(seg, off, name):
            key = (id(seg), off)
            if key in self.labels:
                return self.labels[key]
            base = name
            i = 2
            while name in names_used:
                name = f"{base}_{i}"
                i += 1
            names_used.add(name)
            self.labels[key] = name
            return name

        for seg in self.segments:                              # entry points and the user's labels first
            for addr, name in seg.entries:
                off = seg.exact(addr)
                if off is not None and self._line_start(seg, off):
                    add(seg, off, seg.prefix + name if name else self._label_name(seg, addr))
            for vaddr, vname in seg.vectors:
                off = seg.exact(vaddr)
                if off is None or off + 1 >= len(seg.data):
                    continue
                target = seg.data[off] | (seg.data[off + 1] << 8)
                toff = seg.exact(target)
                if toff is not None and self._line_start(seg, toff) and toff in self.code[id(seg)]:
                    add(seg, toff, seg.prefix + vname)
            for addr, name in self.hints.labels.items():
                off = seg.exact(addr)
                if off is not None and self._line_start(seg, off):
                    add(seg, off, name)
        rw_names: dict[tuple[int, str], str] = {}
        for seg in self.segments:
            for off, ins in sorted(self.code[id(seg)].items()):
                if ins.target is None or "{t}" not in ins.operand:
                    continue
                t = ins.target
                hit = None
                for s2 in self._segments_for(seg, t):
                    toff = s2.exact(t)
                    if toff is not None and self._line_start(s2, toff):
                        hit = (s2, toff)
                if hit is not None:                  # (ld hl,nn into the program = a data pointer: same value)
                    s2, toff = hit
                    name = self.labels.get((id(s2), toff)) or add(s2, toff, self._label_name(s2, t))
                    self.refs[(id(seg), off)] = (name, "label")
                    continue
                # hardware register / ROM routine / system variable
                acc = "call" if ins.kind in ("call", "jump") else self._access(ins)
                if not acc and ins.width == "imm16":
                    reg = hwregs.lookup(self.system, t, "r")
                    reg = reg if reg is not None and reg.access == "var" else None
                else:
                    reg = hwregs.lookup(self.system, t, acc or "r") if self.system else None
                    if reg is not None and reg.access == "call" and acc != "call":
                        reg = None
                if reg is not None:
                    key = (t, reg.name)
                    nm = rw_names.setdefault(key, reg.name)
                    self.equates[nm] = t
                    self.equate_docs[nm] = reg.text
                    self.refs[(id(seg), off)] = (nm, "equ")
                    continue
                lo_hi = hwregs.ZP_RAM.get(self.system)
                if lo_hi and lo_hi[0] <= t <= lo_hi[1] and not ins.kind:
                    nm = f"ram_{t:02X}"
                    self.equates[nm] = t
                    self.equate_docs[nm] = "zero-page RAM variable"
                    self.refs[(id(seg), off)] = (nm, "equ")

    def _access(self, ins: Instr) -> str:
        fn = getattr(self.dec, "access", None)
        return fn(ins) if callable(fn) else "r"

    # ------------------------------------------------------------------ output
    def operand(self, seg: Segment, off: int, ins: Instr, dialect: str) -> str:
        ref = self.refs.get((id(seg), off))
        t = ins.target
        if "{t}" not in ins.operand:
            return ins.operand
        if ref is not None:
            value = ref[0]
        elif t is None:
            value = ""
        elif ins.width == "zp":
            value = hex8(t)
        else:
            value = hex16(t)
        return ins.operand.replace("{t}", value)

    def mnemonic(self, seg: Segment, off: int, ins: Instr, dialect: str) -> tuple[str, str]:
        """(mnemonic text, operand text) with the 16-bit forcing of the 6502 dialects."""
        opnd = self.operand(seg, off, ins, dialect)
        m = ins.mnemonic
        if self.cpu == "6502" and ins.width == "abs16" and ins.kind not in ("jump", "call", "jumpind") and \
                ins.target is not None and ins.target < 0x100:
            if dialect == "dasm":
                m = f"{m}.w"
            elif dialect == "ca65" and not opnd.startswith("("):
                opnd = "a:" + opnd
        return m, opnd

    def needs_bytes(self, ins: Instr, dialect: str) -> bool:
        """Instructions written back as raw bytes so the assembler cannot pick another encoding."""
        if ins.undocumented:
            return True
        if self.cpu == "z80" and ins.mnemonic == "nop" and ins.size > 1:
            return True
        return False

    def instruction_text(self, seg: Segment, off: int, ins: Instr, dialect: str = "") -> str:
        m, opnd = self.mnemonic(seg, off, ins, dialect)
        return f"{m} {opnd}".rstrip()

    def render_equates(self, dialect: str) -> str:
        d = DIALECTS[dialect]
        out = []
        for name, v in sorted(self.equates.items(), key=lambda kv: (kv[1], kv[0])):
            val = hex8(v) if v < 0x100 else hex16(v)
            doc = self.equate_docs.get(name, "")
            out.append(d["equ"].format(n=name, v=val) + (f"    ; {doc}" if doc else ""))
        return "\n".join(out)

    def render_segment(self, seg: Segment, dialect: str, indent: str = "        ", per_line: int = 8,
                       address_comments: bool = True) -> str:
        d = DIALECTS[dialect]
        code = self.code[id(seg)]
        lines: list[str] = []
        data = seg.data
        n = len(data)
        vec_at = {seg.exact(a): name for a, name in seg.vectors if seg.exact(a) is not None}
        off = 0
        pending: list[int] = []
        pend_start = 0

        def flush():
            nonlocal pending
            if not pending:
                return
            for i in range(0, len(pending), per_line):
                chunk = pending[i:i + per_line]
                addr = seg.base + pend_start + i
                txt = ",".join(hex8(b) for b in chunk)
                asc = "".join(chr(b) if 32 <= b < 127 and chr(b) not in "\\;" else "." for b in chunk)
                lines.append(f"{indent}{d['byte']} {txt}".ljust(48) + (f"; {addr:04X} {asc}" if address_comments
                                                                       else ""))
            pending = []

        while off < n:
            addr = seg.base + off
            label = self.labels.get((id(seg), off))
            comment = self.hints.comments.get(addr)
            if label or comment or off in code or off in vec_at:
                flush()
            if comment:
                lines.append(f"; {comment}")
            if label:
                lines.append(d["label"].format(n=label))
            if off in vec_at and off + 1 < n and off + 1 not in code and not any(
                    (id(seg), off + 1) == k for k in self.labels):
                v = data[off] | (data[off + 1] << 8)
                name = None
                for s2 in self._segments_for(seg, v):
                    toff = s2.exact(v)
                    if toff is not None:
                        name = self.labels.get((id(s2), toff))
                lines.append(f"{indent}{d['word']} {name or hex16(v)}".ljust(48) + f"; {addr:04X} {vec_at[off]} vector")
                off += 2
                continue
            ins = code.get(off)
            if ins is not None:
                if self.needs_bytes(ins, dialect):
                    txt = ",".join(hex8(b) for b in ins.raw)
                    lines.append(f"{indent}{d['byte']} {txt}".ljust(48) +
                                 f"; {addr:04X} {self.instruction_text(seg, off, ins, dialect)}"
                                 + (" (undocumented)" if ins.undocumented else ""))
                else:
                    m, opnd = self.mnemonic(seg, off, ins, dialect)
                    lines.append(f"{indent}{m} {opnd}".rstrip().ljust(48) + (f"; {addr:04X}" if address_comments
                                                                            else ""))
                off += ins.size
                continue
            if not pending:
                pend_start = off
            pending.append(data[off])
            off += 1
        flush()
        return "\n".join(lines)

    def listing(self, seg: Segment) -> list[tuple[int, str, str, str]]:
        """(address, hex bytes, text, kind "code" / "data") rows of a segment, for viewers."""
        rows = []
        code = self.code[id(seg)]
        off = 0
        while off < len(seg.data):
            ins = code.get(off)
            addr = seg.base + off
            if ins is not None:
                rows.append((addr, " ".join(f"{b:02X}" for b in ins.raw),
                             self.instruction_text(seg, off, ins, ""), "code"))
                off += ins.size
            else:
                rows.append((addr, f"{seg.data[off]:02X}", f"db {hex8(seg.data[off])}", "data"))
                off += 1
        return rows

    def stats(self) -> dict:
        total = sum(len(s.data) for s in self.segments if s.trace)
        code = sum(len(self.owner[id(s)]) for s in self.segments if s.trace)
        return {"bytes": total, "code_bytes": code, "data_bytes": total - code,
                "instructions": sum(len(self.code[id(s)]) for s in self.segments),
                "labels": len(self.labels), "equates": len(self.equates), "conflicts": len(self.conflicts)}


def analyze(segments: list[Segment], cpu: str, system: str = "", hints: Hints | None = None,
            undocumented: bool | None = None) -> Disassembly:
    return Disassembly(segments, cpu, system, hints).run(undocumented)
