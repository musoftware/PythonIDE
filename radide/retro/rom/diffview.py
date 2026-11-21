"""Compare two files: side-by-side hex views that scroll together, the differing bytes in red, a list of the
differences and Next / Previous Difference."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QSplitter,
                             QVBoxLayout, QWidget)

from .buffer import HexBuffer
from .hexview import HexView
from .patches import eq_run


def diff_ranges(a: bytes, b: bytes, limit: int = 200_000) -> list[tuple[int, int]]:
    """(start, end) of the runs where *a* and *b* differ (the longer file's tail is one difference)."""
    out: list[tuple[int, int]] = []
    n = min(len(a), len(b))
    i = 0
    while i < n and len(out) < limit:
        i += eq_run(a, b, i, n)
        if i >= n:
            break
        j = i
        while j < n and a[j] != b[j]:
            j += 1
        out.append((i, j))
        i = j
    if len(a) != len(b) and len(out) < limit:
        out.append((n, max(len(a), len(b))))
    return out


class CompareView(QWidget):
    """A document tab comparing two files (read-only)."""
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal()

    def __init__(self, left, right, parent=None):
        super().__init__(parent)
        self.left_path, self.right_path = Path(left), Path(right)
        self.path = self.right_path
        a, b = self.left_path.read_bytes(), self.right_path.read_bytes()
        self.ranges = diff_ranges(a, b)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.summary = QLabel()
        b_prev = QPushButton("Previous Difference")
        b_prev.clicked.connect(lambda: self.goto_diff(-1))
        b_next = QPushButton("Next Difference")
        b_next.clicked.connect(lambda: self.goto_diff(1))
        bar.addWidget(self.summary, 1)
        bar.addWidget(b_prev)
        bar.addWidget(b_next)
        lay.addLayout(bar)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.views = []
        for path, data in ((self.left_path, a), (self.right_path, b)):
            box = QWidget()
            v = QVBoxLayout(box)
            v.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(f"<b>{path.name}</b>  ({len(data):,} bytes)")
            lbl.setToolTip(str(path))
            view = HexView(HexBuffer(data, path))
            view.read_only = True
            view.set_diff_ranges(self.ranges)
            v.addWidget(lbl)
            v.addWidget(view)
            split.addWidget(box)
            self.views.append(view)
        self.list = QListWidget()
        self.list.setMaximumWidth(260)
        for s, e in self.ranges[:5000]:
            it = QListWidgetItem(f"0x{s:08X}  {e - s:,} byte{'s' if e - s != 1 else ''}")
            it.setData(Qt.ItemDataRole.UserRole, s)
            self.list.addItem(it)
        self.list.currentItemChanged.connect(self._on_item)
        split.addWidget(self.list)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        lay.addWidget(split, 1)
        l_v, r_v = self.views
        self._syncing = False
        l_v.verticalScrollBar().valueChanged.connect(lambda v: self._sync(r_v, v))
        r_v.verticalScrollBar().valueChanged.connect(lambda v: self._sync(l_v, v))
        l_v.cursorMoved.connect(lambda o: self._sync_cursor(r_v, o))
        r_v.cursorMoved.connect(lambda o: self._sync_cursor(l_v, o))
        total = sum(e - s for s, e in self.ranges)
        if not self.ranges:
            self.summary.setText("The files are identical.")
        else:
            self.summary.setText(f"{len(self.ranges):,} difference(s), {total:,} byte(s) differ"
                                 + (f"; sizes {len(a):,} / {len(b):,}" if len(a) != len(b) else ""))
        self._index = -1

    def _sync(self, other: HexView, value: int) -> None:
        if self._syncing:
            return
        self._syncing = True
        other.verticalScrollBar().setValue(value)
        self._syncing = False

    def _sync_cursor(self, other: HexView, off: int) -> None:
        if self._syncing:
            return
        self._syncing = True
        other.cursor = min(off, len(other.buf))
        other.viewport().update()
        self._syncing = False

    def goto_diff(self, step: int) -> None:
        if not self.ranges:
            return
        cur = self.views[0].cursor
        if step > 0:
            idx = next((i for i, (s, _e) in enumerate(self.ranges) if s > cur), 0)
        else:
            prev = [i for i, (s, _e) in enumerate(self.ranges) if s < cur]
            idx = prev[-1] if prev else len(self.ranges) - 1
        self._show(idx)

    def _show(self, idx: int) -> None:
        s, e = self.ranges[idx]
        self._index = idx
        for v in self.views:
            v.set_cursor(min(s, len(v.buf)))
        if idx < self.list.count():
            self.list.blockSignals(True)
            self.list.setCurrentRow(idx)
            self.list.blockSignals(False)

    def _on_item(self, it, _prev) -> None:
        if it is not None:
            self._show(self.list.row(it))

    # document protocol of the hex feature
    def is_modified(self) -> bool:
        return False

    def save(self) -> bool:
        return True

    def edit_op(self, op: str) -> None:
        if op == "copy":
            self.views[0].copy() if self.views[0].hasFocus() else self.views[1].copy()


__all__ = ["CompareView", "diff_ranges"]
