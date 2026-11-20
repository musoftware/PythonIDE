"""Icon / Image Editor document tab (like the VB 2005 / Visual Studio image editor).

Tools on the left, the zoomable canvas in the middle, *Image Types* (icon sizes) + *Layers* + an
actual-size preview on the right and the colour palette at the bottom.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QColor, QIcon, QImage, QKeySequence, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                             QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMenu, QMessageBox, QPushButton, QScrollArea, QSlider, QSpinBox,
                             QSplitter, QToolBar, QToolButton, QVBoxLayout, QWidget, QFontDialog)

from .. import theme
from . import ICON_SIZES
from .canvas import TOOLS, PixelCanvas, checker_brush
from .document import ICON_EXTS, ImageDocument

FILTER_OPEN = "Images (*.ico *.cur *.png *.bmp *.gif *.jpg *.jpeg);;All files (*)"
FILTER_SAVE = ("Icon (*.ico);;Cursor (*.cur);;PNG image (*.png);;Bitmap (*.bmp);;GIF image (*.gif);;"
               "JPEG image (*.jpg)")

# the 28 colours of the VB / Paint palette
PALETTE = ["#000000", "#808080", "#800000", "#808000", "#008000", "#008080", "#000080", "#800080",
           "#808040", "#004040", "#0080FF", "#004080", "#4000FF", "#804000",
           "#FFFFFF", "#C0C0C0", "#FF0000", "#FFFF00", "#00FF00", "#00FFFF", "#0000FF", "#FF00FF",
           "#FFFF80", "#00FF80", "#80FFFF", "#8080FF", "#FF0080", "#FF8040"]


# ---------------------------------------------------------------------- small painted icons
def tool_icon(tool: str, size: int = 20) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    fg = QColor(theme.color("text"))
    p.setPen(QPen(fg, 1.6))
    s = size
    if tool == "select":
        p.setPen(QPen(fg, 1.2, Qt.PenStyle.DashLine))
        p.drawRect(3, 4, s - 7, s - 9)
    elif tool == "pencil":
        p.drawLine(4, s - 4, s - 5, 5)
        p.drawLine(4, s - 4, 4, s - 8)
        p.drawLine(4, s - 4, 8, s - 4)
    elif tool == "eraser":
        p.setBrush(QColor("#F4A0B0"))
        p.drawPolygon(*[QPoint(*xy) for xy in ((3, 13), (10, 6), (17, 11), (10, 18))])
    elif tool == "fill":
        p.setBrush(QColor("#3B82F6"))
        p.drawPolygon(*[QPoint(*xy) for xy in ((4, 10), (10, 4), (16, 10), (10, 16))])
        p.drawEllipse(15, 13, 3, 4)
    elif tool == "picker":
        p.drawLine(4, s - 4, s - 7, 7)
        p.setBrush(fg)
        p.drawEllipse(s - 9, 3, 6, 6)
    elif tool == "line":
        p.drawLine(4, s - 4, s - 4, 4)
    elif tool in ("rect", "rect_fill"):
        if tool == "rect_fill":
            p.setBrush(fg)
        p.drawRect(3, 5, s - 7, s - 10)
    elif tool in ("ellipse", "ellipse_fill"):
        if tool == "ellipse_fill":
            p.setBrush(fg)
        p.drawEllipse(3, 5, s - 7, s - 10)
    elif tool == "text":
        f = p.font()
        f.setBold(True)
        f.setPixelSize(s - 4)
        p.setFont(f)
        p.drawText(QRect(0, 0, s, s), int(Qt.AlignmentFlag.AlignCenter), "A")
    elif tool == "hotspot":
        p.drawLine(s // 2, 2, s // 2, s - 2)
        p.drawLine(2, s // 2, s - 2, s // 2)
        p.drawEllipse(s // 2 - 4, s // 2 - 4, 8, 8)
    p.end()
    return QIcon(pm)


def swatch(color: QColor, size: QSize = QSize(18, 18)) -> QPixmap:
    pm = QPixmap(size)
    p = QPainter(pm)
    p.fillRect(pm.rect(), checker_brush(4))
    p.fillRect(pm.rect(), color)
    p.setPen(QColor("#606060"))
    p.drawRect(pm.rect().adjusted(0, 0, -1, -1))
    p.end()
    return pm


def thumb(img: QImage, size: int = 32) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    sc = img.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation if img.width() <= size
                    else Qt.TransformationMode.SmoothTransformation)
    p.drawImage((size - sc.width()) // 2, (size - sc.height()) // 2, sc)
    p.end()
    return QIcon(pm)


# ---------------------------------------------------------------------- palette
class ColorWell(QToolButton):
    def __init__(self, color: QColor, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.setFixedSize(20, 20)
        self.setAutoRaise(True)
        self._refresh()

    def set_color(self, c: QColor) -> None:
        self.color = QColor(c)
        self._refresh()

    def _refresh(self) -> None:
        self.setIcon(QIcon(swatch(self.color, QSize(16, 16))))
        self.setIconSize(QSize(16, 16))
        self.setToolTip(f"{self.color.name(QColor.NameFormat.HexArgb).upper()}  (left click = primary, "
                        "right click = secondary, double click = edit)")


class PaletteBar(QWidget):
    """Primary / secondary colour, the 28-colour palette, a transparent well, alpha and hex."""
    def __init__(self, canvas: PixelCanvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        self.primary = QPushButton()
        self.secondary = QPushButton()
        for b, which in ((self.primary, 0), (self.secondary, 1)):
            b.setFixedSize(34, 34)
            b.setIconSize(QSize(26, 26))
            b.setToolTip(("Primary (left button)" if which == 0 else "Secondary (right button)") +
                         " colour - click to choose any colour with alpha")
            b.clicked.connect(lambda _c=False, w=which: self.edit(w))
        swap = QToolButton()
        swap.setText("⇄")
        swap.setToolTip("Swap primary and secondary colours")
        swap.clicked.connect(self.swap)
        lay.addWidget(self.primary)
        lay.addWidget(self.secondary)
        lay.addWidget(swap)
        grid = QGridLayout()
        grid.setSpacing(1)
        self.wells: list[ColorWell] = []
        trans = ColorWell(QColor(0, 0, 0, 0))
        trans.setToolTip("Transparent (left click = primary, right click = secondary)")
        grid.addWidget(trans, 0, 0, 2, 1)
        self.wells.append(trans)
        for i, c in enumerate(PALETTE):
            w = ColorWell(QColor(c))
            grid.addWidget(w, i // 14, 1 + i % 14)
            self.wells.append(w)
        for w in self.wells:
            w.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            w.clicked.connect(lambda _c=False, w=w: self.pick(w.color, 0))
            w.customContextMenuRequested.connect(lambda _p, w=w: self.pick(w.color, 1))
        lay.addLayout(grid)
        lay.addSpacing(10)
        lay.addWidget(QLabel("Alpha:"))
        self.alpha = QSlider(Qt.Orientation.Horizontal)
        self.alpha.setRange(0, 255)
        self.alpha.setFixedWidth(110)
        self.alpha.setToolTip("Opacity of the primary colour (0 = transparent, 255 = opaque)")
        self.alpha.valueChanged.connect(self._alpha_changed)
        self.alpha_lbl = QLabel("255")
        self.alpha_lbl.setMinimumWidth(26)
        lay.addWidget(self.alpha)
        lay.addWidget(self.alpha_lbl)
        self.hex = QLineEdit()
        self.hex.setFixedWidth(90)
        self.hex.setToolTip("Primary colour as #RRGGBB or #AARRGGBB")
        self.hex.editingFinished.connect(self._hex_changed)
        lay.addWidget(self.hex)
        lay.addStretch(1)
        canvas.colorPicked.connect(lambda c, w: self.refresh())
        self.refresh()

    def pick(self, c: QColor, which: int) -> None:
        if which == 0:
            self.canvas.primary = QColor(c)
        else:
            self.canvas.secondary = QColor(c)
        self.refresh()

    def edit(self, which: int) -> None:
        cur = self.canvas.primary if which == 0 else self.canvas.secondary
        c = QColorDialog.getColor(cur, self, "Choose colour", QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self.pick(c, which)

    def swap(self) -> None:
        cv = self.canvas
        cv.primary, cv.secondary = cv.secondary, cv.primary
        self.refresh()

    def _alpha_changed(self, v: int) -> None:
        c = QColor(self.canvas.primary)
        c.setAlpha(v)
        self.canvas.primary = c
        self.alpha_lbl.setText(str(v))
        self.primary.setIcon(QIcon(swatch(c, QSize(26, 26))))
        self.hex.setText(c.name(QColor.NameFormat.HexArgb).upper())

    def _hex_changed(self) -> None:
        t = self.hex.text().strip()
        c = QColor(t if t.startswith("#") else "#" + t)
        if c.isValid():
            self.pick(c, 0)

    def refresh(self) -> None:
        cv = self.canvas
        self.primary.setIcon(QIcon(swatch(cv.primary, QSize(26, 26))))
        self.secondary.setIcon(QIcon(swatch(cv.secondary, QSize(26, 26))))
        self.alpha.blockSignals(True)
        self.alpha.setValue(cv.primary.alpha())
        self.alpha.blockSignals(False)
        self.alpha_lbl.setText(str(cv.primary.alpha()))
        self.hex.setText(cv.primary.name(QColor.NameFormat.HexArgb).upper())


# ---------------------------------------------------------------------- dialogs
class NewImageDialog(QDialog):
    """File > New > Icon / Cursor / Image."""
    def __init__(self, parent=None, kind: str = "icon"):
        super().__init__(parent)
        self.setWindowTitle("New Image")
        lay = QFormLayout(self)
        self.kind = QComboBox()
        self.kind.addItems(["Icon (.ico)", "Cursor (.cur)", "PNG image", "Bitmap (.bmp)"])
        self.kind.setCurrentIndex({"icon": 0, "cursor": 1, "png": 2, "bmp": 3}.get(kind, 0))
        lay.addRow("Type:", self.kind)
        self.name = QLineEdit("Icon1")
        lay.addRow("Name:", self.name)
        self.sizes_box = QWidget()
        sl = QHBoxLayout(self.sizes_box)
        sl.setContentsMargins(0, 0, 0, 0)
        self.size_checks = {}
        for s in ICON_SIZES:
            cb = QCheckBox(f"{s}")
            cb.setChecked(s in (16, 32, 48, 256))
            self.size_checks[s] = cb
            sl.addWidget(cb)
        lay.addRow("Icon sizes:", self.sizes_box)
        self.w = QSpinBox()
        self.h = QSpinBox()
        for sp in (self.w, self.h):
            sp.setRange(1, 4096)
            sp.setValue(64)
        wh = QHBoxLayout()
        wh.addWidget(self.w)
        wh.addWidget(QLabel("x"))
        wh.addWidget(self.h)
        self.wh_box = QWidget()
        self.wh_box.setLayout(wh)
        lay.addRow("Size:", self.wh_box)
        self.transparent = QCheckBox("Transparent background")
        self.transparent.setChecked(True)
        lay.addRow("", self.transparent)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addRow(bb)
        self.kind.currentIndexChanged.connect(self._update)
        self._update()

    def _update(self) -> None:
        i = self.kind.currentIndex()
        self.sizes_box.setEnabled(i <= 1)
        self.wh_box.setEnabled(i >= 2)
        stem = self.name.text()
        if stem in ("Icon1", "Cursor1", "Image1", ""):
            self.name.setText(["Icon1", "Cursor1", "Image1", "Image1"][i])

    def extension(self) -> str:
        return [".ico", ".cur", ".png", ".bmp"][self.kind.currentIndex()]

    def make_document(self) -> ImageDocument:
        i = self.kind.currentIndex()
        if i <= 1:
            sizes = [s for s, cb in self.size_checks.items() if cb.isChecked()] or [32]
            return ImageDocument.new_icon(sizes, cursor=i == 1)
        bg = None if self.transparent.isChecked() else QColor("#FFFFFF")
        return ImageDocument.new_image(self.w.value(), self.h.value(), bg)


def ask_size(parent, title: str, w: int = 32, h: int = 32, square: bool = True):
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    lay = QFormLayout(dlg)
    combo = QComboBox()
    combo.setEditable(True)
    combo.addItems([f"{s}x{s}" for s in ICON_SIZES] + ["128x128"])
    combo.setCurrentText(f"{w}x{h}")
    lay.addRow("Size (W x H):", combo)
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    lay.addRow(bb)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    try:
        a, _, b = combo.currentText().lower().partition("x")
        ww, hh = int(a), int(b or a)
    except ValueError:
        return None
    if not (1 <= ww <= 4096 and 1 <= hh <= 4096):
        return None
    return ww, hh


# ---------------------------------------------------------------------- the editor tab
class IconEditor(QWidget):
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal()

    def __init__(self, doc: ImageDocument | None = None, path: Path | None = None, parent=None):
        super().__init__(parent)
        if doc is None:
            doc = ImageDocument(path) if path is not None else ImageDocument.new_icon()
        self.doc = doc
        if path is not None and doc.path is None:
            doc.path = Path(path)
        self.canvas = PixelCanvas(doc)
        self._build()
        doc.modifiedChanged.connect(self.modifiedChanged)
        doc.structureChanged.connect(self._fill_lists)
        doc.changed.connect(self._on_changed)
        theme.changed.connect(self._retheme)
        self._fill_lists()
        self._on_changed()

    @property
    def path(self) -> Path:
        return self.doc.path or Path("Untitled" + (".cur" if self.doc.cursor else ".ico" if self.doc.is_icon
                                                   else ".png"))

    # ---------------------------------------------------------------- UI
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        tb = QToolBar()
        tb.setIconSize(QSize(16, 16))
        self.toolbar = tb
        tb.addAction("Save", self.save).setToolTip("Save (Ctrl+S)")
        tb.addAction("Save As...", self.save_as)
        tb.addSeparator()
        self.a_undo = tb.addAction("Undo", self.undo)
        self.a_redo = tb.addAction("Redo", self.redo)
        tb.addSeparator()
        tb.addWidget(QLabel(" Zoom: "))
        self.zoom = QComboBox()
        self.zoom.addItems([f"{z}x" for z in (1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32)])
        self.zoom.setCurrentText(f"{self.canvas.zoom}x")
        self.zoom.currentTextChanged.connect(lambda t: t.rstrip("x").isdigit() and
                                             self.canvas.set_zoom(int(t.rstrip("x"))))
        self.canvas.zoomChanged.connect(lambda z: (self.zoom.blockSignals(True), self.zoom.setCurrentText(f"{z}x"),
                                                   self.zoom.blockSignals(False)))
        tb.addWidget(self.zoom)
        self.grid_cb = QCheckBox("Grid")
        self.grid_cb.setChecked(True)
        self.grid_cb.toggled.connect(lambda on: (setattr(self.canvas, "grid", on), self.canvas.update()))
        tb.addWidget(self.grid_cb)
        tb.addSeparator()
        tb.addWidget(QLabel(" Pen size: "))
        self.pen = QSpinBox()
        self.pen.setRange(1, 16)
        self.pen.valueChanged.connect(lambda v: setattr(self.canvas, "pen_size", v))
        tb.addWidget(self.pen)
        font_btn = QToolButton()
        font_btn.setText("Text Font...")
        font_btn.clicked.connect(self._choose_font)
        tb.addWidget(font_btn)
        tb.addSeparator()
        img_btn = QToolButton()
        img_btn.setText("Image")
        img_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        img_btn.setMenu(self._image_menu())
        tb.addWidget(img_btn)
        gen = tb.addAction("Generate All Sizes", self.generate_sizes)
        gen.setToolTip("Make every icon size (16, 24, 32, 48, 64, 256) from the current image")
        root.addWidget(tb)

        body = QSplitter(Qt.Orientation.Horizontal)
        # tools
        tools = QWidget()
        tl = QGridLayout(tools)
        tl.setContentsMargins(4, 4, 4, 4)
        tl.setSpacing(2)
        self.tool_group = QActionGroup(self)
        self.tool_buttons: dict[str, QToolButton] = {}
        for i, (tid, label, key) in enumerate(TOOLS):
            act = QAction(tool_icon(tid), f"{label} ({key})", self)
            act.setCheckable(True)
            act.setData(tid)
            act.setShortcut(QKeySequence(key))
            act.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            act.triggered.connect(lambda _c=False, t=tid: self.set_tool(t))
            self.tool_group.addAction(act)
            self.addAction(act)
            b = QToolButton()
            b.setDefaultAction(act)
            b.setIconSize(QSize(20, 20))
            b.setAutoRaise(True)
            tl.addWidget(b, i // 2, i % 2)
            self.tool_buttons[tid] = b
        tl.setRowStretch(len(TOOLS) // 2 + 1, 1)
        tools.setFixedWidth(64)
        body.addWidget(tools)
        # canvas
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.canvas)
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        theme.role(self.scroll, "stage")
        body.addWidget(self.scroll)
        # right side
        side = QWidget()
        sl = QVBoxLayout(side)
        sl.setContentsMargins(4, 4, 4, 4)
        lbl = QLabel("Image Types")
        theme.role(lbl, "heading")
        sl.addWidget(lbl)
        self.frames = QListWidget()
        self.frames.setIconSize(QSize(32, 32))
        self.frames.currentRowChanged.connect(lambda r: r >= 0 and self.doc.select_frame(r))
        self.frames.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.frames.customContextMenuRequested.connect(self._frames_menu)
        sl.addWidget(self.frames, 2)
        fb = QHBoxLayout()
        for text, fn, tip in (("New...", self.new_frame, "New Image Type (another icon size)"),
                              ("Delete", self.delete_frame, "Delete this image type"),
                              ("All sizes", self.generate_sizes, "Generate all icon sizes from this image")):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            fb.addWidget(b)
        sl.addLayout(fb)
        lbl = QLabel("Layers")
        theme.role(lbl, "heading")
        sl.addWidget(lbl)
        self.layers = QListWidget()
        self.layers.currentRowChanged.connect(self._on_layer_row)
        self.layers.itemChanged.connect(self._on_layer_item)
        sl.addWidget(self.layers, 1)
        lb = QHBoxLayout()
        for text, fn, tip in (("+", self.doc.add_layer, "Add layer"), ("-", self.doc.remove_layer, "Delete layer"),
                              ("↑", lambda: self.doc.move_layer(1), "Move layer up"),
                              ("↓", lambda: self.doc.move_layer(-1), "Move layer down"),
                              ("Merge", self.doc.merge_down, "Merge down")):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            lb.addWidget(b)
        lb.addStretch(1)
        sl.addLayout(lb)
        lbl = QLabel("Preview")
        theme.role(lbl, "heading")
        sl.addWidget(lbl)
        self.preview = QLabel()
        self.preview.setMinimumHeight(70)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        sl.addWidget(self.preview)
        side.setMinimumWidth(190)
        body.addWidget(side)
        body.setStretchFactor(1, 1)
        body.setSizes([64, 600, 210])
        root.addWidget(body, 1)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)
        self.palette = PaletteBar(self.canvas)
        root.addWidget(self.palette)
        self.status = QLabel()
        theme.role(self.status, "muted")
        self.status.setContentsMargins(6, 0, 6, 3)
        root.addWidget(self.status)
        self.canvas.hover.connect(self._on_hover)
        self.set_tool("pencil")
        self.tool_buttons["hotspot"].setVisible(self.doc.cursor)

    def _image_menu(self) -> QMenu:
        m = QMenu(self)
        m.addAction("New Image Type...", self.new_frame)
        m.addAction("Delete Image Type", self.delete_frame)
        m.addAction("Generate All Icon Sizes", self.generate_sizes)
        m.addSeparator()
        m.addAction("Import Image into This Size...", lambda: self.import_image(False))
        m.addAction("Import Image into All Sizes...", lambda: self.import_image(True))
        m.addAction("Export All Sizes as PNG...", self.export_pngs)
        m.addSeparator()
        m.addAction("Resize / Canvas Size...", self.resize_image)
        m.addAction("Crop to Selection", self.canvas.crop_to_selection)
        m.addAction("Flip Horizontal", lambda: self.canvas.flip(True))
        m.addAction("Flip Vertical", lambda: self.canvas.flip(False))
        m.addAction("Rotate 90°", self.canvas.rotate90)
        m.addAction("Invert Colors", self.canvas.invert_colors)
        m.addSeparator()
        m.addAction("Select All", self.canvas.select_all)
        m.addAction("Deselect", self.canvas.deselect)
        return m

    def _retheme(self, _name: str = "") -> None:
        for tid, b in self.tool_buttons.items():
            b.defaultAction().setIcon(tool_icon(tid))
        self.canvas.update()
        self._on_changed()

    # ---------------------------------------------------------------- state
    def set_tool(self, tool: str) -> None:
        self.canvas.set_tool(tool)
        for a in self.tool_group.actions():
            a.setChecked(a.data() == tool)

    def _fill_lists(self) -> None:
        d = self.doc
        self.frames.blockSignals(True)
        self.frames.clear()
        for f in d.frames:
            it = QListWidgetItem(thumb(f.composite()), f.label)
            self.frames.addItem(it)
        self.frames.setCurrentRow(d.current)
        self.frames.blockSignals(False)
        self.layers.blockSignals(True)
        self.layers.clear()
        layers = d.frame.layers
        for la in reversed(layers):           # top layer first (like Paint.NET / Photoshop)
            it = QListWidgetItem(thumb(la.image, 24), la.name)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEditable)
            it.setCheckState(Qt.CheckState.Checked if la.visible else Qt.CheckState.Unchecked)
            self.layers.addItem(it)
        self.layers.setCurrentRow(len(layers) - 1 - d.layer)
        self.layers.blockSignals(False)
        self.tool_buttons["hotspot"].setVisible(d.cursor)
        self._on_changed()

    def _on_layer_row(self, row: int) -> None:
        if row >= 0:
            self.canvas.commit_floating()
            self.doc.layer = len(self.doc.frame.layers) - 1 - row

    def _on_layer_item(self, it: QListWidgetItem) -> None:
        i = len(self.doc.frame.layers) - 1 - self.layers.row(it)
        la = self.doc.frame.layers[i]
        if it.text() and it.text() != la.name:
            la.name = it.text()
        self.doc.set_layer_visible(i, it.checkState() == Qt.CheckState.Checked)

    def _on_changed(self) -> None:
        d = self.doc
        img = d.composite()
        pm = QPixmap(max(160, img.width() * 2 + 30), max(64, img.height() * 2 + 8))
        pm.fill(QColor(theme.color("base")))
        p = QPainter(pm)
        p.drawImage(4, 4, img)                                        # actual size
        if img.width() <= 128:
            p.drawImage(QRect(img.width() + 16, 4, img.width() * 2, img.height() * 2), img)
        p.end()
        self.preview.setPixmap(pm.scaled(min(pm.width(), 200), min(pm.height(), 300),
                                         Qt.AspectRatioMode.KeepAspectRatio)
                               if pm.width() > 200 else pm)
        it = self.frames.item(d.current)
        if it is not None:
            it.setIcon(thumb(img))
        self.a_undo.setEnabled(d.can_undo())
        self.a_redo.setEnabled(d.can_redo())
        self._on_hover(-1, -1)

    def _on_hover(self, x: int, y: int) -> None:
        f = self.doc.frame
        parts = [f"{f.width} x {f.height}", f"{len(self.doc.frames)} image type(s)"]
        if x >= 0:
            c = self.doc.pixel(x, y, merged=True)
            parts.insert(0, f"({x}, {y})  {c.name(QColor.NameFormat.HexArgb).upper()}")
        if self.doc.cursor:
            parts.append(f"hot spot {f.hotspot[0]},{f.hotspot[1]}")
        sel = self.canvas.selection
        if sel is not None:
            parts.append(f"selection {sel.width()}x{sel.height()}")
        self.status.setText("    ".join(parts))

    def _choose_font(self) -> None:
        f, ok = QFontDialog.getFont(self.canvas.text_font, self, "Text tool font")
        if ok:
            self.canvas.text_font = f

    def _frames_menu(self, pos) -> None:
        m = QMenu(self)
        m.addAction("New Image Type...", self.new_frame)
        m.addAction("Delete Image Type", self.delete_frame)
        m.addAction("Generate All Sizes from This", self.generate_sizes)
        m.exec(self.frames.mapToGlobal(pos))

    # ---------------------------------------------------------------- commands
    def new_frame(self) -> None:
        f = self.doc.frame
        r = ask_size(self, "New Image Type", f.width, f.height)
        if r:
            self.doc.add_frame(*r, from_current=True)

    def delete_frame(self) -> None:
        if len(self.doc.frames) > 1:
            self.doc.remove_frame(self.doc.current)

    def generate_sizes(self) -> None:
        self.canvas.commit_floating()
        self.doc.generate_sizes(ICON_SIZES)

    def import_image(self, all_sizes: bool, path: str | None = None) -> None:
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Import Image", str(self.path.parent), FILTER_OPEN)
        if path:
            try:
                self.doc.import_image(Path(path), all_sizes)
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(self, "Import Image", f"Cannot read the picture:\n{e}")

    def export_pngs(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Export all sizes as PNG", str(self.path.parent))
        if folder:
            out = self.doc.export_pngs(Path(folder), self.path.stem)
            QMessageBox.information(self, "Export", "Saved:\n" + "\n".join(p.name for p in out))

    def resize_image(self) -> None:
        f = self.doc.frame
        r = ask_size(self, "Resize Image", f.width, f.height)
        if not r:
            return
        scale = QMessageBox.question(self, "Resize", "Scale the picture to the new size?\n\n"
                                     "Yes = scale the pixels, No = change the canvas size only") == \
            QMessageBox.StandardButton.Yes
        self.doc.resize_canvas(*r, scale)

    def undo(self) -> None:
        self.canvas.commit_floating()
        self.doc.undo()

    def redo(self) -> None:
        self.doc.redo()

    def edit_op(self, op: str) -> None:
        cv = self.canvas
        {"undo": self.undo, "redo": self.redo, "copy": cv.copy, "cut": cv.cut, "paste": cv.paste,
         "delete": cv.delete, "select_all": cv.select_all}.get(op, lambda: None)()

    # ---------------------------------------------------------------- files
    def is_modified(self) -> bool:
        return self.doc.is_modified()

    def save(self) -> bool:
        if self.doc.path is None:
            return self.save_as()
        self.canvas.commit_floating()
        try:
            if self.doc.path.suffix.lower() in ICON_EXTS and any(f.width > 256 for f in self.doc.frames):
                QMessageBox.information(self, "Save", "Images larger than 256x256 are not stored in an icon.")
            self.doc.save()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Save", f"Cannot save {self.doc.path.name}:\n{e}")
            return False
        self.saved.emit()
        return True

    def save_as(self, path: str | None = None) -> bool:
        if path is None:
            default = str(self.path)
            path, _ = QFileDialog.getSaveFileName(self, "Save Image As", default, FILTER_SAVE)
            if not path:
                return False
        p = Path(path)
        if not p.suffix:
            p = p.with_suffix(".ico" if self.doc.is_icon else ".png")
        if p.suffix.lower() not in ICON_EXTS and len(self.doc.frames) > 1:
            QMessageBox.information(self, "Save As", f"{p.suffix} holds one picture: the current image type "
                                    f"({self.doc.frame.label}) is saved.")
        self.doc.path = p
        self.doc.cursor = p.suffix.lower() == ".cur"
        return self.save()

    def maybe_close(self) -> bool:
        if not self.is_modified():
            return True
        r = QMessageBox.question(self, "Image Editor", f"Save changes to {self.path.name}?",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Save:
            return self.save()
        return r == QMessageBox.StandardButton.Discard

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if not getattr(self, "_fitted", False):
            self._fitted = True
            self.canvas.fit_zoom(self.scroll.viewport().size())


__all__ = ["IconEditor", "NewImageDialog", "PaletteBar", "tool_icon", "FILTER_OPEN", "FILTER_SAVE"]
