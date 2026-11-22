"""Finding widgets / actions and describing them for the automation channel.

Selector (a dict, every key optional, all given keys must match):
    name      objectName (exact)
    cls       class name, own or a base class (e.g. "QPushButton", "DesignerView")
    text      substring of the widget's text (button / label / line edit / window title ...), '&' ignored,
              case-insensitive; "=Exact" for an exact match
    title     substring of the title of the widget's top-level window
    attr      attribute name on the main window (win.<attr>, e.g. "output", "error_list", "toolbox")
    visible   default True: only visible widgets (False: hidden ones too)
    index     n-th match (default 0)
    within    another selector: only descendants of that widget
A plain string is a shorthand: "#objName", "@attr" (win attribute), "Class", or "text".
"""
from __future__ import annotations

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import (QAbstractButton, QAbstractSpinBox, QApplication, QComboBox, QDialog, QDockWidget,
                             QGroupBox, QLabel, QLineEdit, QListWidget, QMenu, QMessageBox, QPlainTextEdit,
                             QSlider, QTabWidget, QTableWidget, QTextEdit, QTreeWidget, QWidget)

from .registry import AutomationError


def clean(s: str) -> str:
    return (s or "").replace("&&", "\0").replace("&", "").replace("\0", "&").strip()


def _match_text(have: str, want: str) -> bool:
    have = clean(have)
    if want.startswith("="):
        return have.lower() == clean(want[1:]).lower()
    return clean(want).lower() in have.lower()


def class_names(w) -> list[str]:
    return [c.__name__ for c in type(w).__mro__]


def widget_text(w) -> str:
    try:
        if isinstance(w, QMessageBox):
            return w.text()
        if isinstance(w, (QAbstractButton, QLabel, QLineEdit)):
            return w.text()
        if isinstance(w, (QPlainTextEdit, QTextEdit)):
            return w.toPlainText()
        if isinstance(w, QComboBox):
            return w.currentText()
        if isinstance(w, QGroupBox):
            return w.title()
        if isinstance(w, QAbstractSpinBox):
            return w.text()
        if w.isWindow() or isinstance(w, QDockWidget):
            return w.windowTitle()
        t = getattr(w, "text", None)
        if callable(t):
            v = t()
            if isinstance(v, str):
                return v
    except Exception:  # noqa: BLE001
        pass
    return ""


def items_of(w) -> list[str] | None:
    try:
        if isinstance(w, QComboBox):
            return [w.itemText(i) for i in range(w.count())]
        if isinstance(w, QListWidget):
            return [w.item(i).text() for i in range(w.count())]
        if isinstance(w, QTreeWidget):
            out = []

            def walk(it, depth):
                out.append("  " * depth + " | ".join(it.text(c) for c in range(w.columnCount())).rstrip(" |"))
                for i in range(it.childCount()):
                    walk(it.child(i), depth + 1)
            for i in range(w.topLevelItemCount()):
                walk(w.topLevelItem(i), 0)
            return out[:2000]
        if isinstance(w, QTableWidget):
            return [" | ".join((w.item(r, c).text() if w.item(r, c) else "") for c in range(w.columnCount()))
                    for r in range(min(w.rowCount(), 2000))]
        if isinstance(w, QTabWidget):
            return [w.tabText(i) for i in range(w.count())]
    except Exception:  # noqa: BLE001
        pass
    return None


def rect_of(w) -> list[int]:
    try:
        tl = w.mapToGlobal(w.rect().topLeft())
        return [tl.x(), tl.y(), w.width(), w.height()]
    except Exception:  # noqa: BLE001
        return []


def state(w, full: bool = True) -> dict:
    d = {"cls": type(w).__name__, "name": w.objectName(), "text": widget_text(w)[:20000],
         "visible": w.isVisible(), "enabled": w.isEnabled(), "rect": rect_of(w),
         "window": w.window().windowTitle() if w.window() is not None else "", "id": id(w)}
    if isinstance(w, QAbstractButton):
        d["checkable"], d["checked"] = w.isCheckable(), w.isChecked()
    if isinstance(w, (QSlider,)) or hasattr(w, "value") and isinstance(w, QAbstractSpinBox):
        try:
            d["value"] = w.value()
        except Exception:  # noqa: BLE001
            pass
    if full:
        its = items_of(w)
        if its is not None:
            d["items"] = its
        if isinstance(w, (QComboBox, QListWidget, QTabWidget)):
            d["current"] = w.currentIndex() if not isinstance(w, QListWidget) else w.currentRow()
        tip = w.toolTip()
        if tip:
            d["tooltip"] = tip[:500]
        if w.accessibleName():
            d["accessible"] = w.accessibleName()
    return d


def _all_widgets():
    return QApplication.allWidgets()


def find_all(ctx, sel) -> list[QWidget]:
    if isinstance(sel, QWidget):
        return [sel]
    if isinstance(sel, str):
        s = sel
        if s.startswith("#"):
            sel = {"name": s[1:]}
        elif s.startswith("@"):
            sel = {"attr": s[1:]}
        elif s[:1].isupper() and s.isidentifier():
            sel = {"cls": s}
        else:
            sel = {"text": s}
    sel = dict(sel or {})
    if "attr" in sel:
        obj = ctx.win
        for part in sel["attr"].split("."):
            obj = getattr(obj, part, None)
            if obj is None:
                return []
        if not isinstance(obj, QWidget):
            raise AutomationError(f"win.{sel['attr']} is not a widget ({type(obj).__name__})")
        return [obj]
    vis = sel.get("visible", True)
    root = None
    if sel.get("within") is not None:
        roots = find_all(ctx, sel["within"])
        if not roots:
            return []
        root = roots[0]
    out = []
    for w in (root.findChildren(QWidget) if root is not None else _all_widgets()):
        try:
            if vis and not w.isVisible():
                continue
            if "name" in sel and w.objectName() != sel["name"]:
                continue
            if "cls" in sel and sel["cls"] not in class_names(w):
                continue
            if "text" in sel and not _match_text(widget_text(w), sel["text"]):
                continue
            if "title" in sel and not _match_text(w.window().windowTitle(), sel["title"]):
                continue
            if "tooltip" in sel and not _match_text(w.toolTip(), sel["tooltip"]):
                continue
            out.append(w)
        except RuntimeError:          # deleted C++ object
            continue
    return out


def find(ctx, sel) -> QWidget:
    ws = find_all(ctx, sel)
    idx = (sel.get("index", 0) if isinstance(sel, dict) else 0) or 0
    if len(ws) <= idx:
        raise AutomationError(f"no widget matches {sel!r} ({len(ws)} found)")
    return ws[idx]


# ------------------------------------------------------------------------------------------ dialogs
def dialogs() -> list[QWidget]:
    out = []
    for w in QApplication.topLevelWidgets():
        try:
            if w.isVisible() and (isinstance(w, (QDialog, QMenu)) or w.isModal()):
                out.append(w)
        except RuntimeError:
            continue
    return out


def describe_dialog(w) -> dict:
    d = {"cls": type(w).__name__, "title": w.windowTitle(), "modal": w.isModal(), "id": id(w),
         "active_modal": QApplication.activeModalWidget() is w, "name": w.objectName()}
    if isinstance(w, QMessageBox):
        d["text"] = w.text()
        d["informative"] = w.informativeText()
        d["detailed"] = w.detailedText()
    if isinstance(w, QMenu):
        d["items"] = [clean(a.text()) for a in w.actions() if not a.isSeparator()]
    btns = [clean(b.text()) for b in w.findChildren(QAbstractButton) if b.isVisible() and b.text()]
    d["buttons"] = btns
    labels = [lb.text() for lb in w.findChildren(QLabel) if lb.isVisible() and lb.text()]
    d["labels"] = labels[:40]
    return d


def find_dialog(sel=None) -> QWidget:
    ds = dialogs()
    if not ds:
        raise AutomationError("no dialog is open")
    if not sel or sel == "active":
        m = QApplication.activeModalWidget()
        return m if m is not None and m.isVisible() else ds[-1]
    if isinstance(sel, str):
        sel = {"title": sel}
    for w in reversed(ds):
        if "title" in sel and not _match_text(w.windowTitle(), sel["title"]):
            continue
        if "cls" in sel and sel["cls"] not in class_names(w):
            continue
        if "text" in sel and not (isinstance(w, QMessageBox) and _match_text(w.text(), sel["text"])):
            continue
        return w
    raise AutomationError(f"no dialog matches {sel!r}; open: {[d.windowTitle() for d in ds]}")


__all__ = ["QRect", "clean", "describe_dialog", "dialogs", "find", "find_all", "find_dialog", "items_of",
           "state", "widget_text"]
