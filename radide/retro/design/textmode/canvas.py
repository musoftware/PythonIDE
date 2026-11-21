"""CellCanvas - a Qt view of a CellBuffer (zoom, cell <-> pixel mapping, blink). Base of the designer canvas,
the ANSI editor canvas and the Test Run window."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from .buffer import CellBuffer
from .glyphs import CELL, render_image


class CellCanvas(QWidget):
    zoomChanged = pyqtSignal(float)

    def __init__(self, buf: CellBuffer | None = None, parent=None):
        super().__init__(parent)
        self.setProperty("i18n_skip", True)
        self.buf = buf or CellBuffer()
        self.cw, self.ch = CELL
        self.zoom = 1.0
        self.ice = False
        self.blink_on = True
        self.show_grid = False
        self._img: QImage | None = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._blink = QTimer(self)
        self._blink.timeout.connect(self._toggle_blink)
        self._blink.start(530)

    # ------------------------------------------------------------ buffer
    def set_buffer(self, buf: CellBuffer) -> None:
        size_changed = (buf.cols, buf.rows) != (self.buf.cols, self.buf.rows)
        self.buf = buf
        self._img = None
        if size_changed:
            self.updateGeometry()
            self.resize(self.sizeHint())
        self.update()

    def refresh(self, region: tuple[int, int, int, int] | None = None) -> None:
        if region is not None and self._img is not None:
            render_image(self.buf, self.cw, self.ch, self.blink_on, self.ice, region, self._img)
        else:
            self._img = None
        self.update()

    def image(self) -> QImage:
        if self._img is None or self._img.width() != self.buf.cols * self.cw or \
                self._img.height() != self.buf.rows * self.ch:
            self._img = render_image(self.buf, self.cw, self.ch, self.blink_on, self.ice)
        return self._img

    def _toggle_blink(self) -> None:
        if self.ice or not any(a & 0x80 for a in self.buf.attrs):
            if not self.blink_on:
                self.blink_on = True
                self._img = None
                self.update()
            return
        self.blink_on = not self.blink_on
        self._img = None
        self.update()

    # ------------------------------------------------------------ geometry
    def set_zoom(self, z: float) -> None:
        self.zoom = max(0.5, min(4.0, z))
        self.updateGeometry()
        self.resize(self.sizeHint())
        self.update()
        self.zoomChanged.emit(self.zoom)

    def sizeHint(self) -> QSize:
        return QSize(int(self.buf.cols * self.cw * self.zoom), int(self.buf.rows * self.ch * self.zoom))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def cell_at(self, pos: QPoint) -> tuple[int, int]:
        x = int(pos.x() / (self.cw * self.zoom))
        y = int(pos.y() / (self.ch * self.zoom))
        return max(0, min(self.buf.cols - 1, x)), max(0, min(self.buf.rows - 1, y))

    def cell_rect(self, x: int, y: int, w: int = 1, h: int = 1) -> QRect:
        cw, ch = self.cw * self.zoom, self.ch * self.zoom
        return QRect(int(x * cw), int(y * ch), int(w * cw), int(h * ch))

    # ------------------------------------------------------------ painting
    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        img = self.image()
        p.drawImage(QRect(0, 0, int(img.width() * self.zoom), int(img.height() * self.zoom)), img)
        if self.show_grid:
            pen = QPen(QColor(255, 255, 255, 28))
            p.setPen(pen)
            for x in range(self.buf.cols + 1):
                r = self.cell_rect(x, 0)
                p.drawLine(r.left(), 0, r.left(), self.height())
            for y in range(self.buf.rows + 1):
                r = self.cell_rect(0, y)
                p.drawLine(0, r.top(), self.width(), r.top())
        self.paint_overlay(p)
        p.end()

    def paint_overlay(self, p: QPainter) -> None:
        """Subclasses draw selections, handles, cursors."""
