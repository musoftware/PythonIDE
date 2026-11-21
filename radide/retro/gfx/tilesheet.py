"""A view of raw bytes (a ROM or any binary file) as a sheet of tiles, plus pixel tools and byte-level undo.

Nothing here knows about Qt: the editor widgets (ui_tiles.py) and the tests drive the same model.
Pixel blocks are ``list[list[int]]`` (rows of colour indices).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .codecs import TileFormat, get_format

Block = list[list[int]]


@dataclass
class TileSheet:
    data: bytearray
    fmt: TileFormat
    offset: int = 0
    cols: int = 16
    rows: int = 16
    tile_h: int = 8              # variable-height formats (Atari 2600 players)
    bottom_up: bool = False      # rows stored bottom line first (many 2600 kernels count Y down)

    @classmethod
    def from_bytes(cls, data, fmt="nes", **kw) -> "TileSheet":
        f = get_format(fmt) if isinstance(fmt, str) else fmt
        return cls(bytearray(data), f, **kw)

    # ------------------------------------------------------------ geometry
    @property
    def stride(self) -> int:
        return self.fmt.size(self.tile_h)

    @property
    def tw(self) -> int:
        return self.fmt.width

    @property
    def th(self) -> int:
        return self.fmt.tile_height(self.tile_h)

    @property
    def page_bytes(self) -> int:
        return self.stride * self.cols * self.rows

    def tile_count(self) -> int:
        """Tiles from the offset to the end of the data (a partial last tile is padded with zeros)."""
        left = len(self.data) - self.offset
        return max(0, -(-left // self.stride))

    def tile_offset(self, index: int) -> int:
        return self.offset + index * self.stride

    def tile_at(self, tx: int, ty: int) -> int:
        return ty * self.cols + tx

    # ------------------------------------------------------------ tiles
    def get_tile(self, index: int) -> Block | None:
        off = self.tile_offset(index)
        if index < 0 or off >= len(self.data):
            return None
        flat = self.fmt.decode(self.data[off: off + self.stride], self.tile_h)
        rows = [flat[y * self.tw:(y + 1) * self.tw] for y in range(self.th)]
        return rows[::-1] if self.bottom_up else rows

    def encode_tile(self, block: Block) -> bytes:
        rows = block[::-1] if self.bottom_up else block
        return self.fmt.encode([p for r in rows for p in r], self.tile_h)

    def set_tile(self, index: int, block: Block) -> tuple[int, bytes, bytes] | None:
        """Write *block* into tile *index*; returns the (offset, old, new) change or None."""
        off = self.tile_offset(index)
        if index < 0 or off >= len(self.data):
            return None
        new = self.encode_tile(block)
        new = new[: len(self.data) - off]              # never grow the file
        old = bytes(self.data[off: off + len(new)])
        if old == new:
            return None
        self.data[off: off + len(new)] = new
        return off, old, new

    # ------------------------------------------------------------ blocks of tiles (selection)
    def get_block(self, tx: int, ty: int, tcols: int, trows: int) -> Block:
        """Pixels of a rectangle of tiles of the current page (-1 = past the end of the data)."""
        out: Block = [[-1] * (tcols * self.tw) for _ in range(trows * self.th)]
        for j in range(trows):
            for i in range(tcols):
                t = self.get_tile(self.tile_at(tx + i, ty + j))
                if t is None:
                    continue
                for y, row in enumerate(t):
                    out[j * self.th + y][i * self.tw:(i + 1) * self.tw] = row
        return out

    def set_block(self, tx: int, ty: int, block: Block) -> list[tuple[int, bytes, bytes]]:
        changes = []
        trows, tcols = len(block) // self.th, len(block[0]) // self.tw
        for j in range(trows):
            for i in range(tcols):
                tile = [row[i * self.tw:(i + 1) * self.tw] for row in block[j * self.th:(j + 1) * self.th]]
                if any(p < 0 for r in tile for p in r):
                    continue
                c = self.set_tile(self.tile_at(tx + i, ty + j), tile)
                if c:
                    changes.append(c)
        return changes

    def page(self) -> Block:
        return self.get_block(0, 0, self.cols, self.rows)


# ================================================================= pixel tools on blocks
def copy_block(b: Block) -> Block:
    return [list(r) for r in b]


def flip_h(b: Block) -> Block:
    return [r[::-1] for r in b]


def flip_v(b: Block) -> Block:
    return [list(r) for r in b[::-1]]


def rotate_cw(b: Block) -> Block:
    return [list(r) for r in zip(*b[::-1])]


def rotate_ccw(b: Block) -> Block:
    return [list(r) for r in zip(*b)][::-1]


def flood_fill(b: Block, x: int, y: int, color: int) -> Block:
    out = copy_block(b)
    h, w = len(out), len(out[0]) if out else 0
    if not (0 <= x < w and 0 <= y < h):
        return out
    target = out[y][x]
    if target == color or target < 0:
        return out
    stack = [(x, y)]
    while stack:
        cx, cy = stack.pop()
        if 0 <= cx < w and 0 <= cy < h and out[cy][cx] == target:
            out[cy][cx] = color
            stack.extend(((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)))
    return out


def line_points(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    """Bresenham line, both ends included."""
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return pts
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def draw_line(b: Block, x0, y0, x1, y1, color: int) -> Block:
    out = copy_block(b)
    for x, y in line_points(x0, y0, x1, y1):
        if 0 <= y < len(out) and 0 <= x < len(out[0]) and out[y][x] >= 0:
            out[y][x] = color
    return out


# ================================================================= undo / redo of byte changes
@dataclass
class ByteHistory:
    """Undo stack of byte edits: every entry is a list of (offset, old bytes, new bytes)."""
    undo_stack: list = field(default_factory=list)
    redo_stack: list = field(default_factory=list)
    clean_index: int = 0

    def push(self, changes: list[tuple[int, bytes, bytes]]) -> None:
        if changes:
            if self.clean_index > len(self.undo_stack):
                self.clean_index = -1                 # the saved state can no longer be reached
            self.undo_stack.append(list(changes))
            self.redo_stack.clear()

    def undo(self, data: bytearray) -> list | None:
        if not self.undo_stack:
            return None
        ch = self.undo_stack.pop()
        for off, old, _new in reversed(ch):
            data[off: off + len(old)] = old
        self.redo_stack.append(ch)
        return ch

    def redo(self, data: bytearray) -> list | None:
        if not self.redo_stack:
            return None
        ch = self.redo_stack.pop()
        for off, _old, new in ch:
            data[off: off + len(new)] = new
        self.undo_stack.append(ch)
        return ch

    def mark_clean(self) -> None:
        self.clean_index = len(self.undo_stack)

    @property
    def modified(self) -> bool:
        return len(self.undo_stack) != self.clean_index


# ================================================================= where the graphics usually are
def ines_chr_offset(data: bytes) -> int | None:
    """File offset of CHR-ROM in an iNES / NES 2.0 file (None when there is no CHR-ROM)."""
    if len(data) < 16 or data[:4] != b"NES\x1a":
        return None
    prg, chr_ = data[4], data[5]
    if chr_ == 0:
        return None
    trainer = 512 if data[6] & 4 else 0
    off = 16 + trainer + prg * 16384
    return off if off < len(data) else None


def suggested_offset(data: bytes, fmt_key: str) -> int:
    if fmt_key == "nes":
        off = ines_chr_offset(data)
        if off is not None:
            return off
    if fmt_key in ("c64spr", "c64sprmc", "c64mc", "1bpp") and len(data) > 2 and len(data) % 64 == 2:
        return 2                                  # .prg load address in front of sprite blocks
    return 0
