"""Toolbox: pick a control and click (or drag) it onto the form, VB style."""
from __future__ import annotations

from PyQt6.QtCore import QMimeData, QObject, QPointF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QFont, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import QListWidget, QListWidgetItem

from .controls import CONTROL_TYPES

MIME = "application/x-radide-control"
POINTER = "Pointer"


class ToolState(QObject):
    changed = pyqtSignal(object)   # str | None

    def __init__(self):
        super().__init__()
        self.current: str | None = None

    def set(self, tool: str | None) -> None:
        self.current = tool
        self.changed.emit(tool)


TOOL_STATE = ToolState()


def control_icon(type_name: str) -> QIcon:
    """Small drawn icons, so the app needs no image files."""
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#3c3c3c"))
    p.setPen(pen)
    f = QFont("Segoe UI", 7, QFont.Weight.Bold)
    p.setFont(f)
    if type_name == POINTER:
        p.setBrush(QColor("#ffffff"))
        p.drawPolygon(QPolygonF([QPointF(6, 2), QPointF(6, 16), QPointF(9, 13),
                                 QPointF(12, 18), QPointF(14, 17), QPointF(11, 12), QPointF(15, 12)]))
    elif type_name == "Button":
        p.setBrush(QColor("#e8e8e8"))
        p.drawRoundedRect(1, 5, 18, 10, 2, 2)
        p.drawText(1, 5, 18, 10, Qt.AlignmentFlag.AlignCenter, "ab")
    elif type_name == "Label":
        p.setFont(QFont("Times New Roman", 12, QFont.Weight.Bold))
        p.drawText(0, 0, 20, 20, Qt.AlignmentFlag.AlignCenter, "A")
    elif type_name == "TextBox":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(1, 5, 18, 10)
        p.drawText(3, 5, 16, 10, Qt.AlignmentFlag.AlignVCenter, "ab|")
    elif type_name == "CheckBox":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(4, 4, 12, 12)
        p.setPen(QPen(QColor("#1e8f1e"), 2))
        p.drawPolyline(QPolygonF([QPointF(6, 10), QPointF(9, 13), QPointF(14, 6)]))
    elif type_name == "RadioButton":
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(3, 3, 14, 14)
        p.setBrush(QColor("#1e5fbf"))
        p.drawEllipse(7, 7, 6, 6)
    elif type_name == "ListBox":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(2, 2, 16, 16)
        for y in (6, 10, 14):
            p.drawLine(5, y, 15, y)
    elif type_name == "ComboBox":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(1, 5, 18, 10)
        p.setBrush(QColor("#d0d0d0"))
        p.drawRect(12, 5, 7, 10)
        p.drawText(12, 5, 7, 10, Qt.AlignmentFlag.AlignCenter, "▾")
    elif type_name == "PictureBox":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(2, 3, 16, 14)
        p.setBrush(QColor("#3c9b3c"))
        p.drawPolygon(QPolygonF([QPointF(3, 16), QPointF(8, 9), QPointF(12, 14), QPointF(17, 16)]))
        p.setBrush(QColor("#f0c419"))
        p.drawEllipse(12, 5, 4, 4)
    elif type_name == "ProgressBar":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(1, 6, 18, 8)
        p.fillRect(2, 7, 10, 7, QColor("#2fb12f"))
    elif type_name == "NumericUpDown":
        p.setBrush(QColor("#ffffff"))
        p.drawRect(1, 4, 18, 12)
        p.drawText(2, 4, 10, 12, Qt.AlignmentFlag.AlignCenter, "12")
        p.drawLine(13, 4, 13, 16)
        p.drawLine(13, 10, 19, 10)
    elif type_name == "TrackBar":
        p.drawLine(2, 10, 18, 10)
        p.setBrush(QColor("#4a78c2"))
        p.drawRect(8, 5, 4, 10)
    elif type_name == "Panel":
        p.setPen(QPen(QColor("#3c3c3c"), 1, Qt.PenStyle.DashLine))
        p.drawRect(2, 3, 16, 14)
    elif type_name == "GroupBox":
        p.drawRect(2, 6, 16, 12)
        p.fillRect(4, 3, 9, 6, QColor("#f0f0f0"))
        p.drawText(4, 1, 12, 9, Qt.AlignmentFlag.AlignLeft, "xy")
    elif type_name == "Timer":
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(2, 2, 16, 16)
        p.drawLine(10, 10, 10, 5)
        p.drawLine(10, 10, 14, 10)
    elif type_name == "MenuStrip":
        p.setBrush(QColor("#dfe8f6"))
        p.drawRect(1, 3, 18, 5)
        p.setBrush(QColor("#ffffff"))
        p.drawRect(3, 8, 10, 10)
        for y in (11, 14):
            p.drawLine(5, y, 11, y)
    p.end()
    return QIcon(pm)


class Toolbox(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(20, 20))
        self.setDragEnabled(True)
        self.setSpacing(1)
        for name in [POINTER, *CONTROL_TYPES]:
            it = QListWidgetItem(control_icon(name), name)
            it.setData(Qt.ItemDataRole.UserRole, name)
            self.addItem(it)
        self.setCurrentRow(0)
        self.currentItemChanged.connect(self._on_current)
        TOOL_STATE.changed.connect(self._on_tool_reset)

    def _on_current(self, item, _prev):
        if item is None:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        TOOL_STATE.set(None if name == POINTER else name)

    def _on_tool_reset(self, tool):
        if tool is None and self.currentRow() != 0:
            self.blockSignals(True)
            self.setCurrentRow(0)
            self.blockSignals(False)

    def startDrag(self, actions):
        item = self.currentItem()
        if item is None:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if name == POINTER:
            return
        mime = QMimeData()
        mime.setData(MIME, name.encode())
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(item.icon().pixmap(20, 20))
        drag.exec(Qt.DropAction.CopyAction)
