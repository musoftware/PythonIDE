"""Writes the four sample designs of this folder (all art is original, drawn here - CC0).

Run:  .venv\\Scripts\\python.exe samples\\Tests\\Retro\\DesignSamples\\make_samples.py [--gen]

    Castle.a26scr   Atari 2600: castle towers in the playfield, sunset colour bands, a knight and a dragon
    Meadow.nesscr   NES: a 3-screen level (ground, platforms, pipes, coins, clouds, a title), hero + enemies
    Town.gbmap      Game Boy: houses and a road on the background, a HUD in the window, two sprites
    Cave.m13scr     DOS mode 13h: a cave of stone tiles over a dark gradient, the player and two slimes

``--gen`` also writes the generated code into gen/<name>/ (what saving in the designer does).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

from radide.retro.design.game import gen_dir, generate, new_design  # noqa: E402
from radide.retro.design.game import art  # noqa: E402


def castle():
    d = new_design("a2600", "Castle")
    pf, bk, pfc, col = (d.layer(n) for n in ("Playfield", "Background colour", "Playfield colour", "Collision"))
    h = pf.h
    for y in range(h):
        for x in range(20):
            on = 0
            if y >= h - 12:
                on = 1                                         # ground
            elif y >= 100:
                on = 1 if x in (2, 3, 4, 5) or x in (9, 10, 11) else 0      # tower + wall
                if x in (6, 7, 8) and y >= 140:
                    on = 1
                if y < 108 and x in (2, 4, 9, 11):
                    on = 1 if (y // 4) % 2 == 0 else 0        # battlements
            elif y >= 80 and x in (3, 4):
                on = 1                                         # spire
            pf.set(x, y, on)
            if on:
                col.set(x, y, 1)
                col.set(39 - x, y, 1)
        band = min(7, y // 14)
        bk.set(0, y, ((0x40 + band * 2) if y < 100 else 0x84) >> 1 if y < h - 12 else 0x00)
        pfc.set(0, y, (0x08 if y < h - 12 else 0xC6) >> 1)
    d.sprites["Knight"] = {"w": 8, "h": 10, "pixels": bytearray(
        1 if c == "X" else 0 for r in ["..XXX...", "..X.X...", "..XXX..X", "...X...X", ".XXXXXXX", "X.XXX..X",
                                         "..XXX...", "..X.X...", ".XX.XX..", ".X...X.."] for c in r)}
    d.sprites["Dragon"] = {"w": 8, "h": 9, "pixels": bytearray(
        1 if c == "X" else 0 for r in ["X.....XX", "XX...XXX", ".XXXXXX.", "..XXXXXX", ".XXXXX.X", "XXXXXX..",
                                         "X.XXX...", "..X.X...", ".XX.XX.."] for c in r)}
    p0, p1 = d.object("Player0"), d.object("Player1")
    p0.update({"sprite": "Knight", "x": 76, "y": h - 22, "color": 0x0E >> 1})
    p1.update({"sprite": "Dragon", "x": 118, "y": 40, "color": 0xC6 >> 1, "nusiz": 5})
    d.object("Ball").update({"x": 128, "y": 52, "height": 2, "enabled": True})
    return d


def meadow():
    d = new_design("nes", "Meadow", screens=3)
    nt, at, col = d.layer("Nametable"), d.layer("Attributes"), d.layer("Collision")
    nt.data[:] = bytes(len(nt.data))
    col.data[:] = bytes(len(col.data))
    W = nt.w
    for x in range(W):
        gap = 40 <= x < 43 or 70 <= x < 72
        for y in range(26, 30):
            if not gap:
                nt.set(x, y, 13 if y == 26 else 5)
                col.set(x, y, 1)
        if x % 11 == 4:
            nt.set(x, 5 + (x % 3), 7)
            nt.set(x + 1, 5 + (x % 3), 8)
    for x0, y0, n in ((10, 19, 4), (24, 15, 5), (48, 18, 6), (60, 13, 3), (80, 17, 5)):
        for x in range(x0, x0 + n):
            nt.set(x, y0, 4)
            col.set(x, y0, 1)
            nt.set(x, y0 - 2, 10)
            col.set(x, y0 - 2, 3)
    for px in (33, 76):
        for y in range(22, 26):
            nt.set(px, y, 14)
            nt.set(px + 1, y, 14)
            col.set(px, y, 1)
            col.set(px + 1, y, 1)
    for i, ch in enumerate(art.text_tiles("MEADOW - WORLD 1")):
        nt.set(3 + i, 2, ch)
    for my in range(15):
        for mx in range(at.w):
            at.set(mx, my, 3 if my < 2 else (1 if my >= 13 else 2))
    for x0, y0, n in ((10, 19, 4), (24, 15, 5), (48, 18, 6), (60, 13, 3), (80, 17, 5)):
        for x in range(x0, x0 + n):
            at.set(x // 2, y0 // 2, 0)
    d.objects = [{"name": "Hero", "kind": "sprite", "x": 24, "y": 192, "tile": 0, "w": 2, "h": 2, "palette": 0,
                  "flip_h": False, "flip_v": False, "behind": False}]
    for i, x in enumerate((180, 400, 610)):
        d.objects.append({"name": f"Enemy{i + 1}", "kind": "sprite", "x": x, "y": 200, "tile": 2, "w": 1, "h": 1,
                          "palette": 1, "flip_h": bool(i % 2), "flip_v": False, "behind": False})
    return d


def town():
    d = new_design("gb", "Town")
    bg, win, col = d.layer("Background"), d.layer("Window"), d.layer("Collision")
    bg.data[:] = bytes(len(bg.data))
    col.data[:] = bytes(len(col.data))
    for x in range(32):
        bg.set(x, 12, 12)                          # road
        bg.set(x, 13, 12)
        for y in range(14, 18):
            bg.set(x, y, 13 if y == 14 else 5)
            col.set(x, y, 1)
    for hx in (1, 8, 15):
        for y in range(7, 12):
            for x in range(hx, hx + 5):
                bg.set(x, y, 4 if y > 7 else 6)
                col.set(x, y, 1)
        bg.set(hx + 2, 11, 11)                     # door
    for i, ch in enumerate(art.text_tiles("TOWN")):
        bg.set(8 + i, 2, ch)
    win.data[:] = bytes(len(win.data))
    for x in range(20):
        win.set(x, 0, 6)
    for i, ch in enumerate(art.text_tiles("HP 3  GOLD 12")):
        win.set(1 + i, 1, ch)
    d.settings.update({"wy": 128, "window": True})
    return d


def cave():
    d = new_design("dos13h", "Cave")
    for i in range(16):                            # dark cave gradient
        d.palette[200 + i] = [2 + i, 1 + i // 2, 4 + i * 2]
    bg = d.layer("Background")
    for y in range(200):
        bg.data[y * 320:(y + 1) * 320] = bytes([200 + min(15, y // 13)]) * 320
    tl, col = d.layer("Tiles"), d.layer("Collision")
    tl.data[:] = bytes([255]) * len(tl.data)
    col.data[:] = bytes(len(col.data))
    for x in range(tl.w):
        for y in (0, 11, 12):
            tl.set(x, y, 2)
            col.set(x, y, 1)
        if x in (0, tl.w - 1):
            for y in range(tl.h):
                tl.set(x, y, 2)
                col.set(x, y, 1)
    for x in range(5, 9):
        tl.set(x, 8, 2)
        col.set(x, 8, 1)
    for x in range(12, 16):
        tl.set(x, 6, 2)
        col.set(x, 6, 1)
    for x in (9, 10):
        tl.set(x, 11, 3)                            # water pool
        col.set(x, 11, 2)
    d.objects = [{"name": "Player", "kind": "sprite", "x": 40, "y": 160, "sprite": "Hero", "player": True},
                 {"name": "Slime1", "kind": "sprite", "x": 200, "y": 84, "sprite": "Slime", "player": False},
                 {"name": "Slime2", "kind": "sprite", "x": 250, "y": 164, "sprite": "Slime", "player": False}]
    return d


def main() -> None:
    from radide.retro.design.game import SYSTEMS
    for fn in (castle, meadow, town, cave):
        d = fn()
        p = HERE / f"{d.name}{SYSTEMS[d.system].EXT}"
        d.save(p)
        print("wrote", p.name)
        if "--gen" in sys.argv:
            info = generate(d, gen_dir(p))
            print("  generated", len(info["files"]), "files in", os.path.relpath(gen_dir(p), HERE))


if __name__ == "__main__":
    main()
