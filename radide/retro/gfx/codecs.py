"""Tile / sprite pixel formats of old consoles and home computers (pure Python, no Qt).

A tile is decoded to a flat list of colour indices (row by row, ``width * height`` values) and encoded back
to the bytes the hardware reads.  ``stride`` is how far the next tile starts (a C64 sprite is 63 data bytes in
a 64-byte block); ``encode`` returns only the data bytes so padding in the ROM is never overwritten.

Formats (``FORMATS`` keys):

==============  =====================================================================================
``1bpp``        8x8, one byte per row, bit 7 = left pixel (also ZX Spectrum / C64 hires charset)
``nes``         NES / Famicom CHR 2bpp planar: 8 bytes plane 0, then 8 bytes plane 1
``gb``          Game Boy / SNES 2bpp: per row a low-plane byte then a high-plane byte
``snes4``       SNES / PC Engine 4bpp: planes 0+1 interleaved (16 bytes), then planes 2+3 (16 bytes)
``genesis``     Mega Drive / Genesis 4bpp packed, high nibble = left pixel
``gba4``        Game Boy Advance / DS 4bpp packed, low nibble = left pixel
``c64mc``       C64 multicolour charset: 4x8 double-wide pixels, 2 bits each
``c64spr``      C64 hires sprite 24x21 (63 bytes in a 64-byte block)
``c64sprmc``    C64 multicolour sprite 12x21 double-wide pixels
``a2600``       Atari 2600 player graphics: 8 pixels wide, ``height`` bytes, one byte per scan line
==============  =====================================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class TileFormat:
    key: str
    name: str
    width: int
    height: int
    bpp: int
    stride: int                 # bytes from one tile to the next
    system: str                 # default system palette key (palettes.SYSTEM_PALETTES)
    aspect: int = 1             # horizontal pixel stretch (C64 multicolour pixels are double wide)
    var_height: bool = False    # height chosen by the user (Atari 2600 players)
    _dec: Callable | None = None
    _enc: Callable | None = None

    @property
    def colors(self) -> int:
        return 1 << self.bpp

    def size(self, height: int | None = None) -> int:
        """Bytes per tile (the stride) for *height* (variable-height formats)."""
        if self.var_height:
            return int(height or self.height) * self.width * self.bpp // 8
        return self.stride

    def data_len(self, height: int | None = None) -> int:
        h = int(height or self.height) if self.var_height else self.height
        return self.width * h * self.bpp // 8

    def tile_height(self, height: int | None = None) -> int:
        return int(height or self.height) if self.var_height else self.height

    def decode(self, data: bytes, height: int | None = None) -> list[int]:
        h = self.tile_height(height)
        need = self.data_len(height)
        buf = bytes(data[:need])
        if len(buf) < need:
            buf = buf + bytes(need - len(buf))
        return self._dec(buf, self.width, h)

    def encode(self, pixels: list[int], height: int | None = None) -> bytes:
        h = self.tile_height(height)
        if len(pixels) != self.width * h:
            raise ValueError(f"{self.key}: expected {self.width * h} pixels, got {len(pixels)}")
        mask = self.colors - 1
        return bytes(self._enc([int(p) & mask for p in pixels], self.width, h))


# ------------------------------------------------------------------ 1 bit per pixel, row bytes
def _dec_1bpp(buf: bytes, w: int, h: int) -> list[int]:
    out: list[int] = []
    bpr = w // 8
    for y in range(h):
        for bx in range(bpr):
            b = buf[y * bpr + bx]
            out.extend((b >> (7 - i)) & 1 for i in range(8))
    return out


def _enc_1bpp(px: list[int], w: int, h: int) -> bytearray:
    out = bytearray()
    for y in range(h):
        for bx in range(w // 8):
            b = 0
            for i in range(8):
                b |= (px[y * w + bx * 8 + i] & 1) << (7 - i)
            out.append(b)
    return out


# ------------------------------------------------------------------ NES planar 2bpp
def _dec_nes(buf: bytes, w: int, h: int) -> list[int]:
    out = []
    for y in range(8):
        lo, hi = buf[y], buf[y + 8]
        out.extend(((lo >> (7 - i)) & 1) | (((hi >> (7 - i)) & 1) << 1) for i in range(8))
    return out


def _enc_nes(px: list[int], w: int, h: int) -> bytearray:
    out = bytearray(16)
    for y in range(8):
        lo = hi = 0
        for i in range(8):
            p = px[y * 8 + i]
            lo |= (p & 1) << (7 - i)
            hi |= ((p >> 1) & 1) << (7 - i)
        out[y], out[y + 8] = lo, hi
    return out


# ------------------------------------------------------------------ interleaved planes (GB / SNES)
def _dec_interleaved(buf: bytes, w: int, h: int, planes: int) -> list[int]:
    out = [0] * 64
    for y in range(8):
        for pair in range(planes // 2):
            base = pair * 16 + y * 2
            lo, hi = buf[base], buf[base + 1]
            for i in range(8):
                v = ((lo >> (7 - i)) & 1) | (((hi >> (7 - i)) & 1) << 1)
                out[y * 8 + i] |= v << (pair * 2)
    return out


def _enc_interleaved(px: list[int], w: int, h: int, planes: int) -> bytearray:
    out = bytearray(planes * 8)
    for y in range(8):
        for pair in range(planes // 2):
            lo = hi = 0
            for i in range(8):
                v = px[y * 8 + i] >> (pair * 2)
                lo |= (v & 1) << (7 - i)
                hi |= ((v >> 1) & 1) << (7 - i)
            base = pair * 16 + y * 2
            out[base], out[base + 1] = lo, hi
    return out


# ------------------------------------------------------------------ packed nibbles
def _dec_packed4(buf: bytes, w: int, h: int, high_first: bool) -> list[int]:
    out = []
    for b in buf[: w * h // 2]:
        a, c = (b >> 4) & 15, b & 15
        out.extend((a, c) if high_first else (c, a))
    return out


def _enc_packed4(px: list[int], w: int, h: int, high_first: bool) -> bytearray:
    out = bytearray()
    for i in range(0, w * h, 2):
        a, c = px[i] & 15, px[i + 1] & 15
        out.append((a << 4 | c) if high_first else (c << 4 | a))
    return out


# ------------------------------------------------------------------ packed 2bpp (C64 multicolour)
def _dec_packed2(buf: bytes, w: int, h: int) -> list[int]:
    out = []
    for b in buf[: w * h // 4]:
        out.extend((b >> s) & 3 for s in (6, 4, 2, 0))
    return out


def _enc_packed2(px: list[int], w: int, h: int) -> bytearray:
    out = bytearray()
    for i in range(0, w * h, 4):
        out.append((px[i] & 3) << 6 | (px[i + 1] & 3) << 4 | (px[i + 2] & 3) << 2 | (px[i + 3] & 3))
    return out


def _fmt(key, name, w, h, bpp, stride, system, dec, enc, **kw) -> TileFormat:
    return TileFormat(key, name, w, h, bpp, stride, system, _dec=dec, _enc=enc, **kw)


FORMATS: dict[str, TileFormat] = {f.key: f for f in (
    _fmt("1bpp", "1bpp 8x8 (generic / ZX / C64 hires charset)", 8, 8, 1, 8, "mono", _dec_1bpp, _enc_1bpp),
    _fmt("nes", "NES 2bpp planar (CHR)", 8, 8, 2, 16, "nes", _dec_nes, _enc_nes),
    _fmt("gb", "Game Boy / SNES 2bpp", 8, 8, 2, 16, "gb",
         lambda b, w, h: _dec_interleaved(b, w, h, 2), lambda p, w, h: _enc_interleaved(p, w, h, 2)),
    _fmt("snes4", "SNES / PC Engine 4bpp planar", 8, 8, 4, 32, "grey16",
         lambda b, w, h: _dec_interleaved(b, w, h, 4), lambda p, w, h: _enc_interleaved(p, w, h, 4)),
    _fmt("genesis", "Mega Drive / Genesis 4bpp", 8, 8, 4, 32, "grey16",
         lambda b, w, h: _dec_packed4(b, w, h, True), lambda p, w, h: _enc_packed4(p, w, h, True)),
    _fmt("gba4", "GBA / DS 4bpp", 8, 8, 4, 32, "grey16",
         lambda b, w, h: _dec_packed4(b, w, h, False), lambda p, w, h: _enc_packed4(p, w, h, False)),
    _fmt("c64mc", "C64 multicolour charset (4x8)", 4, 8, 2, 8, "c64", _dec_packed2, _enc_packed2, aspect=2),
    _fmt("c64spr", "C64 hires sprite (24x21)", 24, 21, 1, 64, "c64", _dec_1bpp, _enc_1bpp),
    _fmt("c64sprmc", "C64 multicolour sprite (12x21)", 12, 21, 2, 64, "c64", _dec_packed2, _enc_packed2,
         aspect=2),
    _fmt("a2600", "Atari 2600 player graphics (8 x height)", 8, 8, 1, 8, "a2600ntsc", _dec_1bpp, _enc_1bpp,
         var_height=True),
)}


def get_format(key: str) -> TileFormat:
    return FORMATS[key]


def guess_format(path: str) -> str:
    """A sensible first format for a file name (the user can always change it)."""
    p = str(path).lower()
    for ext, key in ((".chr", "nes"), (".nes", "nes"), (".gb", "gb"), (".gbc", "gb"), (".2bpp", "gb"),
                     (".sfc", "snes4"), (".smc", "snes4"), (".4bpp", "snes4"), (".md", "genesis"),
                     (".gen", "genesis"), (".bin", "1bpp"), (".gba", "gba4"), (".a26", "a2600"),
                     (".prg", "c64spr"), (".spr", "c64spr"), (".64c", "1bpp"), (".1bpp", "1bpp")):
        if p.endswith(ext):
            return key
    return "1bpp"
