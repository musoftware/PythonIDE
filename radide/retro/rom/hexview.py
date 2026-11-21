"""HexView - a virtualised hex / text view of a HexBuffer (only the visible rows are painted, so a 64 MB file
scrolls like a 1 KB one). Overwrite and insert modes, nibble editing, selection, structure overlay (header
fields coloured with a tooltip), bookmarks, diff marks and search hits, .tbl-aware text column."""
from __future__ import annotations

import bisect

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QKeySequence, QPainter, QPalette
from PyQt6.QtWidgets import QAbstractScrollArea, QApplication, QToolTip

from .buffer import HexBuffer

HEX_DIGITS = "0123456789abcdefABCDEF"


def _font() -> QFont:
    f = QFont("Consolas")
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setPointSize(10)
    return f


class HexView(QAbstractScrollArea):
    cursorMoved = pyqtSignal(int)
    selectionChanged = pyqtSignal(int, int)          # start, length
    edited = pyqtSignal()
    modeChanged = pyqtSignal(bool)                   # insert mode

    def __init__(self, buffer: HexBuffer | None = None, parent=None):
        super().__init__(parent)
        self.buf = buffer or HexBuffer()
        self.bpr = 16
        self.cursor = 0
        self.nibble = 0
        self.area = "hex"
        self.anchor: int | None = None
        self.insert_mode = False
        self.read_only = False
        self.table = None                            # tbl.Table for the text column
        self.codec = "latin-1"
        self.fields: list = []                       # detect.Field overlay
        self._field_starts: list[int] = []
        self.diff_ranges: list[tuple[int, int]] = []  # (start, end) highlighted (compare view)
        self._diff_starts: list[int] = []
        self.hit: tuple[int, int] | None = None
        self.hits: list[tuple[int, int]] = []
        self.addr_base = 0                           # added to the offsets shown in the left column
        self.setFont(_font())
        self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.viewport().setMouseTracking(True)
        self._drag = False
        self.buf.listeners.append(self._on_buffer)
        self._metrics()

    # ------------------------------------------------------------------ setup
    def set_buffer(self, buf: HexBuffer) -> None:
        if self._on_buffer in self.buf.listeners:
            self.buf.listeners.remove(self._on_buffer)
        self.buf = buf
        buf.listeners.append(self._on_buffer)
        self.cursor = min(self.cursor, len(buf))
        self.anchor = None
        self._update_scroll()
        self.viewport().update()

    def set_fields(self, fields) -> None:
        self.fields = sorted([f for f in fields if 0 < f.length <= 4096], key=lambda f: f.offset)
        self._field_starts = [f.offset for f in self.fields]
        self.viewport().update()

    def set_diff_ranges(self, ranges) -> None:
        self.diff_ranges = sorted(ranges)
        self._diff_starts = [a for a, _b in self.diff_ranges]
        self.viewport().update()

    def set_bytes_per_row(self, n: int) -> None:
        self.bpr = max(4, min(64, int(n)))
        self._metrics()
        self.ensure_visible(self.cursor)
        self.viewport().update()

    def set_table(self, table) -> None:
        self.table = table
        self.viewport().update()

    def setFont(self, f) -> None:  # noqa: N802 - Qt naming
        super().setFont(f)
        self._metrics()

    def _metrics(self) -> None:
        fm = QFontMetrics(self.font())
        self.cw = max(1, fm.horizontalAdvance("0"))
        self.rh = fm.height() + 2
        self.ascent = fm.ascent() + 1
        self.off_digits = 8
        self.x_hex = (self.off_digits + 2) * self.cw
        self.x_text = self.x_hex + (self.bpr * 3 + self.bpr // 8 + 1) * self.cw
        self.total_w = self.x_text + (self.bpr + 2) * self.cw
        self._update_scroll()

    # ------------------------------------------------------------------ geometry
    def rows(self) -> int:
        return len(self.buf) // self.bpr + 1

    def visible_rows(self) -> int:
        return max(1, self.viewport().height() // self.rh)

    def _update_scroll(self) -> None:
        vs = self.verticalScrollBar()
        vs.setRange(0, max(0, self.rows() - self.visible_rows()))
        vs.setPageStep(self.visible_rows())
        vs.setSingleStep(1)
        hs = self.horizontalScrollBar()
        hs.setRange(0, max(0, self.total_w - self.viewport().width()))
        hs.setPageStep(self.viewport().width())

    def resizeEvent(self, e) -> None:  # noqa: N802
        super().resizeEvent(e)
        self._update_scroll()

    def _hex_x(self, col: int) -> int:
        return self.x_hex + (col * 3 + col // 8) * self.cw

    def _text_x(self, col: int) -> int:
        return self.x_text + col * self.cw

    def _hit_test(self, pos: QPoint) -> tuple[int, str, int] | None:
        """(offset, area, nibble) under a viewport point."""
        x = pos.x() + self.horizontalScrollBar().value()
        row = self.verticalScrollBar().value() + pos.y() // self.rh
        if x >= self.x_text - self.cw // 2:
            col = (x - self.x_text) // self.cw
            area, nib = "text", 0
        else:
            rel = x - self.x_hex
            if rel < 0:
                col, nib = 0, 0
            else:
                col = 0
                for c in range(self.bpr):       # account for the group gaps
                    if self._hex_x(c) - self.x_hex <= rel:
                        col = c
                units = (rel - (self._hex_x(col) - self.x_hex)) // self.cw
                nib = 1 if units >= 1 else 0
            area = "hex"
        col = max(0, min(self.bpr - 1, col))
        off = row * self.bpr + col
        return min(off, len(self.buf)), area, nib

    # ------------------------------------------------------------------ selection / cursor
    def selection(self) -> tuple[int, int]:
        """(start, length); length 0 = no selection."""
        if self.anchor is None or self.anchor == self.cursor:
            return self.cursor, 0
        a, b = sorted((self.anchor, self.cursor))
        return a, b - a + (1 if b < len(self.buf) else 0)

    def selected_bytes(self) -> bytes:
        s, n = self.selection()
        return self.buf.read(s, n) if n else b""

    def set_cursor(self, offset: int, select: int = 0, extend: bool = False, nibble: int = 0) -> None:
        offset = max(0, min(int(offset), len(self.buf)))
        if extend:
            if self.anchor is None:
                self.anchor = self.cursor
        else:
            self.anchor = None
        self.cursor = offset
        self.nibble = nibble
        if select > 0:
            self.anchor = offset
            self.cursor = min(len(self.buf), offset + select - 1)
        self.ensure_visible(self.cursor)
        self.viewport().update()
        self.cursorMoved.emit(self.cursor)
        self.selectionChanged.emit(*self.selection())

    def select_range(self, start: int, length: int) -> None:
        self.set_cursor(start, select=max(1, length))
        self.ensure_visible(start)

    def ensure_visible(self, offset: int) -> None:
        row = offset // self.bpr
        vs = self.verticalScrollBar()
        first = vs.value()
        vis = self.visible_rows()
        if row < first:
            vs.setValue(row)
        elif row >= first + vis:
            vs.setValue(row - vis + 1)

    def top_offset(self) -> int:
        return self.verticalScrollBar().value() * self.bpr

    def scroll_to_offset(self, offset: int) -> None:
        self.verticalScrollBar().setValue(offset // self.bpr)

    # ------------------------------------------------------------------ painting
    def _field_at(self, off: int):
        i = bisect.bisect_right(self._field_starts, off) - 1
        while i >= 0:
            f = self.fields[i]
            if f.offset <= off < f.offset + f.length:
                return f
            if off - f.offset > 4096:
                break
            i -= 1
        return None

    def _in_diff(self, off: int) -> bool:
        i = bisect.bisect_right(self._diff_starts, off) - 1
        return i >= 0 and self.diff_ranges[i][0] <= off < self.diff_ranges[i][1]

    def _char(self, b: int) -> str:
        if self.table is not None:
            v = self.table.single(b)
            if v is None:
                return "·"
            return v if len(v) == 1 and v.isprintable() else "•"
        if self.codec == "latin-1":
            return chr(b) if 32 <= b < 127 or 160 < b else "."
        try:
            c = bytes([b]).decode(self.codec)
            return c if c.isprintable() else "."
        except (UnicodeDecodeError, LookupError):
            return "."

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self.viewport())
        pal = self.palette()
        base = pal.color(QPalette.ColorRole.Base)
        text = pal.color(QPalette.ColorRole.Text)
        dark = base.lightness() < 128
        p.fillRect(self.viewport().rect(), base)
        p.setFont(self.font())
        dx = -self.horizontalScrollBar().value()
        first = self.verticalScrollBar().value()
        vis = self.visible_rows() + 1
        data = self.buf.data
        n = len(data)
        sel_s, sel_n = self.selection()
        sel_e = sel_s + sel_n
        gutter = QColor("#2b2b2b" if dark else "#f0f0f0")
        p.fillRect(QRect(0, 0, self.x_hex - self.cw + dx, self.viewport().height()), gutter)
        off_color = QColor("#7f8c8d")
        sel_color = pal.color(QPalette.ColorRole.Highlight)
        sel_color.setAlpha(110)
        diff_color = QColor(220, 50, 47, 90)
        hit_color = QColor(255, 200, 0, 150)
        bm_color = QColor(245, 166, 35, 120)
        bm_offsets = {b.offset for b in self.buf.bookmarks}
        hit = self.hit
        for r in range(vis):
            row = first + r
            start = row * self.bpr
            if start > n:
                break
            y = r * self.rh
            chunk = data[start:start + self.bpr]
            # backgrounds
            for c in range(len(chunk) if start < n else 0):
                off = start + c
                color = None
                if sel_n and sel_s <= off < sel_e:
                    color = sel_color
                elif hit is not None and hit[0] <= off < hit[0] + hit[1]:
                    color = hit_color
                elif self.diff_ranges and self._in_diff(off):
                    color = diff_color
                elif off in bm_offsets:
                    color = bm_color
                elif self.fields:
                    f = self._field_at(off)
                    if f is not None:
                        color = QColor(f.color)
                        color.setAlpha(70 if not dark else 90)
                if color is not None:
                    p.fillRect(QRect(self._hex_x(c) + dx, y, self.cw * 3, self.rh), color)
                    p.fillRect(QRect(self._text_x(c) + dx, y, self.cw, self.rh), color)
            # offset column
            p.setPen(off_color)
            p.drawText(QPoint(self.cw // 2 + dx, y + self.ascent), f"{start + self.addr_base:08X}")
            # hex
            p.setPen(text)
            parts = []
            for c, b in enumerate(chunk):
                parts.append(f"{b:02X} ")
                if c % 8 == 7:
                    parts.append(" ")
            p.drawText(QPoint(self.x_hex + dx, y + self.ascent), "".join(parts))
            p.drawText(QPoint(self.x_text + dx, y + self.ascent), "".join(self._char(b) for b in chunk))
        # separator line
        p.setPen(QColor("#888888"))
        xs = self.x_text - self.cw // 2 + dx
        p.drawLine(xs, 0, xs, self.viewport().height())
        # cursor
        crow = self.cursor // self.bpr - first
        if 0 <= crow <= vis:
            col = self.cursor % self.bpr
            y = crow * self.rh
            focus = self.hasFocus()
            cur = QColor("#e74c3c") if focus else QColor("#95a5a6")
            if self.area == "hex":
                x = self._hex_x(col) + self.nibble * self.cw + dx
                w = self.cw if not self.insert_mode else 2
                p.fillRect(QRect(x, y + self.rh - 3, self.cw, 3), cur) if not self.insert_mode else \
                    p.fillRect(QRect(x, y, w, self.rh), cur)
                p.setPen(cur)
                p.drawRect(QRect(self._text_x(col) + dx, y, self.cw - 1, self.rh - 1))
            else:
                x = self._text_x(col) + dx
                p.fillRect(QRect(x, y + self.rh - 3, self.cw, 3), cur) if not self.insert_mode else \
                    p.fillRect(QRect(x, y, 2, self.rh), cur)
                p.setPen(cur)
                p.drawRect(QRect(self._hex_x(col) + dx, y, self.cw * 2, self.rh - 1))
        p.end()

    # ------------------------------------------------------------------ buffer changes
    def _on_buffer(self, offset: int, old_len: int, new_len: int) -> None:
        if old_len != new_len:
            self._update_scroll()
        self.viewport().update()

    # ------------------------------------------------------------------ mouse
    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(e)
        hit = self._hit_test(e.position().toPoint())
        if hit is None:
            return
        off, area, nib = hit
        self.area = area
        extend = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        self.set_cursor(off, extend=extend, nibble=nib if area == "hex" else 0)
        if not extend:
            self.anchor = off
        self._drag = True

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        pos = e.position().toPoint()
        if self._drag and e.buttons() & Qt.MouseButton.LeftButton:
            hit = self._hit_test(pos)
            if hit is not None:
                self.cursor = min(hit[0], max(0, len(self.buf) - 1)) if len(self.buf) else 0
                self.ensure_visible(self.cursor)
                self.viewport().update()
                self.cursorMoved.emit(self.cursor)
                self.selectionChanged.emit(*self.selection())
            return
        if self.fields:
            hit = self._hit_test(pos)
            f = self._field_at(hit[0]) if hit else None
            if f is not None:
                QToolTip.showText(e.globalPosition().toPoint(), f"<b>{f.name}</b><br>{f.value}<br>"
                                  f"0x{f.offset:X} - 0x{f.offset + f.length - 1:X}", self.viewport())
            else:
                QToolTip.hideText()

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        self._drag = False
        if self.anchor == self.cursor:
            self.anchor = None
        super().mouseReleaseEvent(e)

    # ------------------------------------------------------------------ keyboard
    def keyPressEvent(self, e) -> None:  # noqa: N802
        key = e.key()
        mods = e.modifiers()
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        n = len(self.buf)
        move = None
        if key == Qt.Key.Key_Left:
            if self.area == "hex" and self.nibble == 1 and not shift:
                self.nibble = 0
                self.viewport().update()
                return
            move = self.cursor - 1
        elif key == Qt.Key.Key_Right:
            move = self.cursor + 1
        elif key == Qt.Key.Key_Up:
            move = self.cursor - self.bpr
        elif key == Qt.Key.Key_Down:
            move = self.cursor + self.bpr
        elif key == Qt.Key.Key_PageUp:
            move = self.cursor - self.bpr * self.visible_rows()
        elif key == Qt.Key.Key_PageDown:
            move = self.cursor + self.bpr * self.visible_rows()
        elif key == Qt.Key.Key_Home:
            move = 0 if ctrl else self.cursor - self.cursor % self.bpr
        elif key == Qt.Key.Key_End:
            move = n if ctrl else min(n, self.cursor - self.cursor % self.bpr + self.bpr - 1)
        if move is not None:
            if move < 0 and key in (Qt.Key.Key_Up, Qt.Key.Key_PageUp):
                move = self.cursor % self.bpr if key == Qt.Key.Key_PageUp else self.cursor
            self.set_cursor(max(0, min(n, move)), extend=shift)
            return
        if key == Qt.Key.Key_Tab or key == Qt.Key.Key_Backtab:
            self.area = "text" if self.area == "hex" else "hex"
            self.nibble = 0
            self.viewport().update()
            return
        if key == Qt.Key.Key_Insert and not mods:
            self.insert_mode = not self.insert_mode
            self.modeChanged.emit(self.insert_mode)
            self.viewport().update()
            return
        if e.matches(QKeySequence.StandardKey.SelectAll):
            self.select_all()
            return
        if e.matches(QKeySequence.StandardKey.Copy):
            self.copy()
            return
        if e.matches(QKeySequence.StandardKey.Paste):
            self.paste()
            return
        if e.matches(QKeySequence.StandardKey.Cut):
            self.cut()
            return
        if e.matches(QKeySequence.StandardKey.Undo):
            self.undo()
            return
        if e.matches(QKeySequence.StandardKey.Redo):
            self.redo()
            return
        if self.read_only:
            return super().keyPressEvent(e)
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            s, ln = self.selection()
            if ln:
                self.delete_selection()
            elif key == Qt.Key.Key_Delete and self.cursor < n:
                if self.insert_mode:
                    self.buf.delete(self.cursor, 1)
                else:
                    self.buf.overwrite(self.cursor, b"\x00", merge_key="")
                self._edited()
            elif key == Qt.Key.Key_Backspace and self.cursor > 0:
                if self.insert_mode:
                    self.buf.delete(self.cursor - 1, 1)
                    self.set_cursor(self.cursor - 1)
                else:
                    self.set_cursor(self.cursor - 1)
                self._edited()
            return
        t = e.text()
        if not t or ctrl or not t.isprintable():
            return super().keyPressEvent(e)
        if self.area == "hex":
            if t not in HEX_DIGITS:
                return
            self.type_nibble(int(t, 16))
        else:
            self.type_text(t)

    def type_nibble(self, v: int) -> None:
        s, ln = self.selection()
        if ln and self.insert_mode:
            self.buf.delete(s, ln)
            self.cursor, self.anchor = s, None
        elif ln:
            self.cursor, self.anchor = s, None
        off = self.cursor
        n = len(self.buf)
        if self.nibble == 0:
            if self.insert_mode or off >= n:
                self.buf.insert(off, bytes([v << 4]), merge_key="hex")
            else:
                old = self.buf.data[off]
                self.buf.overwrite(off, bytes([(v << 4) | (old & 0x0F)]), merge_key="hexhi")
            self.nibble = 1
        else:
            old = self.buf.data[off] if off < len(self.buf) else 0
            self.buf.overwrite(off, bytes([(old & 0xF0) | v]), merge_key="hexlo")
            self.nibble = 0
            self.cursor = min(len(self.buf), off + 1)
        self.ensure_visible(self.cursor)
        self._edited()

    def type_text(self, t: str) -> None:
        if self.table is not None:
            data = self.table.encode(t)
            if data is None:
                QApplication.beep()
                return
        else:
            try:
                data = t.encode(self.codec)
            except (UnicodeEncodeError, LookupError):
                QApplication.beep()
                return
        s, ln = self.selection()
        if ln:
            self.buf.replace(s, data, ln)
            self.cursor, self.anchor = s + len(data), None
        elif self.insert_mode:
            self.buf.insert(self.cursor, data, merge_key="text")
            self.cursor += len(data)
        else:
            self.buf.overwrite(self.cursor, data, merge_key="text")
            self.cursor += len(data)
        self.cursor = min(self.cursor, len(self.buf))
        self.ensure_visible(self.cursor)
        self._edited()

    def _edited(self) -> None:
        self.viewport().update()
        self.cursorMoved.emit(self.cursor)
        self.edited.emit()

    # ------------------------------------------------------------------ edit operations
    def select_all(self) -> None:
        if len(self.buf):
            self.anchor = 0
            self.cursor = len(self.buf) - 1
            self.viewport().update()
            self.selectionChanged.emit(*self.selection())

    def copy(self, fmt: str = "") -> str:
        from .formats import copy_text
        data = self.selected_bytes() or self.buf.read(self.cursor, 1)
        fmt = fmt or ("text" if self.area == "text" else "hex")
        text = copy_text(data, fmt, self.selection()[0], self.table, self.codec)
        QApplication.clipboard().setText(text)
        return text

    def cut(self) -> None:
        if self.read_only:
            return
        self.copy()
        self.delete_selection()

    def delete_selection(self) -> None:
        s, ln = self.selection()
        if not ln:
            return
        if self.insert_mode:
            self.buf.delete(s, ln)
        else:
            self.buf.fill(s, ln, b"\x00")
        self.anchor = None
        self.cursor = s
        self._edited()

    def paste(self, text: str | None = None) -> None:
        if self.read_only:
            return
        from .buffer import PatternError, parse_hex_bytes
        text = QApplication.clipboard().text() if text is None else text
        if not text:
            return
        data = None
        if self.area == "hex":
            try:
                data = parse_hex_bytes(text)
            except PatternError:
                data = None
        if data is None:
            data = (self.table.encode(text) if self.table is not None else None) or text.encode(self.codec, "replace")
        s, ln = self.selection()
        if ln and self.insert_mode:
            self.buf.replace(s, data, ln)
        elif self.insert_mode:
            self.buf.insert(s, data)
        else:
            self.buf.overwrite(s, data)
        self.anchor = None
        self.cursor = min(len(self.buf), s + len(data))
        self._edited()

    def undo(self) -> None:
        e = self.buf.undo()
        if e is not None:
            self.anchor = None
            self.cursor = min(e.cursor_before, len(self.buf))
            self.nibble = 0
            self.ensure_visible(self.cursor)
            self._edited()

    def redo(self) -> None:
        e = self.buf.redo()
        if e is not None:
            self.anchor = None
            self.cursor = min(e.cursor_after, len(self.buf))
            self.nibble = 0
            self.ensure_visible(self.cursor)
            self._edited()


__all__ = ["HexView"]
