"""Fill areas: runs of one byte value (0xFF erased flash, 0x00, 0x55/0xAA test patterns) or of a short repeating
pattern (e.g. FF FF 00 00, or a 2/4-byte 'illegal instruction' filler) at least *min_size* long."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class FillArea:
    start: int
    end: int
    pattern: bytes

    @property
    def size(self) -> int:
        return self.end - self.start

    @property
    def label(self) -> str:
        if len(self.pattern) == 1:
            return f"0x{self.pattern[0]:02X} fill"
        return self.pattern.hex(" ").upper() + " pattern"


def find_fill(data: bytes, min_size: int = 256, patterns: int = 4) -> list[FillArea]:
    """Single-byte runs first, then repeating 2..*patterns*-byte patterns in what is left."""
    out: list[FillArea] = []
    rx = re.compile(rb"(.)\1{%d,}" % (min_size - 1), re.S)
    for m in rx.finditer(data):
        out.append(FillArea(m.start(), m.end(), m.group(1)))
    taken = [(a.start, a.end) for a in out]
    for plen in range(2, patterns + 1):
        rep = max(2, min_size // plen)
        rxp = re.compile(rb"(.{%d})\1{%d,}" % (plen, rep - 1), re.S)
        for m in rxp.finditer(data):
            pat = m.group(1)
            if len(set(pat)) == 1:
                continue          # a single-byte run, already listed
            a, b = m.start(), m.end()
            if any(a < y and x < b for x, y in taken):
                continue
            # a pattern that is itself a repetition of a shorter one was found with that shorter length
            if any(pat == pat[:k] * (plen // k) for k in range(1, plen) if plen % k == 0):
                continue
            out.append(FillArea(a, b, pat))
            taken.append((a, b))
    out.sort(key=lambda f: f.start)
    return out


def used_size(data: bytes, areas: list[FillArea]) -> int:
    return len(data) - sum(a.size for a in areas)
