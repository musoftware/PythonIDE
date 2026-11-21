"""Starter art for new designs: a few 8x8 2-bit tiles, sprites and a 3x5 font (all original, drawn here as text).

Characters: ``.`` colour 0, ``1`` / ``2`` / ``3`` colours 1-3.
"""
from __future__ import annotations

TILES_8 = {
    "blank": ["........"] * 8,
    "solid1": ["11111111"] * 8,
    "solid2": ["22222222"] * 8,
    "solid3": ["33333333"] * 8,
    "brick": ["11111113", "11111113", "11111113", "33333333", "11131111", "11131111", "11131111", "33333333"],
    "ground": ["22222222", "22122212", "12111211", "11111111", "11131111", "11111111", "11111311", "11111111"],
    "block": ["33333332", "31111112", "31111112", "31111112", "31111112", "31111112", "31111112", "22222222"],
    "cloud_l": ["........", "....333.", "..333333", ".3333333", "33333333", "33333333", ".3322222", "........"],
    "cloud_r": ["........", ".333....", "333333..", "3333333.", "33333333", "33333333", "2222233.", "........"],
    "water": ["........", ".33..33.", "3..33..3", "11111111", "11111111", "13111311", "11111111", "11111111"],
    "coin": ["..3333..", ".322223.", "3223322.", "3223322.", "3223322.", "3223322.", ".322223.", "..2222.."],
    "ladder": ["2......2", "22222222", "2......2", "2......2", "2......2", "22222222", "2......2", "2......2"],
    "checker": ["11112222", "11112222", "11112222", "11112222", "22221111", "22221111", "22221111", "22221111"],
    "grass": ["...2....", "2..2..2.", "2.22.22.", "22222222", "22222222", "21222122", "11111111", "11111111"],
    "pipe": ["3112211.", "3112211.", "3112211.", "3112211.", "3112211.", "3112211.", "3112211.", "3112211."],
    "star": ["...3....", "...3....", "..333...", "3333333.", ".33333..", "..333...", ".33.33..", "3.....3."],
}
BG_ORDER = ["blank", "solid1", "solid2", "solid3", "brick", "ground", "block", "cloud_l", "cloud_r", "water",
            "coin", "ladder", "checker", "grass", "pipe", "star"]

SPRITES_8 = {
    # 2x2 hero (tiles 0, 1 / 16, 17 in a 16-wide sprite sheet)
    "hero_tl": ["....1111", "...11111", "...22323", "..222333", "..223333", "....3333", "...11211", "..111211"],
    "hero_tr": ["1.......", "1111....", "3.......", "333.....", "3333....", "333.....", "1.......", "11......"],
    "hero_bl": [".1111222", ".3311222", ".3322222", "...22222", "...222..", "..111...", ".1111...", "........"],
    "hero_br": ["2111....", "21133...", "2233....", "222.....", ".222....", "..111...", "..1111..", "........"],
    "enemy": ["..1111..", ".111111.", "11311311", "11311311", "11111111", ".222222.", ".2.22.2.", "22....22"],
    "ball": ["..3333..", ".333333.", "33322333", "33222233", "33222233", "33322333", ".333333.", "..3333.."],
    "bullet": ["........", "........", "...33...", "..3223..", "..3223..", "...33...", "........", "........"],
    "heart": [".11..11.", "1111111.", "1131111.", "1111111.", ".11111..", "..111...", "...1....", "........"],
}

# 3x5 font: each glyph is 5 rows of 3 bits (left = bit 2)
FONT_3x5 = {
    "0": (7, 5, 5, 5, 7), "1": (2, 6, 2, 2, 7), "2": (7, 1, 7, 4, 7), "3": (7, 1, 3, 1, 7), "4": (5, 5, 7, 1, 1),
    "5": (7, 4, 7, 1, 7), "6": (7, 4, 7, 5, 7), "7": (7, 1, 2, 2, 2), "8": (7, 5, 7, 5, 7), "9": (7, 5, 7, 1, 7),
    "A": (2, 5, 7, 5, 5), "B": (6, 5, 6, 5, 6), "C": (3, 4, 4, 4, 3), "D": (6, 5, 5, 5, 6), "E": (7, 4, 6, 4, 7),
    "F": (7, 4, 6, 4, 4), "G": (3, 4, 5, 5, 3), "H": (5, 5, 7, 5, 5), "I": (7, 2, 2, 2, 7), "J": (1, 1, 1, 5, 2),
    "K": (5, 5, 6, 5, 5), "L": (4, 4, 4, 4, 7), "M": (5, 7, 7, 5, 5), "N": (6, 5, 5, 5, 5), "O": (2, 5, 5, 5, 2),
    "P": (6, 5, 6, 4, 4), "Q": (2, 5, 5, 6, 3), "R": (6, 5, 6, 5, 5), "S": (3, 4, 2, 1, 6), "T": (7, 2, 2, 2, 2),
    "U": (5, 5, 5, 5, 7), "V": (5, 5, 5, 5, 2), "W": (5, 5, 7, 7, 5), "X": (5, 5, 2, 5, 5), "Y": (5, 5, 2, 2, 2),
    "Z": (7, 1, 2, 4, 7), "!": (2, 2, 2, 0, 2), "-": (0, 0, 7, 0, 0), ".": (0, 0, 0, 0, 2), ":": (0, 2, 0, 2, 0),
    "?": (6, 1, 2, 0, 2), "/": (1, 1, 2, 4, 4),
}
FONT_FIRST = 0x20          # tile number of ' ' when the font is placed ASCII-ordered (0x20..0x5F)


def tile_from_rows(rows: list[str]) -> bytearray:
    m = {".": 0, "1": 1, "2": 2, "3": 3}
    return bytearray(m.get(ch, 0) for r in rows for ch in r.ljust(8, ".")[:8])


def glyph_tile(ch: str, color: int = 3) -> bytearray:
    """A font glyph as an 8x8 tile (3x5 pixels doubled horizontally to 6x5, placed at x 1, y 1)."""
    out = bytearray(64)
    rows = FONT_3x5.get(ch.upper())
    if not rows:
        return out
    for y, bits in enumerate(rows):
        for x in range(3):
            if bits & (4 >> x):
                for dx in (0, 1):
                    out[(y + 1) * 8 + 1 + x * 2 + dx] = color
    return out


def bg_tileset(count: int = 256) -> list[bytearray]:
    """BG tiles: the named starter tiles at 0-15, the font at 0x20-0x5F (ASCII), the rest blank."""
    tiles = [bytearray(64) for _ in range(count)]
    for i, name in enumerate(BG_ORDER):
        tiles[i] = tile_from_rows(TILES_8[name])
    for code in range(0x20, 0x60):
        if code - FONT_FIRST + 0x20 < count:
            tiles[code] = glyph_tile(chr(code))
    return tiles


def sprite_tileset(count: int = 256) -> list[bytearray]:
    """Sprite tiles laid out like a 16-wide sheet: hero 2x2 at 0/1/16/17, then enemy 2, ball 3, bullet 4, heart 5."""
    tiles = [bytearray(64) for _ in range(count)]
    for idx, name in ((0, "hero_tl"), (1, "hero_tr"), (16, "hero_bl"), (17, "hero_br"), (2, "enemy"), (3, "ball"),
                      (4, "bullet"), (5, "heart")):
        tiles[idx] = tile_from_rows(SPRITES_8[name])
    return tiles


def text_tiles(text: str) -> list[int]:
    """Tile numbers for *text* with the ASCII-placed font."""
    return [ord(c) if 0x20 <= ord(c) < 0x60 else 0x20 for c in text.upper()]
