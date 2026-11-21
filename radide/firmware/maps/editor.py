"""The map editor (Qt): one calibration map as a table (axes + physical values, heat-map or ori/mod colouring),
a 2D line chart and a 3D surface, with editing tools - set value, +/- %, add, multiply, interpolate, smooth,
copy / paste with Excel, reset to original - written back to the working copy (one undo step per operation).

The editor works on a *buffer* with ``data`` and ``replace(offset, bytes)`` (radide/retro/rom/buffer.HexBuffer
gives undo / redo) and an optional *original* (bytes) for the differences.
"""
from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QItemSelectionModel, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QInputDialog, QLabel, QMenu, QSplitter,
                             QTableView, QTabWidget, QToolBar, QToolButton, QVBoxLayout, QWidget)

from . import ops
from .model import DTYPE_LABELS, MapDef, fmt_hex, map_to_tsv
from .views import CurveChart, MapTableModel, Surface3D
from .views import tr_ui as _tr


class MapEditor(QWidget):
    edited = pyqtSignal()                 # bytes of the map changed
    message = pyqtSignal(str)
    propertiesRequested = pyqtSignal()

    def __init__(self, buf=None, original=None, parent=None, read_only: bool = False):
        super().__init__(parent)
        self.buf = buf
        self.original = original          # bytes or None
        self.m: MapDef | None = None
        self.read_only = read_only
        self._build()

    # ------------------------------------------------------------------ ui
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        head = QHBoxLayout()
        head.setContentsMargins(6, 4, 6, 0)
        self.title = QLabel("No map selected")
        f = self.title.font()
        f.setBold(True)
        self.title.setFont(f)
        self.title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        head.addWidget(self.title, 1)
        head.addWidget(QLabel("Colours:"))
        self.colour = QComboBox()
        self.colour.addItem(_tr("Heat map"), "heat")
        self.colour.addItem(_tr("Differences vs original"), "diff")
        self.colour.addItem(_tr("None"), "plain")
        self.colour.currentIndexChanged.connect(self._on_colour)
        head.addWidget(self.colour)
        lay.addLayout(head)
        self.info = QLabel("")
        self.info.setContentsMargins(6, 0, 6, 0)
        self.info.setWordWrap(True)
        lay.addWidget(self.info)

        tb = QToolBar("Map")
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.toolbar = tb
        self.actions_: dict[str, QAction] = {}

        def act(key, text, slot, shortcut=None, tip=""):
            a = QAction(text, self)
            a.triggered.connect(lambda _c=False: slot())
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
                a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            if tip:
                a.setToolTip(tip)
            self.actions_[key] = a
            self.addAction(a)
            return a
        tb.addAction(act("set", "Set Value...", self.op_set, "=", "Set the selected cells to a value"))
        tb.addAction(act("pct", "+/- %...", self.op_percent, "%", "Change the selected cells by a percentage"))
        tb.addAction(act("add", "Add...", self.op_add, "+", "Add a value to the selected cells"))
        tb.addAction(act("mul", "Multiply...", self.op_multiply, "*", "Multiply the selected cells"))
        interp = QToolButton()
        interp.setText("Interpolate")
        interp.setToolTip("Linear interpolation inside the selection from its edges")
        interp.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        im = QMenu(interp)
        im.addAction(act("interp", "Interpolate (auto)", lambda: self.op_interpolate("auto"), "I"))
        im.addAction(act("interp_h", "Interpolate Horizontally", lambda: self.op_interpolate("h")))
        im.addAction(act("interp_v", "Interpolate Vertically", lambda: self.op_interpolate("v")))
        im.addAction(act("interp_2d", "Interpolate Bilinear (corners)", lambda: self.op_interpolate("2d")))
        interp.setMenu(im)
        interp.setDefaultAction(self.actions_["interp"])
        interp.setText("Interpolate")
        tb.addWidget(interp)
        tb.addAction(act("smooth", "Smooth", self.op_smooth, "S", "3x3 average of the selected cells"))
        tb.addSeparator()
        tb.addAction(act("copy", "Copy", self.copy, QKeySequence.StandardKey.Copy, "Copy the selection (Excel)"))
        tb.addAction(act("copy_axes", "Copy with Axes", lambda: self.copy(with_axes=True)))
        tb.addAction(act("paste", "Paste", self.paste, QKeySequence.StandardKey.Paste, "Paste from Excel / text"))
        tb.addAction(act("reset", "Reset to Original", self.op_reset,
                         tip="Put the original values back into the selected cells"))
        tb.addSeparator()
        tb.addAction(act("props", "Properties...", self.propertiesRequested.emit,
                         tip="Address, type, factor / offset, units and axes of the map"))
        lay.addWidget(tb)

        split = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableView()
        self.model = MapTableModel(self)
        self.model.cellEdited.connect(self._on_cell_edited)
        self.table.setModel(self.model)
        self.table.setProperty("i18n_skip_items", True)
        self.table.horizontalHeader().setDefaultSectionSize(64)
        self.table.verticalHeader().setDefaultSectionSize(22)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.selectionModel().selectionChanged.connect(lambda *_a: self._on_selection())
        split.addWidget(self.table)
        self.views = QTabWidget()
        self.views.setDocumentMode(True)
        self.chart = CurveChart()
        self.surface = Surface3D()
        self.views.addTab(self.surface, "3D")
        self.views.addTab(self.chart, "2D")
        split.addWidget(self.views)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        lay.addWidget(split, 1)
        self.status = QLabel("")
        self.status.setContentsMargins(6, 0, 6, 2)
        lay.addWidget(self.status)
        self._set_enabled(False)

    def _set_enabled(self, on: bool) -> None:
        for k, a in self.actions_.items():
            a.setEnabled(on and (k in ("copy", "copy_axes", "props") or not self.read_only))

    # ------------------------------------------------------------------ data
    def data(self):
        if self.buf is None:
            return b""
        return self.buf.data if hasattr(self.buf, "data") else self.buf

    def set_map(self, m: MapDef | None) -> None:
        self.m = m
        self._set_enabled(m is not None)
        if m is None:
            self.title.setText("No map selected")
            self.info.setText("")
            self.model.set_values(np.zeros((0, 0)), [], [])
            self.chart.set_values(np.zeros((0, 0)), [], [])
            self.surface.set_values(np.zeros((0, 0)), [], [])
            return
        self.model.read_only = self.read_only
        self.refresh(reset=True)

    def ori_values(self):
        if self.m is None or self.original is None or self.m.end > len(self.original):
            return None
        return self.m.phys(self.original)

    def refresh(self, reset: bool = False) -> None:
        m = self.m
        if m is None:
            return
        d = self.data()
        z = m.phys(d)
        x, y = m.x_values(d), m.y_values(d)
        ori = self.ori_values()
        dims = {"value": "single value", "curve": f"curve, {m.cols} points",
                "map": f"map {m.cols} x {m.rows}"}[m.kind]
        self.title.setText(f"{m.name} - {_tr(dims)}")
        bits = [_tr(f"Address {fmt_hex(m.address)}"), _tr(DTYPE_LABELS.get(m.dtype, m.dtype)) +
                ("" if m.cell_size == 1 else (" Hi-Lo" if m.endian == "be" else " Lo-Hi")),
                _tr(f"factor {m.factor:g}, offset {m.offset:g}") + (f" [{m.unit}]" if m.unit else "")]
        if m.kind == "map" and m.order == "col":
            bits.append(_tr("column order"))
        for nm, ax in (("X", m.x_axis), ("Y", m.y_axis)):
            if m.kind == "value" or (nm == "Y" and m.kind != "map"):
                continue
            src = f"{fmt_hex(int(ax.address))}" if ax.stored else _tr("fixed values" if ax.values else "index")
            bits.append(f"{nm}: {ax.name or '-'} ({src}{', ' + ax.unit if ax.unit else ''})")
        if m.description:
            bits.append(m.description)
        self.info.setText("   |   ".join(bits))
        if reset or self.model.z.shape != z.shape:
            self.model.set_values(z, x, y, ori, m.digits)
        else:
            self.model.x, self.model.y, self.model.ori = np.asarray(x), np.asarray(y), ori
            self.model.update_values(z)
            self.model.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, max(0, z.shape[1] - 1))
            self.model.headerDataChanged.emit(Qt.Orientation.Vertical, 0, max(0, z.shape[0] - 1))
        self.chart.set_values(z, x, y, ori, m.unit)
        self.surface.set_values(z, x, y, ori)
        self.views.setTabEnabled(0, m.kind != "value")
        if m.kind == "curve" and self.views.currentIndex() == 0:
            self.views.setCurrentIndex(1)
        self._on_selection()

    def _on_colour(self) -> None:
        self.model.mode = self.colour.currentData()
        self.model.layoutChanged.emit()
        self.surface.show_original = self.model.mode == "diff"
        self.surface.update()

    # ------------------------------------------------------------------ selection
    def selection_mask(self) -> np.ndarray:
        z = self.model.z
        mask = np.zeros(z.shape, dtype=bool)
        for idx in self.table.selectionModel().selectedIndexes():
            mask[idx.row(), idx.column()] = True
        if not mask.any():
            cur = self.table.currentIndex()
            if cur.isValid():
                mask[cur.row(), cur.column()] = True
        return mask

    def select_cells(self, r0: int, c0: int, r1: int, c1: int) -> None:
        sm = self.table.selectionModel()
        sm.clearSelection()
        from PyQt6.QtCore import QItemSelection
        sel = QItemSelection(self.model.index(min(r0, r1), min(c0, c1)), self.model.index(max(r0, r1), max(c0, c1)))
        sm.select(sel, QItemSelectionModel.SelectionFlag.Select)
        self.table.setCurrentIndex(self.model.index(r0, c0))
        sm.select(sel, QItemSelectionModel.SelectionFlag.Select)

    def select_all(self) -> None:
        self.table.selectAll()

    def _on_selection(self) -> None:
        mask = self.selection_mask() if self.model.z.size else None
        if mask is None or not mask.any():
            self.status.setText("")
            return
        v = self.model.z[mask]
        changed = int(self.model.changed().sum())
        txt = _tr(f"{int(mask.sum())} cell(s), min {self.model.fmt(v.min())}, max {self.model.fmt(v.max())}, "
                  f"mean {self.model.fmt(round(float(v.mean()), 4))}")
        if self.model.ori is not None:
            txt += "   |   " + _tr(f"{changed} cell(s) differ from the original")
        self.status.setText(txt)
        rows = np.nonzero(mask.any(axis=1))[0]
        self.chart.highlight_row = int(rows[0]) if len(rows) == 1 else -1
        self.chart.update()

    # ------------------------------------------------------------------ editing
    def write(self, z_new, what: str = "Edit") -> bool:
        if self.m is None or self.read_only or self.buf is None:
            return False
        changed = ops.apply(self.buf, self.m, z_new)
        if changed:
            self.refresh()
            self.edited.emit()
            self.message.emit(f"{self.m.name}: {_tr(what)}")
        return changed

    def _ask(self, title: str, label: str, value: float = 0.0, decimals: int = 4):
        v, ok = QInputDialog.getDouble(self, title, label, value, -1e12, 1e12, decimals)
        return v if ok else None

    def _on_cell_edited(self, r: int, c: int, v: float) -> None:
        z = self.model.z.copy()
        z[r, c] = v
        self.write(z, "set value")

    def op_set(self, value: float | None = None) -> bool:
        mask = self.selection_mask()
        if value is None:
            cur = self.model.z[mask][0] if mask.any() else 0.0
            value = self._ask("Set Value", "New value for the selected cells:", float(cur))
            if value is None:
                return False
        return self.write(ops.set_value(self.model.z, mask, value), f"set {value:g}")

    def op_percent(self, pct: float | None = None) -> bool:
        if pct is None:
            pct = self._ask("Change by Percent", "Percent (negative to lower):", 5.0, 2)
            if pct is None:
                return False
        return self.write(ops.add_percent(self.model.z, self.selection_mask(), pct), f"{pct:+g}%")

    def op_add(self, v: float | None = None) -> bool:
        if v is None:
            v = self._ask("Add", "Value to add (negative to subtract):", 1.0)
            if v is None:
                return False
        return self.write(ops.add(self.model.z, self.selection_mask(), v), f"add {v:g}")

    def op_multiply(self, f: float | None = None) -> bool:
        if f is None:
            f = self._ask("Multiply", "Factor:", 1.05)
            if f is None:
                return False
        return self.write(ops.multiply(self.model.z, self.selection_mask(), f), f"multiply by {f:g}")

    def op_interpolate(self, direction: str = "auto") -> bool:
        return self.write(ops.interpolate(self.model.z, self.selection_mask(), direction), "interpolate")

    def op_smooth(self) -> bool:
        return self.write(ops.smooth(self.model.z, self.selection_mask()), "smooth")

    def op_reset(self) -> bool:
        ori = self.ori_values()
        if ori is None:
            self.message.emit("There is no original to compare with.")
            return False
        mask = self.selection_mask()
        if not mask.any():
            mask = ops.full_mask(ori)
        z = self.model.z.copy()
        z[mask] = ori[mask]
        return self.write(z, "reset to original")

    def copy(self, with_axes: bool = False) -> str:
        if self.m is None:
            return ""
        if with_axes:
            text = map_to_tsv(self.m, self.data(), True, self.m.digits)
        else:
            text = ops.copy_text(self.model.z, self.selection_mask() if self.selection_mask().any() else None,
                                 self.m.digits)
        QApplication.clipboard().setText(text)
        self.message.emit("Copied to the clipboard (tab separated: paste into Excel)")
        return text

    def paste(self, text: str | None = None) -> bool:
        if self.m is None:
            return False
        text = QApplication.clipboard().text() if text is None else text
        if not text.strip():
            return False
        cur = self.table.currentIndex()
        mask = self.selection_mask()
        r0, c0 = (cur.row(), cur.column()) if cur.isValid() else (0, 0)
        if mask.any():
            rs, cs = np.nonzero(mask)
            r0, c0 = int(rs.min()), int(cs.min())
        # a block copied "with axes" from this map: drop the axis row / column
        from .model import parse_tsv
        grid = parse_tsv(text)
        z = self.model.z
        if self.m.kind == "map" and len(grid) == z.shape[0] + 1 and grid and len(grid[1]) == z.shape[1] + 1:
            text = "\n".join("\t".join("" if v is None else repr(v) for v in row[1:]) for row in grid[1:])
            r0 = c0 = 0
        elif self.m.kind == "curve" and len(grid) == 2 and len(grid[1]) == z.shape[1]:
            text = "\t".join(repr(v) if v is not None else "" for v in grid[1])
            r0 = c0 = 0
        z_new, changed = ops.paste(z, text, r0, c0)
        if not changed.any():
            return False
        return self.write(z_new, f"paste {int(changed.sum())} cell(s)")

    def _context_menu(self, pos) -> None:
        m = QMenu(self)
        for k in ("set", "pct", "add", "mul", None, "interp", "interp_h", "interp_v", "interp_2d", "smooth", None,
                  "copy", "copy_axes", "paste", "reset", None, "props"):
            if k is None:
                m.addSeparator()
            else:
                m.addAction(self.actions_[k])
        m.exec(self.table.viewport().mapToGlobal(pos))
