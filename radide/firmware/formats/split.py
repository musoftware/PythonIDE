"""Split / merge helpers for firmware dumps:

* interleave / deinterleave: 16-bit buses built from two 8-bit EPROMs (even = low byte chip, odd = high byte
  chip), or four chips on a 32-bit bus;
* byte swap of 16-bit / 32-bit words (dumps read with the wrong endianness);
* split one image into chips / flash banks of given sizes, and concatenate them again (e.g. internal flash +
  external flash, or a 1 MB file into two 512 KB EPROMs);
* merge memory maps (internal flash at 0x80000000 + external at 0x... -> one image with a gap).

Pure Python; every function returns new bytes and never changes its input.
"""
from __future__ import annotations

from .memmap import MemoryMap


def deinterleave(data: bytes, ways: int = 2, width: int = 1) -> list[bytes]:
    """Split *data* into *ways* chip images, *width* bytes per chip per bus cycle.
    ways=2, width=1: [even bytes, odd bytes] (two 8-bit EPROMs on a 16-bit bus)."""
    if ways < 2:
        return [bytes(data)]
    step = ways * width
    if len(data) % step:
        raise ValueError(f"size {len(data)} is not a multiple of {step}")
    out = []
    for w in range(ways):
        chip = bytearray(len(data) // ways)
        for k in range(width):
            chip[k::width] = data[w * width + k::step]
        out.append(bytes(chip))
    return out


def interleave(chips: list[bytes], width: int = 1) -> bytes:
    """The inverse of :func:`deinterleave`: [even, odd] -> one 16-bit image."""
    if not chips:
        return b""
    n = len(chips[0])
    if any(len(c) != n for c in chips):
        raise ValueError("all chip images must have the same size")
    if n % width:
        raise ValueError(f"chip size {n} is not a multiple of {width}")
    ways = len(chips)
    out = bytearray(n * ways)
    step = ways * width
    for w, chip in enumerate(chips):
        for k in range(width):
            out[w * width + k::step] = chip[k::width]
    return bytes(out)


def byteswap(data: bytes, width: int = 2) -> bytes:
    """Swap the byte order of every *width*-byte word (2: AB CD -> BA DC, 4: ABCD -> DCBA)."""
    if width not in (2, 4, 8):
        raise ValueError("width must be 2, 4 or 8")
    if len(data) % width:
        raise ValueError(f"size {len(data)} is not a multiple of {width}")
    out = bytearray(len(data))
    for k in range(width):
        out[k::width] = data[width - 1 - k::width]
    return bytes(out)


def wordswap(data: bytes) -> bytes:
    """Swap the two 16-bit halves of every 32-bit word (ABCD -> CDAB, 'word swap' of some readers)."""
    if len(data) % 4:
        raise ValueError(f"size {len(data)} is not a multiple of 4")
    out = bytearray(len(data))
    out[0::4], out[1::4], out[2::4], out[3::4] = data[2::4], data[3::4], data[0::4], data[1::4]
    return bytes(out)


def split_sizes(data: bytes, sizes: list[int]) -> list[bytes]:
    """Cut *data* into consecutive parts; the last size may be 0 = 'the rest'."""
    out, pos = [], 0
    for i, n in enumerate(sizes):
        if n <= 0 and i == len(sizes) - 1:
            n = len(data) - pos
        out.append(bytes(data[pos:pos + n]))
        pos += n
    if pos < len(data):
        out.append(bytes(data[pos:]))
    return out


def split_equal(data: bytes, parts: int) -> list[bytes]:
    if parts < 1 or len(data) % parts:
        raise ValueError(f"size {len(data)} cannot be split into {parts} equal parts")
    n = len(data) // parts
    return [bytes(data[i * n:(i + 1) * n]) for i in range(parts)]


def concat(parts: list[bytes]) -> bytes:
    return b"".join(bytes(p) for p in parts)


def merge_maps(maps: list[tuple[MemoryMap, int]]) -> MemoryMap:
    """Merge memory maps; each (map, offset) is moved by *offset* first. Later maps win on overlaps."""
    out = MemoryMap()
    for m, delta in maps:
        for s in m.segments:
            out.add(s.address + delta, bytes(s.data), s.name, s.flags)
        if out.start is None and m.start is not None:
            out.start = m.start + delta
        out.symbols += [type(sym)(sym.name, sym.address + delta, sym.size, sym.kind) for sym in m.symbols]
    return out


def overlaps(maps: list[tuple[MemoryMap, int]]) -> list[tuple[int, int]]:
    """Address ranges covered by more than one of *maps* (to warn before merging)."""
    ranges = sorted((s.address + d, s.end + d) for m, d in maps for s in m.segments)
    out = []
    for (a0, a1), (b0, b1) in zip(ranges, ranges[1:]):
        if b0 < a1:
            out.append((b0, min(a1, b1)))
    return out
