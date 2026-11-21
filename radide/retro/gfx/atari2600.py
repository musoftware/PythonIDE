"""Atari 2600 (TIA) graphics helpers: the playfield bit order and the player reflect / NUSIZ preview.

Playfield: 20 bits per half scan line (each bit is 4 colour clocks wide), from left to right:

* PF0 bits 4, 5, 6, 7   (the low nibble is not displayed)
* PF1 bits 7, 6, 5, 4, 3, 2, 1, 0
* PF2 bits 0, 1, 2, 3, 4, 5, 6, 7

The right half repeats the left half, or mirrors it when CTRLPF bit 0 (REF) is set.  An *asymmetric*
playfield rewrites PF0-PF2 in the middle of the line, so it needs a second set of three tables.

Players: an 8-bit GRP0/GRP1 byte, bit 7 = left pixel (REFP0 bit 3 reflects it); NUSIZ0 bits 0-2 choose
copies and stretch.
"""
from __future__ import annotations

PF_WIDTH = 20

# playfield bit position -> (register, bit)
PF_BITS: list[tuple[str, int]] = ([("PF0", b) for b in (4, 5, 6, 7)] + [("PF1", b) for b in range(7, -1, -1)]
                                  + [("PF2", b) for b in range(8)])


def bytes_to_half(pf0: int, pf1: int, pf2: int) -> list[int]:
    regs = {"PF0": pf0, "PF1": pf1, "PF2": pf2}
    return [(regs[r] >> b) & 1 for r, b in PF_BITS]


def half_to_bytes(bits: list[int]) -> tuple[int, int, int]:
    if len(bits) != PF_WIDTH:
        raise ValueError("a playfield half has 20 bits")
    regs = {"PF0": 0, "PF1": 0, "PF2": 0}
    for (r, b), v in zip(PF_BITS, bits):
        if v:
            regs[r] |= 1 << b
    return regs["PF0"], regs["PF1"], regs["PF2"]


def full_line(left: list[int], right: list[int] | None = None, reflect: bool = False) -> list[int]:
    """40 playfield pixels of a scan line."""
    if right is None:
        right = left[::-1] if reflect else list(left)
    return list(left) + list(right)


class Playfield:
    """A playfield picture: *height* rows of 40 pixels (0/1)."""

    def __init__(self, height: int = 24, reflect: bool = False, asymmetric: bool = False):
        self.height = height
        self.reflect = reflect
        self.asymmetric = asymmetric
        self.rows: list[list[int]] = [[0] * 40 for _ in range(height)]

    def resize(self, height: int) -> None:
        if height < self.height:
            self.rows = self.rows[:height]
        else:
            self.rows += [[0] * 40 for _ in range(height - self.height)]
        self.height = height

    def get(self, x: int, y: int) -> int:
        return self.display_row(y)[x]

    def set(self, x: int, y: int, v: int) -> None:
        """Set a pixel; in symmetric mode the right half follows the left half."""
        row = self.rows[y]
        if not self.asymmetric and x >= PF_WIDTH:
            x = (39 - x) if self.reflect else (x - PF_WIDTH)
        row[x] = 1 if v else 0

    def display_row(self, y: int) -> list[int]:
        row = self.rows[y]
        if self.asymmetric:
            return list(row)
        return full_line(row[:PF_WIDTH], None, self.reflect)

    # ------------------------------------------------------------ tables
    def tables(self) -> dict[str, list[int]]:
        """PF0/PF1/PF2 tables (top row first) and, for an asymmetric playfield, PF0R/PF1R/PF2R."""
        out: dict[str, list[int]] = {"PF0": [], "PF1": [], "PF2": []}
        if self.asymmetric:
            out.update({"PF0R": [], "PF1R": [], "PF2R": []})
        for y in range(self.height):
            row = self.rows[y]
            for k, v in zip(("PF0", "PF1", "PF2"), half_to_bytes(row[:PF_WIDTH])):
                out[k].append(v)
            if self.asymmetric:
                for k, v in zip(("PF0R", "PF1R", "PF2R"), half_to_bytes(row[PF_WIDTH:])):
                    out[k].append(v)
        return out

    @classmethod
    def from_tables(cls, pf0, pf1, pf2, pf0r=None, pf1r=None, pf2r=None, reflect=False) -> "Playfield":
        asym = pf0r is not None
        pf = cls(len(pf0), reflect, asym)
        for y in range(len(pf0)):
            left = bytes_to_half(pf0[y], pf1[y], pf2[y])
            right = bytes_to_half(pf0r[y], pf1r[y], pf2r[y]) if asym else [0] * PF_WIDTH
            pf.rows[y] = left + right
        return pf

    @classmethod
    def from_binary(cls, data: bytes, offset: int, height: int, layout: str = "tables",
                    reflect: bool = False, asymmetric: bool = False) -> "Playfield":
        """Read from a ROM: ``tables`` = PF0[height], PF1[height], PF2[height] (then the right-half tables);
        ``interleaved`` = PF0, PF1, PF2 (, PF0R, PF1R, PF2R) per row."""
        n = 6 if asymmetric else 3
        vals = [[0] * height for _ in range(n)]
        for y in range(height):
            for k in range(n):
                i = offset + (k * height + y if layout == "tables" else y * n + k)
                vals[k][y] = data[i] if i < len(data) else 0
        return cls.from_tables(*vals, reflect=reflect) if asymmetric else \
            cls.from_tables(vals[0], vals[1], vals[2], reflect=reflect)

    def to_binary(self, data: bytearray, offset: int, layout: str = "tables") -> list[tuple[int, bytes, bytes]]:
        """Write the tables back into *data* (PF0's unused low nibble keeps its old value)."""
        t = self.tables()
        keys = ["PF0", "PF1", "PF2"] + (["PF0R", "PF1R", "PF2R"] if self.asymmetric else [])
        n = len(keys)
        changes = []
        for k, key in enumerate(keys):
            for y, v in enumerate(t[key]):
                i = offset + (k * self.height + y if layout == "tables" else y * n + k)
                if i >= len(data):
                    raise ValueError(f"the playfield does not fit: byte {i:#x} is past the end of the file")
                if key.startswith("PF0"):
                    v = (v & 0xF0) | (data[i] & 0x0F)
                if data[i] != v:
                    changes.append((i, bytes([data[i]]), bytes([v])))
                    data[i] = v
        return changes

    def export_asm(self, label: str = "Playfield", syntax: str = "dasm", reverse: bool = False) -> str:
        """Data tables for DASM (``.byte``, ``%`` binary) or ca65 (``.byte``) / ACME (``!byte``)."""
        directive = {"dasm": "    .byte", "ca65": "    .byte", "acme": "    !byte", "c": None}.get(syntax, "    .byte")
        t = self.tables()
        lines = [f"; {label}: {self.height} rows, "
                 f"{'asymmetric' if self.asymmetric else ('reflected' if self.reflect else 'repeated')} playfield",
                 "; PF0 uses bits 4-7 (left to right D4..D7), PF1 D7..D0, PF2 D0..D7"]
        for key, vals in t.items():
            vals = vals[::-1] if reverse else vals
            if directive is None:
                lines.append(f"const unsigned char {label}_{key}[{len(vals)}] = {{")
                lines.append("    " + ", ".join(f"0x{v:02X}" for v in vals))
                lines.append("};")
                continue
            lines.append(f"{label}_{key}:")
            for v in vals:
                lines.append(f"{directive} %{v:08b}")
        return "\n".join(lines) + "\n"


# ===================================================================== players
def reflect_byte(b: int) -> int:
    return int(f"{b & 0xFF:08b}"[::-1], 2)


# NUSIZ bits 0-2 -> (copy start offsets in colour clocks, pixel width)
NUSIZ_LAYOUT: dict[int, tuple[tuple[int, ...], int]] = {
    0: ((0,), 1), 1: ((0, 16), 1), 2: ((0, 32), 1), 3: ((0, 16, 32), 1),
    4: ((0, 64), 1), 5: ((0,), 2), 6: ((0, 32, 64), 1), 7: ((0,), 4),
}
NUSIZ_NAMES = ["one copy", "two copies - close", "two copies - medium", "three copies - close",
               "two copies - wide", "double size", "three copies - medium", "quad size"]


def player_scanline(grp: int, nusiz: int = 0, reflect: bool = False, x: int = 0, width: int = 160) -> list[int]:
    """The *width* colour clocks of one scan line showing player byte *grp* at horizontal position *x*."""
    line = [0] * width
    bits = reflect_byte(grp) if reflect else grp & 0xFF
    starts, scale = NUSIZ_LAYOUT[nusiz & 7]
    for s in starts:
        for i in range(8):
            if (bits >> (7 - i)) & 1:
                for k in range(scale):
                    px = (x + s + i * scale + k) % width
                    line[px] = 1
    return line
