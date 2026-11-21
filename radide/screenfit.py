"""Keep every window of the IDE on the screen: small laptops (1366x768, 1280x720), netbooks
(1024x600) and big monitors with Windows display scaling (150 % / 175 % of 1920x1080).

install(app) adds one application-wide event filter.  When any top-level window or dialog is
shown it

* makes a dialog / tool window whose content cannot shrink to the screen scrollable (the content
  goes into a QScrollArea, the OK / Cancel row stays visible below it) - only when it is needed;
* lowers fixed / minimum sizes that are larger than the screen;
* shrinks the window to the available area of its screen (taskbar excluded, window frame
  included) and moves it fully on-screen - this also repairs a geometry that was saved on a big
  monitor and restored on a small one, or a window placed partly off-screen;
* opens the main window maximized when its default size does not fit.

The docked tool windows of a QMainWindow get small minimum heights on small screens, so that the
main window itself can be made as small as the screen (they used to need ~790 px of height).

On a screen that is large enough nothing is changed (no window is touched that already fits).
RADIDE_NO_SCREENFIT=1 in the environment turns all of it off (comparisons, troubleshooting).
fit_window(w) / wrap_in_scroll(w) can also be called directly.
"""
from __future__ import annotations

import os
import sys

from PyQt6.QtCore import QEvent, QMargins, QObject, QRect, Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (QAbstractButton, QApplication, QBoxLayout, QComboBox,
                             QDialogButtonBox, QDockWidget, QFormLayout, QFrame, QGridLayout,
                             QLayout, QMainWindow, QMenu, QScrollArea, QTabBar, QWidget, QWizard)

ENABLED = os.environ.get("RADIDE_NO_SCREENFIT", "") not in ("1", "true", "yes")
SMALL_W, SMALL_H = 1400, 900          # logical px: below this the screen counts as "small"
_SKIP_TYPES = (Qt.WindowType.Popup, Qt.WindowType.ToolTip, Qt.WindowType.SplashScreen,
               Qt.WindowType.Desktop, Qt.WindowType.Drawer)
_WRAPPED = "_rad_screenfit_wrapped"


# ----------------------------------------------------------------------------- geometry helpers
def screen_for(w: QWidget):
    """The screen the window is (or will be) shown on: its parent window's, else the screen under
    its centre, else the primary screen."""
    par = w.parentWidget()
    if par is not None and not w.isVisible():
        par = par.window()
        if par.isVisible() and par.screen() is not None:
            return par.screen()
    scr = QGuiApplication.screenAt(w.geometry().center()) if w.testAttribute(Qt.WidgetAttribute.WA_Moved) \
        or w.isVisible() else None
    return scr or w.screen() or QGuiApplication.primaryScreen()


def is_small_screen(screen=None) -> bool:
    screen = screen or QGuiApplication.primaryScreen()
    if screen is None:
        return False
    av = screen.availableGeometry()
    return av.width() < SMALL_W or av.height() < SMALL_H


def frame_margins(w: QWidget) -> QMargins:
    """Window frame (title bar + borders) around the client area; an estimate before the window
    is first shown (Windows 10/11 title bar ~31 logical px)."""
    fg, g = w.frameGeometry(), w.geometry()
    if fg != g and w.isVisible():
        return QMargins(g.left() - fg.left(), g.top() - fg.top(), fg.right() - g.right(), fg.bottom() - g.bottom())
    if QGuiApplication.platformName() == "offscreen":
        return QMargins(2, 2, 2, 2)
    if (w.windowFlags() & Qt.WindowType.FramelessWindowHint) or sys.platform != "win32":
        return QMargins(0, 0 if w.windowFlags() & Qt.WindowType.FramelessWindowHint else 28, 0, 0)
    return QMargins(1, 31, 1, 1)


def client_area(w: QWidget) -> QRect:
    """The largest client rectangle the window may have on its screen."""
    scr = screen_for(w)
    av = scr.availableGeometry() if scr is not None else QRect(0, 0, 1280, 720)
    m = frame_margins(w)
    return av.adjusted(m.left(), m.top(), -m.right(), -m.bottom())


def needed_size(w: QWidget):
    """The smallest size the window's layout allows."""
    s = w.minimumSizeHint()
    nw, nh = max(s.width(), w.minimumWidth()), max(s.height(), w.minimumHeight())
    lay = w.layout()
    if lay is not None:
        lay.activate()
        t = lay.totalMinimumSize()
        nw, nh = max(nw, t.width()), max(nh, t.height())
    return nw, nh


# ----------------------------------------------------------------------------- scroll wrapping
def _is_button_row(item) -> bool:
    """The OK / Cancel row of a dialog: a QDialogButtonBox, or a row of buttons and spacers."""
    wdg = item.widget()
    if wdg is not None:
        return isinstance(wdg, QDialogButtonBox)
    lay = item.layout()
    if isinstance(lay, QBoxLayout) and lay.direction() in (QBoxLayout.Direction.LeftToRight,
                                                           QBoxLayout.Direction.RightToLeft):
        kinds = []
        for i in range(lay.count()):
            it = lay.itemAt(i)
            if it.widget() is not None:
                kinds.append(isinstance(it.widget(), (QAbstractButton, QDialogButtonBox)))
            elif it.layout() is not None:
                return False
        return bool(kinds) and all(kinds)
    return False


def _relax(w: QWidget) -> None:
    """Cheap width savers before scrolling: combo boxes stop sizing to their longest item and
    long form rows wrap their field below the label."""
    for c in w.findChildren(QComboBox):
        if c.sizeAdjustPolicy() == QComboBox.SizeAdjustPolicy.AdjustToContents:
            c.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            c.setMinimumContentsLength(max(c.minimumContentsLength(), 12))
    for f in w.findChildren(QFormLayout):
        if f.rowWrapPolicy() == QFormLayout.RowWrapPolicy.DontWrapRows:
            f.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)


def wrap_in_scroll(w: QWidget, max_width: int | None = None) -> bool:
    """Move the content of w's layout into a QScrollArea (the dialog's button row stays outside).
    Works with box, grid and form layouts; returns False when w was left unchanged."""
    lay = w.layout()
    if lay is None or w.property(_WRAPPED) or lay.count() == 0:
        return False
    if isinstance(w, (QMainWindow, QWizard, QScrollArea)):
        return False
    inner = QWidget()
    inner.setObjectName("rad_screenfit_content")
    keep = []                                    # items that stay outside the scroll area
    if isinstance(lay, QBoxLayout):
        items = [(lay.itemAt(i), lay.stretch(i)) for i in range(lay.count())]
        vertical = lay.direction() in (QBoxLayout.Direction.TopToBottom, QBoxLayout.Direction.BottomToTop)
        if vertical and len(items) > 1 and _is_button_row(items[-1][0]):
            last = items[-1][0]
            if max_width is None or last.minimumSize().width() <= max_width:
                keep = [last]                    # (a row wider than the screen scrolls with the rest)
        new = QBoxLayout(lay.direction())
        for _ in range(lay.count()):
            lay.takeAt(0)
        for it, st in items:
            if any(it is k for k in keep):
                continue
            new.addItem(it)
            new.setStretch(new.count() - 1, st)
    elif isinstance(lay, QGridLayout):
        pos = [lay.getItemPosition(i) for i in range(lay.count())]
        items = [lay.itemAt(i) for i in range(lay.count())]
        new = QGridLayout()
        for r in range(lay.rowCount()):
            new.setRowStretch(r, lay.rowStretch(r))
            new.setRowMinimumHeight(r, lay.rowMinimumHeight(r))
            lay.setRowStretch(r, 0)
            lay.setRowMinimumHeight(r, 0)
        for c in range(lay.columnCount()):
            new.setColumnStretch(c, lay.columnStretch(c))
            new.setColumnMinimumWidth(c, lay.columnMinimumWidth(c))
            lay.setColumnStretch(c, 0)
            lay.setColumnMinimumWidth(c, 0)
        new.setHorizontalSpacing(lay.horizontalSpacing())
        new.setVerticalSpacing(lay.verticalSpacing())
        for _ in range(lay.count()):
            lay.takeAt(0)
        for it, (r, c, rs, cs) in zip(items, pos):
            new.addItem(it, r, c, rs, cs)
    elif isinstance(lay, QFormLayout):
        pos = [lay.getItemPosition(i) for i in range(lay.count())]
        items = [lay.itemAt(i) for i in range(lay.count())]
        new = QFormLayout()
        new.setFieldGrowthPolicy(lay.fieldGrowthPolicy())
        new.setLabelAlignment(lay.labelAlignment())
        new.setFormAlignment(lay.formAlignment())
        new.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        new.setHorizontalSpacing(lay.horizontalSpacing())
        new.setVerticalSpacing(lay.verticalSpacing())
        for _ in range(lay.count()):
            lay.takeAt(0)
        while lay.rowCount():
            lay.removeRow(0)
        for it, (r, role) in zip(items, pos):
            new.setItem(r, role, it)
    else:
        return False
    if not isinstance(lay, (QGridLayout, QFormLayout)):
        new.setSpacing(lay.spacing())
    new.setContentsMargins(0, 0, 0, 0)
    inner.setLayout(new)                         # reparents every widget of the moved items
    sa = QScrollArea(w)
    sa.setObjectName("rad_screenfit_scroll")
    sa.setFrameShape(QFrame.Shape.NoFrame)
    sa.setWidgetResizable(True)
    sa.setWidget(inner)
    sa.setSizeAdjustPolicy(QScrollArea.SizeAdjustPolicy.AdjustToContents)
    if isinstance(lay, QBoxLayout):
        lay.addWidget(sa, 1)
        for it in keep:
            lay.addItem(it)
    elif isinstance(lay, QGridLayout):
        lay.addWidget(sa, 0, 0)
    else:
        lay.addRow(sa)
    lay.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
    sa.show()
    inner.show()
    w.setProperty(_WRAPPED, True)
    lay.invalidate()
    return True


def _wrap_wizard(wz: QWizard, area: QRect) -> None:
    for pid in wz.pageIds():
        page = wz.page(pid)
        if page is not None and page.layout() is not None:
            nw, nh = needed_size(page)
            if nw > area.width() - 40 or nh > area.height() - 160:
                _relax(page)
                wrap_in_scroll(page, area.width() - 40)


# ----------------------------------------------------------------------------- fitting
def fit_window(w: QWidget, wrap: bool = True) -> None:
    """Shrink and move one top-level window so that it lies fully inside its screen."""
    if not w.isWindow() or isinstance(w, QMenu) or w.windowType() in _SKIP_TYPES:
        return
    if w.windowState() & (Qt.WindowState.WindowMaximized | Qt.WindowState.WindowFullScreen
                          | Qt.WindowState.WindowMinimized):
        return
    if w.property("rad_screenfit_off"):
        return
    area = client_area(w)
    if area.width() < 200 or area.height() < 150:
        return
    g0 = w.geometry()                           # the size the window asked for (wrapping may change it)
    if wrap and not isinstance(w, QMainWindow):
        nw, nh = needed_size(w)
        if nw > area.width() or nh > area.height():
            _relax(w)
            if isinstance(w, QWizard):
                _wrap_wizard(w, area)
            else:
                nw, nh = needed_size(w)
                if nw > area.width() or nh > area.height():
                    wrap_in_scroll(w, area.width())
    if isinstance(w, QMainWindow):
        fit_docks(w)
    if w.layout() is not None:                  # minimums of the new content (scroll area, docks)
        w.layout().invalidate()
        w.layout().activate()
    # explicit minimums / fixed sizes larger than the screen (not the main window's: its minimum
    # comes from the docks and stays layout-driven)
    if not isinstance(w, QMainWindow):
        if w.minimumWidth() > area.width():
            w.setMinimumWidth(area.width())
        if w.minimumHeight() > area.height():
            w.setMinimumHeight(area.height())
    if w.maximumWidth() < w.minimumWidth():
        w.setMaximumWidth(w.minimumWidth())
    if w.maximumHeight() < w.minimumHeight():
        w.setMaximumHeight(w.minimumHeight())
    g = w.geometry()
    if g.size() != g0.size():
        g = QRect(g.topLeft(), g0.size().expandedTo(w.minimumSize()))
    big = g.width() > area.width() or g.height() > area.height()
    if isinstance(w, QMainWindow) and big and not w.property("rad_screenfit_no_maximize"):
        w.setGeometry(area)
        w.setWindowState(w.windowState() | Qt.WindowState.WindowMaximized)
        return
    width, height = min(g.width(), area.width()), min(g.height(), area.height())
    if not w.isVisible() and not w.testAttribute(Qt.WidgetAttribute.WA_Moved):
        if not big:
            return                          # not placed yet and it fits: the window system centres it
        g = QRect(area.left() + (area.width() - width) // 2, area.top() + (area.height() - height) // 2,
                  width, height)
        w.setGeometry(g)
        return
    x = min(max(g.x(), area.left()), area.right() + 1 - width)
    y = min(max(g.y(), area.top()), area.bottom() + 1 - height)
    if (x, y, width, height) != (g.x(), g.y(), g.width(), g.height()):
        w.setGeometry(x, y, width, height)


def dock_min_height(w: QWidget) -> int:
    """Minimum content height of a docked tool window on a small screen: about four text lines."""
    return max(60, w.fontMetrics().height() * 4 + 24)


def fit_dock(d: QDockWidget) -> None:
    """On a small screen a docked tool window may be made as low as a few lines (its content
    scrolls or clips) instead of forcing the main window taller than the screen."""
    content = d.widget()
    if content is None or d.isFloating() or content.property("rad_screenfit_dock"):
        return
    mw = d.parentWidget()
    if not isinstance(mw, QMainWindow) or not is_small_screen(mw.screen()):
        return
    cap = dock_min_height(content)
    if needed_size(content)[1] > cap:
        content.setMinimumHeight(cap)
    content.setProperty("rad_screenfit_dock", True)


def fit_docks(mw: QMainWindow) -> None:
    for d in mw.findChildren(QDockWidget):
        if d.parentWidget() is mw:
            fit_dock(d)
    for tb in mw.findChildren(QTabBar):
        fit_dock_tabbar(tb)


def fit_dock_tabbar(tb: QTabBar) -> None:
    """The tab bar of a group of docked tool windows on a small screen: whole titles and scroll
    arrows instead of "P...", "A..." when many tool windows share the group."""
    mw = tb.parentWidget()
    if not isinstance(mw, QMainWindow) or tb.property("rad_screenfit_tabs") or not is_small_screen(mw.screen()):
        return
    tb.setElideMode(Qt.TextElideMode.ElideNone)
    tb.setUsesScrollButtons(True)
    tb.setProperty("rad_screenfit_tabs", True)


def apply_small_screen_layout(mw: QMainWindow) -> None:
    """First run on a small screen (no saved layout): Solution Explorer and Properties share one
    tab group when the screen is too low to stack them, and the Output panel is lower."""
    scr = mw.screen() or QGuiApplication.primaryScreen()
    if not ENABLED or scr is None or not is_small_screen(scr):
        return
    av = scr.availableGeometry()
    sol, props = getattr(mw, "dock_solution", None), getattr(mw, "dock_props", None)
    if av.height() < 700 and sol is not None and props is not None and not sol.isFloating() \
            and not props.isFloating() and mw.dockWidgetArea(sol) == mw.dockWidgetArea(props):
        # Qt cannot tabify a dock that already sits in another tab group: take the whole
        # Solution Explorer group out first, then add it to the Properties group
        group = [sol] + [d for d in mw.tabifiedDockWidgets(sol) if d is not props]
        visible = {id(d): d.isVisible() for d in group}
        for d in group:
            mw.removeDockWidget(d)
        for d in group:
            mw.tabifyDockWidget(props, d)
            d.setVisible(visible[id(d)])
        props.raise_()
        mw.resizeDocks([props], [max(260, min(340, int(mw.width() * 0.26)))], Qt.Orientation.Horizontal)
    out = getattr(mw, "dock_output", None)
    if out is not None and not out.isFloating():
        mw.resizeDocks([out], [max(90, min(150, int(av.height() * 0.17)))], Qt.Orientation.Vertical)


# ----------------------------------------------------------------------------- event filter
class _ScreenFit(QObject):
    def eventFilter(self, obj, ev):
        t = ev.type()
        if t == QEvent.Type.Show:
            try:
                if isinstance(obj, QWidget):
                    if obj.isWindow():
                        fit_window(obj)
                    elif isinstance(obj, QDockWidget):
                        fit_dock(obj)
                    elif isinstance(obj, QTabBar):
                        fit_dock_tabbar(obj)
            except RuntimeError:          # a window being destroyed
                pass
            except Exception as e:  # noqa: BLE001 - never break showing a window
                sys.__stderr__ and sys.__stderr__.write(f"[screenfit] {e}\n")
        return False


_FILTER: _ScreenFit | None = None


def install(app: QApplication | None = None) -> None:
    """Install the screen-fit filter once for the whole application."""
    global _FILTER
    app = app or QApplication.instance()
    if app is None or _FILTER is not None or not ENABLED:
        return
    _FILTER = _ScreenFit(app)
    app.installEventFilter(_FILTER)


def refit_later(w: QWidget) -> None:
    QTimer.singleShot(0, lambda: fit_window(w))


__all__ = ["install", "fit_window", "wrap_in_scroll", "fit_dock", "fit_docks", "is_small_screen",
           "apply_small_screen_layout", "client_area", "needed_size"]
