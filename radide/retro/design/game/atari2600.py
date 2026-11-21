"""Atari 2600 Screen Designer: data model, TIA preview and the DASM kernel generator (pure Python).

The screen is a column of scan lines (192 NTSC / 228 PAL). Every line has its own playfield (20 bits for the
left half; the right half repeats it or mirrors it - CTRLPF REF), background colour (COLUBK) and playfield
colour (COLUPF). Player 0 / 1 (8-pixel sprites with NUSIZ copies / stretch and REFP reflect), missile 0 / 1
and the ball are placed objects.

Generated program (one-line kernel, every value comes from a full-height table indexed by the line)::

    KernelLoop  lda BKT-1,y / ldx PFCT-1,y / sta WSYNC          ; values for this line are ready
                sta COLUBK (3) stx COLUPF (6) PF0 (13) PF1 (20) PF2 (27)
                GRP0 (34) GRP1 (41) ENAM0 (48) ENAM1 (53) ENABL (58)  ; CPU cycle at which each store lands
                dey / bne KernelLoop                              ; 63 + 11 = 74 of 76 cycles

The tables sit one byte into a 256-byte page, so ``TABLE-1,y`` never crosses a page (4-cycle loads) and the
loop itself lives in one page (3-cycle branch). All playfield writes land before the beam reaches them
(PF1 is read from cycle 28, PF2 from cycle 38.7). A player / missile / ball that lies completely left of the
pixel where its register is written (GRP0 34, GRP1 55, ENAM0 76, ENAM1 91, ENABL 106) would show the previous
line's value, so its table is generated one line early ("early" objects, see :func:`kernel_tables`); an object
that straddles that pixel gets a warning instead.

Frame: 3 VSYNC + 37 VBLANK + 192 kernel + 30 overscan = 262 lines (PAL 3 + 45 + 228 + 36 = 312); VBLANK and
overscan are timed with the RIOT timer (TIM64T), so object positioning may take one or two lines each.
"""
from __future__ import annotations

from pathlib import Path

from .compat import half_to_bytes, system_palette
from .model import Design, Layer, byte_lines, ident

SYSTEM = "a2600"
EXT = ".a26scr"
TITLE = "Atari 2600 Screen"
TV = {"NTSC": {"lines": 192, "vblank": 37, "overscan": 30, "total": 262, "palette": "a2600ntsc"},
      "PAL": {"lines": 228, "vblank": 45, "overscan": 36, "total": 312, "palette": "a2600pal"}}
WIDTH = 160                                   # colour clocks of the visible line
PF_PIXEL = 4                                  # one playfield bit = 4 colour clocks
NUSIZ_COPIES = {0: ([0], 1), 1: ([0, 16], 1), 2: ([0, 32], 1), 3: ([0, 16, 32], 1), 4: ([0, 64], 1),
                5: ([0], 2), 6: ([0, 32, 64], 1), 7: ([0], 4)}
NUSIZ_NAMES = ["one copy", "two copies - close", "two copies - medium", "three copies - close",
               "two copies - wide", "double size", "three copies - medium", "quad size"]
# pixel at which the kernel's store for the object lands (cycle * 3 - 68)
WRITE_PIXEL = {"player0": 34, "player1": 55, "missile0": 76, "missile1": 91, "ball": 106}
OBJECT_KINDS = ("player0", "player1", "missile0", "missile1", "ball")

REGS = [("VSYNC", 0x00), ("VBLANK", 0x01), ("WSYNC", 0x02), ("NUSIZ0", 0x04), ("NUSIZ1", 0x05), ("COLUP0", 0x06),
        ("COLUP1", 0x07), ("COLUPF", 0x08), ("COLUBK", 0x09), ("CTRLPF", 0x0A), ("REFP0", 0x0B), ("REFP1", 0x0C),
        ("PF0", 0x0D), ("PF1", 0x0E), ("PF2", 0x0F), ("RESP0", 0x10), ("RESP1", 0x11), ("RESM0", 0x12),
        ("RESM1", 0x13), ("RESBL", 0x14), ("GRP0", 0x1B), ("GRP1", 0x1C), ("ENAM0", 0x1D), ("ENAM1", 0x1E),
        ("ENABL", 0x1F), ("HMP0", 0x20), ("HMP1", 0x21), ("HMM0", 0x22), ("HMM1", 0x23), ("HMBL", 0x24),
        ("HMOVE", 0x2A), ("HMCLR", 0x2B), ("CXCLR", 0x2C)]

# Properties grid schema: key -> (type, extra). Types: int (min, max), bool, choice (list), color, sprite.
SETTINGS_SCHEMA = {"tv": ("choice", ["NTSC", "PAL"]), "reflect": ("bool", None), "score": ("bool", None),
                   "priority": ("bool", None), "ball_size": ("choice", ["1", "2", "4", "8"])}
OBJECT_SCHEMA = {
    "player": {"x": ("int", (0, 159)), "y": ("int", (0, 227)), "sprite": ("sprite", None), "color": ("color", None),
               "nusiz": ("choice", NUSIZ_NAMES), "reflect": ("bool", None), "enabled": ("bool", None)},
    "missile": {"x": ("int", (0, 159)), "y": ("int", (0, 227)), "height": ("int", (0, 228)),
                "size": ("choice", ["1", "2", "4", "8"]), "enabled": ("bool", None)},
    "ball": {"x": ("int", (0, 159)), "y": ("int", (0, 227)), "height": ("int", (0, 228)), "enabled": ("bool", None)},
}


def schema_for(obj: dict) -> dict:
    k = obj.get("kind", "")
    return OBJECT_SCHEMA["player" if k.startswith("player") else "missile" if k.startswith("missile") else "ball"]


# ------------------------------------------------------------------ new document
def _sprite(rows: list[str]) -> dict:
    px = bytearray(1 if ch == "X" else 0 for r in rows for ch in r.ljust(8)[:8])
    return {"w": 8, "h": len(rows), "pixels": px}


HERO = ["...XX...", "...XX...", "..XXXX..", ".X.XX.X.", "X..XX..X", "...XX...", "..X..X..", ".X....X."]
SHIP = ["...XX...", "..XXXX..", ".XXXXXX.", "XX.XX.XX", "XXXXXXXX", "..X..X..", ".X.XX.X.", "X.X..X.X"]


def new_design(name: str = "Screen1", tv: str = "NTSC") -> Design:
    tv = tv if tv in TV else "NTSC"
    h = TV[tv]["lines"]
    d = Design(SYSTEM, name, {"tv": tv, "reflect": True, "score": False, "priority": False, "ball_size": "1"})
    # colours everywhere are 2600 palette indices 0..127 (COLUxx >> 1)
    d.palette = []                                   # colours are 2600 palette indices (0..127) in the layers
    d.sprites = {"Hero": _sprite(HERO), "Ship": _sprite(SHIP)}
    pf = Layer("Playfield", "playfield", 20, h, PF_PIXEL, 1)
    bk = Layer("Background colour", "linecolor", 1, h, WIDTH, 1)
    pfc = Layer("Playfield colour", "linecolor", 1, h, WIDTH, 1)
    col = Layer("Collision", "collision", 40, h, PF_PIXEL, 1)
    for y in range(h):                               # a framed screen with a ground band to start from
        for x in range(20):
            edge = y < 8 or y >= h - 8 or x == 0
            pf.data[y * 20 + x] = 1 if edge else 0
        bk.data[y] = 0x60 if y < h * 2 // 3 else 0x63    # dark blue sky, then a lighter band
        pfc.data[y] = 0x1A if y >= h - 8 else 0x22       # orange ground, green frame
    d.layers = [bk, pf, pfc, col]
    d.objects = [
        {"name": "Player0", "kind": "player0", "x": 40, "y": h // 2, "sprite": "Hero", "color": 0x0E,
         "nusiz": 0, "reflect": False, "enabled": True},
        {"name": "Player1", "kind": "player1", "x": 110, "y": h // 2 - 20, "sprite": "Ship", "color": 0x23,
         "nusiz": 0, "reflect": False, "enabled": True},
        {"name": "Missile0", "kind": "missile0", "x": 60, "y": h // 2 + 2, "height": 2, "size": 1, "enabled": False},
        {"name": "Missile1", "kind": "missile1", "x": 100, "y": h // 2 - 16, "height": 2, "size": 1,
         "enabled": False},
        {"name": "Ball", "kind": "ball", "x": 80, "y": 30, "height": 4, "enabled": True},
    ]
    return d


def set_tv(d: Design, tv: str) -> None:
    """Switch NTSC / PAL: the scan-line layers grow or shrink."""
    tv = tv if tv in TV else "NTSC"
    d.settings["tv"] = tv
    h = TV[tv]["lines"]
    for lay in d.layers:
        if lay.h != h:
            lay.resize(lay.w, h)


def lines(d: Design) -> int:
    return TV.get(d.settings.get("tv", "NTSC"), TV["NTSC"])["lines"]


def palette_rgb(d: Design) -> list:
    return system_palette(TV.get(d.settings.get("tv", "NTSC"), TV["NTSC"])["palette"])


def color_byte(index: int) -> int:
    """Palette index (0..127) -> COLUxx value (hue in the high nibble, luminance in bits 1-3)."""
    return (int(index) & 0x7F) << 1


# ------------------------------------------------------------------ encoding
def pf_bits(d: Design, y: int) -> list[int]:
    lay = d.layer("playfield")
    return [1 if lay.get(x, y) else 0 for x in range(20)] if lay else [0] * 20


def full_row(bits20: list[int], reflect: bool) -> list[int]:
    return list(bits20) + (list(bits20[::-1]) if reflect else list(bits20))


def edit_index(x40: int, reflect: bool) -> int:
    """Playfield column (0..39 on screen) -> stored left-half bit (0..19)."""
    if x40 < 20:
        return x40
    return 39 - x40 if reflect else x40 - 20


def ctrlpf(d: Design) -> int:
    s = d.settings
    size = size_index(s.get("ball_size", 0))
    return (1 if s.get("reflect", True) else 0) | (2 if s.get("score") else 0) | (4 if s.get("priority") else 0) \
        | (size << 4)


def _obj(d: Design, kind: str) -> dict:
    return next((o for o in d.objects if o.get("kind") == kind), {"kind": kind, "enabled": False})


def _sprite_rows(d: Design, obj: dict) -> list[int]:
    spr = d.sprites.get(obj.get("sprite", ""))
    if not spr:
        return []
    w, h, px = spr["w"], spr["h"], spr["pixels"]
    out = []
    for r in range(h):
        b = 0
        for i in range(min(8, w)):
            if px[r * w + i]:
                b |= 0x80 >> i
        out.append(b)
    return out


def size_index(v) -> int:
    """A size property (index 0..3, or the text "1" / "2" / "4" / "8") -> 0..3."""
    if isinstance(v, str):
        return {"1": 0, "2": 1, "4": 2, "8": 3}.get(v.strip(), 0)
    try:
        return max(0, min(3, int(v)))
    except (TypeError, ValueError):
        return 0


def _missile_size(obj: dict) -> int:
    return size_index(obj.get("size", 0))


def nusiz(d: Design, n: int) -> int:
    p, m = _obj(d, f"player{n}"), _obj(d, f"missile{n}")
    return (int(p.get("nusiz", 0)) & 7) | (_missile_size(m) << 4)


def object_extent(d: Design, obj: dict) -> tuple[int, int]:
    """(first pixel, pixel after the last) an object covers on a line (copies included, no wrap)."""
    k = obj.get("kind", "")
    x = int(obj.get("x", 0)) % WIDTH
    if k.startswith("player"):
        offs, stretch = NUSIZ_COPIES[int(obj.get("nusiz", 0)) & 7]
        return x, x + max(offs) + 8 * stretch
    if k.startswith("missile"):
        n = int(k[-1])
        offs, stretch = NUSIZ_COPIES[int(_obj(d, f"player{n}").get("nusiz", 0)) & 7]
        offs = offs if stretch == 1 else [0]
        return x, x + max(offs) + (1 << _missile_size(obj))
    return x, x + (1 << size_index(d.settings.get("ball_size", 0)))


def _vertical(obj: dict, h_lines: int, rows: list[int] | None = None) -> list[int]:
    """Per kernel line value of an object (sprite row byte, or 1/0 for missiles / ball)."""
    out = [0] * h_lines
    if not obj.get("enabled", True):
        return out
    y0 = int(obj.get("y", 0))
    if rows is None:
        rows = [1] * max(0, int(obj.get("height", 1)))
    for r, v in enumerate(rows):
        if 0 <= y0 + r < h_lines:
            out[y0 + r] = v
    return out


def kernel_tables(d: Design) -> dict:
    """Everything the kernel reads, top line first: {"BKT", "PFCT", "PF0T", "PF1T", "PF2T", "G0T", "G1T", "ENT"}
    (lists of *lines* bytes) plus "pre" (GRP0, GRP1, EN values written before the first line), "early"
    (object kinds generated one line ahead) and "warnings"."""
    h = lines(d)
    bk, pfc = d.layer("Background colour"), d.layer("Playfield colour")
    t = {k: [0] * h for k in ("BKT", "PFCT", "PF0T", "PF1T", "PF2T", "G0T", "G1T", "ENT")}
    for y in range(h):
        t["BKT"][y] = color_byte(bk.get(0, y) if bk else 0)
        t["PFCT"][y] = color_byte(pfc.get(0, y) if pfc else 0)
        t["PF0T"][y], t["PF1T"][y], t["PF2T"][y] = half_to_bytes(pf_bits(d, y))
    pre = {"G0": 0, "G1": 0, "EN": 0}
    early, warnings = [], []

    def place(kind: str, values: list[int], table: str, shift_bits: int, pre_key: str):
        obj = _obj(d, kind)
        x0, x1 = object_extent(d, obj)
        p = WRITE_PIXEL[kind]
        is_early = x1 <= p - 1 and any(values)
        if not is_early and x0 < p + 1 and x1 > p - 1 and any(values):
            warnings.append(f"{obj.get('name', kind)}: x {x0}-{x1 - 1} crosses pixel {p} where the kernel writes "
                            f"its register - its rows may be torn; move it left of {max(0, p - (x1 - x0) - 1)} "
                            f"or right of {p}")
        if is_early:
            early.append(kind)
            pre[pre_key] |= values[0] << shift_bits
            values = values[1:] + [0]
        for y in range(h):
            t[table][y] |= values[y] << shift_bits

    for n in (0, 1):
        obj = _obj(d, f"player{n}")
        place(f"player{n}", _vertical(obj, h, _sprite_rows(d, obj)), f"G{n}T", 0, f"G{n}")
    for kind, bit in (("missile0", 1), ("missile1", 2), ("ball", 3)):
        place(kind, _vertical(_obj(d, kind), h), "ENT", bit, "EN")
    t["pre"], t["early"], t["warnings"] = pre, early, warnings
    return t


# ------------------------------------------------------------------ preview
def render_indexed(d: Design, visible: set | None = None) -> tuple[int, int, bytearray, list]:
    """(160, lines, palette index per pixel, RGB palette) - what the TIA shows (objects at their x / y)."""
    h = lines(d)
    vis = (lambda name: True) if visible is None else (lambda name: name in visible)
    bk, pfc = d.layer("Background colour"), d.layer("Playfield colour")
    reflect = bool(d.settings.get("reflect", True))
    score = bool(d.settings.get("score"))
    prio = bool(d.settings.get("priority"))
    p0, p1 = _obj(d, "player0"), _obj(d, "player1")
    c0, c1 = int(p0.get("color", 0x0E)) & 0x7F, int(p1.get("color", 0x23)) & 0x7F
    buf = bytearray(WIDTH * h)
    show_objects = vis("Objects")
    rows = {n: _vertical(_obj(d, f"player{n}"), h, _sprite_rows(d, _obj(d, f"player{n}"))) for n in (0, 1)}
    ens = {k: _vertical(_obj(d, k), h) for k in ("missile0", "missile1", "ball")}

    def spans_player(n: int, byte: int) -> list[tuple[int, int]]:
        obj = _obj(d, f"player{n}")
        offs, s = NUSIZ_COPIES[int(obj.get("nusiz", 0)) & 7]
        x = int(obj.get("x", 0))
        out = []
        for off in offs:
            for j in range(8):
                bit = (byte >> j) & 1 if obj.get("reflect") else (byte >> (7 - j)) & 1
                if bit:
                    out.append((x + off + j * s, s))
        return out

    def spans_simple(kind: str) -> list[tuple[int, int]]:
        obj = _obj(d, kind)
        x0, x1 = object_extent(d, obj)
        if kind.startswith("missile"):
            n = int(kind[-1])
            offs, stretch = NUSIZ_COPIES[int(_obj(d, f"player{n}").get("nusiz", 0)) & 7]
            offs = offs if stretch == 1 else [0]
            w = 1 << _missile_size(obj)
            return [(x0 + o, w) for o in offs]
        return [(x0, x1 - x0)]

    for y in range(h):
        line = bytearray([bk.get(0, y) if (bk and vis(bk.name)) else 0]) * WIDTH
        pf_layer = []
        if vis("Playfield"):
            bits = full_row(pf_bits(d, y), reflect)
            pc = pfc.get(0, y) if (pfc and vis(pfc.name)) else 0x07
            for i, b in enumerate(bits):
                if b:
                    col = (c0 if i < 20 else c1) if score else pc
                    pf_layer.append((i * PF_PIXEL, PF_PIXEL, col))
        if show_objects and ens["ball"][y]:
            pc = pfc.get(0, y) if pfc else 0x07
            pf_layer += [(x, w, pc) for x, w in spans_simple("ball")]
        players = []
        if show_objects:
            for n, col in ((1, c1), (0, c0)):                # P1 first: P0 wins (drawn later)
                if rows[n][y]:
                    players += [(x, w, col) for x, w in spans_player(n, rows[n][y])]
                if ens[f"missile{n}"][y]:
                    players += [(x, w, col) for x, w in spans_simple(f"missile{n}")]
        for layer_spans in ((players, pf_layer) if prio else (pf_layer, players)):
            for x, w, col in layer_spans:
                for px in range(x, x + w):
                    line[px % WIDTH] = col
        buf[y * WIDTH:(y + 1) * WIDTH] = line
    return WIDTH, h, buf, palette_rgb(d)


# ------------------------------------------------------------------ code generation
def _table_block(label: str, values: list[int]) -> list[str]:
    """A kernel table: page aligned + 1 so that LABEL-1,y (y = lines..1) stays inside the page; stored bottom
    line first because the kernel counts y down."""
    return ["    ALIGN 256", "    .byte 0", label] + byte_lines(list(reversed(values)), ".byte")


def generate_data(d: Design, tables: dict | None = None) -> str:
    t = tables or kernel_tables(d)
    nm = ident(d.name)
    out = [f"; {nm}_data.asm - kernel tables of the Atari 2600 screen '{d.name}'",
           "; Generated by RAD IDE (Atari 2600 Screen Designer). Re-generated when the design is saved.",
           "; Each table has one byte per scan line, stored bottom line first, one byte into a page.", ""]
    names = {"BKT": "background colour (COLUBK)", "PFCT": "playfield colour (COLUPF)", "PF0T": "PF0",
             "PF1T": "PF1", "PF2T": "PF2", "G0T": "player 0 graphics (GRP0)", "G1T": "player 1 graphics (GRP1)",
             "ENT": "bit 1 ENAM0, bit 2 ENAM1, bit 3 ENABL"}
    for key, what in names.items():
        out.append(f"; {what}")
        out += _table_block(key, t[key])
        out.append("")
    return "\n".join(out) + "\n"


def generate_collision(d: Design) -> str:
    """The collision layer as 5 bytes per line (40 playfield-sized cells, bit 7 of byte 0 = leftmost)."""
    lay = d.layer("collision")
    nm = ident(d.name)
    h = lines(d)
    data = []
    for y in range(h):
        for b in range(5):
            v = 0
            for i in range(8):
                if lay and lay.get(b * 8 + i, y):
                    v |= 0x80 >> i
            data.append(v)
    out = [f"; {nm}_collision.asm - collision map of '{d.name}': 5 bytes per scan line, top line first",
           "; (40 cells of 4 colour clocks; bit 7 of the first byte is the leftmost cell). Not included by the",
           "; generated kernel: include it in your own game code when you need it.", f"{nm}_Collision"]
    return "\n".join(out + byte_lines(data, ".byte", 20)) + "\n"


def timer_plan(cycles: int) -> tuple[int, int]:
    """(pad cycles, TIM64T value) so that the timer runs out *cycles* after the point where the padding starts."""
    v, pad = divmod(max(0, cycles), 64)
    if pad == 1:
        v, pad = v - 1, 65
    return pad, v


def timer_vblank(tv: dict) -> tuple[int, int]:
    """TIM64T lands at cycle 11 + pad of line 3; it must run out at cycle ~29 of line 3 + (VBLANK - 2), so the
    WSYNC after the INTIM loop (5-12 cycles later) ends the last-but-one VBLANK line near its middle."""
    return timer_plan((tv["vblank"] - 2) * 76 + 18)


def timer_overscan(tv: dict) -> tuple[int, int]:
    """TIM64T lands at cycle 37 + pad of the first overscan line; runs out at cycle ~29 of the last one."""
    return timer_plan((tv["overscan"] - 1) * 76 - 8)


def _delay(cycles: int) -> list[str]:
    out = []
    if cycles % 2:
        out.append("    bit $80                 ; 3-cycle delay")
        cycles -= 3
    out += ["    nop"] * (cycles // 2)
    return out


def generate_main(d: Design, tables: dict | None = None) -> str:
    t = tables or kernel_tables(d)
    tv = TV.get(d.settings.get("tv", "NTSC"), TV["NTSC"])
    nm = ident(d.name)
    p0, p1 = _obj(d, "player0"), _obj(d, "player1")
    xs = [int(_obj(d, k).get("x", 0)) % WIDTH for k in OBJECT_KINDS]
    L = []
    a = L.append
    a(f"; {nm}.asm - Atari 2600 screen '{d.name}' ({d.settings.get('tv', 'NTSC')}, {tv['lines']} lines)")
    a("; Generated by RAD IDE (Atari 2600 Screen Designer). Build: dasm " + f"{nm}.asm -f3 -o{nm}.bin")
    a("; Re-generated when the design is saved - put your own code in another file.")
    for w in t["warnings"]:
        a(f"; WARNING: {w}")
    a("")
    a("    processor 6502")
    a("")
    for n, v in REGS:
        a(f"{n:<8}= ${v:02X}")
    a("")
    a("INTIM   = $0284")
    a("TIM64T  = $0296")
    a(f"LINES   = {tv['lines']}")
    a("")
    a("    seg code")
    a("    org $F000")
    a("")
    a("Reset")
    a("    sei")
    a("    cld")
    a("    ldx #0")
    a("    txa")
    a("ClearMem")
    a("    dex")
    a("    txs")
    a("    pha")
    a("    bne ClearMem")
    a("")
    a("Frame")
    a("    lda #2")
    a("    sta VBLANK")
    a("    sta VSYNC")
    a("    sta WSYNC")
    a("    sta WSYNC")
    a("    sta WSYNC")
    a("    lda #0")
    a("    sta VSYNC")
    pad, v = timer_vblank(tv)
    L.extend(_delay(pad))
    a(f"    lda #{v}            ; VBLANK length is timed by the RIOT timer")
    a("    sta TIM64T")
    regs = [("CTRLPF", ctrlpf(d)), ("NUSIZ0", nusiz(d, 0)), ("NUSIZ1", nusiz(d, 1)),
            ("REFP0", 8 if p0.get("reflect") else 0), ("REFP1", 8 if p1.get("reflect") else 0),
            ("COLUP0", color_byte(p0.get("color", 0x0E))), ("COLUP1", color_byte(p1.get("color", 0x23)))]
    for reg, v in regs:
        a(f"    lda #${v:02X}")
        a(f"    sta {reg}")
    a("; horizontal positions (one or two lines each), then HMOVE")
    for i, (kind, x) in enumerate(zip(OBJECT_KINDS, xs)):
        a(f"    lda #{x}                ; {kind}")
        a(f"    ldx #{i}")
        a("    jsr PosObject")
    a("    sta WSYNC")
    a("    sta HMOVE")
    a("WaitVBlank")
    a("    lda INTIM")
    a("    bne WaitVBlank")
    a("    sta WSYNC")
    a("; last VBLANK line: clear, preload the objects drawn left of their register write, beam on")
    a("    lda #0")
    for reg in ("COLUBK", "PF0", "PF1", "PF2"):
        a(f"    sta {reg}")
    a(f"    lda #${t['pre']['G0']:02X}")
    a("    sta GRP0")
    a(f"    lda #${t['pre']['G1']:02X}")
    a("    sta GRP1")
    a(f"    lda #${t['pre']['EN']:02X}")
    a("    sta ENAM0")
    a("    lsr")
    a("    sta ENAM1")
    a("    lsr")
    a("    sta ENABL")
    a("    lda #0")
    a("    sta VBLANK")
    a("    ldy #LINES")
    a("    jmp KernelLoop")
    a("")
    a("PosObject                   ; A = x (0..159), X = 0 P0, 1 P1, 2 M0, 3 M1, 4 BL")
    a("    sta WSYNC")
    a("    sec")
    a("PosDivide")
    a("    sbc #15")
    a("    bcs PosDivide")
    a("    eor #7")
    a("    asl")
    a("    asl")
    a("    asl")
    a("    asl")
    a("    sta HMP0,x")
    a("    sta RESP0,x")
    a("    rts")
    a("")
    a("    ALIGN 256")
    a("KernelLoop")
    a("    lda BKT-1,y")
    a("    ldx PFCT-1,y")
    a("    sta WSYNC")
    a("    sta COLUBK")
    a("    stx COLUPF")
    for tab, reg in (("PF0T", "PF0"), ("PF1T", "PF1"), ("PF2T", "PF2"), ("G0T", "GRP0"), ("G1T", "GRP1")):
        a(f"    lda {tab}-1,y")
        a(f"    sta {reg}")
    a("    lda ENT-1,y")
    a("    sta ENAM0")
    a("    lsr")
    a("    sta ENAM1")
    a("    lsr")
    a("    sta ENABL")
    a("    dey")
    a("    bne KernelLoop")
    a("    sta WSYNC")
    a("    lda #2")
    a("    sta VBLANK")
    a("    lda #0")
    for reg in ("PF0", "PF1", "PF2", "GRP0", "GRP1", "ENAM0", "ENAM1", "ENABL"):
        a(f"    sta {reg}")
    pad, v = timer_overscan(tv)
    L.extend(_delay(pad))
    a(f"    lda #{v}            ; overscan length is timed by the RIOT timer")
    a("    sta TIM64T")
    a("WaitOverscan")
    a("    lda INTIM")
    a("    bne WaitOverscan")
    a("    sta WSYNC")
    a("    jmp Frame")
    a("")
    a(f'    include "{nm}_data.asm"')
    a("")
    a("    org $FFFC")
    a("    .word Reset")
    a("    .word Reset")
    return "\n".join(L) + "\n"


def generate(d: Design, outdir) -> dict:
    """Write the DASM program into *outdir*. Returns {"main": path, "files": [...], "warnings": [...],
    "rom": expected ROM path, "system": "a2600"}."""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    nm = ident(d.name)
    t = kernel_tables(d)
    files = []
    for fname, text in ((f"{nm}.asm", generate_main(d, t)), (f"{nm}_data.asm", generate_data(d, t)),
                        (f"{nm}_collision.asm", generate_collision(d))):
        p = out / fname
        p.write_text(text, encoding="utf-8")
        files.append(p)
    return {"main": files[0], "files": files, "warnings": t["warnings"], "rom": out / f"{nm}.bin",
            "system": SYSTEM}


def build_commands(d: Design, outdir, find) -> list[tuple[list[str], str]]:
    """[(argv, cwd)] that build the ROM; *find* maps an executable name to its path ("" = missing)."""
    nm = ident(d.name)
    dasm = find("dasm")
    if not dasm:
        raise FileNotFoundError("dasm")
    return [([dasm, f"{nm}.asm", "-f3", f"-o{nm}.bin", f"-s{nm}.sym", f"-l{nm}.lst"], str(outdir))]
