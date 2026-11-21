"""ANSI / ASCII Art Editor (Qt): draw text-mode screens with CP437 characters and the 16 colours.

Tools: Pencil, Line (single / double lines join with existing box drawing automatically), Box, Fill, Text,
Select (copy / cut / paste / move / delete), Eyedropper. Character palette (all 256 CP437 characters, F1..F8
quick slots), foreground / background colours (iCE colours: 16 backgrounds instead of blink). Files: .ANS (with
SAUCE title / author / group), .BIN, .TXT; PNG export. Tools > Retro > Text-Mode > Use as Splash Screen puts the
art in front of the startup screen of a DOS Text-Mode Forms App.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QKeySequence, QPainter, QPen, QShortcut
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                             QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QScrollArea, QSpinBox,
                             QToolBar, QToolButton, QVBoxLayout, QWidget)

from .ansi import Sauce, art_sauce, load_art, save_art
from .buffer import CellBuffer
from .canvas import CellCanvas
from .cp437 import from_unicode, to_unicode
from .glyphs import CELL, render_image, rgb

TOOLS = ["Pencil", "Line", "Box", "Fill", "Text", "Select", "Eyedropper"]
QUICK = [0xDB, 0xB2, 0xB1, 0xB0, 0xDF, 0xDC, 0xDD, 0xDE]
FILTER = "ANSI art (*.ans);;Binary text (*.bin);;Text (*.txt *.asc *.nfo);;All files (*)"
MAX_UNDO = 100


class CharPalette(QWidget):
    """16 x 16 grid of the CP437 characters."""
    picked = pyqtSignal(int)

    def __init__(self, parent=None, scale: float = 1.4):
        super().__init__(parent)
        self.setProperty("i18n_skip", True)
        self.cur = 0xDB
        self.cw, self.ch = int(CELL[0] * scale) + 4, int(CELL[1] * scale) + 2
        b = CellBuffer(16, 16)
        for i in range(256):
            b.put(i % 16, i // 16, i, 0x0F)
        self.img = render_image(b)
        self.setFixedSize(self.cw * 16 + 1, self.ch * 16 + 1)
        self.setToolTip("Click a character")

    def set_char(self, code: int) -> None:
        self.cur = code & 0xFF
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0))
        for i in range(256):
            x, y = (i % 16) * self.cw, (i // 16) * self.ch
            src = QRect((i % 16) * CELL[0], (i // 16) * CELL[1], CELL[0], CELL[1])
            p.drawImage(QRect(x + 2, y + 1, self.cw - 4, self.ch - 2), self.img, src)
        x, y = (self.cur % 16) * self.cw, (self.cur // 16) * self.ch
        p.setPen(QPen(QColor(255, 255, 0), 2))
        p.drawRect(x, y, self.cw, self.ch)
        p.end()

    def mousePressEvent(self, e) -> None:
        x = int(e.position().x()) // self.cw
        y = int(e.position().y()) // self.ch
        if 0 <= x < 16 and 0 <= y < 16:
            self.set_char(y * 16 + x)
            self.picked.emit(self.cur)


class ColorBar(QWidget):
    """Foreground (left click) / background (right click) colour picker."""
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fg, self.bg = 15, 1
        self.ice = False
        self.setFixedSize(16 * 18 + 60, 26)
        self.setToolTip("Left click: foreground colour - right click: background colour")

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(0, 0, 50, 26, rgb(self.bg))
        p.fillRect(10, 6, 30, 14, rgb(self.fg))
        for i in range(16):
            r = QRect(56 + i * 18, 4, 16, 18)
            p.fillRect(r, rgb(i))
            if i >= 8 and not self.ice:
                p.setPen(QPen(QColor(80, 80, 80)))
                p.drawLine(r.bottomLeft(), r.topRight())
            if i == self.fg:
                p.setPen(QPen(QColor(255, 255, 255), 2))
                p.drawRect(r.adjusted(1, 1, -1, -1))
            if i == self.bg:
                p.setPen(QPen(QColor(255, 255, 0), 1, Qt.PenStyle.DashLine))
                p.drawRect(r.adjusted(3, 3, -3, -3))
        p.end()

    def mousePressEvent(self, e) -> None:
        i = (int(e.position().x()) - 56) // 18
        if not 0 <= i < 16:
            return
        if e.button() == Qt.MouseButton.RightButton:
            if i < 8 or self.ice:
                self.bg = i
        else:
            self.fg = i
        self.update()
        self.changed.emit()

    def attr(self, blink: bool = False) -> int:
        return (self.bg << 4) | self.fg | (0x80 if blink and not self.ice else 0)


class ArtCanvas(CellCanvas):
    """The drawing surface."""
    edited = pyqtSignal()
    beforeEdit = pyqtSignal()
    picked = pyqtSignal(int, int)          # eyedropper: char, attr
    status = pyqtSignal(str)

    def __init__(self, buf: CellBuffer, editor: "AnsiEditor"):
        super().__init__(buf)
        self.ed = editor
        self.tool = "Pencil"
        self._start: tuple[int, int] | None = None
        self._last: tuple[int, int] | None = None
        self._preview: CellBuffer | None = None
        self.sel: QRect | None = None          # in cells
        self.text_pos: tuple[int, int] | None = None
        self.clip: CellBuffer | None = None
        self.float_paste: tuple[CellBuffer, int, int] | None = None

    def paint_overlay(self, p: QPainter) -> None:
        if self.sel is not None:
            r = self.cell_rect(self.sel.x(), self.sel.y(), self.sel.width(), self.sel.height())
            p.setPen(QPen(QColor(255, 255, 0), 1, Qt.PenStyle.DashLine))
            p.drawRect(r.adjusted(0, 0, -1, -1))
        if self.float_paste is not None:
            b, x, y = self.float_paste
            r = self.cell_rect(x, y, b.cols, b.rows)
            p.drawImage(r, render_image(b, self.cw, self.ch, True, self.ice))
            p.setPen(QPen(QColor(0, 255, 255), 1, Qt.PenStyle.DashLine))
            p.drawRect(r.adjusted(0, 0, -1, -1))
        if self.tool == "Text" and self.text_pos is not None:
            x, y = self.text_pos
            r = self.cell_rect(x, y)
            p.fillRect(QRect(r.left(), r.bottom() - 2, r.width(), 2), QColor(255, 255, 255))

    # ------------------------------------------------------------ drawing helpers
    def _attr(self) -> int:
        return self.ed.colors.attr(self.ed.blink.isChecked())

    def _plot(self, buf: CellBuffer, x: int, y: int) -> None:
        buf.put(x, y, self.ed.char, self._attr())

    def _line(self, buf: CellBuffer, x0: int, y0: int, x1: int, y1: int) -> None:
        style = self.ed.line_style()
        if style and (x0 == x1 or y0 == y1):
            w = 2 if style == "double" else 1
            a = self._attr()
            if y0 == y1:
                lo, hi = sorted((x0, x1))
                for x in range(lo, hi + 1):
                    dirs = ("l" if x > lo else "") + ("r" if x < hi else "")
                    buf.line_join(x, y0, w, a, dirs or "lr")
            else:
                lo, hi = sorted((y0, y1))
                for y in range(lo, hi + 1):
                    dirs = ("u" if y > lo else "") + ("d" if y < hi else "")
                    buf.line_join(x0, y, w, a, dirs or "ud")
            return
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self._plot(buf, x0, y0)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def _box(self, buf: CellBuffer, x0: int, y0: int, x1: int, y1: int) -> None:
        x, y = min(x0, x1), min(y0, y1)
        w, h = abs(x1 - x0) + 1, abs(y1 - y0) + 1
        style = self.ed.line_style()
        if style:
            buf.box(x, y, w, h, style, self._attr(), fill=self.ed.box_fill.isChecked())
        else:
            if self.ed.box_fill.isChecked():
                buf.fill(x, y, w, h, self.ed.char, self._attr())
            else:
                for xx in range(x, x + w):
                    self._plot(buf, xx, y)
                    self._plot(buf, xx, y + h - 1)
                for yy in range(y, y + h):
                    self._plot(buf, x, yy)
                    self._plot(buf, x + w - 1, yy)

    def flood(self, x: int, y: int) -> None:
        target = self.buf.get(x, y)
        new = (self.ed.char, self._attr())
        if target == new:
            return
        stack = [(x, y)]
        seen = set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in seen or not self.buf.inside(cx, cy) or self.buf.get(cx, cy) != target:
                continue
            seen.add((cx, cy))
            self.buf.put(cx, cy, *new)
            stack += [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]

    # ------------------------------------------------------------ mouse
    def mousePressEvent(self, e) -> None:
        self.setFocus()
        x, y = self.cell_at(e.position().toPoint())
        if self.float_paste is not None:
            b, _px, _py = self.float_paste
            self.beforeEdit.emit()
            self.buf.blit(b, x, y)
            self.float_paste = None
            self.refresh()
            self.edited.emit()
            return
        if e.button() == Qt.MouseButton.RightButton or self.tool == "Eyedropper":
            c, a = self.buf.get(x, y)
            self.picked.emit(c, a)
            return
        t = self.tool
        if t == "Text":
            self.text_pos = (x, y)
            self.update()
            return
        if t == "Select":
            self._start = (x, y)
            self.sel = QRect(x, y, 1, 1)
            self.update()
            return
        self.beforeEdit.emit()
        if t == "Fill":
            self.flood(x, y)
            self.refresh()
            self.edited.emit()
            return
        self._start = self._last = (x, y)
        if t == "Pencil":
            self._plot(self.buf, x, y)
            self.refresh((x, y, 1, 1))
        else:
            self._preview = self.buf.copy()
        self.edited.emit()

    def mouseMoveEvent(self, e) -> None:
        x, y = self.cell_at(e.position().toPoint())
        c, a = self.buf.get(x, y)
        self.status.emit(f"{x}, {y}   char {c} ({to_unicode(c)})   fore {a & 15} back {(a >> 4) & 7}"
                         + ("  blink" if a & 0x80 else ""))
        if self.float_paste is not None:
            b, _x, _y = self.float_paste
            self.float_paste = (b, x, y)
            self.update()
            return
        if self._start is None or not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        t = self.tool
        if t == "Pencil":
            lx, ly = self._last
            self._line(self.buf, lx, ly, x, y) if (lx, ly) != (x, y) else None
            self._last = (x, y)
            self.refresh()
        elif t in ("Line", "Box") and self._preview is not None:
            self.buf = self._preview.copy()
            sx, sy = self._start
            if t == "Line":
                if e.modifiers() & Qt.KeyboardModifier.ShiftModifier or self.ed.line_style():
                    if abs(x - sx) >= abs(y - sy):
                        y = sy
                    else:
                        x = sx
                self._line(self.buf, sx, sy, x, y)
            else:
                self._box(self.buf, sx, sy, x, y)
            self.ed.buf = self.buf
            self.refresh()
        elif t == "Select":
            sx, sy = self._start
            self.sel = QRect(min(sx, x), min(sy, y), abs(x - sx) + 1, abs(y - sy) + 1)
            self.update()

    def mouseReleaseEvent(self, _e) -> None:
        if self._preview is not None:
            self._preview = None
            self.edited.emit()
        self._start = None

    # ------------------------------------------------------------ keys (text tool, selection)
    def keyPressEvent(self, e) -> None:
        k = e.key()
        if self.float_paste is not None and k == Qt.Key.Key_Escape:
            self.float_paste = None
            self.update()
            return
        if self.tool == "Text" and self.text_pos is not None:
            x, y = self.text_pos
            if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.text_pos = (self._text_x0 if hasattr(self, "_text_x0") else 0, min(self.buf.rows - 1, y + 1))
            elif k == Qt.Key.Key_Backspace:
                if x > 0:
                    self.beforeEdit.emit()
                    self.buf.put(x - 1, y, 0x20, self._attr())
                    self.text_pos = (x - 1, y)
                    self.refresh()
                    self.edited.emit()
            elif k in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
                dx = {Qt.Key.Key_Left: -1, Qt.Key.Key_Right: 1}.get(k, 0)
                dy = {Qt.Key.Key_Up: -1, Qt.Key.Key_Down: 1}.get(k, 0)
                self.text_pos = (max(0, min(self.buf.cols - 1, x + dx)), max(0, min(self.buf.rows - 1, y + dy)))
            elif Qt.Key.Key_F1 <= k <= Qt.Key.Key_F8:
                self._type(QUICK[k - Qt.Key.Key_F1])
            elif e.text() and e.text().isprintable():
                self._type(from_unicode(e.text()[0]))
            else:
                return super().keyPressEvent(e)
            self.update()
            return
        if k == Qt.Key.Key_Delete and self.sel is not None:
            self.ed.delete_selection()
            return
        super().keyPressEvent(e)

    def _type(self, code: int) -> None:
        x, y = self.text_pos
        self.beforeEdit.emit()
        self.buf.put(x, y, code, self._attr())
        self.text_pos = (min(self.buf.cols - 1, x + 1), y)
        self.refresh((x, y, 1, 1))
        self.edited.emit()


class SauceDialog(QDialog):
    def __init__(self, sauce: Sauce, cols: int, rows: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Art Properties (SAUCE)")
        f = QFormLayout(self)
        self.title = QLineEdit(sauce.title)
        self.title.setMaxLength(35)
        self.author = QLineEdit(sauce.author)
        self.author.setMaxLength(20)
        self.group = QLineEdit(sauce.group)
        self.group.setMaxLength(20)
        self.cols = QSpinBox()
        self.cols.setRange(1, 160)
        self.cols.setValue(cols)
        self.rows = QSpinBox()
        self.rows.setRange(1, 2000)
        self.rows.setValue(rows)
        self.ice = QCheckBox("iCE colours (16 background colours, no blink)")
        self.ice.setChecked(sauce.ice_colors)
        for label, w in (("Title:", self.title), ("Author:", self.author), ("Group:", self.group),
                         ("Columns:", self.cols), ("Rows:", self.rows)):
            f.addRow(label, w)
        f.addRow(self.ice)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)


class AnsiEditor(QWidget):
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal()
    splashRequested = pyqtSignal(object)        # path

    def __init__(self, path: Path | None = None, cols: int = 80, rows: int = 25, parent=None):
        super().__init__(parent)
        self.doc_path: Path | None = Path(path) if path else None
        self.sauce = Sauce()
        if self.doc_path is not None and self.doc_path.exists():
            self.buf = load_art(self.doc_path)
            self.sauce = art_sauce(self.doc_path) or Sauce()
        else:
            self.buf = CellBuffer(cols, rows, 0x20, 0x07)
        self.char = 0xDB
        self._undo: list[CellBuffer] = []
        self._redo: list[CellBuffer] = []
        self._modified = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        tb = QToolBar()
        lay.addWidget(tb)
        self.tool_group = QButtonGroup(self)
        for t in TOOLS:
            b = QToolButton()
            b.setText(t)
            b.setCheckable(True)
            b.setChecked(t == "Pencil")
            self.tool_group.addButton(b)
            b.clicked.connect(lambda _c=False, tt=t: self.set_tool(tt))
            tb.addWidget(b)
        tb.addSeparator()
        tb.addWidget(QLabel(" Lines: "))
        self.lines = QComboBox()
        self.lines.addItems(["character", "single", "double"])
        self.lines.setToolTip("Line and Box tools: draw with the selected character, or with single / double "
                              "box-drawing lines that join automatically")
        tb.addWidget(self.lines)
        self.box_fill = QCheckBox("Fill box")
        tb.addWidget(self.box_fill)
        self.blink = QCheckBox("Blink")
        tb.addWidget(self.blink)
        tb.addSeparator()
        tb.addAction("Undo", self.undo)
        tb.addAction("Redo", self.redo)
        tb.addSeparator()
        tb.addAction("Import...", self.import_dialog)
        tb.addAction("Export...", self.export_dialog)
        tb.addAction("Export PNG...", self.export_png)
        tb.addAction("Properties...", self.properties)
        tb.addAction("Use as Splash Screen", lambda: self.splashRequested.emit(self.doc_path))
        body = QHBoxLayout()
        lay.addLayout(body, 1)
        self.canvas = ArtCanvas(self.buf, self)
        self.canvas.ice = self.sauce.ice_colors
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.canvas)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setStyleSheet("QScrollArea { background: #3c3c3c; }")
        body.addWidget(self.scroll, 1)
        side = QVBoxLayout()
        side.addWidget(QLabel("Character (F1..F8 in the Text tool: block characters):"))
        self.palette = CharPalette(self)
        self.palette.set_char(self.char)
        self.palette.picked.connect(self._char_picked)
        side.addWidget(self.palette)
        side.addWidget(QLabel("Colours (left: fore, right: back):"))
        self.colors = ColorBar(self)
        self.colors.ice = self.sauce.ice_colors
        side.addWidget(self.colors)
        self.info = QLabel("")
        self.info.setProperty("i18n_skip", True)
        side.addWidget(self.info)
        side.addStretch(1)
        body.addLayout(side)
        self.canvas.beforeEdit.connect(self._snapshot)
        self.canvas.edited.connect(self._edited)
        self.canvas.picked.connect(self._eyedrop)
        self.canvas.status.connect(self.info.setText)
        for seq, fn in (("Ctrl+Z", self.undo), ("Ctrl+Y", self.redo), ("Ctrl+C", self.copy),
                        ("Ctrl+X", self.cut), ("Ctrl+V", self.paste), ("Ctrl+S", self.save)):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(fn)

    # ------------------------------------------------------------ state
    @property
    def path(self) -> Path:
        return self.doc_path or Path("Untitled.ans")

    def is_modified(self) -> bool:
        return self._modified

    def _set_modified(self, m: bool) -> None:
        if m != self._modified:
            self._modified = m
            self.modifiedChanged.emit(m)

    def line_style(self) -> str:
        t = self.lines.currentText()
        return "" if t == "character" else t

    def set_tool(self, t: str) -> None:
        self.canvas.tool = t
        for b in self.tool_group.buttons():
            b.setChecked(b.text() == t)
        if t != "Select":
            self.canvas.sel = None
        self.canvas.update()

    def _char_picked(self, code: int) -> None:
        self.char = code

    def _eyedrop(self, c: int, a: int) -> None:
        self.char = c
        self.palette.set_char(c)
        self.colors.fg, self.colors.bg = a & 15, (a >> 4) & (15 if self.colors.ice else 7)
        self.blink.setChecked(bool(a & 0x80) and not self.colors.ice)
        self.colors.update()

    def _snapshot(self) -> None:
        self._undo.append(self.canvas.buf.copy())
        del self._undo[:-MAX_UNDO]
        self._redo.clear()

    def _edited(self) -> None:
        self.buf = self.canvas.buf
        self._set_modified(True)

    def _set_buf(self, b: CellBuffer) -> None:
        self.buf = b
        self.canvas.set_buffer(b)

    def undo(self) -> None:
        if self._undo:
            self._redo.append(self.canvas.buf.copy())
            self._set_buf(self._undo.pop())
            self._set_modified(True)

    def redo(self) -> None:
        if self._redo:
            self._undo.append(self.canvas.buf.copy())
            self._set_buf(self._redo.pop())
            self._set_modified(True)

    # ------------------------------------------------------------ selection / clipboard
    def _sel(self) -> tuple[int, int, int, int] | None:
        r = self.canvas.sel
        return (r.x(), r.y(), r.width(), r.height()) if r is not None else None

    def copy(self) -> None:
        s = self._sel()
        if s:
            self.canvas.clip = self.canvas.buf.region(*s)
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(self.canvas.clip.plain_text())

    def cut(self) -> None:
        self.copy()
        self.delete_selection()

    def delete_selection(self) -> None:
        s = self._sel()
        if s:
            self._snapshot()
            self.canvas.buf.fill(*s, 0x20, self.colors.attr())
            self.canvas.refresh()
            self._edited()

    def paste(self) -> None:
        clip = self.canvas.clip
        if clip is None:
            from PyQt6.QtWidgets import QApplication
            from .ansi import parse_text
            t = QApplication.clipboard().text()
            if not t:
                return
            clip = parse_text(t.encode("utf-8"), max(len(ln) for ln in t.splitlines() or [""]) or 1)
        self.canvas.float_paste = (clip, 0, 0)
        self.set_tool("Select")
        self.canvas.update()

    def edit_op(self, op: str) -> None:
        {"undo": self.undo, "redo": self.redo, "copy": self.copy, "cut": self.cut, "paste": self.paste,
         "delete": self.delete_selection}.get(op, lambda: None)()

    # ------------------------------------------------------------ files
    def save(self, path=None) -> bool:
        p = Path(path) if path else self.doc_path
        if p is None:
            f, _ = QFileDialog.getSaveFileName(self, "Save Art", "Untitled.ans", FILTER)
            if not f:
                return False
            p = Path(f)
        save_art(self.canvas.buf, p, self.sauce)
        self.doc_path = p
        self._set_modified(False)
        self.saved.emit()
        return True

    def import_dialog(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Import Art", "", FILTER)
        if not f:
            return
        try:
            b = load_art(Path(f))
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Import", str(e))
            return
        self._snapshot()
        sc = art_sauce(f)
        if sc is not None:
            self.sauce = sc
            self.canvas.ice = self.colors.ice = sc.ice_colors
        self._set_buf(b)
        self._edited()

    def export_dialog(self) -> None:
        f, _ = QFileDialog.getSaveFileName(self, "Export Art", self.path.stem + ".ans", FILTER)
        if f:
            save_art(self.canvas.buf, Path(f), self.sauce)

    def export_png(self) -> None:
        from .glyphs import save_png
        f, _ = QFileDialog.getSaveFileName(self, "Export PNG", self.path.stem + ".png", "PNG (*.png)")
        if f:
            save_png(self.canvas.buf, f, 1, self.sauce.ice_colors)

    def properties(self) -> None:
        d = SauceDialog(self.sauce, self.canvas.buf.cols, self.canvas.buf.rows, self)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        self.sauce.title, self.sauce.author, self.sauce.group = d.title.text(), d.author.text(), d.group.text()
        self.sauce.ice_colors = d.ice.isChecked()
        self.canvas.ice = self.colors.ice = self.sauce.ice_colors
        if (d.cols.value(), d.rows.value()) != (self.canvas.buf.cols, self.canvas.buf.rows):
            self._snapshot()
            self._set_buf(self.canvas.buf.resized(d.cols.value(), d.rows.value()))
        self.canvas.refresh()
        self.colors.update()
        self._set_modified(True)

    def sizeHint(self) -> QSize:
        return QSize(1100, 600)


ART_EXTS = (".ans", ".asc", ".nfo", ".diz")


def is_art_file(path) -> bool:
    """.ans / .asc / .nfo always; .bin only with a SAUCE record or a 4000 / 8000-byte screen dump."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext in ART_EXTS:
        return True
    if ext == ".bin":
        try:
            size = p.stat().st_size
            if size in (4000, 6880, 8000):
                return True
            with open(p, "rb") as f:
                f.seek(max(0, size - 128))
                return f.read(7) == b"SAUCE00"
        except OSError:
            return False
    return False


__all__ = ["AnsiEditor", "CharPalette", "ColorBar", "ArtCanvas", "is_art_file"]
