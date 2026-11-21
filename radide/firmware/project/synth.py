"""A synthetic ECU-like firmware image written by RAD IDE (no manufacturer data): code-like bytes, an ID
string, calibration tables with axes, an adaptation area and three checksum blocks.  Used by the
"ECU Project (Demo Firmware)" template, the docs and the tests.

Layout of the 64 KB image (big-endian, like many PowerPC / TriCore-era calibrations):

    0x0000-0x3FFE  "boot + code" bytes, sum16 of BE words stored at 0x3FFE           -> block "Boot sum16"
    0x4000-0x7FFC  code + ID string "RADIDE DEMO ECU", CRC-16/CCITT-FALSE at 0x7FFC,
                   its ones' complement at 0x7FFE (a complement pair)              -> block "Code CRC16"
    0x8000-0xC000  calibration: 16x16 u16 map + axes at 0x8100, 8x8 u8 map at 0x8400, 1D curve at 0x8600
    0xC000-0xD000  "adaptation" area (changes in the car - left out of the CRC: a hole)
    0xD000-0xFFFC  more calibration, CRC-32 (zip) of 0x8000-0xFFFC without the hole at 0xFFFC
                                                                                     -> block "Calibration CRC32"
"""
from __future__ import annotations

import random
import struct

from ..checksum.blocks import ChecksumBlock, correct

SIZE = 0x10000
ID_TEXT = b"RADIDE DEMO ECU SW 0001 (synthetic test image, no vehicle data)"
MAP16_AT = 0x8100          # 16 x-axis u16, 16 y-axis u16, 16x16 u16 values
MAP8_AT = 0x8400           # 8 x-axis u8, 8 y-axis u8, 8x8 u8 values
CURVE_AT = 0x8600          # 12 x-axis u16, 12 u16 values


def demo_blocks() -> list[ChecksumBlock]:
    return [
        ChecksumBlock("Boot sum16", "sum16-be", [(0x0000, 0x3FFE)], [], 0x3FFE, 2, "be",
                      note="synthetic demo block"),
        ChecksumBlock("Code CRC16", "crc16-ccitt-false", [(0x4000, 0x7FFC)], [], 0x7FFC, 2, "be", 0x7FFE,
                      note="synthetic demo block with a complement copy"),
        ChecksumBlock("Calibration CRC32", "crc32", [(0x8000, 0xFFFC)], [(0xC000, 0xD000)], 0xFFFC, 4, "be",
                      note="synthetic demo block; the adaptation area 0xC000-0xD000 is skipped"),
    ]


def _code_like(rng: random.Random, n: int) -> bytes:
    ops = [0x7C, 0x38, 0x3C, 0x60, 0x80, 0x90, 0x48, 0x4E, 0x94, 0x81, 0x7D, 0x41, 0x40, 0x2C]
    out = bytearray()
    while len(out) < n:
        out += bytes([rng.choice(ops), rng.randrange(256), rng.randrange(256), rng.randrange(256)])
    return bytes(out[:n])


def image(seed: int = 2026) -> bytes:
    rng = random.Random(seed)
    d = bytearray(b"\xFF" * SIZE)
    d[0:0x3FFE] = _code_like(rng, 0x3FFE)
    d[0:8] = b"\x48\x00\x01\x00RDE1"                 # "branch to 0x100" + magic, PowerPC-looking
    d[0x4000:0x7FFC] = _code_like(rng, 0x3FFC)
    d[0x4100:0x4100 + len(ID_TEXT)] = ID_TEXT
    # calibration area: maps with axes, separated by FF filler
    xs = [500 + 500 * i for i in range(16)]          # rpm
    ys = [10 + 6 * i for i in range(16)]             # load %
    vals = [int(200 + 3 * x / 100 + 20 * y / 10) for y in ys for x in xs]
    d[MAP16_AT:MAP16_AT + 64 + 512] = struct.pack(">16H16H256H", *xs, *ys, *vals)
    ax8 = [i * 30 for i in range(8)]
    m8 = [min(255, 40 + 5 * i + 9 * j) for j in range(8) for i in range(8)]
    d[MAP8_AT:MAP8_AT + 80] = bytes(ax8 + ax8 + m8)
    cx = [i * 250 for i in range(12)]
    cv = [1000 + 37 * i for i in range(12)]
    d[CURVE_AT:CURVE_AT + 48] = struct.pack(">12H12H", *cx, *cv)
    d[0xC000:0xD000] = bytes(rng.randrange(256) for _ in range(0x1000))        # adaptation (varies)
    d[0xD000:0xE000] = bytes((i * 7 + 3) & 0xFF for i in range(0x1000))
    correct(d, demo_blocks())
    return bytes(d)


__all__ = ["image", "demo_blocks", "SIZE", "MAP16_AT", "MAP8_AT", "CURVE_AT", "ID_TEXT"]
