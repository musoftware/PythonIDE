"""Accessibility (round 7): names for screen readers, keyboard-only navigation and a contrast check.

* Every widget is given an accessible name / description when it is polished (an application event filter),
  if it has none: toolbars and docks by their title, icon-only tool buttons by their action text or tooltip,
  editors by their buddy label / placeholder / tooltip, item views by their dock, controls on the designed form
  by their control name ("rad_<Name>" widgets of radide/preview.py), the Toolbox and the Properties grid.
* Keyboard: **F6 / Shift+F6** move the focus between the editor area and the visible docks (like Visual
  Studio); **Ctrl+F6** goes back to the editor; the menus keep their Alt mnemonics (checked by the test).
* **Tools > Accessibility Check...**: WCAG contrast ratios of the current theme's colour pairs (and of all
  themes) + focusable widgets of the main window without an accessible name.
* Windows "High contrast" on (SPI_GETHIGHCONTRAST) -> the High Contrast theme is applied at start-up unless
  QSettings "accessibility/follow_high_contrast" is false.
"""
from __future__ import annotations

import sys

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer
from PyQt6.QtGui import QColor, QKeySequence, QShortcut
from PyQt6.QtWidgets import (QAbstractButton, QAbstractItemView, QAbstractSpinBox, QApplication, QComboBox,
                             QDialog, QDialogButtonBox, QDockWidget, QLabel, QLineEdit, QPlainTextEdit, QTabWidget,
                             QTextBrowser, QTextEdit, QToolBar, QToolButton, QVBoxLayout, QWidget)

# colour pairs (foreground token, background token, minimum WCAG ratio): 4.5 = normal text, 3.0 = large / UI
CONTRAST_PAIRS = [("text", "base", 4.5), ("text", "window", 4.5), ("button_text", "button", 4.5),
                  ("menu_text", "menu", 4.5), ("menu_sel_text", "menu_sel", 4.5),
                  ("highlight_text", "highlight", 4.5), ("tab_text", "tab", 4.5), ("tab_sel_text", "tab_sel", 4.5),
                  ("status_text", "status", 4.5), ("bar_text", "toolbar1", 4.5), ("title_text", "title1", 4.5),
                  ("header_text", "header", 4.5), ("tooltip_text", "tooltip", 4.5), ("muted", "base", 4.5),
                  ("link", "base", 4.5), ("error", "base", 4.5), ("success", "base", 4.5),
                  ("disabled", "base", 3.0), ("placeholder", "base", 3.0)]


def _lum(c: str) -> float:
    q = QColor(c)

    def ch(v: float) -> float:
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(q.red()) + 0.7152 * ch(q.green()) + 0.0722 * ch(q.blue())


def contrast(fg: str, bg: str) -> float:
    a, b = sorted((_lum(fg), _lum(bg)), reverse=True)
    return round((a + 0.05) / (b + 0.05), 2)


def contrast_report(theme_dict: dict | None = None) -> list[tuple[str, str, float, float, bool]]:
    """[(fg token, bg token, ratio, required, ok)] for a theme (default: the current one)."""
    from .. import theme
    t = theme_dict or theme.current()
    out = []
    for fg, bg, need in CONTRAST_PAIRS:
        if fg in t and bg in t:
            r = contrast(t[fg], t[bg])
            out.append((fg, bg, r, need, r >= need))
    return out


def windows_high_contrast() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        class HIGHCONTRAST(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwFlags", ctypes.c_uint), ("lpszDefaultScheme", ctypes.c_wchar_p)]
        hc = HIGHCONTRAST()
        hc.cbSize = ctypes.sizeof(HIGHCONTRAST)
        if ctypes.windll.user32.SystemParametersInfoW(0x0042, hc.cbSize, ctypes.byref(hc), 0):   # SPI_GETHIGHCONTRAST
            return bool(hc.dwFlags & 1)                                                      # HCF_HIGHCONTRASTON
    except Exception:  # noqa: BLE001
        pass
    return False


# ------------------------------------------------------------------------------------------ naming
def _clean(text: str) -> str:
    return (text or "").replace("&&", "\0").replace("&", "").replace("\0", "&").split("\t")[0].strip(" .")


def _dock_of(w: QWidget) -> QDockWidget | None:
    p = w.parentWidget()
    while p is not None:
        if isinstance(p, QDockWidget):
            return p
        p = p.parentWidget()
    return None


def suggested_name(w: QWidget) -> str:
    """A name for a widget that has none ("" = leave it to Qt, e.g. buttons with text)."""
    from ..properties import PropertiesPanel
    from ..toolbox import Toolbox
    on = w.objectName()
    if on.startswith("rad_") and on != "rad_page":          # a control on the designed form (preview.py)
        return on[4:]
    if isinstance(w, QDockWidget):
        return _clean(w.windowTitle())
    if isinstance(w, QToolBar):
        d = _dock_of(w)
        base = _clean(w.windowTitle()) or (on if on and on != "Toolbar" else "") or \
            (_clean(d.windowTitle()) if d is not None else "")
        return (base or "Tools") + " toolbar"
    if on == "qt_toolbar_ext_button":
        return "More toolbar items"
    if isinstance(w, Toolbox):
        return "Toolbox"
    if isinstance(w, PropertiesPanel):
        return "Properties"
    if isinstance(w, QAbstractButton):
        if w.text().strip():
            return ""
        if isinstance(w, QToolButton) and w.defaultAction() is not None:
            a = w.defaultAction()
            return _clean(a.text() or a.toolTip() or a.iconText())
        return _clean(w.toolTip()) or _clean(w.statusTip())
    if isinstance(w, (QLineEdit, QComboBox, QAbstractSpinBox, QPlainTextEdit, QTextEdit)):
        if isinstance(w, QLineEdit) and isinstance(w.parentWidget(), (QComboBox, QAbstractSpinBox)):
            outer = w.parentWidget()                      # the inner editor of an editable combo / spin box
            return outer.accessibleName() or suggested_name(outer)
        lab = _buddy_label(w)
        if lab:
            return lab
        ph = w.placeholderText() if hasattr(w, "placeholderText") else ""
        if ph:
            return _clean(ph)
        if w.toolTip():
            return _clean(w.toolTip())
        if isinstance(w, QComboBox) and w.parentWidget() is not None and \
                w.parentWidget().inherits("PropertiesPanel"):
            return "Object"                               # the Properties window's object selector
        d = _dock_of(w)
        if d is not None and isinstance(w, (QComboBox, QAbstractSpinBox)):
            return f"{_clean(d.windowTitle())} {'choice' if isinstance(w, QComboBox) else 'value'}"
    if isinstance(w, (QAbstractItemView, QPlainTextEdit, QTextBrowser, QTabWidget)):
        if isinstance(w.parentWidget(), QWidget) and w.parentWidget().inherits("PropertiesPanel"):
            return "Properties grid"
        d = _dock_of(w)
        if d is not None:
            return _clean(d.windowTitle())
        if w.toolTip():
            return _clean(w.toolTip())
    return ""


def _buddy_label(w: QWidget) -> str:
    # a buddy label sits next to its field (same form / dialog page): search a few levels up, not the
    # whole main window - findChildren over thousands of IDE widgets for every new editor (e.g. each
    # Properties grid refresh) cost ~30 ms per editor
    top, win = w, w.window()
    vp = w.parentWidget()
    if vp is not None and isinstance(vp.parentWidget(), QAbstractItemView):
        return ""       # a cell editor of a grid (Properties window): no label is its buddy - and each
                        # search walked every other cell widget of the grid (~30 ms per new editor)
    for _ in range(3):
        if top is win or top.parentWidget() is None or isinstance(top, QDockWidget):
            break
        top = top.parentWidget()
    for lab in top.findChildren(QLabel):
        try:
            if lab.buddy() is w and lab.text():
                return _clean(lab.text()).rstrip(":")
        except RuntimeError:
            continue
    return ""


def annotate(w: QWidget) -> bool:
    """Give *w* an accessible name (and a description for designer controls) if it has none."""
    try:
        if w.accessibleName():
            return False
        name = suggested_name(w)
    except RuntimeError:
        return False
    except Exception:  # noqa: BLE001 - never break a widget
        return False
    if not name:
        return False
    w.setAccessibleName(name)
    on = w.objectName()
    if on.startswith("rad_") and not w.accessibleDescription():
        w.setAccessibleDescription(f"{w.metaObject().className()} control {name} on the designed form")
    elif isinstance(w, QDockWidget) and not w.accessibleDescription():
        w.setAccessibleDescription(f"{name} window - F6 / Shift+F6 move between windows")
    return True


def annotate_tree(root: QWidget) -> int:
    n = int(annotate(root))
    for w in root.findChildren(QWidget):
        n += annotate(w)
    return n


class _Polisher(QObject):
    """Names widgets as they appear (Polish / Show), cheaply: one check per widget."""

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t in (QEvent.Type.Polish, QEvent.Type.Show) and isinstance(obj, QWidget):
            annotate(obj)
        return False


# ------------------------------------------------------------------------------------------ keyboard
def focus_regions(win) -> list[QWidget]:
    """Editor area first, then the visible, non-floating docks in screen order (top-left first)."""
    regions = [win.tabs] if getattr(win, "tabs", None) is not None and win.tabs.isVisible() else []
    docks = [d for d in win.findChildren(QDockWidget) if d.isVisible() and d.widget() is not None and
             not d.visibleRegion().isEmpty()]
    docks.sort(key=lambda d: (d.mapTo(win, d.rect().topLeft()).x() // 40, d.mapTo(win, d.rect().topLeft()).y()))
    return regions + docks


def _region_of(win, w: QWidget | None, regions) -> int:
    while w is not None:
        if w in regions:
            return regions.index(w)
        w = w.parentWidget()
    return -1


def _focus_into(region: QWidget) -> None:
    target = region
    if isinstance(region, QDockWidget):
        region.raise_()
        target = region.widget()
    elif isinstance(region, QTabWidget) and region.currentWidget() is not None:
        target = region.currentWidget()
    fw = target if target.focusPolicy() != Qt.FocusPolicy.NoFocus else None
    if fw is None:
        fw = next((c for c in target.findChildren(QWidget) if c.isVisible() and c.isEnabled() and
                   c.focusPolicy() & Qt.FocusPolicy.TabFocus), None)
    (fw or target).setFocus(Qt.FocusReason.TabFocusReason)


def cycle_focus(win, step: int = 1) -> QWidget | None:
    regions = focus_regions(win)
    if not regions:
        return None
    cur = _region_of(win, QApplication.focusWidget(), regions)
    nxt = regions[(cur + step) % len(regions)] if cur >= 0 else regions[0]
    _focus_into(nxt)
    title = nxt.windowTitle() if isinstance(nxt, QDockWidget) else "Editor"
    try:
        win.statusBar().showMessage(f"Focus: {_clean(title)}", 2000)
    except Exception:  # noqa: BLE001
        pass
    return nxt


# ------------------------------------------------------------------------------------------ check dialog
def unnamed_focusable(root: QWidget) -> list[QWidget]:
    out = []
    for w in root.findChildren(QWidget):
        try:
            if not w.isVisible() or not (w.focusPolicy() & Qt.FocusPolicy.TabFocus):
                continue
            if isinstance(w, QAbstractButton) and w.text().strip():
                continue
            if isinstance(w, QLineEdit) and isinstance(w.parentWidget(), (QComboBox, QAbstractSpinBox)):
                continue
            if not w.accessibleName():
                out.append(w)
        except RuntimeError:
            continue
    return out


def check_report(win) -> str:
    from .. import theme
    lines = [f"Theme: {theme.current_name()}", "", "Contrast (WCAG 2.1: 4.5 for text, 3.0 for disabled/placeholder):"]
    bad = 0
    for fg, bg, r, need, ok in contrast_report():
        if not ok:
            bad += 1
        lines.append(f"  {'OK  ' if ok else 'LOW '} {fg} on {bg}: {r}:1 (needs {need})")
    lines.append(f"  {bad} pair(s) below the minimum.")
    for name, t in theme.THEMES.items():
        low = [f"{fg}/{bg} {r}" for fg, bg, r, _n, ok in contrast_report(t) if not ok]
        lines.append(f"  theme {name}: " + ("all pairs pass" if not low else "low: " + ", ".join(low)))
    annotate_tree(win)
    missing = unnamed_focusable(win)
    lines += ["", f"Focusable widgets without an accessible name: {len(missing)}"]
    for w in missing[:40]:
        lines.append(f"  {w.metaObject().className()} '{w.objectName()}' tooltip={w.toolTip()[:40]!r}")
    lines += ["", "Keyboard: F6 / Shift+F6 = next / previous window, Ctrl+F6 = editor, Alt = menus.",
              f"Windows high contrast: {'on' if windows_high_contrast() else 'off'}"]
    return "\n".join(lines)


def show_check(win) -> QDialog:
    from .. import theme
    d = QDialog(win)
    d.setWindowTitle("Accessibility Check")
    d.resize(640, 560)
    text = QPlainTextEdit(check_report(win))
    text.setReadOnly(True)
    text.setAccessibleName("Accessibility report")
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    bb.rejected.connect(d.reject)
    lay = QVBoxLayout(d)
    hint = QLabel("Contrast of the current theme and widgets a screen reader cannot name:")
    theme.role(hint, "muted")
    lay.addWidget(hint)
    lay.addWidget(text, 1)
    lay.addWidget(bb)
    d.show()
    return d


# ------------------------------------------------------------------------------------------ install
def install(win) -> None:
    import os
    if os.environ.get("RADIDE_A11Y_OFF") == "1":          # tests: measure the IDE without this feature
        return
    app = QApplication.instance()
    win._a11y_polisher = _Polisher(win)
    app.installEventFilter(win._a11y_polisher)
    QTimer.singleShot(0, lambda: annotate_tree(win))
    for seq, step in (("F6", 1), ("Shift+F6", -1)):
        sc = QShortcut(QKeySequence(seq), win)
        sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
        sc.activated.connect(lambda s=step: cycle_focus(win, s))
    sc = QShortcut(QKeySequence("Ctrl+F6"), win)
    sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
    sc.activated.connect(lambda: getattr(win, "tabs", None) is not None and _focus_into(win.tabs))
    win.a11y_cycle_focus = lambda step=1: cycle_focus(win, step)
    try:
        menu = next(a.menu() for a in win.menuBar().actions()
                    if a.menu() is not None and a.text().replace("&", "") == "Tools")
        a = menu.addAction("Accessibility Chec&k...", lambda: show_check(win))
        a.setToolTip("Contrast of the theme colours and widgets without a name for screen readers")
    except StopIteration:
        pass
    try:
        follow = str(win.settings.value("accessibility/follow_high_contrast", True)).lower() not in ("false", "0")
        if follow and windows_high_contrast():
            from .. import theme
            if theme.current_name() != "High Contrast":
                theme.apply("High Contrast")
                win.log("[accessibility] Windows high contrast is on: using the High Contrast theme "
                        "(Tools > Options to change).")
    except Exception:  # noqa: BLE001
        pass


__all__ = ["annotate", "annotate_tree", "check_report", "contrast", "contrast_report", "cycle_focus",
           "focus_regions", "install", "suggested_name", "unnamed_focusable", "windows_high_contrast"]
