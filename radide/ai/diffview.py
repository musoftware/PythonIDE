"""Review AI changes before they touch a file (docs/CONTRACTS.md 9.3 - shared by AI Chat, the
AI editor commands, the Agent Manager and the Web Chats).

    from radide.ai.diffview import DiffReview, MultiDiffReview, apply_file_change

    text = DiffReview(parent, path, old_text, new_text).exec()    # accepted text or None (rejected)
    files = MultiDiffReview(parent, [(path, old, new), ...]).exec()
    #   -> {path: accepted text (None = delete the file)} of the accepted files, or None (cancelled)
    ok = apply_file_change(win, path, new_text)     # review + write to disk + update an open editor

The side-by-side view aligns both versions, colours removed / added lines and lists every change
("hunk") with a check box: unticked hunks keep the old lines.  "Edit result" makes the proposed
text editable before accepting it.  Colours follow radide/theme.py (and theme.changed)."""
from __future__ import annotations

import difflib
import os
from pathlib import Path

from PyQt6.QtCore import QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QKeySequence, QPainter, QShortcut, QTextCursor, QTextFormat
from PyQt6.QtWidgets import (QApplication, QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
                             QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QSplitter,
                             QStackedWidget, QTextEdit, QToolButton, QVBoxLayout, QWidget)

try:
    from .. import theme
except Exception:  # noqa: BLE001 - usable outside the IDE too
    theme = None


# ============================================================================ text helpers
def _norm(text: str | None) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def read_text(path) -> tuple[str, str, str]:
    """-> (text with \\n newlines, newline of the file, encoding).  A missing file is ("", "\\n", "utf-8")."""
    p = Path(path)
    if not p.is_file():
        return "", "\n", "utf-8"
    raw = p.read_bytes()
    for enc in ("utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    nl = "\r\n" if "\r\n" in text else "\n"
    return _norm(text), nl, enc


def write_text(path, text: str, newline: str = "\n", encoding: str = "utf-8") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = _norm(text)
    if newline != "\n":
        data = data.replace("\n", newline)
    with open(p, "w", encoding=encoding, newline="") as f:
        f.write(data)


def _lines(text: str) -> list[str]:
    return _norm(text).splitlines(keepends=True)


class Hunk:
    __slots__ = ("tag", "i1", "i2", "j1", "j2", "accepted")

    def __init__(self, tag, i1, i2, j1, j2):
        self.tag, self.i1, self.i2, self.j1, self.j2 = tag, i1, i2, j1, j2
        self.accepted = True

    @property
    def removed(self) -> int:
        return self.i2 - self.i1

    @property
    def added(self) -> int:
        return self.j2 - self.j1


def diff_hunks(old: str, new: str) -> tuple[list[str], list[str], list]:
    """-> (old lines, new lines, opcodes [(tag, i1, i2, j1, j2, Hunk|None)])."""
    a, b = _lines(old), _lines(new)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    ops = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        ops.append((tag, i1, i2, j1, j2, None if tag == "equal" else Hunk(tag, i1, i2, j1, j2)))
    return a, b, ops


def merge(a: list[str], b: list[str], ops) -> str:
    """The old text with the accepted hunks applied."""
    out = []
    for tag, i1, i2, j1, j2, h in ops:
        if h is None:
            out.extend(a[i1:i2])
        elif h.accepted:
            out.extend(b[j1:j2])
        else:
            out.extend(a[i1:i2])
    return "".join(out)


def unified(old: str, new: str, path: str = "file") -> str:
    return "".join(difflib.unified_diff(_lines(old), _lines(new), f"a/{path}", f"b/{path}"))


# ============================================================================ colours
def _t(token: str, fallback: str) -> str:
    try:
        return theme.color(token) if theme is not None else fallback
    except Exception:  # noqa: BLE001
        return fallback


def _mix(a: str, b: str, f: float) -> QColor:
    ca, cb = QColor(a), QColor(b)
    return QColor(round(ca.red() + (cb.red() - ca.red()) * f), round(ca.green() + (cb.green() - ca.green()) * f),
                  round(ca.blue() + (cb.blue() - ca.blue()) * f))


def colors() -> dict:
    base, text = _t("base", "#FFFFFF"), _t("text", "#000000")
    dark = bool(theme.is_dark()) if theme is not None else False
    f = 0.30 if dark else 0.20
    return {
        "base": QColor(base), "text": QColor(text), "muted": QColor(_t("muted", "#5A5A5A")),
        "add": _mix(base, _t("success", "#087F23"), f), "del": _mix(base, _t("error", "#C42B1C"), f),
        "add_off": _mix(base, _t("success", "#087F23"), f / 3), "del_off": _mix(base, _t("error", "#C42B1C"), f / 3),
        "filler": _mix(base, _t("mid", "#B8B8B0"), 0.25), "gutter": QColor(_t("alt_base", "#F5F5F0")),
        "current": _mix(base, _t("accent", "#316AC5"), 0.35), "border": QColor(_t("border", "#A0AFC3")),
    }


def _mono() -> QFont:
    f = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    for fam in ("Cascadia Mono", "Consolas"):
        if fam in QFontDatabase.families():
            f = QFont(fam)
            break
    f.setPointSize(10)
    return f


# ============================================================================ one pane (with line numbers)
class _Gutter(QWidget):
    def __init__(self, pane: "DiffPane"):
        super().__init__(pane)
        self.pane = pane

    def sizeHint(self):
        return QSize(self.pane.gutter_width(), 0)

    def paintEvent(self, e):
        self.pane.paint_gutter(e)


class DiffPane(QPlainTextEdit):
    """A read-only text pane whose rows map to file line numbers (None = filler row)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(_mono())
        self.numbers: list[int | None] = []
        self.marks: list[str] = []          # per row: "", "+", "-", "~" (filler)
        self.gutter = _Gutter(self)
        self.blockCountChanged.connect(lambda _n: self._margins())
        self.updateRequest.connect(self._on_update)
        self._margins()

    def gutter_width(self) -> int:
        n = max([x for x in self.numbers if x] or [1])
        return 14 + self.fontMetrics().horizontalAdvance("9" * max(3, len(str(n)))) + 14

    def _margins(self):
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def _on_update(self, rect, dy):
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        self.gutter.setGeometry(QRect(cr.left(), cr.top(), self.gutter_width(), cr.height()))

    def paint_gutter(self, e):
        c = colors()
        p = QPainter(self.gutter)
        p.fillRect(e.rect(), c["gutter"])
        block = self.firstVisibleBlock()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        fm = self.fontMetrics()
        w = self.gutter.width()
        while block.isValid() and top <= e.rect().bottom():
            h = round(self.blockBoundingRect(block).height())
            row = block.blockNumber()
            if block.isVisible() and bottom_visible(top, h, e.rect()):
                num = self.numbers[row] if row < len(self.numbers) else None
                mark = self.marks[row] if row < len(self.marks) else ""
                p.setPen(c["muted"])
                if num:
                    p.drawText(0, top, w - 16, fm.height(), Qt.AlignmentFlag.AlignRight, str(num))
                if mark in "+-" and mark:
                    p.setPen(c["text"])
                    p.drawText(w - 13, top, 10, fm.height(), Qt.AlignmentFlag.AlignCenter, mark)
            block = block.next()
            top += h
        p.end()


def bottom_visible(top: int, h: int, rect) -> bool:
    return top + h >= rect.top()


# ============================================================================ the diff widget
class DiffWidget(QWidget):
    """Side-by-side review of one file.  result_text() is the old text with the ticked hunks
    applied (or the edited text when "Edit result" was used)."""

    changed = pyqtSignal()

    def __init__(self, path: str = "", old_text: str | None = "", new_text: str | None = "", parent=None):
        super().__init__(parent)
        self.path = str(path or "")
        self.old = _norm(old_text)
        self.deleting = new_text is None
        self.new = "" if new_text is None else _norm(new_text)
        self.is_new_file = bool(old_text is None or (not self.old and self.path and not Path(self.path).exists()))
        self._editing = False
        self._rows_old: list[int] = []        # hunk index -> first row
        self._build()
        self.set_texts(self.old, self.new)
        if theme is not None:
            try:
                theme.changed.connect(self._restyle)
            except Exception:  # noqa: BLE001
                pass

    # ---------------------------------------------------------- UI
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        top = QHBoxLayout()
        top.setContentsMargins(4, 2, 4, 0)
        self.title = QLabel()
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        f = self.title.font()
        f.setBold(True)
        self.title.setFont(f)
        self.stats = QLabel()
        self.prev_btn = QToolButton(text="Previous", toolTip="Previous change (Shift+F7)")
        self.next_btn = QToolButton(text="Next", toolTip="Next change (F7)")
        self.prev_btn.clicked.connect(lambda: self.goto_hunk(-1))
        self.next_btn.clicked.connect(lambda: self.goto_hunk(+1))
        self.all_btn = QToolButton(text="Accept all", toolTip="Tick every change")
        self.none_btn = QToolButton(text="Reject all", toolTip="Untick every change (keeps the old text)")
        self.all_btn.clicked.connect(lambda: self.set_all(True))
        self.none_btn.clicked.connect(lambda: self.set_all(False))
        self.edit_box = QCheckBox("Edit result")
        self.edit_box.setToolTip("Edit the proposed text before accepting it")
        self.edit_box.toggled.connect(self._toggle_edit)
        top.addWidget(self.title)
        top.addWidget(self.stats)
        top.addStretch(1)
        for w in (self.prev_btn, self.next_btn, self.all_btn, self.none_btn, self.edit_box):
            top.addWidget(w)
        lay.addLayout(top)

        self.hunks = QListWidget()
        self.hunks.setMaximumHeight(110)
        self.hunks.itemChanged.connect(self._hunk_toggled)
        self.hunks.currentRowChanged.connect(lambda r: r >= 0 and self._scroll_to_hunk(r))
        self.left, self.right = DiffPane(), DiffPane()
        self.editor = QPlainTextEdit()
        self.editor.setFont(_mono())
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.right_stack = QStackedWidget()
        self.right_stack.addWidget(self.right)
        self.right_stack.addWidget(self.editor)
        left_box, right_box = QWidget(), QWidget()
        for box, lbl, pane in ((left_box, "Current", self.left), (right_box, "Proposed", self.right_stack)):
            v = QVBoxLayout(box)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(1)
            cap = QLabel(lbl)
            if theme is not None:
                theme.role(cap, "muted")
            v.addWidget(cap)
            v.addWidget(pane)
            if lbl == "Current":
                self.left_caption = cap
            else:
                self.right_caption = cap
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(left_box)
        split.addWidget(right_box)
        split.setChildrenCollapsible(False)
        vsplit = QSplitter(Qt.Orientation.Vertical)
        vsplit.addWidget(self.hunks)
        vsplit.addWidget(split)
        vsplit.setStretchFactor(1, 1)
        lay.addWidget(vsplit, 1)
        self._sync = False
        self.left.verticalScrollBar().valueChanged.connect(lambda v: self._sync_scroll(self.right, v))
        self.right.verticalScrollBar().valueChanged.connect(lambda v: self._sync_scroll(self.left, v))
        self.left.horizontalScrollBar().valueChanged.connect(
            lambda v: self.right.horizontalScrollBar().setValue(v))
        self.right.horizontalScrollBar().valueChanged.connect(
            lambda v: self.left.horizontalScrollBar().setValue(v))
        QShortcut(QKeySequence("F7"), self, activated=lambda: self.goto_hunk(+1))
        QShortcut(QKeySequence("Shift+F7"), self, activated=lambda: self.goto_hunk(-1))

    def _sync_scroll(self, other, v):
        if self._sync:
            return
        self._sync = True
        other.verticalScrollBar().setValue(v)
        self._sync = False

    # ---------------------------------------------------------- content
    def set_texts(self, old: str, new: str):
        self.old, self.new = _norm(old), _norm(new)
        self.a, self.b, self.ops = diff_hunks(self.old, self.new)
        self.hunk_list = [op[5] for op in self.ops if op[5] is not None]
        self._render()

    def _render(self):
        lrows, rrows, lnum, rnum, lmark, rmark = [], [], [], [], [], []
        self._hunk_rows = []
        for tag, i1, i2, j1, j2, h in self.ops:
            if h is not None:
                self._hunk_rows.append(len(lrows))
            n = max(i2 - i1, j2 - j1)
            for k in range(n):
                li, rj = i1 + k, j1 + k
                if tag == "equal":
                    lrows.append(self.a[li]), rrows.append(self.b[rj])
                    lnum.append(li + 1), rnum.append(rj + 1)
                    lmark.append(""), rmark.append("")
                    continue
                if li < i2:
                    lrows.append(self.a[li]), lnum.append(li + 1), lmark.append("-")
                else:
                    lrows.append("\n"), lnum.append(None), lmark.append("~")
                if rj < j2:
                    rrows.append(self.b[rj]), rnum.append(rj + 1), rmark.append("+")
                else:
                    rrows.append("\n"), rnum.append(None), rmark.append("~")
        self._row_hunk = []
        hi = -1
        for tag, i1, i2, j1, j2, h in self.ops:
            n = max(i2 - i1, j2 - j1)
            if h is not None:
                hi += 1
            self._row_hunk.extend([hi if h is not None else -1] * n)
        for pane, rows, nums, marks in ((self.left, lrows, lnum, lmark), (self.right, rrows, rnum, rmark)):
            pane.numbers, pane.marks = nums, marks
            txt = "".join(r if r.endswith("\n") else r + "\n" for r in rows)
            pane.setPlainText(txt[:-1] if txt.endswith("\n") else txt)
            pane._margins()
        self._fill_hunks()
        self._colour()
        self._update_labels()

    def _fill_hunks(self):
        self.hunks.blockSignals(True)
        self.hunks.clear()
        for i, h in enumerate(self.hunk_list):
            if h.tag == "insert":
                where = f"after line {h.i1}" if h.i1 else "at the start"
            else:
                where = f"line {h.i1 + 1}" if h.removed == 1 else f"lines {h.i1 + 1}-{h.i2}"
            sample = (self.b[h.j1] if h.added else self.a[h.i1]).strip()
            if len(sample) > 70:
                sample = sample[:67] + "..."
            it = QListWidgetItem(f"{i + 1}.  -{h.removed} +{h.added}   {where}    {sample}")
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if h.accepted else Qt.CheckState.Unchecked)
            self.hunks.addItem(it)
        self.hunks.blockSignals(False)
        self.hunks.setVisible(bool(self.hunk_list))

    def _colour(self):
        c = colors()
        for pane, side in ((self.left, "-"), (self.right, "+")):
            sels = []
            block = pane.document().firstBlock()
            while block.isValid():
                row = block.blockNumber()
                mark = pane.marks[row] if row < len(pane.marks) else ""
                if mark:
                    hi = self._row_hunk[row] if row < len(self._row_hunk) else -1
                    on = hi < 0 or self.hunk_list[hi].accepted
                    if mark == "~":
                        col = c["filler"]
                    elif mark == "-":
                        col = c["del"] if on else c["del_off"]
                    else:
                        col = c["add"] if on else c["add_off"]
                    s = QTextEdit.ExtraSelection()
                    s.format.setBackground(col)
                    s.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                    s.cursor = QTextCursor(block)
                    sels.append(s)
                block = block.next()
            pane.setExtraSelections(sels)
            pane.gutter.update()

    def _update_labels(self):
        name = Path(self.path).name if self.path else "(text)"
        state = " (new file)" if self.is_new_file else " (delete file)" if self.deleting else ""
        self.title.setText(name + state)
        self.title.setToolTip(self.path)
        add = sum(h.added for h in self.hunk_list if h.accepted)
        rem = sum(h.removed for h in self.hunk_list if h.accepted)
        on = sum(1 for h in self.hunk_list if h.accepted)
        if not self.hunk_list:
            self.stats.setText("  no changes")
        else:
            self.stats.setText(f"  {on} of {len(self.hunk_list)} changes ticked,  +{add}  -{rem}")
        for w in (self.prev_btn, self.next_btn, self.all_btn, self.none_btn):
            w.setEnabled(bool(self.hunk_list) and not self._editing)

    def _restyle(self, *_a):
        self._colour()

    # ---------------------------------------------------------- hunks
    def _hunk_toggled(self, it: QListWidgetItem):
        row = self.hunks.row(it)
        if 0 <= row < len(self.hunk_list):
            self.hunk_list[row].accepted = it.checkState() == Qt.CheckState.Checked
            self._colour()
            self._update_labels()
            self.changed.emit()

    def set_all(self, on: bool):
        for h in self.hunk_list:
            h.accepted = on
        self._fill_hunks()
        self._colour()
        self._update_labels()
        self.changed.emit()

    def set_hunk(self, index: int, on: bool):
        self.hunk_list[index].accepted = on
        self._fill_hunks()
        self._colour()
        self._update_labels()
        self.changed.emit()

    def _scroll_to_hunk(self, i: int):
        if not (0 <= i < len(self._hunk_rows)):
            return
        row = self._hunk_rows[i]
        for pane in (self.left, self.right):
            cur = QTextCursor(pane.document().findBlockByNumber(row))
            pane.setTextCursor(cur)
            pane.centerCursor()

    def goto_hunk(self, step: int):
        if not self.hunk_list:
            return
        r = self.hunks.currentRow()
        r = (0 if step > 0 else len(self.hunk_list) - 1) if r < 0 else (r + step) % len(self.hunk_list)
        self.hunks.setCurrentRow(r)
        self._scroll_to_hunk(r)

    # ---------------------------------------------------------- edit mode
    def _toggle_edit(self, on: bool):
        if on:
            self.editor.setPlainText(merge(self.a, self.b, self.ops))
            self.right_stack.setCurrentWidget(self.editor)
            self.right_caption.setText("Proposed (editing - untick 'Edit result' to see the diff again)")
            self.hunks.setEnabled(False)
            self._editing = True
        else:
            edited = self.editor.toPlainText()
            self._editing = False
            self.right_stack.setCurrentWidget(self.right)
            self.right_caption.setText("Proposed")
            self.hunks.setEnabled(True)
            self.set_texts(self.old, edited)
        self._update_labels()
        self.changed.emit()

    # ---------------------------------------------------------- result
    def result_text(self) -> str:
        if self._editing:
            return _norm(self.editor.toPlainText())
        return merge(self.a, self.b, self.ops)

    def has_changes(self) -> bool:
        return self.result_text() != self.old or (self.is_new_file and not self.deleting)

    def accepted_count(self) -> int:
        return sum(1 for h in self.hunk_list if h.accepted)


# ============================================================================ dialogs
def _parent_window(parent):
    return parent if isinstance(parent, QWidget) else QApplication.activeWindow()


class DiffReview(QDialog):
    """DiffReview(parent, path, old_text, new_text).exec() -> accepted text, or None when rejected.
    old_text None = a new file; new_text None = the file would be deleted (exec returns "" on accept)."""

    def __init__(self, parent, path, old_text, new_text, title: str | None = None, accept_text: str = "Accept",
                 note: str = ""):
        super().__init__(_parent_window(parent))
        self.setWindowTitle(title or f"Review changes - {Path(str(path or 'text')).name}")
        self.resize(1100, 720)
        self.setSizeGripEnabled(True)
        lay = QVBoxLayout(self)
        if note:
            n = QLabel(note)
            n.setWordWrap(True)
            if theme is not None:
                theme.role(n, "banner")
            lay.addWidget(n)
        self.view = DiffWidget(str(path or ""), old_text, new_text)
        lay.addWidget(self.view, 1)
        self.buttons = QDialogButtonBox()
        self.accept_btn = self.buttons.addButton(accept_text, QDialogButtonBox.ButtonRole.AcceptRole)
        self.reject_btn = self.buttons.addButton("Reject", QDialogButtonBox.ButtonRole.RejectRole)
        self.accept_btn.setDefault(True)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)
        self.view.changed.connect(self._update)
        self._update()

    def _update(self):
        n = self.view.accepted_count()
        tot = len(self.view.hunk_list)
        if self.view.deleting:
            self.accept_btn.setText("Delete file")
        elif self.view._editing or tot == 0:
            self.accept_btn.setText("Accept")
        else:
            self.accept_btn.setText("Accept" if n == tot else f"Accept {n} of {tot}")

    def result_text(self) -> str:
        return "" if self.view.deleting else self.view.result_text()

    def exec(self):  # noqa: A003 - returns the accepted text instead of an int
        r = super().exec()
        return self.result_text() if r == QDialog.DialogCode.Accepted else None

    @staticmethod
    def ask(parent, path, old_text, new_text, **kw):
        return DiffReview(parent, path, old_text, new_text, **kw).exec()


class MultiDiffReview(QDialog):
    """Review several files: MultiDiffReview(parent, [(path, old_or_None, new_or_None), ...]).exec()
    -> {path: accepted text, or None = delete} for the ticked files, or None when cancelled."""

    def __init__(self, parent, changes, title: str = "Review changes", note: str = ""):
        super().__init__(_parent_window(parent))
        self.setWindowTitle(title)
        self.resize(1200, 760)
        self.setSizeGripEnabled(True)
        self.changes = [(str(p), o, n) for p, o, n in changes]
        self._views: dict[int, DiffWidget] = {}
        lay = QVBoxLayout(self)
        if note:
            lbl = QLabel(note)
            lbl.setWordWrap(True)
            if theme is not None:
                theme.role(lbl, "banner")
            lay.addWidget(lbl)
        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.files = QListWidget()
        root = os.path.commonpath([os.path.dirname(p) or "." for p, _o, _n in self.changes]) if self.changes else ""
        for p, o, n in self.changes:
            kind = "new" if o is None or (not o and not Path(p).exists()) else "deleted" if n is None else "modified"
            try:
                shown = os.path.relpath(p, root) if root else p
            except ValueError:
                shown = p
            it = QListWidgetItem(f"{shown}   [{kind}]")
            it.setToolTip(p)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked)
            self.files.addItem(it)
        row = QHBoxLayout()
        b_all, b_none = QPushButton("Tick all"), QPushButton("Untick all")
        b_all.clicked.connect(lambda: self._tick(True))
        b_none.clicked.connect(lambda: self._tick(False))
        row.addWidget(b_all)
        row.addWidget(b_none)
        lv.addWidget(QLabel(f"{len(self.changes)} file(s)"))
        lv.addWidget(self.files, 1)
        lv.addLayout(row)
        self.stack = QStackedWidget()
        split.addWidget(left)
        split.addWidget(self.stack)
        split.setStretchFactor(1, 1)
        split.setSizes([260, 900])
        lay.addWidget(split, 1)
        self.buttons = QDialogButtonBox()
        self.accept_btn = self.buttons.addButton("Accept ticked files", QDialogButtonBox.ButtonRole.AcceptRole)
        self.buttons.addButton("Reject all", QDialogButtonBox.ButtonRole.RejectRole)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)
        self.files.currentRowChanged.connect(self._show)
        self.files.itemChanged.connect(lambda _i: self._update())
        if self.changes:
            self.files.setCurrentRow(0)
        self._update()

    def view(self, i: int) -> DiffWidget:
        v = self._views.get(i)
        if v is None:
            p, o, n = self.changes[i]
            v = DiffWidget(p, o, n)
            self._views[i] = v
            self.stack.addWidget(v)
        return v

    def _show(self, i: int):
        if 0 <= i < len(self.changes):
            self.stack.setCurrentWidget(self.view(i))

    def _tick(self, on: bool):
        for i in range(self.files.count()):
            self.files.item(i).setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)

    def _update(self):
        n = sum(1 for i in range(self.files.count()) if self.files.item(i).checkState() == Qt.CheckState.Checked)
        self.accept_btn.setText(f"Accept {n} file(s)")
        self.accept_btn.setEnabled(n > 0)

    def result(self) -> dict:  # noqa: D401
        out = {}
        for i, (p, o, n) in enumerate(self.changes):
            if self.files.item(i).checkState() != Qt.CheckState.Checked:
                continue
            if n is None:
                out[p] = None
                continue
            v = self._views.get(i)
            out[p] = v.result_text() if v is not None else _norm(n)
        return out

    def exec(self):  # noqa: A003
        r = super().exec()
        return self.result() if r == QDialog.DialogCode.Accepted else None


# ============================================================================ IDE helpers
def _widget_path(w) -> str:
    for obj in (w, getattr(w, "editor", None)):
        v = getattr(obj, "path", None) if obj is not None else None
        if v and not callable(v):
            return str(v)
    return ""


def _same(a, b) -> bool:
    try:
        return os.path.normcase(str(Path(a).resolve())) == os.path.normcase(str(Path(b).resolve()))
    except OSError:
        return False


def find_open_editor(win, path):
    """The editor widget of an open tab showing *path* (or None)."""
    tabs = getattr(win, "tabs", None)
    seen = []
    if tabs is not None:
        seen += [tabs.widget(i) for i in range(tabs.count())]
    for attr in ("modviews", "codeviews"):
        seen += list((getattr(win, attr, None) or {}).values())
    for w in seen:
        ed = getattr(w, "editor", None)
        if ed is None:
            continue
        p = _widget_path(w)
        if p and _same(p, path):
            return ed
    return None


def editor_text(ed) -> str:
    for name in ("toPlainText", "text"):
        f = getattr(ed, name, None)
        if callable(f):
            try:
                return _norm(str(f()))
            except Exception:  # noqa: BLE001
                continue
    return ""


def set_editor_text(ed, text: str, saved: bool = True) -> None:
    """Replace an editor's whole text as one undoable step (Monaco and the built-in editor)."""
    old = editor_text(ed)
    text = _norm(text)
    if old != text:
        lines = old.split("\n")
        try:
            ed.beginUndoAction()
        except Exception:  # noqa: BLE001
            pass
        try:
            ed.setSelection(0, 0, len(lines) - 1, len(lines[-1]))
            ed.replaceSelectedText(text)
        except Exception:  # noqa: BLE001
            ed.setText(text)
        try:
            ed.endUndoAction()
        except Exception:  # noqa: BLE001
            pass
    if saved:
        try:
            ed.setModified(False)
        except Exception:  # noqa: BLE001
            pass


def apply_file_change(win, path, new_text: str | None, review: bool = True, parent=None, title: str | None = None,
                      note: str = "") -> bool:
    """Show the diff of *path* (its open editor's text, else the file on disk) against new_text,
    then write the accepted text to disk and update the open editor.  Returns True when written."""
    p = Path(path)
    ed = find_open_editor(win, p) if win is not None else None
    disk, nl, enc = read_text(p)
    old = editor_text(ed) if ed is not None else disk
    exists = p.exists()
    if review:
        res = DiffReview(parent or win, str(p), old if exists or ed is not None else None, new_text,
                         title=title, note=note).exec()
        if res is None:
            return False
    else:
        res = "" if new_text is None else _norm(new_text)
    if new_text is None:
        try:
            p.unlink()
        except OSError as e:
            QMessageBox.warning(parent or win, "Delete file", f"Cannot delete {p}:\n{e}")
            return False
        if win is not None:
            _refresh_tree(win)
        return True
    try:
        write_text(p, res, nl, "utf-8" if enc in ("latin-1",) else enc)
    except OSError as e:
        QMessageBox.warning(parent or win, "Apply changes", f"Cannot write {p}:\n{e}")
        return False
    if ed is not None:
        set_editor_text(ed, res, saved=True)
    if win is not None:
        try:
            win.statusBar().showMessage(f"Applied changes to {p.name}", 5000)
        except Exception:  # noqa: BLE001
            pass
        if not exists:
            _refresh_tree(win)
    return True


def apply_file_changes(win, changes, review: bool = True, parent=None, title: str = "Review changes",
                       note: str = "") -> list[str]:
    """Several files at once ([(path, new_text_or_None)]) -> the paths written / deleted."""
    items = []
    for path, new in changes:
        p = Path(path)
        ed = find_open_editor(win, p) if win is not None else None
        disk, _nl, _enc = read_text(p)
        old = editor_text(ed) if ed is not None else (disk if p.exists() else None)
        items.append((str(p), old, new))
    if review:
        res = MultiDiffReview(parent or win, items, title=title, note=note).exec()
        if res is None:
            return []
    else:
        res = {p: (None if n is None else _norm(n)) for p, _o, n in items}
    done = []
    for p, text in res.items():
        if apply_file_change(win, p, text, review=False, parent=parent):
            done.append(p)
    return done


def _refresh_tree(win):
    def later():
        for name in ("refresh_solution", "_fill_solution"):
            f = getattr(win, name, None)
            if callable(f):
                try:
                    f()
                except Exception:  # noqa: BLE001
                    pass
                return
    QTimer.singleShot(0, later)


__all__ = ["DiffReview", "MultiDiffReview", "DiffWidget", "DiffPane", "apply_file_change", "apply_file_changes",
           "diff_hunks", "merge", "unified", "read_text", "write_text", "find_open_editor", "editor_text",
           "set_editor_text", "colors"]
