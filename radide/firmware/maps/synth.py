"""Synthetic firmware images with known calibration maps (tests, demos). Nothing here comes from a real ECU.

``build_image(seed)`` returns (bytes, [MapDef]) - a pseudo "code" area (random instruction-like words, strings,
pointer tables, 0xFF fill) with maps of different layouts embedded at known offsets: Bosch-style headers,
headerless axes, 8 / 16-bit, signed, LE / BE, float32, row and column order.
"""
from __future__ import annotations

import struct

import numpy as np

from .model import AxisDef, MapDef, encode_array


def _surface(rows: int, cols: int, kind: int, lo: float, hi: float) -> np.ndarray:
    y = np.linspace(0, 1, rows)[:, None]
    x = np.linspace(0, 1, cols)[None, :]
    if kind == 0:
        z = 0.6 * x + 0.4 * y
    elif kind == 1:
        z = np.sin(x * 2.2) * 0.7 + y * 0.3
    elif kind == 2:
        z = np.exp(-((x - 0.6) ** 2 + (y - 0.4) ** 2) * 3)
    else:
        z = x * y + 0.2 * x
    z = (z - z.min()) / (np.ptp(z) or 1)
    return lo + z * (hi - lo)


def _code(rng, n: int) -> bytes:
    """Instruction-like noise: random little-endian words with a bias to common opcode bytes + some strings."""
    out = bytearray(rng.integers(0, 256, n, dtype=np.uint8).tobytes())
    for _ in range(n // 400):
        p = int(rng.integers(0, max(1, n - 32)))
        s = b"ECU-SYNTHETIC-TEST " + bytes(rng.integers(65, 91, 8, dtype=np.uint8).tobytes())
        out[p:p + len(s)] = s
    for _ in range(n // 1000):                 # pointer tables (increasing 32-bit addresses: not maps)
        p = int(rng.integers(0, max(1, n - 64))) & ~3
        base = int(rng.integers(0x80000, 0x90000))
        for k in range(12):
            out[p + 4 * k:p + 4 * k + 4] = struct.pack("<I", base + k * int(rng.integers(8, 200)))
    return bytes(out)


def _place(img: bytearray, off: int, b: bytes) -> int:
    img[off:off + len(b)] = b
    return off + len(b)


def build_image(seed: int = 1, size: int = 0x40000) -> tuple[bytes, list[MapDef]]:
    rng = np.random.default_rng(seed)
    img = bytearray(_code(rng, size))
    img[size - 0x4000:] = b"\xff" * 0x4000
    maps: list[MapDef] = []
    pos = 0x8000

    def gap():
        nonlocal pos
        pos += int(rng.integers(0x300, 0x900))
        pos = (pos + 3) & ~3

    # 1. Bosch-style 8-bit map: [nx][ny][X][Y][Z] u8, 12x10
    nx, ny = 12, 10
    x = np.linspace(20, 240, nx).round()
    y = np.linspace(10, 200, ny).round()
    z = _surface(ny, nx, 0, 30, 220).round()
    p = _place(img, pos, bytes([nx, ny]))
    xo = p
    p = _place(img, p, encode_array(x, "u8"))
    yo = p
    p = _place(img, p, encode_array(y, "u8"))
    maps.append(MapDef("KF_BOSCH8", p, nx, ny, "u8", "le", "row", 0.75, 0, "deg",
                       AxisDef("rpm", xo, nx, "u8", "le", 40, 0, "1/min"),
                       AxisDef("load", yo, ny, "u8", "le", 0.5, 0, "%")))
    _place(img, p, encode_array(z, "u8"))
    pos = p + nx * ny
    gap()
    # 2. Bosch-style 16-bit LE map with words header, 16x12, signed values
    nx, ny = 16, 12
    x = np.linspace(600, 7000, nx).round()
    y = np.linspace(100, 2400, ny).round()
    z = _surface(ny, nx, 1, -300, 900).round()
    p = _place(img, pos, struct.pack("<HH", nx, ny))
    xo = p
    p = _place(img, p, encode_array(x, "u16", "le"))
    yo = p
    p = _place(img, p, encode_array(y, "u16", "le"))
    maps.append(MapDef("KF_BOSCH16", p, nx, ny, "s16", "le", "row", 0.1, 0, "deg",
                       AxisDef("rpm", xo, nx, "u16", "le"), AxisDef("load", yo, ny, "u16", "le")))
    _place(img, p, encode_array(z, "s16", "le"))
    pos = p + nx * ny * 2
    gap()
    # 3. headerless big-endian 16-bit map, column order, 8x8
    nx, ny = 8, 8
    x = np.array([500, 1000, 1500, 2200, 3000, 4000, 5200, 6500])
    y = np.array([0, 20, 40, 60, 80, 100, 130, 160])
    z = _surface(ny, nx, 2, 1000, 30000).round()
    xo = pos
    p = _place(img, pos, encode_array(x, "u16", "be"))
    yo = p
    p = _place(img, p, encode_array(y, "u16", "be"))
    maps.append(MapDef("MAP_BE_COL", p, nx, ny, "u16", "be", "col", 1, 0, "",
                       AxisDef("x", xo, nx, "u16", "be"), AxisDef("y", yo, ny, "u16", "be")))
    _place(img, p, encode_array(z.T.ravel(), "u16", "be"))
    pos = p + nx * ny * 2
    gap()
    # 4. float32 LE map, 10x6 (32-bit controllers: TriCore / ARM style)
    nx, ny = 10, 6
    x = np.linspace(0.5, 9.5, nx)
    y = np.array([-20.0, 0.0, 20.0, 45.0, 70.0, 95.0])
    z = _surface(ny, nx, 3, 0.8, 1.6)
    xo = pos
    p = _place(img, pos, encode_array(x, "f32", "le"))
    yo = p
    p = _place(img, p, encode_array(y, "f32", "le"))
    maps.append(MapDef("MAP_F32", p, nx, ny, "f32", "le", "row", 1, 0, "",
                       AxisDef("x", xo, nx, "f32", "le"), AxisDef("y", yo, ny, "f32", "le")))
    _place(img, p, encode_array(z, "f32", "le"))
    pos = p + nx * ny * 4
    gap()
    # 5. Bosch-style 8-bit curve: [n][axis][values], 16 points
    n = 16
    x = np.linspace(5, 245, n).round()
    v = (80 + 100 * np.sqrt(np.linspace(0, 1, n))).round()
    p = _place(img, pos, bytes([n]))
    xo = p
    p = _place(img, p, encode_array(x, "u8"))
    maps.append(MapDef("KL_CURVE8", p, n, 1, "u8", "le", "row", 1, 0, "",
                       AxisDef("x", xo, n, "u8", "le")))
    _place(img, p, encode_array(v, "u8"))
    pos = p + n
    gap()
    # 6. headerless 16-bit BE curve, signed values, 12 points
    n = 12
    x = np.linspace(-400, 1200, n).round()
    v = (np.cos(np.linspace(0, 2.4, n)) * 800).round()
    xo = pos
    p = _place(img, pos, encode_array(x, "s16", "be"))
    maps.append(MapDef("KL_S16_BE", p, n, 1, "s16", "be", "row", 1, 0, "",
                       AxisDef("x", xo, n, "s16", "be")))
    _place(img, p, encode_array(v, "s16", "be"))
    pos = p + n * 2
    gap()
    # 7. Bosch-style 16-bit big-endian map 20x16 (word header), unsigned
    nx, ny = 20, 16
    x = np.linspace(400, 8000, nx).round()
    y = np.linspace(50, 3000, ny).round()
    z = _surface(ny, nx, 1, 2000, 60000).round()
    p = _place(img, pos, struct.pack(">HH", nx, ny))
    xo = p
    p = _place(img, p, encode_array(x, "u16", "be"))
    yo = p
    p = _place(img, p, encode_array(y, "u16", "be"))
    maps.append(MapDef("KF_BOSCH16_BE", p, nx, ny, "u16", "be", "row", 1, 0, "",
                       AxisDef("x", xo, nx, "u16", "be"), AxisDef("y", yo, ny, "u16", "be")))
    _place(img, p, encode_array(z, "u16", "be"))
    pos = p + nx * ny * 2
    return bytes(img), maps
