"""Generate the sample files of samples/Tests/Retro/Gfx/Sample (all original, CC0 - see README.md).

* homebrew.chr     8 KB NES CHR: digits 0-9, A-Z, a smiley, a brick, a heart and a little ship, drawn here
* castle.bin       Atari 2600 data block: a reflected castle playfield (PF0/PF1/PF2 tables) + a player sprite
* castle.rtpf      the Playfield Editor document of that playfield
* demo.rom         a tiny synthetic "ROM": NES-style pointer table at 0x40 -> 5 English strings at 0x100
* demo.tbl         ASCII + one code per Arabic letter form from 0x80 (Add Arabic Letter Forms)
* demo_ar.csv      the script sheet with Arabic translations (Load Sheet, then Insert with Shape + RTL)
* level.rtmap      a 32x30 nametable using homebrew.chr
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

from radide.retro.gfx import arabic  # noqa: E402
from radide.retro.gfx.atari2600 import Playfield  # noqa: E402
from radide.retro.gfx.codecs import get_format  # noqa: E402
from radide.retro.gfx.script import PointerSpec, dump_pointers  # noqa: E402
from radide.retro.gfx.textable import ascii_table  # noqa: E402
from radide.retro.gfx.tilemap import TileMap  # noqa: E402

OUT = os.path.join(HERE, "Sample")

# 5x7 font drawn for this sample (rows top to bottom, '#' = on)
FONT = {
    "0": ".###.#...##..###.#.###..##...#.###.", "1": "..#...##....#....#....#....#...###.",
    "2": ".###.#...#....#...#...#...#....#####", "3": "#####...#...#.....#....##...#.###.",
    "4": "...#...##..#.#.#..#.#####...#....#.", "5": "######....####.....#....##...#.###.",
    "6": "..##..#...#....####.#...##...#.###.", "7": "#####....#...#...#...#....#....#...",
    "8": ".###.#...##...#.###.#...##...#.###.", "9": ".###.#...##...#.####....#...#..##..",
}


def glyph_rows(pattern: str) -> list[str]:
    pattern = pattern.ljust(35, ".")[:35]
    return [pattern[i * 5:(i + 1) * 5] for i in range(7)]


def letter(ch: str) -> list[list[int]]:
    """Letters as simple block shapes (original 5x7 drawings generated from strokes)."""
    strokes = {
        "A": ["..#..", ".#.#.", "#...#", "#####", "#...#", "#...#", "#...#"],
        "B": ["####.", "#...#", "####.", "#...#", "#...#", "#...#", "####."],
        "C": [".####", "#....", "#....", "#....", "#....", "#....", ".####"],
        "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
        "E": ["#####", "#....", "####.", "#....", "#....", "#....", "#####"],
        "H": ["#...#", "#...#", "#####", "#...#", "#...#", "#...#", "#...#"],
        "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
        "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
        "R": ["####.", "#...#", "####.", "#.#..", "#..#.", "#...#", "#...#"],
        "S": [".####", "#....", ".###.", "....#", "....#", "#...#", ".###."],
        "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
        "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
        "Y": ["#...#", ".#.#.", "..#..", "..#..", "..#..", "..#..", "..#.."],
    }.get(ch)
    rows = strokes or ["#####", "#...#", "#...#", "#...#", "#...#", "#...#", "#####"]
    return to_tile(rows)


def to_tile(rows: list[str], color: int = 1) -> list[list[int]]:
    tile = [[0] * 8 for _ in range(8)]
    for y, r in enumerate(rows[:8]):
        for x, c in enumerate(r[:8]):
            if c == "#":
                tile[y][x + (1 if len(r) <= 6 else 0)] = color
            elif c in "123":
                tile[y][x] = int(c)
    return tile


PICTURES = {
    "smiley": ["..1111..", ".122221.", "12322321", "12222221", "12322321", "12233221", ".122221.", "..1111.."],
    "brick": ["33333333", "12221222", "12221222", "33333333", "22122212", "22122212", "33333333", "12221222"],
    "heart": [".11..11.", "1221122.", "12222221", "12222221", ".122221.", "..1221..", "...11...", "........"],
    "ship": ["...33...", "...33...", "..3223..", "..3223..", ".321123.", "32211223", "33.11.33", "........"],
}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    nes = get_format("nes")
    chr_data = bytearray(8192)
    tiles: list[list[list[int]]] = [[[0] * 8 for _ in range(8)]]          # tile 0 = blank
    tiles += [to_tile(glyph_rows(FONT[d])) for d in "0123456789"]           # 1..10
    tiles += [letter(chr(c)) for c in range(ord("A"), ord("Z") + 1)]        # 11..36
    tiles += [to_tile(PICTURES[k]) for k in ("smiley", "brick", "heart", "ship")]   # 37..40
    for i, t in enumerate(tiles):
        chr_data[i * 16:(i + 1) * 16] = nes.encode([p for r in t for p in r])
    open(os.path.join(OUT, "homebrew.chr"), "wb").write(chr_data)

    # Atari 2600 castle: 16 rows, reflected
    pf = Playfield(16, reflect=True)
    art = ["####################", "#..#..#..#..........", "####################", "##..................",
           "##.......####.......", "##.......#..#.......", "##.......#..#.......", "##......######......",
           "##......#....#......", "##......#.##.#......", "##......#.##.#......", "##......#.##.#......",
           "##......######......", "##..................", "####################", "####################"]
    for y, row in enumerate(art):
        for x, c in enumerate(row):
            pf.set(x, y, 1 if c == "#" else 0)
    blob = bytearray(256)
    blob[0:16] = b"RADIDE 2600 DEMO"
    pf.to_binary(blob, 0x20)
    player = [0x18, 0x3C, 0x7E, 0xDB, 0xFF, 0x24, 0x5A, 0xA5]              # a little invader-like sprite
    blob[0x80:0x88] = bytes(player)
    open(os.path.join(OUT, "castle.bin"), "wb").write(blob)
    doc = {"format": "radide-playfield", "version": 1, "height": pf.height, "reflect": True, "asymmetric": False,
           "rows": ["".join(map(str, r)) for r in pf.rows], "bg": 0x80 >> 1, "fg": 0x1E >> 1,
           "binary": {"path": "castle.bin", "offset": 0x20, "layout": "tables"}}
    open(os.path.join(OUT, "castle.rtpf"), "w", encoding="utf-8").write(json.dumps(doc, indent=1))

    # synthetic ROM with a pointer table (base $8000, add $10 like a one-bank NES game)
    rom = bytearray(0x400)
    rom[0:4] = b"DEMO"
    strings = [b"HELLO!\x00", b"PRESS START\x00", b"GAME OVER\x00", b"YOU WIN!\x00", b"HELLO!\x00"]
    pos = 0x100
    for i, s in enumerate(strings):
        rom[pos:pos + len(s)] = s
        rom[0x40 + 2 * i:0x42 + 2 * i] = (pos - 0x10 + 0x8000).to_bytes(2, "little")
        pos += len(s)
    open(os.path.join(OUT, "demo.rom"), "wb").write(rom)
    tbl = arabic.arabic_table(0x80, base=ascii_table())
    tbl.save(os.path.join(OUT, "demo.tbl"))
    sc = dump_pointers(bytes(rom), tbl, PointerSpec(0x40, 5, 2, "little", 0x8000, 0x10))
    translations = ["أهلا!<end>", "اضغط ابدأ<end>", "انتهت اللعبة<end>", "فزت!<end>", ""]
    for e, t in zip(sc.entries, translations):
        e.translation = t
    open(os.path.join(OUT, "demo_ar.csv"), "w", encoding="utf-8-sig").write(sc.to_csv())

    m = TileMap.new("nes")
    for x in range(32):
        m.set(x, 0, 38, 1)
        m.set(x, 29, 38, 1)
    for y in range(30):
        m.set(0, y, 38, 1)
        m.set(31, y, 38, 1)
    for i, ch in enumerate("HELLO"):
        m.set(13 + i, 12, 11 + ord(ch) - ord("A"), 0)
    m.set(15, 15, 37, 2)
    m.set(14, 17, 39, 3)
    m.set(16, 17, 40, 0)
    m.tileset = {"file": "homebrew.chr", "offset": 0, "format": "nes"}
    m.metatiles = [[38, 38, 38, 38]]
    m.save(os.path.join(OUT, "level.rtmap"))
    print("sample written to", OUT)


if __name__ == "__main__":
    main()
