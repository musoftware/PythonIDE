"""Widget-level commands: find / inspect / click / type / keys / select items / grab screenshots, menus and
actions, dialogs (list, press a button, close)."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QAbstractButton, QAbstractItemView, QAbstractSpinBox, QApplication, QCheckBox,
                             QComboBox, QLineEdit, QListWidget, QMenu, QPlainTextEdit, QTabBar, QTabWidget,
                             QTableWidget, QTextEdit, QTreeWidget, QWidget)

from .registry import AutomationError, command
from . import widgets as W
from .commands_core import pump

try:
    from PyQt6.QtTest import QTest
except ImportError:  # pragma: no cover - a build without QtTest: plain events
    QTest = None

BUTTONS = {"left": Qt.MouseButton.LeftButton, "right": Qt.MouseButton.RightButton,
           "middle": Qt.MouseButton.MiddleButton}


def _pos(w, x=None, y=None) -> QPoint:
    return QPoint(int(x), int(y)) if x is not None and y is not None else w.rect().center()


def mouse(w: QWidget, kind: str = "click", button: str = "left", x=None, y=None, modifiers: str = "") -> None:
    b = BUTTONS.get(button, Qt.MouseButton.LeftButton)
    mods = _mods(modifiers)
    p = _pos(w, x, y)
    if QTest is None:
        raise AutomationError("PyQt6.QtTest is not available in this build")
    if kind == "dclick":
        QTest.mouseClick(w, b, mods, p)            # Qt needs the press/release before the double-click
        QTest.mouseDClick(w, b, mods, p)
    elif kind == "press":
        QTest.mousePress(w, b, mods, p)
    elif kind == "release":
        QTest.mouseRelease(w, b, mods, p)
    elif kind == "move":
        QTest.mouseMove(w, p)
    else:
        QTest.mouseClick(w, b, mods, p)


def _mods(text: str):
    m = Qt.KeyboardModifier.NoModifier
    for part in (text or "").lower().replace("+", " ").split():
        m |= {"ctrl": Qt.KeyboardModifier.ControlModifier, "shift": Qt.KeyboardModifier.ShiftModifier,
              "alt": Qt.KeyboardModifier.AltModifier, "meta": Qt.KeyboardModifier.MetaModifier}.get(
            part, Qt.KeyboardModifier.NoModifier)
    return m


def send_keys(w: QWidget, keys: str) -> None:
    """keys like "F5", "Ctrl+S", "Return", "Ctrl+Space", several separated by ', '."""
    if QTest is None:
        raise AutomationError("PyQt6.QtTest is not available in this build")
    top = w.window()
    if top is not None and QApplication.activeWindow() is not top:     # window shortcuts need an active window
        top.activateWindow()
        pump()
    for part in [k.strip() for k in keys.split(",") if k.strip()]:
        seq = QKeySequence(part)
        if seq.isEmpty():
            raise AutomationError(f"unknown key {part!r}")
        comb = seq[0]
        try:
            QTest.keyClick(w, comb.key(), comb.keyboardModifiers())
        except RuntimeError:          # the widget went away (an item editor that committed on focus change)
            w = QApplication.focusWidget() or top
            QTest.keyClick(w, comb.key(), comb.keyboardModifiers())
        pump()


def _target(ctx, sel):
    if sel is None:
        w = QApplication.focusWidget() or QApplication.activeModalWidget() or ctx.win
        return w
    return W.find(ctx, sel)


@command("widgets", doc="widgets matching a selector (see radide/automation/widgets.py) -> [state]")
def _widgets(ctx, sel=None, limit: int = 50, full: bool = False):
    return [W.state(w, full) for w in W.find_all(ctx, sel or {})[:limit]]


@command("widget", doc="state of one widget: cls, name, text, visible, enabled, rect, items, checked ...")
def _widget(ctx, sel):
    return W.state(W.find(ctx, sel))


@command("exists", doc="how many widgets match")
def _exists(ctx, sel):
    return len(W.find_all(ctx, sel))


@command("click", doc="mouse click on a widget (x/y local, button, modifiers, kind=click|dclick|press|release|move)")
def _click(ctx, sel, x=None, y=None, button: str = "left", kind: str = "click", modifiers: str = "",
           async_: bool = False):
    w = W.find(ctx, sel)
    if async_:
        QTimer.singleShot(0, lambda: mouse(w, kind, button, x, y, modifiers))
    else:
        mouse(w, kind, button, x, y, modifiers)
    return W.state(w, False)


@command("press_button", doc="QAbstractButton.click() on a button found by selector (async: no answer wait)")
def _press_button(ctx, sel, async_: bool = True):
    w = W.find(ctx, sel)
    if not isinstance(w, QAbstractButton):
        raise AutomationError(f"{type(w).__name__} is not a button")
    QTimer.singleShot(0, w.click) if async_ else w.click()
    return W.state(w, False)


@command("type", doc="type text into a widget like a user (key events); clear=True selects all first")
def _type(ctx, text: str, sel=None, clear: bool = False):
    w = _target(ctx, sel)
    w.setFocus()
    if clear:
        if isinstance(w, (QLineEdit, QPlainTextEdit, QTextEdit)):
            w.selectAll()
        elif isinstance(w, QAbstractSpinBox):
            w.selectAll()
    if QTest is None:
        raise AutomationError("PyQt6.QtTest is not available in this build")
    QTest.keyClicks(w, text)
    pump()
    return W.state(w, False)


@command("key", doc="send keys (\"F5\", \"Ctrl+S\", \"Return\" ...) to a widget (default: the focus widget)")
def _key(ctx, keys: str, sel=None, async_: bool = False):
    w = _target(ctx, sel)
    if async_:
        QTimer.singleShot(0, lambda: send_keys(w, keys))
        return {"target": type(w).__name__}
    name = type(w).__name__
    send_keys(w, keys)
    return {"target": name}


@command("set_value", doc="set a widget's value directly: text / checked / index / number")
def _set_value(ctx, sel, value):
    w = W.find(ctx, sel)
    if isinstance(w, QLineEdit):
        w.setText(str(value))
        w.editingFinished.emit()
    elif isinstance(w, (QPlainTextEdit, QTextEdit)):
        w.setPlainText(str(value))
    elif isinstance(w, (QCheckBox,)) or (isinstance(w, QAbstractButton) and w.isCheckable()):
        w.setChecked(bool(value))
    elif isinstance(w, QComboBox):
        if isinstance(value, int):
            w.setCurrentIndex(value)
        else:
            i = w.findText(str(value))
            if i < 0:
                i = next((k for k in range(w.count()) if str(value).lower() in w.itemText(k).lower()), -1)
            if i < 0:
                if w.isEditable():
                    w.setEditText(str(value))
                else:
                    raise AutomationError(f"{value!r} is not in the combo box: {[w.itemText(k) for k in range(w.count())]}")
            else:
                w.setCurrentIndex(i)
                w.activated.emit(i)
    elif isinstance(w, QAbstractSpinBox) and hasattr(w, "setValue"):
        w.setValue(type(w.value())(value))
    elif hasattr(w, "setValue"):
        w.setValue(value)
    else:
        raise AutomationError(f"cannot set a value on {type(w).__name__}")
    pump()
    return W.state(w, False)


def _find_item(w, text: str, column: int = 0):
    want = text.lower()
    if isinstance(w, QListWidget):
        for i in range(w.count()):
            if want == w.item(i).text().lower() or (want.startswith("~") and want[1:] in w.item(i).text().lower()):
                return w.item(i)
        for i in range(w.count()):
            if want in w.item(i).text().lower():
                return w.item(i)
    elif isinstance(w, QTreeWidget):
        from PyQt6.QtWidgets import QTreeWidgetItemIterator
        parts = text.split("/") if "/" in text and not text.startswith("~") else [text]
        if len(parts) > 1:                                  # "Parent/Child" path
            items = [w.topLevelItem(i) for i in range(w.topLevelItemCount())]
            it = None
            for p in parts:
                it = next((x for x in items if x.text(column).lower() == p.lower()), None) or next(
                    (x for x in items if p.lower() in x.text(column).lower()), None)
                if it is None:
                    return None
                items = [it.child(i) for i in range(it.childCount())]
            return it
        exact = sub = None
        itr = QTreeWidgetItemIterator(w)
        while itr.value():
            it = itr.value()
            t = it.text(column).lower()
            if t == want and exact is None:
                exact = it
            elif want.lstrip("~") in t and sub is None:
                sub = it
            itr += 1
        return exact or sub
    elif isinstance(w, QTableWidget):
        for r in range(w.rowCount()):
            for c in range(w.columnCount()):
                it = w.item(r, c)
                if it is not None and want in it.text().lower():
                    return it
    return None


@command("select_item", doc="select an item of a list / tree / table / combo / tab widget by text "
                            "(dclick=True: double-click it, like a user)")
def _select_item(ctx, sel, text: str, dclick: bool = False, column: int = 0, async_: bool = True):
    w = W.find(ctx, sel)
    if isinstance(w, QComboBox):
        return _set_value(ctx, w, text)
    if isinstance(w, (QTabWidget, QTabBar)):
        n = w.count()
        for i in range(n):
            if text.lower() in W.clean(w.tabText(i)).lower():
                w.setCurrentIndex(i)
                return {"index": i}
        raise AutomationError(f"no tab {text!r}")
    it = _find_item(w, text, column)
    if it is None:
        raise AutomationError(f"no item {text!r} in {type(w).__name__}")
    if isinstance(w, QTreeWidget):
        p = it.parent()
        while p is not None:
            p.setExpanded(True)
            p = p.parent()
        w.setCurrentItem(it, column)
        w.scrollToItem(it)
    else:
        w.setCurrentItem(it)
        w.scrollToItem(it)
    if dclick:
        view = w.viewport() if isinstance(w, QAbstractItemView) else w
        r = w.visualItemRect(it)
        pt = r.center()

        def go():
            if QTest is not None:
                QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pt)
                QTest.mouseDClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pt)
            if isinstance(w, QTreeWidget) and not ctx.data.get("_dclick_seen"):
                pass
        QTimer.singleShot(0, go) if async_ else go()
    return {"text": it.text(column) if isinstance(w, QTreeWidget) else it.text()}


@command("grab", doc="screenshot of a widget (default: the main window) into a PNG file")
def _grab(ctx, path: str, sel=None):
    w = ctx.win if sel is None else (W.find_dialog(sel["dialog"]) if isinstance(sel, dict) and "dialog" in sel
                                      else W.find(ctx, sel))
    pump()
    pm = w.grab()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not pm.save(path):
        raise AutomationError(f"cannot save {path}")
    return {"path": path, "size": [pm.width(), pm.height()]}


@command("focus", doc="the focus widget and the active window")
def _focus(ctx):
    f = QApplication.focusWidget()
    a = QApplication.activeWindow()
    return {"focus": W.state(f, False) if f else None, "active_window": a.windowTitle() if a else None}


# ------------------------------------------------------------------------------------ menus / actions
def _menu_path(a: QAction, parents: list[str]) -> str:
    return "/".join(parents + [W.clean(a.text())])


def walk_actions(ctx):
    """(path, action) of every menu bar action, depth first, plus toolbar actions ("Toolbar:<name>/...")."""
    out = []

    def walk(menu, parents):
        for a in menu.actions():
            if a.isSeparator():
                continue
            out.append((_menu_path(a, parents), a))
            m = a.menu()
            if m is not None:
                try:
                    m.aboutToShow.emit()        # menus filled on demand (Recent, Window ...)
                except Exception:  # noqa: BLE001
                    pass
                walk(m, parents + [W.clean(a.text())])
    walk(ctx.win.menuBar(), [])
    from PyQt6.QtWidgets import QToolBar
    for tb in ctx.win.findChildren(QToolBar):
        for a in tb.actions():
            if not a.isSeparator():
                out.append((f"Toolbar:{tb.windowTitle() or tb.objectName()}/{W.clean(a.text())}", a))
    return out


def _norm(s: str) -> str:
    return W.clean(s).rstrip(".").strip().lower()


def find_action(ctx, path: str = "", name: str = "", text: str = "", shortcut: str = "") -> QAction:
    acts = walk_actions(ctx)
    if path:
        want = [_norm(p) for p in path.split("/")]
        for p, a in acts:
            have = [_norm(x) for x in p.split("/")]
            if have == want:
                return a
        for p, a in acts:                      # suffix match: "Debug/Start" also finds "Debug/Start Debugging"
            have = [_norm(x) for x in p.split("/")]
            if len(have) == len(want) and all(w in h for w, h in zip(want, have)):
                return a
        raise AutomationError(f"no menu item {path!r}")
    for a in [a for _p, a in acts] + ctx.win.findChildren(QAction):
        if name and a.objectName() == name:
            return a
        if text and _norm(a.text()) == _norm(text):
            return a
        if shortcut and a.shortcut().toString().lower() == shortcut.lower():
            return a
    raise AutomationError(f"no action name={name!r} text={text!r} shortcut={shortcut!r}")


@command("actions", doc="menu bar + toolbar actions [{path, name, enabled, checked, shortcut}] (filter: substring)")
def _actions(ctx, filter: str = ""):  # noqa: A002
    out = []
    for p, a in walk_actions(ctx):
        if filter and filter.lower() not in p.lower():
            continue
        out.append({"path": p, "name": a.objectName(), "enabled": a.isEnabled(), "checkable": a.isCheckable(),
                    "checked": a.isChecked(), "shortcut": a.shortcut().toString(), "submenu": a.menu() is not None})
    return out


@command("trigger", doc="trigger a menu / toolbar action by path ('File/New Project...'), name, text or "
                        "shortcut; async by default (a modal dialog may open)")
def _trigger(ctx, path: str = "", name: str = "", text: str = "", shortcut: str = "", async_: bool = True,
             checked=None):
    a = find_action(ctx, path, name, text, shortcut)
    if not a.isEnabled():
        raise AutomationError(f"action {W.clean(a.text())!r} is disabled")

    def go():
        if checked is not None and a.isCheckable():
            a.setChecked(not bool(checked))
        a.trigger()
    QTimer.singleShot(0, go) if async_ else go()
    return {"text": W.clean(a.text()), "enabled": a.isEnabled(), "checked": a.isChecked()}


# ------------------------------------------------------------------------------------ dialogs
@command("dialogs", doc="open dialogs / message boxes / popup menus [{cls, title, text, buttons, labels}]")
def _dialogs(ctx):
    return [W.describe_dialog(d) for d in W.dialogs()]


@command("press", doc="press a button of a dialog (dialog: title substring / 'active'; button: text)")
def _press(ctx, button: str, dialog=None, async_: bool = True):
    d = W.find_dialog(dialog)
    want = W.clean(button).lower()
    btns = [b for b in d.findChildren(QAbstractButton) if b.isVisible() and b.isEnabled()]
    b = next((b for b in btns if W.clean(b.text()).lower() == want), None) or next(
        (b for b in btns if want in W.clean(b.text()).lower()), None)
    if b is None:
        raise AutomationError(f"no button {button!r} in {d.windowTitle()!r}: {[W.clean(x.text()) for x in btns]}")
    QTimer.singleShot(0, b.click) if async_ else b.click()
    return {"dialog": d.windowTitle(), "button": W.clean(b.text())}


@command("close_dialog", doc="reject / close a dialog (default: the active one)")
def _close_dialog(ctx, dialog=None, accept: bool = False):
    d = W.find_dialog(dialog)
    title = d.windowTitle()

    def go():
        if isinstance(d, QMenu):
            d.close()
        elif hasattr(d, "accept") and accept:
            d.accept()
        elif hasattr(d, "reject"):
            d.reject()
        else:
            d.close()
    QTimer.singleShot(0, go)
    return {"closed": title}


@command("menu_item", doc="trigger an item of an open popup menu (context menu) by text path 'A/B'")
def _menu_item(ctx, text: str):
    menus = [d for d in W.dialogs() if isinstance(d, QMenu)]
    if not menus:
        raise AutomationError("no popup menu is open")
    m = menus[-1]
    parts = text.split("/")
    for i, p in enumerate(parts):
        a = next((a for a in m.actions() if _norm(a.text()) == _norm(p)), None) or next(
            (a for a in m.actions() if _norm(p) in _norm(a.text())), None)
        if a is None:
            raise AutomationError(f"no item {p!r} in menu: {[W.clean(x.text()) for x in m.actions()]}")
        if i == len(parts) - 1:
            top = menus[0]
            QTimer.singleShot(0, lambda: (a.trigger(), top.close()))
            return {"item": W.clean(a.text())}
        m = a.menu()
        if m is None:
            raise AutomationError(f"{p!r} has no submenu")
    return None
