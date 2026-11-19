"""Hide the stale dock tab bars that QMainWindow.restoreState() leaves behind.

Qt keeps the QTabBar objects of the dock-tab groups that existed before a restoreState() and, when the
state is restored before the window is shown (the workbench layouts do that), some of them stay visible
at old positions: a second "Toolbox | Databases" row in the left panel, or a "Solution Explorer | AI Chat"
bar showing through transparent parts of the editors. A tab bar that Qt really uses always sits directly
above or below the dock of its current tab; every other visible tab bar of the main window is hidden.
"""
from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, QTimer
from PyQt6.QtWidgets import QDockWidget, QTabBar

_SLACK = 8


def _attached(win, bar: QTabBar) -> bool:
    if bar.count() == 0:
        return False
    title = bar.tabText(bar.currentIndex() if bar.currentIndex() >= 0 else 0)
    g = bar.geometry()
    for d in win.findChildren(QDockWidget):
        if d.parent() is not win or not d.isVisible() or d.isFloating() or d.windowTitle() != title:
            continue
        r = d.geometry()
        inside_x = g.left() >= r.left() - _SLACK and g.left() <= r.right() + _SLACK
        inside_y = g.top() >= r.top() - _SLACK and g.top() <= r.bottom() + _SLACK
        below_or_above = abs(g.top() - r.bottom()) <= _SLACK or abs(g.bottom() - r.top()) <= _SLACK
        beside = abs(g.left() - r.right()) <= _SLACK or abs(g.right() - r.left()) <= _SLACK  # West/East tabs
        if (inside_x and below_or_above) or (inside_y and beside):
            return True
    return False


def hide_stale_tabbars(win) -> int:
    """Hide the main window's visible dock tab bars that are not attached to their dock. Returns the count."""
    if not win.isVisible():
        return 0
    n = 0
    for bar in win.findChildren(QTabBar):
        if bar.parent() is win and bar.isVisible() and not _attached(win, bar):
            bar.hide()
            n += 1
    return n


class _ShowWatcher(QObject):
    def __init__(self, win):
        super().__init__(win)
        self.win = win

    def eventFilter(self, obj, ev):
        if obj is self.win and ev.type() == QEvent.Type.Show:
            schedule(self.win)
        return False


def schedule(win) -> None:
    for ms in (0, 250):
        QTimer.singleShot(ms, lambda: hide_stale_tabbars(win))


def install(win) -> None:
    orig = win.restoreState

    def restore_state(*args, **kw):
        ok = orig(*args, **kw)
        schedule(win)
        return ok
    win.restoreState = restore_state
    win._dock_tabbar_watcher = _ShowWatcher(win)
    win.installEventFilter(win._dock_tabbar_watcher)
