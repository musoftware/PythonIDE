"""Form designer commands, done the way a user does them: pick a Toolbox tool and click / drag on the form,
select and double-click controls, edit values in the Properties window, read the form back."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QComboBox, QWidget

from .registry import AutomationError, command
from .commands_core import pump
from .commands_widgets import mouse

try:
    from PyQt6.QtTest import QTest
except ImportError:  # pragma: no cover
    QTest = None


def move_pressed(w, pos: QPoint) -> None:
    """A mouse move with the left button held (QTest.mouseMove carries no buttons for widgets)."""
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtWidgets import QApplication
    ev = QMouseEvent(QMouseEvent.Type.MouseMove, QPointF(pos), QPointF(w.mapToGlobal(pos)),
                     Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(w, ev)


def designer(ctx, form: str | None = None):
    win = ctx.win
    if form:
        win.open_designer(form)
        pump()
    d = win._current_designer()
    if d is None:
        raise AutomationError("no form designer is the current tab (open_form first)")
    return d


def control(d, name: str):
    if not name or name == d.doc.form.name:
        return None
    c = d.doc.form.find(name)
    if c is None:
        raise AutomationError(f"no control {name!r} on {d.doc.form.name}: {[x.name for x in d.doc.form.controls]}")
    return c


def describe(c, props=("Text", "Caption", "Left", "Top", "Width", "Height")) -> dict:
    return {"name": c.name, "type": c.type, "parent": c.parent,
            "props": {k: c.props.get(k) for k in props if k in c.props}}


@command("designer_controls", doc="controls of the current (or given) form [{name, type, parent, props}]")
def _controls(ctx, form: str | None = None, all_props: bool = False):
    d = designer(ctx, form)
    return {"form": d.doc.form.name, "selected": [c.name for c in d.doc.selection],
            "controls": [({"name": c.name, "type": c.type, "parent": c.parent, "props": dict(c.props)}
                          if all_props else describe(c)) for c in d.doc.form.controls],
            "can_undo": d.doc.can_undo(), "can_redo": d.doc.can_redo(), "modified": d.doc.modified}


@command("toolbox", doc="the Toolbox tools that are shown [{name, group}] (filter substring)")
def _toolbox(ctx, filter: str = ""):  # noqa: A002
    from ..toolbox import TB_ROLE, CAT_ROLE
    tb = ctx.win.toolbox
    out = []
    for r in range(tb.count()):
        it = tb.item(r)
        if it.data(TB_ROLE) == "item" and not it.isHidden():
            n = it.data(Qt.ItemDataRole.UserRole)
            if not filter or filter.lower() in str(n).lower():
                out.append({"name": n, "group": it.data(CAT_ROLE), "label": it.text()})
    return out


def pick_tool(ctx, type_name: str) -> None:
    """Click the tool in the Toolbox like a user (falls back to TOOL_STATE when it is not shown)."""
    from ..toolbox import TOOL_STATE, TB_ROLE
    tb = ctx.win.toolbox
    row = next((r for r in range(tb.count()) if tb.item(r).data(Qt.ItemDataRole.UserRole) == type_name
                and tb.item(r).data(TB_ROLE) == "item"), None)
    if row is None:
        raise AutomationError(f"the Toolbox has no tool {type_name!r}")
    it = tb.item(row)
    if it.isHidden():
        raise AutomationError(f"the tool {type_name!r} is hidden (not supported by this project)")
    tb.scrollToItem(it)
    pump()
    if QTest is not None and tb.isVisible():
        QTest.mouseClick(tb.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         tb.visualItemRect(it).center())
        pump()
    if TOOL_STATE.current != type_name:
        tb.setCurrentRow(row)
        pump()
    if TOOL_STATE.current != type_name:
        TOOL_STATE.set(type_name)


@command("designer_place", doc="place a control: Toolbox tool + click (or drag when w/h are given) on the form "
                               "at x, y (form coordinates); returns the new control")
def _place(ctx, type: str, x: int = 40, y: int = 40, w: int | None = None, h: int | None = None,  # noqa: A002
           form: str | None = None, name: str | None = None):
    d = designer(ctx, form)
    before = {id(c) for c in d.doc.form.controls}
    pick_tool(ctx, type)
    ov = d.overlay
    ox, oy = d.doc.form.client_origin(None) if hasattr(d.doc.form, "client_origin") else (0, 0)
    p = QPoint(int(x) + ox, int(y) + oy)
    if QTest is None:
        d.create_control(type, p)
    else:
        QTest.mousePress(ov, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p)
        if w and h:
            q = QPoint(p.x() + int(w), p.y() + int(h))
            move_pressed(ov, QPoint(p.x() + 5, p.y() + 5))
            move_pressed(ov, q)
            QTest.mouseRelease(ov, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, q)
        else:
            QTest.mouseRelease(ov, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p)
    pump()
    new = [c for c in d.doc.form.controls if id(c) not in before]
    if not new:
        raise AutomationError(f"no {type} was created (tool state / designer did not react)")
    c = new[-1]
    if name and name != c.name:
        _set_property(ctx, c.name, "Name", name)
        c = d.doc.form.find(name) or c
    return describe(c)


@command("designer_select", doc="click a control on the form (ctrl=True: add to the selection); '' = the form")
def _select(ctx, name: str = "", ctrl: bool = False, form: str | None = None):
    d = designer(ctx, form)
    c = control(d, name)
    if c is None:
        d.doc.select(None)
    else:
        r = d.overlay.abs_rect(c)
        mouse(d.overlay, "click", "left", r.center().x(), r.center().y(), "ctrl" if ctrl else "")
        if c not in d.doc.selection:
            d.doc.select(c, add=ctrl)
    pump()
    return [x.name for x in d.doc.selection]


@command("designer_dclick", doc="double-click a control (or the form, name='') - opens / writes its default "
                                "event handler in the code editor")
def _dclick(ctx, name: str = "", form: str | None = None):
    d = designer(ctx, form)
    c = control(d, name)
    if c is None:
        pos = QPoint(d.overlay.width() - 5, d.overlay.height() - 5)
        fr = d.doc.form
        pos = QPoint(int(fr.props.get("Width", 300)) - 10, int(fr.props.get("Height", 200)) - 10) \
            if hasattr(fr, "props") else pos
        d.doc.eventRequested.emit(None, "Load")
    else:
        r = d.overlay.abs_rect(c)
        mouse(d.overlay, "dclick", "left", r.center().x(), r.center().y())
    pump(150)
    from .commands_ide import _tabs
    return _tabs(ctx)


@command("designer_drag", doc="drag a control by dx, dy with the mouse (VS move)")
def _drag(ctx, name: str, dx: int, dy: int, form: str | None = None):
    d = designer(ctx, form)
    c = control(d, name)
    r = d.overlay.abs_rect(c)
    p = r.center()
    q = QPoint(p.x() + int(dx), p.y() + int(dy))
    QTest.mousePress(d.overlay, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p)
    for i in range(1, 6):
        move_pressed(d.overlay, QPoint(p.x() + int(dx) * i // 5, p.y() + int(dy) * i // 5))
    QTest.mouseRelease(d.overlay, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, q)
    pump()
    return describe(c)


def _row_for(panel, prop: str) -> int:
    for row in range(panel.props.rowCount()):
        dfn = panel._row_def(row)
        if dfn is not None and dfn.name.lower() == prop.lower():
            return row
    raise AutomationError(f"the Properties window has no {prop!r}")


@command("set_property", doc="set a property in the Properties window (name '' = the form): types into the "
                             "value cell / picks the combo value")
def _set_property(ctx, name: str, prop: str, value, form: str | None = None):
    d = designer(ctx, form)
    c = control(d, name)
    d.doc.select(c)
    pump()
    panel = ctx.win.properties
    panel.tabs.setCurrentIndex(0)
    row = _row_for(panel, prop)
    panel.props.setCurrentCell(row, 1)
    w = panel.props.cellWidget(row, 1)
    combo = w if isinstance(w, QComboBox) else (w.findChild(QComboBox) if isinstance(w, QWidget) else None)
    if combo is not None:
        i = combo.findText(str(value))
        if i < 0:
            i = next((k for k in range(combo.count()) if str(value).lower() == combo.itemText(k).lower()), -1)
        if i < 0 and combo.isEditable():
            combo.setEditText(str(value))
            if combo.lineEdit() is not None:
                combo.lineEdit().editingFinished.emit()
        elif i < 0:
            raise AutomationError(f"{prop}: {value!r} not in {[combo.itemText(k) for k in range(combo.count())]}")
        else:
            combo.setCurrentIndex(i)
            combo.activated.emit(i)
    else:
        it = panel.props.item(row, 1)
        if it is None:
            le = w.findChild(__import__("PyQt6.QtWidgets", fromlist=["QLineEdit"]).QLineEdit) if w else None
            if le is None:
                raise AutomationError(f"{prop}: no editable cell ({type(w).__name__ if w else None})")
            le.setText(str(value))
            le.editingFinished.emit()
        else:
            it.setText(str(value))           # itemChanged -> PropertiesPanel._on_item_changed (validation)
    pump()
    owner = d.doc.form.find(value) if prop.lower() == "name" else (c if c is not None else None)
    props = owner.props if owner is not None else getattr(d.doc.form, "props", {})
    got = props.get(prop) if prop.lower() != "name" else (owner.name if owner is not None else None)
    return {"control": owner.name if owner is not None else d.doc.form.name, "prop": prop, "value": got,
            "help": panel.help.text()}


@command("get_property", doc="a property value as stored in the form (name '' = the form)")
def _get_property(ctx, name: str, prop: str, form: str | None = None):
    d = designer(ctx, form)
    c = control(d, name)
    props = c.props if c is not None else getattr(d.doc.form, "props", {})
    return props.get(prop)


@command("events_tab", doc="the Properties window's Events tab for a control: [{event, handler}]; "
                           "dclick=<event> writes / opens that handler")
def _events_tab(ctx, name: str = "", dclick: str = "", form: str | None = None):
    d = designer(ctx, form)
    c = control(d, name)
    d.doc.select(c)
    pump()
    panel = ctx.win.properties
    panel.tabs.setCurrentIndex(1)
    pump()
    rows = []
    for r in range(panel.events.rowCount()):
        a, b = panel.events.item(r, 0), panel.events.item(r, 1)
        rows.append({"event": a.text() if a else "", "handler": b.text() if b else ""})
        if dclick and a is not None and a.text().lower() == dclick.lower():
            panel._on_event_dclick(r, 0)
            pump(100)
    return rows
