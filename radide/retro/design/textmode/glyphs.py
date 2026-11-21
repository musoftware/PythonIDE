"""CP437 glyphs for the Qt views: a CellBuffer -> QImage (designer canvas, ANSI editor, PNG export).

The line-drawing characters (single / double, all junctions), the half blocks, the full block and the three
shades are drawn here pixel by pixel, so lines join without gaps at any cell size - no CP437 font is needed.
Letters and the other symbols come from a monospaced system font (Consolas / Lucida Console / Courier New).
"""
from __future__ import annotations

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QImage, QPainter

from .buffer import CellBuffer
from .cp437 import BOX, COLORS, to_unicode

FONTS = ["Consolas", "Lucida Console", "Courier New", "monospace"]
CELL = (9, 16)


def rgb(index: int) -> QColor:
    r, g, b = COLORS[index & 15][1]
    return QColor(r, g, b)


class GlyphSet:
    """Glyph masks and coloured glyphs for one cell size (cached)."""

    def __init__(self, cw: int = CELL[0], ch: int = CELL[1]):
        self.cw, self.ch = cw, ch
        self._mask: dict[int, QImage] = {}
        self._color: dict[tuple[int, int], QImage] = {}
        self.font = QFont()
        for fam in FONTS:
            f = QFont(fam)
            if QFontMetrics(f).horizontalAdvance("M") > 0:
                self.font = f
                break
        self.font.setStyleHint(QFont.StyleHint.Monospace)
        size = ch
        while size > 6:
            self.font.setPixelSize(size)
            fm = QFontMetrics(self.font)
            if fm.height() <= ch + 1 and fm.horizontalAdvance("W") <= cw + 1:
                break
            size -= 1

    # ------------------------------------------------------------ masks
    def mask(self, code: int) -> QImage:
        m = self._mask.get(code)
        if m is None:
            m = self._make_mask(code)
            self._mask[code] = m
        return m

    def _make_mask(self, code: int) -> QImage:
        cw, ch = self.cw, self.ch
        img = QImage(cw, ch, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        white = QColor(255, 255, 255)
        if code in BOX:
            self._box(p, BOX[code], white)
        elif code == 0xDB:
            p.fillRect(0, 0, cw, ch, white)
        elif code == 0xDC:
            p.fillRect(0, ch // 2, cw, ch - ch // 2, white)
        elif code == 0xDF:
            p.fillRect(0, 0, cw, ch // 2, white)
        elif code == 0xDD:
            p.fillRect(0, 0, (cw + 1) // 2, ch, white)
        elif code == 0xDE:
            p.fillRect((cw + 1) // 2, 0, cw - (cw + 1) // 2, ch, white)
        elif code == 0xFE:
            s = max(2, cw // 2)
            p.fillRect((cw - s) // 2, (ch - s) // 2, s, s, white)
        elif code in (0xB0, 0xB1, 0xB2):
            for y in range(ch):
                for x in range(cw):
                    if code == 0xB0:
                        on = (y % 2 == 0 and x % 4 == 0) or (y % 2 == 1 and x % 4 == 2)
                    elif code == 0xB1:
                        on = (x + y) % 2 == 0
                    else:
                        on = not ((y % 2 == 0 and x % 4 == 2) or (y % 2 == 1 and x % 4 == 0))
                    if on:
                        p.fillRect(x, y, 1, 1, white)
        elif code not in (0x00, 0x20, 0xFF):
            p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            p.setFont(self.font)
            p.setPen(white)
            p.drawText(QRect(0, 0, cw, ch), Qt.AlignmentFlag.AlignCenter, to_unicode(code))
        p.end()
        return img

    def _box(self, p: QPainter, arms: tuple[int, int, int, int], color: QColor) -> None:
        """Line-drawing glyph: arms (up, down, left, right), 1 single / 2 double."""
        cw, ch = self.cw, self.ch
        t = max(1, ch // 16)                  # line thickness
        cx, cy = (cw - t) // 2, (ch - t) // 2
        g = max(2, cw // 4)                   # offset of the two strokes of a double line
        up, down, left, right = arms

        def hline(x1: int, x2: int, y: int) -> None:
            if x2 >= x1:
                p.fillRect(x1, y, x2 - x1 + t, t, color)

        def vline(y1: int, y2: int, x: int) -> None:
            if y2 >= y1:
                p.fillRect(x, y1, t, y2 - y1 + t, color)

        horiz_double = 2 in (left, right)
        vert_double = 2 in (up, down)
        # vertical arms
        for arm, sign in ((up, -1), (down, 1)):
            if not arm:
                continue
            edge = 0 if sign < 0 else ch - t
            if arm == 1:
                start = cy + (g if horiz_double else 0) * sign
                vline(min(edge, start), max(edge, start), cx)
            else:
                for s in (-1, 1):
                    # a stroke stops at a horizontal arm on its side, otherwise it runs past the centre
                    side = left if s < 0 else right
                    near = cy + sign * (g if side == 2 else 0) if side else cy - sign * g
                    vline(min(edge, near), max(edge, near), cx + s * g)
        # horizontal arms
        for arm, sign in ((left, -1), (right, 1)):
            if not arm:
                continue
            edge = 0 if sign < 0 else cw - t
            if arm == 1:
                start = cx + (g if vert_double else 0) * sign
                hline(min(edge, start), max(edge, start), cy)
            else:
                for s in (-1, 1):
                    side = up if s < 0 else down
                    if side:
                        near = cx + sign * (g if side == 2 else 0)
                    else:
                        near = cx - sign * g
                    y = cy + s * g
                    hline(min(edge, near), max(edge, near), y)

    # ------------------------------------------------------------ coloured glyphs
    def glyph(self, code: int, fg: int) -> QImage:
        key = (code, fg)
        img = self._color.get(key)
        if img is None:
            m = self.mask(code)
            img = QImage(m.size(), QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(rgb(fg))
            p = QPainter(img)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            p.drawImage(0, 0, m)
            p.end()
            self._color[key] = img
        return img


_SETS: dict[tuple[int, int], GlyphSet] = {}


def glyph_set(cw: int = CELL[0], ch: int = CELL[1]) -> GlyphSet:
    gs = _SETS.get((cw, ch))
    if gs is None:
        gs = _SETS[(cw, ch)] = GlyphSet(cw, ch)
    return gs


def paint_cell(p: QPainter, gs: GlyphSet, x: int, y: int, code: int, attr: int, blink_on: bool = True,
               ice: bool = False) -> None:
    fg = attr & 15
    bg = (attr >> 4) & (15 if ice else 7)
    p.fillRect(x, y, gs.cw, gs.ch, rgb(bg))
    if not ice and attr & 0x80 and not blink_on:
        return
    if code not in (0x00, 0x20, 0xFF):
        p.drawImage(x, y, gs.glyph(code, fg))


def render_image(buf: CellBuffer, cw: int = CELL[0], ch: int = CELL[1], blink_on: bool = True,
                 ice: bool = False, region: tuple[int, int, int, int] | None = None,
                 into: QImage | None = None) -> QImage:
    """The buffer as an image (cols*cw x rows*ch). *region* (x, y, w, h in cells) repaints only part of *into*."""
    gs = glyph_set(cw, ch)
    img = into if into is not None else QImage(buf.cols * cw, buf.rows * ch, QImage.Format.Format_RGB32)
    p = QPainter(img)
    x0, y0, w, h = region if region else (0, 0, buf.cols, buf.rows)
    for yy in range(max(0, y0), min(buf.rows, y0 + h)):
        for xx in range(max(0, x0), min(buf.cols, x0 + w)):
            c, a = buf.get(xx, yy)
            paint_cell(p, gs, xx * cw, yy * ch, c, a, blink_on, ice)
    p.end()
    return img


def save_png(buf: CellBuffer, path, scale: int = 1, ice: bool = False) -> bool:
    img = render_image(buf, ice=ice)
    if scale > 1:
        img = img.scaled(img.width() * scale, img.height() * scale, Qt.AspectRatioMode.IgnoreAspectRatio,
                         Qt.TransformationMode.FastTransformation)
    return img.save(str(path), "PNG")


def char_icon(code: int, fg: int = 15, bg: int = 0, cw: int = CELL[0], ch: int = CELL[1], scale: int = 2):
    from PyQt6.QtGui import QIcon, QPixmap
    b = CellBuffer(1, 1, code, (bg << 4) | fg)
    img = render_image(b, cw, ch)
    return QIcon(QPixmap.fromImage(img.scaled(cw * scale, ch * scale)))
