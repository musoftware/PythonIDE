"""Code page 437 (the IBM PC / DOS character set) and the 16 text-mode colours. No Qt in here.

* ``to_unicode(b)`` / ``from_unicode(ch)``: the glyph of every byte 0..255 (0x01..0x1F and 0x7F are the
  PC's symbols - smileys, arrows, card suits - not control characters).
* ``BOX`` describes the line-drawing characters as (up, down, left, right) weights (0 none, 1 single,
  2 double) so the renderer can draw them pixel-exact and the editors can join lines automatically.
* ``COLORS``: the CGA / EGA / VGA text palette (index -> (name, RGB)).
"""
from __future__ import annotations

# 0x00..0x1F and 0x7F: the symbol glyphs of the PC character ROM
_LOW = (" ☺☻♥♦♣♠•◘○◙♂♀♪♫☼"
        "►◄↕‼¶§▬↨↑↓→←∟↔▲▼")

TABLE: list[str] = list(_LOW) + [chr(i) for i in range(0x20, 0x7F)] + ["⌂"] + \
    list(bytes(range(0x80, 0x100)).decode("cp437"))
TABLE[0xFF] = " "
_REV: dict[str, int] = {}
for _i, _c in enumerate(TABLE):
    _REV.setdefault(_c, _i)
_REV[" "] = 0x20
# common look-alikes typed on a modern keyboard
_REV.update({"│": 0xB3, "─": 0xC4, "·": 0xFA, "■": 0xFE, "█": 0xDB, "\t": 0x20,
             "’": 0x27, "‘": 0x27, "“": 0x22, "”": 0x22, "–": 0x2D, "—": 0xC4})


def to_unicode(b: int) -> str:
    return TABLE[b & 0xFF]


def from_unicode(ch: str, default: int = 0x3F) -> int:
    """CP437 byte of *ch* (*default* = '?' when the character has no CP437 glyph)."""
    if not ch:
        return 0x20
    v = _REV.get(ch[0])
    if v is not None:
        return v
    try:
        return ch[0].encode("cp437")[0]
    except (UnicodeEncodeError, IndexError):
        return default


def encode(text: str) -> bytes:
    return bytes(from_unicode(c) for c in text)


def decode(data: bytes) -> str:
    return "".join(TABLE[b] for b in data)


# --------------------------------------------------------------- line drawing: (up, down, left, right)
BOX: dict[int, tuple[int, int, int, int]] = {
    0xB3: (1, 1, 0, 0), 0xB4: (1, 1, 1, 0), 0xB5: (1, 1, 2, 0), 0xB6: (2, 2, 1, 0), 0xB7: (0, 2, 1, 0),
    0xB8: (0, 1, 2, 0), 0xB9: (2, 2, 2, 0), 0xBA: (2, 2, 0, 0), 0xBB: (0, 2, 2, 0), 0xBC: (2, 0, 2, 0),
    0xBD: (2, 0, 1, 0), 0xBE: (1, 0, 2, 0), 0xBF: (0, 1, 1, 0), 0xC0: (1, 0, 0, 1), 0xC1: (1, 0, 1, 1),
    0xC2: (0, 1, 1, 1), 0xC3: (1, 1, 0, 1), 0xC4: (0, 0, 1, 1), 0xC5: (1, 1, 1, 1), 0xC6: (1, 1, 0, 2),
    0xC7: (2, 2, 0, 1), 0xC8: (2, 0, 0, 2), 0xC9: (0, 2, 0, 2), 0xCA: (2, 0, 2, 2), 0xCB: (0, 2, 2, 2),
    0xCC: (2, 2, 0, 2), 0xCD: (0, 0, 2, 2), 0xCE: (2, 2, 2, 2), 0xCF: (1, 0, 2, 2), 0xD0: (2, 0, 1, 1),
    0xD1: (0, 1, 2, 2), 0xD2: (0, 2, 1, 1), 0xD3: (2, 0, 0, 1), 0xD4: (1, 0, 0, 2), 0xD5: (0, 1, 0, 2),
    0xD6: (0, 2, 0, 1), 0xD7: (2, 2, 1, 1), 0xD8: (1, 1, 2, 2), 0xD9: (1, 0, 1, 0), 0xDA: (0, 1, 0, 1),
}
BOX_REV: dict[tuple[int, int, int, int], int] = {v: k for k, v in BOX.items()}


def box_char(up: int, down: int, left: int, right: int) -> int:
    """The line-drawing character with these arm weights (closest match when CP437 has no exact one)."""
    key = (up, down, left, right)
    if key in BOX_REV:
        return BOX_REV[key]
    if up == down == 0 and (left or right):
        return 0xCD if max(left, right) == 2 else 0xC4
    if left == right == 0 and (up or down):
        return 0xBA if max(up, down) == 2 else 0xB3
    # mixed weights CP437 lacks (e.g. single up + double down): use the heavier weight for the axis
    v = max(up, down)
    h = max(left, right)
    key = (v if up else 0, v if down else 0, h if left else 0, h if right else 0)
    return BOX_REV.get(key, 0xC5 if v < 2 and h < 2 else 0xCE)


BLOCKS = {0xB0, 0xB1, 0xB2, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF, 0xFE}

# border styles of windows / frames / list boxes: (top-left, top, top-right, side, bottom-left, bottom-right)
BORDERS: dict[str, tuple[int, int, int, int, int, int, int]] = {
    #          tl    top   tr    left  right bl    br  (bottom uses top's char)
    "single": (0xDA, 0xC4, 0xBF, 0xB3, 0xB3, 0xC0, 0xD9),
    "double": (0xC9, 0xCD, 0xBB, 0xBA, 0xBA, 0xC8, 0xBC),
    "mixed": (0xD5, 0xCD, 0xB8, 0xB3, 0xB3, 0xD4, 0xBE),       # double top/bottom, single sides
    "block": (0xDB, 0xDF, 0xDB, 0xDB, 0xDB, 0xDB, 0xDB),        # solid (bottom drawn with 0xDC)
}
BORDER_STYLES = ["none", "single", "double", "mixed", "block"]

# --------------------------------------------------------------- colours
COLORS: list[tuple[str, tuple[int, int, int]]] = [
    ("Black", (0, 0, 0)), ("Blue", (0, 0, 170)), ("Green", (0, 170, 0)), ("Cyan", (0, 170, 170)),
    ("Red", (170, 0, 0)), ("Magenta", (170, 0, 170)), ("Brown", (170, 85, 0)), ("LightGray", (170, 170, 170)),
    ("DarkGray", (85, 85, 85)), ("LightBlue", (85, 85, 255)), ("LightGreen", (85, 255, 85)),
    ("LightCyan", (85, 255, 255)), ("LightRed", (255, 85, 85)), ("LightMagenta", (255, 85, 255)),
    ("Yellow", (255, 255, 85)), ("White", (255, 255, 255)),
]
COLOR_NAMES = [n for n, _ in COLORS]


def color_index(v) -> int:
    """0..15 from an int or a colour name ("Yellow", "light blue", "14")."""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v & 15
    s = str(v).strip().replace(" ", "").lower()
    for i, n in enumerate(COLOR_NAMES):
        if n.lower() == s or n.lower().replace("light", "l") == s:
            return i
    aliases = {"grey": 7, "gray": 7, "darkgrey": 8, "lightgrey": 7, "orange": 6, "purple": 5, "brightwhite": 15}
    if s in aliases:
        return aliases[s]
    try:
        return int(s, 0) & 15
    except ValueError:
        return 7


def attr(fg: int, bg: int, blink: bool = False) -> int:
    """Text-mode attribute byte: blink bit 7, background 4..6, foreground 0..3 (bg 8..15 = iCE colours)."""
    return ((bg & 15) << 4 | (fg & 15)) | (0x80 if blink and bg < 8 else 0)


def split_attr(a: int) -> tuple[int, int, bool]:
    """(fg, bg 0..7, blink) of an attribute byte."""
    return a & 15, (a >> 4) & 7, bool(a & 0x80)
