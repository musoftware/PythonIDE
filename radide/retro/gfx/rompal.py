"""Palettes stored in a ROM: read them for the Tile Editor and write edits back (pure Python, no Qt).

Layouts (``LAYOUTS`` keys):

==============  =============================================================================================
``nes4``        NES: 4 bytes per sub-palette ($00-$3F PPU colour numbers), 8 sub-palettes = the 32-byte block a
                game copies to $3F00 (4 background + 4 sprite palettes)
``nes_slot``    NES: one byte per sub-palette for ONE colour slot (games that build palettes in code, e.g. a
                table of "colour 2" values) - the other slots keep their colours
``gb_bgp``      Game Boy BGP / OBP0 / OBP1 register value: 1 byte, 2 bits per colour = shade 0-3
``bgr555``      Game Boy Color / SNES / GBA: 2 bytes per colour, little endian %0BBBBBGGGGGRRRRR
                (4 colours per sub-palette for 2bpp tiles, 16 for 4bpp)
``genesis``     Mega Drive / Genesis CRAM words: big endian %0000BBB0GGG0RRR0, 16 colours per palette
==============  =============================================================================================

A ``RomPalette`` binds the colour slots of the Tile Editor to ROM bytes. ``colors()`` gives RGB tuples,
``set_slot()`` changes the bytes (the editor writes them into the file with Save).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import palettes

LAYOUTS = {
    "nes4": "NES palette table (4 bytes per sub-palette)",
    "nes_slot": "NES: one colour slot per byte",
    "gb_bgp": "Game Boy BGP / OBP register (1 byte)",
    "bgr555": "GBC / SNES / GBA BGR555 (2 bytes per colour)",
    "genesis": "Mega Drive / Genesis CRAM (2 bytes per colour)",
}


def bgr555_to_rgb(v: int) -> tuple[int, int, int]:
    r, g, b = v & 31, (v >> 5) & 31, (v >> 10) & 31
    return (r << 3) | (r >> 2), (g << 3) | (g >> 2), (b << 3) | (b >> 2)


def rgb_to_bgr555(rgb) -> int:
    r, g, b = (max(0, min(255, int(c))) for c in rgb[:3])
    return ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)


def genesis_to_rgb(v: int) -> tuple[int, int, int]:
    r, g, b = (v >> 1) & 7, (v >> 5) & 7, (v >> 9) & 7
    return r * 255 // 7, g * 255 // 7, b * 255 // 7


def rgb_to_genesis(rgb) -> int:
    r, g, b = (max(0, min(255, int(c))) * 7 // 255 for c in rgb[:3])
    return (b << 9) | (g << 5) | (r << 1)


@dataclass
class RomPalette:
    layout: str
    offset: int                  # file offset of the table
    index: int = 0               # which sub-palette
    colors_n: int = 4            # colours per sub-palette (bgr555 / genesis)
    slot: int = 2                # nes_slot: the colour slot the bytes are for
    base: list = field(default_factory=lambda: [0x0F, 0x16, 0x27, 0x30])   # nes_slot: the other slots

    # ---------------------------------------------------------------- where the bytes are
    def slot_offsets(self) -> list[int | None]:
        """File offset of the byte (first byte) of every colour slot; None = not stored in the ROM."""
        o = self.offset
        if self.layout == "nes4":
            return [o + 4 * self.index + i for i in range(4)]
        if self.layout == "nes_slot":
            return [o + self.index if i == self.slot else None for i in range(4)]
        if self.layout == "gb_bgp":
            return [o + self.index] * 4
        if self.layout in ("bgr555", "genesis"):
            return [o + 2 * (self.colors_n * self.index + i) for i in range(self.colors_n)]
        raise ValueError(self.layout)

    def span(self) -> tuple[int, int]:
        offs = [x for x in self.slot_offsets() if x is not None]
        width = 2 if self.layout in ("bgr555", "genesis") else 1
        return min(offs), max(offs) + width

    # ---------------------------------------------------------------- reading
    def system(self) -> str:
        return {"nes4": "nes", "nes_slot": "nes", "gb_bgp": "gb"}.get(self.layout, "")

    def slots(self, data) -> list[int]:
        """System palette indices (NES colour numbers / GB shades) - only for the indexed layouts."""
        offs = self.slot_offsets()
        if self.layout == "nes4":
            return [data[x] & 0x3F for x in offs]
        if self.layout == "nes_slot":
            return [data[x] & 0x3F if x is not None else self.base[i] & 0x3F for i, x in enumerate(offs)]
        if self.layout == "gb_bgp":
            v = data[offs[0]]
            return [(v >> (2 * i)) & 3 for i in range(4)]
        raise ValueError(f"{self.layout} has no system palette indices")

    def colors(self, data) -> list[tuple[int, int, int]]:
        if self.layout in ("nes4", "nes_slot", "gb_bgp"):
            pal = palettes.palette(self.system())
            return [pal[i % len(pal)] for i in self.slots(data)]
        offs = self.slot_offsets()
        if self.layout == "bgr555":
            return [bgr555_to_rgb(data[x] | (data[x + 1] << 8)) for x in offs]
        return [genesis_to_rgb((data[x] << 8) | data[x + 1]) for x in offs]

    def valid(self, data) -> bool:
        try:
            a, b = self.span()
        except ValueError:
            return False
        return 0 <= a and b <= len(data)

    # ---------------------------------------------------------------- writing
    def set_slot(self, data: bytearray, slot: int, value) -> list[tuple[int, bytes, bytes]]:
        """Write colour *slot*: a system palette index (NES / GB) or an (r, g, b) tuple (BGR555 / Genesis).
        Returns the byte changes [(offset, old, new)]; nothing for slots that are not in the ROM."""
        offs = self.slot_offsets()
        if not 0 <= slot < len(offs) or offs[slot] is None:
            return []
        x = offs[slot]
        if self.layout in ("nes4", "nes_slot"):
            new = bytes([int(value) & 0x3F])
        elif self.layout == "gb_bgp":
            v = data[x]
            v = (v & ~(3 << (2 * slot))) | ((int(value) & 3) << (2 * slot))
            new = bytes([v & 0xFF])
        elif self.layout == "bgr555":
            w = rgb_to_bgr555(value)
            new = bytes((w & 0xFF, w >> 8))
        else:
            w = rgb_to_genesis(value)
            new = bytes((w >> 8, w & 0xFF))
        old = bytes(data[x:x + len(new)])
        if old == new:
            return []
        data[x:x + len(new)] = new
        return [(x, old, new)]

    def to_dict(self) -> dict:
        return {"layout": self.layout, "offset": self.offset, "index": self.index, "colors": self.colors_n,
                "slot": self.slot, "base": list(self.base)}

    @classmethod
    def from_dict(cls, d: dict) -> "RomPalette":
        return cls(str(d.get("layout", "nes4")), int(d.get("offset", 0)), int(d.get("index", 0)),
                   int(d.get("colors", 4)), int(d.get("slot", 2)), list(d.get("base", [0x0F, 0x16, 0x27, 0x30])))


# ====================================================================== finding palette tables
@dataclass
class PaletteCandidate:
    layout: str
    offset: int
    length: int
    score: float
    preview: list                 # RGB tuples of the whole table

    def label(self) -> str:
        what = {"nes4": "NES", "bgr555": "BGR555"}.get(self.layout, self.layout)
        return f"0x{self.offset:06X}  {what} {self.length} bytes  (score {self.score:.2f})"


def find_nes_palettes(data, length: int = 32, max_results: int = 40) -> list[PaletteCandidate]:
    """32-byte (or 16-byte) blocks that look like NES palettes: every byte $00-$3F (no $0D: "blacker than black"
    is avoided by games), the first colour of each 4-byte group mostly the same (the shared background), several
    different colours, not a run of one value."""
    data = bytes(data)
    pal = palettes.palette("nes")
    out = []
    n = len(data)
    i = 0
    while i + length <= n:
        blk = data[i:i + length]
        if max(blk) > 0x3F or 0x0D in blk:
            i += 1
            continue
        firsts = [blk[k] for k in range(0, length, 4)]
        common = max(set(firsts), key=firsts.count)
        same_bg = firsts.count(common) / len(firsts)
        distinct = len(set(blk))
        if same_bg < 0.75 or distinct < 5 or blk.count(blk[0]) > length * 0.6:
            i += 1
            continue
        # NES colours in palettes: dark ($0x) .. light ($3x) columns, black $0F; a good table uses several rows
        rows = len({b >> 4 for b in blk})
        score = same_bg * min(1.0, distinct / 12) * (0.6 + 0.1 * rows) + (0.15 if common in (0x0F, 0x30, 0x21, 0x22) else 0)
        out.append(PaletteCandidate("nes4", i, length, round(score, 3), [pal[b] for b in blk]))
        i += 4 if score > 0.6 else 1
    out.sort(key=lambda c: -c.score)
    picked: list[PaletteCandidate] = []
    for c in out:
        if all(abs(c.offset - p.offset) >= length for p in picked):
            picked.append(c)
        if len(picked) >= max_results:
            break
    return picked


def find_bgr555_palettes(data, colors: int = 4, max_results: int = 40) -> list[PaletteCandidate]:
    """GBC / SNES / GBA palettes: groups of words with bit 15 clear, 3+ different colours, white ($7FFF) or
    black ($0000) at one end - the usual first / last colour."""
    data = bytes(data)
    out = []
    size = colors * 2
    for i in range(0, len(data) - size * 2 + 1, 2):
        words = [data[i + 2 * k] | (data[i + 2 * k + 1] << 8) for k in range(colors * 2)]
        if any(w & 0x8000 for w in words):
            continue
        first = words[:colors]
        if len(set(first)) < 3:
            continue
        ends = sum(1 for w in (first[0], first[-1]) if w in (0x0000, 0x7FFF))
        if not ends:
            continue
        score = 0.5 + 0.2 * ends + 0.1 * min(3, len(set(first)) - 2) + (0.05 if i % 8 == 0 else 0)
        out.append(PaletteCandidate("bgr555", i, size, round(score, 3), [bgr555_to_rgb(w) for w in first]))
    out.sort(key=lambda c: -c.score)
    picked = []
    for c in out:
        if all(abs(c.offset - p.offset) >= c.length for p in picked):
            picked.append(c)
        if len(picked) >= max_results:
            break
    return picked


def find_palettes(data, layout: str = "nes4", **kw) -> list[PaletteCandidate]:
    if layout == "bgr555":
        return find_bgr555_palettes(data, **kw)
    return find_nes_palettes(data, **kw)


__all__ = ["LAYOUTS", "PaletteCandidate", "RomPalette", "bgr555_to_rgb", "find_bgr555_palettes",
           "find_nes_palettes", "find_palettes", "genesis_to_rgb", "rgb_to_bgr555", "rgb_to_genesis"]
