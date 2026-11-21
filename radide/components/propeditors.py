"""Schema-driven Properties window editors (radide/properties.py uses them for the kinds below and for every
property with an ``editor`` id).

Kinds edited here: multiline, flags, image, file (with a ``filter``), columns, alignment, gradient, shadow,
border, custom - plus any property whose manifest names a custom editor from the package's ``editors.py``
(see docs/COMPONENTS.md "Custom property editors"). The plain kinds (str, int, float, bool, enum, color, font,
list, anchor, dbref, menu) keep the Properties window's own editors.
"""
from __future__ import annotations

import shutil
import traceback
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPixmap
from PyQt6.QtWidgets import (QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                             QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton,
                             QSpinBox, QVBoxLayout)

from . import proptypes

DIALOG_KINDS = ("multiline", "flags", "columns", "gradient", "shadow", "border")
OWN_KINDS = DIALOG_KINDS + ("image", "alignment", "custom")


class EditorContext:
    """What a custom editor gets: the property, the control's values, the form and the project."""

    def __init__(self, panel, d):
        self.panel = panel
        self.propdef = d
        self.name = d.name
        doc = getattr(panel, "doc", None)
        self.control = panel._owner() if doc is not None else None
        self.form = doc.form if doc is not None else None
        self.props = dict(panel._props_dict()) if doc is not None else {}
        self.project_folder = Path(doc.path).parent if doc is not None and getattr(doc, "path", None) else None
        from . import package_of
        self.package = package_of(self.control.type) if self.control is not None else None


def custom_editor(panel, d):
    """The package editor object for *d* (None if the property has no editor id or it is not found)."""
    if not d.editor:
        return None
    from . import package_of
    owner = panel._owner() if getattr(panel, "doc", None) is not None else None
    pkg = package_of(owner.type) if owner is not None else None
    if pkg is None:
        return None
    try:
        return pkg.editor(d.editor)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return None


def handles(panel, d) -> bool:
    if d.kind in OWN_KINDS:
        return True
    if d.kind == "file" and d.meta and d.meta.get("filter"):
        return True
    return bool(d.editor) and custom_editor(panel, d) is not None


def _button(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setStyleSheet("text-align:left; padding-left:4px;")
    return b


def _commit(panel, name, value) -> None:
    panel._set(name, value)
    panel._refresh_values()


def cell_widget(panel, row: int, d, value, mixed: bool = False) -> None:
    """Create (once) or update the value cell's editor of property *d* in the Properties table. *mixed*: the
    selected controls have different values (multi-select) - the cell is blank."""
    table = panel.props
    w = table.cellWidget(row, 1)
    if w is not None and getattr(w, "rad_peng", None) != (d.name, d.kind, d.editor):
        table.removeCellWidget(row, 1)
        w = None
    ed = custom_editor(panel, d) if d.editor else None
    if ed is not None and hasattr(ed, "create"):              # inline custom editor
        ctx = EditorContext(panel, d)
        if w is None:
            try:
                w = ed.create(table, value, lambda v, n=d.name: _commit(panel, n, v), ctx)
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                w = QLabel(f"(editor error) {value}")
            w.rad_peng = (d.name, d.kind, d.editor)
            table.setCellWidget(row, 1, w)
        elif hasattr(ed, "set_value"):
            try:
                ed.set_value(w, value, ctx)
            except Exception:  # noqa: BLE001
                traceback.print_exc()
        return
    if d.kind == "alignment":
        if w is None:
            w = QComboBox()
            w.addItems(list(d.choices or proptypes.ALIGNMENTS))
            w.currentTextChanged.connect(lambda t, n=d.name: t and panel._set(n, t))
            w.rad_peng = (d.name, d.kind, d.editor)
            table.setCellWidget(row, 1, w)
        w.blockSignals(True)
        if mixed:
            w.setCurrentIndex(-1)
        else:
            w.setCurrentText(str(value or "MiddleLeft"))
        w.blockSignals(False)
        return
    if w is None:
        w = _button("")
        w.rad_peng = (d.name, d.kind, d.editor)
        w.clicked.connect(lambda _=False, dd=d: open_editor(panel, dd))
        table.setCellWidget(row, 1, w)
    text = proptypes.text_of(d.kind, value)
    if d.kind in ("image", "file"):
        text = text or "(none)"
    if d.kind == "custom" and ed is None and not d.editor:
        text = text or "(value)"
    if mixed:
        w.setText("   ...")
        w.setIcon(QIcon())
        return
    w.setText(text + "   ...")
    w.setIcon(_icon_for(d.kind, value))


def _icon_for(kind: str, value) -> QIcon:
    if kind == "gradient":
        g = proptypes.parse_gradient(value)
        if g:
            pm = QPixmap(14, 14)
            p = QPainter(pm)
            lg = QLinearGradient(0, 0, 14, 0)
            lg.setColorAt(0, QColor(g["start"]))
            lg.setColorAt(1, QColor(g["end"]))
            p.fillRect(pm.rect(), lg)
            p.end()
            return QIcon(pm)
    if kind in ("shadow", "border"):
        info = proptypes.parse_shadow(value) if kind == "shadow" else proptypes.parse_border(value)
        if info:
            pm = QPixmap(14, 14)
            pm.fill(QColor(info["color"]))
            return QIcon(pm)
    return QIcon()


def open_editor(panel, d):
    """The "..." button of a value cell."""
    props = panel._props_dict()
    value = props.get(d.name, d.default)
    ed = custom_editor(panel, d) if d.editor else None
    new = None
    if ed is not None:
        fn = getattr(ed, "edit", None) or (ed if callable(ed) else None)
        if fn is not None:
            try:
                new = fn(panel, value, EditorContext(panel, d))
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                new = None
    elif d.kind == "multiline":
        new = edit_text(panel, d.name, str(value or ""), multiline=True)
    elif d.kind == "columns":
        new = edit_text(panel, d.name, "\n".join(x for x in str(value or "").split(";") if x.strip()),
                        multiline=True, hint="One item per line.")
        new = None if new is None else ";".join(x.strip() for x in new.splitlines() if x.strip())
    elif d.kind == "flags":
        new = edit_flags(panel, d, value)
    elif d.kind == "gradient":
        new = edit_gradient(panel, value)
    elif d.kind == "shadow":
        new = edit_shadow(panel, value)
    elif d.kind == "border":
        new = edit_border(panel, value)
    elif d.kind in ("image", "file"):
        new = pick_file(panel, d)
    if new is not None:
        _commit(panel, d.name, new)
    return new


# ------------------------------------------------------------------ dialogs
def _dialog(parent, title: str):
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    lay = QVBoxLayout(dlg)
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    return dlg, lay, bb


def edit_text(parent, name: str, value: str, multiline=True, hint: str = "") -> str | None:
    dlg, lay, bb = _dialog(parent, f"{name} - Text Editor" if not hint else f"{name} - Collection Editor")
    if hint:
        lay.addWidget(QLabel(hint))
    ed = QPlainTextEdit(value)
    ed.setObjectName("radTextEditor")
    ed.setMinimumSize(360, 200)
    lay.addWidget(ed)
    lay.addWidget(bb)
    edit_text.last_dialog = dlg
    return ed.toPlainText() if dlg.exec() else None


def edit_flags(parent, d, value) -> str | None:
    dlg, lay, bb = _dialog(parent, f"{d.name}")
    lst = QListWidget()
    lst.setObjectName("radFlags")
    on = set(proptypes.parse_flags(value, d.choices))
    for c in d.choices:
        it = QListWidgetItem(c)
        it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        it.setCheckState(Qt.CheckState.Checked if c in on else Qt.CheckState.Unchecked)
        lst.addItem(it)
    lay.addWidget(lst)
    lay.addWidget(bb)
    edit_flags.last_dialog = dlg
    if not dlg.exec():
        return None
    return proptypes.format_flags([lst.item(i).text() for i in range(lst.count())
                                   if lst.item(i).checkState() == Qt.CheckState.Checked])


class _ColorButton(QPushButton):
    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.color = color or "#000000"
        self.clicked.connect(self._pick)
        self._show()

    def _show(self):
        pm = QPixmap(14, 14)
        pm.fill(QColor(self.color))
        self.setIcon(QIcon(pm))
        self.setText(self.color)

    def _pick(self):
        c = QColorDialog.getColor(QColor(self.color), self, "Colour",
                                  QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self.color = c.name(QColor.NameFormat.HexArgb) if c.alpha() < 255 else c.name()
            self._show()


def edit_gradient(parent, value) -> str | None:
    g = proptypes.parse_gradient(value) or {"start": "#FFFFFF", "end": "#C0C8D8", "angle": 90}
    dlg, lay, bb = _dialog(parent, "Gradient")
    form = QFormLayout()
    a, b = _ColorButton(g["start"]), _ColorButton(g["end"])
    angle = QSpinBox()
    angle.setRange(0, 359)
    angle.setValue(int(g["angle"]))
    form.addRow("Start colour", a)
    form.addRow("End colour", b)
    form.addRow("Angle (degrees)", angle)
    lay.addLayout(form)
    none = QPushButton("No gradient")
    result = {"none": False}
    none.clicked.connect(lambda: (result.update(none=True), dlg.accept()))
    row = QHBoxLayout()
    row.addWidget(none)
    row.addStretch(1)
    row.addWidget(bb)
    lay.addLayout(row)
    edit_gradient.last_dialog = dlg
    if not dlg.exec():
        return None
    return "" if result["none"] else proptypes.format_gradient(a.color, b.color, angle.value())


def edit_shadow(parent, value) -> str | None:
    s = proptypes.parse_shadow(value) or {"dx": 2, "dy": 2, "blur": 6, "color": "#80000000"}
    dlg, lay, bb = _dialog(parent, "Shadow")
    form = QFormLayout()
    spins = {}
    for key, label in (("dx", "X offset"), ("dy", "Y offset"), ("blur", "Blur radius")):
        sp = QSpinBox()
        sp.setRange(-50 if key != "blur" else 0, 50)
        sp.setValue(int(s[key]))
        spins[key] = sp
        form.addRow(label, sp)
    color = _ColorButton(s["color"])
    form.addRow("Colour", color)
    lay.addLayout(form)
    none = QPushButton("No shadow")
    result = {"none": False}
    none.clicked.connect(lambda: (result.update(none=True), dlg.accept()))
    row = QHBoxLayout()
    row.addWidget(none)
    row.addStretch(1)
    row.addWidget(bb)
    lay.addLayout(row)
    edit_shadow.last_dialog = dlg
    if not dlg.exec():
        return None
    return "" if result["none"] else proptypes.format_shadow(spins["dx"].value(), spins["dy"].value(),
                                                             spins["blur"].value(), color.color)


def edit_border(parent, value) -> str | None:
    b = proptypes.parse_border(value) or {"width": 1, "style": "solid", "color": "#808080", "radius": 0}
    dlg, lay, bb = _dialog(parent, "Border")
    form = QFormLayout()
    width = QSpinBox()
    width.setRange(0, 40)
    width.setValue(int(b["width"]))
    style = QComboBox()
    style.addItems(list(proptypes.BORDER_STYLES))
    style.setCurrentText(b["style"])
    color = _ColorButton(b["color"])
    radius = QSpinBox()
    radius.setRange(0, 200)
    radius.setValue(int(b["radius"]))
    form.addRow("Width", width)
    form.addRow("Style", style)
    form.addRow("Colour", color)
    form.addRow("Corner radius", radius)
    lay.addLayout(form)
    lay.addWidget(bb)
    edit_border.last_dialog = dlg
    if not dlg.exec():
        return None
    return proptypes.format_border(width.value(), style.currentText(), color.color, radius.value())


def pick_file(panel, d) -> str | None:
    doc = panel.doc
    root = Path(doc.path).parent
    flt = (d.meta or {}).get("filter") or ("Images (*.png *.gif *.ico *.jpg *.jpeg *.bmp *.svg);;All files (*)"
                                            if d.kind == "image" else "All files (*)")
    f, _ = QFileDialog.getOpenFileName(panel, f"Choose {d.name}", str(root), flt)
    if not f:
        return None
    src = Path(f)
    try:
        rel = src.resolve().relative_to(root.resolve())
    except ValueError:                     # outside files go to the project's Resources folder
        res = root / "Resources"
        res.mkdir(exist_ok=True)
        dst = res / src.name
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
        rel = dst.relative_to(root)
    return rel.as_posix()


__all__ = ["EditorContext", "OWN_KINDS", "handles", "cell_widget", "open_editor", "custom_editor", "edit_text",
           "edit_flags", "edit_gradient", "edit_shadow", "edit_border", "pick_file"]
