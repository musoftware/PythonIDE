"""Shared Qt pieces of the retro graphics editors: document base class, hex spin box, palette widgets."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPen
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QGridLayout, QMessageBox, QSpinBox, QToolButton,
                             QVBoxLayout, QWidget)

from . import palettes


def block_image(block, colors, aspect: int = 1) -> QImage:
    """QImage of a pixel block (-1 = transparent / outside the data, drawn dark grey)."""
    h = len(block)
    w = len(block[0]) if h else 0
    buf = bytearray(max(1, w * aspect) * max(1, h) * 4)
    n = len(colors)
    i = 0
    for row in block:
        for v in row:
            r, g, b = colors[v % n] if v >= 0 else (40, 40, 40)
            for _a in range(aspect):
                buf[i:i + 4] = bytes((b, g, r, 255))
                i += 4
    img = QImage(bytes(buf), max(1, w * aspect), max(1, h), max(1, w * aspect) * 4, QImage.Format.Format_ARGB32)
    return img.copy()


class HexSpin(QSpinBox):
    """Offset / address editor shown in hex (0x...)."""

    def __init__(self, maximum: int = 0x7FFFFFFF, parent=None):
        super().__init__(parent)
        self.setDisplayIntegerBase(16)
        self.setPrefix("0x")
        self.setRange(0, maximum)
        self.setAccelerated(True)
        self.setMinimumWidth(96)

    def textFromValue(self, v: int) -> str:
        return f"{v:X}"


class RetroDoc(QWidget):
    """A document tab: ``retro_path``, ``save()``, ``is_modified()``, ``maybe_close()``, ``reload_from_disk()``."""
    modifiedChanged = pyqtSignal(bool)
    kind = "Retro"

    def __init__(self, win=None, parent=None):
        super().__init__(parent)
        self.win = win
        self.retro_path: Path | None = None
        self._modified = False

    def is_modified(self) -> bool:
        return self._modified

    def set_modified(self, on: bool) -> None:
        if on != self._modified:
            self._modified = on
            self.modifiedChanged.emit(on)

    def title(self) -> str:
        return (self.retro_path.name if self.retro_path else self.kind)

    def save(self) -> bool:                       # overridden
        return False

    def maybe_close(self) -> bool:
        if not self.is_modified():
            return True
        r = QMessageBox.question(self, "Retro Graphics", f"Save changes to {self.title()}?",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Cancel:
            return False
        if r in (QMessageBox.StandardButton.Save, QMessageBox.StandardButton.Yes):
            return bool(self.save())
        return True

    def reload_from_disk(self) -> None:          # overridden
        pass

    def log(self, text: str) -> None:
        try:
            if self.win is not None:
                self.win.log(text)
        except Exception:  # noqa: BLE001
            pass

    def notify_written(self, path) -> None:
        from .. import filebus
        filebus.file_changed(self.win, path, source=self)


class SystemPaletteDialog(QDialog):
    """Pick one colour of a system palette (grid of swatches)."""

    def __init__(self, system: str, current: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Color")
        self.value = current
        colors = palettes.palette(system)
        lay = QVBoxLayout(self)
        grid = QGridLayout()
        grid.setSpacing(1)
        per_row = 16 if len(colors) >= 64 else 8 if len(colors) >= 16 else len(colors)
        if system in ("a2600ntsc", "a2600pal"):
            per_row = 8                           # one hue per row, 8 luminances
        for i, (r, g, b) in enumerate(colors):
            btn = QToolButton()
            btn.setFixedSize(22, 22)
            btn.setStyleSheet(f"background: rgb({r},{g},{b}); border: {'2px solid red' if i == current else '1px solid #333'};")
            btn.setToolTip(f"${i:02X}" + (f"  (COLU value ${palettes.a2600_color_byte(i):02X})"
                                           if system.startswith("a2600") else "") + f"  #{r:02X}{g:02X}{b:02X}")
            btn.clicked.connect(lambda _c, i=i: self._pick(i))
            grid.addWidget(btn, i // per_row, i % per_row)
        lay.addLayout(grid)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _pick(self, i: int) -> None:
        self.value = i
        self.accept()


class PaletteBar(QWidget):
    """The colour slots of the current format; click = drawing colour, double-click = choose system colour
    (or any RGB colour when the slots are free colours, e.g. a GBC / SNES palette read from the ROM)."""
    colorPicked = pyqtSignal(int)
    slotsChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.system = "nes"
        self.slots: list[int] = [0, 1, 2, 3]
        self.custom: list[tuple[int, int, int]] | None = None     # free RGB colours instead of system indices
        self.current = 1
        self.setMinimumHeight(30)
        self.setMouseTracking(True)

    def set_slots(self, system: str, slots: list[int]) -> None:
        self.system = system
        self.slots = list(slots)
        self.custom = None
        self.current = min(self.current, len(self.slots) - 1)
        self.update()

    def set_custom(self, colors) -> None:
        """Free RGB colours (one per slot)."""
        self.custom = [tuple(int(v) for v in c[:3]) for c in colors]
        self.slots = list(range(len(self.custom)))
        self.current = min(self.current, len(self.slots) - 1)
        self.update()

    def set_slot(self, i: int, value) -> None:
        """Change slot *i* (a system palette index, or an (r, g, b) tuple for free colours) and emit slotsChanged."""
        if self.custom is not None:
            self.custom[i] = tuple(int(v) for v in value[:3])
        else:
            self.slots[i] = int(value)
        self.slotsChanged.emit()
        self.update()

    def colors(self) -> list[tuple[int, int, int]]:
        if self.custom is not None:
            return list(self.custom)
        pal = palettes.palette(self.system)
        return [pal[s % len(pal)] for s in self.slots]

    def _cell(self) -> int:
        return max(14, min(30, (self.width() - 4) // max(1, len(self.slots))))

    def sizeHint(self) -> QSize:
        return QSize(len(self.slots) * 30 + 4, 34)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        c = self._cell()
        for i, (r, g, b) in enumerate(self.colors()):
            rect = QRect(2 + i * c, 2, c - 2, 26)
            p.fillRect(rect, QColor(r, g, b))
            p.setPen(QPen(QColor("#ff3030") if i == self.current else QColor("#555"), 2 if i == self.current else 1))
            p.drawRect(rect)
            p.setPen(QColor(255, 255, 255) if (r + g + b) < 380 else QColor(0, 0, 0))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(i))
        p.end()

    def slot_at(self, x: int) -> int:
        i = (x - 2) // self._cell()
        return i if 0 <= i < len(self.slots) else -1

    def mousePressEvent(self, e) -> None:
        i = self.slot_at(int(e.position().x()))
        if i >= 0:
            self.current = i
            self.colorPicked.emit(i)
            self.update()

    def mouseDoubleClickEvent(self, e) -> None:
        i = self.slot_at(int(e.position().x()))
        if i < 0:
            return
        if self.custom is not None:
            from PyQt6.QtWidgets import QColorDialog
            c = QColorDialog.getColor(QColor(*self.custom[i]), self, "Choose Color")
            if c.isValid():
                self.set_slot(i, (c.red(), c.green(), c.blue()))
            return
        dlg = SystemPaletteDialog(self.system, self.slots[i], self)
        if dlg.exec():
            self.slots[i] = dlg.value
            self.slotsChanged.emit()
            self.update()
