"""Tile palette (pick the tile to paint) and the Import Tileset dialog of the scene designer."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from .. import theme

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"


class TilePalette(QWidget):
    """The tiles of a tileset image in a grid; click picks the tile to paint."""
    tileSelected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pm: QPixmap | None = None
        self.tw = self.th = 32
        self.current = 0
        self.zoom = 1
        self.setMouseTracking(True)
        self._hover = -1

    def set_tileset(self, pm: QPixmap | None, tw: int, th: int) -> None:
        self.pm, self.tw, self.th = pm, max(1, tw), max(1, th)
        self.zoom = 2 if max(self.tw, self.th) <= 20 else 1
        self.updateGeometry()
        self.adjustSize()
        self.update()

    def grid(self) -> tuple[int, int]:
        if self.pm is None:
            return 0, 0
        return max(1, self.pm.width() // self.tw), max(1, self.pm.height() // self.th)

    def count(self) -> int:
        c, r = self.grid()
        return c * r

    def sizeHint(self) -> QSize:
        if self.pm is None:
            return QSize(160, 60)
        c, r = self.grid()
        return QSize(c * self.tw * self.zoom + 1, r * self.th * self.zoom + 1)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def _index_at(self, pos) -> int:
        if self.pm is None:
            return -1
        c, r = self.grid()
        col, row = int(pos.x() // (self.tw * self.zoom)), int(pos.y() // (self.th * self.zoom))
        return row * c + col if 0 <= col < c and 0 <= row < r else -1

    def select(self, index: int) -> None:
        self.current = index
        self.update()
        self.tileSelected.emit(index)

    def mousePressEvent(self, e) -> None:
        i = self._index_at(e.position())
        if i >= 0:
            self.select(i)

    def mouseMoveEvent(self, e) -> None:
        i = self._index_at(e.position())
        if i != self._hover:
            self._hover = i
            self.setToolTip(f"Tile {i}" if i >= 0 else "")
            self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.color("stage")))
        if self.pm is None:
            p.setPen(QColor(theme.color("muted")))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       "No tileset.\nImport one with 'Tileset...'")
            return
        c, r = self.grid()
        tw, th, z = self.tw, self.th, self.zoom
        p.drawPixmap(QRectF(0, 0, c * tw * z, r * th * z), self.pm, QRectF(0, 0, c * tw, r * th))
        p.setPen(QPen(QColor(0, 0, 0, 70), 1))
        for i in range(c + 1):
            p.drawLine(i * tw * z, 0, i * tw * z, r * th * z)
        for j in range(r + 1):
            p.drawLine(0, j * th * z, c * tw * z, j * th * z)
        for idx, col in ((self._hover, QColor(255, 255, 255)), (self.current, QColor(theme.color("accent")))):
            if 0 <= idx < c * r:
                p.setPen(QPen(col, 2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(QRectF((idx % c) * tw * z + 1, (idx // c) * th * z + 1, tw * z - 2, th * z - 2))


class TilesetDialog(QDialog):
    """Import Tileset: image + tile size, with a live grid preview."""

    def __init__(self, parent=None, path: str = "", tile_w: int = 32, tile_h: int = 32, asset_id: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Import Tileset")
        self.resize(560, 480)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        row = QHBoxLayout()
        self.path = QLineEdit(path)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        form.addRow("Image:", row)
        self.asset_id = QLineEdit(asset_id)
        self.asset_id.setPlaceholderText("from the file name")
        form.addRow("Name (id):", self.asset_id)
        self.tw, self.th = QSpinBox(), QSpinBox()
        for s, v in ((self.tw, tile_w), (self.th, tile_h)):
            s.setRange(1, 1024)
            s.setValue(v)
            s.setSuffix(" px")
            s.valueChanged.connect(self._preview)
        sz = QHBoxLayout()
        sz.addWidget(self.tw)
        sz.addWidget(QLabel("x"))
        sz.addWidget(self.th)
        sz.addStretch(1)
        form.addRow("Tile size:", sz)
        lay.addLayout(form)
        self.info = theme.role(QLabel(""), "muted")
        lay.addWidget(self.info)
        self.palette = TilePalette()
        sa = QScrollArea()
        sa.setWidget(self.palette)
        sa.setWidgetResizable(False)
        lay.addWidget(sa, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.path.editingFinished.connect(self._preview)
        self._preview()

    def _browse(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Tileset image", str(Path(self.path.text()).parent), IMAGE_FILTER)
        if f:
            self.path.setText(f)
            self._preview()

    def _preview(self) -> None:
        pm = QPixmap(self.path.text()) if self.path.text() else QPixmap()
        if pm.isNull():
            self.palette.set_tileset(None, self.tw.value(), self.th.value())
            self.info.setText("Choose a tileset image (tiles side by side in a grid).")
            return
        self.palette.set_tileset(pm, self.tw.value(), self.th.value())
        c, r = self.palette.grid()
        self.info.setText(f"{pm.width()} x {pm.height()} px  -  {c} x {r} = {c * r} tiles")

    def _ok(self) -> None:
        if not Path(self.path.text()).is_file():
            self.info.setText("The image file does not exist.")
            return
        self.accept()

    def values(self) -> tuple[str, int, int, str]:
        return self.path.text(), self.tw.value(), self.th.value(), self.asset_id.text().strip()
