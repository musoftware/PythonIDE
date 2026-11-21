"""DOS Mode 13h Game Designer: 320 x 200 x 256 screens -> FreeBASIC, OpenWatcom C and 16-bit NASM code (pure
Python).

* **palette**: 256 VGA DAC entries, 6 bits per channel (0-63) - what ``OUT 3C8h / 3C9h`` loads.
* **Background** layer: a 320 x 200 bitmap (one palette index per pixel).
* **Tiles** layer: a 20 x 13 map of 16 x 16 tiles drawn over the bitmap (255 = no tile; tile pixels equal to
  ``settings["tile_key"]`` let the bitmap show through).
* **Collision** layer: one byte per tile cell, exported for the game code.
* **sprites**: named images with a transparent colour; **objects** place them (``player`` = moved by the arrow
  keys in the FreeBASIC / C programs).

Generated data (the same for every language):

==================  ============================================================================
``<N>.PAL``         768 bytes, 6-bit R G B per colour
``<N>.BG``          64000 bytes: the composed background (bitmap + tiles), row by row
``<N>.RLE``         the background run-length coded: (count 1..255, colour) pairs (for the .COM)
``<N>.SPR``         sprites as placed: "RSPR", count, then x, y, w, h (int16 LE), flags, key, pixels
``<N>.MAP / .COL``  tile map and collision bytes (20 x 13)
==================  ============================================================================

File names are 8.3 (``<N>`` = the design name, upper case, 8 characters). Programs: ``<N>.BAS`` (QBasic /
QuickBASIC dialect: runs in the user's own QBasic and builds with FreeBASIC ``-lang qb`` - the DOS fbc inside
DOSBox-X), ``<N>.C`` (OpenWatcom ``wcl -bt=dos -ml``; ``wcl386 -bt=dos -l=dos4g`` works too) and ``<N>.ASM``
(NASM ``-f bin`` -> .COM; embeds palette, RLE background and sprites, so it needs no files). The BASIC and C
programs accept ``/SHOT``: draw, save the screen to SCREEN.RAW, quit (the tests compare it with the design).
"""
from __future__ import annotations

import struct
from pathlib import Path

from .compat import system_palette
from .model import Design, Layer

SYSTEM = "dos13h"
EXT = ".m13scr"
TITLE = "DOS Mode 13h Screen"
W, H = 320, 200
NO_TILE = 255
SETTINGS_SCHEMA = {"tile_key": ("int", (0, 255)), "target": ("choice", ["nasm", "freebasic", "watcom"]),
                   "speed": ("int", (1, 8))}
OBJECT_SCHEMA = {"sprite": {"x": ("int", (-64, 383)), "y": ("int", (-64, 263)), "sprite": ("sprite", None),
                            "player": ("bool", None)}}
SPRITE_SCHEMA = {"transparent": ("int", (0, 255))}


def schema_for(obj: dict) -> dict:
    return OBJECT_SCHEMA["sprite"]


def default_palette() -> list[list[int]]:
    return [[r >> 2, g >> 2, b >> 2] for (r, g, b) in system_palette("vga")]


def _img(rows: list[str], cmap: dict) -> dict:
    w = max(len(r) for r in rows)
    px = bytearray(cmap.get(ch, 0) for r in rows for ch in r.ljust(w, "."))
    return {"w": w, "h": len(rows), "pixels": px, "transparent": 0}


HERO = ["....RRRR....", "...RRRRRRR..", "...SSSKS....", "..SSSSKSSS..", "..SSSSSKKK..", "....SSSSS...",
        "...BBRBB....", "..BBBRBBRB..", ".BBBBRRRRBB.", ".SSBRYRRYRS.", ".SSSRRRRRSS.", ".SSRRRRRRSS.",
        "...RRR.RRR..", "..KKK...KKK.", ".KKKK...KKKK", "............"]
SLIME = ["................", ".....GGGGGG.....", "...GGGGGGGGGG...", "..GGGGGGGGGGGG..", ".GGGWWGGGGWWGGG.",
         ".GGGWKGGGGWKGGG.", "GGGGGGGGGGGGGGGG", "GGGGGGGGGGGGGGGG", "GGGGGKKKKKKGGGGG", ".GGGGGGGGGGGGGG.",
         "..GGGGGGGGGGGG..", "................"]
COLORS = {".": 0, "R": 4, "S": 6 + 16, "K": 0x10, "B": 1, "Y": 14, "G": 2, "W": 15}
TILE_ROWS = {
    "brick": ["4444444C4444444C"] * 3 + ["CCCCCCCCCCCCCCCC"] + ["444C4444444C4444"] * 3 + ["CCCCCCCCCCCCCCCC"],
    "grass": ["AAAAAAAAAAAAAAAA", "A2AA2AAA2AA2AA2A", "2222222222222222"] + ["6666666666666666"] * 5,
    "stone": ["7777777777777778", "7888888888888878", "7877777777777878", "7878888888887878"] +
             ["7878777777787878"] * 2 + ["7877777777777878", "8888888888888888"],
    "water": ["1111111111111111", "1919119191191911", "9111991119911199", "1111111111111111"] * 2,
}


def _tile16(rows8: list[str]) -> bytearray:
    """8 rows of 16 hex digits drawn at double height -> 16 x 16."""
    out = bytearray()
    for r in rows8:
        line = bytes(int(ch, 16) for ch in r[:16].ljust(16, "0"))
        out += line + line
    return out


def new_design(name: str = "Screen1") -> Design:
    d = Design(SYSTEM, name, {"tile_key": 0, "target": "nasm", "speed": 2})
    d.palette = default_palette()
    d.tile_w = d.tile_h = 16
    d.tiles = [_tile16(TILE_ROWS[k]) for k in ("brick", "grass", "stone", "water")]
    d.sprites = {"Hero": _img(HERO, COLORS), "Slime": _img(SLIME, COLORS)}
    bg = Layer("Background", "bitmap", W, H, 1, 1)
    for i in range(16):                                 # colours 200-215: a sky ramp (dark to light blue)
        d.palette[200 + i] = [4 + i * 2, 12 + i * 3, 30 + i * 2]
    for y in range(H):
        bg.data[y * W:(y + 1) * W] = bytes([200 + min(15, y // 11)]) * W
    tiles = Layer("Tiles", "tiles", W // 16, (H + 15) // 16, 16, 16, fill=NO_TILE)
    col = Layer("Collision", "collision", W // 16, (H + 15) // 16, 16, 16)
    for x in range(tiles.w):
        tiles.set(x, 11, 1)
        tiles.set(x, 12, 0)
        col.set(x, 11, 1)
        col.set(x, 12, 1)
        if 6 <= x <= 9:
            tiles.set(x, 7, 2)
            col.set(x, 7, 1)
    d.layers = [bg, tiles, col]
    d.objects = [{"name": "Player", "kind": "sprite", "x": 40, "y": 160, "sprite": "Hero", "player": True},
                 {"name": "Slime1", "kind": "sprite", "x": 200, "y": 164, "sprite": "Slime", "player": False}]
    return d


def palette_rgb(d: Design) -> list:
    pal = (list(d.palette) + default_palette())[:256]
    return [((r & 63) * 255 // 63, (g & 63) * 255 // 63, (b & 63) * 255 // 63) for r, g, b in pal]


# ------------------------------------------------------------------ composition / encoding
def compose_background(d: Design, visible: set | None = None) -> bytearray:
    vis = (lambda name: True) if visible is None else (lambda name: name in visible)
    bg, tl = d.layer("Background"), d.layer("Tiles")
    buf = bytearray(bg.data) if (bg is not None and vis(bg.name)) else bytearray(W * H)
    key = int(d.settings.get("tile_key", 0))
    if tl is not None and vis(tl.name):
        tw, th = d.tile_w, d.tile_h
        for ty in range(tl.h):
            for tx in range(tl.w):
                t = tl.get(tx, ty)
                if t == NO_TILE or t >= len(d.tiles):
                    continue
                px = d.tiles[t]
                for y in range(th):
                    sy = ty * th + y
                    if sy >= H:
                        break
                    for x in range(tw):
                        v = px[y * tw + x]
                        if v != key:
                            sx = tx * tw + x
                            if sx < W:
                                buf[sy * W + sx] = v
    return buf


def placed_sprites(d: Design) -> list[dict]:
    """Objects clipped to the screen: {x, y, w, h, flags, key, pixels} (pixels of the visible part)."""
    out = []
    for o in d.objects:
        spr = d.sprites.get(o.get("sprite", ""))
        if o.get("kind") != "sprite" or not spr or o.get("hidden"):
            continue
        x0, y0, sw, sh = int(o.get("x", 0)), int(o.get("y", 0)), spr["w"], spr["h"]
        cx0, cy0 = max(0, x0), max(0, y0)
        cx1, cy1 = min(W, x0 + sw), min(H, y0 + sh)
        if cx1 <= cx0 or cy1 <= cy0:
            continue
        px = bytearray()
        for y in range(cy0, cy1):
            row = spr["pixels"][(y - y0) * sw:(y - y0 + 1) * sw]
            px += row[cx0 - x0:cx1 - x0]
        out.append({"x": cx0, "y": cy0, "w": cx1 - cx0, "h": cy1 - cy0, "flags": 1 if o.get("player") else 0,
                    "key": int(spr.get("transparent", 0)) & 0xFF, "pixels": px, "name": o.get("name", "")})
    return out


def render_indexed(d: Design, visible: set | None = None) -> tuple[int, int, bytearray, list]:
    vis = (lambda name: True) if visible is None else (lambda name: name in visible)
    buf = compose_background(d, visible)
    if vis("Objects"):
        for s in placed_sprites(d):
            draw_sprite(buf, s)
    return W, H, buf, palette_rgb(d)


def draw_sprite(buf: bytearray, s: dict) -> None:
    w, key, px = s["w"], s["key"], s["pixels"]
    for y in range(s["h"]):
        base = (s["y"] + y) * W + s["x"]
        for x in range(w):
            v = px[y * w + x]
            if v != key:
                buf[base + x] = v


def screen_after_draw(d: Design) -> bytearray:
    """What the generated programs show right after drawing (background + sprites)."""
    return render_indexed(d)[2]


def pal_bytes(d: Design) -> bytes:
    pal = (list(d.palette) + default_palette())[:256]
    return bytes(c & 63 for rgb in pal for c in rgb)


def rle_encode(data: bytes) -> bytes:
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        v = data[i]
        j = i + 1
        while j < n and j - i < 255 and data[j] == v:
            j += 1
        out += bytes([j - i, v])
        i = j
    return bytes(out)


def rle_decode(data: bytes) -> bytes:
    out = bytearray()
    for i in range(0, len(data) - 1, 2):
        out += bytes([data[i + 1]]) * data[i]
    return bytes(out)


def spr_bytes(d: Design) -> bytes:
    sprites = placed_sprites(d)
    out = bytearray(b"RSPR") + struct.pack("<H", len(sprites))
    for s in sprites:
        out += struct.pack("<hhHHBB", s["x"], s["y"], s["w"], s["h"], s["flags"], s["key"]) + bytes(s["pixels"])
    return bytes(out)


def map_bytes(d: Design, kind: str) -> bytes:
    lay = d.layer(kind)
    return bytes(lay.data) if lay else b""


# ------------------------------------------------------------------ code generation
def dos8(name: str) -> str:
    """8.3 base name (upper case, at most 8 letters / digits) for the DOS files of a design."""
    out = "".join(ch for ch in str(name).upper() if ch.isascii() and (ch.isalnum() or ch in "_-"))[:8]
    return out or "SCREEN"


def generate_basic(d: Design) -> str:
    """QBasic / QuickBASIC dialect (also FreeBASIC -lang qb): SCREEN 13, PALETTE, PSET / POINT, GET / PUT."""
    b = dos8(d.name)
    speed = max(1, int(d.settings.get("speed", 2)))
    return f"""' {b}.BAS - DOS mode 13h screen '{d.name}'
' Generated by RAD IDE (Mode 13h Game Designer). Re-generated when the design is saved.
' QBasic 1.1 / QuickBASIC 4.5 / FreeBASIC -lang qb. Reads {b}.PAL, {b}.BG and {b}.SPR from the current
' folder. Arrow keys move the player sprite, Esc quits. "{b} /SHOT" saves the screen to SCREEN.RAW and quits.
DEFINT A-Z
CONST SPD = {speed}
SCREEN 13
OPEN "{b}.PAL" FOR BINARY AS #1
p$ = SPACE$(768)
GET #1, , p$
CLOSE #1
FOR i = 0 TO 255
    r& = ASC(MID$(p$, i * 3 + 1, 1))
    g& = ASC(MID$(p$, i * 3 + 2, 1))
    b& = ASC(MID$(p$, i * 3 + 3, 1))
    PALETTE i, r& + g& * 256& + b& * 65536&
NEXT i
OPEN "{b}.BG" FOR BINARY AS #1
row$ = SPACE$(320)
FOR y = 0 TO 199
    GET #1, , row$
    FOR x = 0 TO 319
        PSET (x, y), ASC(MID$(row$, x + 1, 1))
    NEXT x
NEXT y
CLOSE #1
OPEN "{b}.SPR" FOR BINARY AS #1
h$ = SPACE$(4)
GET #1, , h$
GET #1, , n
IF n < 1 THEN n = 0
DIM sx(n), sy(n), sw(n), sh(n), sf(n), sk(n), so&(n)
f$ = " "
FOR i = 0 TO n - 1
    GET #1, , sx(i)
    GET #1, , sy(i)
    GET #1, , sw(i)
    GET #1, , sh(i)
    GET #1, , f$
    sf(i) = ASC(f$)
    GET #1, , f$
    sk(i) = ASC(f$)
    so&(i) = SEEK(1)
    SEEK #1, so&(i) + CLNG(sw(i)) * sh(i)
NEXT i
pl = -1
FOR i = 0 TO n - 1
    IF sf(i) AND 1 THEN
        IF pl < 0 THEN pl = i
    ELSE
        GOSUB DrawSprite
    END IF
NEXT i
IF pl >= 0 THEN
    DIM sv((CLNG(sw(pl)) * sh(pl) + 64) \\ 2)
    GET (sx(pl), sy(pl))-(sx(pl) + sw(pl) - 1, sy(pl) + sh(pl) - 1), sv
    i = pl
    GOSUB DrawSprite
END IF
IF INSTR(UCASE$(COMMAND$), "/SHOT") THEN
    GOSUB SaveShot
    CLOSE #1
    SCREEN 0
    WIDTH 80
    END
END IF
DO
    k$ = INKEY$
    IF k$ = CHR$(27) THEN EXIT DO
    IF LEN(k$) = 2 AND pl >= 0 THEN
        c = ASC(RIGHT$(k$, 1))
        dx = 0
        dy = 0
        IF c = 75 THEN dx = -SPD
        IF c = 77 THEN dx = SPD
        IF c = 72 THEN dy = -SPD
        IF c = 80 THEN dy = SPD
        IF dx <> 0 OR dy <> 0 THEN
            PUT (sx(pl), sy(pl)), sv, PSET
            sx(pl) = sx(pl) + dx
            sy(pl) = sy(pl) + dy
            IF sx(pl) < 0 THEN sx(pl) = 0
            IF sy(pl) < 0 THEN sy(pl) = 0
            IF sx(pl) > 320 - sw(pl) THEN sx(pl) = 320 - sw(pl)
            IF sy(pl) > 200 - sh(pl) THEN sy(pl) = 200 - sh(pl)
            GET (sx(pl), sy(pl))-(sx(pl) + sw(pl) - 1, sy(pl) + sh(pl) - 1), sv
            i = pl
            GOSUB DrawSprite
        END IF
    END IF
LOOP
CLOSE #1
SCREEN 0
WIDTH 80
END

DrawSprite:
    SEEK #1, so&(i)
    r$ = SPACE$(sw(i))
    FOR yy = 0 TO sh(i) - 1
        GET #1, , r$
        FOR xx = 0 TO sw(i) - 1
            v = ASC(MID$(r$, xx + 1, 1))
            IF v <> sk(i) THEN PSET (sx(i) + xx, sy(i) + yy), v
        NEXT xx
    NEXT yy
    RETURN

SaveShot:
    OPEN "SCREEN.RAW" FOR OUTPUT AS #2
    CLOSE #2
    OPEN "SCREEN.RAW" FOR BINARY AS #2
    FOR y = 0 TO 199
        row$ = ""
        FOR x = 0 TO 319
            row$ = row$ + CHR$(POINT(x, y))
        NEXT x
        PUT #2, , row$
    NEXT y
    CLOSE #2
    RETURN
"""


def generate_c(d: Design) -> str:
    nm = dos8(d.name)
    speed = max(1, int(d.settings.get("speed", 2)))
    return f"""/* {nm}.c - DOS mode 13h screen '{d.name}'
 * Generated by RAD IDE (Mode 13h Game Designer). Re-generated when the design is saved.
 * OpenWatcom 16-bit:  wcl -bt=dos -ml -fe={nm}.exe {nm}.c
 * OpenWatcom 32-bit:  wcl386 -bt=dos -l=dos4g -fe={nm}.exe {nm}.c
 * Reads {nm}.PAL, {nm}.BG and {nm}.SPR from the current folder. Arrow keys move the player, Esc quits.
 * "{nm} /SHOT" saves the screen to SCREEN.RAW and quits (used by RAD IDE's tests).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <malloc.h>
#include <conio.h>
#include <dos.h>
#include <i86.h>

#define SW 320
#define SH 200
#define SPEED {speed}

#ifdef __386__
typedef unsigned char *vptr;
#define VGA ((vptr)0xA0000)
#define BIGALLOC(n) malloc(n)
static void set_mode(int m) {{ union REGS r; memset(&r, 0, sizeof r); r.w.ax = m; int386(0x10, &r, &r); }}
#else
typedef unsigned char __far *vptr;
#define VGA ((vptr)MK_FP(0xA000, 0))
#define BIGALLOC(n) _fmalloc(n)
static void set_mode(int m) {{ union REGS r; memset(&r, 0, sizeof r); r.x.ax = m; int86(0x10, &r, &r); }}
#endif

typedef struct {{ int x, y, w, h, flags, key; vptr px; }} Sprite;

static Sprite spr[64];
static int nspr;
static vptr bg, back;

static int load_far(const char *name, vptr buf, unsigned n)
{{
    FILE *f = fopen(name, "rb");
    unsigned i;
    int c;
    if (!f) return 0;
    for (i = 0; i < n; i++) {{
        c = fgetc(f);
        if (c == EOF) break;
        buf[i] = (unsigned char)c;
    }}
    fclose(f);
    return i == n;
}}

static int rd16(FILE *f) {{ int lo = fgetc(f); int hi = fgetc(f); return (short)(lo | (hi << 8)); }}

static void load_sprites(const char *name)
{{
    FILE *f = fopen(name, "rb");
    char magic[4];
    int i;
    nspr = 0;
    if (!f) return;
    fread(magic, 1, 4, f);
    nspr = rd16(f) & 0xFFFF;
    if (nspr > 64) nspr = 64;
    for (i = 0; i < nspr; i++) {{
        unsigned n, k;
        spr[i].x = rd16(f); spr[i].y = rd16(f);
        spr[i].w = rd16(f) & 0xFFFF; spr[i].h = rd16(f) & 0xFFFF;
        spr[i].flags = fgetc(f); spr[i].key = fgetc(f);
        n = (unsigned)spr[i].w * (unsigned)spr[i].h;
        spr[i].px = (vptr)BIGALLOC(n);
        for (k = 0; k < n; k++) spr[i].px[k] = (unsigned char)fgetc(f);
    }}
    fclose(f);
}}

static void draw_sprite(vptr scr, const Sprite *s)
{{
    int x, y;
    for (y = 0; y < s->h; y++) {{
        int sy = s->y + y;
        if (sy < 0 || sy >= SH) continue;
        for (x = 0; x < s->w; x++) {{
            int sx = s->x + x;
            unsigned char v;
            if (sx < 0 || sx >= SW) continue;
            v = s->px[y * s->w + x];
            if (v != s->key) scr[(unsigned)sy * SW + sx] = v;
        }}
    }}
}}

static void wait_retrace(void)
{{
    while (inp(0x3DA) & 8) ;
    while (!(inp(0x3DA) & 8)) ;
}}

static void save_shot(void)
{{
    static unsigned char row[SW];
    FILE *f = fopen("SCREEN.RAW", "wb");
    unsigned y, x;
    if (!f) return;
    for (y = 0; y < SH; y++) {{
        for (x = 0; x < SW; x++) row[x] = VGA[y * SW + x];
        fwrite(row, 1, SW, f);
    }}
    fclose(f);
}}

int main(int argc, char **argv)
{{
    static unsigned char pal[768];
    unsigned i;
    int running = 1;
    int shot = argc > 1 && (strcmp(argv[1], "/SHOT") == 0 || strcmp(argv[1], "/shot") == 0);
    FILE *f = fopen("{nm}.PAL", "rb");
    if (!f) {{ printf("Cannot read {nm}.PAL\\n"); return 1; }}
    fread(pal, 1, 768, f);
    fclose(f);
    bg = (vptr)BIGALLOC(64000u);
    back = (vptr)BIGALLOC(64000u);
    if (!bg || !back || !load_far("{nm}.BG", bg, 64000u)) {{ printf("Cannot read {nm}.BG\\n"); return 1; }}
    load_sprites("{nm}.SPR");
    set_mode(0x13);
    outp(0x3C8, 0);
    for (i = 0; i < 768; i++) outp(0x3C9, pal[i]);
    for (i = 0; i < 64000u; i++) back[i] = bg[i];
    {{
        int s;
        for (s = 0; s < nspr; s++) draw_sprite(back, &spr[s]);
    }}
    for (i = 0; i < 64000u; i++) VGA[i] = back[i];
    if (shot) {{
        save_shot();
        set_mode(0x03);
        return 0;
    }}
    while (running) {{
        int s;
        if (kbhit()) {{
            int c = getch();
            int dx = 0, dy = 0;
            if (c == 27) running = 0;
            if (c == 0 || c == 0xE0) {{
                c = getch();
                if (c == 75) dx = -SPEED;
                if (c == 77) dx = SPEED;
                if (c == 72) dy = -SPEED;
                if (c == 80) dy = SPEED;
            }}
            for (s = 0; s < nspr; s++) if (spr[s].flags & 1) {{
                spr[s].x += dx; spr[s].y += dy;
                if (spr[s].x < 0) spr[s].x = 0;
                if (spr[s].y < 0) spr[s].y = 0;
                if (spr[s].x > SW - spr[s].w) spr[s].x = SW - spr[s].w;
                if (spr[s].y > SH - spr[s].h) spr[s].y = SH - spr[s].h;
            }}
        }}
        for (i = 0; i < 64000u; i++) back[i] = bg[i];
        for (s = 0; s < nspr; s++) draw_sprite(back, &spr[s]);
        wait_retrace();
        for (i = 0; i < 64000u; i++) VGA[i] = back[i];
    }}
    set_mode(0x03);
    return 0;
}}
"""


def _asm_db(data: bytes, per: int = 32) -> list[str]:
    return ["    db " + ",".join(str(b) for b in data[i:i + per]) for i in range(0, len(data), per)]


def generate_asm(d: Design) -> str:
    nm = dos8(d.name)
    sprites = placed_sprites(d)
    L = [f"; {nm}.ASM - DOS mode 13h screen '{d.name}' as a .COM program",
         "; Generated by RAD IDE (Mode 13h Game Designer). Re-generated when the design is saved.",
         f"; Build: nasm -f bin -o {nm}.COM {nm}.ASM   (palette, background and sprites are embedded)",
         "; Shows the screen, waits for a key, back to text mode.", "",
         "    cpu 8086", "    org 100h", "",
         "start:",
         "    mov ax, 0013h",
         "    int 10h",
         "    mov dx, 3C8h                ; VGA DAC: start at colour 0",
         "    xor al, al",
         "    out dx, al",
         "    inc dx",
         "    mov si, palette",
         "    mov cx, 768",
         ".pal:",
         "    lodsb",
         "    out dx, al",
         "    loop .pal",
         "    mov ax, 0A000h",
         "    mov es, ax",
         "    xor di, di",
         "    mov si, bg_rle",
         "    cld",
         ".rle:",
         "    cmp si, bg_rle_end",
         "    jae .sprites",
         "    lodsb",
         "    mov cl, al",
         "    xor ch, ch",
         "    lodsb",
         "    rep stosb",
         "    jmp .rle",
         ".sprites:",
         "    mov si, sprite_table",
         "    lodsw",
         "    mov bp, ax                  ; sprites left",
         ".next:",
         "    test bp, bp",
         "    jz .wait",
         "    lodsw                       ; x",
         "    mov di, ax",
         "    lodsw                       ; y",
         "    mov bx, ax",
         "    mov cl, 6",
         "    shl bx, cl                  ; y * 64",
         "    add di, bx",
         "    mov cl, 2",
         "    shl bx, cl                  ; y * 256",
         "    add di, bx                  ; di = y * 320 + x",
         "    lodsw",
         "    mov dx, ax                  ; width",
         "    lodsw",
         "    mov bx, ax                  ; height",
         "    lodsb                       ; flags (unused here)",
         "    lodsb",
         "    mov ah, al                  ; transparent colour",
         ".row:",
         "    mov cx, dx",
         "    push di",
         ".px:",
         "    lodsb",
         "    cmp al, ah",
         "    je .skip",
         "    mov [es:di], al",
         ".skip:",
         "    inc di",
         "    loop .px",
         "    pop di",
         "    add di, 320",
         "    dec bx",
         "    jnz .row",
         "    dec bp",
         "    jmp .next",
         ".wait:",
         "    xor ah, ah",
         "    int 16h",
         "    mov ax, 0003h",
         "    int 10h",
         "    mov ax, 4C00h",
         "    int 21h", "",
         "palette:"]
    L += _asm_db(pal_bytes(d))
    L += ["", "bg_rle:"]
    L += _asm_db(rle_encode(bytes(compose_background(d))))
    L += ["bg_rle_end:", "", "sprite_table:", f"    dw {len(sprites)}"]
    for s in sprites:
        L.append(f"    dw {s['x']}, {s['y']}, {s['w']}, {s['h']}   ; {s['name']}")
        L.append(f"    db {s['flags']}, {s['key']}")
        L += _asm_db(bytes(s["pixels"]))
    return "\n".join(L) + "\n"


def com_size_estimate(d: Design) -> int:
    return 200 + 768 + len(rle_encode(bytes(compose_background(d)))) + \
        sum(10 + len(s["pixels"]) for s in placed_sprites(d))


def generate(d: Design, outdir) -> dict:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    b = dos8(d.name)
    files = []
    bgdata = bytes(compose_background(d))
    for fname, data in ((f"{b}.PAL", pal_bytes(d)), (f"{b}.BG", bgdata), (f"{b}.RLE", rle_encode(bgdata)),
                        (f"{b}.SPR", spr_bytes(d)), (f"{b}.MAP", map_bytes(d, "Tiles")),
                        (f"{b}.COL", map_bytes(d, "collision"))):
        p = out / fname
        p.write_bytes(data)
        files.append(p)
    warnings = []
    texts = [(f"{b}.BAS", generate_basic(d)), (f"{b}.C", generate_c(d))]
    if com_size_estimate(d) < 65000:
        texts.append((f"{b}.ASM", generate_asm(d)))
    else:
        warnings.append("The screen is too detailed for a .COM program (64 KB): use the BASIC or C version")
    for fname, text in texts:
        p = out / fname
        p.write_text(text, encoding="ascii", errors="replace", newline="\r\n")
        files.append(p)
    target = str(d.settings.get("target", "nasm"))
    main = {"freebasic": f"{b}.BAS", "watcom": f"{b}.C"}.get(target, f"{b}.ASM")
    exe = f"{b}.COM" if target == "nasm" else f"{b}.EXE"
    return {"main": out / main, "files": files, "warnings": warnings, "rom": out / exe, "system": "dos"}


def custom_build(d: Design, outdir, log=print, download: bool = False):
    """FreeBASIC (DOS fbc inside DOSBox-X, -lang qb) and OpenWatcom (wcl -bt=dos -ml) go through the DOS
    development slice's builder (radide.retro.dos.build). Returns (ok, exe path) or None for NASM."""
    target = str(d.settings.get("target", "nasm"))
    if target not in ("freebasic", "watcom"):
        return None
    from types import SimpleNamespace
    from ...dos.build import Builder
    b = dos8(d.name)
    lang, main, compiler = (("dos-qbasic", f"{b}.BAS", "freebasic") if target == "freebasic"
                            else ("dos-c", f"{b}.C", "openwatcom"))
    proj = SimpleNamespace(language=lang, name=b, folder=str(outdir), startup=main, modules=[main],
                           extra={"dos": {"main": main, "exe": b, "compiler": compiler, "model": "large",
                                          "output": "exe", "warnings": False}})
    ok = Builder(Path(outdir), project=proj, log=log, download=download).build()
    return ok, Path(outdir) / f"{b}.EXE"


def build_commands(d: Design, outdir, find) -> list[tuple[list[str], str]]:
    b = dos8(d.name)
    nasm = find("nasm")
    if not nasm:
        raise FileNotFoundError("nasm")
    return [([nasm, "-f", "bin", "-o", f"{b}.COM", f"{b}.ASM"], str(outdir))]
