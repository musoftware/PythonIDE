"""System palettes (RGB tuples) and the default colour slots of each tile format.

The Atari 2600 and NES palettes are *generated* here from a simple model of the NTSC / PAL colour signal
(luminance steps + a hue angle per colour), so they are close to - but not byte-identical with - the
palettes of a particular emulator.  The C64 and Game Boy tables are the commonly used reference colours.
"""
from __future__ import annotations

import math

RGB = tuple[int, int, int]


def _clamp(v: float) -> int:
    return max(0, min(255, int(round(v))))


def _yiq(y: float, i: float, q: float) -> RGB:
    r = y + 0.956 * i + 0.621 * q
    g = y - 0.272 * i - 0.647 * q
    b = y - 1.106 * i + 1.703 * q
    return _clamp(r * 255), _clamp(g * 255), _clamp(b * 255)


def _a2600(pal: bool) -> list[RGB]:
    """128 colours indexed by ``COLUxx >> 1`` (hue in the high nibble, luminance in bits 1-3)."""
    out: list[RGB] = []
    for hue in range(16):
        for lum in range(8):
            y = 0.06 + lum * 0.125
            if pal:
                grey = hue in (0, 1, 14, 15)
                angle = 310.0 + (hue - 2) * 15.0 + (180.0 if hue % 2 else 0.0)
            else:
                grey = hue == 0
                angle = 310.0 + (hue - 1) * 25.7
            if grey:
                out.append(_yiq(y, 0.0, 0.0))
                continue
            sat = 0.26 if 0 < lum < 7 else 0.18
            a = math.radians(angle)
            out.append(_yiq(y, sat * math.cos(a), sat * math.sin(a)))
    return out


def _nes() -> list[RGB]:
    """64 colours of the 2C02 PPU ($00-$3F)."""
    levels = (0.30, 0.55, 0.82, 0.95)       # colour luminance per row
    greys = (0.40, 0.66, 0.97, 0.97)        # hue 0 greys
    out: list[RGB] = []
    for row in range(4):
        for hue in range(16):
            if hue == 0:
                out.append(_yiq(greys[row], 0, 0))
            elif hue == 13:
                out.append(_yiq((0.0, 0.25, 0.60, 0.75)[row], 0, 0) if row else (0, 0, 0))
            elif hue >= 14:
                out.append((0, 0, 0))
            else:
                y = levels[row] - (0.12 if row == 0 else 0.0)
                sat = 0.26 if row < 3 else 0.12
                a = math.radians(160.0 - (hue - 1) * 28.0)
                out.append(_yiq(y, sat * math.cos(a), sat * math.sin(a)))
    return out


def _hex(*codes: str) -> list[RGB]:
    return [(int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)) for c in codes]


C64 = _hex("000000", "FFFFFF", "68372B", "70A4B2", "6F3D86", "588D43", "352879", "B8C76F",
           "6F4F25", "433900", "9A6759", "444444", "6C6C6C", "9AD284", "6C5EB5", "959595")
C64_NAMES = ["black", "white", "red", "cyan", "purple", "green", "blue", "yellow", "orange", "brown",
             "light red", "dark grey", "grey", "light green", "light blue", "light grey"]
GB_DMG = _hex("9BBC0F", "8BAC0F", "306230", "0F380F")
GB_POCKET = _hex("FFFFFF", "A9A9A9", "545454", "000000")
EGA16 = _hex("000000", "0000AA", "00AA00", "00AAAA", "AA0000", "AA00AA", "AA5500", "AAAAAA",
             "555555", "5555FF", "55FF55", "55FFFF", "FF5555", "FF55FF", "FFFF55", "FFFFFF")
MONO = _hex("000000", "FFFFFF")
GREY16 = [(v, v, v) for v in (i * 17 for i in range(16))]

SYSTEM_PALETTES: dict[str, tuple[str, list[RGB]]] = {
    "a2600ntsc": ("Atari 2600 NTSC (128)", _a2600(False)),
    "a2600pal": ("Atari 2600 PAL (128)", _a2600(True)),
    "nes": ("NES / Famicom (64)", _nes()),
    "gb": ("Game Boy DMG greens", GB_DMG),
    "gbpocket": ("Game Boy Pocket greys", GB_POCKET),
    "c64": ("Commodore 64 (16)", C64),
    "ega16": ("EGA / CGA 16", EGA16),
    "grey16": ("Greyscale 16", GREY16),
    "mono": ("Black and white", MONO),
}

# default system-palette indices for the colour slots of a format (slot -> palette index)
DEFAULT_SLOTS: dict[str, list[int]] = {
    "a2600ntsc": [0, 7, 0x1E >> 1, 0x46 >> 1],
    "a2600pal": [0, 7, 0x2E >> 1, 0x46 >> 1],
    "nes": [0x0F, 0x16, 0x27, 0x30],
    "gb": [0, 1, 2, 3],
    "gbpocket": [0, 1, 2, 3],
    "c64": [0, 1, 2, 5],
    "ega16": list(range(16)),
    "grey16": list(range(16)),
    "mono": [0, 1],
}


def palette(key: str) -> list[RGB]:
    return SYSTEM_PALETTES[key][1]


def default_slots(system: str, colors: int) -> list[int]:
    """*colors* palette indices to start with for a format whose default system palette is *system*."""
    base = list(DEFAULT_SLOTS.get(system, range(colors)))
    n = len(palette(system))
    if colors == 2 and system in ("a2600ntsc", "a2600pal"):
        base = [0, 0x0E >> 1]                     # black background, white player
    elif colors == 2 and len(base) > 2 and system != "mono":
        base = [base[0], base[-1]]
    if colors == 16 and len(base) < 16:
        base = [round(i * (n - 1) / 15) for i in range(16)]
    while len(base) < colors:
        base.append(len(base) % n)
    return [b % n for b in base[:colors]]


def nearest(rgb: RGB, colors: list[RGB]) -> int:
    """Index of the closest colour (weighted RGB distance, a cheap perceptual approximation)."""
    r, g, b = rgb[:3]
    best, bi = None, 0
    for i, (cr, cg, cb) in enumerate(colors):
        rm = (r + cr) / 2
        d = (2 + rm / 256) * (r - cr) ** 2 + 4 * (g - cg) ** 2 + (2 + (255 - rm) / 256) * (b - cb) ** 2
        if best is None or d < best:
            best, bi = d, i
    return bi


def a2600_color_byte(index: int) -> int:
    """Palette index (0..127) -> value for a COLUP0 / COLUPF register."""
    return (index & 0x7F) << 1
