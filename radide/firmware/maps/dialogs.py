"""Dialogs of the map tools: map properties (address, type, shape, factor / offset, units, axes) and the import
options of A2L / TunerStudio files."""
from __future__ import annotations

from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                             QGroupBox, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QVBoxLayout, QWidget)

from .model import DTYPE_LABELS, DTYPES, AxisDef, MapDef, fmt_hex, parse_int
from .views import tr_ui as _tr


def _dtype_combo(value: str) -> QComboBox:
    c = QComboBox()
    for k in DTYPES:
        c.addItem(_tr(DTYPE_LABELS.get(k, k)), k)
    c.setCurrentIndex(max(0, c.findData(value)))
    return c


def _endian_combo(value: str) -> QComboBox:
    c = QComboBox()
    c.addItem(_tr("Lo-Hi (little endian)"), "le")
    c.addItem(_tr("Hi-Lo (big endian)"), "be")
    c.setCurrentIndex(0 if value == "le" else 1)
    return c


def _dspin(v: float, lo=-1e12, hi=1e12, dec=8) -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(dec)
    s.setValue(v)
    return s


class _AxisBox(QGroupBox):
    def __init__(self, title: str, ax: AxisDef, parent=None):
        super().__init__(title, parent)
        f = QFormLayout(self)
        self.kind = QComboBox()
        self.kind.addItem(_tr("Stored in the file"), "stored")
        self.kind.addItem(_tr("Fixed values"), "values")
        self.kind.addItem(_tr("Index (0, 1, 2 ...)"), "index")
        self.kind.setCurrentIndex(0 if ax.stored else 1 if ax.values else 2)
        f.addRow("Axis:", self.kind)
        self.name = QLineEdit(ax.name)
        f.addRow("Name:", self.name)
        self.address = QLineEdit(fmt_hex(int(ax.address)) if ax.address is not None else "")
        f.addRow("Address:", self.address)
        self.dtype = _dtype_combo(ax.dtype)
        f.addRow("Data type:", self.dtype)
        self.endian = _endian_combo(ax.endian)
        f.addRow("Byte order:", self.endian)
        self.factor = _dspin(ax.factor)
        self.offset = _dspin(ax.offset)
        f.addRow("Factor:", self.factor)
        f.addRow("Offset:", self.offset)
        self.unit = QLineEdit(ax.unit)
        f.addRow("Unit:", self.unit)
        self.values = QLineEdit(" ".join(f"{v:g}" for v in (ax.values or [])))
        self.values.setPlaceholderText("e.g. 500 1000 1500 2000")
        f.addRow("Fixed values:", self.values)
        self.kind.currentIndexChanged.connect(self._sync)
        self._sync()

    def _sync(self) -> None:
        k = self.kind.currentData()
        for w in (self.address, self.dtype, self.endian, self.factor, self.offset):
            w.setEnabled(k == "stored")
        self.values.setEnabled(k == "values")

    def axis(self, count: int) -> AxisDef:
        k = self.kind.currentData()
        ax = AxisDef(name=self.name.text().strip(), dtype=self.dtype.currentData(), endian=self.endian.currentData(),
                     factor=self.factor.value() or 1.0, offset=self.offset.value(), unit=self.unit.text().strip())
        if k == "stored" and self.address.text().strip():
            ax.address, ax.count = parse_int(self.address.text()), count
        elif k == "values":
            ax.values = [float(v) for v in self.values.text().replace(",", " ").split()]
            ax.count = len(ax.values)
        return ax


class MapPropertiesDialog(QDialog):
    """Edit a map definition. ``result_map()`` returns the new MapDef."""

    def __init__(self, m: MapDef, parent=None, folders=()):
        super().__init__(parent)
        self.setWindowTitle("Map Properties")
        self.m = m
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        left = QWidget()
        f = QFormLayout(left)
        self.name = QLineEdit(m.name)
        f.addRow("Name:", self.name)
        self.folder = QComboBox()
        self.folder.setEditable(True)
        self.folder.addItems(sorted({x for x in folders if x} | ({m.folder} if m.folder else set())))
        self.folder.setCurrentText(m.folder)
        f.addRow("Folder:", self.folder)
        self.address = QLineEdit(fmt_hex(m.address))
        f.addRow("Address:", self.address)
        self.cols = QSpinBox()
        self.cols.setRange(1, 4096)
        self.cols.setValue(m.cols)
        self.rows = QSpinBox()
        self.rows.setRange(1, 4096)
        self.rows.setValue(m.rows)
        f.addRow("Columns (X):", self.cols)
        f.addRow("Rows (Y):", self.rows)
        self.dtype = _dtype_combo(m.dtype)
        f.addRow("Data type:", self.dtype)
        self.endian = _endian_combo(m.endian)
        f.addRow("Byte order:", self.endian)
        self.order = QComboBox()
        self.order.addItem(_tr("Row by row (X fastest)"), "row")
        self.order.addItem(_tr("Column by column (Y fastest)"), "col")
        self.order.setCurrentIndex(0 if m.order == "row" else 1)
        f.addRow("Storage order:", self.order)
        self.factor = _dspin(m.factor)
        self.offset = _dspin(m.offset)
        f.addRow("Factor:", self.factor)
        f.addRow("Offset:", self.offset)
        f.addRow(QLabel("physical value = raw x factor + offset"))
        self.unit = QLineEdit(m.unit)
        f.addRow("Unit:", self.unit)
        self.digits = QSpinBox()
        self.digits.setRange(-1, 10)
        self.digits.setSpecialValueText(_tr("auto"))
        self.digits.setValue(-1 if m.digits is None else m.digits)
        f.addRow("Decimals:", self.digits)
        self.desc = QLineEdit(m.description)
        f.addRow("Description:", self.desc)
        top.addWidget(left)
        axes = QVBoxLayout()
        self.xbox = _AxisBox("X axis", m.x_axis)
        self.ybox = _AxisBox("Y axis", m.y_axis)
        axes.addWidget(self.xbox)
        axes.addWidget(self.ybox)
        top.addLayout(axes)
        lay.addLayout(top)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def result_map(self) -> MapDef:
        m = MapDef(name=self.name.text().strip() or self.m.name, address=parse_int(self.address.text()),
                   cols=self.cols.value(), rows=self.rows.value(), dtype=self.dtype.currentData(),
                   endian=self.endian.currentData(), order=self.order.currentData(), factor=self.factor.value() or 1.0,
                   offset=self.offset.value(), unit=self.unit.text().strip(), folder=self.folder.currentText().strip(),
                   description=self.desc.text().strip(), source=self.m.source or "manual",
                   lower=self.m.lower, upper=self.m.upper,
                   digits=None if self.digits.value() < 0 else self.digits.value())
        m.x_axis = self.xbox.axis(m.cols)
        m.y_axis = self.ybox.axis(m.rows)
        return m


class ImportOptionsDialog(QDialog):
    """Base address (ECU address of file offset 0) and options before an A2L / TunerStudio import."""

    def __init__(self, title: str, base: int, parent=None, note: str = "", replace: bool = False,
                 scalars: bool | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        f = QFormLayout(self)
        if note:
            lbl = QLabel(note)
            lbl.setWordWrap(True)
            f.addRow(lbl)
        self.base = QLineEdit(fmt_hex(base))
        f.addRow("Address of file offset 0:", self.base)
        self.replace = QCheckBox("Replace the maps of the pack (otherwise add)")
        self.replace.setChecked(replace)
        f.addRow(self.replace)
        self.scalars = None
        if scalars is not None:
            self.scalars = QCheckBox("Also import single values (scalars)")
            self.scalars.setChecked(scalars)
            f.addRow(self.scalars)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def base_address(self) -> int:
        try:
            return parse_int(self.base.text())
        except ValueError:
            return 0
