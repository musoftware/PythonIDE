"""Memory-map model of a firmware image: segments of bytes at addresses, with gaps between them.

Every container format (raw .bin, Intel HEX, Motorola S-record, ELF) loads into a :class:`MemoryMap` and saves
from one, so conversions and split / merge work the same way for all of them. Pure Python.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass, field


@dataclass
class Segment:
    address: int
    data: bytearray
    name: str = ""
    flags: str = ""            # "r", "rw", "rx" ... (ELF program header / section flags, informational)

    @property
    def end(self) -> int:
        """First address after the segment."""
        return self.address + len(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def contains(self, addr: int) -> bool:
        return self.address <= addr < self.end


@dataclass
class Symbol:
    name: str
    address: int
    size: int = 0
    kind: str = ""             # "func", "object", "label", ...


@dataclass
class MemoryMap:
    """Ordered, non-overlapping segments. ``start`` is the entry point (Intel HEX 03/05, S7/S8/S9, ELF e_entry)."""
    segments: list[Segment] = field(default_factory=list)
    start: int | None = None
    symbols: list[Symbol] = field(default_factory=list)
    sections: list[Segment] = field(default_factory=list)      # ELF sections (views, informational)
    header: str = ""                                           # S0 header text / ELF machine, informational
    meta: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ building
    def add(self, address: int, data: bytes, name: str = "", flags: str = "", merge: bool = True) -> None:
        """Write *data* at *address*: overlapping bytes are overwritten, touching segments are joined."""
        if not data:
            return
        new = Segment(address, bytearray(data), name, flags)
        keep: list[Segment] = []
        for s in self.segments:
            if s.end < new.address or s.address > new.end or (not merge and (s.end == new.address
                                                                             or s.address == new.end)):
                keep.append(s)
                continue
            # overlapping or touching: combine into one segment, the new bytes win
            lo = min(s.address, new.address)
            hi = max(s.end, new.end)
            buf = bytearray(hi - lo)
            buf[s.address - lo:s.end - lo] = s.data
            buf[new.address - lo:new.end - lo] = new.data
            # bytes of *buf* between the two that neither covers can't exist (they touch or overlap)
            new = Segment(lo, buf, new.name or s.name, new.flags or s.flags)
        keep.append(new)
        keep.sort(key=lambda s: s.address)
        self.segments = keep

    @classmethod
    def from_bytes(cls, data: bytes, base: int = 0, name: str = "") -> "MemoryMap":
        m = cls()
        if data:
            m.segments.append(Segment(base, bytearray(data), name))
        return m

    def copy(self) -> "MemoryMap":
        m = MemoryMap([Segment(s.address, bytearray(s.data), s.name, s.flags) for s in self.segments], self.start,
                      list(self.symbols), list(self.sections), self.header, dict(self.meta))
        return m

    # ------------------------------------------------------------------ queries
    @property
    def min_address(self) -> int:
        return self.segments[0].address if self.segments else 0

    @property
    def max_address(self) -> int:
        """First address after the last segment."""
        return self.segments[-1].end if self.segments else 0

    @property
    def size(self) -> int:
        """Bytes actually present (gaps excluded)."""
        return sum(len(s) for s in self.segments)

    def span(self) -> int:
        return self.max_address - self.min_address

    def gaps(self) -> list[tuple[int, int]]:
        """(start, end) of every hole between segments."""
        out = []
        for a, b in zip(self.segments, self.segments[1:]):
            if b.address > a.end:
                out.append((a.end, b.address))
        return out

    def segment_at(self, addr: int) -> Segment | None:
        starts = [s.address for s in self.segments]
        i = bisect.bisect_right(starts, addr) - 1
        if i >= 0 and self.segments[i].contains(addr):
            return self.segments[i]
        return None

    def contains(self, addr: int) -> bool:
        return self.segment_at(addr) is not None

    def read(self, addr: int, n: int, fill: int | None = None) -> bytes:
        """*n* bytes from *addr*; bytes in gaps are *fill* (KeyError when *fill* is None)."""
        out = bytearray()
        a = addr
        end = addr + n
        while a < end:
            s = self.segment_at(a)
            if s is None:
                if fill is None:
                    raise KeyError(f"address 0x{a:X} is not in the image")
                nxt = min((x.address for x in self.segments if x.address > a), default=end)
                k = min(nxt, end) - a
                out += bytes([fill]) * k
                a += k
                continue
            k = min(s.end, end) - a
            out += s.data[a - s.address:a - s.address + k]
            a += k
        return bytes(out)

    def write(self, addr: int, data: bytes) -> None:
        """Overwrite bytes that exist (KeyError for addresses in gaps; use :meth:`add` to create bytes)."""
        a = addr
        i = 0
        while i < len(data):
            s = self.segment_at(a)
            if s is None:
                raise KeyError(f"address 0x{a:X} is not in the image")
            k = min(s.end - a, len(data) - i)
            s.data[a - s.address:a - s.address + k] = data[i:i + k]
            a += k
            i += k

    def to_flat(self, fill: int = 0xFF, start: int | None = None, end: int | None = None) -> bytes:
        """One continuous block from *start* (default: lowest address) to *end*, gaps filled with *fill*."""
        lo = self.min_address if start is None else start
        hi = self.max_address if end is None else end
        if hi <= lo:
            return b""
        buf = bytearray([fill]) * (hi - lo)
        for s in self.segments:
            a, b = max(s.address, lo), min(s.end, hi)
            if a < b:
                buf[a - lo:b - lo] = s.data[a - s.address:b - s.address]
        return bytes(buf)

    def offset_to_address(self, offset: int) -> int:
        """Offset in :meth:`to_flat` -> address."""
        return self.min_address + offset

    def address_to_offset(self, addr: int) -> int:
        return addr - self.min_address

    def symbol_at(self, addr: int) -> Symbol | None:
        for s in self.symbols:
            if s.address == addr:
                return s
        return None

    def relocate(self, delta: int) -> "MemoryMap":
        """A copy with every address moved by *delta* (e.g. raw .bin loaded at 0 -> real flash base)."""
        m = self.copy()
        for s in m.segments:
            s.address += delta
        m.symbols = [Symbol(s.name, s.address + delta, s.size, s.kind) for s in m.symbols]
        if m.start is not None:
            m.start += delta
        return m

    def describe(self) -> list[str]:
        lines = []
        for s in self.segments:
            lines.append(f"0x{s.address:08X}-0x{s.end - 1:08X}  {len(s):>9,} bytes  {s.name}".rstrip())
        for a, b in self.gaps():
            lines.append(f"  gap 0x{a:08X}-0x{b - 1:08X}  {b - a:>9,} bytes")
        return lines

    def __eq__(self, other) -> bool:          # same bytes at the same addresses (names / flags ignored)
        if not isinstance(other, MemoryMap):
            return NotImplemented
        a = [(s.address, bytes(s.data)) for s in self.segments]
        b = [(s.address, bytes(s.data)) for s in other.segments]
        return a == b
