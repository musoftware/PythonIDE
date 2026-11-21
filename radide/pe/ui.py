"""PE / MFC Resource Workbench (a tab in the IDE; radide/features/pe_workbench.py opens it).

Tabs: Resources (tree + editors: dialog designer, menu, string table, accelerators, version, icons /
bitmaps, text, toolbar, dialog init, hex), Code (functions, disassembly with names / strings / callers,
Edit Instruction - same size or smaller, Ghidra pseudo-C when Ghidra is installed), MFC Events (message
maps per class, retarget / remove / add-in-free-slot), Patches (list + revert) and Info.

Every save writes a new file (default <name>_edited.exe); a file that is replaced gets a .bak first.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QFontDatabase, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFileDialog, QFormLayout, QGraphicsItem, QGraphicsRectItem, QGraphicsScene,
                             QGraphicsView, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QPushButton,
                             QScrollArea, QSpinBox, QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem,
                             QTabWidget, QToolBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import mfc as M
from . import rc as RC
from . import resources as R
from .document import EditError, PeDocument

ROLE = Qt.ItemDataRole.UserRole


def mono() -> QFont:
    f = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    f.setPointSize(9)
    return f


def _int(text: str) -> int:
    t = text.strip().lower().replace("_", "")
    if t.endswith("h") and re.fullmatch(r"[0-9a-f]+h", t):
        return int(t[:-1], 16)
    return int(t, 0)


def _res_name(text: str):
    t = text.strip()
    try:
        return _int(t)
    except ValueError:
        return t.strip('"').upper()


# ============================================================================ dialog designer
KINDS = [("PushButton", 0x80, 0x50010000, 50, 14, "Button"), ("DefPushButton", 0x80, 0x50010001, 50, 14, "OK"),
         ("CheckBox", 0x80, 0x50010003, 60, 10, "Check"), ("RadioButton", 0x80, 0x50000009, 60, 10, "Radio"),
         ("GroupBox", 0x80, 0x50000007, 100, 50, "Group"), ("Label", 0x82, 0x50020000, 60, 8, "Label"),
         ("Edit", 0x81, 0x50810080, 80, 14, ""), ("ComboBox", 0x85, 0x50010003, 80, 60, ""),
         ("ListBox", 0x83, 0x50A10001, 80, 40, ""), ("Picture", 0x82, 0x5000000E, 30, 20, "")]


class ControlItem(QGraphicsRectItem):
    HANDLE = 6

    def __init__(self, canvas: "DialogCanvas", index: int):
        super().__init__()
        self.canvas = canvas
        self.index = index
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setAcceptHoverEvents(True)
        self._resizing = False
        self.sync()

    @property
    def ctrl(self) -> R.DlgControl:
        return self.canvas.dialog.controls[self.index]

    def sync(self) -> None:
        c = self.ctrl
        sx, sy = self.canvas.sx, self.canvas.sy
        self.setPos(c.x * sx, c.y * sy)
        self.setRect(0, 0, max(2, c.cx * sx), max(2, c.cy * sy))
        self.setZValue(-1 if c.kind == "GroupBox" else 1)

    def paint(self, p: QPainter, _opt, _w=None) -> None:
        c = self.ctrl
        r = self.rect()
        kind = c.kind
        p.setFont(self.canvas.font())
        p.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        text = c.caption.replace("&&", "\0").replace("&", "").replace("\0", "&")
        pal_btn, pal_win, pal_txt = QColor("#e1e1e1"), QColor("#ffffff"), QColor("#000000")
        if not c.style & R.WS_VISIBLE:
            p.setOpacity(0.45)
        if kind in ("PushButton", "DefPushButton"):
            p.setPen(QPen(QColor("#0078d7") if kind == "DefPushButton" else QColor("#adadad"),
                          2 if kind == "DefPushButton" else 1))
            p.setBrush(pal_btn)
            p.drawRect(r.adjusted(0.5, 0.5, -0.5, -0.5))
            p.setPen(pal_txt)
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, text)
        elif kind in ("CheckBox", "RadioButton"):
            box = QRectF(r.left() + 1, r.center().y() - 6, 12, 12)
            p.setPen(QColor("#333"))
            p.setBrush(pal_win)
            if kind == "RadioButton":
                p.drawEllipse(box)
            else:
                p.drawRect(box)
            p.drawText(r.adjusted(17, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        elif kind == "GroupBox":
            p.setPen(QColor("#a0a0a0"))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(r.adjusted(0.5, 7, -0.5, -0.5))
            fm = p.fontMetrics()
            w = fm.horizontalAdvance(text) + 6
            p.fillRect(QRectF(r.left() + 7, r.top(), w, 14), self.canvas.bg)
            p.setPen(QColor("#0033aa"))
            p.drawText(QRectF(r.left() + 10, r.top(), w, 14), Qt.AlignmentFlag.AlignVCenter, text)
        elif kind in ("Edit", "ListBox"):
            p.setPen(QColor("#7a7a7a"))
            p.setBrush(pal_win)
            p.drawRect(r.adjusted(0.5, 0.5, -0.5, -0.5))
            p.setPen(QColor("#888"))
            p.drawText(r.adjusted(3, 2, -2, -2), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                       text or ("Edit" if kind == "Edit" else "ListBox"))
        elif kind == "ComboBox":
            box = QRectF(r.left(), r.top(), r.width(), min(r.height(), 22))
            p.setPen(QColor("#7a7a7a"))
            p.setBrush(pal_win)
            p.drawRect(box.adjusted(0.5, 0.5, -0.5, -0.5))
            p.fillRect(QRectF(box.right() - 16, box.top() + 1, 15, box.height() - 2), pal_btn)
            p.setPen(QColor("#333"))
            p.drawText(QRectF(box.right() - 16, box.top(), 16, box.height()), Qt.AlignmentFlag.AlignCenter, "v")
        elif kind in ("Icon", "Picture"):
            p.setPen(QPen(QColor("#999"), 1, Qt.PenStyle.DashLine))
            p.setBrush(QColor("#f4f4f4"))
            p.drawRect(r.adjusted(0.5, 0.5, -0.5, -0.5))
            p.setPen(QColor("#666"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, text or kind)
        elif kind == "Label":
            p.setPen(pal_txt)
            align = {1: Qt.AlignmentFlag.AlignHCenter, 2: Qt.AlignmentFlag.AlignRight}.get(c.style & 3,
                                                                                         Qt.AlignmentFlag.AlignLeft)
            if c.style & 0x1000:
                p.setPen(QColor("#a0a0a0"))
                p.drawRect(r.adjusted(0.5, 0.5, -0.5, -0.5))
                p.setPen(pal_txt)
            p.drawText(r, align | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, text)
        else:
            p.setPen(QPen(QColor("#6a5acd"), 1, Qt.PenStyle.DashLine))
            p.setBrush(QColor(230, 230, 250, 160))
            p.drawRect(r.adjusted(0.5, 0.5, -0.5, -0.5))
            p.setPen(QColor("#333"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, f"{c.class_name}\n{text}" if text else c.class_name)
        p.setOpacity(1.0)
        if self.canvas.handlers_for(c.id):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#2e9e44"))
            p.drawEllipse(QRectF(r.right() - 7, r.top() + 1, 6, 6))       # "has an event handler"
        if self.isSelected():
            p.setPen(QPen(QColor("#0060c0"), 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(r)
            p.setBrush(QColor("#0060c0"))
            p.drawRect(QRectF(r.right() - self.HANDLE, r.bottom() - self.HANDLE, self.HANDLE, self.HANDLE))

    def _in_handle(self, pos: QPointF) -> bool:
        r = self.rect()
        return pos.x() >= r.right() - self.HANDLE - 2 and pos.y() >= r.bottom() - self.HANDLE - 2

    def hoverMoveEvent(self, e) -> None:  # noqa: N802
        self.setCursor(Qt.CursorShape.SizeFDiagCursor if self.isSelected() and self._in_handle(e.pos())
                       else Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, e) -> None:  # noqa: N802
        self._resizing = self.isSelected() and self._in_handle(e.pos())
        self._start = (self.ctrl.x, self.ctrl.y, self.ctrl.cx, self.ctrl.cy)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        if self._resizing:
            sx, sy = self.canvas.sx, self.canvas.sy
            w = max(4, round(e.pos().x() / sx))
            h = max(4, round(e.pos().y() / sy))
            self.setRect(0, 0, w * sx, h * sy)
            return
        super().mouseMoveEvent(e)
        sx, sy = self.canvas.sx, self.canvas.sy
        self.setPos(round(self.pos().x() / sx) * sx, round(self.pos().y() / sy) * sy)   # snap to dialog units

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        super().mouseReleaseEvent(e)
        sx, sy = self.canvas.sx, self.canvas.sy
        if self._resizing:
            new = (self._start[0], self._start[1], round(self.rect().width() / sx), round(self.rect().height() / sy))
        else:
            new = (round(self.pos().x() / sx), round(self.pos().y() / sy), self._start[2], self._start[3])
        self._resizing = False
        if new != self._start:
            self.canvas.geometry_changed(self.index, *new)

    def mouseDoubleClickEvent(self, e) -> None:  # noqa: N802
        self.canvas.controlActivated.emit(self.index)


class DialogCanvas(QGraphicsView):
    """Shows a DIALOG / DIALOGEX template at its real size (dialog units -> pixels)."""
    selectionChangedTo = pyqtSignal(int)          # control index, -1 = the dialog
    controlActivated = pyqtSignal(int)            # double-click
    geometryEdited = pyqtSignal(int, int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("i18n_skip", True)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.scene_ = QGraphicsScene(self)
        self.setScene(self.scene_)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.setBackgroundBrush(QColor("#808080"))
        self.dialog: R.Dialog | None = None
        self.items_: list[ControlItem] = []
        self.sx = self.sy = 1.5
        self.bg = QColor("#f0f0f0")
        self.handler_ids: set[int] = set()
        self.frame = None
        self.scene_.selectionChanged.connect(self._sel)

    def handlers_for(self, cid: int) -> bool:
        return cid in self.handler_ids

    def changeEvent(self, e) -> None:  # noqa: N802 - the user's dialog stays left-to-right in an Arabic IDE
        super().changeEvent(e)
        from PyQt6.QtCore import QEvent
        if e.type() == QEvent.Type.LayoutDirectionChange and self.layoutDirection() != Qt.LayoutDirection.LeftToRight:
            QTimer.singleShot(0, self._force_ltr)

    def _force_ltr(self) -> None:
        try:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            self.viewport().setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            self.viewport().update()
        except RuntimeError:
            pass

    def set_dialog(self, d: R.Dialog, keep_selection: bool = True) -> None:
        sel = self.selected_index() if keep_selection else -1
        self.dialog = d
        bx, by = d.base_units()
        self.sx, self.sy = bx / 4.0, by / 8.0
        f = QFont(d.font_name if d.font_name and "shell dlg" not in d.font_name.lower() else "Segoe UI")
        f.setPixelSize(max(9, int(round(d.font_size * 96 / 72))) if d.font_size else 12)
        self.setFont(f)
        self.scene_.blockSignals(True)
        self.scene_.clear()
        self.items_ = []
        w, h = d.cx * self.sx, d.cy * self.sy
        title_h = 24 if d.style & R.WS_CAPTION == R.WS_CAPTION else 0
        frame = self.scene_.addRect(QRectF(-4, -4 - title_h, w + 8, h + 8 + title_h), QPen(QColor("#555")),
                                    QBrush(QColor("#3a6ea5") if title_h else self.bg))
        frame.setZValue(-10)
        client = self.scene_.addRect(QRectF(0, 0, w, h), QPen(Qt.PenStyle.NoPen), QBrush(self.bg))
        client.setZValue(-5)
        if title_h:
            t = self.scene_.addSimpleText(d.title or "")
            t.setBrush(QColor("white"))
            t.setFont(self.font())
            t.setPos(4, -title_h + 4)
            t.setZValue(-4)
        self.frame = client
        for i in range(len(d.controls)):
            it = ControlItem(self, i)
            self.scene_.addItem(it)
            self.items_.append(it)
        self.scene_.setSceneRect(QRectF(-30, -30 - title_h, w + 60, h + 60 + title_h))
        self.scene_.blockSignals(False)
        if 0 <= sel < len(self.items_):
            self.items_[sel].setSelected(True)

    def selected_index(self) -> int:
        for it in self.items_:
            try:
                if it.isSelected():
                    return it.index
            except RuntimeError:
                return -1
        return -1

    def select(self, index: int) -> None:
        self.scene_.clearSelection()
        if 0 <= index < len(self.items_):
            self.items_[index].setSelected(True)
            self.centerOn(self.items_[index])

    def _sel(self) -> None:
        self.selectionChangedTo.emit(self.selected_index())

    def geometry_changed(self, index, x, y, cx, cy) -> None:
        self.geometryEdited.emit(index, x, y, cx, cy)


class DialogEditor(QWidget):
    """Designer + toolbox + properties + MFC events of one dialog resource."""

    def __init__(self, wb: "PeWorkbench"):
        super().__init__()
        self.wb = wb
        self.entry: R.ResEntry | None = None
        self.d: R.Dialog | None = None
        self._loading = False
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        split = QSplitter()
        lay.addWidget(split)
        # toolbox
        tb = QWidget()
        tl = QVBoxLayout(tb)
        tl.setContentsMargins(2, 2, 2, 2)
        tl.addWidget(QLabel("Toolbox"))
        self.toolbox = QListWidget()
        for k in KINDS:
            it = QListWidgetItem(k[0])
            it.setData(ROLE, k[0])
            self.toolbox.addItem(it)
        self.toolbox.itemDoubleClicked.connect(lambda it: self.add_control(it.data(ROLE)))
        tl.addWidget(self.toolbox)
        b = QPushButton("Add Control")
        b.clicked.connect(lambda: self.add_control(self.toolbox.currentItem().data(ROLE) if self.toolbox.currentItem()
                                                   else "PushButton"))
        tl.addWidget(b)
        self.del_btn = QPushButton("Delete Control")
        self.del_btn.clicked.connect(self.delete_control)
        tl.addWidget(self.del_btn)
        self.test_btn = QPushButton("Preview (Windows)")
        self.test_btn.setToolTip("Show this dialog template with Windows itself (custom classes may not show).")
        self.test_btn.clicked.connect(self.preview)
        tl.addWidget(self.test_btn)
        split.addWidget(tb)
        self.canvas = DialogCanvas()
        self.canvas.selectionChangedTo.connect(self._selected)
        self.canvas.controlActivated.connect(self._activated)
        self.canvas.geometryEdited.connect(self._geometry)
        split.addWidget(self.canvas)
        # properties + events
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(2, 2, 2, 2)
        self.prop_title = QLabel("Dialog")
        self.prop_title.setStyleSheet("font-weight: bold")
        rl.addWidget(self.prop_title)
        form = QFormLayout()
        self.f_text = QLineEdit()
        self.f_id = QLineEdit()
        self.f_class = QLineEdit()
        self.f_x, self.f_y, self.f_cx, self.f_cy = (QSpinBox() for _ in range(4))
        for s in (self.f_x, self.f_y, self.f_cx, self.f_cy):
            s.setRange(-32768, 32767)
        self.f_style = QLineEdit()
        self.f_exstyle = QLineEdit()
        self.f_font = QLineEdit()
        self.f_visible = QCheckBox("Visible")
        self.f_disabled = QCheckBox("Disabled")
        self.f_tabstop = QCheckBox("Tab stop")
        self.f_group = QCheckBox("Group")
        form.addRow("Caption:", self.f_text)
        form.addRow("ID:", self.f_id)
        form.addRow("Class:", self.f_class)
        form.addRow("X:", self.f_x)
        form.addRow("Y:", self.f_y)
        form.addRow("Width:", self.f_cx)
        form.addRow("Height:", self.f_cy)
        form.addRow("Style:", self.f_style)
        form.addRow("Ex style:", self.f_exstyle)
        form.addRow("Font:", self.f_font)
        flags = QHBoxLayout()
        for c in (self.f_visible, self.f_disabled, self.f_tabstop, self.f_group):
            flags.addWidget(c)
        form.addRow(flags)
        rl.addLayout(form)
        self.apply_btn = QPushButton("Apply Properties")
        self.apply_btn.clicked.connect(self.apply_props)
        rl.addWidget(self.apply_btn)
        for w in (self.f_text, self.f_id, self.f_class, self.f_style, self.f_exstyle, self.f_font):
            w.returnPressed.connect(self.apply_props)
        for s in (self.f_x, self.f_y, self.f_cx, self.f_cy):
            s.editingFinished.connect(self.apply_props)
        for c in (self.f_visible, self.f_disabled, self.f_tabstop, self.f_group):
            c.toggled.connect(lambda _v: not self._loading and self.apply_props())
        rl.addWidget(QLabel("MFC event handlers (double-click: show code)"))
        self.owner = QComboBox()
        self.owner.setToolTip("The MFC class whose message map handles this dialog")
        self.owner.currentIndexChanged.connect(lambda _i: not self._loading and self._refresh_events())
        rl.addWidget(self.owner)
        self.events = QListWidget()
        self.events.itemDoubleClicked.connect(self._event_activated)
        rl.addWidget(self.events, 1)
        eb = QHBoxLayout()
        self.ev_show = QPushButton("Show Code")
        self.ev_show.clicked.connect(lambda: self._event_activated(self.events.currentItem()))
        self.ev_retarget = QPushButton("Retarget...")
        self.ev_retarget.clicked.connect(self._event_retarget)
        eb.addWidget(self.ev_show)
        eb.addWidget(self.ev_retarget)
        rl.addLayout(eb)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(right)
        split.addWidget(scroll)
        split.setSizes([120, 600, 300])

    # ---------------------------------------------------------------- load
    def load(self, entry: R.ResEntry) -> None:
        self.entry = entry
        self.d = R.parse_dialog(entry.data)
        self._loading = True
        maps = self.wb.maps()
        self.owner.clear()
        self.owner.addItem("(no MFC class)", 0)
        for m in maps:
            if m.entries:
                self.owner.addItem(m.label, m.va)
        guess = M.guess_dialog_owner(maps, {c.id for c in self.d.controls})
        if guess is not None:
            self.owner.setCurrentIndex(max(0, self.owner.findData(guess.va)))
        self._loading = False
        self._refresh_handler_ids()
        self.canvas.set_dialog(self.d, keep_selection=False)
        self._selected(-1)

    def owner_map(self) -> M.MsgMap | None:
        va = self.owner.currentData()
        return next((m for m in self.wb.maps() if m.va == va), None) if va else None

    def _refresh_handler_ids(self) -> None:
        own = self.owner_map()
        ids = set()
        if own is not None:
            for m in M.chain(self.wb.maps(), own):
                ids |= m.control_ids()
        self.canvas.handler_ids = ids

    def commit(self, desc: str = "") -> None:
        if self.entry is None:
            return
        self.wb.doc.set_dialog(self.entry.name, self.entry.lang, self.d)
        self.entry = self.wb.doc.get(R.RT_DIALOG, self.entry.name, self.entry.lang)
        self.canvas.set_dialog(self.d)
        self.wb.after_edit(desc or "Dialog edited")

    # ---------------------------------------------------------------- selection / properties
    def selected(self) -> R.DlgControl | None:
        i = self.canvas.selected_index()
        return self.d.controls[i] if self.d is not None and 0 <= i < len(self.d.controls) else None

    def _selected(self, index: int) -> None:
        if self.d is None:
            return
        self._loading = True
        c = self.d.controls[index] if 0 <= index < len(self.d.controls) else None
        is_ctrl = c is not None
        for w in (self.f_id, self.f_class, self.f_tabstop, self.f_group):
            w.setEnabled(is_ctrl)
        self.f_font.setEnabled(not is_ctrl)
        self.del_btn.setEnabled(is_ctrl)
        if c is not None:
            self.prop_title.setText(f"{c.kind}  ({c.class_name})")
            self.f_text.setText(c.caption if not isinstance(c.text, int) else f"#{c.text}")
            self.f_id.setText(str(c.id))
            self.f_class.setText(c.class_name)
            vals = (c.x, c.y, c.cx, c.cy)
            style, ex = c.style, c.exstyle
            self.f_tabstop.setChecked(bool(style & R.WS_TABSTOP))
            self.f_group.setChecked(bool(style & R.WS_GROUP))
        else:
            d = self.d
            self.prop_title.setText("Dialog" + (" (DIALOGEX)" if d.extended else " (DIALOG)"))
            self.f_text.setText(d.title)
            self.f_id.setText(R.name_label(self.entry.name) if self.entry else "")
            self.f_class.setText("")
            vals = (d.x, d.y, d.cx, d.cy)
            style, ex = d.style, d.exstyle
            self.f_font.setText(f"{d.font_size}, {d.font_name}" if d.has_font else "")
        for s, v in zip((self.f_x, self.f_y, self.f_cx, self.f_cy), vals):
            s.setValue(v)
        self.f_style.setText(f"0x{style:08X}")
        self.f_exstyle.setText(f"0x{ex:08X}")
        self.f_visible.setChecked(bool(style & R.WS_VISIBLE))
        self.f_disabled.setChecked(bool(style & R.WS_DISABLED))
        self._loading = False
        self._refresh_events()

    def apply_props(self) -> None:
        if self._loading or self.d is None:
            return
        c = self.selected()
        try:
            style = _int(self.f_style.text())
            ex = _int(self.f_exstyle.text())
        except ValueError:
            QMessageBox.warning(self, "Dialog", "Style values must be numbers (for example 0x50010000).")
            return
        for bit, box in ((R.WS_VISIBLE, self.f_visible), (R.WS_DISABLED, self.f_disabled)):
            style = (style | bit) if box.isChecked() else (style & ~bit)
        geo = (self.f_x.value(), self.f_y.value(), self.f_cx.value(), self.f_cy.value())
        if c is not None:
            for bit, box in ((R.WS_TABSTOP, self.f_tabstop), (R.WS_GROUP, self.f_group)):
                style = (style | bit) if box.isChecked() else (style & ~bit)
            try:
                cid = _int(self.f_id.text())
            except ValueError:
                QMessageBox.warning(self, "Dialog", "The control ID must be a number.")
                return
            text = self.f_text.text()
            new_text = int(text[1:]) if re.fullmatch(r"#\d+", text) else text
            cls = self.f_class.text().strip() or c.cls
            if isinstance(cls, str) and cls.upper() in R.ATOM_OF:
                cls = R.ATOM_OF[cls.upper()]
            new = (new_text, cid, cls, style, ex, *geo)
            old = (c.text, c.id, c.cls, c.style, c.exstyle, c.x, c.y, c.cx, c.cy)
            if new == old:
                return
            c.text, c.id, c.cls, c.style, c.exstyle, c.x, c.y, c.cx, c.cy = new
            self.commit(f"Control {cid} changed")
        else:
            d = self.d
            font = self.f_font.text().strip()
            old = (d.title, d.style, d.exstyle, d.x, d.y, d.cx, d.cy, d.font_size, d.font_name)
            d.title = self.f_text.text()
            d.style, d.exstyle = style, ex
            d.x, d.y, d.cx, d.cy = geo
            if font:
                size, _, name = font.partition(",")
                try:
                    d.font_size = int(size)
                    d.font_name = name.strip() or d.font_name or "MS Shell Dlg"
                    d.style |= R.DS_SETFONT
                except ValueError:
                    pass
            if old != (d.title, d.style, d.exstyle, d.x, d.y, d.cx, d.cy, d.font_size, d.font_name):
                self.commit("Dialog properties changed")

    def _geometry(self, index, x, y, cx, cy) -> None:
        c = self.d.controls[index]
        c.x, c.y, c.cx, c.cy = x, y, cx, cy
        self.commit(f"Control {c.id} moved / resized")
        self.canvas.select(index)

    def add_control(self, kind: str) -> None:
        if self.d is None:
            return
        k = next((k for k in KINDS if k[0] == kind), KINDS[0])
        used = {c.id for c in self.d.controls}
        cid = max([c.id for c in self.d.controls if 1000 <= c.id < 0xFFFF] + [999]) + 1
        while cid in used:
            cid += 1
        if k[0] in ("Label", "GroupBox", "Picture"):
            cid = -1 if k[0] != "Label" else cid
        self.d.controls.append(R.DlgControl(k[1], k[5], cid, k[2], 0, 7, 7, k[3], k[4]))
        self.commit(f"{kind} added")
        self.canvas.select(len(self.d.controls) - 1)

    def delete_control(self) -> None:
        i = self.canvas.selected_index()
        if self.d is None or i < 0:
            return
        c = self.d.controls.pop(i)
        self.commit(f"Control {c.id} deleted")

    # ---------------------------------------------------------------- events
    def _refresh_events(self) -> None:
        self._refresh_handler_ids()
        self.events.clear()
        own = self.owner_map()
        c = self.selected()
        an = self.wb.analysis_if_ready()
        if own is None:
            self.events.addItem("No MFC message map is linked to this dialog.")
            return
        if c is not None:
            hs = M.handlers_for_control(self.wb.maps(), c.id, own)
        else:
            hs = [(m, e) for m in M.chain(self.wb.maps(), own) for e in m.entries if e.msg != M.WM_COMMAND
                  and e.msg != M.WM_NOTIFY]
        for m, e in hs:
            name = an.name_of(e.pfn) if an is not None else f"sub_{e.pfn:X}"
            it = QListWidgetItem(f"{e.event_text(c.kind if c else '')}  ->  {name}  [{m.label}]")
            it.setData(ROLE, (m.va, e.index))
            self.events.addItem(it)
        if not hs:
            self.events.addItem("(no handler)" if c is not None else "(no window-message handlers)")

    def _event_of(self, item):
        if item is None or item.data(ROLE) is None:
            return None, None
        mva, idx = item.data(ROLE)
        m = next((m for m in self.wb.maps() if m.va == mva), None)
        return (m, m.entries[idx]) if m is not None and idx < len(m.entries) else (None, None)

    def _activated(self, index: int) -> None:
        """Double-click on a control: its handler's code (like VB's code view)."""
        self.canvas.select(index)
        self._refresh_events()
        if self.events.count() and self.events.item(0).data(ROLE) is not None:
            self._event_activated(self.events.item(0))
        else:
            self.wb.message.emit("This control has no MFC event handler.")

    def _event_activated(self, item) -> None:
        m, e = self._event_of(item)
        if e is not None:
            self.wb.show_code(e.pfn)

    def _event_retarget(self) -> None:
        m, e = self._event_of(self.events.currentItem())
        if e is not None:
            self.wb.retarget_dialog(e)

    def preview(self) -> None:
        """Show the template with Windows itself (CreateDialogIndirectParam) - read-only preview."""
        import sys
        if sys.platform != "win32" or self.d is None:
            QMessageBox.information(self, "Preview", "The Windows preview needs Windows.")
            return
        import ctypes
        from ctypes import wintypes
        d = R.parse_dialog(R.build_dialog(self.d))
        d.menu = None                                    # the menu resource lives in the edited program
        d.wclass = None
        for c in d.controls:
            if isinstance(c.text, int):
                c.text = ""
        tmpl = R.build_dialog(d)
        buf = ctypes.create_string_buffer(tmpl, len(tmpl) + 16)
        user32 = ctypes.windll.user32
        proto = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

        def proc(h, msg, wp, lp):
            if msg == 0x0111 and (wp & 0xFFFF) in (1, 2) or msg == 0x0010:
                user32.DestroyWindow(h)
                return 1
            return 1 if msg == 0x0110 else 0
        self._preview_proc = proto(proc)
        user32.CreateDialogIndirectParamW.restype = wintypes.HWND
        user32.CreateDialogIndirectParamW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p, wintypes.HWND, proto,
                                                      wintypes.LPARAM]
        h = user32.CreateDialogIndirectParamW(None, buf, None, self._preview_proc, 0)
        if not h:
            QMessageBox.information(self, "Preview", "Windows could not create this dialog (it may use window "
                                    "classes that only the program registers).")
            return
        user32.ShowWindow(h, 5)


# ============================================================================ menu editor
class MenuEditorPanel(QWidget):
    def __init__(self, wb: "PeWorkbench"):
        super().__init__()
        self.wb = wb
        self.entry = None
        self.menu: R.Menu | None = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.info = QLabel()
        lay.addWidget(self.info)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Text", "ID", "Flags", "MFC handler"])
        self.tree.setColumnWidth(0, 260)
        self.tree.setProperty("i18n_skip_items", True)
        self.tree.itemDoubleClicked.connect(self._dbl)
        lay.addWidget(self.tree, 1)
        row = QHBoxLayout()
        for text, fn in (("Add Item", self.add_item), ("Add Submenu", self.add_popup),
                         ("Add Separator", self.add_sep), ("Delete", self.delete), ("Move Up", lambda: self.move(-1)),
                         ("Move Down", lambda: self.move(1)), ("Apply", self.apply), ("Show Handler", self.show_handler)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)

    def load(self, entry) -> None:
        self.entry = entry
        self.menu = R.parse_menu(entry.data)
        self.info.setText(("MENUEX" if self.menu.extended else "MENU") + " - edit Text and ID in place, then Apply."
                          " Grey/check flags are kept.")
        self.tree.clear()
        an = self.wb.analysis_if_ready()

        def add(parent, items):
            for it in items:
                hs = M.handlers_for_command(self.wb.maps(), it.id) if it.id and not it.is_popup else []
                hname = ", ".join((an.name_of(e.pfn) if an else f"sub_{e.pfn:X}") for _m, e in hs)
                w = QTreeWidgetItem([("-" * 12) if it.is_separator else it.text,
                                     "" if it.is_popup else str(it.id), f"0x{it.flags:X}", hname])
                w.setData(0, ROLE, it)
                w.setFlags(w.flags() | Qt.ItemFlag.ItemIsEditable)
                (parent.addChild(w) if parent else self.tree.addTopLevelItem(w))
                if it.is_popup:
                    add(w, it.children or [])
        add(None, self.menu.items)
        self.tree.expandAll()

    def _collect(self) -> list:
        def walk(w) -> R.MenuItem:
            old: R.MenuItem = w.data(0, ROLE) or R.MenuItem()
            it = R.MenuItem(old.text, old.id, old.flags, old.state, old.help_id, None)
            if not old.is_separator or w.childCount():
                it.text = w.text(0)
                try:
                    it.id = _int(w.text(1)) if w.text(1).strip() else 0
                except ValueError:
                    raise EditError(f"'{w.text(1)}' is not a number (menu ID of '{w.text(0)}').") from None
            if old.is_popup or w.childCount():
                it.children = [walk(w.child(i)) for i in range(w.childCount())]
            return it
        return [walk(self.tree.topLevelItem(i)) for i in range(self.tree.topLevelItemCount())]

    def apply(self) -> None:
        try:
            self.menu.items = self._collect()
        except EditError as e:
            QMessageBox.warning(self, "Menu", str(e))
            return
        self.wb.doc.set_menu(self.entry.name, self.entry.lang, self.menu)
        self.wb.after_edit("Menu edited")
        self.load(self.wb.doc.get(R.RT_MENU, self.entry.name, self.entry.lang))

    def _new(self, item: R.MenuItem) -> None:
        cur = self.tree.currentItem()
        w = QTreeWidgetItem([item.text, "" if item.is_popup else str(item.id), "0x0", ""])
        w.setData(0, ROLE, item)
        w.setFlags(w.flags() | Qt.ItemFlag.ItemIsEditable)
        if cur is None:
            self.tree.addTopLevelItem(w)
        else:
            data = cur.data(0, ROLE)
            if data is not None and data.is_popup:
                cur.addChild(w)
                cur.setExpanded(True)
            else:
                parent = cur.parent()
                if parent is None:
                    self.tree.insertTopLevelItem(self.tree.indexOfTopLevelItem(cur) + 1, w)
                else:
                    parent.insertChild(parent.indexOfChild(cur) + 1, w)
        self.tree.setCurrentItem(w)

    def _next_id(self) -> int:
        ids = [cid for cid, _p in R.menu_commands(self.menu.items)] if self.menu else []
        return max(ids + [40000]) + 1

    def add_item(self):
        self._new(R.MenuItem("New Item", self._next_id()))

    def add_popup(self):
        self._new(R.MenuItem("New Menu", 0, 0, children=[]))

    def add_sep(self):
        self._new(R.MenuItem("", 0, R.MFT_SEPARATOR if self.menu and self.menu.extended else 0))

    def delete(self):
        cur = self.tree.currentItem()
        if cur is not None:
            (cur.parent() or self.tree.invisibleRootItem()).removeChild(cur)

    def move(self, step: int):
        cur = self.tree.currentItem()
        if cur is None:
            return
        parent = cur.parent() or self.tree.invisibleRootItem()
        i = parent.indexOfChild(cur)
        j = i + step
        if 0 <= j < parent.childCount():
            parent.takeChild(i)
            parent.insertChild(j, cur)
            self.tree.setCurrentItem(cur)

    def _dbl(self, item, col):
        if col == 3:
            self.show_handler()

    def show_handler(self):
        cur = self.tree.currentItem()
        if cur is None:
            return
        try:
            cid = _int(cur.text(1))
        except ValueError:
            return
        hs = M.handlers_for_command(self.wb.maps(), cid)
        if hs:
            self.wb.show_code(hs[0][1].pfn)
        else:
            self.wb.message.emit(f"No MFC ON_COMMAND handler for {cid}.")


# ============================================================================ simple table editors
class TableEditor(QWidget):
    """Two-or-more-column grid with Add / Delete / Apply (strings, accelerators, version strings, dlginit)."""

    def __init__(self, wb, headers: list[str], apply_fn, info: str = ""):
        super().__init__()
        self.wb = wb
        self.apply_fn = apply_fn
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.info = QLabel(info)
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        self.extra = QFormLayout()
        lay.addLayout(self.extra)
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeMode.Stretch)
        self.table.setProperty("i18n_skip_items", True)
        lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        for text, fn in (("Add Row", self.add_row), ("Delete Row", self.del_row), ("Apply", self._apply)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)
        self.entry = None

    def set_rows(self, rows: list[list[str]]) -> None:
        self.table.setRowCount(0)
        for r in rows:
            self.add_row(r)

    def add_row(self, values=None) -> None:
        i = self.table.rowCount()
        self.table.insertRow(i)
        for c in range(self.table.columnCount()):
            v = values[c] if values and c < len(values) else ""
            self.table.setItem(i, c, QTableWidgetItem(str(v)))

    def del_row(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def rows(self) -> list[list[str]]:
        return [[(self.table.item(r, c).text() if self.table.item(r, c) else "") for c in range(self.table.columnCount())]
                for r in range(self.table.rowCount())]

    def _apply(self) -> None:
        try:
            self.apply_fn(self)
        except (ValueError, EditError) as e:
            QMessageBox.warning(self, "Resources", str(e))


class ImagePanel(QWidget):
    def __init__(self, wb):
        super().__init__()
        self.wb = wb
        self.entry = None
        lay = QVBoxLayout(self)
        self.info = QLabel()
        lay.addWidget(self.info)
        self.view = QLabel()
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.setMinimumHeight(160)
        self.view.setStyleSheet("background: #c8c8c8; border: 1px solid #999")
        lay.addWidget(self.view, 1)
        row = QHBoxLayout()
        self.b_replace = QPushButton("Replace from File...")
        self.b_replace.clicked.connect(self.replace)
        self.b_export = QPushButton("Export...")
        self.b_export.clicked.connect(lambda: self.wb.export_entry(self.entry))
        row.addWidget(self.b_replace)
        row.addWidget(self.b_export)
        row.addStretch()
        lay.addLayout(row)

    def file_bytes(self, e) -> tuple[bytes, str]:
        if e.type in (R.RT_GROUP_ICON, R.RT_GROUP_CURSOR):
            return self.wb.doc.icon_file(e), ".cur" if e.type == R.RT_GROUP_CURSOR else ".ico"
        if e.type == R.RT_BITMAP:
            return R.dib_to_bmp(e.data), ".bmp"
        if e.type == R.RT_ICON:
            return R.group_to_file(struct.pack("<HHHBBBBHHIH", 0, 1, 1, 0, 0, 0, 0, 1, 32, len(e.data), 1),
                                   {1: e.data}), ".ico"
        return e.data, ".png" if R.png_or_ico_image(e.data) else ".bin"

    def load(self, e) -> None:
        self.entry = e
        data, ext = self.file_bytes(e)
        pm = QPixmap()
        ok = pm.loadFromData(data)
        if e.type in (R.RT_GROUP_ICON, R.RT_GROUP_CURSOR):
            sizes = ", ".join(f"{g['w']}x{g['h']} {g['bits']}-bit" for g in R.group_entries(e.data))
            self.info.setText(f"{R.type_label(e.type)} {R.name_label(e.name)}: {sizes}")
        else:
            self.info.setText(f"{R.type_label(e.type)} {R.name_label(e.name)}: {len(e.data)} bytes"
                              + (f", {pm.width()} x {pm.height()}" if ok else ""))
        if ok:
            if pm.width() < 96:
                pm = pm.scaled(pm.width() * 3, pm.height() * 3, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.FastTransformation)
            self.view.setPixmap(pm)
        else:
            self.view.setText("(no preview)")
        self.b_replace.setEnabled(e.type in (R.RT_GROUP_ICON, R.RT_GROUP_CURSOR, R.RT_BITMAP) or ext == ".png")

    def replace(self, path: str | None = None) -> None:
        e = self.entry
        if e is None:
            return
        flt = {R.RT_GROUP_ICON: "Icons (*.ico)", R.RT_GROUP_CURSOR: "Cursors (*.cur)",
               R.RT_BITMAP: "Bitmaps (*.bmp)"}.get(e.type, "Images (*.png)")
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Replace Resource", "", flt + ";;All files (*.*)")
        if not path:
            return
        data = Path(path).read_bytes()
        try:
            if e.type in (R.RT_GROUP_ICON, R.RT_GROUP_CURSOR):
                self.wb.doc.replace_icon_group(e, data)
            elif e.type == R.RT_BITMAP:
                self.wb.doc.set_resource(e.type, e.name, e.lang, R.bmp_to_dib(data))
            else:
                self.wb.doc.set_resource(e.type, e.name, e.lang, data)
        except ValueError as ex:
            QMessageBox.warning(self, "Replace", str(ex))
            return
        self.wb.after_edit(f"{R.type_label(e.type)} {R.name_label(e.name)} replaced", reload_tree=True)


class TextPanel(QWidget):
    def __init__(self, wb):
        super().__init__()
        self.wb = wb
        self.entry = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit = QPlainTextEdit()
        self.edit.setFont(mono())
        lay.addWidget(self.edit, 1)
        b = QPushButton("Apply")
        b.clicked.connect(self.apply)
        lay.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)

    def load(self, e) -> None:
        self.entry = e
        raw = e.data
        if raw[:2] in (b"\xff\xfe",):
            self.edit.setPlainText(raw[2:].decode("utf-16-le", "replace"))
        else:
            self.edit.setPlainText(raw.decode("utf-8-sig", "replace"))

    def apply(self) -> None:
        e = self.entry
        data = self.edit.toPlainText().encode("utf-8")
        if e.data.startswith(b"\xef\xbb\xbf"):
            data = b"\xef\xbb\xbf" + data
        self.wb.doc.set_resource(e.type, e.name, e.lang, data)
        self.wb.after_edit(f"{R.type_label(e.type)} {R.name_label(e.name)} edited")


class HexPanel(QWidget):
    def __init__(self, wb):
        super().__init__()
        self.wb = wb
        self.entry = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.info = QLabel()
        lay.addWidget(self.info)
        try:
            from ..retro.rom.buffer import HexBuffer
            from ..retro.rom.hexview import HexView
            self._buf_cls = HexBuffer
            self.view = HexView(HexBuffer(b""))
        except Exception:  # noqa: BLE001 - fall back to a read-only dump
            self._buf_cls = None
            self.view = QPlainTextEdit()
            self.view.setReadOnly(True)
            self.view.setFont(mono())
        lay.addWidget(self.view, 1)
        row = QHBoxLayout()
        b = QPushButton("Apply")
        b.clicked.connect(self.apply)
        row.addWidget(b)
        b2 = QPushButton("Replace from File...")
        b2.clicked.connect(self.replace)
        row.addWidget(b2)
        b3 = QPushButton("Export...")
        b3.clicked.connect(lambda: self.wb.export_entry(self.entry))
        row.addWidget(b3)
        row.addStretch()
        lay.addLayout(row)

    def load(self, e) -> None:
        self.entry = e
        self.info.setText(f"{R.type_label(e.type)} {R.name_label(e.name)} - {len(e.data)} bytes (hex editor)")
        if self._buf_cls is not None:
            self.buf = self._buf_cls(bytes(e.data))
            self.view.set_buffer(self.buf)
        else:
            self.view.setPlainText("\n".join(f"{i:08X}  {e.data[i:i + 16].hex(' ')}" for i in range(0, len(e.data), 16)))

    def current_bytes(self) -> bytes:
        if self._buf_cls is not None:
            return bytes(self.buf.read(0, len(self.buf)))
        return self.entry.data

    def apply(self) -> None:
        e = self.entry
        data = self.current_bytes()
        if data != e.data:
            self.wb.doc.set_resource(e.type, e.name, e.lang, data)
            self.wb.after_edit(f"{R.type_label(e.type)} {R.name_label(e.name)} edited")

    def replace(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Replace Resource", "", "All files (*.*)")
        if path:
            e = self.entry
            self.wb.doc.set_resource(e.type, e.name, e.lang, Path(path).read_bytes())
            self.wb.after_edit(f"{R.type_label(e.type)} {R.name_label(e.name)} replaced", reload_tree=True)


# ============================================================================ code dialogs
class EditInstructionDialog(QDialog):
    def __init__(self, wb: "PeWorkbench", va: int):
        super().__init__(wb)
        self.wb = wb
        self.va = va
        self.setWindowTitle("Edit Instruction")
        self.resize(560, 360)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Address 0x{va:X}. The new code must fit in the instructions it replaces "
                             "(same size or smaller; the rest is filled with NOPs). No code is added to the program."))
        form = QFormLayout()
        self.count = QSpinBox()
        self.count.setRange(1, 16)
        self.count.valueChanged.connect(self._update)
        form.addRow("Instructions to replace:", self.count)
        lay.addLayout(form)
        self.orig = QPlainTextEdit()
        self.orig.setReadOnly(True)
        self.orig.setFont(mono())
        self.orig.setMaximumHeight(90)
        lay.addWidget(QLabel("Original:"))
        lay.addWidget(self.orig)
        lay.addWidget(QLabel("New assembly (one instruction per line):"))
        self.asm = QPlainTextEdit()
        self.asm.setFont(mono())
        self.asm.setMaximumHeight(90)
        self.asm.textChanged.connect(self._update)
        lay.addWidget(self.asm)
        self.preview = QLabel()
        self.preview.setFont(mono())
        self.preview.setWordWrap(True)
        lay.addWidget(self.preview)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        self.ok_btn = bb.button(QDialogButtonBox.StandardButton.Ok)
        lay.addWidget(bb)
        lines = wb.doc.analysis().disasm(va, 32, max_lines=1)
        if lines:
            self.asm.setPlainText(f"{lines[0].mnemonic} {lines[0].op_str}".strip())
        self._update()

    def _update(self) -> None:
        an = self.wb.doc.analysis()
        lines = an.disasm(self.va, 16 * self.count.value() + 16, max_lines=self.count.value())
        self.orig.setPlainText("\n".join(ln.text() for ln in lines))
        try:
            new, old, _l = self.wb.doc.plan_instruction_patch(self.va, self.asm.toPlainText(), self.count.value())
            self.preview.setText(f"{old.hex(' ').upper()}\n-> {new.hex(' ').upper()}")
            self.preview.setStyleSheet("")
            self.ok_btn.setEnabled(True)
        except EditError as e:
            self.preview.setText(str(e))
            self.preview.setStyleSheet("color: #b00020")
            self.ok_btn.setEnabled(False)

    def _ok(self) -> None:
        try:
            self.wb.doc.patch_instructions(self.va, self.asm.toPlainText(), self.count.value())
        except EditError as e:
            QMessageBox.warning(self, "Edit Instruction", str(e))
            return
        self.accept()


class FunctionPicker(QDialog):
    def __init__(self, wb: "PeWorkbench", title: str, current: int = 0):
        super().__init__(wb)
        self.setWindowTitle(title)
        self.resize(520, 460)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Pick an existing function (MFC handlers are listed first). Only functions that "
                             "already exist in the program can be used."))
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter (name or address)")
        lay.addWidget(self.filter)
        self.list = QListWidget()
        lay.addWidget(self.list, 1)
        an = wb.doc.analysis()
        handlers = {e.pfn for m in wb.maps() for e in m.entries}
        funcs = sorted(wb.doc.valid_handler_targets(), key=lambda va: (va not in handlers, va))
        for va in funcs:
            it = QListWidgetItem(f"0x{va:X}  {an.name_of(va)}")
            it.setData(ROLE, va)
            self.list.addItem(it)
            if va == current:
                self.list.setCurrentItem(it)
        self.filter.textChanged.connect(self._filter)
        self.list.itemDoubleClicked.connect(lambda _i: self.accept())
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _filter(self, text: str) -> None:
        t = text.lower()
        for i in range(self.list.count()):
            it = self.list.item(i)
            it.setHidden(bool(t) and t not in it.text().lower())

    def value(self) -> int | None:
        it = self.list.currentItem()
        return it.data(ROLE) if it is not None else None


# ============================================================================ the workbench
class PeWorkbench(QWidget):
    modifiedChanged = pyqtSignal(bool)
    message = pyqtSignal(str)
    saved = pyqtSignal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self.doc = PeDocument.open(self.path)
        self.save_path: Path | None = None
        self._was_modified = False
        self._ghidra = {}
        self.doc.listeners.append(self._doc_changed)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        tb = QToolBar()
        self.toolbar = tb
        self.a_save = tb.addAction("Save As...", self.save)
        self.a_undo = tb.addAction("Undo", self.undo)
        self.a_redo = tb.addAction("Redo", self.redo)
        tb.addSeparator()
        tb.addAction("Export .rc...", self.export_rc)
        tb.addAction("Import .rc...", self.import_rc)
        tb.addSeparator()
        tb.addAction("Add Resource...", self.add_resource)
        tb.addAction("Delete Resource", self.delete_resource)
        lay.addWidget(tb)
        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet("padding: 3px")
        lay.addWidget(self.banner)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        self._build_resources()
        self._build_code()
        self._build_mfc()
        self._build_patches()
        self._build_info()
        self.tabs.currentChanged.connect(self._tab_changed)
        self.fill_tree()
        self._banner()
        self._update_actions()

    # ---------------------------------------------------------------- doc glue
    def maps(self) -> list:
        try:
            return self.doc.message_maps()
        except Exception:  # noqa: BLE001
            return []

    def analysis_if_ready(self):
        return self.doc._analysis

    def ensure_analysis(self):
        if self.doc._analysis is None:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                self.doc.analysis(lambda m: self.message.emit(m))
            finally:
                QApplication.restoreOverrideCursor()
            self.fill_functions()
        return self.doc._analysis

    def is_modified(self) -> bool:
        return self.doc.is_modified()

    def _doc_changed(self) -> None:
        m = self.doc.is_modified()
        if m != self._was_modified:
            self._was_modified = m
            self.modifiedChanged.emit(m)
        self._update_actions()

    def _update_actions(self) -> None:
        self.a_undo.setEnabled(self.doc.can_undo())
        self.a_redo.setEnabled(self.doc.can_redo())

    def after_edit(self, desc: str, reload_tree: bool = False) -> None:
        self.message.emit(desc)
        if reload_tree:
            self.fill_tree(keep=True)
        self.fill_patches()
        self._doc_changed()

    def _banner(self) -> None:
        img = self.doc.img
        parts = [f"{self.path.name}: {img.machine_name} {'DLL' if img.is_dll else 'EXE'}, "
                 f"{len(self.doc.resources)} resources, {len(self.maps())} MFC message maps"]
        warn = []
        if img.has_certificate():
            warn.append("signed - saving removes the digital signature")
        if img.dll_characteristics & 0x4000:
            warn.append("Control Flow Guard is on")
        if img.directory(14)[0]:
            warn.append(".NET assembly - resources only, use the .NET tools for code")
        self.banner.setText("  |  ".join(parts + warn))

    def undo(self) -> None:
        if self.doc.undo():
            self._reload_views()

    def redo(self) -> None:
        if self.doc.redo():
            self._reload_views()

    def _reload_views(self) -> None:
        self.fill_tree(keep=True)
        self.fill_mfc()
        self.fill_patches()
        self._update_actions()

    # ---------------------------------------------------------------- resources tab
    def _build_resources(self) -> None:
        w = QSplitter()
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Resource", "Size"])
        self.tree.setColumnWidth(0, 220)
        self.tree.currentItemChanged.connect(lambda cur, _p: self._open_item(cur))
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        w.addWidget(self.tree)
        self.stack = QStackedWidget()
        self.empty = QLabel("Select a resource on the left.\n\nDialogs open in the designer: drag to move, drag the "
                            "corner to resize, double-click a control to see its MFC event handler code.")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setWordWrap(True)
        self.dlg_editor = DialogEditor(self)
        self.menu_editor = MenuEditorPanel(self)
        self.str_editor = TableEditor(self, ["ID", "Text"], self._apply_strings,
                                      "String table of one language (all blocks). Edit, add or delete rows, then Apply.")
        self.acc_editor = TableEditor(self, ["Key", "Command ID"], self._apply_accel,
                                      "Keys like Ctrl+Shift+F5, Alt+X, Delete, \"a\" (ASCII). Apply writes the table.")
        self.ver_editor = TableEditor(self, ["Name", "Value"], self._apply_version, "Version information.")
        self.ver_file = QLineEdit()
        self.ver_prod = QLineEdit()
        self.ver_editor.extra.addRow("File version:", self.ver_file)
        self.ver_editor.extra.addRow("Product version:", self.ver_prod)
        self.tb_editor = TableEditor(self, ["Button command ID (0 = separator)"], self._apply_toolbar,
                                     "MFC toolbar (RT_TOOLBAR 241): button order of the toolbar bitmap.")
        self.tb_w = QSpinBox()
        self.tb_h = QSpinBox()
        for s in (self.tb_w, self.tb_h):
            s.setRange(1, 256)
        self.tb_editor.extra.addRow("Button width:", self.tb_w)
        self.tb_editor.extra.addRow("Button height:", self.tb_h)
        self.init_editor = TableEditor(self, ["Control ID", "Message", "Text"], self._apply_dlginit,
                                       "MFC dialog init data (RT_DLGINIT 240): strings MFC adds to combo / list boxes "
                                       "(0x403 = CB_ADDSTRING, 0x180 = LB_ADDSTRING).")
        self.img_panel = ImagePanel(self)
        self.text_panel = TextPanel(self)
        self.hex_panel = HexPanel(self)
        for p in (self.empty, self.dlg_editor, self.menu_editor, self.str_editor, self.acc_editor, self.ver_editor,
                  self.tb_editor, self.init_editor, self.img_panel, self.text_panel, self.hex_panel):
            self.stack.addWidget(p)
        w.addWidget(self.stack)
        w.setSizes([240, 900])
        self.tabs.addTab(w, "Resources")

    def fill_tree(self, keep: bool = False) -> None:
        cur = self.tree.currentItem()
        sel = cur.data(0, ROLE) if cur is not None else None
        self.tree.blockSignals(True)
        self.tree.clear()
        groups: dict = {}
        for e in sorted(self.doc.resources, key=lambda e: (R._sort_key(e.type), R._sort_key(e.name), e.lang)):
            groups.setdefault(e.type, []).append(e)
        target = None
        for t, ents in groups.items():
            ti = QTreeWidgetItem([R.type_label(t), str(len(ents))])
            self.tree.addTopLevelItem(ti)
            names: dict = {}
            for e in ents:
                names.setdefault(e.name, []).append(e)
            for n, items in names.items():
                multi = len(items) > 1
                ni = QTreeWidgetItem([R.name_label(n), "" if multi else str(len(items[0].data))])
                ti.addChild(ni)
                if not multi:
                    ni.setData(0, ROLE, items[0].key)
                    ni.setToolTip(0, f"Language {R.lang_label(items[0].lang)}")
                    if sel == items[0].key:
                        target = ni
                    continue
                for e in items:
                    li = QTreeWidgetItem([R.lang_label(e.lang), str(len(e.data))])
                    li.setData(0, ROLE, e.key)
                    ni.addChild(li)
                    if sel == e.key:
                        target = li
        self.tree.blockSignals(False)
        if keep and target is not None:
            self.tree.setCurrentItem(target)
            self._open_item(target)
        elif keep and sel is not None:
            self.stack.setCurrentWidget(self.empty)

    def entry_of(self, key) -> R.ResEntry | None:
        return next((e for e in self.doc.resources if e.key == key), None) if key else None

    def select_resource(self, rtype, name, lang=None) -> bool:
        it = self._find_item(rtype, name, lang)
        if it is None:
            return False
        self.tabs.setCurrentIndex(0)
        self.tree.setCurrentItem(it)
        return True

    def _find_item(self, rtype, name, lang=None):
        def walk(item):
            k = item.data(0, ROLE)
            if k and k[0] == rtype and k[1] == name and (lang is None or k[2] == lang):
                return item
            for i in range(item.childCount()):
                r = walk(item.child(i))
                if r is not None:
                    return r
            return None
        return walk(self.tree.invisibleRootItem())

    def _open_item(self, item) -> None:
        e = self.entry_of(item.data(0, ROLE)) if item is not None else None
        if e is None:
            self.stack.setCurrentWidget(self.empty)
            return
        try:
            self._open_entry(e)
        except Exception as ex:  # noqa: BLE001 - undecodable resource: hex view
            self.message.emit(f"Cannot decode {R.type_label(e.type)} {R.name_label(e.name)} ({ex}); hex view")
            self.hex_panel.load(e)
            self.stack.setCurrentWidget(self.hex_panel)

    def _open_entry(self, e: R.ResEntry) -> None:
        t = e.type
        if t == R.RT_DIALOG:
            self.dlg_editor.load(e)
            self.stack.setCurrentWidget(self.dlg_editor)
        elif t == R.RT_MENU:
            self.menu_editor.load(e)
            self.stack.setCurrentWidget(self.menu_editor)
        elif t == R.RT_STRING:
            self.str_editor.entry = e
            strings = self.doc.strings(e.lang).get(e.lang, {})
            self.str_editor.set_rows([[str(k), v] for k, v in sorted(strings.items())])
            self.stack.setCurrentWidget(self.str_editor)
        elif t == R.RT_ACCELERATOR:
            self.acc_editor.entry = e
            self.acc_editor.set_rows([[a.key_text(), str(a.cmd)] for a in R.parse_accel(e.data)])
            self.stack.setCurrentWidget(self.acc_editor)
        elif t == R.RT_VERSION:
            v = R.parse_version(e.data)
            self.ver_editor.entry = e
            self.ver_file.setText(R.version_string(v.file_version))
            self.ver_prod.setText(R.version_string(v.product_version))
            rows = [[k, val] for items in v.strings.values() for k, val in items.items()]
            self.ver_editor.set_rows(rows)
            self.stack.setCurrentWidget(self.ver_editor)
        elif t == R.RT_TOOLBAR:
            tb = R.parse_toolbar(e.data)
            self.tb_editor.entry = e
            self.tb_w.setValue(tb.width)
            self.tb_h.setValue(tb.height)
            self.tb_editor.set_rows([[str(i)] for i in tb.ids])
            self.stack.setCurrentWidget(self.tb_editor)
        elif t == R.RT_DLGINIT:
            self.init_editor.entry = e
            self.init_editor.set_rows([[str(i.ctrl_id), f"0x{i.msg:X}", i.text] for i in R.parse_dlginit(e.data)])
            self.stack.setCurrentWidget(self.init_editor)
        elif t in (R.RT_GROUP_ICON, R.RT_GROUP_CURSOR, R.RT_BITMAP, R.RT_ICON) or R.png_or_ico_image(e.data):
            self.img_panel.load(e)
            self.stack.setCurrentWidget(self.img_panel)
        elif t in (R.RT_MANIFEST, R.RT_HTML, R.RT_DLGINCLUDE) or (isinstance(t, str) and t in ("XML", "TEXT", "JSON")):
            self.text_panel.load(e)
            self.stack.setCurrentWidget(self.text_panel)
        else:
            self.hex_panel.load(e)
            self.stack.setCurrentWidget(self.hex_panel)

    def _apply_strings(self, ed: TableEditor) -> None:
        out = {}
        for sid, text in ed.rows():
            if not sid.strip():
                continue
            k = _int(sid)
            if not 0 <= k <= 0xFFFF:
                raise ValueError(f"String ID {k} must be 0..65535.")
            if k in out:
                raise ValueError(f"String ID {k} is listed twice.")
            out[k] = text
        self.doc.set_strings(ed.entry.lang, out)
        self.after_edit("String table edited", reload_tree=True)

    def _apply_accel(self, ed: TableEditor) -> None:
        items = []
        for key, cmd in ed.rows():
            if not key.strip():
                continue
            flags, k = R.parse_key_text(key)
            items.append(R.Accel(flags, k, _int(cmd)))
        e = ed.entry
        self.doc.set_resource(e.type, e.name, e.lang, R.build_accel(items))
        self.after_edit("Accelerators edited")

    def _apply_version(self, ed: TableEditor) -> None:
        e = ed.entry
        v = R.parse_version(e.data)
        v.file_version = R.parse_version_string(self.ver_file.text())
        v.product_version = R.parse_version_string(self.ver_prod.text())
        table = next(iter(v.strings), "040904b0")
        v.strings = {table: {k: val for k, val in ed.rows() if k.strip()}}
        self.doc.set_resource(e.type, e.name, e.lang, R.build_version(v))
        self.after_edit("Version information edited")

    def _apply_toolbar(self, ed: TableEditor) -> None:
        e = ed.entry
        ids = [_int(r[0]) for r in ed.rows() if r[0].strip()]
        self.doc.set_resource(e.type, e.name, e.lang, R.build_toolbar(R.Toolbar(self.tb_w.value(), self.tb_h.value(), ids)))
        self.after_edit("Toolbar edited")

    def _apply_dlginit(self, ed: TableEditor) -> None:
        e = ed.entry
        items = [R.text_item(_int(c), t, _int(m)) for c, m, t in ed.rows() if c.strip()]
        self.doc.set_resource(e.type, e.name, e.lang, R.build_dlginit(items))
        self.after_edit("Dialog init data edited")

    def _tree_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        e = self.entry_of(item.data(0, ROLE)) if item is not None else None
        m = QMenu(self)
        if e is not None:
            m.addAction("Export...", lambda: self.export_entry(e))
            m.addAction("Delete Resource", self.delete_resource)
            m.addAction("Copy to Language...", lambda: self.copy_language(e))
        m.addAction("Add Resource...", self.add_resource)
        m.exec(self.tree.viewport().mapToGlobal(pos))

    def current_entry(self) -> R.ResEntry | None:
        it = self.tree.currentItem()
        return self.entry_of(it.data(0, ROLE)) if it is not None else None

    def export_entry(self, e, path: str | None = None) -> Path | None:
        if e is None:
            return None
        data, ext = self.img_panel.file_bytes(e) if e.type in (R.RT_GROUP_ICON, R.RT_GROUP_CURSOR, R.RT_BITMAP,
                                                              R.RT_ICON) else (e.data, ".bin")
        if e.type == R.RT_MANIFEST:
            ext = ".manifest"
        if path is None:
            tname = re.sub(r"[^\w]", "_", R.type_label(e.type))
            default = str(self.path.with_name(f"{tname}_{e.name}{ext}"))
            path, _ = QFileDialog.getSaveFileName(self, "Export Resource", default, f"*{ext};;All files (*.*)")
        if not path:
            return None
        Path(path).write_bytes(data)
        self.message.emit(f"Exported {Path(path).name}")
        return Path(path)

    def delete_resource(self) -> None:
        e = self.current_entry()
        if e is None:
            return
        if QMessageBox.question(self, "Delete Resource", f"Delete {R.type_label(e.type)} {R.name_label(e.name)}?") \
                != QMessageBox.StandardButton.Yes:
            return
        self.doc.remove_resource(e.type, e.name, e.lang)
        self.after_edit("Resource deleted", reload_tree=True)

    def copy_language(self, e) -> None:
        text, ok = QInputDialog.getText(self, "Copy to Language", "Language ID (for example 0x401 Arabic, 0xC01 "
                                        "Arabic - Egypt, 0x409 English):", text="0x401")
        if ok and text.strip():
            try:
                lang = _int(text)
            except ValueError:
                return
            self.doc.set_resource(e.type, e.name, lang, e.data)
            self.after_edit(f"Copied to language {lang}", reload_tree=True)

    def add_resource(self, path: str | None = None, rtype=None, name=None) -> None:
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Add Resource from File", "",
                                                  "Icons (*.ico);;Cursors (*.cur);;Bitmaps (*.bmp);;All files (*.*)")
        if not path:
            return
        data = Path(path).read_bytes()
        ext = Path(path).suffix.lower()
        lang = (self.doc.languages() or [0x409])[0]
        if name is None:
            text, ok = QInputDialog.getText(self, "Add Resource", "Resource name or number:",
                                            text=str(self.doc.next_id(R.RT_GROUP_ICON if ext == ".ico" else
                                                                      R.RT_BITMAP if ext == ".bmp" else R.RT_RCDATA)))
            if not ok or not text.strip():
                return
            name = _res_name(text)
        try:
            if ext in (".ico", ".cur") and rtype is None:
                self.doc.add_icon_group(name, lang, data, cursor=ext == ".cur")
            elif ext == ".bmp" and rtype is None:
                self.doc.set_resource(R.RT_BITMAP, name, lang, R.bmp_to_dib(data))
            else:
                self.doc.set_resource(rtype if rtype is not None else R.RT_RCDATA, name, lang, data)
        except ValueError as ex:
            QMessageBox.warning(self, "Add Resource", str(ex))
            return
        self.after_edit("Resource added", reload_tree=True)

    def export_rc(self, folder: str | None = None) -> Path | None:
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Export Resources (.rc) to Folder",
                                                      str(self.path.parent))
        if not folder:
            return None
        p = RC.export_rc(self.doc.resources, folder, self.path.stem)
        self.message.emit(f"Exported {p}")
        return p

    def import_rc(self, path: str | None = None) -> bool:
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Import Resources (.rc)", str(self.path.parent),
                                                  "Resource scripts (*.rc);;All files (*.*)")
        if not path:
            return False
        try:
            entries = RC.import_rc(path)
        except (RC.RcError, ValueError, OSError) as e:
            QMessageBox.warning(self, "Import .rc", f"Cannot import {Path(path).name}:\n{e}")
            return False
        self.doc.replace_all_resources(entries)
        self.after_edit(f"Imported {len(entries)} resources from {Path(path).name}", reload_tree=True)
        return True

    # ---------------------------------------------------------------- code tab
    def _build_code(self) -> None:
        w = QSplitter()
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.func_filter = QLineEdit()
        self.func_filter.setPlaceholderText("Filter functions (name or address)")
        self.func_filter.textChanged.connect(self._filter_funcs)
        ll.addWidget(self.func_filter)
        self.funcs = QTreeWidget()
        self.funcs.setHeaderLabels(["Address", "Name", "Size"])
        self.funcs.setProperty("i18n_skip_items", True)
        self.funcs.setColumnWidth(0, 110)
        self.funcs.setColumnWidth(1, 220)
        self.funcs.currentItemChanged.connect(lambda cur, _p: cur is not None and self.show_code(cur.data(0, ROLE),
                                                                                                 switch=False))
        ll.addWidget(self.funcs, 1)
        self.side = QTabWidget()
        self.imports_list = QListWidget()
        self.strings_list = QListWidget()
        self.xrefs_list = QListWidget()
        for lw in (self.imports_list, self.strings_list, self.xrefs_list):
            lw.setProperty("i18n_skip_items", True)
            lw.itemDoubleClicked.connect(self._side_activated)
        self.side.addTab(self.xrefs_list, "Called From")
        self.side.addTab(self.imports_list, "Imports")
        self.side.addTab(self.strings_list, "Strings")
        ll.addWidget(self.side, 1)
        w.addWidget(left)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.goto = QLineEdit()
        self.goto.setPlaceholderText("Go to address / name")
        self.goto.returnPressed.connect(self._goto)
        bar.addWidget(self.goto)
        for text, fn in (("Edit Instruction...", self.edit_instruction), ("NOP Instruction", self.nop_instruction),
                         ("Follow", self.follow), ("Rename...", self.rename_function),
                         ("Decompile (Ghidra)", self.decompile)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            bar.addWidget(b)
        rl.addLayout(bar)
        self.code_view = QPlainTextEdit()
        self.code_view.setReadOnly(True)
        self.code_view.setFont(mono())
        self.code_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.code_view.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.code_view.mouseDoubleClickEvent = self._code_dbl
        rl.addWidget(self.code_view, 3)
        self.pseudo = QPlainTextEdit()
        self.pseudo.setReadOnly(True)
        self.pseudo.setFont(mono())
        self.pseudo.setPlaceholderText("Pseudo-C (Decompile with Ghidra, when Ghidra is installed)")
        self.pseudo.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        rl.addWidget(self.pseudo, 1)
        w.addWidget(right)
        w.setSizes([340, 800])
        self.code_tab = w
        self.current_func = 0
        self.tabs.addTab(w, "Code")

    def fill_functions(self) -> None:
        an = self.doc._analysis
        if an is None:
            return
        self.funcs.blockSignals(True)
        self.funcs.clear()
        handlers = {e.pfn for m in self.maps() for e in m.entries}
        for va in sorted(an.functions, key=lambda v: (v not in handlers, v)):
            f = an.functions[va]
            it = QTreeWidgetItem([f"{va:08X}", f.name, str(f.size)])
            it.setData(0, ROLE, va)
            if va in handlers:
                it.setForeground(1, QBrush(QColor("#2e7d32")))
            self.funcs.addTopLevelItem(it)
        self.funcs.blockSignals(False)
        self.imports_list.clear()
        for slot, label in sorted(an.imports.items(), key=lambda kv: kv[1].lower()):
            it = QListWidgetItem(f"{label}   [0x{slot:X}]")
            it.setData(ROLE, ("import", slot))
            self.imports_list.addItem(it)
        self.strings_list.clear()
        for va, s in list(sorted(an.strings.items()))[:20000]:
            it = QListWidgetItem(f"{va:08X}  {'L' if s.wide else ''}{s.text[:120]!r}")
            it.setData(ROLE, ("string", va))
            self.strings_list.addItem(it)

    def _filter_funcs(self, text: str) -> None:
        t = text.lower()
        for i in range(self.funcs.topLevelItemCount()):
            it = self.funcs.topLevelItem(i)
            it.setHidden(bool(t) and t not in it.text(0).lower() and t not in it.text(1).lower())

    def show_code(self, va: int, switch: bool = True) -> None:
        an = self.ensure_analysis()
        if va not in an.functions and an.function_at(va) is None:
            an.add_function(va, None, "user")
            an.reclose()
        f = an.function_at(va) or an.functions.get(va)
        self.current_func = f.va if f else va
        self.code_view.setPlainText(an.listing_text(va))
        if f is not None and f.va != va:
            self._select_line(va)
        self.xrefs_list.clear()
        for src in an.xrefs_to(self.current_func)[:500]:
            it = QListWidgetItem(f"{src:08X}  {an.name_of(src)}")
            it.setData(ROLE, ("code", src))
            self.xrefs_list.addItem(it)
        for m in self.maps():
            for e in m.entries:
                if e.pfn == self.current_func:
                    it = QListWidgetItem(f"message map {m.label}: {e.macro()}")
                    it.setData(ROLE, ("mfc", m.va))
                    self.xrefs_list.addItem(it)
        c = self._ghidra.get(self.current_func)
        self.pseudo.setPlainText(c or "")
        if switch:
            self.tabs.setCurrentWidget(self.code_tab)
            self.side.setCurrentWidget(self.xrefs_list)
        self.message.emit(f"{an.name_of(self.current_func)} at 0x{self.current_func:X}")

    def _select_line(self, va: int) -> None:
        doc = self.code_view.document()
        key = f"{va:08X}"
        for i in range(doc.blockCount()):
            b = doc.findBlockByNumber(i)
            if b.text().startswith(key):
                cur = self.code_view.textCursor()
                cur.setPosition(b.position())
                cur.movePosition(cur.MoveOperation.EndOfBlock, cur.MoveMode.KeepAnchor)
                self.code_view.setTextCursor(cur)
                self.code_view.centerCursor()
                return

    def selected_va(self) -> int | None:
        line = self.code_view.textCursor().block().text()
        m = re.match(r"([0-9A-F]{8,16})\s", line)
        return int(m.group(1), 16) if m else None

    def _line_target(self) -> int | None:
        va = self.selected_va()
        if va is None:
            return None
        ln = next(iter(self.doc.analysis().disasm(va, 16, max_lines=1)), None)
        return ln.target if ln is not None else None

    def _code_dbl(self, e) -> None:
        QPlainTextEdit.mouseDoubleClickEvent(self.code_view, e)
        self.follow()

    def follow(self) -> None:
        t = self._line_target()
        if t is not None and self.doc.img.is_code_va(t):
            self.show_code(t)

    def _goto(self) -> None:
        text = self.goto.text().strip()
        an = self.ensure_analysis()
        try:
            va = _int(text)
        except ValueError:
            va = next((v for v, n in an.names.items() if n.lower() == text.lower()), None) or \
                next((v for v, n in an.names.items() if text.lower() in n.lower()), None)
        if va is None or not self.doc.img.valid_va(va):
            self.message.emit(f"Not found: {text}")
            return
        self.show_code(va)
        self._select_line(va)

    def _side_activated(self, item) -> None:
        data = item.data(ROLE)
        if not data:
            return
        kind, va = data
        if kind == "code":
            self.show_code(va)
            self._select_line(va)
        elif kind == "mfc":
            self.tabs.setCurrentWidget(self.mfc_tab)
        else:
            refs = self.doc.analysis().xrefs_to(va)
            if refs:
                self.show_code(refs[0])
                self._select_line(refs[0])
            else:
                self.message.emit("No code reference found.")

    def edit_instruction(self, va: int | None = None, asm: str | None = None, count: int = 1) -> bool:
        va = va if va is not None else self.selected_va()
        if va is None:
            self.message.emit("Click an instruction line first.")
            return False
        if asm is not None:                            # programmatic (tests / scripts)
            self.doc.patch_instructions(va, asm, count)
        else:
            dlg = EditInstructionDialog(self, va)
            if not dlg.exec():
                return False
        self.after_edit(f"Instruction at 0x{va:X} edited")
        self.show_code(self.current_func, switch=False)
        self._select_line(va)
        return True

    def nop_instruction(self) -> None:
        va = self.selected_va()
        if va is None:
            return
        if QMessageBox.question(self, "NOP Instruction", f"Replace the instruction at 0x{va:X} with NOPs?") != \
                QMessageBox.StandardButton.Yes:
            return
        try:
            self.doc.nop_instructions(va, 1)
        except EditError as e:
            QMessageBox.warning(self, "NOP Instruction", str(e))
            return
        self.after_edit(f"NOP at 0x{va:X}")
        self.show_code(self.current_func, switch=False)

    def rename_function(self) -> None:
        an = self.ensure_analysis()
        if not self.current_func:
            return
        text, ok = QInputDialog.getText(self, "Rename Function", "Name:", text=an.name_of(self.current_func))
        if ok and text.strip():
            an.rename(self.current_func, text.strip())
            self.fill_functions()
            self.show_code(self.current_func, switch=False)

    def decompile(self) -> None:
        try:
            from ..firmware.analysis import ghidra
        except Exception:  # noqa: BLE001
            QMessageBox.information(self, "Decompile", "Ghidra support is not available in this IDE build.")
            return
        ok, info = ghidra.available()
        if not ok:
            QMessageBox.information(self, "Decompile", info)
            return
        va = self.current_func
        if not va:
            return
        import tempfile
        import threading
        work = Path(tempfile.mkdtemp(prefix="radpe_ghidra_"))
        self.pseudo.setPlainText("Running Ghidra headless (this can take a few minutes) ...")
        result = {}

        def run():
            result["r"] = ghidra.analyze(self.path, work, raw=False, entries=[va], max_decompile=400)
        t = threading.Thread(target=run, daemon=True)
        t.start()

        def poll():
            if t.is_alive():
                QTimer.singleShot(500, poll)
                return
            r = result.get("r")
            if r is None or r.error:
                self.pseudo.setPlainText(f"Ghidra: {r.error if r else 'failed'}")
                return
            for f in r.functions:
                c = r.decompiled.get(f.name)
                if c:
                    self._ghidra[f.address] = c
            self.pseudo.setPlainText(self._ghidra.get(va) or "Ghidra did not decompile this function.")
        QTimer.singleShot(500, poll)

    # ---------------------------------------------------------------- MFC tab
    def _build_mfc(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        info = QLabel("MFC message maps found in the program (class names from RTTI). Each entry links a Windows "
                      "message / control notification / menu command to a handler function. Retarget points an entry "
                      "at another existing function; entries can be removed, and added again only where a removal "
                      "freed a slot (the table is never moved or enlarged).")
        info.setWordWrap(True)
        lay.addWidget(info)
        self.mfc_tree = QTreeWidget()
        self.mfc_tree.setHeaderLabels(["Class / event", "ID", "Handler", "Macro"])
        self.mfc_tree.setProperty("i18n_skip_items", True)
        self.mfc_tree.setColumnWidth(0, 260)
        self.mfc_tree.setColumnWidth(1, 90)
        self.mfc_tree.setColumnWidth(2, 260)
        self.mfc_tree.itemDoubleClicked.connect(lambda it, _c: self._mfc_show(it))
        lay.addWidget(self.mfc_tree, 1)
        row = QHBoxLayout()
        for text, fn in (("Show Handler Code", lambda: self._mfc_show(self.mfc_tree.currentItem())),
                         ("Retarget Handler...", self._mfc_retarget), ("Remove Entry", self._mfc_remove),
                         ("Add Entry...", self._mfc_add), ("Find Dialog", self._mfc_dialog)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)
        self.mfc_tab = w
        self.tabs.addTab(w, "MFC Events")

    def fill_mfc(self) -> None:
        an = self.doc._analysis
        self.mfc_tree.clear()
        cmds = {}
        for e in self.doc.find(R.RT_MENU):
            try:
                cmds.update(dict(R.menu_commands(R.parse_menu(e.data).items)))
            except Exception:  # noqa: BLE001
                pass
        for m in self.maps():
            base = next((b.label for b in self.maps() if b.va == m.base_map_va), m.base_label or "")
            label = m.label + (" (name guessed)" if m.name_guessed else "")
            free = self.doc.free_slots(m)
            ti = QTreeWidgetItem([label, "", f"base: {base}" if base else "",
                                  f"{len(m.entries)} entries" + (f", {free} free slot(s)" if free else "")])
            ti.setData(0, ROLE, ("map", m.va))
            self.mfc_tree.addTopLevelItem(ti)
            for e in m.entries:
                name = an.name_of(e.pfn) if an else f"sub_{e.pfn:X}"
                idtext = (str(e.id) if e.id == e.last_id else f"{e.id}-{e.last_id}") if e.id or e.last_id else ""
                if e.id in cmds:
                    idtext += f"  ({cmds[e.id]})"
                ci = QTreeWidgetItem([e.event_text(), idtext, name, e.macro(name.split("::")[-1])])
                ci.setData(0, ROLE, ("entry", m.va, e.index))
                ti.addChild(ci)
            ti.setExpanded(bool(m.entries) and not m.name_guessed)

    def _mfc_sel(self, item=None):
        item = item or self.mfc_tree.currentItem()
        if item is None:
            return None, None
        d = item.data(0, ROLE)
        if not d:
            return None, None
        m = next((x for x in self.maps() if x.va == d[1]), None)
        if m is None:
            return None, None
        if d[0] == "entry" and d[2] < len(m.entries):
            return m, m.entries[d[2]]
        return m, None

    def _mfc_show(self, item) -> None:
        m, e = self._mfc_sel(item)
        if e is not None:
            self.show_code(e.pfn)

    def retarget_dialog(self, e: M.MsgEntry, new_pfn: int | None = None) -> bool:
        if new_pfn is None:
            dlg = FunctionPicker(self, f"Retarget {e.event_text()} (ID {e.id})", e.pfn)
            if not dlg.exec() or dlg.value() is None:
                return False
            new_pfn = dlg.value()
            if QMessageBox.question(
                    self, "Retarget Handler",
                    f"Point {e.macro()} at {self.doc.analysis().name_of(new_pfn)}?\n\nThe new function receives the "
                    "same arguments as the old one; pick a handler of the same kind (for example another "
                    "BN_CLICKED / ON_COMMAND handler), or the program may crash. You can Undo, and the original "
                    "file is never changed.") != QMessageBox.StandardButton.Yes:
                return False
        try:
            self.doc.mfc_retarget(e, new_pfn)
        except EditError as ex:
            QMessageBox.warning(self, "Retarget Handler", str(ex))
            return False
        self.after_edit(f"Handler of {e.event_text()} {e.id} -> 0x{new_pfn:X}")
        self.fill_mfc()
        return True

    def _mfc_retarget(self) -> None:
        _m, e = self._mfc_sel()
        if e is not None:
            self.retarget_dialog(e)

    def _mfc_remove(self) -> None:
        m, e = self._mfc_sel()
        if e is None:
            return
        if QMessageBox.question(self, "Remove Entry", f"Remove {e.macro()} from the message map of {m.label}?\n"
                                "The event will no longer be handled by this class.") != QMessageBox.StandardButton.Yes:
            return
        self.doc.mfc_remove_entry(m, e.index)
        self.after_edit(f"Removed {e.macro()}")
        self.fill_mfc()

    def _mfc_add(self) -> None:
        m, _e = self._mfc_sel()
        if m is None:
            return
        if self.doc.free_slots(m) < 1:
            QMessageBox.information(self, "Add Entry", f"The message map of {m.label} has no free slot. An entry can "
                                    "only be added where one was removed before (the table is not moved or enlarged).")
            return
        text, ok = QInputDialog.getText(self, "Add Entry", "Control or command ID (BN_CLICKED / ON_COMMAND):")
        if not ok or not text.strip():
            return
        try:
            cid = _int(text)
        except ValueError:
            return
        dlg = FunctionPicker(self, f"Handler for ID {cid}")
        if not dlg.exec() or dlg.value() is None:
            return
        try:
            self.doc.mfc_add_entry(m, M.WM_COMMAND, 0, cid, None, M.command_signature(self.maps()), dlg.value())
        except EditError as ex:
            QMessageBox.warning(self, "Add Entry", str(ex))
            return
        self.after_edit(f"Added ON_COMMAND({cid})")
        self.fill_mfc()

    def _mfc_dialog(self) -> None:
        m, _e = self._mfc_sel()
        if m is None:
            return
        for e in self.doc.find(R.RT_DIALOG):
            try:
                d = R.parse_dialog(e.data)
            except Exception:  # noqa: BLE001
                continue
            if M.guess_dialog_owner([m], {c.id for c in d.controls}) is m:
                self.select_resource(e.type, e.name, e.lang)
                return
        self.message.emit(f"No dialog matches the controls handled by {m.label}.")

    # ---------------------------------------------------------------- patches / info
    def _build_patches(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel("Code and message-map changes in this session (resources are listed in the tree). "
                             "Undo works for every change; Revert undoes one patch."))
        self.patch_list = QListWidget()
        self.patch_list.setProperty("i18n_skip_items", True)
        lay.addWidget(self.patch_list, 1)
        b = QPushButton("Revert Patch")
        b.clicked.connect(self._revert)
        lay.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)
        self.tabs.addTab(w, "Patches")

    def fill_patches(self) -> None:
        self.patch_list.clear()
        for p in self.doc.patches:
            it = QListWidgetItem(f"0x{p.va:X}  {p.desc}")
            it.setData(ROLE, id(p))
            self.patch_list.addItem(it)

    def _revert(self) -> None:
        it = self.patch_list.currentItem()
        if it is None:
            return
        rec = next((p for p in self.doc.patches if id(p) == it.data(ROLE)), None)
        if rec is not None:
            self.doc.revert_patch(rec)
            self.doc.refresh_maps()
            self.after_edit("Patch reverted")
            self.fill_mfc()

    def _build_info(self) -> None:
        self.info_view = QPlainTextEdit()
        self.info_view.setReadOnly(True)
        self.info_view.setFont(mono())
        self.info_view.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.tabs.addTab(self.info_view, "Info")

    def fill_info(self) -> None:
        img = self.doc.img
        lines = [f"File: {self.path}", f"Machine: {img.machine_name}   {'PE32+ (64-bit)' if img.is64 else 'PE32 (32-bit)'}"
                 f"   {'DLL' if img.is_dll else 'EXE'}",
                 f"Image base: 0x{img.image_base:X}   Entry point: 0x{img.entry_va:X}   Subsystem: {img.subsystem}",
                 f"DllCharacteristics: 0x{img.dll_characteristics:04X}"
                 f"{'  ASLR' if img.dll_characteristics & 0x40 else ''}{'  NX' if img.dll_characteristics & 0x100 else ''}"
                 f"{'  CFG' if img.dll_characteristics & 0x4000 else ''}",
                 f"Checksum: 0x{img.checksum:08X} (computed 0x{img.compute_checksum():08X})",
                 f"Signed: {'yes' if img.has_certificate() else 'no'}   Overlay: {len(img.overlay())} bytes", "",
                 "Sections:", f"  {'Name':<9}{'VA':>10}{'VSize':>10}{'Raw':>10}{'RawSize':>10}  Flags"]
        for s in img.sections:
            lines.append(f"  {s.name:<9}{s.vaddr:>10X}{s.vsize:>10X}{s.raw_ptr:>10X}{s.raw_size:>10X}  {s.flags_text()}")
        lines += ["", f"Imports ({len(img.imports())}):"]
        last = None
        for im in img.imports():
            if im.dll != last:
                lines.append(f"  {im.dll}{' (delay-load)' if im.delay else ''}")
                last = im.dll
            lines.append(f"      {im.name}")
        ex = img.exports()
        if ex:
            lines += ["", f"Exports ({len(ex)}):"] + [f"  {e.ordinal:>5}  0x{e.rva:08X}  {e.name}"
                                                      + (f" -> {e.forwarder}" if e.forwarder else "") for e in ex]
        self.info_view.setPlainText("\n".join(lines))

    def _tab_changed(self, i: int) -> None:
        w = self.tabs.widget(i)
        if w is self.code_tab:
            self.ensure_analysis()
            if self.funcs.topLevelItemCount() == 0:
                self.fill_functions()
        elif w is self.mfc_tab:
            self.ensure_analysis()
            self.fill_mfc()
        elif w is self.info_view:
            self.fill_info()

    # ---------------------------------------------------------------- save
    def save(self) -> bool:
        default = str(self.save_path or self.doc.default_save_path())
        path, _ = QFileDialog.getSaveFileName(self, "Save Edited Program As", default,
                                              "Programs (*.exe *.dll *.ocx *.cpl);;All files (*.*)")
        if not path:
            return False
        if Path(path).resolve() == self.path.resolve():
            if QMessageBox.question(self, "Save", "Replace the original file? A copy is kept as "
                                    f"{self.path.name}.bak.") != QMessageBox.StandardButton.Yes:
                return False
        try:
            target, notes = self.save_to(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Save", f"Cannot save:\n{e}")
            return False
        QMessageBox.information(self, "Save", f"Saved {target.name}." + ("\n\n" + "\n".join(notes) if notes else ""))
        return True

    def save_to(self, path) -> tuple[Path, list[str]]:
        target, notes = self.doc.save(path)
        self.save_path = target
        self.saved.emit(str(target))
        self._doc_changed()
        self.message.emit(f"Saved {target}")
        return target, notes
