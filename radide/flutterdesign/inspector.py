"""Properties inspector of the Flutter designer, driven by the catalog's property schemas (model.PropSpec kinds).

Editors: colour (alpha, Flutter palette, theme colours), EdgeInsets (all / symmetric / LTRB), border radius (all /
per corner), alignment (3x3 grid), Main / Cross axis alignment (pictured buttons), BoxDecoration (colour, gradient
with stops + angle, image with fit, border, radius, shadows, shape), TextStyle (Google font, size, weight, colour,
spacing, height, decoration), InputDecoration, ButtonStyle, ShapeBorder, icons (searchable picker of every
Material icon), images (project assets / import / URL), nav items, raw Dart (``{"$code"}``) for any property;
events (double-click = create the handler in the user Dart file, like VB) and entrance animations.
"""
from __future__ import annotations

import math

from PyQt6.QtCore import (QAbstractListModel, QModelIndex, QRectF, QSize, QSortFilterProxyModel, Qt,
                          QTimer, pyqtSignal)
from PyQt6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QColorDialog, QComboBox, QDialog,
                             QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
                             QHBoxLayout, QLabel, QLineEdit, QListView, QMenu, QPlainTextEdit, QPushButton,
                             QScrollArea, QSizePolicy, QSpinBox, QToolButton, QVBoxLayout, QWidget)

from . import iconfont
from . import model as M
from . import motion as MO
from . import variants_fd as VF
from .palette import type_icon

SCHEME_KEYS = ["primary", "onPrimary", "primaryContainer", "onPrimaryContainer", "secondary", "onSecondary",
               "secondaryContainer", "onSecondaryContainer", "tertiary", "surface", "onSurface", "onSurfaceVariant",
               "surfaceContainerLow", "surfaceContainer", "surfaceContainerHighest", "outline", "outlineVariant",
               "error", "onError", "inverseSurface"]
FLUTTER_SWATCHES = ["red", "pink", "purple", "deepPurple", "indigo", "blue", "lightBlue", "cyan", "teal", "green",
                    "lightGreen", "lime", "yellow", "amber", "orange", "deepOrange", "brown", "grey", "blueGrey"]
GOOGLE_FONTS_FALLBACK = ["Poppins", "Roboto", "Inter", "Montserrat", "Lato", "Open Sans", "Nunito", "Raleway",
                         "Rubik", "Work Sans", "DM Sans", "Manrope", "Outfit", "Playfair Display", "Merriweather",
                         "Lora", "Oswald", "Bebas Neue", "Pacifico", "Dancing Script", "Cairo", "Tajawal", "Almarai",
                         "Noto Sans", "Source Code Pro", "Fira Code", "JetBrains Mono", "Quicksand", "Ubuntu",
                         "Josefin Sans", "Comfortaa", "Lobster", "Kanit", "Mulish", "Barlow", "Plus Jakarta Sans"]

COMPOSITES: dict[str, list[tuple[str, str]]] = {
    "box_decoration": [("color", "color"), ("gradient", "gradient"), ("image", "decoration_image"),
                       ("borderRadius", "border_radius"), ("border", "border"), ("boxShadow", "box_shadows"),
                       ("shape", "enum:BoxShape")],
    "text_style": [("googleFont", "google_font"), ("fontFamily", "string"), ("fontSize", "double"),
                   ("fontWeight", "enum:FontWeight"), ("fontStyle", "enum:FontStyle"), ("color", "color"),
                   ("letterSpacing", "double"), ("wordSpacing", "double"), ("height", "double"),
                   ("decoration", "enum:TextDecoration"), ("decorationColor", "color"),
                   ("backgroundColor", "color"), ("shadows", "text_shadows")],
    "button_style": [("backgroundColor", "color"), ("foregroundColor", "color"), ("padding", "edge_insets"),
                     ("shape", "shape"), ("side", "side"), ("elevation", "double"), ("minimumSize", "size"),
                     ("textStyle", "text_style")],
    "input_decoration": [("hintText", "string"), ("labelText", "string"), ("helperText", "string"),
                         ("prefixIcon", "icon"), ("suffixIcon", "icon"), ("border", "choice:none|outline|underline"),
                         ("borderRadius", "border_radius"), ("borderColor", "color"),
                         ("focusedBorderColor", "color"), ("filled", "bool"), ("fillColor", "color"),
                         ("contentPadding", "edge_insets"), ("hintStyle", "text_style"),
                         ("labelStyle", "text_style"), ("isDense", "bool")],
    "shape": [("type", "choice:rounded|circle|stadium|beveled"), ("radius", "border_radius"), ("side", "side")],
    "side": [("color", "color"), ("width", "double")],
    "constraints": [("minWidth", "double"), ("maxWidth", "double"), ("minHeight", "double"),
                    ("maxHeight", "double")],
    "decoration_image": [("source", "choice:asset|network"), ("src", "image_src"), ("fit", "enum:BoxFit"),
                         ("alignment", "alignment"), ("opacity", "double")],
    "image": [("source", "choice:asset|network"), ("src", "image_src")],
}
COMPOSITE_TITLES = {"box_decoration": "BoxDecoration", "text_style": "TextStyle", "button_style": "ButtonStyle",
                    "input_decoration": "InputDecoration", "shape": "Shape", "side": "BorderSide",
                    "constraints": "BoxConstraints", "decoration_image": "DecorationImage", "image": "ImageProvider"}
GROUP_ORDER = ["Text", "Layout", "Style", "Behaviour", ""]


def google_fonts() -> list[str]:
    try:
        from . import fonts as FN
        names = [f.family for f in FN.builtin_catalog()]
        try:
            names = list(dict.fromkeys(list(FN.cached_families()) + names))
        except Exception:  # noqa: BLE001
            pass
        if names:
            return names
    except Exception:  # noqa: BLE001
        pass
    return list(GOOGLE_FONTS_FALLBACK)


def qcolor_of(v, scheme: dict | None = None) -> QColor | None:
    try:
        from .qtpreview import color
        from .qtpreview import color_scheme
        sch = scheme or color_scheme(None, False)

        class _C:
            pass
        c = _C()
        c.scheme = sch
        return color(v, c)
    except Exception:  # noqa: BLE001
        return None


def hex_of(c: QColor) -> str:
    return "#%02X%02X%02X%02X" % (c.alpha(), c.red(), c.green(), c.blue())


def swatch(c: QColor | None, size: int = 16) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    for y in range(0, size, 4):            # checkerboard behind transparent colours
        for x in range(0, size, 4):
            p.fillRect(x, y, 4, 4, QColor("#FFFFFF") if (x + y) // 4 % 2 == 0 else QColor("#CCCCCC"))
    if c is not None:
        p.fillRect(0, 0, size, size, c)
    else:
        p.setPen(QPen(QColor("#D32F2F"), 1.5))
        p.drawLine(1, size - 1, size - 1, 1)
    p.setPen(QColor("#80000000"))
    p.drawRect(0, 0, size - 1, size - 1)
    p.end()
    return QIcon(pm)


def _num_text(v) -> str:
    if v is None:
        return ""
    if v == "infinity":
        return "infinity"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _parse_num(text: str, as_int: bool = False):
    t = text.strip()
    if not t:
        return None
    if t.lower() in ("inf", "infinity", "double.infinity"):
        return "infinity"
    try:
        f = float(t)
    except ValueError:
        return None
    if as_int or f.is_integer():
        return int(round(f))
    return f


# =============================================================================== editors
class EdCtx:
    """What editors need from the designer."""

    def __init__(self, designer=None):
        self.designer = designer

    def folder(self):
        d = self.designer
        return d.project_folder() if d is not None and hasattr(d, "project_folder") else None

    def scheme(self):
        d = self.designer
        return d.scheme() if d is not None and hasattr(d, "scheme") else None


class Ed(QWidget):
    """Base value editor: ``set_value(v)`` (no signal) and ``committed(value)`` (None = unset)."""
    committed = pyqtSignal(object)

    def __init__(self, ctx: EdCtx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._v = None

    def set_value(self, v) -> None:
        self._v = v

    def value(self):
        return self._v

    def commit(self, v) -> None:
        if v == self._v:
            return
        self._v = v
        self.committed.emit(v)


def _hbox(w: QWidget, margins=0, spacing=3) -> QHBoxLayout:
    lay = QHBoxLayout(w)
    lay.setContentsMargins(margins, margins, margins, margins)
    lay.setSpacing(spacing)
    return lay


class StringEd(Ed):
    def __init__(self, ctx, parent=None, placeholder="", empty_is_none=True):
        super().__init__(ctx, parent)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.empty_is_none = empty_is_none
        _hbox(self).addWidget(self.edit)
        self.edit.editingFinished.connect(self._done)

    def set_value(self, v):
        super().set_value(v)
        self.edit.setText("" if v is None else str(v))

    def _done(self):
        t = self.edit.text()
        self.commit(None if (t == "" and self.empty_is_none) else t)


class TextEd(Ed):
    """Multi-line text (Text.data): Ctrl+Enter or leaving the field commits."""

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.edit = QPlainTextEdit()
        self.edit.setFixedHeight(46)
        self.edit.setTabChangesFocus(True)
        _hbox(self).addWidget(self.edit)
        self.edit.installEventFilter(self)

    def eventFilter(self, obj, ev):
        from PyQt6.QtCore import QEvent
        if ev.type() == QEvent.Type.FocusOut:
            self.commit(self.edit.toPlainText())
        elif ev.type() == QEvent.Type.KeyPress and ev.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and \
                ev.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.commit(self.edit.toPlainText())
            return True
        return False

    def set_value(self, v):
        super().set_value(v)
        if self.edit.toPlainText() != ("" if v is None else str(v)):
            self.edit.setPlainText("" if v is None else str(v))


class NumberEd(Ed):
    def __init__(self, ctx, parent=None, as_int=False, placeholder=""):
        super().__init__(ctx, parent)
        self.as_int = as_int
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setToolTip("A number; empty = default; 'infinity' = double.infinity")
        _hbox(self).addWidget(self.edit)
        self.edit.editingFinished.connect(lambda: self.commit(_parse_num(self.edit.text(), self.as_int)))
        self.edit.installEventFilter(self)

    def eventFilter(self, obj, ev):          # arrow keys step the value like a spin box
        from PyQt6.QtCore import QEvent
        if ev.type() == QEvent.Type.KeyPress and ev.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            v = _parse_num(self.edit.text(), self.as_int)
            v = 0 if not isinstance(v, (int, float)) else v
            step = 10 if ev.modifiers() & Qt.KeyboardModifier.ShiftModifier else (
                0.1 if ev.modifiers() & Qt.KeyboardModifier.AltModifier and not self.as_int else 1)
            v = v + (step if ev.key() == Qt.Key.Key_Up else -step)
            v = round(v, 3)
            if isinstance(v, float) and v.is_integer():
                v = int(v)
            self.edit.setText(_num_text(v))
            self.commit(v)
            return True
        return False

    def set_value(self, v):
        super().set_value(v)
        self.edit.setText(_num_text(v) if not M.is_code(v) else "")


class BoolEd(Ed):
    def __init__(self, ctx, parent=None, default=None):
        super().__init__(ctx, parent)
        self.combo = QComboBox()
        self.combo.addItem(f"(default{': ' + str(default).lower() if default is not None else ''})", None)
        self.combo.addItem("true", True)
        self.combo.addItem("false", False)
        _hbox(self).addWidget(self.combo)
        self.combo.activated.connect(lambda i: self.commit(self.combo.itemData(i)))

    def set_value(self, v):
        super().set_value(v)
        i = self.combo.findData(v) if isinstance(v, bool) else 0
        self.combo.setCurrentIndex(max(0, i))


class ChoiceEd(Ed):
    def __init__(self, ctx, values: list[str], parent=None, labels=None, default=None):
        super().__init__(ctx, parent)
        self.combo = QComboBox()
        self.combo.addItem("(default" + (f": {default.rsplit('.', 1)[-1]}" if isinstance(default, str) else "") + ")",
                           None)
        for i, v in enumerate(values):
            self.combo.addItem(labels[i] if labels else v.rsplit(".", 1)[-1], v)
            self.combo.setItemData(i + 1, v, Qt.ItemDataRole.ToolTipRole)
        _hbox(self).addWidget(self.combo)
        self.combo.activated.connect(lambda i: self.commit(self.combo.itemData(i)))

    def set_value(self, v):
        super().set_value(v)
        i = self.combo.findData(v) if v is not None else 0
        if i < 0 and isinstance(v, str):
            self.combo.addItem(v.rsplit(".", 1)[-1], v)
            i = self.combo.count() - 1
        self.combo.setCurrentIndex(max(0, i))


def _axis_glyph(enum: str, value: str, vertical: bool, size: int = 22) -> QIcon:
    """Small picture of a Main / Cross axis alignment value (bars in a box)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#9E9E9E"), 1))
    p.drawRect(1, 1, size - 3, size - 3)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#3F51B5"))
    n, bw, bl = 3, 4.0, 9.0
    inner = size - 6.0
    if enum == "MainAxisAlignment":
        total = n * bw
        gap = 1.5
        free = inner - total - gap * (n - 1)
        pos = {"start": [0], "end": [free], "center": [free / 2]}.get(value)
        if pos is not None:
            starts = [pos[0] + i * (bw + gap) for i in range(n)]
        elif value == "spaceBetween":
            starts = [i * (inner - bw) / (n - 1) for i in range(n)]
        elif value == "spaceAround":
            s = (inner - total) / n
            starts = [s / 2 + i * (bw + s) for i in range(n)]
        else:
            s = (inner - total) / (n + 1)
            starts = [s + i * (bw + s) for i in range(n)]
        for st in starts:
            r = QRectF(3 + st, 3 + (inner - bl) / 2, bw, bl) if not vertical else \
                QRectF(3 + (inner - bl) / 2, 3 + st, bl, bw)
            p.drawRect(r)
    else:
        lens = [9.0, 13.0, 6.0]
        for i, ln in enumerate(lens):
            ln = inner if value == "stretch" else ln
            off = {"start": 0, "baseline": 0, "end": inner - ln, "center": (inner - ln) / 2}.get(value, 0)
            main = 3 + 1.5 + i * (bw + 2.5)
            r = QRectF(main, 3 + off, bw, ln) if not vertical else QRectF(3 + off, main, ln, bw)
            p.drawRect(r)
    p.end()
    return QIcon(pm)


class AxisAlignEd(Ed):
    """MainAxisAlignment / CrossAxisAlignment as pictured toggle buttons (oriented like the Row / Column)."""

    def __init__(self, ctx, enum: str, vertical: bool, parent=None):
        super().__init__(ctx, parent)
        lay = _hbox(self, spacing=1)
        self.group = QButtonGroup(self)
        self.group.setExclusive(False)
        self.buttons = {}
        for v in M.ENUMS[enum]:
            b = QToolButton()
            b.setCheckable(True)
            b.setAutoRaise(True)
            b.setIcon(_axis_glyph(enum, v, vertical))
            b.setIconSize(QSize(22, 22))
            full = f"{enum}.{v}"
            b.setToolTip(full)
            b.clicked.connect(lambda checked, f=full: self.commit(f if checked else None))
            lay.addWidget(b)
            self.buttons[full] = b
        lay.addStretch(1)

    def set_value(self, v):
        super().set_value(v)
        for full, b in self.buttons.items():
            b.setChecked(full == v)

    def commit(self, v):
        for full, b in self.buttons.items():
            b.setChecked(full == v)
        super().commit(v)


class ColorEd(Ed):
    """Swatch + text (#AARRGGBB, Colors.*, scheme.*); the menu has a picker with alpha, theme and Flutter colours."""

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        lay = _hbox(self)
        self.btn = QToolButton()
        self.btn.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.btn.setIconSize(QSize(16, 16))
        self.btn.clicked.connect(self._pick)
        self.btn.setToolTip("Pick a colour (with transparency); the arrow lists theme and Flutter colours")
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("#AARRGGBB / Colors.white / scheme.primary")
        self.edit.editingFinished.connect(self._typed)
        lay.addWidget(self.btn)
        lay.addWidget(self.edit, 1)
        m = QMenu(self.btn)
        m.aboutToShow.connect(lambda: self._fill_menu(m))
        self.btn.setMenu(m)

    def _fill_menu(self, m: QMenu):
        m.clear()
        m.addAction("Pick colour...", self._pick)
        m.addAction("Transparent", lambda: self._set("Colors.transparent"))
        m.addAction("Clear (default)", lambda: self._set(None))
        th = m.addMenu("Theme colour")
        sch = self.ctx.scheme() or {}
        for k in SCHEME_KEYS:
            th.addAction(swatch(sch.get(k)), k, lambda k=k: self._set(f"scheme.{k}"))
        fl = m.addMenu("Flutter colours")
        for base in ("white", "black", "black87", "black54", "black26", "white70", "white54"):
            fl.addAction(swatch(qcolor_of(f"Colors.{base}")), base, lambda b=base: self._set(f"Colors.{b}"))
        fl.addSeparator()
        for sw in FLUTTER_SWATCHES:
            sub = fl.addMenu(swatch(qcolor_of(f"Colors.{sw}")), sw)
            sub.addAction(swatch(qcolor_of(f"Colors.{sw}")), sw, lambda s=sw: self._set(f"Colors.{s}"))
            for shade in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900):
                name = f"Colors.{sw}.shade{shade}"
                sub.addAction(swatch(qcolor_of(name)), f"shade{shade}", lambda n=name: self._set(n))

    def _set(self, v):
        self.set_value(v)
        self._v = object()           # force the commit
        self.commit(v)

    def _pick(self):
        cur = qcolor_of(self._v, self.ctx.scheme()) or QColor("#FF2196F3")
        c = QColorDialog.getColor(cur, self, "Colour", QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self._set(hex_of(c))

    def _typed(self):
        t = self.edit.text().strip()
        if not t:
            self.commit(None)
            return
        v = M.normalize_color(t)
        if qcolor_of(v, self.ctx.scheme()) is None and not t.startswith(("Colors.", "scheme.", "CupertinoColors.")):
            v = {"$code": t}
        self.set_value(v)
        self._v = object()
        self.commit(v)

    def set_value(self, v):
        self._v = v
        self.btn.setIcon(swatch(qcolor_of(v, self.ctx.scheme()) if v is not None else None))
        self.edit.setText("" if v is None else (v["$code"] if M.is_code(v) else str(v)))


class _Fields(Ed):
    """A few numeric fields in a row (helpers for EdgeInsets / radius / offset)."""

    def _spin(self, tip: str, mn=-9999.0) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(mn, 99999)
        s.setDecimals(1)
        s.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        s.setToolTip(tip)
        s.setFixedWidth(46)
        s.setKeyboardTracking(False)
        return s


def _clean(v: float):
    return int(v) if float(v).is_integer() else round(float(v), 2)


class EdgeInsetsEd(_Fields):
    MODES = ["none", "all", "symmetric", "only"]

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        lay = _hbox(self)
        self.mode = QComboBox()
        for m in self.MODES:
            self.mode.addItem({"none": "(none)", "all": "all", "symmetric": "symmetric", "only": "LTRB"}[m], m)
        self.mode.setFixedWidth(84)
        lay.addWidget(self.mode)
        self.sp = {k: self._spin(t, 0) for k, t in (("all", "all sides"), ("h", "horizontal"), ("v", "vertical"),
                                                     ("l", "left"), ("t", "top"), ("r", "right"), ("b", "bottom"))}
        for s in self.sp.values():
            lay.addWidget(s)
            s.valueChanged.connect(self._changed)
        lay.addStretch(1)
        self.mode.activated.connect(self._mode)
        self._show("none")

    def _show(self, m):
        vis = {"none": (), "all": ("all",), "symmetric": ("h", "v"), "only": ("l", "t", "r", "b")}[m]
        for k, s in self.sp.items():
            s.setVisible(k in vis)

    def _mode(self, _i):
        m = self.mode.currentData()
        self._show(m)
        self._changed()

    def _read(self):
        m = self.mode.currentData()
        if m == "none":
            return None
        if m == "all":
            return {"all": _clean(self.sp["all"].value())}
        if m == "symmetric":
            return {k: _clean(self.sp[k].value()) for k in ("h", "v") if self.sp[k].value()}
        return {k: _clean(self.sp[k].value()) for k in ("l", "t", "r", "b") if self.sp[k].value()}

    def _changed(self, *_a):
        if not getattr(self, "_loading", False):
            self.commit(self._read())

    def set_value(self, v):
        super().set_value(v)
        self._loading = True
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            v = {"all": v}
        if not isinstance(v, dict) or M.is_code(v):
            m = "none"
        elif "all" in v:
            m = "all"
        elif set(v) <= {"h", "v"} and v:
            m = "symmetric"
        else:
            m = "only"
        self.mode.setCurrentIndex(self.MODES.index(m))
        for k, s in self.sp.items():
            s.setValue(float(v.get(k, 0) or 0) if isinstance(v, dict) and not M.is_code(v) else 0.0)
        self._show(m)
        self._loading = False


class RadiusEd(_Fields):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        lay = _hbox(self)
        self.mode = QComboBox()
        for k, t in (("none", "(none)"), ("all", "all"), ("corners", "corners")):
            self.mode.addItem(t, k)
        self.mode.setFixedWidth(84)
        lay.addWidget(self.mode)
        self.sp = {k: self._spin(t, 0) for k, t in (("all", "radius"), ("tl", "top left"), ("tr", "top right"),
                                                     ("bl", "bottom left"), ("br", "bottom right"))}
        for s in self.sp.values():
            lay.addWidget(s)
            s.valueChanged.connect(self._changed)
        lay.addStretch(1)
        self.mode.activated.connect(lambda _i: (self._show(), self._changed()))
        self._show()

    def _show(self):
        m = self.mode.currentData()
        for k, s in self.sp.items():
            s.setVisible((m == "all" and k == "all") or (m == "corners" and k != "all"))

    def _changed(self, *_a):
        if getattr(self, "_loading", False):
            return
        m = self.mode.currentData()
        if m == "none":
            self.commit(None)
        elif m == "all":
            self.commit(_clean(self.sp["all"].value()))
        else:
            self.commit({k: _clean(self.sp[k].value()) for k in ("tl", "tr", "bl", "br") if self.sp[k].value()})

    def set_value(self, v):
        super().set_value(v)
        self._loading = True
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            self.mode.setCurrentIndex(1)
            self.sp["all"].setValue(float(v))
        elif isinstance(v, dict) and not M.is_code(v):
            self.mode.setCurrentIndex(2)
            for k in ("tl", "tr", "bl", "br"):
                self.sp[k].setValue(float(v.get(k, 0) or 0))
        else:
            self.mode.setCurrentIndex(0)
        self._show()
        self._loading = False


class PairEd(_Fields):
    """[x, y] (Offset) / [w, h] (Size)."""

    def __init__(self, ctx, parent=None, labels=("x", "y")):
        super().__init__(ctx, parent)
        lay = _hbox(self)
        self.on = QCheckBox()
        self.on.setToolTip("set")
        lay.addWidget(self.on)
        self.a, self.b = self._spin(labels[0]), self._spin(labels[1])
        for lab, s in zip(labels, (self.a, self.b)):
            lay.addWidget(QLabel(lab))
            lay.addWidget(s)
            s.valueChanged.connect(self._changed)
        lay.addStretch(1)
        self.on.toggled.connect(self._changed)

    def _changed(self, *_a):
        if not getattr(self, "_loading", False):
            self.commit([_clean(self.a.value()), _clean(self.b.value())] if self.on.isChecked() else None)

    def set_value(self, v):
        super().set_value(v)
        self._loading = True
        ok = isinstance(v, list) and len(v) == 2
        self.on.setChecked(ok)
        self.a.setValue(float(v[0]) if ok and isinstance(v[0], (int, float)) else 0.0)
        self.b.setValue(float(v[1]) if ok and isinstance(v[1], (int, float)) else 0.0)
        self._loading = False


class AlignmentEd(Ed):
    """3 x 3 grid of the named alignments + a custom Alignment(x, y)."""
    NAMES = [["topLeft", "topCenter", "topRight"], ["centerLeft", "center", "centerRight"],
             ["bottomLeft", "bottomCenter", "bottomRight"]]

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        lay = _hbox(self, spacing=6)
        grid_w = QFrame()
        grid_w.setFrameShape(QFrame.Shape.StyledPanel)
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(2, 2, 2, 2)
        grid.setSpacing(1)
        self.buttons = {}
        for r, row in enumerate(self.NAMES):
            for c, n in enumerate(row):
                b = QToolButton()
                b.setCheckable(True)
                b.setFixedSize(14, 14)
                b.setToolTip(f"Alignment.{n}")
                b.clicked.connect(lambda checked, n=n: self._click(n, checked))
                grid.addWidget(b, r, c)
                self.buttons[f"Alignment.{n}"] = b
        lay.addWidget(grid_w)
        self.custom = QLineEdit()
        self.custom.setPlaceholderText("x, y  (-1..1)")
        self.custom.setFixedWidth(80)
        self.custom.editingFinished.connect(self._typed)
        lay.addWidget(self.custom)
        lay.addStretch(1)

    def _click(self, n, checked):
        v = f"Alignment.{n}" if checked else None
        self.set_value(v)
        self._v = object()
        self.commit(v)

    def _typed(self):
        t = self.custom.text().strip()
        if not t:
            return
        try:
            x, y = (float(s) for s in t.replace(";", ",").split(","))
        except ValueError:
            return
        v = {"x": _clean(x), "y": _clean(y)}
        named = {(-1, -1): "topLeft", (0, -1): "topCenter", (1, -1): "topRight", (-1, 0): "centerLeft",
                 (0, 0): "center", (1, 0): "centerRight", (-1, 1): "bottomLeft", (0, 1): "bottomCenter",
                 (1, 1): "bottomRight"}.get((x, y))
        if named:
            v = f"Alignment.{named}"
        self.set_value(v)
        self._v = object()
        self.commit(v)

    def set_value(self, v):
        super().set_value(v)
        key = v if isinstance(v, str) else None
        if isinstance(key, str) and key.startswith("AlignmentDirectional."):
            key = "Alignment." + {"topStart": "topLeft", "topEnd": "topRight", "centerStart": "centerLeft",
                                  "centerEnd": "centerRight", "bottomStart": "bottomLeft",
                                  "bottomEnd": "bottomRight"}.get(key.split(".", 1)[1], key.split(".", 1)[1])
        for k, b in self.buttons.items():
            b.setChecked(k == key)
        self.custom.setText(f"{v.get('x', 0)}, {v.get('y', 0)}" if isinstance(v, dict) and not M.is_code(v) else "")


# ---------------------------------------------------------------------------- icon picker
class _IconModel(QAbstractListModel):
    def __init__(self, names: list[str]):
        super().__init__()
        self.names = names
        self._cache: dict[str, QIcon] = {}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.names)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        n = self.names[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return n
        if role == Qt.ItemDataRole.DecorationRole:
            ic = self._cache.get(n)
            if ic is None:
                ic = self._cache[n] = iconfont.icon("Icons." + n, 28, "#FF1D1B20")
            return ic
        if role == Qt.ItemDataRole.ToolTipRole:
            return "Icons." + n
        return None


class IconPickerDialog(QDialog):
    """Every Material icon of the Flutter SDK, searchable; double-click picks."""

    def __init__(self, parent=None, current: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Choose an icon")
        self.resize(720, 560)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search icons (e.g. email, lock, arrow)")
        self.search.setClearButtonEnabled(True)
        self.styles = QCheckBox("Outlined / rounded / sharp variants")
        top.addWidget(self.search, 1)
        top.addWidget(self.styles)
        lay.addLayout(top)
        self.model = _IconModel(iconfont.icon_names(styles=True))
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.view = QListView()
        self.view.setViewMode(QListView.ViewMode.IconMode)
        self.view.setIconSize(QSize(28, 28))
        self.view.setGridSize(QSize(104, 64))
        self.view.setUniformItemSizes(True)
        self.view.setResizeMode(QListView.ResizeMode.Adjust)
        self.view.setWordWrap(True)
        self.view.setLayoutMode(QListView.LayoutMode.Batched)
        self.view.setModel(self.proxy)
        self.view.setProperty("i18n_skip_items", True)
        self.view.doubleClicked.connect(lambda _i: self.accept())
        lay.addWidget(self.view, 1)
        self.count = QLabel()
        lay.addWidget(self.count)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.search.textChanged.connect(self._filter)
        self.styles.toggled.connect(lambda _c: self._filter(self.search.text()))
        self._filter("")
        cur = iconfont.bare(current)
        if cur:
            self.search.setText(cur)

    def _filter(self, text: str):
        t = text.strip().replace(" ", "_")
        pat = t if t else ""
        if not self.styles.isChecked():
            rx = (f".*{pat}.*" if pat else ".*")
            self.proxy.setFilterRegularExpression(f"^(?!.*_(outlined|rounded|sharp)$){rx}$" if not
                                                  pat.endswith(("_outlined", "_rounded", "_sharp")) else rx)
        else:
            self.proxy.setFilterFixedString(pat)
        self.count.setText(f"{self.proxy.rowCount()} icons")

    def selected(self) -> str | None:
        idx = self.view.currentIndex()
        if not idx.isValid():
            if self.proxy.rowCount() == 1:
                idx = self.proxy.index(0, 0)
            else:
                return None
        return "Icons." + self.proxy.data(idx)


class IconEd(Ed):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        lay = _hbox(self)
        self.btn = QPushButton()
        self.btn.setIconSize(QSize(18, 18))
        self.btn.setStyleSheet("text-align:left; padding:2px 6px")
        self.btn.clicked.connect(self._pick)
        self.clear = QToolButton()
        self.clear.setText("x")
        self.clear.setToolTip("Clear")
        self.clear.setAutoRaise(True)
        self.clear.clicked.connect(lambda: self.commit(None) or self.set_value(None))
        lay.addWidget(self.btn, 1)
        lay.addWidget(self.clear)

    def _pick(self):
        dlg = IconPickerDialog(self, self._v if isinstance(self._v, str) else "")
        if dlg.exec():
            v = dlg.selected()
            if v:
                self.set_value(v)
                self._v = object()
                self.commit(v)

    def set_value(self, v):
        super().set_value(v)
        if isinstance(v, str):
            self.btn.setIcon(iconfont.icon(v, 18))
            self.btn.setText(v)
        else:
            self.btn.setIcon(QIcon())
            self.btn.setText("(none) - choose..." if v is None else str(v))


# ------------------------------------------------------------------------- images / fonts
class ImageSrcEd(Ed):
    """Asset path or URL + a menu: project assets, import a file, a sample photo URL."""

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        lay = _hbox(self)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("assets/images/x.png or https://...")
        self.edit.editingFinished.connect(lambda: self.commit(self.edit.text().strip() or None))
        self.btn = QToolButton()
        self.btn.setText("...")
        self.btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        m = QMenu(self.btn)
        m.aboutToShow.connect(lambda: self._fill(m))
        self.btn.setMenu(m)
        lay.addWidget(self.edit, 1)
        lay.addWidget(self.btn)

    def _fill(self, m: QMenu):
        m.clear()
        folder = self.ctx.folder()
        m.addAction("Import image file...", self._import).setEnabled(folder is not None)
        m.addAction("Sample photo (picsum.photos)", lambda: self._set("https://picsum.photos/seed/rad/800/600"))
        if folder is not None:
            try:
                from . import assets as AS
                lst = [a for a in AS.list_assets(folder) if a.kind in ("image",)]
            except Exception:  # noqa: BLE001
                lst = []
            if lst:
                m.addSeparator()
                for a in lst[:60]:
                    m.addAction(a.rel, lambda r=a.rel: self._set(r))

    def _set(self, v):
        self.set_value(v)
        self._v = object()
        self.commit(v)

    def _import(self):
        folder = self.ctx.folder()
        if folder is None:
            return
        path, _f = QFileDialog.getOpenFileName(self, "Import image", "",
                                               "Images (*.png *.jpg *.jpeg *.gif *.webp *.bmp);;All files (*)")
        if not path:
            return
        try:
            from . import assets as AS
            info = AS.import_asset(folder, path, kind="image")
            self._set(info.rel)
        except Exception as e:  # noqa: BLE001
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Import image", str(e))

    def set_value(self, v):
        super().set_value(v)
        self.edit.setText("" if v is None else str(v))


class FontEd(Ed):
    """Google font family (editable list)."""

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.addItem("")
        self.combo.addItems(google_fonts())
        self.combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo.lineEdit().setPlaceholderText("Google font (e.g. Poppins)")
        self.combo.setMaxVisibleItems(20)
        self.combo.setProperty("i18n_skip_items", True)
        _hbox(self).addWidget(self.combo)
        self.combo.activated.connect(lambda _i: self.commit(self.combo.currentText().strip() or None))
        self.combo.lineEdit().editingFinished.connect(lambda: self.commit(self.combo.currentText().strip() or None))

    def set_value(self, v):
        super().set_value(v)
        self.combo.setCurrentText("" if v is None else str(v))


# --------------------------------------------------------------------------- lists
class _ListEd(Ed):
    """Rows of sub editors (+ add / remove)."""

    def __init__(self, ctx, parent=None, add_text="Add"):
        super().__init__(ctx, parent)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(2)
        self.rows_w = QWidget()
        self.rows = QVBoxLayout(self.rows_w)
        self.rows.setContentsMargins(0, 0, 0, 0)
        self.rows.setSpacing(2)
        self.lay.addWidget(self.rows_w)
        bar = QHBoxLayout()
        self.add_btn = QPushButton(add_text)
        self.add_btn.clicked.connect(self._add)
        bar.addWidget(self.add_btn)
        bar.addStretch(1)
        self.lay.addLayout(bar)
        self.items: list = []

    def new_item(self):
        return {}

    def make_row(self, i: int, item) -> QWidget:
        raise NotImplementedError

    def _rebuild(self):
        while self.rows.count():
            w = self.rows.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        for i, it in enumerate(self.items):
            self.rows.addWidget(self.make_row(i, it))

    def _add(self):
        self.items.append(self.new_item())
        self._rebuild()
        self._emit()

    def _remove(self, i):
        del self.items[i]
        self._rebuild()
        self._emit()

    def _update(self, i, key, v):
        if 0 <= i < len(self.items) and isinstance(self.items[i], dict):
            if v is None:
                self.items[i].pop(key, None)
            else:
                self.items[i][key] = v
            self._emit()

    def _emit(self):
        out = [dict(x) if isinstance(x, dict) else x for x in self.items]
        self.commit(out or None)

    def _del_btn(self, i) -> QToolButton:
        b = QToolButton()
        b.setText("x")
        b.setAutoRaise(True)
        b.setToolTip("Remove")
        b.clicked.connect(lambda: self._remove(i))
        return b

    def set_value(self, v):
        super().set_value(v)
        self.items = [dict(x) if isinstance(x, dict) else x for x in v] if isinstance(v, list) else []
        self._rebuild()


class ShadowsEd(_ListEd):
    def __init__(self, ctx, parent=None, spread=True):
        self.spread = spread
        super().__init__(ctx, parent, "Add shadow")

    def new_item(self):
        return {"color": "#33000000", "blur": 12, "offset": [0, 6]} | ({"spread": 0} if self.spread else {})

    def make_row(self, i, item):
        w = QFrame()
        w.setFrameShape(QFrame.Shape.StyledPanel)
        g = QGridLayout(w)
        g.setContentsMargins(3, 3, 3, 3)
        g.setSpacing(2)
        if M.is_code(item):
            g.addWidget(QLabel(item["$code"]), 0, 0)
            g.addWidget(self._del_btn(i), 0, 1)
            return w
        ce = ColorEd(self.ctx)
        ce.set_value(item.get("color"))
        ce.committed.connect(lambda v, i=i: self._update(i, "color", v))
        g.addWidget(ce, 0, 0, 1, 3)
        g.addWidget(self._del_btn(i), 0, 3)
        col = 0
        for key, tip in (("blur", "blur"), ("spread", "spread")):
            if key == "spread" and not self.spread:
                continue
            ne = NumberEd(self.ctx, placeholder=tip)
            ne.set_value(item.get(key))
            ne.setToolTip(tip)
            ne.committed.connect(lambda v, i=i, k=key: self._update(i, k, v))
            g.addWidget(ne, 1, col)
            col += 1
        oe = PairEd(self.ctx, labels=("x", "y"))
        oe.set_value(item.get("offset") if isinstance(item.get("offset"), list) else None)
        oe.committed.connect(lambda v, i=i: self._update(i, "offset", v))
        g.addWidget(oe, 2, 0, 1, 4)
        return w


class GradientBar(QWidget):
    def __init__(self, ed):
        super().__init__()
        self.ed = ed
        self.setFixedHeight(18)

    def paintEvent(self, _e):
        p = QPainter(self)
        r = QRectF(self.rect()).adjusted(0, 0, -1, -1)
        g = self.ed.value()
        grad = QLinearGradient(r.topLeft(), r.topRight())
        cols = (g or {}).get("colors") or []
        stops = (g or {}).get("stops") or [i / max(1, len(cols) - 1) for i in range(len(cols))]
        for s, c in zip(stops, cols):
            q = qcolor_of(c, self.ed.ctx.scheme())
            if q is not None and isinstance(s, (int, float)):
                grad.setColorAt(max(0.0, min(1.0, float(s))), q)
        p.fillRect(r, grad if cols else QColor("#EEEEEE"))
        p.setPen(QColor("#999999"))
        p.drawRect(r)


class GradientEd(Ed):
    """Type, angle (linear) / centre + radius (radial), colour stops with positions."""

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        top = QHBoxLayout()
        self.type = QComboBox()
        for t in ("(none)", "linear", "radial", "sweep"):
            self.type.addItem(t, None if t == "(none)" else t)
        self.angle = QSpinBox()
        self.angle.setRange(0, 359)
        self.angle.setSuffix(" deg")
        self.angle.setWrapping(True)
        self.angle.setToolTip("Direction: 0 = left to right, 90 = top to bottom")
        self.angle.setKeyboardTracking(False)
        self.radius = QDoubleSpinBox()
        self.radius.setRange(0.05, 5)
        self.radius.setSingleStep(0.05)
        self.radius.setPrefix("r ")
        self.radius.setKeyboardTracking(False)
        top.addWidget(self.type)
        top.addWidget(self.angle)
        top.addWidget(self.radius)
        top.addStretch(1)
        lay.addLayout(top)
        self.bar = GradientBar(self)
        lay.addWidget(self.bar)
        self.stops_w = QWidget()
        self.stops = QVBoxLayout(self.stops_w)
        self.stops.setContentsMargins(0, 0, 0, 0)
        self.stops.setSpacing(1)
        lay.addWidget(self.stops_w)
        self.add = QPushButton("Add colour")
        self.add.clicked.connect(self._add_stop)
        lay.addWidget(self.add, 0, Qt.AlignmentFlag.AlignLeft)
        self.type.activated.connect(lambda _i: self._changed(rebuild=True))
        self.angle.valueChanged.connect(lambda _v: self._changed())
        self.radius.valueChanged.connect(lambda _v: self._changed())
        self._g: dict | None = None

    @staticmethod
    def angle_of(g: dict) -> int:
        from .qtpreview import align
        bx, by = align(g.get("begin", "Alignment.centerLeft"), (-1.0, 0.0))
        ex, ey = align(g.get("end", "Alignment.centerRight"), (1.0, 0.0))
        return int(round(math.degrees(math.atan2(ey - by, ex - bx)))) % 360

    @staticmethod
    def ends_of(angle: int) -> tuple:
        a = math.radians(angle)
        x, y = math.cos(a), math.sin(a)
        k = 1 / max(abs(x), abs(y))           # onto the box edge
        x, y = round(x * k, 2), round(y * k, 2)
        names = {(-1, -1): "topLeft", (0, -1): "topCenter", (1, -1): "topRight", (-1, 0): "centerLeft",
                 (0, 0): "center", (1, 0): "centerRight", (-1, 1): "bottomLeft", (0, 1): "bottomCenter",
                 (1, 1): "bottomRight"}

        def al(px, py):
            n = names.get((px, py))
            return f"Alignment.{n}" if n else {"x": _clean(px), "y": _clean(py)}
        return al(-x, -y), al(x, y)

    def _add_stop(self):
        g = dict(self._g or {"type": "linear", "colors": [], "begin": "Alignment.centerLeft",
                             "end": "Alignment.centerRight"})
        cols = list(g.get("colors") or [])
        cols.append(cols[-1] if cols else "#FF8F94FB")
        if len(cols) == 1:
            cols.append("#FF4E54C8")
        g["colors"] = cols
        if g.get("stops"):
            g["stops"] = [round(i / (len(cols) - 1), 2) for i in range(len(cols))]
        self._g = g
        self._rebuild_stops()
        self._emit()

    def _rebuild_stops(self):
        while self.stops.count():
            w = self.stops.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        g = self._g or {}
        cols = g.get("colors") or []
        stops = g.get("stops") or []
        for i, c in enumerate(cols):
            row = QWidget()
            h = _hbox(row)
            ce = ColorEd(self.ctx)
            ce.set_value(c)
            ce.committed.connect(lambda v, i=i: self._set_color(i, v))
            sp = QDoubleSpinBox()
            sp.setRange(0, 1)
            sp.setSingleStep(0.05)
            sp.setDecimals(2)
            sp.setToolTip("stop (0..1) - leave all at automatic by removing stops")
            sp.setKeyboardTracking(False)
            sp.setValue(float(stops[i]) if i < len(stops) and isinstance(stops[i], (int, float))
                        else i / max(1, len(cols) - 1))
            sp.valueChanged.connect(lambda v, i=i: self._set_stop(i, v))
            rm = QToolButton()
            rm.setText("x")
            rm.setAutoRaise(True)
            rm.clicked.connect(lambda _c=False, i=i: self._remove(i))
            h.addWidget(ce, 1)
            h.addWidget(sp)
            h.addWidget(rm)
            self.stops.addWidget(row)
        self.bar.update()

    def _set_color(self, i, v):
        g = dict(self._g or {})
        cols = list(g.get("colors") or [])
        if i < len(cols) and v is not None:
            cols[i] = v
            g["colors"] = cols
            self._g = g
            self._emit()

    def _set_stop(self, i, v):
        g = dict(self._g or {})
        cols = g.get("colors") or []
        stops = list(g.get("stops") or [round(k / max(1, len(cols) - 1), 2) for k in range(len(cols))])
        if i < len(stops):
            stops[i] = round(v, 2)
            g["stops"] = stops
            self._g = g
            self._emit()

    def _remove(self, i):
        g = dict(self._g or {})
        cols = list(g.get("colors") or [])
        if i < len(cols):
            del cols[i]
            g["colors"] = cols
            if g.get("stops") and i < len(g["stops"]):
                st = list(g["stops"])
                del st[i]
                g["stops"] = st
            self._g = g if cols else None
            self._rebuild_stops()
            self._emit()

    def _changed(self, rebuild=False):
        if getattr(self, "_loading", False):
            return
        t = self.type.currentData()
        if t is None:
            self._g = None
        else:
            g = dict(self._g or {"colors": ["#FF8F94FB", "#FF4E54C8"]})
            g["type"] = t
            if t == "linear":
                g.pop("center", None)
                g.pop("radius", None)
                g["begin"], g["end"] = self.ends_of(self.angle.value())
            else:
                g.pop("begin", None)
                g.pop("end", None)
                g.setdefault("center", "Alignment.center")
                if t == "radial":
                    g["radius"] = _clean(self.radius.value())
            self._g = g
        self._show()
        if rebuild:
            self._rebuild_stops()
        self._emit()

    def _show(self):
        t = self.type.currentData()
        self.angle.setVisible(t == "linear")
        self.radius.setVisible(t == "radial")
        self.stops_w.setVisible(t is not None)
        self.add.setVisible(t is not None)
        self.bar.setVisible(t is not None)

    def _emit(self):
        self.bar.update()
        self.commit(dict(self._g) if self._g else None)

    def value(self):
        return self._g

    def set_value(self, v):
        super().set_value(v)
        self._loading = True
        self._g = dict(v) if isinstance(v, dict) and not M.is_code(v) else None
        g = self._g or {}
        i = self.type.findData(g.get("type", "linear")) if self._g else 0
        self.type.setCurrentIndex(max(0, i))
        self.angle.setValue(self.angle_of(g) if g else 0)
        self.radius.setValue(float(g.get("radius", 0.5)) if isinstance(g.get("radius"), (int, float)) else 0.5)
        self._show()
        self._rebuild_stops()
        self._loading = False


class BorderEd(Ed):
    """Border.all(color, width) or per side (top / right / bottom / left)."""

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self.mode = QComboBox()
        for k, t in (("none", "(none)"), ("all", "all sides"), ("sides", "per side")):
            self.mode.addItem(t, k)
        lay.addWidget(self.mode)
        self.parts: dict[str, CompositeEd] = {}
        for k in ("all", "top", "right", "bottom", "left"):
            ed = CompositeEd(ctx, "side", title=k if k != "all" else "", flat=True)
            ed.committed.connect(lambda v, k=k: self._part(k, v))
            self.parts[k] = ed
            lay.addWidget(ed)
        self.mode.activated.connect(lambda _i: self._mode())
        self._b: dict | None = None
        self._show()

    def _show(self):
        m = self.mode.currentData()
        for k, ed in self.parts.items():
            ed.setVisible((m == "all" and k == "all") or (m == "sides" and k != "all"))

    def _mode(self):
        m = self.mode.currentData()
        if m == "none":
            self._b = None
        elif m == "all":
            self._b = {"color": "#FFE0E0E0", "width": 1}
        else:
            self._b = {"bottom": {"color": "#FFE0E0E0", "width": 1}}
        self.set_value(self._b)
        self._v = object()
        self.commit(self._b)

    def _part(self, k, v):
        if k == "all":
            self._b = v
        else:
            b = {kk: vv for kk, vv in (self._b or {}).items() if kk in ("top", "right", "bottom", "left")}
            if v:
                b[k] = v
            else:
                b.pop(k, None)
            self._b = b or None
        self.commit(dict(self._b) if self._b else None)

    def set_value(self, v):
        super().set_value(v)
        self._b = dict(v) if isinstance(v, dict) and not M.is_code(v) else None
        b = self._b or {}
        sides = any(k in b for k in ("top", "right", "bottom", "left"))
        self.mode.setCurrentIndex(0 if not self._b else (2 if sides else 1))
        self.parts["all"].set_value(b if self._b and not sides else None)
        for k in ("top", "right", "bottom", "left"):
            self.parts[k].set_value(b.get(k) if sides else None)
        self._show()


class NavItemsEd(_ListEd):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent, "Add item")

    def new_item(self):
        return {"icon": "Icons.circle", "label": f"Item {len(self.items) + 1}"}

    def make_row(self, i, item):
        w = QWidget()
        h = _hbox(w)
        if M.is_code(item):
            h.addWidget(QLabel(item["$code"]), 1)
            h.addWidget(self._del_btn(i))
            return w
        ie = IconEd(self.ctx)
        ie.set_value(item.get("icon"))
        ie.committed.connect(lambda v, i=i: self._update(i, "icon", v))
        le = StringEd(self.ctx, placeholder="label")
        le.set_value(item.get("label"))
        le.committed.connect(lambda v, i=i: self._update(i, "label", v))
        h.addWidget(ie, 1)
        h.addWidget(le, 1)
        h.addWidget(self._del_btn(i))
        return w


class StringListEd(Ed):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("One; Two; Three")
        _hbox(self).addWidget(self.edit)
        self.edit.editingFinished.connect(
            lambda: self.commit([s.strip() for s in self.edit.text().split(";") if s.strip()] or None))

    def set_value(self, v):
        super().set_value(v)
        self.edit.setText("; ".join(str(x) for x in v) if isinstance(v, list) else "")


class CodeEd(Ed):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.edit = QPlainTextEdit()
        self.edit.setFixedHeight(60)
        f = self.edit.font()
        f.setFamily("Consolas")
        self.edit.setFont(f)
        self.edit.setTabChangesFocus(True)
        _hbox(self).addWidget(self.edit)
        self.edit.installEventFilter(self)

    def eventFilter(self, obj, ev):
        from PyQt6.QtCore import QEvent
        if ev.type() == QEvent.Type.FocusOut:
            self.commit(self.edit.toPlainText() or None)
        return False

    def set_value(self, v):
        super().set_value(v)
        if self.edit.toPlainText() != (v or ""):
            self.edit.setPlainText("" if v is None else str(v))


class CompositeEd(Ed):
    """A JSON object of sub-properties (BoxDecoration, TextStyle, InputDecoration ...), collapsible."""

    def __init__(self, ctx, kind: str, parent=None, title: str | None = None, flat=False):
        super().__init__(ctx, parent)
        self.kind = kind
        self.fields = COMPOSITES[kind]
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        self.head = QToolButton()
        self.head.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.head.setCheckable(True)
        self.head.setAutoRaise(True)
        self.head.setArrowType(Qt.ArrowType.RightArrow)
        self.head.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.head.toggled.connect(self._toggle)
        self.title = title if title is not None else COMPOSITE_TITLES.get(kind, kind)
        lay.addWidget(self.head)
        self.body = QFrame()
        self.body.setFrameShape(QFrame.Shape.StyledPanel if not flat else QFrame.Shape.NoFrame)
        self.form = QFormLayout(self.body)
        self.form.setContentsMargins(6 if not flat else 0, 3, 3, 3)
        self.form.setSpacing(2)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        lay.addWidget(self.body)
        self.eds: dict[str, Ed] = {}
        self._d: dict = {}
        self._built = False
        if flat:
            self.head.hide()
            self._build()
            self.body.show()
        else:
            self.body.hide()
        self._update_head()

    def _build(self):
        if self._built:
            return
        self._built = True
        for key, kind in self.fields:
            ed = make_editor(kind, self.ctx)
            ed.set_value(self._d.get(key))
            ed.committed.connect(lambda v, k=key: self._sub(k, v))
            lab = QLabel(key)
            lab.setProperty("i18n_skip", True)          # Flutter parameter names stay English
            lab.setToolTip(f"{key} ({kind})")
            self.form.addRow(lab, ed)
            self.eds[key] = ed

    def _toggle(self, on):
        if on:
            self._build()
        self.body.setVisible(on)
        self.head.setArrowType(Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow)

    def _update_head(self):
        keys = [k for k, _ in self.fields if self._d.get(k) not in (None, "", [], {})]
        extra = ", ".join(keys[:4]) + (" ..." if len(keys) > 4 else "")
        self.head.setText(f"{self.title}" + (f"  ({extra})" if keys else "  (empty)"))

    def _sub(self, key, v):
        d = dict(self._d)
        if v in (None, "", [], {}):
            d.pop(key, None)
        else:
            d[key] = v
        self._d = d
        self._update_head()
        self.commit(dict(d) if d else None)

    def set_value(self, v):
        super().set_value(v)
        self._d = dict(v) if isinstance(v, dict) and not M.is_code(v) else {}
        if self._built:
            for k, ed in self.eds.items():
                ed.set_value(self._d.get(k))
        self._update_head()

    def expand(self, on=True):
        self.head.setChecked(on)


def make_editor(kind: str, ctx: EdCtx, spec: M.PropSpec | None = None, vertical: bool = False,
                key: str = "") -> Ed:
    """The editor for a property kind (catalog PropSpec.kind or a composite field kind)."""
    default = spec.default if spec is not None else None
    if kind.startswith("enum:"):
        enum = kind[5:]
        return ChoiceEd(ctx, [f"{enum}.{v}" for v in M.ENUMS.get(enum, [])], default=default)
    if kind.startswith("choice:"):
        return ChoiceEd(ctx, kind[7:].split("|"))
    if kind == "enum" and spec is not None:
        if spec.enum in ("MainAxisAlignment", "CrossAxisAlignment"):
            return AxisAlignEd(ctx, spec.enum, vertical)
        return ChoiceEd(ctx, spec.values, default=default)
    if kind == "string":
        return TextEd(ctx) if key == "data" else StringEd(ctx, empty_is_none=not (spec and spec.required))
    if kind in ("int", "double"):
        return NumberEd(ctx, as_int=kind == "int",
                        placeholder=_num_text(default) if isinstance(default, (int, float)) else "")
    if kind == "bool":
        return BoolEd(ctx, default=default)
    if kind == "color":
        return ColorEd(ctx)
    if kind == "edge_insets":
        return EdgeInsetsEd(ctx)
    if kind == "border_radius":
        return RadiusEd(ctx)
    if kind == "alignment":
        return AlignmentEd(ctx)
    if kind == "icon":
        return IconEd(ctx)
    if kind == "offset":
        return PairEd(ctx, labels=("x", "y"))
    if kind == "size":
        return PairEd(ctx, labels=("w", "h"))
    if kind == "duration":
        return NumberEd(ctx, as_int=True, placeholder="ms")
    if kind == "string_list":
        return StringListEd(ctx)
    if kind == "gradient":
        return GradientEd(ctx)
    if kind == "box_shadows":
        return ShadowsEd(ctx)
    if kind == "text_shadows":
        return ShadowsEd(ctx, spread=False)
    if kind == "border":
        return BorderEd(ctx)
    if kind == "nav_items":
        return NavItemsEd(ctx)
    if kind == "image_src":
        return ImageSrcEd(ctx)
    if kind == "google_font":
        return FontEd(ctx)
    if kind == "physics":
        return ChoiceEd(ctx, M.ENUMS["Physics"])
    if kind in COMPOSITES:
        return CompositeEd(ctx, kind)
    return CodeEd(ctx)


# ============================================================================ property row
class PropRow(QWidget):
    """Editor + a raw-Dart toggle ({}) + reset."""
    committed = pyqtSignal(str, object)

    def __init__(self, key: str, spec: M.PropSpec, ctx: EdCtx, vertical: bool = False, parent=None):
        super().__init__(parent)
        self.key, self.spec, self.ctx = key, spec, ctx
        lay = _hbox(self, spacing=1)
        self.ed = make_editor(spec.kind, ctx, spec, vertical, key)
        self.ed.committed.connect(lambda v: self.committed.emit(self.key, v))
        self.code = QLineEdit()
        self.code.setPlaceholderText("Dart expression")
        f = self.code.font()
        f.setFamily("Consolas")
        self.code.setFont(f)
        self.code.editingFinished.connect(self._code_done)
        self.code.hide()
        self.dart = QToolButton()
        self.dart.setText("{}")
        self.dart.setCheckable(True)
        self.dart.setAutoRaise(True)
        self.dart.setToolTip("Raw Dart: write this property as a Dart expression")
        self.dart.toggled.connect(self._toggle_code)
        self.reset = QToolButton()
        self.reset.setText("x")
        self.reset.setAutoRaise(True)
        self.reset.setToolTip("Reset to the default")
        self.reset.clicked.connect(lambda: self.committed.emit(self.key, None))
        lay.addWidget(self.ed, 1)
        lay.addWidget(self.code, 1)
        lay.addWidget(self.dart, 0, Qt.AlignmentFlag.AlignTop)
        lay.addWidget(self.reset, 0, Qt.AlignmentFlag.AlignTop)

    def _toggle_code(self, on):
        if getattr(self, "_loading", False):
            return
        self.ed.setVisible(not on)
        self.code.setVisible(on)
        if on:
            self.code.setFocus()
        elif M.is_code(self.ed.value()):
            self.committed.emit(self.key, None)

    def _code_done(self):
        if self.code.isReadOnly():
            return
        t = self.code.text().strip()
        self.committed.emit(self.key, {"$code": t} if t else None)

    def set_value(self, v):
        self._loading = True
        animated = MO.is_when(v) or MO.is_timeline(v)
        self.code.setReadOnly(animated)
        self.dart.setEnabled(not animated)
        if animated:                       # $when / $timeline: shown as text, edited with the row menu
            from .motion_ui import describe_value
            self.dart.setChecked(False)
            self.ed.setVisible(False)
            self.code.setVisible(True)
            self.code.setText(describe_value(v))
            self.code.setToolTip("Animated value - right-click the property name to change or remove it")
            self.reset.setEnabled(True)
            self._loading = False
            return
        self.code.setToolTip("")
        is_code = M.is_code(v)
        self.dart.setChecked(is_code)
        self.ed.setVisible(not is_code)
        self.code.setVisible(is_code)
        self.code.setText(v["$code"] if is_code else "")
        self.ed.blockSignals(True)
        self.ed.set_value(None if is_code else v)
        self.ed.blockSignals(False)
        self.reset.setEnabled(v is not None)
        self._loading = False


class Section(QWidget):
    """Collapsible group of rows."""

    def __init__(self, title: str, parent=None, expanded=True):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(0)
        self.head = QToolButton()
        self.head.setText(title)
        self.head.setCheckable(True)
        self.head.setChecked(expanded)
        self.head.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.head.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.head.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.head.setStyleSheet("QToolButton{font-weight:bold; border:none; padding:3px; text-align:left;"
                                "background: palette(midlight);}")
        self.body = QWidget()
        self.form = QFormLayout(self.body)
        self.form.setContentsMargins(4, 3, 2, 3)
        self.form.setSpacing(3)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self.head)
        lay.addWidget(self.body)
        self.body.setVisible(expanded)
        self.head.toggled.connect(self._t)

    def _t(self, on):
        self.body.setVisible(on)
        self.head.setArrowType(Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow)


# ================================================================================ inspector
class Inspector(QScrollArea):
    """``inspect(node_id)`` (None = the screen); the designer calls ``refresh()`` after every change."""

    def __init__(self, designer, parent=None):
        super().__init__(parent)
        self.designer = designer
        self.ctx = EdCtx(designer)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumWidth(300)
        self.node_id: str | None = None
        self._sig = None
        self.rows: dict[str, PropRow] = {}
        self.events: dict[str, QLineEdit] = {}
        self._build_empty()

    # ------------------------------------------------------------------ building
    def _build_empty(self):
        w = QWidget()
        QVBoxLayout(w).addWidget(QLabel("Select a widget"))
        self.setWidget(w)

    def inspect(self, node_id: str | None, force=False):
        scr = self.designer.screen
        node = scr.find(node_id) if node_id else None
        sig = (node_id, node.get("type") if node else None, node.get("ctor") if node else None,
               self._parent_type(node_id))
        if sig == self._sig and not force:
            self.refresh()
            return
        self._sig = sig
        self.node_id = node_id if node else None
        pos = self.verticalScrollBar().value()
        root = QWidget()
        root.setProperty("i18n_skip_items", True)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(2)
        self.rows, self.events = {}, {}
        self.labels: dict = {}
        self.anim_eds: dict = {}
        self.anim_extra = None
        self.name_edit = None
        self.screen_eds: dict = {}
        if node is None or node is scr.tree:
            self._screen_section(lay)
        if node is not None:
            self._node_sections(lay, node)
        lay.addStretch(1)
        self.setWidget(root)
        QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(pos))
        self.refresh()

    def _parent_type(self, node_id):
        if not node_id:
            return None
        try:
            p, _w = self.designer.screen.parent_of(node_id)
        except KeyError:
            return None
        return p.get("type") if p else None

    def _header(self, lay, node):
        spec = M.widget_spec(node["type"], node.get("ctor"))
        base = M.CATALOG.get(node["type"])
        box = QFrame()
        box.setFrameShape(QFrame.Shape.StyledPanel)
        g = QGridLayout(box)
        g.setContentsMargins(4, 4, 4, 4)
        ic = QLabel()
        ic.setPixmap(type_icon(node["type"], 24).pixmap(24, 24))
        title = QLabel(f"<b>{node['type']}</b>  <span style='color:gray'>{node.get('id', '')}</span>")
        g.addWidget(ic, 0, 0)
        g.addWidget(title, 0, 1)
        if base is not None and base.ctors:
            ctor = QComboBox()
            if base.unnamed_ctor:
                ctor.addItem(f"{node['type']}()", "")
            for c in base.ctors:
                ctor.addItem(f"{node['type']}.{c}()", c)
            ctor.setCurrentIndex(max(0, ctor.findData(node.get("ctor") or "")))
            ctor.activated.connect(lambda i, cb=ctor: self.designer.set_ctor(self.node_id, cb.itemData(i) or None))
            ctor.setToolTip("Constructor")
            g.addWidget(ctor, 0, 2)
        g.addWidget(QLabel("Name"), 1, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("field name (txtEmail, btnLogin)" if not (base and base.needs_name)
                                          else "required: the State field")
        self.name_edit.setToolTip("VB-style name: a field of the screen's State class (controllers, values)")
        self.name_edit.editingFinished.connect(lambda: self.designer.rename(self.node_id,
                                                                            self.name_edit.text().strip() or None))
        g.addWidget(self.name_edit, 1, 1, 1, 2)
        if spec is not None and spec.help:
            h = QLabel(spec.help)
            h.setWordWrap(True)
            h.setStyleSheet("color: gray")
            g.addWidget(h, 2, 0, 1, 3)
        lay.addWidget(box)

    def _node_sections(self, lay, node):
        self._header(lay, node)
        spec = M.widget_spec(node["type"], node.get("ctor"))
        if spec is None:
            return
        vertical = node["type"] == "Column" or (node["type"] == "Flex" and
                                                (node.get("props") or {}).get("direction") == "Axis.vertical")
        groups: dict[str, list] = {}
        for k, ps in spec.props.items():
            groups.setdefault(ps.group or "", []).append((k, ps))
        order = sorted(groups, key=lambda g: GROUP_ORDER.index(g) if g in GROUP_ORDER else 9)
        for gname in order:
            sec = Section(gname or "Properties")
            for k, ps in groups[gname]:
                row = PropRow(k, ps, self.ctx, vertical)
                row.committed.connect(self._prop)
                lab = QLabel(k + (" *" if ps.required else ""))
                lab.setProperty("i18n_skip", True)
                lab.setToolTip(f"{k}: {ps.kind}{(' ' + ps.enum) if ps.enum else ''}"
                               + (f"\n{ps.help}" if ps.help else "") + "\nRight-click: sizes / animate")
                lab.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                lab.customContextMenuRequested.connect(lambda _pt, k=k, ps=ps, lab=lab: self._row_menu(k, ps, lab))
                lab.setProperty("rad_text", k + (" *" if ps.required else ""))
                sec.form.addRow(lab, row)
                self.rows[k] = row
                self.labels[k] = lab
            lay.addWidget(sec)
        extra = [k for k in (node.get("props") or {}) if k not in spec.props]
        if extra:
            sec = Section("Other (raw Dart)")
            for k in extra:
                row = PropRow(k, M.PropSpec("code"), self.ctx)
                row.committed.connect(self._prop)
                lab = QLabel(k)
                lab.setProperty("i18n_skip", True)
                sec.form.addRow(lab, row)
                self.rows[k] = row
            lay.addWidget(sec)
        if spec.events:
            sec = Section("Events")
            for ev, sig in spec.events.items():
                row = QWidget()
                h = _hbox(row)
                le = QLineEdit()
                le.setPlaceholderText("double-click: create handler")
                le.setToolTip(f"{ev}({sig}) - a handler name, nav:/route, replace:/route, push:Screen or back.\n"
                              "Double-click creates the handler in the screen's _events.dart file (like VB).")
                le.editingFinished.connect(lambda ev=ev, le=le: self.designer.set_event(self.node_id, ev,
                                                                                        le.text().strip() or None))
                le.mouseDoubleClickEvent = lambda _e, ev=ev: self.designer.create_handler(self.node_id, ev)
                btn = QToolButton()
                btn.setText("...")
                btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
                m = QMenu(btn)
                m.aboutToShow.connect(lambda m=m, ev=ev: self._event_menu(m, ev))
                btn.setMenu(m)
                h.addWidget(le, 1)
                h.addWidget(btn)
                lab = QLabel(ev)
                lab.setProperty("i18n_skip", True)
                sec.form.addRow(lab, row)
                self.events[ev] = le
            lay.addWidget(sec)
        if node.get("type") != "Scaffold":
            lay.addWidget(self._anim_section())

    def _event_menu(self, m: QMenu, ev: str):
        m.clear()
        m.addAction("Create / go to handler", lambda: self.designer.create_handler(self.node_id, ev))
        nav = m.addMenu("Navigate to screen")
        for name, route in self.designer.screens_list():
            nav.addAction(f"{name}  ({route})", lambda r=route: self.designer.set_event(self.node_id, ev, f"nav:{r}"))
        if not nav.actions():
            nav.setEnabled(False)
        rep = m.addMenu("Replace with screen")
        for name, route in self.designer.screens_list():
            rep.addAction(f"{name}  ({route})",
                          lambda r=route: self.designer.set_event(self.node_id, ev, f"replace:{r}"))
        m.addAction("Go back (Navigator.pop)", lambda: self.designer.set_event(self.node_id, ev, "back"))
        scr = self.designer.screen
        tr = m.addMenu("Push with transition")
        for name, _route in self.designer.screens_list():
            sub = tr.addMenu(name)
            for t in MO.TRANSITIONS:
                sub.addAction(t, lambda n=name, t=t: self.designer.set_event(self.node_id, ev,
                                                                              f"push:{n}?transition={t}"))
        tr.setEnabled(bool(tr.actions()))
        tg = m.addMenu("Toggle state variable")
        for s in MO.state_fields(scr):
            if s.get("type", "bool") == "bool":
                tg.addAction(s["name"], lambda n=s["name"]: self.designer.set_event(self.node_id, ev, f"toggle:{n}"))
        tg.setEnabled(bool(tg.actions()))
        pl = m.addMenu("Play / reverse animation")
        ctrls = [t["name"] for t in MO.timelines(scr)] + sorted(
            {MO.controller_name(n) for n, *_ in scr.walk()
             if MO.trigger_of(n.get("anim"))[0] == "manual" or (n.get("anim") or {}).get("controller")})
        for c in ctrls:
            pl.addAction(f"play:{c}", lambda c=c: self.designer.set_event(self.node_id, ev, f"play:{c}"))
            pl.addAction(f"reverse:{c}", lambda c=c: self.designer.set_event(self.node_id, ev, f"reverse:{c}"))
        pl.setEnabled(bool(ctrls))
        m.addSeparator()
        m.addAction("Clear", lambda: self.designer.set_event(self.node_id, ev, None))

    def _anim_section(self) -> Section:
        sec = Section("Animation", expanded=False)
        self.anim_sec = sec
        typ = QComboBox()
        typ.addItem("(none)", None)
        for t in M.ANIM_TYPES:
            typ.addItem(t, t)
        preset = QComboBox()
        preset.addItem("Apply a preset...", None)
        try:
            from . import animations as AN
            group = None
            for p in AN.PRESETS:
                if p.group != group and group is not None:
                    preset.insertSeparator(preset.count())
                group = p.group
                preset.addItem(p.label, p.id)
                preset.setItemData(preset.count() - 1, f"{p.group}: {p.help}", Qt.ItemDataRole.ToolTipRole)
        except Exception:  # noqa: BLE001
            pass
        delay, dur = NumberEd(self.ctx, as_int=True, placeholder="0"), NumberEd(self.ctx, as_int=True,
                                                                                placeholder="500")
        ox, oy = NumberEd(self.ctx, placeholder="0"), NumberEd(self.ctx, placeholder="30")
        curve = ChoiceEd(self.ctx, [f"Curves.{c}" for c in M.ENUMS["Curves"]], default="Curves.easeOut")
        scale = NumberEd(self.ctx, placeholder="0.8")
        play = QPushButton("Play")
        play.setToolTip("Play the entrance animations of the screen in the preview")
        play.clicked.connect(lambda: self.designer.play_animations())
        self.anim_eds = {"type": typ, "preset": preset, "delayMs": delay, "durationMs": dur, "offsetX": ox,
                         "offsetY": oy, "curve": curve, "scale": scale}
        typ.activated.connect(lambda i: self._anim("type", typ.itemData(i)))
        preset.activated.connect(lambda i: self._preset(preset.itemData(i)))
        for k in ("delayMs", "durationMs", "offsetX", "offsetY", "curve", "scale"):
            self.anim_eds[k].committed.connect(lambda v, k=k: self._anim(k, v))
        sec.form.addRow("Animation type", typ)
        sec.form.addRow("Preset", preset)
        sec.form.addRow("Delay (ms)", delay)
        sec.form.addRow("Duration (ms)", dur)
        sec.form.addRow("Offset X", ox)
        sec.form.addRow("Offset Y", oy)
        sec.form.addRow("Curve", curve)
        sec.form.addRow("Scale", scale)
        from .motion_ui import AnimExtra
        self.anim_extra = AnimExtra(self.designer)
        self.anim_extra.changed.connect(self._anim)
        sec.form.addRow(self.anim_extra)
        sec.form.addRow("", play)
        return sec

    def _screen_section(self, lay):
        scr = self.designer.screen
        sec = Section("Screen")
        name = StringEd(self.ctx)
        name.committed.connect(lambda v: v and self.designer.set_screen("name", M.class_name(v)))
        route = StringEd(self.ctx)
        route.committed.connect(lambda v: self.designer.set_screen("route", v or None))
        sec.form.addRow("Screen name", name)
        sec.form.addRow("Route", route)
        seed, bright, font, bg = ColorEd(self.ctx), ChoiceEd(self.ctx, ["light", "dark"]), FontEd(self.ctx), \
            ColorEd(self.ctx)
        for k, ed in (("seedColor", seed), ("brightness", bright), ("fontFamily", font), ("background", bg)):
            ed.committed.connect(lambda v, k=k: self._theme(k, v))
        sec.form.addRow("Theme seed colour", seed)
        sec.form.addRow("Brightness", bright)
        sec.form.addRow("Theme font", font)
        sec.form.addRow("Background", bg)
        self.screen_eds = {"name": name, "route": route, "seedColor": seed, "brightness": bright,
                           "fontFamily": font, "background": bg}
        info = QLabel(f"{len(list(scr.walk()))} widgets  -  file: {self.designer.path.name if self.designer.path else ''}")
        info.setStyleSheet("color: gray")
        sec.form.addRow(info)
        lay.addWidget(sec)
        lay.addWidget(self._motion_section())

    def _motion_section(self) -> Section:
        """State variables, timelines, page transition and sizes of the screen."""
        from . import motion_ui as MU
        scr = self.designer.screen
        sec = Section("Motion and sizes", expanded=bool(scr.data.get("state") or scr.data.get("timelines") or
                                                        scr.data.get("transition") or scr.data.get("variants")))

        def table(key, title, cols, help_text):
            def run():
                dlg = MU.RowsDialog(title, cols, MU.copy_screen_list(self.designer.screen, key), self, help_text)
                if dlg.exec():
                    self.designer.set_screen(key, dlg.rows() or None)
            return run
        b_state = QPushButton(f"State variables... ({len(MO.state_fields(scr))})")
        b_state.clicked.connect(table("state", "State variables", MU.STATE_COLUMNS,
                                      "Fields of the screen's State: animate properties with them ($when), toggle "
                                      "them from events (toggle:name) or start animations (trigger state:name)."))
        b_tl = QPushButton(f"Timelines... ({len(MO.timelines(scr))})")
        b_tl.clicked.connect(table("timelines", "Timelines", MU.TIMELINE_COLUMNS,
                                   "AnimationControllers of the screen: drive FadeTransition / SlideTransition ... "
                                   "($timeline) and start them from events (play:name, reverse:name)."))
        trans = QComboBox()
        trans.addItem("(default)", None)
        for t in MO.TRANSITIONS:
            trans.addItem(t, t)
        cur = MO.transition_of(scr) or {}
        trans.setCurrentIndex(max(0, trans.findData(cur.get("type"))))
        ms = QSpinBox()
        ms.setRange(50, 5000)
        ms.setSingleStep(50)
        ms.setValue(int(cur.get("durationMs") or 300))
        ms.setSuffix(" ms")

        def set_trans(*_a):
            t = trans.currentData()
            self.designer.set_screen("transition", None if not t else
                                     ({"type": t} if ms.value() == 300 else {"type": t, "durationMs": ms.value()}))
        trans.activated.connect(set_trans)
        ms.editingFinished.connect(set_trans)
        b_sizes = QPushButton(f"Sizes... ({len(VF.sizes(scr))})")
        b_sizes.clicked.connect(self.designer.edit_sizes_dialog)
        sec.form.addRow("State", b_state)
        sec.form.addRow("Timelines", b_tl)
        sec.form.addRow("Page transition", trans)
        sec.form.addRow("", ms)
        sec.form.addRow("Sizes", b_sizes)
        return sec

    def _row_menu(self, key: str, ps: M.PropSpec, lab: QLabel):
        """Right-click on a property name: per-size actions and animated values."""
        from PyQt6.QtGui import QCursor
        from . import motion_ui as MU
        d = self.designer
        node = d.screen.find(self.node_id) if self.node_id else None
        if node is None:
            return
        m = QMenu(self)
        vid = d.this_size()
        sizes = VF.sizes(d.screen)
        if vid:
            o = VF.overrides(node, vid)
            m.addAction("Apply to all sizes", lambda: d.apply(VF.apply_to_all, node["id"], vid, key,
                                                              text=f"{key}: all sizes")).setEnabled(key in o)
            m.addAction("Reset to base", lambda: d.apply(VF.remove_override, node["id"], vid, key,
                                                         text=f"{key}: base")).setEnabled(key in o)
            cp = m.addMenu("Copy to")
            for s2 in sizes:
                if s2["id"] != vid:
                    cp.addAction(VF.label(s2), lambda t=s2["id"]: d.apply(VF.copy_to, node["id"], vid, key, t,
                                                                          text=f"{key}: copy"))
            cp.setEnabled(len(sizes) > 1)
            hidden = VF.is_hidden(node, vid)
            m.addAction("Show on this size" if hidden else "Hide on this size",
                        lambda: d.set_hidden(node["id"], vid, False if hidden else True))
            m.addSeparator()
        elif sizes:
            elsewhere = [VF.label(s2) for s2 in sizes if key in VF.overrides(node, s2["id"])]
            a = m.addAction("Overridden on: " + (", ".join(elsewhere) if elsewhere else "no size"))
            a.setEnabled(False)
            m.addSeparator()
        cur = (node.get("props") or {}).get(key)

        def animate():
            dlg = MU.WhenDialog(d.screen, key, ps.kind, cur, self)
            if dlg.exec():
                d.set_prop(node["id"], key, dlg.value())
        m.addAction("Animate value (state / timeline)...", animate)
        a = m.addAction("Remove animated value", lambda: d.set_prop(node["id"], key, None))
        a.setEnabled(MO.is_when(cur) or MO.is_timeline(cur))
        m.exec(QCursor.pos())

    # ------------------------------------------------------------------ values
    def refresh(self):
        scr = self.designer.screen
        node = scr.find(self.node_id) if self.node_id else None
        if self.node_id and node is None:
            self.inspect(None, force=True)
            return
        if self.screen_eds:
            th = scr.data.get("theme") or {}
            vals = {"name": scr.data.get("name"), "route": scr.data.get("route"), **{k: th.get(k) for k in
                                                                                   ("seedColor", "brightness",
                                                                                    "fontFamily", "background")}}
            for k, ed in self.screen_eds.items():
                ed.blockSignals(True)
                ed.set_value(vals.get(k))
                ed.blockSignals(False)
        if node is None:
            return
        pr = dict(node.get("props") or {})
        vid = self.designer.this_size() if hasattr(self.designer, "this_size") else None
        if vid:                            # This size only: the values seen on that size
            pr.update({k: v for k, v in VF.overrides(node, vid).items() if k != VF.HIDDEN})
        for k, row in self.rows.items():
            row.set_value(pr.get(k))
        for k, lab in getattr(self, "labels", {}).items():
            mark = VF.marker(node, k, vid)
            lab.setText((mark + " " if mark else "") + str(lab.property("rad_text") or k))
            lab.setStyleSheet("color: #F7630C; font-weight: bold" if mark == VF.MARK_HERE else "")
        evs = node.get("events") or {}
        for k, le in self.events.items():
            le.setText(evs.get(k) or "")
        if self.name_edit is not None:
            self.name_edit.setText(node.get("name") or "")
        a = node.get("anim") or {}
        if self.anim_eds:
            t = self.anim_eds["type"]
            t.setCurrentIndex(max(0, t.findData(a.get("type"))) if a else 0)
            for k in ("delayMs", "durationMs", "offsetX", "offsetY", "curve", "scale"):
                ed = self.anim_eds[k]
                ed.blockSignals(True)
                ed.set_value(a.get(k))
                ed.blockSignals(False)
            if a:
                self.anim_sec.head.setChecked(True)
            if self.anim_extra is not None:
                self.anim_extra.set_anim(a)

    def _prop(self, key, value):
        if self.node_id:
            self.designer.set_prop(self.node_id, key, value)

    def _anim(self, key, value):
        if not self.node_id:
            return
        node = self.designer.screen.find(self.node_id)
        a = dict(node.get("anim") or {})
        if key == "type":
            if value is None:
                self.designer.set_anim(self.node_id, None)
                return
            a["type"] = value
        else:
            if not a:
                a["type"] = "fadeInUp"
            if value is None:
                a.pop(key, None)
            else:
                a[key] = value
        self.designer.set_anim(self.node_id, a)

    def _preset(self, pid):
        if not pid or not self.node_id:
            return
        try:
            from . import animations as AN
            a = AN.make_anim(pid)
        except Exception:  # noqa: BLE001
            return
        node = self.designer.screen.find(self.node_id)
        old = node.get("anim") or {}
        if "delayMs" in old:
            a["delayMs"] = old["delayMs"]
        self.designer.set_anim(self.node_id, a)
        self.anim_eds["preset"].setCurrentIndex(0)

    def _theme(self, key, value):
        th = dict(self.designer.screen.data.get("theme") or {})
        if value is None:
            th.pop(key, None)
        else:
            th[key] = value
        self.designer.set_screen("theme", th)

