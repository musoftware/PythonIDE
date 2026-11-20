"""Toolbox: pick a control and click (or drag) it onto the form, VB style."""
from __future__ import annotations

from PyQt6.QtCore import QMimeData, QObject, QPointF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QFont, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import QListWidget, QListWidgetItem

from .controls import CONTROL_TYPES
from .mobile.controls import MOBILE_CONTROL_TYPES
from .mobile.render import mobile_tool_icon

MIME = "application/x-radide-control"
POINTER = "Pointer"
MOBILE_HEADER = "Mobile"                 # Toolbox group captions shown for phone forms
CLASSIC_HEADER = "Common Controls"


class ToolState(QObject):
    changed = pyqtSignal(object)   # str | None

    def __init__(self):
        super().__init__()
        self.current: str | None = None

    def set(self, tool: str | None) -> None:
        self.current = tool
        self.changed.emit(tool)

    # mobile forms (CONTRACTS 10.1): the shown designer says whether it is a phone form
    modeChanged = pyqtSignal(bool, object)      # mobile, enabled control types (set) | None
    mobile = False
    supported = None

    def set_mode(self, mobile: bool, supported=None) -> None:
        mobile = bool(mobile)
        supported = set(supported) if (mobile and supported) else None
        if mobile == self.mobile and supported == self.supported:
            return
        self.mobile, self.supported = mobile, supported
        self.modeChanged.emit(mobile, supported)

    # designer profile of the shown form's language plugin (``plugin.designer_profile``), e.g. a
    # WinForms form of an opened Visual Studio project: {"labels": {type: shown name},
    # "allowed": set of control types | None}.  None = the IDE's own control names.
    profileChanged = pyqtSignal(object)
    profile = None

    def set_profile(self, profile) -> None:
        if profile is self.profile:
            return
        self.profile = profile
        self.profileChanged.emit(profile)


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
    if type_name in MOBILE_CONTROL_TYPES:
        p.end()
        return mobile_tool_icon(type_name)
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
    else:
        _draw_new_icon(p, type_name)
    p.end()
    return QIcon(pm)


def _draw_new_icon(p: QPainter, type_name: str) -> None:
    """Icons of the controls added with the second control set (tabs, trees, grids, dialogs...)."""
    white, dark = QColor("#ffffff"), QColor("#3c3c3c")
    if type_name == "TabControl":
        p.setBrush(white)
        p.drawRect(2, 6, 16, 12)
        p.setBrush(QColor("#dfe8f6"))
        p.drawRect(2, 2, 7, 4)
        p.setBrush(white)
        p.drawRect(9, 3, 6, 3)
    elif type_name == "TreeView":
        p.drawLine(4, 4, 4, 15)
        p.drawLine(4, 9, 9, 9)
        p.drawLine(4, 15, 9, 15)
        p.setBrush(QColor("#f0c419"))
        for x, y in ((2, 2), (9, 7), (9, 13)):
            p.drawRect(x, y, 5, 4)
    elif type_name == "ListView":
        p.setBrush(white)
        p.drawRect(1, 2, 18, 16)
        p.fillRect(2, 3, 17, 4, QColor("#dfe8f6"))
        for y in (10, 14):
            p.fillRect(3, y - 1, 3, 3, QColor("#4a78c2"))
            p.drawLine(8, y, 17, y)
    elif type_name == "DataGridView":
        p.setBrush(white)
        p.drawRect(1, 2, 18, 16)
        p.fillRect(2, 3, 17, 4, QColor("#dfe8f6"))
        for x in (7, 13):
            p.drawLine(x, 2, x, 18)
        for y in (7, 12):
            p.drawLine(1, y, 19, y)
    elif type_name == "DateTimePicker":
        p.setBrush(white)
        p.drawRect(2, 4, 16, 14)
        p.fillRect(3, 5, 15, 4, QColor("#d9542b"))
        for x in (5, 9, 13):
            for y in (11, 15):
                p.fillRect(x, y - 1, 2, 2, dark)
    elif type_name == "LinkLabel":
        f = QFont("Segoe UI", 9)
        f.setUnderline(True)
        p.setFont(f)
        p.setPen(QColor("#0066cc"))
        p.drawText(0, 0, 20, 20, Qt.AlignmentFlag.AlignCenter, "A")
    elif type_name == "StatusBar":
        p.setBrush(white)
        p.drawRect(1, 2, 18, 16)
        p.setBrush(QColor("#d4d0c8"))
        p.drawRect(1, 13, 18, 5)
        p.drawLine(12, 13, 12, 18)
    elif type_name == "ToolStrip":
        p.setBrush(QColor("#dfe8f6"))
        p.drawRect(1, 5, 18, 10)
        p.setBrush(QColor("#4a78c2"))
        p.drawRect(3, 7, 5, 6)
        p.setBrush(QColor("#2fb12f"))
        p.drawRect(10, 7, 5, 6)
    elif type_name in ("OpenFileDialog", "FolderBrowserDialog"):
        p.setBrush(QColor("#f0c419"))
        p.drawPolygon(QPolygonF([QPointF(2, 6), QPointF(8, 6), QPointF(10, 8), QPointF(18, 8),
                                 QPointF(18, 17), QPointF(2, 17)]))
        if type_name == "OpenFileDialog":
            p.setBrush(white)
            p.drawRect(6, 2, 8, 9)
    elif type_name == "SaveFileDialog":
        p.setBrush(QColor("#4a78c2"))
        p.drawRect(3, 3, 14, 14)
        p.setBrush(white)
        p.drawRect(6, 3, 8, 5)
        p.drawRect(5, 11, 10, 6)
    elif type_name == "ColorDialog":
        for i, c in enumerate(("#d9542b", "#2fb12f", "#4a78c2", "#f0c419")):
            p.setBrush(QColor(c))
            p.drawRect(2 + (i % 2) * 8, 2 + (i // 2) * 8, 7, 7)
    elif type_name == "FontDialog":
        p.setFont(QFont("Times New Roman", 11, QFont.Weight.Bold))
        p.drawText(0, 0, 13, 20, Qt.AlignmentFlag.AlignCenter, "A")
        p.setFont(QFont("Segoe UI", 7))
        p.drawText(9, 4, 11, 16, Qt.AlignmentFlag.AlignCenter, "a")
    elif type_name == "ActiveX":
        p.setBrush(white)
        p.drawRect(2, 2, 16, 16)
        p.setPen(QColor("#d9542b"))
        p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        p.drawText(2, 2, 16, 16, Qt.AlignmentFlag.AlignCenter, "OCX")


class Toolbox(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(20, 20))
        self.setDragEnabled(True)
        self.setSpacing(1)
        # names are elided to the dock's width - never a horizontal scroll bar
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setUniformItemSizes(True)
        mobile = [n for n in CONTROL_TYPES if n in MOBILE_CONTROL_TYPES]
        classic = [n for n in CONTROL_TYPES if n not in MOBILE_CONTROL_TYPES]
        self._headers: dict[str, QListWidgetItem] = {}
        for name in [POINTER, MOBILE_HEADER, *mobile, CLASSIC_HEADER, *classic]:
            if name in (MOBILE_HEADER, CLASSIC_HEADER):          # group caption (mobile designers only)
                it = QListWidgetItem(name)
                f = it.font()
                f.setBold(True)
                it.setFont(f)
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setSizeHint(QSize(10, 22))
                self._headers[name] = it
                self.addItem(it)
                continue
            it = QListWidgetItem(control_icon(name), name)
            it.setData(Qt.ItemDataRole.UserRole, name)
            ctype = CONTROL_TYPES.get(name)
            it.setToolTip(f"{name}: {ctype.description}" if ctype is not None and ctype.description else name)
            it.setSizeHint(QSize(10, 24))          # the row is as wide as the list, the text elides
            self.addItem(it)
        self.setCurrentRow(0)
        self.currentItemChanged.connect(self._on_current)
        TOOL_STATE.changed.connect(self._on_tool_reset)
        TOOL_STATE.modeChanged.connect(self._on_mode)
        TOOL_STATE.profileChanged.connect(lambda _p: self._on_mode(TOOL_STATE.mobile, TOOL_STATE.supported))
        self._on_mode(TOOL_STATE.mobile, TOOL_STATE.supported)

    def _on_mode(self, mobile: bool, supported) -> None:
        """Desktop forms: the classic controls only.  Phone forms: the Mobile group first and the
        Windows-only classic controls greyed (not available in mobile apps)."""
        from .mobile.controls import supported_controls
        allowed = set(supported) if supported else supported_controls(None)
        for row in range(self.count()):
            it = self.item(row)
            name = it.data(Qt.ItemDataRole.UserRole)
            if name is None:                                   # group caption
                it.setHidden(not mobile)
                continue
            if name == POINTER:
                continue
            ctype = CONTROL_TYPES.get(name)
            desc = f"{name}: {ctype.description}" if ctype is not None and ctype.description else name
            if name in MOBILE_CONTROL_TYPES:
                it.setHidden(not mobile)
                ok = True
            else:
                it.setHidden(False)
                ok = not mobile or name in allowed
            it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled
                        if ok else Qt.ItemFlag.NoItemFlags)
            it.setToolTip(desc if ok else f"{name}: Windows only - not available in mobile apps.")
            prof = TOOL_STATE.profile if not mobile else None
            label = (prof.get("labels") or {}).get(name, name) if prof else name
            if it.text() != label:
                it.setText(label)
            if prof and prof.get("allowed") is not None and name not in prof["allowed"]:
                it.setHidden(True)                 # e.g. no such control in Windows Forms
        if TOOL_STATE.current is not None and (TOOL_STATE.current not in CONTROL_TYPES or
                                               (mobile and TOOL_STATE.current not in allowed) or
                                               (not mobile and TOOL_STATE.current in MOBILE_CONTROL_TYPES)):
            TOOL_STATE.set(None)

    def _on_current(self, item, _prev):
        if item is None or item.data(Qt.ItemDataRole.UserRole) is None:
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
