"""Game Boy Map Designer: background map, window, sprites -> RGBDS data + a small ROM (pure Python).

* **Background** layer: 32 x 32 tiles ($9800); SCX / SCY pick the 20 x 18 tile part on screen.
* **Window** layer: 32 x 32 tiles ($9C00) shown from WX - 7 / WY (only the top-left 20 x 18 can be seen).
* **Collision** layer: one byte per background tile, exported as a table.
* **Objects**: sprites (tile or ``w`` x ``h`` metasprite from a 16-wide sheet) at screen positions.
* 256 tiles (2 bits per pixel) shared by background, window and sprites ($8000 addressing, LCDC bit 4 = 1);
  BGP / OBP0 / OBP1 map the 4 colour numbers to the 4 shades.

Generated files: ``<name>.2bpp`` (tiles), ``<name>_bg.tilemap``, ``<name>_win.tilemap``, ``<name>_data.inc``
(sprites, palettes, scroll / window settings, collision) and ``<name>.asm`` that copies everything to VRAM / OAM
with the LCD off and switches it on. Build: ``rgbasm`` + ``rgblink`` + ``rgbfix -v -p 0xFF``.
"""
from __future__ import annotations

from pathlib import Path

from . import art
from .compat import encode_tile, system_palette
from .model import Design, Layer, byte_lines, ident

SYSTEM = "gb"
EXT = ".gbmap"
TITLE = "Game Boy Map"
SETTINGS_SCHEMA = {"scx": ("int", (0, 255)), "scy": ("int", (0, 255)), "window": ("bool", None),
                   "wx": ("int", (7, 166)), "wy": ("int", (0, 143)), "bgp": ("int", (0, 255)),
                   "obp0": ("int", (0, 255)), "obp1": ("int", (0, 255))}
OBJECT_SCHEMA = {"sprite": {"x": ("int", (0, 167)), "y": ("int", (0, 159)), "tile": ("int", (0, 255)),
                            "w": ("int", (1, 4)), "h": ("int", (1, 4)), "palette": ("int", (0, 1)),
                            "flip_h": ("bool", None), "flip_v": ("bool", None), "behind": ("bool", None)}}
SPRITE_BASE = 128           # sprite tiles live in the upper half of the tile set by default


def schema_for(obj: dict) -> dict:
    return OBJECT_SCHEMA["sprite"]


def new_design(name: str = "Map1") -> Design:
    d = Design(SYSTEM, name, {"scx": 0, "scy": 0, "window": True, "wx": 7, "wy": 128,
                              "bgp": 0xE4, "obp0": 0xE4, "obp1": 0xD2})
    bg_tiles = art.bg_tileset(128)
    spr = art.sprite_tileset(128)
    d.tiles = bg_tiles + spr
    bg = Layer("Background", "tiles", 32, 32, 8, 8)
    win = Layer("Window", "tiles", 32, 32, 8, 8)
    col = Layer("Collision", "collision", 32, 32, 8, 8)
    for x in range(32):
        for y in (16, 17):
            bg.set(x, y, 5 if y == 16 else 4)
            col.set(x, y, 1)
        if x % 10 == 2:
            bg.set(x, 4, 7)
            bg.set(x + 1, 4, 8)
    for x in range(20):
        win.set(x, 0, 6)
        win.set(x, 1, 0x20)
    for i, ch in enumerate(art.text_tiles(f"SCORE 0000  {name[:6]}")):
        win.set(1 + i, 1, ch)
    d.layers = [bg, win, col]
    d.objects = [{"name": "Hero", "kind": "sprite", "x": 32, "y": 112, "tile": SPRITE_BASE, "w": 2, "h": 2,
                  "palette": 0, "flip_h": False, "flip_v": False, "behind": False},
                 {"name": "Enemy1", "kind": "sprite", "x": 120, "y": 120, "tile": SPRITE_BASE + 2, "w": 1, "h": 1,
                  "palette": 1, "flip_h": False, "flip_v": False, "behind": False}]
    return d


def shades() -> list:
    return system_palette("gb")


def _map_pal(byte: int) -> list[int]:
    return [(byte >> (2 * i)) & 3 for i in range(4)]


def hw_sprites(d: Design) -> list[tuple[int, int, int, int]]:
    """(screen x, screen y, tile, flags) - OAM wants y + 16 / x + 8."""
    out = []
    for o in d.objects:
        if o.get("kind") != "sprite" or o.get("hidden"):
            continue
        w, h = max(1, int(o.get("w", 1))), max(1, int(o.get("h", 1)))
        flags = (0x80 if o.get("behind") else 0) | (0x40 if o.get("flip_v") else 0) | \
            (0x20 if o.get("flip_h") else 0) | (0x10 if int(o.get("palette", 0)) else 0)
        for r in range(h):
            for c in range(w):
                sc = (w - 1 - c) if o.get("flip_h") else c
                sr = (h - 1 - r) if o.get("flip_v") else r
                out.append((int(o.get("x", 0)) + c * 8, int(o.get("y", 0)) + r * 8,
                            (int(o.get("tile", 0)) + sr * 16 + sc) & 0xFF, flags))
    return out[:40]


def oam_bytes(d: Design) -> bytes:
    out = bytearray()
    for x, y, t, f in hw_sprites(d):
        out += bytes([(y + 16) & 0xFF, (x + 8) & 0xFF, t, f])
    return bytes(out)


def tiles_2bpp(d: Design) -> bytes:
    return b"".join(encode_tile("gb", d.tile(i)) for i in range(256))


def tilemap(d: Design, name: str) -> bytes:
    lay = d.layer(name)
    return bytes(lay.get(x, y) for y in range(32) for x in range(32)) if lay else bytes(1024)


# ------------------------------------------------------------------ preview
def render_indexed(d: Design, visible: set | None = None) -> tuple[int, int, bytearray, list]:
    """The 160 x 144 LCD (shade index per pixel). SCX / SCY wrap the 256 x 256 background."""
    vis = (lambda name: True) if visible is None else (lambda name: name in visible)
    s = d.settings
    W, H = 160, 144
    bgp, obp = _map_pal(int(s.get("bgp", 0xE4))), [_map_pal(int(s.get("obp0", 0xE4))),
                                                   _map_pal(int(s.get("obp1", 0xD2)))]
    buf = bytearray(W * H)
    raw = bytearray(W * H)                     # colour numbers for sprite priority
    bg, win = d.layer("Background"), d.layer("Window")
    scx, scy = int(s.get("scx", 0)), int(s.get("scy", 0))
    if bg is not None and vis(bg.name):
        for y in range(H):
            by = (y + scy) & 255
            for x in range(W):
                bx = (x + scx) & 255
                v = d.tile(bg.get(bx // 8, by // 8))[(by % 8) * 8 + bx % 8]
                raw[y * W + x] = v
                buf[y * W + x] = bgp[v]
    else:
        buf = bytearray([bgp[0]]) * (W * H)
    if win is not None and s.get("window", True) and vis(win.name):
        wx, wy = int(s.get("wx", 7)) - 7, int(s.get("wy", 0))
        for y in range(max(0, wy), H):
            for x in range(max(0, wx), W):
                tx, ty = x - wx, y - wy
                v = d.tile(win.get(tx // 8, ty // 8))[(ty % 8) * 8 + tx % 8]
                raw[y * W + x] = v
                buf[y * W + x] = bgp[v]
    if vis("Objects"):
        for x0, y0, t, f in reversed(hw_sprites(d)):
            px = d.tile(t)
            pal = obp[1 if f & 0x10 else 0]
            for y in range(8):
                for x in range(8):
                    sx, sy = x0 + x, y0 + y
                    if not (0 <= sx < W and 0 <= sy < H):
                        continue
                    v = px[(7 - y if f & 0x40 else y) * 8 + (7 - x if f & 0x20 else x)]
                    if v and not (f & 0x80 and raw[sy * W + sx]):
                        buf[sy * W + sx] = pal[v]
    return W, H, buf, shades()


# ------------------------------------------------------------------ code generation
def generate_data(d: Design) -> str:
    nm = ident(d.name)
    s = d.settings
    col = d.layer("collision")
    oam = oam_bytes(d)
    lcdc = 0x80 | 0x10 | 0x02 | 0x01 | ((0x20 | 0x40) if s.get("window", True) else 0)
    L = [f"; {nm}_data.inc - Game Boy map '{d.name}' (generated by RAD IDE, re-generated on save)", "",
         f"DEF {nm}_BGP EQU ${int(s.get('bgp', 0xE4)) & 0xFF:02X}",
         f"DEF {nm}_OBP0 EQU ${int(s.get('obp0', 0xE4)) & 0xFF:02X}",
         f"DEF {nm}_OBP1 EQU ${int(s.get('obp1', 0xD2)) & 0xFF:02X}",
         f"DEF {nm}_SCX EQU {int(s.get('scx', 0)) & 0xFF}", f"DEF {nm}_SCY EQU {int(s.get('scy', 0)) & 0xFF}",
         f"DEF {nm}_WX EQU {int(s.get('wx', 7)) & 0xFF}", f"DEF {nm}_WY EQU {int(s.get('wy', 0)) & 0xFF}",
         f"DEF {nm}_LCDC EQU ${lcdc:02X}", "", 'SECTION "' + nm + ' data", ROM0', "",
         f"{nm}_Tiles:", f'    INCBIN "{nm}.2bpp"', f"{nm}_TilesEnd:", "",
         f"{nm}_BgMap:", f'    INCBIN "{nm}_bg.tilemap"', "", f"{nm}_WinMap:", f'    INCBIN "{nm}_win.tilemap"', "",
         "; OAM entries: y+16, x+8, tile, flags", f"{nm}_Sprites:"]
    L += byte_lines(oam, "db") if oam else []
    L += [f"{nm}_SpritesEnd:", "", "; collision: one byte per background tile, 32 x 32, row by row",
          f"{nm}_Collision:"]
    for y in range(32):
        L += byte_lines([col.get(x, y) if col else 0 for x in range(32)], "db", 32)
    return "\n".join(L) + "\n"


def generate_main(d: Design) -> str:
    nm = ident(d.name)
    return f"""; {nm}.asm - shows the Game Boy map '{d.name}' (generated by RAD IDE, re-generated on save)
; Build:  rgbasm -o {nm}.o {nm}.asm
;         rgblink -o {nm}.gb -n {nm}.sym -m {nm}.map {nm}.o
;         rgbfix -v -p 0xFF -t "{nm[:11].upper()}" {nm}.gb

DEF rLCDC EQU $FF40
DEF rSCY  EQU $FF42
DEF rSCX  EQU $FF43
DEF rLY   EQU $FF44
DEF rBGP  EQU $FF47
DEF rOBP0 EQU $FF48
DEF rOBP1 EQU $FF49
DEF rWY   EQU $FF4A
DEF rWX   EQU $FF4B
DEF rIE   EQU $FFFF

INCLUDE "{nm}_data.inc"

SECTION "Header", ROM0[$100]
    nop
    jp Start
    ds $150 - @, 0              ; logo, title and checksums: filled in by rgbfix

SECTION "Main", ROM0[$150]
Start:
    di
    ld sp, $FFFE
.waitVBlank
    ldh a, [rLY]
    cp 144
    jr c, .waitVBlank
    xor a
    ldh [rLCDC], a              ; LCD off: VRAM and OAM are free to write
    ld de, {nm}_Tiles
    ld hl, $8000
    ld bc, {nm}_TilesEnd - {nm}_Tiles
    call MemCopy
    ld de, {nm}_BgMap
    ld hl, $9800
    ld bc, 1024
    call MemCopy
    ld de, {nm}_WinMap
    ld hl, $9C00
    ld bc, 1024
    call MemCopy
    ld hl, $FE00                ; clear OAM (y = 0 hides a sprite)
    ld b, 160
    xor a
.clearOam
    ld [hli], a
    dec b
    jr nz, .clearOam
    ld de, {nm}_Sprites
    ld hl, $FE00
    ld bc, {nm}_SpritesEnd - {nm}_Sprites
    call MemCopy
    ld a, {nm}_BGP
    ldh [rBGP], a
    ld a, {nm}_OBP0
    ldh [rOBP0], a
    ld a, {nm}_OBP1
    ldh [rOBP1], a
    ld a, {nm}_SCX
    ldh [rSCX], a
    ld a, {nm}_SCY
    ldh [rSCY], a
    ld a, {nm}_WX
    ldh [rWX], a
    ld a, {nm}_WY
    ldh [rWY], a
    xor a
    ldh [rIE], a
    ld a, {nm}_LCDC
    ldh [rLCDC], a
.forever
    jr .forever

MemCopy:                        ; copy bc bytes from de to hl (bc = 0 copies nothing)
    ld a, b
    or c
    ret z
.loop
    ld a, [de]
    ld [hli], a
    inc de
    dec bc
    ld a, b
    or c
    jr nz, .loop
    ret
"""


def generate(d: Design, outdir) -> dict:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    nm = ident(d.name)
    files = []
    for fname, data in ((f"{nm}.2bpp", tiles_2bpp(d)), (f"{nm}_bg.tilemap", tilemap(d, "Background")),
                        (f"{nm}_win.tilemap", tilemap(d, "Window"))):
        p = out / fname
        p.write_bytes(data)
        files.append(p)
    for fname, text in ((f"{nm}.asm", generate_main(d)), (f"{nm}_data.inc", generate_data(d))):
        p = out / fname
        p.write_text(text, encoding="utf-8")
        files.append(p)
    warnings = []
    n = sum(max(1, int(o.get("w", 1))) * max(1, int(o.get("h", 1))) for o in d.objects if o.get("kind") == "sprite")
    if n > 40:
        warnings.append(f"{n} hardware sprites - the Game Boy has 40; the rest are left out")
    return {"main": files[3], "files": files, "warnings": warnings, "rom": out / f"{nm}.gb", "system": SYSTEM}


def build_commands(d: Design, outdir, find) -> list[tuple[list[str], str]]:
    nm = ident(d.name)
    tools = {t: find(t) for t in ("rgbasm", "rgblink", "rgbfix")}
    for t, p in tools.items():
        if not p:
            raise FileNotFoundError(t)
    return [([tools["rgbasm"], "-o", f"{nm}.o", f"{nm}.asm"], str(outdir)),
            ([tools["rgblink"], "-o", f"{nm}.gb", "-n", f"{nm}.sym", "-m", f"{nm}.map", f"{nm}.o"], str(outdir)),
            ([tools["rgbfix"], "-v", "-p", "0xFF", "-t", nm[:11].upper(), f"{nm}.gb"], str(outdir))]
