"""Designer zoom commands: View > Zoom (In / Out / 100% / levels) and a zoom box in the status bar that
follows the current form designer (or the game scene editor, which has its own zoom).
Ctrl+mouse wheel over a designer zooms too (radide/designer_zoom.py)."""
from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QComboBox

from ..designer_zoom import LEVELS, set_zoom, step


def _target(win):
    """('form', DesignerView) | ('scene', scene editor with a zoom) | (None, None)."""
    d = win._current_designer() if hasattr(win, "_current_designer") else None
    if d is not None:
        return "form", d
    tabs = getattr(win, "tabs", None)
    w = tabs.currentWidget() if tabs is not None else None
    for obj in (w, getattr(w, "canvas", None), getattr(w, "view", None)):
        if obj is not None and callable(getattr(obj, "set_zoom", None)) and hasattr(obj, "zoom"):
            return "scene", obj
    return None, None


def _current_zoom(obj) -> float:
    z = getattr(obj, "zoom", 1.0)
    z = z() if callable(z) else z
    try:
        return float(z)
    except (TypeError, ValueError):
        return 1.0


def install(win) -> None:
    box = QComboBox()
    box.setEditable(True)
    box.setToolTip("Designer zoom (Ctrl+mouse wheel)")
    box.addItems([f"{lv}%" for lv in LEVELS])
    box.setCurrentText("100%")
    box.setMinimumContentsLength(5)
    box.setVisible(False)
    win.statusBar().addPermanentWidget(box)
    win.designer_zoom_box = box
    busy = [False]

    def show_zoom(z: float) -> None:
        busy[0] = True
        box.setCurrentText(f"{round(z * 100)}%")
        busy[0] = False

    def sync(*_a) -> None:
        kind, obj = _target(win)
        box.setVisible(kind is not None)
        if kind == "form":
            obj.zoomChangedHook = show_zoom
        if obj is not None:
            show_zoom(_current_zoom(obj))

    def apply(text: str) -> None:
        if busy[0]:
            return
        try:
            z = float(text.strip().rstrip("%").strip()) / 100
        except ValueError:
            return
        kind, obj = _target(win)
        if kind == "form":
            set_zoom(obj, z)
        elif kind == "scene":
            obj.set_zoom(z)

    box.currentTextChanged.connect(lambda t: apply(t) if t.strip().endswith("%") or box.view().isVisible() else None)
    box.lineEdit().returnPressed.connect(lambda: apply(box.currentText()))

    def zoom_by(direction: int) -> None:
        kind, obj = _target(win)
        if kind == "form":
            step(obj, direction)
        elif kind == "scene":
            cur = round(_current_zoom(obj) * 100)
            lv = next((x for x in LEVELS if x > cur), LEVELS[-1]) if direction > 0 else \
                next((x for x in reversed(LEVELS) if x < cur), LEVELS[0])
            obj.set_zoom(lv / 100)
        sync()

    def zoom_to(z: float) -> None:
        kind, obj = _target(win)
        if kind == "form":
            set_zoom(obj, z)
        elif kind == "scene":
            obj.set_zoom(z)
        sync()

    view_menu = None
    for act in win.menuBar().actions():
        if act.text().replace("&", "") == "View" and act.menu() is not None:
            view_menu = act.menu()
            break
    if view_menu is not None:
        view_menu.addSeparator()
        zm = view_menu.addMenu("&Zoom")
        zm.addAction("Zoom &In  (Ctrl+Wheel)", lambda: zoom_by(1))
        zm.addAction("Zoom &Out", lambda: zoom_by(-1))
        zm.addAction("&100%", lambda: zoom_to(1.0))
        zm.addSeparator()
        for lv in (50, 75, 150, 200, 300, 400):
            zm.addAction(f"{lv}%", lambda _=False, z=lv / 100: zoom_to(z))
        win.menu_designer_zoom = zm
    tabs = getattr(win, "tabs", None)
    if tabs is not None:
        tabs.currentChanged.connect(lambda _i: QTimer.singleShot(0, sync))
    win.designer_zoom_sync = sync
