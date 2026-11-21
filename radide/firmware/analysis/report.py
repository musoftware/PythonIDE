"""One-call analysis of a firmware image (used by the Analysis view, the CLI and the Firmware Analysis project's
Build): container + memory map, entropy regions, fill areas, strings / identification strings, CPU and base
address guesses. Pure Python (+ numpy for speed)."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..formats.memmap import MemoryMap
from . import arch as _arch
from . import entropy, fill, strings


@dataclass
class Analysis:
    mm: MemoryMap
    flat: bytes
    block: int
    profile: list[float]
    regions: list[entropy.Region]
    fills: list[fill.FillArea]
    strings: list[strings.FoundString]
    detection: _arch.Detection
    notes: list[str] = field(default_factory=list)

    @property
    def base(self) -> int:
        """Load address of offset 0 of ``flat``: the container's address, or the best guess for a raw file."""
        if self.mm.meta.get("format") in ("ihex", "srec", "elf"):
            return self.mm.min_address
        b = self.detection.base
        return b.base if b is not None and b.confidence >= 0.5 else self.mm.min_address

    @property
    def arch(self) -> str:
        known = self.mm.meta.get("arch") or ""
        if known:
            return "arm-thumb" if known == "arm" and self.detection.best and \
                self.detection.best.arch == "arm-thumb" else known
        return self.detection.best.arch if self.detection.best else ""

    def entry_points(self) -> list[int]:
        """Reset vector + vector table entries (addresses) of the detected CPU."""
        out: list[int] = []
        a = self.arch
        for t in self.detection.vectors.get(a, []):
            if "vectors" in t:
                out += t["vectors"]
            elif t.get("reset") is not None:
                out.append(t["reset"])
        if self.mm.start is not None:
            out.append(self.mm.start & ~1 if a == "arm-thumb" else self.mm.start)
        b = self.base
        span = (b, b + len(self.flat))
        return sorted({x for x in out if span[0] <= x < span[1]})

    def text(self) -> str:
        L = [f"Format: {self.mm.meta.get('format', 'raw')}   bytes present: {self.mm.size:,}   "
             f"span: 0x{self.mm.min_address:X}-0x{max(self.mm.max_address - 1, 0):X}"]
        if self.mm.header:
            L.append(f"Header: {self.mm.header}")
        L.append("Memory map:")
        L += ["  " + s for s in self.mm.describe()]
        L.append("CPU (guess):")
        for g in [x for x in self.detection.arches if x.confidence >= 0.01][:5]:
            L.append(f"  {g.confidence:5.0%}  {g.label}" + (f"   [{'; '.join(g.evidence[:3])}]" if g.evidence else ""))
        if not self.detection.arches:
            L.append("  (no CPU pattern found - data / encrypted / compressed image?)")
        L.append("Load address (guess):")
        for b in self.detection.bases[:3]:
            L.append(f"  {b.confidence:5.0%}  0x{b.base:08X}   {b.reason}")
        L.append("Regions (entropy):")
        for k, v in sorted(entropy.summary(self.regions).items(), key=lambda kv: -kv[1]):
            L.append(f"  {entropy.CLASSES.get(k, k):34s} {v:>10,} bytes")
        L.append(f"Fill areas: {len(self.fills)}  ({sum(f.size for f in self.fills):,} bytes)")
        for f in self.fills[:10]:
            L.append(f"  0x{self.mm.min_address + f.start:08X}  {f.size:>9,}  {f.label}")
        ids = strings.identification(self.strings)
        L.append(f"Strings: {len(self.strings)}   identification-like: {len(ids)}")
        for s in ids[:15]:
            L.append(f"  0x{self.mm.min_address + s.offset:08X}  {s.text[:60]!r}  ({', '.join(s.tags)})")
        L += self.notes
        return "\n".join(L)


def analyze(mm: MemoryMap, block: int | None = None, arch: str = "") -> Analysis:
    flat = mm.to_flat(0xFF)
    if block is None:
        block = 512 if len(flat) <= 1 << 20 else 1024 if len(flat) <= 8 << 20 else 4096
    prof = entropy.entropy_profile(flat, block)
    regions = entropy.classify(flat, block, prof)
    fills = fill.find_fill(flat)
    strs = strings.find_strings(flat)
    known = arch or mm.meta.get("arch", "")
    if known == "arm":
        known = ""                      # ELF says ARM: let the detector decide Thumb vs A32
    det = _arch.detect(flat, known)
    notes = []
    if mm.meta.get("format") == "elf" and mm.meta.get("vle"):
        notes.append("ELF sections are marked as PowerPC VLE code.")
        if not arch:
            det = _arch.detect(flat, "ppc-vle")
    return Analysis(mm, flat, block, prof, regions, fills, strs, det, notes)
