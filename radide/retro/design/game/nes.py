"""NES Screen / Level Designer: model, PPU preview and the ca65 / ld65 generator (pure Python).

* **Nametable** layer: ``screens * 32`` x 30 tiles (a level is several screens side by side).
* **Attributes** layer: one palette (0-3) per 16x16 metatile, packed into the attribute table (one byte per
  32x32 block: bits 0-1 top-left, 2-3 top-right, 4-5 bottom-left, 6-7 bottom-right metatile).
* **Collision** layer: one byte per tile, exported as a table for the game code.
* **Objects**: sprites (one tile or a ``w`` x ``h`` metasprite from the 16-wide sprite sheet) at world positions.
* **CHR**: 256 background tiles ($0000) + 256 sprite tiles ($1000) - edited in the designer's tile editor (or
  the retro graphics editors) and written as ``<name>.chr``.

The generated NROM program (vertical mirroring = two name tables side by side) loads the palettes, draws the
first 64 columns, enables NMI and then scrolls with the D-pad (or automatically): every time the camera crosses
an 8-pixel column the NMI streams the new column (30 tiles, PPU +32 increment) and its attribute bytes, copies
the sprites with OAM DMA and sets the scroll. Sprites are placed at ``world x - camera x`` (hidden off screen).
"""
from __future__ import annotations

from pathlib import Path

from . import art
from .compat import encode_tile, system_palette
from .model import Design, Layer, byte_lines, ident

SYSTEM = "nes"
EXT = ".nesscr"
TITLE = "NES Screen / Level"
MAX_SCREENS = 8
MAX_SPRITES = 64

SETTINGS_SCHEMA = {"screens": ("int", (1, MAX_SCREENS)), "scroll": ("choice", ["dpad", "auto", "none"]),
                   "speed": ("int", (1, 4))}
OBJECT_SCHEMA = {"sprite": {"x": ("int", (0, 2047)), "y": ("int", (0, 239)), "tile": ("int", (0, 255)),
                            "w": ("int", (1, 4)), "h": ("int", (1, 4)), "palette": ("int", (0, 3)),
                            "flip_h": ("bool", None), "flip_v": ("bool", None), "behind": ("bool", None)}}

DEFAULT_PALETTES = [[0x21, 0x07, 0x17, 0x27], [0x21, 0x0A, 0x1A, 0x2A], [0x21, 0x0F, 0x00, 0x30],
                    [0x21, 0x16, 0x27, 0x30],
                    [0x21, 0x16, 0x27, 0x18], [0x21, 0x0F, 0x2C, 0x30], [0x21, 0x06, 0x28, 0x38],
                    [0x21, 0x12, 0x22, 0x32]]


def schema_for(obj: dict) -> dict:
    return OBJECT_SCHEMA["sprite"]


def screens(d: Design) -> int:
    return max(1, min(MAX_SCREENS, int(d.settings.get("screens", 1))))


def new_design(name: str = "Level1", n_screens: int = 2) -> Design:
    n = max(1, min(MAX_SCREENS, int(n_screens)))
    d = Design(SYSTEM, name, {"screens": n, "scroll": "dpad", "speed": 1})
    d.palette = [list(p) for p in DEFAULT_PALETTES]
    d.tiles = art.bg_tileset(256) + art.sprite_tileset(256)
    nt = Layer("Nametable", "tiles", 32 * n, 30, 8, 8)
    at = Layer("Attributes", "attributes", 16 * n, 15, 16, 16)
    col = Layer("Collision", "collision", 32 * n, 30, 8, 8)
    w = 32 * n
    for x in range(w):                      # ground, a few platforms, clouds
        for y in (26, 27, 28, 29):
            nt.set(x, y, 5 if y == 26 else 4)
            col.set(x, y, 1)
        if x % 12 == 3:
            nt.set(x, 6, 7)
            nt.set(x + 1, 6, 8)
        if x % 16 in (8, 9, 10):
            nt.set(x, 20, 6)
            col.set(x, 20, 1)
    for x in range(16 * n):
        at.set(x, 13, 0)                    # bricks palette at the bottom
        at.set(x, 14, 0)
        for y in range(0, 13):
            at.set(x, y, 2 if y < 5 else 1)
    for i, ch in enumerate(art.text_tiles(f"{name[:20]}")):
        nt.set(2 + i, 2, ch)
    d.layers = [nt, at, col]
    d.objects = [{"name": "Hero", "kind": "sprite", "x": 40, "y": 192, "tile": 0, "w": 2, "h": 2, "palette": 0,
                  "flip_h": False, "flip_v": False, "behind": False},
                 {"name": "Enemy1", "kind": "sprite", "x": 150, "y": 200, "tile": 2, "w": 1, "h": 1, "palette": 1,
                  "flip_h": False, "flip_v": False, "behind": False}]
    return d


def set_screens(d: Design, n: int) -> None:
    n = max(1, min(MAX_SCREENS, int(n)))
    d.settings["screens"] = n
    for lay in d.layers:
        if lay.kind == "attributes":
            lay.resize(16 * n, 15)
        else:
            lay.resize(32 * n, 30)


def master_palette() -> list:
    return system_palette("nes")


# ------------------------------------------------------------------ encoding
def attribute_byte(at: Layer, gx: int, ay: int) -> int:
    """Attribute byte of the 32x32 block (*gx*, *ay*): metatiles (2gx, 2ay), (2gx+1, 2ay), (2gx, 2ay+1),
    (2gx+1, 2ay+1) -> bits 0-1, 2-3, 4-5, 6-7. Row 7 only has its top half on screen (30 tile rows)."""
    v = 0
    for q, (dx, dy) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
        mx, my = gx * 2 + dx, ay * 2 + dy
        if my < at.h:
            v |= (at.get(mx, my) & 3) << (q * 2)
    return v


def attribute_table(d: Design, screen: int = 0) -> bytes:
    at = d.layer("attributes")
    return bytes(attribute_byte(at, screen * 8 + ax, ay) for ay in range(8) for ax in range(8))


def unpack_attribute_table(data: bytes) -> list[list[int]]:
    """64 bytes -> 15 x 16 metatile palettes (rows), the inverse of :func:`attribute_table`."""
    out = [[0] * 16 for _ in range(15)]
    for ay in range(8):
        for ax in range(8):
            v = data[ay * 8 + ax]
            for q, (dx, dy) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
                my = ay * 2 + dy
                if my < 15:
                    out[my][ax * 2 + dx] = (v >> (q * 2)) & 3
    return out


def nametable(d: Design, screen: int = 0) -> bytes:
    nt = d.layer("Nametable")
    return bytes(nt.get(screen * 32 + x, y) for y in range(30) for x in range(32))


def chr_bytes(d: Design) -> bytes:
    out = bytearray()
    for i in range(512):
        out += encode_tile("nes", d.tile(i))
    return bytes(out)


def palette_bytes(d: Design) -> bytes:
    pals = (d.palette + DEFAULT_PALETTES)[:8]
    out = bytearray()
    for i, p in enumerate(pals):
        p = (list(p) + [0x0F] * 4)[:4]
        out += bytes([pals[0][0] & 0x3F] + [c & 0x3F for c in p[1:]])
    return bytes(out)


def hw_sprites(d: Design) -> list[tuple[int, int, int, int]]:
    """Objects expanded to hardware sprites: (world x, screen y, tile, attribute)."""
    out = []
    for o in d.objects:
        if o.get("kind") != "sprite" or o.get("hidden"):
            continue
        w, h = max(1, int(o.get("w", 1))), max(1, int(o.get("h", 1)))
        attr = (int(o.get("palette", 0)) & 3) | (0x20 if o.get("behind") else 0) | \
            (0x40 if o.get("flip_h") else 0) | (0x80 if o.get("flip_v") else 0)
        for r in range(h):
            for c in range(w):
                sc = (w - 1 - c) if o.get("flip_h") else c
                sr = (h - 1 - r) if o.get("flip_v") else r
                tile = (int(o.get("tile", 0)) + sr * 16 + sc) & 0xFF
                out.append((int(o.get("x", 0)) + c * 8, int(o.get("y", 0)) + r * 8, tile, attr))
    return out


# ------------------------------------------------------------------ preview
def render_indexed(d: Design, visible: set | None = None) -> tuple[int, int, bytearray, list]:
    """(screens*256, 240, NES palette index per pixel, master palette)."""
    vis = (lambda name: True) if visible is None else (lambda name: name in visible)
    n = screens(d)
    W, H = 256 * n, 240
    pal = palette_bytes(d)
    buf = bytearray([pal[0]]) * (W * H)
    nt, at = d.layer("Nametable"), d.layer("attributes")
    if nt is not None and vis(nt.name):
        for ty in range(30):
            for tx in range(32 * n):
                t = d.tile(nt.get(tx, ty))
                p = (at.get(tx // 2, ty // 2) if (at is not None and vis(at.name)) else 0) & 3
                cols = pal[p * 4:p * 4 + 4]
                for y in range(8):
                    row = t[y * 8:y * 8 + 8]
                    base = (ty * 8 + y) * W + tx * 8
                    buf[base:base + 8] = bytes(cols[v] if v else pal[0] for v in row)
    if vis("Objects"):
        for x0, y0, tile, attr in reversed(hw_sprites(d)):       # lower OAM index wins -> draw it last
            t = d.tile(256 + tile)
            p = 4 + (attr & 3)
            cols = pal[p * 4:p * 4 + 4]
            for y in range(8):
                sy = y0 + y
                if not 0 <= sy < H:
                    continue
                for x in range(8):
                    sx = x0 + x
                    if not 0 <= sx < W:
                        continue
                    v = t[(7 - y if attr & 0x80 else y) * 8 + (7 - x if attr & 0x40 else x)]
                    if v and not (attr & 0x20 and buf[sy * W + sx] != pal[0]):
                        buf[sy * W + sx] = cols[v]
    return W, H, buf, master_palette()


# ------------------------------------------------------------------ code generation
NROM_CFG = """# nrom.cfg - ld65 memory map for a 32K PRG / 8K CHR NROM cartridge (generated by RAD IDE)
MEMORY {
    ZP:     start = $00,   size = $100,  type = rw, file = "";
    OAM:    start = $0200, size = $100,  type = rw, file = "";
    RAM:    start = $0300, size = $500,  type = rw, file = "";
    HDR:    start = $0000, size = $10,   type = ro, file = %O, fill = yes;
    PRG:    start = $8000, size = $8000, type = ro, file = %O, fill = yes, fillval = $FF;
    CHR:    start = $0000, size = $2000, type = ro, file = %O, fill = yes;
}
SEGMENTS {
    ZEROPAGE: load = ZP,  type = zp;
    OAM:      load = OAM, type = bss, align = $100;
    BSS:      load = RAM, type = bss;
    HEADER:   load = HDR, type = ro;
    CODE:     load = PRG, type = ro, start = $8000;
    RODATA:   load = PRG, type = ro;
    VECTORS:  load = PRG, type = ro, start = $FFFA;
    CHARS:    load = CHR, type = ro;
}
"""


def generate_data(d: Design) -> str:
    nm = ident(d.name)
    n = screens(d)
    ncols = 32 * n
    nt, at, col = d.layer("Nametable"), d.layer("attributes"), d.layer("collision")
    spr = hw_sprites(d)[:MAX_SPRITES]
    L = [f"; {nm}_data.s - NES level '{d.name}' ({n} screen(s), {ncols} columns)",
         "; Generated by RAD IDE (NES Screen / Level Designer). Re-generated when the design is saved.", "",
         f"{nm}_NCOLS = {ncols}", f"{nm}_NSPR = {len(spr)}", "",
         "; palettes: 4 background + 4 sprite palettes ($3F00-$3F1F)", f"{nm}_palette:"]
    L += byte_lines(palette_bytes(d), ".byte")
    L += ["", "; tiles column by column (30 rows each), first column first", f"{nm}_columns:"]
    for x in range(ncols):
        L += byte_lines([nt.get(x, y) for y in range(30)], ".byte", 30)
    L += [f"{nm}_colptr_lo:", "    .lobytes " + ", ".join(f"{nm}_columns+{x * 30}" for x in range(ncols)),
          f"{nm}_colptr_hi:", "    .hibytes " + ", ".join(f"{nm}_columns+{x * 30}" for x in range(ncols)), ""]
    L += ["; attribute bytes per 32-pixel column group (8 rows each)", f"{nm}_attrcols:"]
    for g in range(ncols // 4):
        L += byte_lines([attribute_byte(at, g, ay) for ay in range(8)], ".byte", 8)
    L += [f"{nm}_attrptr_lo:", "    .lobytes " + ", ".join(f"{nm}_attrcols+{g * 8}" for g in range(ncols // 4)),
          f"{nm}_attrptr_hi:", "    .hibytes " + ", ".join(f"{nm}_attrcols+{g * 8}" for g in range(ncols // 4)), ""]
    L += ["; sprites (world x = xhi:xlo, OAM y = screen y - 1)"]
    for key, vals in (("xlo", [s[0] & 0xFF for s in spr]), ("xhi", [(s[0] >> 8) & 0xFF for s in spr]),
                      ("y", [(s[1] - 1) & 0xFF for s in spr]), ("tile", [s[2] for s in spr]),
                      ("attr", [s[3] for s in spr])):
        L.append(f"{nm}_spr_{key}:")
        L += byte_lines(vals, ".byte") if vals else ["    .byte 0"]
    L += ["", "; collision map: one byte per tile, row by row (screens*32 x 30)", f"{nm}_collision:"]
    for y in range(30):
        L += byte_lines([col.get(x, y) if col else 0 for x in range(ncols)], ".byte", 32)
    return "\n".join(L) + "\n"


def generate_main(d: Design) -> str:
    nm = ident(d.name)
    n = screens(d)
    ncols = 32 * n
    init_cols = min(64, ncols)
    mode = str(d.settings.get("scroll", "dpad"))
    speed = max(1, min(4, int(d.settings.get("speed", 1))))
    maxx = (n - 1) * 256
    scroll = n > 1 and mode != "none"
    T = f"""; {nm}_main.s - NROM program that shows the NES level '{d.name}'
; Generated by RAD IDE (NES Screen / Level Designer). Build:
;   ca65 {nm}_main.s -g -o {nm}_main.o
;   ld65 -C nrom.cfg {nm}_main.o -o {nm}.nes --dbgfile {nm}.dbg
; Re-generated when the design is saved - copy it before you change it.

PPUCTRL   = $2000
PPUMASK   = $2001
PPUSTATUS = $2002
OAMADDR   = $2003
PPUSCROLL = $2005
PPUADDR   = $2006
PPUDATA   = $2007
OAMDMA    = $4014
JOYPAD1   = $4016
CTRL_SPR  = $08                 ; sprites use the pattern table at $1000
CTRL_NMI  = $88                 ; + NMI at vblank
MAXX      = {maxx}
SPEED     = {speed}

.segment "HEADER"
    .byte "NES", $1A
    .byte 2                     ; 2 x 16K PRG
    .byte 1                     ; 1 x 8K CHR
    .byte $01                   ; vertical mirroring (name tables side by side), mapper 0
    .byte $00
    .res 8, 0

.segment "ZEROPAGE"
camx:     .res 2
ptr:      .res 2
tmp:      .res 2
sx:       .res 1
pad:      .res 1
frame:    .res 1
col_req:  .res 1
col_idx:  .res 1
ctrl:     .res 1

.segment "OAM"
oam:      .res 256

.segment "RODATA"
.include "{nm}_data.s"

.segment "CODE"
reset:
    sei
    cld
    ldx #$40
    stx $4017
    ldx #$FF
    txs
    inx
    stx PPUCTRL
    stx PPUMASK
    stx $4010
    bit PPUSTATUS
@vb1:
    bit PPUSTATUS
    bpl @vb1
    txa
@clr:
    sta $0000,x
    sta $0100,x
    sta $0300,x
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    inx
    bne @clr
    lda #$FF
@hide:
    sta oam,x
    inx
    bne @hide
@vb2:
    bit PPUSTATUS
    bpl @vb2
    lda #CTRL_SPR
    sta ctrl
    sta PPUCTRL
    ; palettes
    lda PPUSTATUS
    lda #$3F
    sta PPUADDR
    lda #$00
    sta PPUADDR
    ldx #0
@pal:
    lda {nm}_palette,x
    sta PPUDATA
    inx
    cpx #32
    bne @pal
    ; clear both name tables
    lda #$20
    sta PPUADDR
    lda #$00
    sta PPUADDR
    ldy #8
    ldx #0
@cnt:
    sta PPUDATA
    inx
    bne @cnt
    dey
    bne @cnt
    ; first {init_cols} columns
    ldx #0
@cols:
    stx col_idx
    jsr draw_column
    ldx col_idx
    inx
    cpx #{init_cols}
    bne @cols
    jsr update_sprites
@vb3:
    bit PPUSTATUS
    bpl @vb3
    lda #CTRL_NMI
    sta ctrl
    sta PPUCTRL
    lda #0
    sta PPUSCROLL
    sta PPUSCROLL
    lda #%00011110              ; background + sprites, also in the left 8 pixels
    sta PPUMASK

main:
    lda frame
@wait:
    cmp frame
    beq @wait
    jsr read_pad
    jsr move_camera
    jsr update_sprites
    jmp main

; ---------------------------------------------------------------- column streaming
draw_column:                    ; col_idx = level column (0..{ncols - 1})
    lda ctrl
    ora #$04                    ; PPU address +32 after each write: a vertical column
    sta PPUCTRL
    lda col_idx
    and #$20                    ; name table 0 or 1
    lsr
    lsr
    lsr
    ora #$20
    sta PPUADDR
    lda col_idx
    and #$1F
    sta PPUADDR
    ldx col_idx
    lda {nm}_colptr_lo,x
    sta ptr
    lda {nm}_colptr_hi,x
    sta ptr+1
    ldy #0
@tile:
    lda (ptr),y
    sta PPUDATA
    iny
    cpy #30
    bne @tile
    lda ctrl
    sta PPUCTRL                 ; back to +1
    lda col_idx
    lsr
    lsr
    tax                         ; attribute column group
    lda {nm}_attrptr_lo,x
    sta ptr
    lda {nm}_attrptr_hi,x
    sta ptr+1
    txa
    and #$08
    beq @nt0
    lda #$27
    bne @nthi
@nt0:
    lda #$23
@nthi:
    sta tmp
    txa
    and #$07
    ora #$C0
    sta tmp+1
    ldy #0
@attr:
    lda tmp
    sta PPUADDR
    lda tmp+1
    sta PPUADDR
    lda (ptr),y
    sta PPUDATA
    lda tmp+1
    clc
    adc #8
    sta tmp+1
    iny
    cpy #8
    bne @attr
    rts

; ---------------------------------------------------------------- input / camera / sprites
read_pad:                       ; pad: bit 7 A, 6 B, 5 Select, 4 Start, 3 Up, 2 Down, 1 Left, 0 Right
    lda #1
    sta JOYPAD1
    lda #0
    sta JOYPAD1
    ldx #8
@bit:
    lda JOYPAD1
    lsr
    rol pad
    dex
    bne @bit
    rts

cam_column:                     ; A = (camx >> 3) & $FF
    lda camx+1
    sta tmp
    lda camx
    lsr tmp
    ror
    lsr tmp
    ror
    lsr tmp
    ror
    rts

"""
    if not scroll:
        T += "move_camera:\n    rts\n\n"
    else:
        right_test = "    jmp @right\n" if mode == "auto" else "    lda pad\n    and #$01\n    beq @left\n"
        cmp_ncols = "" if ncols >= 256 else f"    cmp #{ncols}\n    bcs @done\n"
        T += f"""move_camera:
    ldx #SPEED
@step:
    txa
    pha
    jsr camera_step
    pla
    tax
    dex
    bne @step
    rts

camera_step:
{right_test}@right:
    lda camx+1                  ; at the right end?
    cmp #>MAXX
    bcc @inc
    bne @done
    lda camx
    cmp #<MAXX
    bcs @done
@inc:
    lda camx
    clc
    adc #1
    sta camx
    lda camx+1
    adc #0
    sta camx+1
    lda camx
    and #7
    bne @done
    jsr cam_column
    clc
    adc #32                     ; the column entering on the right
    bcs @done
{cmp_ncols}    sta col_idx
    lda #1
    sta col_req
    rts
@left:
    lda pad
    and #$02
    beq @done
    lda camx
    ora camx+1
    beq @done
    lda camx
    sec
    sbc #1
    sta camx
    lda camx+1
    sbc #0
    sta camx+1
    lda camx
    and #7
    cmp #7
    bne @done
    jsr cam_column              ; the column entering on the left
    sta col_idx
    lda #1
    sta col_req
@done:
    rts

"""
    T += f"""update_sprites:                 ; world x - camera x; hidden when off screen
    ldx #0
    ldy #0
@spr:
    cpx #{nm}_NSPR
    beq @rest
    lda {nm}_spr_xlo,x
    sec
    sbc camx
    sta sx
    lda {nm}_spr_xhi,x
    sbc camx+1
    bne @off
    lda {nm}_spr_y,x
    sta oam,y
    lda {nm}_spr_tile,x
    sta oam+1,y
    lda {nm}_spr_attr,x
    sta oam+2,y
    lda sx
    sta oam+3,y
    jmp @next
@off:
    lda #$FF
    sta oam,y
@next:
    iny
    iny
    iny
    iny
    inx
    bne @spr
@rest:
    rts

; ---------------------------------------------------------------- interrupts
nmi:
    pha
    txa
    pha
    tya
    pha
    lda #0
    sta OAMADDR
    lda #>oam
    sta OAMDMA
    lda col_req
    beq @nocol
    jsr draw_column
    lda #0
    sta col_req
@nocol:
    lda camx+1
    and #1
    ora #CTRL_NMI
    sta PPUCTRL
    lda camx
    sta PPUSCROLL
    lda #0
    sta PPUSCROLL
    inc frame
    pla
    tay
    pla
    tax
    pla
irq:
    rti

.segment "VECTORS"
    .addr nmi, reset, irq

.segment "CHARS"
    .incbin "{nm}.chr"
"""
    return T


def generate(d: Design, outdir) -> dict:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    nm = ident(d.name)
    warnings = []
    if len(hw_sprites(d)) > MAX_SPRITES:
        warnings.append(f"{len(hw_sprites(d))} hardware sprites - only the first {MAX_SPRITES} are generated")
    files = []
    for fname, data in ((f"{nm}_main.s", generate_main(d)), (f"{nm}_data.s", generate_data(d)),
                        ("nrom.cfg", NROM_CFG)):
        p = out / fname
        p.write_text(data, encoding="utf-8")
        files.append(p)
    chrp = out / f"{nm}.chr"
    chrp.write_bytes(chr_bytes(d))
    files.append(chrp)
    return {"main": files[0], "files": files, "warnings": warnings, "rom": out / f"{nm}.nes", "system": SYSTEM}


def build_commands(d: Design, outdir, find) -> list[tuple[list[str], str]]:
    nm = ident(d.name)
    ca65, ld65 = find("ca65"), find("ld65")
    if not ca65:
        raise FileNotFoundError("ca65")
    if not ld65:
        raise FileNotFoundError("ld65")
    return [([ca65, f"{nm}_main.s", "-g", "-o", f"{nm}_main.o"], str(outdir)),
            ([ld65, "-C", "nrom.cfg", f"{nm}_main.o", "-o", f"{nm}.nes", "--dbgfile", f"{nm}.dbg"], str(outdir))]
