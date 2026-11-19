"""More room for the Design View of web pages (CONTRACTS 8.2).

The Design View has its own side panel (Toolbox / Layers / CSS / Attributes), so with the IDE's dock
columns on both sides (Databases / Toolbox on the left, Solution Explorer + Properties on the right) the page
canvas was cramped. The first time a Design View tab becomes active in a window, the side dock columns are
narrowed (Visual Studio layout only; the Code / Agent layouts manage their own side bars). After that the
user's own widths are kept.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QDockWidget

LEFT_WIDTH = 180          # Databases / Toolbox column
RIGHT_WIDTH = 240         # Solution Explorer / Properties column
EDITOR_SHARE = 0.66       # narrow the columns only while the editor area is below this share of the window


def _is_design_view(w) -> bool:
    try:
        from ..web_site.design import DesignView
    except Exception:  # noqa: BLE001 - QtWebEngine missing: no Design View at all
        return False
    return isinstance(w, DesignView)


def column(win, area) -> list[QDockWidget]:
    """Visible, docked dock widgets of one side area (tabified docks hidden behind a tab are not visible)."""
    return [d for d in win.findChildren(QDockWidget)
            if d.parent() is win and d.isVisible() and not d.isFloating() and win.dockWidgetArea(d) == area]


def make_room(win, force: bool = False) -> bool:
    """Narrow the side dock columns so the Design View gets the room. True when something changed."""
    wb = getattr(win, "workbench", None)
    if wb is not None and getattr(wb, "mode", "vs") != "vs":
        return False
    if not win.isVisible() or win.isMinimized():
        return False
    if not force and win.tabs.width() >= int(win.width() * EDITOR_SHARE):
        return False
    changed = False
    preview = getattr(win, "dock_web_preview", None)
    for area, width in ((Qt.DockWidgetArea.LeftDockWidgetArea, LEFT_WIDTH),
                        (Qt.DockWidgetArea.RightDockWidgetArea, RIGHT_WIDTH)):
        docks = column(win, area)
        if not docks or (preview is not None and preview in docks):    # the live Preview wants its width
            continue
        if max(d.width() for d in docks) > width + 4:
            win.resizeDocks([docks[0]], [width], Qt.Orientation.Horizontal)
            changed = True
    return changed


def install(win) -> None:
    def on_tab(_i=None):
        if getattr(win, "_rad_design_room_done", False) or not _is_design_view(win.tabs.currentWidget()):
            return
        QTimer.singleShot(0, apply)

    def apply():
        if getattr(win, "_rad_design_room_done", False) or not win.isVisible() or \
                not _is_design_view(win.tabs.currentWidget()):
            return
        win._rad_design_room_done = True           # once per window: afterwards the user's widths win
        make_room(win)
    win.tabs.currentChanged.connect(on_tab)
