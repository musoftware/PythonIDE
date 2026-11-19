"""VB-style Properties window: object selector, Categorized / Alphabetical
property grid, Events tab (handlers that exist are shown in bold)."""
from __future__ import annotations

import keyword
import shutil
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (QAbstractItemView, QColorDialog, QComboBox, QFileDialog,
                             QFontComboBox, QHBoxLayout, QHeaderView, QLabel, QPushButton,
                             QTableWidget, QTableWidgetItem, QTabWidget, QToolButton,
                             QVBoxLayout, QWidget)

from .controls import CONTROL_TYPES, EVENT_HELP, FORM_PROPS
from .document import FormDocument
from .model import Control

CATEGORY_ORDER = ["Appearance", "Behavior", "Data", "Design", "Layout", "Misc"]


def valid_identifier(s: str) -> bool:
    return s.isidentifier() and not keyword.iskeyword(s)


class PropertiesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc: FormDocument | None = None
        self.plugin = None
        self.code_provider = lambda form_name: ""      # set by the main window
        self._updating = False
        self.categorized = True

        self.selector = QComboBox()
        self.selector.currentIndexChanged.connect(self._on_selector)
        self.btn_cat = QToolButton(text="Categorized", checkable=True, checked=True)
        self.btn_alpha = QToolButton(text="A-Z", checkable=True)
        self.btn_cat.clicked.connect(lambda: self._set_mode(True))
        self.btn_alpha.clicked.connect(lambda: self._set_mode(False))
        modes = QHBoxLayout()
        modes.setContentsMargins(0, 0, 0, 0)
        modes.addWidget(self.btn_cat)
        modes.addWidget(self.btn_alpha)
        modes.addStretch(1)

        self.tabs = QTabWidget()
        self.props = self._make_table(["Property", "Value"])
        self.events = self._make_table(["Event", "Handler"])
        self.events.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.events.cellDoubleClicked.connect(self._on_event_dclick)
        self.events.currentCellChanged.connect(self._on_event_cell)
        self.props.itemChanged.connect(self._on_item_changed)
        self.props.currentCellChanged.connect(self._on_current_cell)
        self.tabs.addTab(self.props, "Properties")
        self.tabs.addTab(self.events, "Events")
        self.tabs.currentChanged.connect(lambda _i: self._refresh_events())
        self.help = QLabel()
        self.help.setWordWrap(True)
        self.help.setMinimumHeight(44)
        self.help.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.help.setStyleSheet("padding:4px; background:#f4f4f4; border-top:1px solid #ccc;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.addWidget(self.selector)
        lay.addLayout(modes)
        lay.addWidget(self.tabs, 1)
        lay.addWidget(self.help)

    @staticmethod
    def _make_table(headers) -> QTableWidget:
        t = QTableWidget(0, 2)
        t.setHorizontalHeaderLabels(headers)
        t.verticalHeader().hide()
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        t.horizontalHeader().setStretchLastSection(True)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.verticalHeader().setDefaultSectionSize(20)
        return t

    def _set_mode(self, categorized: bool):
        self.categorized = categorized
        self.btn_cat.setChecked(categorized)
        self.btn_alpha.setChecked(not categorized)
        self.refresh()

    # ------------------------------------------------------------ binding
    def set_document(self, doc: FormDocument | None, plugin) -> None:
        if self.doc is doc:
            return
        if self.doc is not None:
            for sig, slot in self._connections():
                try:
                    sig.disconnect(slot)
                except TypeError:
                    pass
        self.doc, self.plugin = doc, plugin
        if doc is not None:
            for sig, slot in self._connections():
                sig.connect(slot)
        self._fill_selector()
        self.refresh()

    def _connections(self):
        d = self.doc
        return [(d.selectionChanged, self._on_selection), (d.structureChanged, self._on_structure),
                (d.controlChanged, self._on_control_changed)]

    def _owner(self) -> Control | None:
        return self.doc.selected if self.doc else None

    def _on_structure(self):
        self._fill_selector()
        self.refresh()

    def _fill_selector(self) -> None:
        self._updating = True
        self.selector.clear()
        if self.doc:
            f = self.doc.form
            self.selector.addItem(f"{f.name}  (Form)", None)
            for c in f.controls:
                self.selector.addItem(f"{c.name}  ({c.type})", c.name)
            self._sync_selector()
        self._updating = False

    def _sync_selector(self) -> None:
        c = self._owner()
        idx = self.selector.findData(c.name if c else None)
        self.selector.setCurrentIndex(max(0, idx))

    def _on_selector(self, idx: int) -> None:
        if self._updating or not self.doc or idx < 0:
            return
        name = self.selector.itemData(idx)
        self.doc.select(self.doc.form.find(name) if name else None)

    def _on_selection(self, _c) -> None:
        self._updating = True
        self._sync_selector()
        self._updating = False
        self.refresh()

    def _on_control_changed(self, ctrl) -> None:
        if ctrl is self._owner():
            self._refresh_values()

    # ------------------------------------------------------------ tables
    def _defs(self):
        c = self._owner()
        defs = list(FORM_PROPS.values()) if c is None else CONTROL_TYPES[c.type].prop_defs()
        if self.categorized:
            return sorted(defs, key=lambda d: (CATEGORY_ORDER.index(d.category)
                                               if d.category in CATEGORY_ORDER else 99, d.name != "Name", d.name))
        return sorted(defs, key=lambda d: (d.name != "Name", d.name))

    def _props_dict(self) -> dict:
        c = self._owner()
        return c.props if c else self.doc.form.props

    def refresh(self) -> None:
        self._updating = True
        self.props.setRowCount(0)
        self.events.setRowCount(0)
        if not self.doc:
            self._updating = False
            return
        rows: list = []
        last_cat = None
        for d in self._defs():
            if self.categorized and d.category != last_cat:
                rows.append(d.category)
                last_cat = d.category
            rows.append(d)
        self.props.setRowCount(len(rows))
        bold = QFont()
        bold.setBold(True)
        for row, d in enumerate(rows):
            if isinstance(d, str):          # category header row
                item = QTableWidgetItem(d)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                item.setFont(bold)
                item.setBackground(QColor("#E4E8EE"))
                self.props.setItem(row, 0, item)
                filler = QTableWidgetItem("")
                filler.setFlags(Qt.ItemFlag.ItemIsEnabled)
                filler.setBackground(QColor("#E4E8EE"))
                self.props.setItem(row, 1, filler)
                continue
            name_item = QTableWidgetItem("(Name)" if d.name == "Name" else d.name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            name_item.setData(Qt.ItemDataRole.UserRole, d)
            self.props.setItem(row, 0, name_item)
        self._refresh_values()
        self._refresh_events()
        self._updating = False

    def _row_def(self, row: int):
        item = self.props.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _refresh_values(self) -> None:
        was = self._updating
        self._updating = True
        props = self._props_dict()
        for row in range(self.props.rowCount()):
            d = self._row_def(row)
            if d is None:
                continue
            value = props.get(d.name, d.default)
            w = self.props.cellWidget(row, 1)
            if d.kind == "bool":
                if w is None:
                    w = QComboBox()
                    w.addItems(["True", "False"])
                    w.currentTextChanged.connect(lambda t, n=d.name: self._set(n, t == "True"))
                    self.props.setCellWidget(row, 1, w)
                w.blockSignals(True)
                w.setCurrentText("True" if value else "False")
                w.blockSignals(False)
            elif d.kind == "enum":
                if w is None:
                    w = QComboBox()
                    w.addItems(list(d.choices))
                    w.currentTextChanged.connect(lambda t, n=d.name: self._set(n, t))
                    self.props.setCellWidget(row, 1, w)
                w.blockSignals(True)
                w.setCurrentText(str(value))
                w.blockSignals(False)
            elif d.kind == "font":
                if w is None:
                    w = QFontComboBox()
                    w.currentFontChanged.connect(lambda f, n=d.name: self._set(n, f.family()))
                    self.props.setCellWidget(row, 1, w)
                w.blockSignals(True)
                w.setCurrentFont(QFont(str(value or "Segoe UI")))
                w.blockSignals(False)
            elif d.kind == "menu":
                if w is None:
                    w = QPushButton("(Collection) ...")
                    w.setStyleSheet("text-align:left; padding-left:4px;")
                    w.clicked.connect(self._edit_menu)
                    self.props.setCellWidget(row, 1, w)
            elif d.kind == "file":
                if w is None:
                    w = QPushButton()
                    w.setStyleSheet("text-align:left; padding-left:4px;")
                    w.clicked.connect(lambda _=False, n=d.name: self._pick_file(n))
                    self.props.setCellWidget(row, 1, w)
                w.setText((value or "(none)") + "   ...")
            elif d.kind == "color":
                if w is None:
                    w = QPushButton()
                    w.setStyleSheet("text-align:left; padding-left:4px;")
                    w.clicked.connect(lambda _=False, n=d.name: self._pick_color(n))
                    self.props.setCellWidget(row, 1, w)
                w.setText(value or "(default)")
                w.setIcon(self._swatch(value))
            else:
                item = self.props.item(row, 1)
                if item is None:
                    item = QTableWidgetItem()
                    self.props.setItem(row, 1, item)
                item.setText(str(value))
        self._updating = was

    @staticmethod
    def _swatch(color: str):
        pm = QPixmap(14, 14)
        pm.fill(QColor(color) if color else QColor("#ECE9D8"))
        return QIcon(pm)

    def _refresh_events(self) -> None:
        if not self.plugin or not self.doc:
            return
        c = self._owner()
        events = self.plugin.events_for(c)
        code = self.code_provider(self.doc.form.name) or ""
        self.events.setRowCount(len(events))
        bold = QFont()
        bold.setBold(True)
        for row, ev in enumerate(events):
            label = f"{ev}.Click" if c is not None and c.type in ("MenuStrip", "ToolStrip") else ev
            handler = self.plugin.handler_for(self.doc.form, c, ev)
            exists = self.plugin.find_handler(code, handler) >= 0
            item = QTableWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, ev)
            hitem = QTableWidgetItem(handler if exists else "")
            if exists:
                item.setFont(bold)
                hitem.setFont(bold)
            self.events.setItem(row, 0, item)
            self.events.setItem(row, 1, hitem)

    # ------------------------------------------------------------ editing
    def _on_current_cell(self, row, *_):
        d = self._row_def(row) if row >= 0 else None
        if d is not None:
            self.help.setText(f"<b>{d.name}</b><br>{d.help or ''}")

    def _on_event_cell(self, row, *_):
        item = self.events.item(row, 0) if row >= 0 else None
        if item:
            ev = item.data(Qt.ItemDataRole.UserRole)
            self.help.setText(f"<b>{item.text()}</b><br>{EVENT_HELP.get(ev, 'Occurs when the item is clicked.')}"
                              "<br><i>Double-click to write the handler.</i>")

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating or item.column() != 1:
            return
        d = self._row_def(item.row())
        if d is None:
            return
        text = item.text()
        if d.kind == "int":
            try:
                value = int(text)
            except ValueError:
                self._refresh_values()
                return
        else:
            value = text
        if d.name == "Name" and not self._valid_name(value):
            self.help.setText(f"<span style='color:#b00'>'{value}' is not a valid unique name.</span>")
            self._refresh_values()
            return
        self._set(d.name, value)

    def _valid_name(self, value: str) -> bool:
        if not valid_identifier(value):
            return False
        owner = self._owner()
        current = owner.name if owner else self.doc.form.name
        if value.lower() == current.lower():
            return True
        return value.lower() not in self.doc.form.all_names()

    def _set(self, name: str, value) -> None:
        """Apply to the primary selection and, for shared properties,
        to every other selected control too (VB multi-select editing)."""
        if not self.doc or self._updating:
            return
        owner = self._owner()
        targets = [owner]
        if owner is not None and name != "Name":
            targets += [c for c in self.doc.selection if c is not owner and name in c.props]
        if len(targets) > 1:
            self.doc.checkpoint()
            for t in targets:
                self.doc.set_prop(t, name, value, record=False)
        else:
            self.doc.set_prop(owner, name, value)

    def _pick_color(self, name: str) -> None:
        current = self._props_dict().get(name) or "#ffffff"
        col = QColorDialog.getColor(QColor(current), self, f"Choose {name}")
        if col.isValid():
            self._set(name, col.name())
            self._refresh_values()

    def _pick_file(self, name: str) -> None:
        root = self.doc.path.parent
        f, _ = QFileDialog.getOpenFileName(self, f"Choose {name}", str(root),
                                           "Images (*.png *.gif *.ico *.jpg *.bmp);;All files (*)")
        if not f:
            return
        src = Path(f)
        try:
            rel = src.resolve().relative_to(root.resolve())
        except ValueError:          # copy outside files into the project's Resources folder
            res = root / "Resources"
            res.mkdir(exist_ok=True)
            dst = res / src.name
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
            rel = dst.relative_to(root)
        self._set(name, rel.as_posix())
        self._refresh_values()

    def _edit_menu(self):
        from .menu_editor import edit_menu
        c = self._owner()
        if c is None or c.type != "MenuStrip":
            return
        taken = {x.name for x in self.doc.form.controls} | {self.doc.form.name}
        items = edit_menu(c.props.get("Items", []), taken, self)
        if items is not None:
            self.doc.set_prop(c, "Items", items)

    def _on_event_dclick(self, row: int, _col: int) -> None:
        ev = self.events.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.doc.eventRequested.emit(self._owner(), ev)
        self._refresh_events()
