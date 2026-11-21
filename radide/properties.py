"""VB-style Properties window: object selector, Categorized / Alphabetical
property grid, Events tab (handlers that exist are shown in bold)."""
from __future__ import annotations

import keyword
import shutil
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (QAbstractItemView, QColorDialog, QComboBox, QFileDialog,
                             QFontComboBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                             QPushButton,
                             QTableWidget, QTableWidgetItem, QTabWidget, QToolButton,
                             QVBoxLayout, QWidget)

from .controls import (ANCHOR_EDGES, CONTROL_TYPES, EVENT_HELP, MENU_TYPES, format_anchor,
                       menu_names, parse_anchor)
from .document import FormDocument
from .mobile.controls import form_prop_defs
from .mobile.material_icons import icon as material_icon
from .model import Control

CATEGORY_ORDER = ["Appearance", "Behavior", "Data", "Design", "Layout", "Misc"]
CATEGORY_BACK = "#E4E8EE"     # category rows (Tools > Options dark theme changes it)


_GENERIC_HELP = {"color": "A colour: click the value to pick one ((default) = the system colour).",
                 "bool": "True or False.", "int": "A whole number (pixels for positions and sizes).",
                 "enum": "Choose one of the values in the list.", "file": "A file: click ... to choose it.",
                 "font": "The font of the text.", "list": "Items separated by ;",
                 "anchor": "The edges of the parent this control keeps its distance to when the form is resized.",
                 "menu": "Click ... to edit the items.", "str": "Text."}


def valid_identifier(s: str) -> bool:
    return s.isidentifier() and not keyword.iskeyword(s)


class AnchorEditor(QFrame):
    """VS-style Anchor editor: a popup with a box and four bars (Top/Bottom/Left/Right)
    that toggle; *changed(str)* is called with the new value ("Top, Left", ...)."""

    def __init__(self, value: str, changed, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setFrameShape(QFrame.Shape.Box)
        self.setStyleSheet("AnchorEditor { background: palette(base); }")
        self.changed = changed
        self.edges = parse_anchor(value)
        grid = QGridLayout(self)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setSpacing(2)
        self.buttons: dict[str, QToolButton] = {}
        spots = {"Top": (0, 1, 22, 34), "Bottom": (2, 1, 22, 34), "Left": (1, 0, 34, 22), "Right": (1, 2, 34, 22)}
        for edge in ANCHOR_EDGES:
            row, col, w, h = spots[edge]
            b = QToolButton(self)
            b.setCheckable(True)
            b.setChecked(edge in self.edges)
            b.setFixedSize(w, h)
            b.setToolTip(edge)
            b.setObjectName(f"anchor{edge}")
            b.setStyleSheet("QToolButton { background: palette(button); border:1px solid palette(mid); }"
                            "QToolButton:checked { background:#3A6FC4; border:1px solid #1E4A90; }")
            b.toggled.connect(lambda on, e=edge: self._toggle(e, on))
            grid.addWidget(b, row, col, Qt.AlignmentFlag.AlignCenter)
            self.buttons[edge] = b
        box = QLabel(self)
        box.setFixedSize(34, 34)
        box.setStyleSheet("background: palette(alternate-base); border:1px solid palette(mid);")
        grid.addWidget(box, 1, 1)

    def _toggle(self, edge: str, on: bool) -> None:
        if on:
            self.edges.add(edge)
        else:
            self.edges.discard(edge)
        self.changed(format_anchor(self.edges))


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
        self.props.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.props.customContextMenuRequested.connect(self._props_menu)
        self.tabs.addTab(self.props, "Properties")
        self.tabs.addTab(self.events, "Events")
        self.tabs.currentChanged.connect(lambda _i: self._refresh_events())
        self.help = QLabel()
        self.help.setWordWrap(True)
        self.help.setMinimumHeight(54)
        self.help.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.help.setProperty("radRole", "help")

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
            if doc is None:
                self.help.setText("")     # e.g. a game scene tab after a form: no stale description
            return
        if self.doc is not None:
            for sig, slot in self._connections():
                try:
                    sig.disconnect(slot)
                except TypeError:
                    pass
        self.doc, self.plugin = doc, plugin
        try:        # the toolbox shows the control names of the form's toolkit (e.g. WinForms)
            from .toolbox import TOOL_STATE
            TOOL_STATE.set_profile(getattr(plugin, "designer_profile", None) if doc is not None else None)
            # component packages without a runtime for the form's language are greyed (components/targets.py)
            TOOL_STATE.set_target(getattr(plugin, "id", None) if doc is not None else None)
        except Exception:  # noqa: BLE001
            pass
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
        defs = form_prop_defs(self.doc.form, self.plugin) if c is None else CONTROL_TYPES[c.type].prop_defs()
        if c is None:          # Localizable / Language / RightToLeft / RightToLeftLayout (features/localization.py)
            from .features.localization import form_defs
            defs = list(defs) + [d for d in form_defs(self.doc.form) if d.name not in {x.name for x in defs}]
        else:
            # component packages: "browsable": false hides a property; several selected controls show only
            # the properties they all have (VS multi-select), never (Name)
            defs = [d for d in defs if not (d.meta and d.meta.get("browsable") is False)]
            others = [x for x in getattr(self.doc, "selection", []) or [] if x is not c and x.type in CONTROL_TYPES]
            if others:
                common = None
                for o in others:
                    names = {d.name for d in CONTROL_TYPES[o.type].prop_defs()}
                    common = names if common is None else common & names
                defs = [d for d in defs if d.name in (common or set()) and d.name != "Name"]
        if self.categorized:
            return sorted(defs, key=lambda d: (CATEGORY_ORDER.index(d.category)
                                               if d.category in CATEGORY_ORDER else 99, d.name != "Name", d.name))
        return sorted(defs, key=lambda d: (d.name != "Name", d.name))

    def _props_dict(self) -> dict:
        c = self._owner()
        props = c.props if c else self.doc.form.props
        shown = getattr(self.doc, "display_props", None)     # a form Language being edited (localization)
        return shown(c, props) if shown is not None else props

    def _defaults(self) -> dict:
        """Default values of the selected object (a new control of its type) - bold / Reset compare to them."""
        c = self._owner()
        if c is None or c.type not in CONTROL_TYPES:
            return {}
        try:
            d = CONTROL_TYPES[c.type].default_props(c.name)
        except Exception:  # noqa: BLE001
            return {}
        if CONTROL_TYPES[c.type].has_text:
            d.pop("Text", None)            # Text starts as the control name: never shown as changed
        return d

    def reset_property(self, name: str) -> bool:
        """Context menu > Reset: the property gets its default value again."""
        d = next((x for x in self._defs() if x.name == name), None)
        if d is None or name == "Name" or not self.doc:
            return False
        value = self._defaults().get(name, d.default)
        self._set(name, value)
        self._refresh_values()
        return True

    def _props_menu(self, pos) -> None:
        from PyQt6.QtWidgets import QMenu
        row = self.props.rowAt(pos.y())
        d = self._row_def(row) if row >= 0 else None
        if d is None or d.name == "Name":
            return
        m = QMenu(self)
        value = self._props_dict().get(d.name, d.default)
        a = m.addAction("&Reset", lambda n=d.name: self.reset_property(n))
        a.setEnabled(value != self._defaults().get(d.name, d.default))
        m.addAction("&Description", lambda: self._on_current_cell(row))
        m.exec(self.props.viewport().mapToGlobal(pos))

    def refresh(self) -> None:
        self._updating = True
        self.props.setRowCount(0)
        self.events.setRowCount(0)
        if not self.doc:
            self._updating = False
            self.help.setText("")         # no stale description (game scene / web page tabs have no form)
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
                item.setBackground(QColor(CATEGORY_BACK))
                self.props.setItem(row, 0, item)
                filler = QTableWidgetItem("")
                filler.setFlags(Qt.ItemFlag.ItemIsEnabled)
                filler.setBackground(QColor(CATEGORY_BACK))
                self.props.setItem(row, 1, filler)
                continue
            label_of = getattr(self.plugin, "property_label", None)   # e.g. .NET names (WinForms)
            label = label_of(d.name, self._owner()) if callable(label_of) else None
            name_item = QTableWidgetItem("(Name)" if d.name == "Name" else (
                label or (d.meta or {}).get("displayName") or d.name))
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            name_item.setData(Qt.ItemDataRole.UserRole, d)
            self.props.setItem(row, 0, name_item)
        self._refresh_values()
        self._refresh_events()
        self._updating = False
        self._describe_owner()

    def _describe_owner(self) -> None:
        """The description box shows the selected object until a property row is picked."""
        if not self.doc:
            self.help.setText("")
            return
        c = self._owner()
        if c is None:
            name, kind, desc = self.doc.form.name, "Form", "A window of the program. Select a property " \
                                                          "to see its description; Events lists its handlers."
        else:
            name, kind = c.name, c.type
            type_of = getattr(self.plugin, "type_label", None)       # e.g. System.Windows.Forms.StatusStrip
            if callable(type_of):
                kind = type_of(c) or kind
            desc = CONTROL_TYPES[c.type].description or "Select a property to see its description."
        self.help.setText(f"<b>{name}</b> ({kind})<br>{desc}")

    def _row_def(self, row: int):
        item = self.props.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _refresh_values(self) -> None:
        was = self._updating
        self._updating = True
        props = self._props_dict()
        defaults = self._defaults()
        from .components import propeditors as _peng       # schema-driven editors (radide/components)
        for row in range(self.props.rowCount()):
            d = self._row_def(row)
            if d is None:
                continue
            value = props.get(d.name, d.default)
            w = self.props.cellWidget(row, 1)
            name_item = self.props.item(row, 0)
            if name_item is not None:          # VS: values that differ from the default are bold
                f = name_item.font()
                changed = d.name != "Name" and value != defaults.get(d.name, d.default)
                if f.bold() != changed:
                    f.setBold(changed)
                    name_item.setFont(f)
            if _peng.handles(self, d):
                _peng.cell_widget(self, row, d, value)
            elif d.kind == "bool":
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
                    if d.name == "Icon":            # mobile Fab / MIcon: show the Material icons
                        for i in range(w.count()):
                            w.setItemIcon(i, material_icon(w.itemText(i), 16))
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
            elif d.kind == "anchor":
                if w is None:
                    w = QPushButton()
                    w.setStyleSheet("text-align:left; padding-left:4px;")
                    w.clicked.connect(lambda _=False, n=d.name, b=w: self._edit_anchor(n, b))
                    self.props.setCellWidget(row, 1, w)
                w.setText(format_anchor(parse_anchor(value)) + "   \u25be")
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
            elif d.kind == "dbref":                 # data binding (radide/databinding_sql.py)
                from .databinding_sql import prop_choices
                if w is None:
                    w = QComboBox()
                    w.setEditable(True)
                    w.lineEdit().editingFinished.connect(
                        lambda n=d.name, cb=w: self._set(n, cb.currentText().strip()))
                    w.activated.connect(lambda _i, n=d.name, cb=w: self._set(n, cb.currentText().strip()))
                    self.props.setCellWidget(row, 1, w)
                w.blockSignals(True)
                w.clear()
                owner = self._owner()
                w.addItems(prop_choices(self.doc.form, owner, d.name) if owner is not None else [""])
                w.setCurrentText(str(value or ""))
                w.blockSignals(False)
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
            from .components.proptypes import GENERIC_HELP
            self.help.setText(f"<b>{d.name}</b><br>{d.help or _GENERIC_HELP.get(d.kind) or GENERIC_HELP.get(d.kind, '')}")

    def _on_event_cell(self, row, *_):
        item = self.events.item(row, 0) if row >= 0 else None
        if item:
            ev = item.data(Qt.ItemDataRole.UserRole)
            owner = self._owner()
            from .components import event_help          # a component package's own event description
            desc = (event_help(owner.type, ev) if owner is not None else "") or \
                EVENT_HELP.get(ev, 'Occurs when the item is clicked.')
            self.help.setText(f"<b>{item.text()}</b><br>{desc}"
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
            lo, hi = (d.meta or {}).get("min"), (d.meta or {}).get("max")     # component package limits
            if (lo is not None and value < lo) or (hi is not None and value > hi):
                self.help.setText(f"<span style='color:#b00'>{d.name}: use a value from {lo} to {hi}.</span>")
                self._refresh_values()
                return
        elif d.kind in ("float", "padding"):       # component package kinds typed in the cell
            from .components.proptypes import coerce
            try:
                value = coerce(d.kind, text)
            except ValueError as e:
                self.help.setText(f"<span style='color:#b00'>{d.name}: {e}</span>")
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
                                           "Reports (*.rpt.json);;All files (*)" if name == "ReportFile" else
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

    def _edit_anchor(self, name: str, button: QPushButton) -> AnchorEditor:
        current = self._props_dict().get(name, "Top, Left")
        pop = AnchorEditor(current, lambda v, n=name: (self._set(n, v), self._refresh_values()), self)
        pop.adjustSize()
        pop.move(button.mapToGlobal(button.rect().bottomLeft()))
        pop.show()
        self._anchor_popup = pop
        return pop

    def _edit_menu(self):
        from .menu_editor import edit_menu
        c = self._owner()
        if c is None or c.type not in MENU_TYPES:
            return
        taken = {x.name for x in self.doc.form.controls} | {self.doc.form.name}
        for other in self.doc.form.controls:
            if other.type in MENU_TYPES and other is not c:
                taken |= set(menu_names(other.props.get("Items", [])))
        items = edit_menu(c.props.get("Items", []), taken, self, flat=c.type == "ToolStrip")
        if items is not None:
            self.doc.set_prop(c, "Items", items)

    def _on_event_dclick(self, row: int, _col: int) -> None:
        ev = self.events.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.doc.eventRequested.emit(self._owner(), ev)
        self._refresh_events()
