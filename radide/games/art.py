"""Placeholder game art drawn in pure Python and saved as PNG (no pygame / PIL needed).

Used by the game templates and samples/HelloGame: a tileset, an animated player sprite sheet,
a spinning coin, a walking enemy, a goal flag and a top-down hero.  Everything is 32x32 pixel art
so beginners can replace the files later with their own pictures of the same size.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path


class Canvas:
    """An RGBA pixel buffer with a few drawing helpers."""

    def __init__(self, w: int, h: int, fill=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.px = [list(fill) for _ in range(w * h)]

    def set(self, x: int, y: int, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            c = tuple(c) + ((255,) if len(c) == 3 else ())
            if c[3] == 255:
                self.px[y * self.w + x] = list(c)
            elif c[3]:
                d = self.px[y * self.w + x]
                a = c[3] / 255
                self.px[y * self.w + x] = [round(c[i] * a + d[i] * (1 - a)) for i in range(3)] + \
                                          [max(d[3], c[3])]

    def rect(self, x: int, y: int, w: int, h: int, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, c)

    def outline(self, x: int, y: int, w: int, h: int, c):
        for xx in range(x, x + w):
            self.set(xx, y, c)
            self.set(xx, y + h - 1, c)
        for yy in range(y, y + h):
            self.set(x, yy, c)
            self.set(x + w - 1, yy, c)

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, c):
        if rx <= 0 or ry <= 0:
            return
        for yy in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for xx in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((xx + 0.5 - cx) / rx) ** 2 + ((yy + 0.5 - cy) / ry) ** 2 <= 1:
                    self.set(xx, yy, c)

    def blit(self, other: "Canvas", ox: int, oy: int):
        for y in range(other.h):
            for x in range(other.w):
                p = other.px[y * other.w + x]
                if p[3]:
                    self.set(ox + x, oy + y, p)

    def png(self) -> bytes:
        raw = b"".join(b"\x00" + bytes(v for p in self.px[y * self.w:(y + 1) * self.w] for v in p)
                       for y in range(self.h))

        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))

    def save(self, path: Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.png())


# ====================================================================== pieces
T = 32
GRASS, DIRT, BRICK, BLOCK, STONE, WATER, WOOD, FLOOR = 0, 1, 2, 3, 4, 5, 6, 7    # tile indices


def tileset() -> Canvas:
    """8 tiles in one row: grass, dirt, brick, block, stone, water, wood, floor."""
    c = Canvas(T * 8, T)
    # 0 grass top
    c.rect(0, 0, T, T, (139, 94, 60))
    c.rect(0, 0, T, 9, (76, 175, 80))
    for x in range(0, T, 4):
        c.rect(x, 9, 2, 2, (76, 175, 80))
    for x, y in ((6, 18), (20, 24), (26, 14)):
        c.rect(x, y, 3, 2, (110, 74, 46))
    # 1 dirt
    c.rect(T, 0, T, T, (139, 94, 60))
    for x, y in ((5, 6), (19, 12), (9, 22), (25, 26), (14, 3)):
        c.rect(T + x, y, 3, 2, (110, 74, 46))
    # 2 brick
    c.rect(2 * T, 0, T, T, (183, 80, 50))
    for y in range(0, T, 8):
        c.rect(2 * T, y, T, 1, (120, 50, 30))
        off = 0 if (y // 8) % 2 == 0 else 8
        for x in range(off, T, 16):
            c.rect(2 * T + x, y, 1, 8, (120, 50, 30))
    # 3 question / bonus block
    c.rect(3 * T, 0, T, T, (240, 180, 40))
    c.outline(3 * T, 0, T, T, (150, 100, 20))
    c.rect(3 * T + 13, 8, 6, 3, (150, 100, 20))
    c.rect(3 * T + 17, 11, 3, 5, (150, 100, 20))
    c.rect(3 * T + 14, 16, 3, 3, (150, 100, 20))
    c.rect(3 * T + 14, 22, 3, 3, (150, 100, 20))
    # 4 stone
    c.rect(4 * T, 0, T, T, (128, 128, 136))
    c.outline(4 * T, 0, T, T, (90, 90, 98))
    c.rect(4 * T + 6, 6, 8, 6, (150, 150, 158))
    c.rect(4 * T + 18, 18, 8, 6, (150, 150, 158))
    # 5 water
    c.rect(5 * T, 0, T, T, (52, 120, 220))
    for x in range(0, T, 8):
        c.rect(5 * T + x, 6, 5, 2, (140, 190, 250))
        c.rect(5 * T + x + 3, 18, 5, 2, (140, 190, 250))
    # 6 wood planks
    c.rect(6 * T, 0, T, T, (160, 110, 60))
    for y in (0, 10, 21):
        c.rect(6 * T, y, T, 1, (110, 70, 35))
    # 7 floor (top-down)
    c.rect(7 * T, 0, T, T, (205, 190, 160))
    c.outline(7 * T, 0, T, T, (185, 170, 140))
    return c


def _hero(c: Canvas, ox: int, leg: int = 0, arm: int = 0, jump: bool = False, body=(52, 120, 220)):
    skin, hair, boots = (255, 205, 160), (90, 50, 20), (60, 40, 30)
    c.rect(ox + 10, 2, 12, 4, hair)                       # hair
    c.rect(ox + 10, 6, 12, 9, skin)                       # face
    c.rect(ox + 18, 9, 2, 2, (20, 20, 20))                # eye (looks right)
    c.rect(ox + 9, 15, 14, 9, body)                       # shirt
    c.rect(ox + 6, 16 + arm, 3, 7, skin)                  # arms
    c.rect(ox + 23, 16 - arm, 3, 7, skin)
    if jump:
        c.rect(ox + 9, 24, 6, 5, (40, 40, 90))
        c.rect(ox + 17, 22, 6, 5, (40, 40, 90))
        c.rect(ox + 8, 28, 6, 3, boots)
        c.rect(ox + 18, 26, 6, 3, boots)
    else:
        c.rect(ox + 10 + leg, 24, 5, 6, (40, 40, 90))     # legs
        c.rect(ox + 17 - leg, 24, 5, 6, (40, 40, 90))
        c.rect(ox + 9 + leg, 30, 7, 2, boots)
        c.rect(ox + 16 - leg, 30, 7, 2, boots)


def player_sheet() -> Canvas:
    """7 frames: idle 0-1, run 2-5, jump 6 (32x32 each)."""
    c = Canvas(T * 7, T)
    _hero(c, 0)
    _hero(c, T, arm=1)
    for i, leg in enumerate((-3, 0, 3, 0)):
        _hero(c, (2 + i) * T, leg=leg, arm=leg // 2)
    _hero(c, 6 * T, jump=True, arm=-3)
    return c


PLAYER_ANIMATIONS = {"idle": {"frames": [0, 1], "fps": 2, "loop": True},
                     "run": {"frames": [2, 3, 4, 5], "fps": 10, "loop": True},
                     "jump": {"frames": [6], "fps": 1, "loop": True}}


def coin_sheet() -> Canvas:
    """4 frames of a spinning coin (24x24)."""
    s = 24
    c = Canvas(s * 4, s)
    for i, rx in enumerate((9, 6, 2, 6)):
        c.ellipse(i * s + 12, 12, rx + 1, 10, (180, 120, 0))
        c.ellipse(i * s + 12, 12, rx, 9, (255, 205, 40))
        if rx > 3:
            c.rect(i * s + 11, 6, 2, 12, (255, 240, 150))
    return c


COIN_ANIMATIONS = {"spin": {"frames": [0, 1, 2, 3], "fps": 8, "loop": True}}


def enemy_sheet() -> Canvas:
    """2 walking frames of a slime-like enemy (32x32)."""
    c = Canvas(T * 2, T)
    for i, squash in enumerate((0, 2)):
        ox = i * T
        c.ellipse(ox + 16, 20 + squash / 2, 14 + squash, 11 - squash / 2, (120, 40, 140))
        c.ellipse(ox + 16, 19 + squash / 2, 12 + squash, 9 - squash / 2, (170, 70, 200))
        c.rect(ox + 9, 15, 4, 5, (255, 255, 255))
        c.rect(ox + 19, 15, 4, 5, (255, 255, 255))
        c.rect(ox + 10, 17, 2, 3, (20, 20, 20))
        c.rect(ox + 20, 17, 2, 3, (20, 20, 20))
    return c


ENEMY_ANIMATIONS = {"walk": {"frames": [0, 1], "fps": 4, "loop": True}}


def flag() -> Canvas:
    """The goal: a flag on a pole (32x64)."""
    c = Canvas(T, 2 * T)
    c.rect(4, 2, 3, 62, (90, 90, 90))
    c.ellipse(5.5, 3, 3, 3, (255, 215, 0))
    for y in range(6, 24):
        w = 22 - abs(15 - y)
        c.rect(7, y, max(4, w), 1, (230, 40, 60))
    c.rect(0, 60, 12, 4, (60, 60, 60))
    return c


def hero_topdown_sheet() -> Canvas:
    """Top-down hero: walk_down 0-1, walk_up 2-3, walk_left 4-5, walk_right 6-7."""
    c = Canvas(T * 8, T)
    for d in range(4):
        for f in range(2):
            ox = (d * 2 + f) * T
            step = 2 if f else -2
            c.ellipse(ox + 16, 18, 10, 11, (40, 140, 90))           # body
            c.ellipse(ox + 16, 12, 8, 8, (255, 205, 160))            # head
            c.rect(ox + 10 + step, 27, 4, 4, (60, 40, 30))           # feet
            c.rect(ox + 18 - step, 27, 4, 4, (60, 40, 30))
            if d == 0:      # down: eyes visible
                c.rect(ox + 12, 11, 2, 2, (20, 20, 20))
                c.rect(ox + 18, 11, 2, 2, (20, 20, 20))
            elif d == 1:    # up: hair
                c.ellipse(ox + 16, 11, 8, 7, (90, 50, 20))
            elif d == 2:
                c.rect(ox + 11, 11, 2, 2, (20, 20, 20))
            else:
                c.rect(ox + 19, 11, 2, 2, (20, 20, 20))
    return c


TOPDOWN_ANIMATIONS = {"walk_down": {"frames": [0, 1], "fps": 6, "loop": True},
                      "walk_up": {"frames": [2, 3], "fps": 6, "loop": True},
                      "walk_left": {"frames": [4, 5], "fps": 6, "loop": True},
                      "walk_right": {"frames": [6, 7], "fps": 6, "loop": True},
                      "idle_down": {"frames": [0], "fps": 1, "loop": True},
                      "idle_up": {"frames": [2], "fps": 1, "loop": True},
                      "idle_left": {"frames": [4], "fps": 1, "loop": True},
                      "idle_right": {"frames": [6], "fps": 1, "loop": True}}


def gem() -> Canvas:
    c = Canvas(20, 20)
    for y in range(20):
        w = 9 - abs(9 - y) if y < 10 else int((19 - y) * 0.9)
        c.rect(10 - w, y, 2 * w, 1, (60, 200, 230))
    c.rect(8, 4, 3, 3, (220, 250, 255))
    return c


def cloud() -> Canvas:
    c = Canvas(96, 40)
    for cx, cy, r in ((24, 26, 14), (46, 18, 18), (70, 26, 14), (48, 28, 16)):
        c.ellipse(cx, cy, r, r * 0.8, (255, 255, 255, 230))
    return c


def wav_beep(path: Path, freq: float = 880.0, ms: int = 120, volume: float = 0.4):
    """A short sine 'blip' WAV (coin sound)."""
    import math
    import wave
    rate = 22050
    n = int(rate * ms / 1000)
    frames = bytearray()
    for i in range(n):
        env = 1 - i / n
        f = freq * (1 + 0.5 * i / n)
        v = int(32767 * volume * env * math.sin(2 * math.pi * f * i / rate))
        frames += struct.pack("<h", v)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def write_platformer_assets(folder: Path) -> dict:
    """Write the platformer art into folder/assets and return the scene "assets" dict."""
    a = Path(folder) / "assets"
    tileset().save(a / "tiles.png")
    player_sheet().save(a / "player.png")
    coin_sheet().save(a / "coin.png")
    enemy_sheet().save(a / "enemy.png")
    flag().save(a / "flag.png")
    cloud().save(a / "cloud.png")
    wav_beep(a / "coin.wav")
    wav_beep(a / "jump.wav", 440, 90, 0.25)
    return {"images": {"flag": "assets/flag.png", "cloud": "assets/cloud.png"},
            "sounds": {"coin": "assets/coin.wav", "jump": "assets/jump.wav"},
            "spritesheets": {
                "player": {"image": "assets/player.png", "frame_w": 32, "frame_h": 32,
                           "animations": PLAYER_ANIMATIONS},
                "coin": {"image": "assets/coin.png", "frame_w": 24, "frame_h": 24, "animations": COIN_ANIMATIONS},
                "enemy": {"image": "assets/enemy.png", "frame_w": 32, "frame_h": 32,
                          "animations": ENEMY_ANIMATIONS}},
            "tilesets": {"tiles": {"image": "assets/tiles.png", "tile_w": 32, "tile_h": 32}}}


def write_topdown_assets(folder: Path) -> dict:
    a = Path(folder) / "assets"
    tileset().save(a / "tiles.png")
    hero_topdown_sheet().save(a / "hero.png")
    gem().save(a / "gem.png")
    enemy_sheet().save(a / "enemy.png")
    wav_beep(a / "pickup.wav", 990, 100)
    return {"images": {"gem": "assets/gem.png"},
            "sounds": {"pickup": "assets/pickup.wav"},
            "spritesheets": {
                "hero": {"image": "assets/hero.png", "frame_w": 32, "frame_h": 32, "animations": TOPDOWN_ANIMATIONS},
                "enemy": {"image": "assets/enemy.png", "frame_w": 32, "frame_h": 32,
                          "animations": ENEMY_ANIMATIONS}},
            "tilesets": {"tiles": {"image": "assets/tiles.png", "tile_w": 32, "tile_h": 32}}}


__all__ = ["Canvas", "tileset", "player_sheet", "coin_sheet", "enemy_sheet", "flag", "hero_topdown_sheet", "gem",
           "cloud", "wav_beep", "write_platformer_assets", "write_topdown_assets", "PLAYER_ANIMATIONS",
           "COIN_ANIMATIONS", "ENEMY_ANIMATIONS", "TOPDOWN_ANIMATIONS"]
