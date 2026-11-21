"""A text-mode screen: rows x cols cells of (CP437 character, attribute) - the same layout as the
video memory at B800:0000 (character byte, attribute byte). No Qt in here."""
from __future__ import annotations

from .cp437 import BORDERS, box_char, BOX, encode


class CellBuffer:
    __slots__ = ("cols", "rows", "chars", "attrs")

    def __init__(self, cols: int = 80, rows: int = 25, ch: int = 0x20, attr: int = 0x07):
        self.cols = cols
        self.rows = rows
        self.chars = bytearray([ch]) * (cols * rows)
        self.attrs = bytearray([attr]) * (cols * rows)

    # ---------------------------------------------------------------- basics
    def copy(self) -> "CellBuffer":
        b = CellBuffer.__new__(CellBuffer)
        b.cols, b.rows = self.cols, self.rows
        b.chars = bytearray(self.chars)
        b.attrs = bytearray(self.attrs)
        return b

    def inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.cols and 0 <= y < self.rows

    def get(self, x: int, y: int) -> tuple[int, int]:
        i = y * self.cols + x
        return self.chars[i], self.attrs[i]

    def put(self, x: int, y: int, ch: int | None, attr: int | None = None) -> None:
        if 0 <= x < self.cols and 0 <= y < self.rows:
            i = y * self.cols + x
            if ch is not None:
                self.chars[i] = ch & 0xFF
            if attr is not None:
                self.attrs[i] = attr & 0xFF

    def fill(self, x: int, y: int, w: int, h: int, ch: int | None, attr: int | None) -> None:
        for yy in range(max(0, y), min(self.rows, y + h)):
            for xx in range(max(0, x), min(self.cols, x + w)):
                self.put(xx, yy, ch, attr)

    def text(self, x: int, y: int, s, attr: int | None, width: int | None = None) -> None:
        """Write *s* (str in Unicode, or CP437 bytes) at x, y; padded with spaces / cut to *width*."""
        data = s if isinstance(s, (bytes, bytearray)) else encode(s)
        if width is not None:
            data = bytes(data[:width]).ljust(width, b" ")
        for i, b in enumerate(data):
            self.put(x + i, y, b, attr)

    def hot_text(self, x: int, y: int, s: str, mask: str, attr: int, hot: int, width: int | None = None) -> None:
        data = encode(s)
        if width is not None:
            data = data[:width].ljust(width, b" ")
        for i, b in enumerate(data):
            self.put(x + i, y, b, hot if i < len(mask) and mask[i] == "1" else attr)

    def box(self, x: int, y: int, w: int, h: int, style: str, attr: int, fill: bool = False,
            fill_attr: int | None = None) -> None:
        if w < 1 or h < 1:
            return
        if fill:
            self.fill(x, y, w, h, 0x20, attr if fill_attr is None else fill_attr)
        if style not in BORDERS:
            return
        tl, top, tr, left, right, bl, br = BORDERS[style]
        bottom = 0xDC if style == "block" else top
        if h == 1:
            self.fill(x, y, w, 1, top, attr)
            return
        if w == 1:
            self.fill(x, y, 1, h, left, attr)
            return
        self.put(x, y, tl, attr)
        self.put(x + w - 1, y, tr, attr)
        self.put(x, y + h - 1, bl, attr)
        self.put(x + w - 1, y + h - 1, br, attr)
        for xx in range(x + 1, x + w - 1):
            self.put(xx, y, top, attr)
            self.put(xx, y + h - 1, bottom, attr)
        for yy in range(y + 1, y + h - 1):
            self.put(x, yy, left, attr)
            self.put(x + w - 1, yy, right, attr)

    def shadow(self, x: int, y: int, w: int, h: int) -> None:
        """The classic drop shadow: 2 columns to the right and 1 row below turn dark grey on black."""
        for yy in range(y + 1, y + h + 1):
            for xx in (x + w, x + w + 1):
                self.put(xx, yy, None, 0x08)
        for xx in range(x + 2, x + w + 2):
            self.put(xx, y + h, None, 0x08)

    def line_join(self, x: int, y: int, weight: int, attr: int | None, dirs: str) -> None:
        """Merge line arms (*dirs* from "udlr") of *weight* into the line-drawing character at x, y."""
        if not self.inside(x, y):
            return
        cur = BOX.get(self.get(x, y)[0], (0, 0, 0, 0))
        arms = list(cur)
        for d in dirs:
            arms["udlr".index(d)] = weight
        self.put(x, y, box_char(*arms), attr)

    def blit(self, other: "CellBuffer", x: int = 0, y: int = 0) -> None:
        for yy in range(other.rows):
            for xx in range(other.cols):
                c, a = other.get(xx, yy)
                self.put(x + xx, y + yy, c, a)

    def region(self, x: int, y: int, w: int, h: int) -> "CellBuffer":
        b = CellBuffer(w, h)
        for yy in range(h):
            for xx in range(w):
                if self.inside(x + xx, y + yy):
                    b.put(xx, yy, *self.get(x + xx, y + yy))
        return b

    def resized(self, cols: int, rows: int, ch: int = 0x20, attr: int = 0x07) -> "CellBuffer":
        b = CellBuffer(cols, rows, ch, attr)
        b.blit(self)
        return b

    # ---------------------------------------------------------------- B800 layout
    def to_bin(self) -> bytes:
        """Raw video memory: (char, attr) per cell, row by row (the .BIN art format / a B800 dump)."""
        out = bytearray(self.cols * self.rows * 2)
        out[0::2] = self.chars
        out[1::2] = self.attrs
        return bytes(out)

    @classmethod
    def from_bin(cls, data: bytes, cols: int = 80) -> "CellBuffer":
        cells = len(data) // 2
        rows = max(1, (cells + cols - 1) // cols)
        b = cls(cols, rows)
        n = min(cells, cols * rows)
        b.chars[:n] = data[0:n * 2:2]
        b.attrs[:n] = data[1:n * 2:2]
        return b

    def plain_text(self) -> str:
        from .cp437 import decode
        return "\n".join(decode(bytes(self.chars[r * self.cols:(r + 1) * self.cols])).rstrip()
                         for r in range(self.rows))

    def diff(self, other: "CellBuffer") -> list[tuple[int, int, tuple[int, int], tuple[int, int]]]:
        """Cells that differ: [(x, y, (ch, attr) here, (ch, attr) there)]."""
        out = []
        for y in range(min(self.rows, other.rows)):
            for x in range(min(self.cols, other.cols)):
                a, b = self.get(x, y), other.get(x, y)
                if a != b:
                    out.append((x, y, a, b))
        return out

    def __eq__(self, other) -> bool:
        return isinstance(other, CellBuffer) and self.cols == other.cols and self.rows == other.rows and \
            self.chars == other.chars and self.attrs == other.attrs

    def rle(self) -> list[tuple[int, int, int]]:
        """Runs of identical cells, row by row (a run never crosses a line end): [(count, ch, attr)]."""
        out: list[tuple[int, int, int]] = []
        for y in range(self.rows):
            x = 0
            while x < self.cols:
                c, a = self.get(x, y)
                n = 1
                while x + n < self.cols and self.get(x + n, y) == (c, a):
                    n += 1
                out.append((n, c, a))
                x += n
        return out
