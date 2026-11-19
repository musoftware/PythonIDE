"""Code editor built on QPlainTextEdit (full Unicode / Arabic / bidi support).

Features: line numbers, breakpoint margin, current-statement marker,
syntax highlighting driven by the language plugin, auto-indent, brace
matching, comment toggling, and IntelliSense (completion list as you type,
member lists after ".", signature calltips after "(").
"""
from __future__ import annotations

import re
from pathlib import Path

from PyQt6.QtCore import QPoint, QPointF, QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (QColor, QFont, QFontMetrics, QIcon, QKeySequence, QPainter, QPixmap, QPolygonF,
                         QShortcut, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QTextFormat)
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                             QPlainTextEdit, QTextEdit, QVBoxLayout, QWidget)

from .document import FormDocument

FONT = QFont("Consolas", 10)
FONT.setStyleHint(QFont.StyleHint.Monospace)
COLORS = {"keyword": "#0000FF", "builtin": "#2B91AF", "comment": "#008000", "string": "#A31515",
          "number": "#098658", "decorator": "#795E26", "defname": "#795E26", "operator": "#000000"}
INDENT = "    "
# editor chrome colours (Tools > Options switches them for the dark theme)
EDITOR_THEME = {"margin": "#F3F3F3", "margin_bp": "#E6E6E6", "line_number": "#2B91AF",
                "breakpoint_line": "#F7D9D6", "current_stmt": "#FFF3A0", "caret_line": "#EEF4FF"}


# =================================================================== highlighting
class Highlighter(QSyntaxHighlighter):
    """Generic highlighter configured from the language plugin
    (keywords, builtins, comment markers, string quotes, triple quotes)."""

    IN_BLOCK_COMMENT, IN_TRIPLE_DQ, IN_TRIPLE_SQ = 1, 2, 3

    def __init__(self, plugin, document):
        super().__init__(document)
        self.plugin = plugin
        cs = plugin.case_sensitive
        flags = 0 if cs else re.I
        self.fmt = {}
        for name, colour in COLORS.items():
            f = QTextCharFormat()
            f.setForeground(QColor(colour))
            if name == "keyword":
                f.setFontWeight(QFont.Weight.Bold)
            if name == "comment":
                f.setFontItalic(True)
            self.fmt[name] = f
        words = lambda ws: r"\b(?:" + "|".join(re.escape(w) for w in sorted(ws, key=len, reverse=True)) + r")\b"
        self.rx_kw = re.compile(words(plugin.keywords), flags) if plugin.keywords else None
        self.rx_bi = re.compile(words(plugin.builtins), flags) if plugin.builtins else None
        self.rx_num = re.compile(r"\b\d+(?:\.\d+)?\b")
        self.rx_def = re.compile(r"\b(?:def|func|class|sub|function)\s+(\w+)", re.I)
        self.rx_deco = re.compile(r"^\s*@\w+") if plugin.id.startswith("python") else None
        self.triple = plugin.id.startswith("python")
        quotes = [re.escape(q) for q in plugin.string_quotes]
        self.rx_str = re.compile("|".join(f"{q}(?:\\\\.|[^{q}\\\\])*{q}?" for q in quotes)) if quotes else None
        self.line_comments = list(plugin.line_comments)
        self.block = plugin.block_comment

    def highlightBlock(self, text: str):
        self.setCurrentBlockState(0)
        start = 0
        prev = self.previousBlockState()
        # continue multi-line constructs
        if prev in (self.IN_TRIPLE_DQ, self.IN_TRIPLE_SQ):
            q = '"""' if prev == self.IN_TRIPLE_DQ else "'''"
            end = text.find(q)
            if end < 0:
                self.setFormat(0, len(text), self.fmt["string"])
                self.setCurrentBlockState(prev)
                return
            self.setFormat(0, end + 3, self.fmt["string"])
            start = end + 3
        elif prev == self.IN_BLOCK_COMMENT and self.block:
            end = text.find(self.block[1])
            if end < 0:
                self.setFormat(0, len(text), self.fmt["comment"])
                self.setCurrentBlockState(prev)
                return
            self.setFormat(0, end + len(self.block[1]), self.fmt["comment"])
            start = end + len(self.block[1])
        body = text[start:]
        for rx, key in ((self.rx_kw, "keyword"), (self.rx_bi, "builtin"), (self.rx_num, "number")):
            if rx is None:
                continue
            for m in rx.finditer(body):
                self.setFormat(start + m.start(), m.end() - m.start(), self.fmt[key])
        for m in self.rx_def.finditer(body):
            self.setFormat(start + m.start(1), m.end(1) - m.start(1), self.fmt["defname"])
        if self.rx_deco:
            m = self.rx_deco.match(body)
            if m:
                self.setFormat(start + m.start(), m.end() - m.start(), self.fmt["decorator"])
        # strings / comments, scanned left to right so "#" inside strings is not a comment
        i = 0
        while i < len(body):
            ch = body[i]
            if self.triple and body.startswith(('"""', "'''"), i):
                q = body[i:i + 3]
                end = body.find(q, i + 3)
                if end < 0:
                    self.setFormat(start + i, len(body) - i, self.fmt["string"])
                    self.setCurrentBlockState(self.IN_TRIPLE_DQ if q == '"""' else self.IN_TRIPLE_SQ)
                    return
                self.setFormat(start + i, end + 3 - i, self.fmt["string"])
                i = end + 3
                continue
            if self.block and body.startswith(self.block[0], i):
                end = body.find(self.block[1], i + len(self.block[0]))
                if end < 0:
                    self.setFormat(start + i, len(body) - i, self.fmt["comment"])
                    self.setCurrentBlockState(self.IN_BLOCK_COMMENT)
                    return
                self.setFormat(start + i, end + len(self.block[1]) - i, self.fmt["comment"])
                i = end + len(self.block[1])
                continue
            if any(body.startswith(c, i) for c in self.line_comments):
                self.setFormat(start + i, len(body) - i, self.fmt["comment"])
                return
            if ch in self.plugin.string_quotes:
                j = i + 1
                while j < len(body) and body[j] != ch:
                    j += 2 if body[j] == "\\" and ch != "`" else 1
                self.setFormat(start + i, min(j + 1, len(body)) - i, self.fmt["string"])
                i = j + 1
                continue
            i += 1


# =================================================================== completion popup
KIND_COLORS = {"keyword": "#0000C0", "function": "#7B3FA0", "method": "#7B3FA0", "class": "#C07000",
               "variable": "#1F6FBF", "property": "#3A7D3A", "module": "#806040", "control": "#C0392B",
               "event": "#D4A017", "param": "#1F6FBF", "instance": "#1F6FBF", "statement": "#0000C0"}
_ICON_CACHE: dict[str, QIcon] = {}


def kind_icon(kind: str) -> QIcon:
    if kind not in _ICON_CACHE:
        pm = QPixmap(14, 14)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(KIND_COLORS.get(kind, "#808080")))
        p.setPen(Qt.PenStyle.NoPen)
        if kind in ("function", "method"):
            p.drawRoundedRect(1, 3, 12, 8, 2, 2)
        elif kind in ("class",):
            p.drawRect(2, 2, 10, 10)
        elif kind == "keyword":
            p.drawRect(1, 5, 12, 4)
        else:
            p.drawEllipse(2, 2, 10, 10)
        p.setPen(QColor("#ffffff"))
        p.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
        p.drawText(QRect(0, 0, 14, 14), Qt.AlignmentFlag.AlignCenter, (kind[:1] or "?").upper())
        p.end()
        _ICON_CACHE[kind] = QIcon(pm)
    return _ICON_CACHE[kind]


class CompletionPopup(QListWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.editor = editor
        self.setWindowFlags(Qt.WindowType.ToolTip)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFont(QFont("Segoe UI", 9))
        self.setIconSize(QSize(14, 14))
        self.setUniformItemSizes(True)
        self.items = []
        self.prefix_start = 0
        self.itemClicked.connect(lambda _i: self.accept())
        self.detail = QLabel(editor)
        self.detail.setWindowFlags(Qt.WindowType.ToolTip)
        self.detail.setStyleSheet("background:#FFFFE1; border:1px solid #888; padding:3px;")
        self.detail.setFont(QFont("Consolas", 9))
        self.currentRowChanged.connect(self._show_detail)

    def open(self, items, prefix_start: int):
        self.items = items
        self.prefix_start = prefix_start
        self.refilter()

    def prefix(self) -> str:
        cur = self.editor.textCursor()
        block_pos = cur.block().position()
        col = cur.position() - block_pos
        return cur.block().text()[self.prefix_start:col]

    def refilter(self):
        pre = self.prefix()
        low = pre.lower()
        self.clear()
        starts = [c for c in self.items if c.name.lower().startswith(low)]
        contains = [c for c in self.items if low and low in c.name.lower() and c not in starts]
        shown = (starts + contains)[:300]
        if not shown or (len(shown) == 1 and shown[0].name == pre):
            self.hide_all()
            return
        for c in shown:
            it = QListWidgetItem(kind_icon(c.kind), c.name)
            it.setData(Qt.ItemDataRole.UserRole, c)
            it.setToolTip(c.detail or c.kind)
            self.addItem(it)
        self.setCurrentRow(0)
        self._place()
        self.show()
        self._show_detail(0)

    def _place(self):
        ed = self.editor
        cur = ed.textCursor()
        cur.setPosition(cur.block().position() + self.prefix_start)
        r = ed.cursorRect(cur)
        pt = ed.viewport().mapToGlobal(r.bottomLeft())
        width = max(220, min(420, max(QFontMetrics(self.font()).horizontalAdvance(self.item(i).text())
                                      for i in range(min(self.count(), 50))) + 50))
        rows = min(self.count(), 12)
        self.setGeometry(pt.x(), pt.y() + 2, width, rows * (self.sizeHintForRow(0) or 18) + 6)

    def _show_detail(self, row: int):
        it = self.item(row) if row >= 0 else None
        c = it.data(Qt.ItemDataRole.UserRole) if it else None
        if c is None or not c.detail or not self.isVisible():
            self.detail.hide()
            return
        self.detail.setText(c.detail[:300])
        self.detail.adjustSize()
        g = self.geometry()
        self.detail.move(g.right() + 4, g.top() + max(0, self.visualItemRect(it).top()))
        self.detail.show()

    def hide_all(self):
        self.hide()
        self.detail.hide()

    def move_selection(self, step: int):
        n = self.count()
        if n:
            self.setCurrentRow(max(0, min(n - 1, self.currentRow() + step)))

    def accept(self):
        it = self.currentItem()
        if it is None:
            self.hide_all()
            return
        ed = self.editor
        cur = ed.textCursor()
        block_pos = cur.block().position()
        end = cur.position()
        # replace the whole identifier under the cursor
        text = cur.block().text()
        col = end - block_pos
        while col < len(text) and (text[col].isalnum() or text[col] == "_"):
            col += 1
        cur.setPosition(block_pos + self.prefix_start)
        cur.setPosition(block_pos + col, QTextCursor.MoveMode.KeepAnchor)
        cur.insertText(it.text())
        ed.setTextCursor(cur)
        self.hide_all()


# =================================================================== margin
class Margin(QWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.editor = editor
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def sizeHint(self):
        return QSize(self.editor.margin_width(), 0)

    def paintEvent(self, e):
        self.editor.paint_margin(self, e)

    def mousePressEvent(self, e):
        block = self.editor.cursorForPosition(QPoint(5, int(e.position().y()))).block()
        if e.position().x() <= 18:
            self.editor.toggle_breakpoint(block.blockNumber())
        else:
            self.editor.setTextCursor(QTextCursor(block))


# =================================================================== editor
class CodeEditor(QPlainTextEdit):
    breakpointToggled = pyqtSignal(int, bool)     # 0-based line, enabled
    contextMenuAboutToShow = pyqtSignal(object)   # QMenu - the IDE adds its own items
    modificationChanged = pyqtSignal(bool)
    hoverWord = pyqtSignal(str, object)              # word, global QPoint (debugger tips)

    def __init__(self, plugin, path: Path, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.path = path
        self.names: dict[str, str] = {}           # form object names -> control types
        self._breakpoints: set[int] = set()
        self._current: int | None = None
        self.setFont(FONT)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(QFontMetrics(FONT).horizontalAdvance(" ") * 4)
        opt = self.document().defaultTextOption()
        opt.setTextDirection(Qt.LayoutDirection.LeftToRight)   # code lines stay LTR, Arabic runs render RTL
        self.document().setDefaultTextOption(opt)
        self.highlighter = Highlighter(plugin, self.document())
        self.margin = Margin(self)
        self.popup = CompletionPopup(self)
        self.calltip_label = QLabel(self)
        self.calltip_label.setWindowFlags(Qt.WindowType.ToolTip)
        self.calltip_label.setStyleSheet("background:#FFFFE1; border:1px solid #888; padding:3px;")
        self.calltip_label.setFont(QFont("Consolas", 9))
        self._complete_timer = QTimer(self, singleShot=True, interval=120)
        self._complete_timer.timeout.connect(lambda: self.smart_complete(auto=True))
        self.blockCountChanged.connect(self._update_margin_width)
        self.updateRequest.connect(self._update_margin)
        self.cursorPositionChanged.connect(self._highlight_current)
        self.document().modificationChanged.connect(self.modificationChanged.emit)
        self.document().contentsChange.connect(self._on_contents_change)
        QShortcut(QKeySequence("Ctrl+Space"), self, lambda: self.smart_complete(auto=False))
        QShortcut(QKeySequence("Ctrl+Shift+Space"), self, self.show_calltip)
        QShortcut(QKeySequence("Ctrl+/"), self, self.toggle_comment)
        self._update_margin_width()
        self._highlight_current()
        self.setMouseTracking(True)
        self._hover_timer = QTimer(self, singleShot=True, interval=500)
        self._hover_timer.timeout.connect(self._emit_hover)
        self._hover_pos = None

    # ------------------------------------------------------------ QScintilla-like API
    def text(self, line: int | None = None) -> str:
        if line is None:
            return self.toPlainText()
        b = self.document().findBlockByNumber(line)
        return b.text() if b.isValid() else ""

    def setText(self, text: str) -> None:
        """Replace all text (marks the document modified; callers loading a
        file call setModified(False) afterwards)."""
        self._breakpoints.clear()
        self.setPlainText(text)
        self.document().setModified(True)

    def isModified(self) -> bool:
        return self.document().isModified()

    def setModified(self, v: bool) -> None:
        self.document().setModified(v)

    def lines(self) -> int:
        return self.blockCount()

    def getCursorPosition(self) -> tuple[int, int]:
        c = self.textCursor()
        return c.blockNumber(), c.position() - c.block().position()

    def _pos(self, line: int, col: int) -> int:
        b = self.document().findBlockByNumber(max(0, min(line, self.blockCount() - 1)))
        return b.position() + max(0, min(col, len(b.text())))

    def setCursorPosition(self, line: int, col: int) -> None:
        c = self.textCursor()
        c.setPosition(self._pos(line, col))
        self.setTextCursor(c)

    def setSelection(self, l1, c1, l2, c2) -> None:
        c = self.textCursor()
        c.setPosition(self._pos(l1, c1))
        c.setPosition(self._pos(l2, c2), QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(c)

    def replaceSelectedText(self, text: str) -> None:
        self.textCursor().insertText(text)

    def removeSelectedText(self) -> None:
        self.textCursor().removeSelectedText()

    def insert(self, text: str) -> None:
        self.textCursor().insertText(text)

    def beginUndoAction(self):
        self._edit_cursor = self.textCursor()
        self._edit_cursor.beginEditBlock()

    def endUndoAction(self):
        if getattr(self, "_edit_cursor", None) is not None:
            self._edit_cursor.endEditBlock()
            self._edit_cursor = None

    def ensureLineVisible(self, line: int) -> None:
        self.setCursorPosition(line, self.getCursorPosition()[1] if self.getCursorPosition()[0] == line else 0)
        self.centerCursor()

    def set_words(self, extra: list[str]) -> None:   # kept for callers; names come via set_names
        pass

    def set_names(self, names: dict[str, str]) -> None:
        self.names = dict(names)

    # ------------------------------------------------------------ margin
    def margin_width(self) -> int:
        digits = max(3, len(str(self.blockCount())))
        return 20 + QFontMetrics(self.font()).horizontalAdvance("9") * digits + 8

    def _update_margin_width(self, *_):
        self.setViewportMargins(self.margin_width(), 0, 0, 0)

    def _update_margin(self, rect, dy):
        if dy:
            self.margin.scroll(0, dy)
        else:
            self.margin.update(0, rect.y(), self.margin.width(), rect.height())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        self.margin.setGeometry(QRect(cr.left(), cr.top(), self.margin_width(), cr.height()))

    def paint_margin(self, widget, e):
        p = QPainter(widget)
        p.fillRect(e.rect(), QColor(EDITOR_THEME["margin"]))
        p.fillRect(QRect(0, e.rect().top(), 18, e.rect().height()), QColor(EDITOR_THEME["margin_bp"]))
        block = self.firstVisibleBlock()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        fm = QFontMetrics(self.font())
        while block.isValid() and top <= e.rect().bottom():
            h = round(self.blockBoundingRect(block).height())
            n = block.blockNumber()
            if block.isVisible() and top + h >= e.rect().top():
                p.setPen(QColor(EDITOR_THEME["line_number"]))
                p.drawText(0, top, widget.width() - 6, fm.height(), Qt.AlignmentFlag.AlignRight, str(n + 1))
                cy = top + fm.height() // 2
                if n in self._breakpoints:
                    p.setRenderHint(QPainter.RenderHint.Antialiasing)
                    p.setBrush(QColor("#C0392B"))
                    p.setPen(QColor("#8E1B10"))
                    p.drawEllipse(3, cy - 6, 12, 12)
                if n == self._current:
                    p.setRenderHint(QPainter.RenderHint.Antialiasing)
                    p.setBrush(QColor("#FFD700"))
                    p.setPen(QColor("#806000"))
                    p.drawPolygon(QPolygonF([QPointF(3, cy - 4), QPointF(10, cy - 4), QPointF(10, cy - 7),
                                             QPointF(16, cy), QPointF(10, cy + 7), QPointF(10, cy + 4),
                                             QPointF(3, cy + 4)]))
            block = block.next()
            top += h

    # ------------------------------------------------------------ breakpoints / debug line
    def _on_contents_change(self, pos: int, removed: int, added: int):
        """Keep breakpoint lines attached to their code when lines are inserted/removed."""
        if not self._breakpoints:
            return
        doc = self.document()
        first = doc.findBlock(pos).blockNumber()
        old_count = getattr(self, "_last_count", doc.blockCount())
        delta = doc.blockCount() - old_count
        self._last_count = doc.blockCount()
        if delta:
            self._breakpoints = {b if b <= first else max(first, b + delta) for b in self._breakpoints}
            self.margin.update()

    def toggle_breakpoint(self, line: int | None = None) -> None:
        if line is None:
            line = self.getCursorPosition()[0]
        on = line not in self._breakpoints
        if on:      # like VB: a breakpoint on a blank/comment line goes to the next statement
            marks = tuple(self.plugin.line_comments)
            n = line
            while n < self.blockCount() and (not self.text(n).strip() or self.text(n).strip().startswith(marks)):
                n += 1
            if n < self.blockCount():
                line = n
                on = line not in self._breakpoints
        (self._breakpoints.add if on else self._breakpoints.discard)(line)
        self._last_count = self.blockCount()
        self.margin.update()
        self._highlight_current()
        self.breakpointToggled.emit(line, on)

    def breakpoints(self) -> list[int]:
        return sorted(self._breakpoints)

    def set_breakpoints(self, lines: list[int]) -> None:
        self._breakpoints = set(lines)
        self._last_count = self.blockCount()
        self.margin.update()
        self._highlight_current()

    def set_current_line(self, line: int | None) -> None:
        self._current = line
        if line is not None:
            self.setCursorPosition(line, 0)
            self.centerCursor()
        self.margin.update()
        self._highlight_current()

    def goto_line(self, line: int) -> None:
        text = self.text(line)
        self.setCursorPosition(line, len(text))
        if text.strip() == "pass":   # select placeholder so typing replaces it
            start = len(text) - len(text.lstrip())
            self.setSelection(line, start, line, len(text))
        self.centerCursor()
        self.setFocus()

    def _highlight_current(self):
        sels = []

        def line_sel(block_no: int, colour: str):
            s = QTextEdit.ExtraSelection()
            s.format.setBackground(QColor(colour))
            s.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            c = QTextCursor(self.document().findBlockByNumber(block_no))
            s.cursor = c
            return s
        for b in self._breakpoints:
            sels.append(line_sel(b, EDITOR_THEME["breakpoint_line"]))
        if self._current is not None:
            sels.append(line_sel(self._current, EDITOR_THEME["current_stmt"]))
        elif not self.isReadOnly():
            sels.append(line_sel(self.textCursor().blockNumber(), EDITOR_THEME["caret_line"]))
        sels += self._brace_selections()
        self.setExtraSelections(sels)

    def _brace_selections(self):
        doc = self.document()
        pos = self.textCursor().position()
        pairs = {"(": ")", "[": "]", "{": "}"}
        rev = {v: k for k, v in pairs.items()}
        for p in (pos, pos - 1):
            ch = doc.characterAt(p) if p >= 0 else ""
            if ch in pairs or ch in rev:
                step = 1 if ch in pairs else -1
                other = pairs.get(ch) or rev.get(ch)
                depth, q = 0, p
                while 0 <= q < doc.characterCount():
                    c = doc.characterAt(q)
                    if c == ch:
                        depth += 1
                    elif c == other:
                        depth -= 1
                        if depth == 0:
                            out = []
                            for at in (p, q):
                                s = QTextEdit.ExtraSelection()
                                s.format.setBackground(QColor("#B4E4B4"))
                                cur = QTextCursor(doc)
                                cur.setPosition(at)
                                cur.setPosition(at + 1, QTextCursor.MoveMode.KeepAnchor)
                                s.cursor = cur
                                out.append(s)
                            return out
                    q += step
                return []
        return []

    # ------------------------------------------------------------ editing helpers
    def keyPressEvent(self, e):
        k, mods, txt = e.key(), e.modifiers(), e.text()
        if self.popup.isVisible():
            if k in (Qt.Key.Key_Down, Qt.Key.Key_Up, Qt.Key.Key_PageDown, Qt.Key.Key_PageUp):
                self.popup.move_selection({Qt.Key.Key_Down: 1, Qt.Key.Key_Up: -1,
                                           Qt.Key.Key_PageDown: 10, Qt.Key.Key_PageUp: -10}[k])
                return
            if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
                self.popup.accept()
                return
            if k == Qt.Key.Key_Escape:
                self.popup.hide_all()
                return
        if k == Qt.Key.Key_Escape and self.calltip_label.isVisible():
            self.calltip_label.hide()
            return
        if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not mods & Qt.KeyboardModifier.ShiftModifier:
            self._newline_with_indent()
            return
        if k == Qt.Key.Key_Tab and not self.textCursor().hasSelection():
            self.insertPlainText(INDENT)
            return
        if k in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab) and (self.textCursor().hasSelection() or k == Qt.Key.Key_Backtab):
            self._indent_selection(k == Qt.Key.Key_Tab)
            return
        if k == Qt.Key.Key_Backspace and not self.textCursor().hasSelection():
            cur = self.textCursor()
            before = cur.block().text()[:cur.positionInBlock()]
            if before and not before.strip() and len(before) % len(INDENT) == 0:
                for _ in range(len(INDENT)):
                    cur.deletePreviousChar()
                return
        super().keyPressEvent(e)
        if txt:
            self._after_typed(txt)

    def _after_typed(self, ch: str):
        if ch == ".":
            self._complete_timer.start(10)
        elif ch.isalnum() or ch == "_":
            if self.popup.isVisible():
                self.popup.refilter()
            else:
                word = self._word_before()
                if len(word) >= 2 and not self._in_string_or_comment():
                    self._complete_timer.start()
        elif ch in "(,":
            self.calltip_label.hide()
            QTimer.singleShot(60, self.show_calltip)
            self.popup.hide_all()
        elif ch == ")":
            self.calltip_label.hide()
            self.popup.hide_all()
        else:
            self.popup.hide_all()

    def _word_before(self) -> str:
        cur = self.textCursor()
        before = cur.block().text()[:cur.positionInBlock()]
        m = re.search(r"[A-Za-z_]\w*$", before)
        return m.group() if m else ""

    def _in_string_or_comment(self) -> bool:
        cur = self.textCursor()
        before = cur.block().text()[:cur.positionInBlock()]
        if any(c in before for c in self.plugin.line_comments):
            return True
        return any(before.count(q) % 2 == 1 for q in self.plugin.string_quotes)

    def _newline_with_indent(self):
        cur = self.textCursor()
        line = cur.block().text()
        before = line[:cur.positionInBlock()]
        indent = re.match(r"[ \t]*", line).group()
        stripped = before.rstrip()
        opens = (stripped.endswith(":") if self.plugin.id.startswith("python") else
                 bool(re.match(r"^\s*(func|def|class|if|elseif|else|for|while|switch|on|other|try|catch|"
                               r"sub|function|do)\b", stripped, re.I)))
        if opens:
            indent += INDENT
        cur.insertText("\n" + indent)
        self.setTextCursor(cur)
        self.popup.hide_all()

    def _indent_selection(self, indent: bool):
        cur = self.textCursor()
        start, end = sorted((cur.anchor(), cur.position()))
        doc = self.document()
        b, last = doc.findBlock(start), doc.findBlock(max(start, end - 1 if end > start else end))
        cur.beginEditBlock()
        while b.isValid():
            c = QTextCursor(b)
            if indent:
                c.insertText(INDENT)
            else:
                n = len(b.text()) - len(b.text().lstrip(" "))
                c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, min(4, n))
                c.removeSelectedText()
            if b == last:
                break
            b = b.next()
        cur.endEditBlock()

    def toggle_comment(self):
        mark = (self.plugin.line_comments or ["#"])[0]
        cur = self.textCursor()
        start, end = sorted((cur.anchor(), cur.position()))
        doc = self.document()
        first, last = doc.findBlock(start), doc.findBlock(end)
        blocks = []
        b = first
        while b.isValid():
            blocks.append(b)
            if b == last:
                break
            b = b.next()
        all_commented = all(bl.text().lstrip().startswith(mark) for bl in blocks if bl.text().strip())
        cur.beginEditBlock()
        for bl in blocks:
            t = bl.text()
            if not t.strip():
                continue
            ind = len(t) - len(t.lstrip())
            c = QTextCursor(bl)
            c.movePosition(QTextCursor.MoveOperation.Right, n=ind)
            if all_commented:
                n = len(mark) + (1 if t[ind + len(mark):ind + len(mark) + 1] == " " else 0)
                c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, n)
                c.removeSelectedText()
            else:
                c.insertText(mark + " ")
        cur.endEditBlock()

    # ------------------------------------------------------------ IntelliSense
    def smart_complete(self, auto: bool = False) -> None:
        if self.isReadOnly():
            return
        line, col = self.getCursorPosition()
        try:
            items = self.plugin.completions(self.text(), line, col, self.path, self.names)
        except Exception:  # noqa: BLE001 - completion must never break typing
            items = []
        if not items:
            self.popup.hide_all()
            return
        word = self._word_before()
        self.popup.open(items, col - len(word))
        if not auto and self.popup.count() == 1:
            self.popup.accept()

    def show_calltip(self) -> None:
        line, col = self.getCursorPosition()
        try:
            tip = self.plugin.calltip(self.text(), line, col, self.path, self.names)
        except Exception:  # noqa: BLE001
            tip = ""
        if not tip:
            self.calltip_label.hide()
            return
        self.calltip_label.setText(tip)
        self.calltip_label.adjustSize()
        r = self.cursorRect()
        pt = self.viewport().mapToGlobal(r.topLeft())
        self.calltip_label.move(pt.x(), pt.y() - self.calltip_label.height() - 2)
        self.calltip_label.show()

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        self._hover_pos = e.position().toPoint()
        self._hover_timer.start()

    def _emit_hover(self):
        if self._hover_pos is None:
            return
        cur = self.cursorForPosition(self._hover_pos)
        text = cur.block().text()
        col = cur.positionInBlock()
        for m in re.finditer(r"[A-Za-z_][\w.]*", text):
            if m.start() <= col < m.end():
                word = text[m.start():col] + re.match(r"\w*", text[col:]).group()
                self.hoverWord.emit(word.rstrip('.'), self.viewport().mapToGlobal(self._hover_pos))
                return

    def focusOutEvent(self, e):
        self.popup.hide_all()
        self.calltip_label.hide()
        super().focusOutEvent(e)

    def contextMenuEvent(self, e):
        m = self.createStandardContextMenu()
        if m is None:
            return
        self.contextMenuAboutToShow.emit(m)
        m.exec(e.globalPos())


def monaco_available() -> bool:
    import importlib.util
    if importlib.util.find_spec("PyQt6.QtWebEngineWidgets") is None:
        return False
    return (Path(__file__).resolve().parent / "web" / "monaco" / "vs" / "loader.js").exists()


def use_monaco() -> bool:
    from PyQt6.QtCore import QSettings
    engine = QSettings("RADIDE", "RADIDE").value("editor/engine", "monaco")
    return engine == "monaco" and monaco_available()


def make_editor(plugin, path: Path, parent=None):
    """Monaco (VS Code editor) when available, else the built-in editor."""
    if use_monaco():
        from .monaco_editor import MonacoEditor
        return MonacoEditor(plugin, path, parent)
    return CodeEditor(plugin, path, parent)


class CodeView(QWidget):
    """Editor with VB's two dropdowns: (object) and (event)."""

    def __init__(self, doc: FormDocument, plugin, path: Path, parent=None):
        super().__init__(parent)
        self.doc, self.plugin = doc, plugin
        self.objects = QComboBox()
        self.events = QComboBox()
        for cb in (self.objects, self.events):
            cb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            cb.setMinimumContentsLength(12)
        self.editor = make_editor(plugin, path)
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(self.objects, 1)
        top.addWidget(self.events, 1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        lay.addLayout(top)
        lay.addWidget(self.editor, 1)
        self.objects.currentIndexChanged.connect(self._fill_events)
        self.events.activated.connect(self._on_event)
        doc.structureChanged.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        current = self.objects.currentData()
        self.objects.blockSignals(True)
        self.objects.clear()
        self.objects.addItem(f"{self.doc.form.name} (Form)", "")
        for c in self.doc.form.controls:
            self.objects.addItem(c.name, c.name)
        idx = self.objects.findData(current)
        self.objects.setCurrentIndex(max(0, idx))
        self.objects.blockSignals(False)
        self._fill_events()
        names = {self.doc.form.name: "Form"}
        names.update({c.name: c.type for c in self.doc.form.controls})
        self.editor.set_names(names)

    def _owner(self):
        name = self.objects.currentData()
        return self.doc.form.find(name) if name else None

    def _fill_events(self, *_):
        self.events.clear()
        self.events.addItem("(Declarations)")
        for ev in self.plugin.events_for(self._owner()):
            self.events.addItem(ev)

    def _on_event(self, idx: int) -> None:
        if idx > 0:
            self.doc.eventRequested.emit(self._owner(), self.events.itemText(idx))
