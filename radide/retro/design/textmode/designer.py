"""The Text-Mode Designer (Qt): a VB-style form designer for DOS text-mode screens (.tform).

Toolbox (Pointer, Window, Frame, Label, Button, TextBox, CheckBox, Option, ListBox, MenuBar, StatusBar,
ProgressBar, Separator) | canvas (80x25 / 80x43 / 80x50 cells, CP437, drawn like the running program) |
Properties window (object box, properties, events). Draw a control by dragging with a tool, move / resize
with the mouse or the arrow keys (Shift = resize), double-click a control (or an event) to write its code,
Ctrl+Z / Ctrl+Y undo / redo, Ctrl+C / Ctrl+V copy / paste, Del deletes. Moving a Window or Frame moves the
controls inside it.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox,
                             QSplitter, QTableWidget, QTableWidgetItem, QToolBar, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

from .canvas import CellCanvas
from .cp437 import COLOR_NAMES, to_unicode
from .glyphs import rgb
from .model import (COMMON, EVENTS, FOCUSABLE, PROP_TITLES, PROPS, SCREEN_PROPS, SIZES, TYPE_DESCRIPTIONS, TYPES,
                    TControl, TScreen, new_screen)
from .render import designer_render, draw_dropdown, dropdown_geometry, menu_layout

TOOL_GLYPHS = {"Pointer": 0x10, "Window": 0xC9, "Frame": 0xDA, "Label": ord("A"), "Button": 0xDB,
               "TextBox": 0x5F, "CheckBox": 0xFB, "Option": 0x07, "ListBox": 0xF0, "MenuBar": 0x16,
               "StatusBar": 0xDC, "ProgressBar": 0xB1, "Separator": 0xC4}
CONTAINER_BACK = ("Label", "CheckBox", "Option", "Separator", "Frame")
MAX_UNDO = 200


def tool_icon(name: str) -> QIcon:
    from .glyphs import char_icon
    return char_icon(TOOL_GLYPHS.get(name, 0x3F), 14, 1)


def color_icon(i: int) -> QIcon:
    pm = QPixmap(14, 14)
    pm.fill(rgb(i))
    return QIcon(pm)


# ====================================================================== canvas
class DesignCanvas(CellCanvas):
    selectionChanged = pyqtSignal()
    changed = pyqtSignal(str)                 # description (for undo) - emitted BEFORE the change is applied
    applied = pyqtSignal()                    # after a change
    codeRequested = pyqtSignal(str, str)      # control name, event
    toolDone = pyqtSignal()

    HANDLE = 6

    def __init__(self, screen: TScreen, parent=None):
        super().__init__(designer_render(screen), parent)
        self.screen = screen
        self.selected: list[TControl] = []
        self.tool = "Pointer"
        self.preview_menu = -1
        self._drag = None           # ("move", start cell, originals) | ("resize", handle, original) | ("new", start)
        self._band: QRect | None = None
        self.show_grid = False

    # ------------------------------------------------------------ model -> view
    def rerender(self) -> None:
        buf = designer_render(self.screen)
        bar = self.selected[0] if len(self.selected) == 1 and self.selected[0].type == "MenuBar" else None
        if bar is not None and self.preview_menu >= 0:
            draw_dropdown(buf, bar, self.preview_menu)
        self.set_buffer(buf)

    def select(self, controls: list[TControl]) -> None:
        self.selected = [c for c in controls if c in self.screen.controls]
        self.preview_menu = -1
        self.rerender()
        self.selectionChanged.emit()

    # ------------------------------------------------------------ overlay
    def handles(self, c: TControl) -> dict[str, QRect]:
        r = self.cell_rect(c.x, c.y, c.w, c.h)
        s = self.HANDLE
        pts = {"tl": r.topLeft(), "t": QPoint(r.center().x(), r.top()), "tr": r.topRight(),
               "l": QPoint(r.left(), r.center().y()), "r": QPoint(r.right(), r.center().y()),
               "bl": r.bottomLeft(), "b": QPoint(r.center().x(), r.bottom()), "br": r.bottomRight()}
        if c.h == 1:
            pts = {k: v for k, v in pts.items() if k in ("l", "r")}
        return {k: QRect(v.x() - s // 2, v.y() - s // 2, s, s) for k, v in pts.items()}

    def paint_overlay(self, p: QPainter) -> None:
        for c in self.screen.controls:
            if not c.get("visible", True):
                r = self.cell_rect(c.x, c.y, c.w, c.h)
                p.setPen(QPen(QColor(255, 255, 0, 120), 1, Qt.PenStyle.DotLine))
                p.drawRect(r.adjusted(0, 0, -1, -1))
        for c in self.selected:
            r = self.cell_rect(c.x, c.y, c.w, c.h)
            p.setPen(QPen(QColor(255, 255, 255), 1, Qt.PenStyle.DashLine))
            p.drawRect(r.adjusted(0, 0, -1, -1))
            if len(self.selected) == 1:
                p.setPen(QPen(QColor(0, 0, 0)))
                for h in self.handles(c).values():
                    p.fillRect(h, QColor(255, 255, 255))
                    p.drawRect(h)
        if self._band is not None:
            p.setPen(QPen(QColor(255, 255, 0), 1, Qt.PenStyle.DashLine))
            p.drawRect(self._band.normalized())

    # ------------------------------------------------------------ mouse
    def _handle_at(self, pos: QPoint):
        if len(self.selected) != 1:
            return None
        for k, r in self.handles(self.selected[0]).items():
            if r.adjusted(-2, -2, 2, 2).contains(pos):
                return k
        return None

    def mousePressEvent(self, e) -> None:
        self.setFocus()
        if e.button() != Qt.MouseButton.LeftButton:
            return
        pos = e.position().toPoint()
        cx, cy = self.cell_at(pos)
        if self.tool != "Pointer":
            self._drag = ("new", (cx, cy))
            self._band = QRect(pos, pos)
            return
        h = self._handle_at(pos)
        if h:
            c = self.selected[0]
            self._drag = ("resize", h, (c.x, c.y, c.w, c.h), (cx, cy), False)
            return
        # menu bar preview: click on a title opens its drop-down in the designer
        if len(self.selected) == 1 and self.selected[0].type == "MenuBar" and cy == self.selected[0].y:
            for i, (tx, t, _m, _k) in enumerate(menu_layout(self.selected[0])):
                if tx <= cx < tx + len(t) + 2:
                    self.preview_menu = -1 if self.preview_menu == i else i
                    self.rerender()
                    return
        hit = self.screen.at(cx, cy)
        mods = e.modifiers()
        if hit is None:
            if not mods & Qt.KeyboardModifier.ShiftModifier:
                self.select([])
            self._drag = ("band", pos)
            self._band = QRect(pos, pos)
            return
        if mods & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier):
            sel = list(self.selected)
            if hit in sel:
                sel.remove(hit)
            else:
                sel.append(hit)
            self.select(sel)
            return
        if hit not in self.selected:
            self.select([hit])
        moving = list(self.selected)
        for c in list(moving):
            if c.type in ("Window", "Frame"):
                moving += [o for o in self.screen.contained(c) if o not in moving]
        self._drag = ("move", (cx, cy), [(c, c.x, c.y) for c in moving], False)

    def mouseMoveEvent(self, e) -> None:
        pos = e.position().toPoint()
        if self._drag is None:
            h = self._handle_at(pos)
            cur = {"l": Qt.CursorShape.SizeHorCursor, "r": Qt.CursorShape.SizeHorCursor,
                   "t": Qt.CursorShape.SizeVerCursor, "b": Qt.CursorShape.SizeVerCursor,
                   "tl": Qt.CursorShape.SizeFDiagCursor, "br": Qt.CursorShape.SizeFDiagCursor,
                   "tr": Qt.CursorShape.SizeBDiagCursor, "bl": Qt.CursorShape.SizeBDiagCursor}.get(h or "")
            self.setCursor(cur if cur is not None else (Qt.CursorShape.CrossCursor if self.tool != "Pointer"
                                                         else Qt.CursorShape.ArrowCursor))
            return
        cx, cy = self.cell_at(pos)
        kind = self._drag[0]
        if kind in ("new", "band"):
            self._band = QRect(self._band.topLeft(), pos)
            self.update()
        elif kind == "move":
            _k, (sx, sy), orig, started = self._drag
            dx, dy = cx - sx, cy - sy
            if (dx or dy) and not started:
                self.changed.emit("Move")
                self._drag = ("move", (sx, sy), orig, True)
            if dx or dy or started:
                minx = min(ox for _c, ox, _oy in orig)
                miny = min(oy for _c, _ox, oy in orig)
                maxx = max(ox + c.w for c, ox, _oy in orig)
                maxy = max(oy + c.h for c, _ox, oy in orig)
                dx = max(-minx, min(dx, self.screen.cols - maxx))
                dy = max(-miny, min(dy, self.screen.rows - maxy))
                for c, ox, oy in orig:
                    c.x, c.y = ox + dx, oy + dy
                self.rerender()
                self.applied.emit()
        elif kind == "resize":
            _k, h, (ox, oy, ow, oh), (sx, sy), started = self._drag
            dx, dy = cx - sx, cy - sy
            if (dx or dy) and not started:
                self.changed.emit("Resize")
                self._drag = ("resize", h, (ox, oy, ow, oh), (sx, sy), True)
            c = self.selected[0]
            x, y, w, hh = ox, oy, ow, oh
            if "l" in h:
                x, w = ox + dx, ow - dx
            if "r" in h:
                w = ow + dx
            if "t" in h:
                y, hh = oy + dy, oh - dy
            if "b" in h:
                hh = oh + dy
            if w >= 1 and hh >= 1:
                c.x, c.y, c.w, c.h = x, y, w, hh
                self.screen.clamp(c)
                self.rerender()
                self.applied.emit()

    def mouseReleaseEvent(self, e) -> None:
        if self._drag is None:
            return
        kind = self._drag[0]
        if kind == "new":
            (sx, sy) = self._drag[1]
            ex, ey = self.cell_at(e.position().toPoint())
            x, y = min(sx, ex), min(sy, ey)
            w, h = abs(ex - sx) + 1, abs(ey - sy) + 1
            small = w <= 1 and h <= 1
            self.add_control(self.tool, x, y, None if small else w, None if small else h)
            self.toolDone.emit()
        elif kind == "band":
            r = self._band.normalized()
            x1, y1 = self.cell_at(r.topLeft())
            x2, y2 = self.cell_at(r.bottomRight())
            if r.width() > 3 or r.height() > 3:
                inside = [c for c in self.screen.controls if c.x >= x1 and c.y >= y1 and c.x + c.w - 1 <= x2 and
                          c.y + c.h - 1 <= y2]
                self.select(inside)
        self._drag = None
        self._band = None
        self.update()

    def mouseDoubleClickEvent(self, e) -> None:
        cx, cy = self.cell_at(e.position().toPoint())
        hit = self.screen.at(cx, cy)
        if hit is None:
            self.codeRequested.emit("", "Load")
            return
        if hit.type == "MenuBar" and self.preview_menu >= 0:
            x, y, w, h, _tw = dropdown_geometry(hit, self.preview_menu)
            if x < cx < x + w - 1 and y < cy < y + h - 1:
                items = (hit.get("menus") or [])[self.preview_menu].get("items") or []
                it = items[cy - y - 1]
                if it.get("name"):
                    self.codeRequested.emit(str(it["name"]), "Click")
                return
        evs = EVENTS.get(hit.type, ())
        if evs:
            self.codeRequested.emit(hit.name, evs[0])

    # ------------------------------------------------------------ editing
    def add_control(self, ctype: str, x: int, y: int, w: int | None = None, h: int | None = None) -> TControl:
        self.changed.emit(f"Add {ctype}")
        c = self.screen.add(ctype, x, y, w, h)
        box = self.screen.container_of(c)
        if box is not None and ctype in CONTAINER_BACK:
            c.props["back"] = int(box.get("back"))
            if ctype in ("Separator", "Frame"):
                c.props["fore"] = int(box.get("fore"))
        if ctype == "MenuBar":
            c.x, c.y, c.w = 0, 0, self.screen.cols
        if ctype == "StatusBar":
            c.x, c.w = 0, self.screen.cols
            if h is None:
                c.y = self.screen.rows - 1
        self.screen.clamp(c)
        self.select([c])
        self.applied.emit()
        return c

    def delete_selected(self) -> None:
        if not self.selected:
            return
        self.changed.emit("Delete")
        for c in self.selected:
            if c in self.screen.controls:
                self.screen.remove(c)
        self.select([])
        self.applied.emit()

    def nudge(self, dx: int, dy: int, resize: bool) -> None:
        if not self.selected:
            return
        self.changed.emit("Resize" if resize else "Move")
        moving = list(self.selected)
        if not resize:
            for c in list(moving):
                if c.type in ("Window", "Frame"):
                    moving += [o for o in self.screen.contained(c) if o not in moving]
        for c in moving:
            if resize:
                c.w, c.h = max(1, c.w + dx), max(1, c.h + dy)
            else:
                c.x, c.y = c.x + dx, c.y + dy
            self.screen.clamp(c)
        self.rerender()
        self.applied.emit()

    def copy_selected(self) -> None:
        if self.selected:
            data = {"format": "radide-tform-clip", "controls": [c.to_dict() for c in self.selected]}
            QApplication.clipboard().setText(json.dumps(data))

    def paste(self) -> None:
        try:
            data = json.loads(QApplication.clipboard().text())
        except (ValueError, TypeError):
            return
        if not isinstance(data, dict) or data.get("format") != "radide-tform-clip":
            return
        self.changed.emit("Paste")
        new = []
        for d in data.get("controls") or []:
            c = TControl.from_dict(d)
            if self.screen.find(c.name) is not None:
                c.name = self.screen.unique_name(c.type)
            c.x, c.y = c.x + 1, c.y + 1
            c.props.pop("events", None)
            self.screen.controls.append(c)
            self.screen.clamp(c)
            new.append(c)
        self.select(new)
        self.applied.emit()

    def keyPressEvent(self, e) -> None:
        k = e.key()
        shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        moves = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}
        if k in moves:
            self.nudge(*moves[k], resize=shift)
        elif k == Qt.Key.Key_Delete:
            self.delete_selected()
        elif k == Qt.Key.Key_Escape:
            self.select([])
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and len(self.selected) == 1:
            c = self.selected[0]
            if EVENTS.get(c.type):
                self.codeRequested.emit(c.name, EVENTS[c.type][0])
        else:
            super().keyPressEvent(e)


# ====================================================================== dialogs
class ItemsDialog(QDialog):
    """List box items: one item per line (like VB's List property)."""

    def __init__(self, items: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("List Items")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("One item per line:"))
        self.edit = QPlainTextEdit("\n".join(items))
        lay.addWidget(self.edit)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.resize(320, 300)

    def items(self) -> list[str]:
        return [ln for ln in self.edit.toPlainText().splitlines()]


class MenuEditorDialog(QDialog):
    """VB-style Menu Editor: menus and their items (caption with &hotkey, name, shortcut text, separators)."""

    def __init__(self, menus: list[dict], used_names: set[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Menu Editor")
        self.used = used_names
        lay = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Caption", "Name", "Shortcut"])
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked |
                                  QAbstractItemView.EditTrigger.EditKeyPressed |
                                  QAbstractItemView.EditTrigger.SelectedClicked)
        self.tree.setProperty("i18n_skip_items", True)
        lay.addWidget(self.tree)
        for m in menus:
            top = self._item(None, m.get("text", "&Menu"), "", "")
            for it in m.get("items") or []:
                self._item(top, it.get("text", ""), it.get("name", ""), it.get("shortcut", ""))
            top.setExpanded(True)
        row = QHBoxLayout()
        for text, fn in (("Add &Menu", self.add_menu), ("Add &Item", self.add_item),
                         ("Add &Separator", self.add_sep), ("&Delete", self.delete), ("Move &Up", self.up),
                         ("Move Do&wn", self.down)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)
        lay.addWidget(QLabel("& marks the hotkey (Alt+letter on the menu bar, the letter in a menu). "
                             "Name = the Click handler (mnuOpen -> mnuOpen_Click). Caption \"-\" = separator."))
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.resize(560, 420)

    def _item(self, parent, text: str, name: str, shortcut: str) -> QTreeWidgetItem:
        it = QTreeWidgetItem([text, name, shortcut])
        it.setFlags(it.flags() | Qt.ItemFlag.ItemIsEditable)
        if parent is None:
            self.tree.addTopLevelItem(it)
        else:
            parent.addChild(it)
        return it

    def _top(self) -> QTreeWidgetItem | None:
        it = self.tree.currentItem()
        if it is None:
            return self.tree.topLevelItem(self.tree.topLevelItemCount() - 1)
        return it if it.parent() is None else it.parent()

    def _new_name(self, text: str) -> str:
        base = "mnu" + "".join(ch for ch in text.replace("&", "").title() if ch.isalnum())[:20] or "mnuItem"
        names = self.used | {self.tree.topLevelItem(i).child(j).text(1).lower()
                             for i in range(self.tree.topLevelItemCount())
                             for j in range(self.tree.topLevelItem(i).childCount())}
        n, i = base, 2
        while n.lower() in names:
            n = f"{base}{i}"
            i += 1
        return n

    def add_menu(self) -> None:
        it = self._item(None, "&Menu", "", "")
        self.tree.setCurrentItem(it)
        self.tree.editItem(it, 0)

    def add_item(self) -> None:
        top = self._top() or self._item(None, "&File", "", "")
        it = self._item(top, "&Item", self._new_name("Item"), "")
        top.setExpanded(True)
        self.tree.setCurrentItem(it)
        self.tree.editItem(it, 0)

    def add_sep(self) -> None:
        top = self._top()
        if top is not None:
            self._item(top, "-", "", "")
            top.setExpanded(True)

    def delete(self) -> None:
        it = self.tree.currentItem()
        if it is None:
            return
        (it.parent() or self.tree.invisibleRootItem()).removeChild(it)

    def _move(self, d: int) -> None:
        it = self.tree.currentItem()
        if it is None:
            return
        par = it.parent() or self.tree.invisibleRootItem()
        i = par.indexOfChild(it)
        j = i + d
        if 0 <= j < par.childCount():
            exp = it.isExpanded()
            par.takeChild(i)
            par.insertChild(j, it)
            it.setExpanded(exp)
            self.tree.setCurrentItem(it)

    def up(self) -> None:
        self._move(-1)

    def down(self) -> None:
        self._move(1)

    def menus(self) -> list[dict]:
        out = []
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            items = []
            for j in range(top.childCount()):
                c = top.child(j)
                if c.text(0).strip() == "-":
                    items.append({"text": "-"})
                    continue
                d = {"text": c.text(0), "name": c.text(1).strip() or self._new_name(c.text(0))}
                if c.text(2).strip():
                    d["shortcut"] = c.text(2).strip()
                items.append(d)
            out.append({"text": top.text(0), "items": items})
        return out


class CharPickerDialog(QDialog):
    """The 256 CP437 characters."""

    def __init__(self, current: int = 0xB0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Character")
        self.value = current
        lay = QVBoxLayout(self)
        from .ansieditor import CharPalette
        self.pal = CharPalette(self)
        self.pal.set_char(current)
        self.pal.picked.connect(self._pick)
        lay.addWidget(self.pal)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _pick(self, code: int) -> None:
        self.value = code


# ====================================================================== properties
class PropertyGrid(QWidget):
    """Object box + property table + events (VB Properties window)."""
    edited = pyqtSignal(object, str, object)     # control (None = screen), key, value
    selectRequested = pyqtSignal(object)
    eventRequested = pyqtSignal(str, str)        # control name ("" = screen), event

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.objects = QComboBox()
        self.objects.setProperty("i18n_skip", True)
        self.objects.activated.connect(self._object_picked)
        lay.addWidget(self.objects)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Property", "Value"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setProperty("i18n_skip_items", True)
        lay.addWidget(self.table, 3)
        lay.addWidget(QLabel("Events (double-click to write the code):"))
        self.events = QListWidget()
        self.events.setProperty("i18n_skip_items", True)
        self.events.itemDoubleClicked.connect(self._event_dclick)
        lay.addWidget(self.events, 1)
        self.help = QLabel("")
        self.help.setWordWrap(True)
        lay.addWidget(self.help)
        self.screen: TScreen | None = None
        self.target: TControl | None = None
        self._loading = False

    def bind(self, screen: TScreen, selected: list[TControl]) -> None:
        self.screen = screen
        self.target = selected[0] if len(selected) == 1 else None
        self._loading = True
        self.objects.clear()
        self.objects.addItem(f"{screen.name} (Screen)", None)
        for c in screen.controls:
            self.objects.addItem(f"{c.name} ({c.type})", c.name)
        if self.target is not None:
            i = self.objects.findData(self.target.name)
            self.objects.setCurrentIndex(max(0, i))
        self._loading = False
        self._fill()

    def _object_picked(self, i: int) -> None:
        if self._loading or self.screen is None:
            return
        name = self.objects.itemData(i)
        self.selectRequested.emit(self.screen.find(name) if name else None)

    def _rows(self) -> list[tuple[str, str]]:
        if self.target is None:
            return list(SCREEN_PROPS)
        return list(COMMON) + list(PROPS.get(self.target.type, []))

    def _value(self, key: str):
        if self.target is None:
            return self.screen.get(key)
        return self.target.get(key)

    def _fill(self) -> None:
        self.table.setRowCount(0)
        if self.screen is None:
            return
        rows = self._rows()
        self.table.setRowCount(len(rows))
        for r, (key, kind) in enumerate(rows):
            it = QTableWidgetItem(PROP_TITLES.get(key, key))
            it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            it.setToolTip(key)
            self.table.setItem(r, 0, it)
            self.table.setCellWidget(r, 1, self._editor(key, kind, self._value(key)))
        self.events.clear()
        if self.target is None:
            evs, owner = EVENTS["Screen"], self.screen.name
            have = list(self.screen.get("events") or [])
        else:
            evs, owner = EVENTS.get(self.target.type, ()), self.target.name
            have = self.target.events()
            if self.target.type == "MenuBar":
                for it in self.target.menu_items():
                    if it.get("name"):
                        li = QListWidgetItem(f"{it['name']}_Click  ({it.get('text', '').replace('&', '')})")
                        li.setData(Qt.ItemDataRole.UserRole, (str(it["name"]), "Click"))
                        self.events.addItem(li)
        for ev in evs:
            mark = "  [code]" if ev in have else ""
            li = QListWidgetItem(f"{owner}_{ev}{mark}")
            li.setData(Qt.ItemDataRole.UserRole, ("" if self.target is None else owner, ev))
            self.events.addItem(li)
        t = self.target.type if self.target is not None else ""
        self.help.setText(TYPE_DESCRIPTIONS.get(t, "The screen: size, desktop background, splash art."))

    def _event_dclick(self, it: QListWidgetItem) -> None:
        name, ev = it.data(Qt.ItemDataRole.UserRole)
        self.eventRequested.emit(name, ev)

    def _emit(self, key: str, value) -> None:
        if not self._loading:
            self.edited.emit(self.target, key, value)

    def _editor(self, key: str, kind: str, value) -> QWidget:
        if kind in ("color", "bgcolor"):
            cb = QComboBox()
            cb.setProperty("i18n_skip", True)
            n = 16 if kind == "color" or (self.screen is not None and self.screen.get("ice_colors")
                                           and self.target is None) else 8
            for i in range(n):
                cb.addItem(color_icon(i), f"{i} {COLOR_NAMES[i]}", i)
            cb.setCurrentIndex(max(0, min(n - 1, int(value or 0))))
            cb.currentIndexChanged.connect(lambda i, k=key, c=cb: self._emit(k, c.itemData(i)))
            return cb
        if kind == "bool":
            ch = QCheckBox()
            ch.setChecked(bool(value))
            ch.toggled.connect(lambda v, k=key: self._emit(k, bool(v)))
            return ch
        if kind == "int":
            sp = QSpinBox()
            sp.setRange(-1 if key == "list_index" else 0, 32767)
            sp.setValue(int(value or 0))
            sp.editingFinished.connect(lambda k=key, s=sp: self._emit(k, s.value()))
            sp.valueChanged.connect(lambda v, k=key, s=sp: (not s.hasFocus()) and self._emit(k, v))
            return sp
        if kind.startswith("choice:"):
            cb = QComboBox()
            opts = kind.split(":", 1)[1].split("|")
            cb.addItems(opts)
            cb.setCurrentIndex(max(0, opts.index(value) if value in opts else 0))
            cb.currentTextChanged.connect(lambda t, k=key: self._emit(k, t))
            return cb
        if kind in ("items", "menus", "char", "file"):
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            if kind == "items":
                txt = f"({len(value or [])} items)"
            elif kind == "menus":
                txt = f"({len(value or [])} menus)"
            elif kind == "char":
                txt = f"{int(value or 0)}  {to_unicode(int(value or 0))}"
            else:
                txt = str(value or "")
            lab = QLineEdit(txt)
            lab.setReadOnly(kind != "file")
            if kind == "file":
                lab.editingFinished.connect(lambda k=key, e=lab: self._emit(k, e.text().strip()))
            h.addWidget(lab, 1)
            b = QPushButton("...")
            b.setFixedWidth(28)
            b.clicked.connect(lambda _c=False, k=key, kd=kind: self._more(k, kd))
            h.addWidget(b)
            return w
        e = QLineEdit(str(value if value is not None else ""))
        e.editingFinished.connect(lambda k=key, w=e: self._emit(k, w.text()))
        return e

    def _more(self, key: str, kind: str) -> None:
        value = self._value(key)
        if kind == "items":
            d = ItemsDialog([str(x) for x in value or []], self)
            if d.exec() == QDialog.DialogCode.Accepted:
                self._emit(key, d.items())
        elif kind == "menus":
            used = {c.name.lower() for c in self.screen.controls}
            d = MenuEditorDialog(copy.deepcopy(value or []), used, self)
            if d.exec() == QDialog.DialogCode.Accepted:
                self._emit(key, d.menus())
        elif kind == "char":
            d = CharPickerDialog(int(value or 0), self)
            if d.exec() == QDialog.DialogCode.Accepted:
                self._emit(key, d.value)
        elif kind == "file":
            start = str(self.screen.path.parent) if self.screen is not None and self.screen.path else ""
            f, _ = QFileDialog.getOpenFileName(self, "Art File", start,
                                               "ANSI / ASCII art (*.ans *.bin *.txt *.asc *.nfo);;All files (*)")
            if f:
                p = Path(f)
                if self.screen is not None and self.screen.path is not None:
                    try:
                        p = p.relative_to(self.screen.path.parent)
                    except ValueError:
                        pass
                self._emit(key, p.as_posix())


# ====================================================================== test run (simulator)
class TestRunDialog(QDialog):
    """Try the screens without DOS: the run-time simulator (radide/retro/design/textmode/sim.py)."""

    def __init__(self, screens: list[TScreen], parent=None):
        super().__init__(parent)
        from .sim import Sim
        self.setWindowTitle("Test Run - " + screens[0].name)
        self.sim = Sim(screens)
        self.sim.on_fire = self._fired
        lay = QVBoxLayout(self)
        self.canvas = CellCanvas(self.sim.buf)
        self.canvas.mousePressEvent = self._click
        self.canvas.keyPressEvent = self._key
        lay.addWidget(self.canvas, 0, Qt.AlignmentFlag.AlignCenter)
        self.status = QLabel("Keys and mouse work as in the DOS program. Events are listed here; "
                             "their code runs in the real program (Build & Run).")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.sim.start()
        self.canvas.set_buffer(self.sim.buf)
        self.canvas.setFocus()

    def _fired(self, handler: str, _sim) -> None:
        self.status.setText(f"Event: {handler}")

    def _sync(self) -> None:
        self.canvas.set_buffer(self.sim.buf)
        self.canvas.refresh()
        if not self.sim.running:
            self.status.setText("The program ended (Esc).")

    def _click(self, e) -> None:
        x, y = self.canvas.cell_at(e.position().toPoint())
        self.sim.click(x, y)
        self._sync()

    def _key(self, e) -> None:
        k = qt_key_code(e)
        if k:
            self.sim.handle_key(k)
            self._sync()


def qt_key_code(e) -> int:
    """A Qt key event -> the runtime's key code (ASCII, or 256 + scan code)."""
    from .sim import ALT_SCAN, KEY
    key = e.key()
    mods = e.modifiers()
    table = {Qt.Key.Key_Tab: KEY["tab"], Qt.Key.Key_Backtab: KEY["shift+tab"], Qt.Key.Key_Return: 13,
             Qt.Key.Key_Enter: 13, Qt.Key.Key_Escape: 27, Qt.Key.Key_Backspace: 8, Qt.Key.Key_Up: KEY["up"],
             Qt.Key.Key_Down: KEY["down"], Qt.Key.Key_Left: KEY["left"], Qt.Key.Key_Right: KEY["right"],
             Qt.Key.Key_F10: KEY["f10"], Qt.Key.Key_Home: KEY["home"], Qt.Key.Key_End: KEY["end"]}
    if key in table:
        return table[key]
    if mods & Qt.KeyboardModifier.AltModifier and Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
        return 256 + ALT_SCAN[chr(key)]
    if mods & Qt.KeyboardModifier.AltModifier and Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
        return 256 + ALT_SCAN[chr(key)]
    t = e.text()
    if t and t.isprintable():
        from .cp437 import from_unicode
        return from_unicode(t[0])
    return 0


# ====================================================================== the designer
class TuiDesigner(QWidget):
    """A .tform document in the IDE."""
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal()
    codeRequested = pyqtSignal(str)          # handler key: btnOK_Click / Main_Load / mnuExit_Click
    actionRequested = pyqtSignal(str)        # "generate" | "build_run" | "view_code" | "add_screen"

    def __init__(self, path: Path | None = None, screen: TScreen | None = None, parent=None):
        super().__init__(parent)
        if screen is None:
            screen = TScreen.load(path) if path is not None and Path(path).exists() else new_screen()
        if path is not None:
            screen.path = Path(path)
        self.screen = screen
        self._undo: list[str] = []
        self._redo: list[str] = []
        self._clean = screen.to_json()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.toolbar = QToolBar()
        lay.addWidget(self.toolbar)
        split = QSplitter()
        lay.addWidget(split, 1)
        # toolbox
        self.toolbox = QListWidget()
        self.toolbox.setMaximumWidth(150)
        for t in ("Pointer",) + TYPES:
            it = QListWidgetItem(tool_icon(t), t)
            it.setToolTip(TYPE_DESCRIPTIONS.get(t, "Select, move and resize controls"))
            it.setData(Qt.ItemDataRole.UserRole, t)
            self.toolbox.addItem(it)
        self.toolbox.setCurrentRow(0)
        self.toolbox.currentItemChanged.connect(self._tool_changed)
        self.toolbox.itemDoubleClicked.connect(self._tool_dclick)
        split.addWidget(self.toolbox)
        # canvas
        self.canvas = DesignCanvas(screen)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.canvas)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setStyleSheet("QScrollArea { background: #3c3c3c; }")
        split.addWidget(self.scroll)
        # properties
        self.props = PropertyGrid()
        split.addWidget(self.props)
        split.setSizes([140, 760, 300])
        self.canvas.selectionChanged.connect(self._sync_props)
        self.canvas.changed.connect(self._snapshot)
        self.canvas.applied.connect(self._after_change)
        self.canvas.codeRequested.connect(self._code_for)
        self.canvas.toolDone.connect(lambda: self.toolbox.setCurrentRow(0))
        self.props.edited.connect(self._prop_edited)
        self.props.selectRequested.connect(lambda c: self.canvas.select([c] if c else []))
        self.props.eventRequested.connect(self._code_for)
        self._build_toolbar()
        for seq, fn in (("Ctrl+Z", self.undo), ("Ctrl+Y", self.redo), ("Ctrl+Shift+Z", self.redo),
                        ("Ctrl+C", self.canvas.copy_selected), ("Ctrl+V", self.canvas.paste),
                        ("Ctrl+X", self.cut), ("Ctrl+A", self.select_all), ("Ctrl+S", self.save),
                        ("F5", self.test_run)):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(fn)
        self._sync_props()

    # ------------------------------------------------------------ toolbar
    def _build_toolbar(self) -> None:
        tb = self.toolbar
        self.size_box = QComboBox()
        for c, r in SIZES:
            self.size_box.addItem(f"{c} x {r}", (c, r))
        i = self.size_box.findData((self.screen.cols, self.screen.rows))
        self.size_box.setCurrentIndex(max(0, i))
        self.size_box.activated.connect(self._size_changed)
        tb.addWidget(QLabel(" Screen: "))
        tb.addWidget(self.size_box)
        tb.addSeparator()
        tb.addAction("Undo", self.undo)
        tb.addAction("Redo", self.redo)
        tb.addSeparator()
        self.a_grid = tb.addAction("Grid", self._toggle_grid)
        self.a_grid.setCheckable(True)
        self.zoom_box = QComboBox()
        for z in (1.0, 1.5, 2.0):
            self.zoom_box.addItem(f"{int(z * 100)}%", z)
        self.zoom_box.activated.connect(lambda i: self.canvas.set_zoom(self.zoom_box.itemData(i)))
        tb.addWidget(self.zoom_box)
        tb.addSeparator()
        tb.addAction("Bring to Front", lambda: self._zorder(True))
        tb.addAction("Send to Back", lambda: self._zorder(False))
        tb.addSeparator()
        tb.addAction("Test Run (F5)", self.test_run)
        tb.addAction("View Code", lambda: self.actionRequested.emit("view_code"))
        tb.addAction("Generate Code", lambda: self.actionRequested.emit("generate"))
        tb.addAction("Build && Run in DOSBox-X", lambda: self.actionRequested.emit("build_run"))
        tb.addAction("Add Screen...", lambda: self.actionRequested.emit("add_screen"))
        tb.addAction("Export PNG...", self.export_png)

    def _toggle_grid(self) -> None:
        self.canvas.show_grid = self.a_grid.isChecked()
        self.canvas.update()

    def _size_changed(self, i: int) -> None:
        cols, rows = self.size_box.itemData(i)
        if (cols, rows) == (self.screen.cols, self.screen.rows):
            return
        self._snapshot("Screen size")
        self.screen.set("cols", cols)
        self.screen.set("rows", rows)
        for c in self.screen.controls:
            if c.type == "StatusBar" and c.y >= rows - 1 or c.y >= rows:
                c.y = rows - 1 if c.type == "StatusBar" else c.y
            if c.type in ("MenuBar", "StatusBar"):
                c.w = cols
            self.screen.clamp(c)
        self._after_change()

    def _zorder(self, front: bool) -> None:
        sel = list(self.canvas.selected)
        if not sel:
            return
        self._snapshot("Z-order")
        for c in sel:
            self.screen.controls.remove(c)
        if front:
            self.screen.controls.extend(sel)
        else:
            self.screen.controls[0:0] = sel
        self._after_change()

    # ------------------------------------------------------------ tools
    def _tool_changed(self, cur, _prev) -> None:
        self.canvas.tool = cur.data(Qt.ItemDataRole.UserRole) if cur is not None else "Pointer"

    def _tool_dclick(self, it) -> None:
        t = it.data(Qt.ItemDataRole.UserRole)
        if t == "Pointer":
            return
        x, y = self.screen.cols // 2 - 5, self.screen.rows // 2
        sel = self.canvas.selected
        if len(sel) == 1 and sel[0].type in ("Window", "Frame"):
            x, y = sel[0].x + 2, sel[0].y + 2
        self.canvas.add_control(t, x, y)
        self.toolbox.setCurrentRow(0)

    def select_all(self) -> None:
        self.canvas.select(list(self.screen.controls))

    def cut(self) -> None:
        self.canvas.copy_selected()
        self.canvas.delete_selected()

    # ------------------------------------------------------------ changes / undo
    def _snapshot(self, _what: str = "") -> None:
        self._undo.append(self.screen.to_json())
        del self._undo[:-MAX_UNDO]
        self._redo.clear()

    def _after_change(self) -> None:
        self.canvas.rerender()
        self._sync_props()
        self.modifiedChanged.emit(self.is_modified())

    def _restore(self, text: str) -> None:
        names = [c.name for c in self.canvas.selected]
        path = self.screen.path
        s = TScreen.from_dict(json.loads(text), path)
        self.screen.props, self.screen.controls = s.props, s.controls
        self.canvas.selected = [c for c in self.screen.controls if c.name in names]
        self._after_change()

    def undo(self) -> None:
        if self._undo:
            self._redo.append(self.screen.to_json())
            self._restore(self._undo.pop())

    def redo(self) -> None:
        if self._redo:
            self._undo.append(self.screen.to_json())
            self._restore(self._redo.pop())

    def _sync_props(self) -> None:
        self.props.bind(self.screen, self.canvas.selected)

    def _prop_edited(self, target, key: str, value) -> None:
        cur = target.get(key) if target is not None else self.screen.get(key)
        if cur == value:
            return
        if key == "name":
            value = str(value).strip()
            other = self.screen.find(value)
            if not value or (other is not None and other is not target):
                QMessageBox.warning(self, "Name", f"The name '{value}' is empty or already used.")
                self._sync_props()
                return
        self._snapshot(f"Set {key}")
        if target is None:
            self.screen.set(key, value)
            if key in ("cols", "rows"):
                for c in self.screen.controls:
                    self.screen.clamp(c)
        else:
            target.set(key, value)
            if key in ("x", "y", "w", "h"):
                self.screen.clamp(target)
            if key == "value" and target.type == "Option" and value:
                for o in self.screen.controls:
                    if o is not target and o.type == "Option" and o.get("group") == target.get("group"):
                        o.props["value"] = False
        self._after_change()

    # ------------------------------------------------------------ code
    def _code_for(self, name: str, event: str) -> None:
        """Make sure the event has a handler (recorded in the .tform) and ask the IDE to show its code."""
        if not name:
            evs = list(self.screen.get("events") or [])
            if event not in evs:
                self._snapshot("Event")
                self.screen.set("events", evs + [event])
                self._after_change()
            self.codeRequested.emit(f"{self.screen.name}_{event}")
            return
        c = self.screen.find(name)
        if c is not None:
            evs = c.events()
            if event not in evs:
                self._snapshot("Event")
                c.props["events"] = evs + [event]
                self._after_change()
        self.codeRequested.emit(f"{name}_{event}")

    # ------------------------------------------------------------ document
    @property
    def path(self) -> Path:
        return self.screen.path or Path(f"{self.screen.name}.tform")

    def is_modified(self) -> bool:
        return self.screen.to_json() != self._clean

    def save(self, path=None) -> bool:
        if path is None and self.screen.path is None:
            f, _ = QFileDialog.getSaveFileName(self, "Save Screen", f"{self.screen.name}.tform",
                                               "Text-mode screens (*.tform)")
            if not f:
                return False
            path = f
        self.screen.save(path)
        self._clean = self.screen.to_json()
        self.modifiedChanged.emit(False)
        self.saved.emit()
        return True

    def edit_op(self, op: str) -> None:
        {"undo": self.undo, "redo": self.redo, "copy": self.canvas.copy_selected, "paste": self.canvas.paste,
         "cut": self.cut, "delete": self.canvas.delete_selected, "select_all": self.select_all}.get(op,
                                                                                                  lambda: None)()

    def test_run(self) -> None:
        screens = [self.screen]
        if self.screen.path is not None:
            from .model import load_project_screens
            try:
                others = [s for s in load_project_screens(self.screen.path.parent)
                          if s.path is None or s.path.resolve() != self.screen.path.resolve()]
                screens += others
            except (OSError, ValueError):
                pass
        TestRunDialog(screens, self).exec()

    def export_png(self) -> None:
        from .glyphs import save_png
        f, _ = QFileDialog.getSaveFileName(self, "Export PNG", f"{self.screen.name}.png", "PNG (*.png)")
        if f:
            save_png(designer_render(self.screen), f, 1)

    def problems(self) -> list[str]:
        return self.screen.problems()


def ask_new_screen(parent, default: str = "Screen1") -> tuple[str, int, int] | None:
    name, ok = QInputDialog.getText(parent, "New Text-Mode Screen", "Screen name (letters and digits):",
                                    text=default)
    if not ok or not name.strip():
        return None
    sizes = [f"{c} x {r}" for c, r in SIZES]
    sz, ok = QInputDialog.getItem(parent, "New Text-Mode Screen", "Size:", sizes, 0, False)
    if not ok:
        return None
    c, r = SIZES[sizes.index(sz)]
    return "".join(ch for ch in name.strip() if ch.isalnum()) or default, c, r


__all__ = ["TuiDesigner", "DesignCanvas", "PropertyGrid", "MenuEditorDialog", "ItemsDialog", "TestRunDialog",
           "ask_new_screen", "qt_key_code", "FOCUSABLE"]
