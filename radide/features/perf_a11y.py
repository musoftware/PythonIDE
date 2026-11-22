"""Accessibility (round 7): names for screen readers, keyboard-only navigation and a contrast check.

* Every widget is given an accessible name / description when it is polished (an application event filter),
  if it has none: toolbars and docks by their title, icon-only tool buttons by their action text or tooltip,
  editors by their buddy label / placeholder / tooltip, item views by their dock, controls on the designed form
  by their control name ("rad_<Name>" widgets of radide/preview.py), the Toolbox and the Properties grid.
  Names follow the display language (renew_names after an Arabic / English switch); the designer surface names
  the selected control (radide/designer.py) and the Properties grid reads "<property>: <value>" (properties.py).
* Keyboard: **F6 / Shift+F6** move the focus between the editor area, the visible docks and the Auto Hide
  windows (slid out, like Visual Studio); **Ctrl+F6** goes back to the editor; **Ctrl+Tab / Ctrl+Shift+Tab**
  switch the tabs around the focus (the documents also from the code editor, a web view that kept Ctrl+Tab);
  every top-level menu gets a unique Alt access key (fix_menu_mnemonics: "Python" and the Te&st / &Share clash);
  field labels of dialogs get a free access key and a row widget buddy forwards the focus to its field
  (dialog_access_keys); tool bar buttons inside tool windows join the Tab order (keyboard_reachable).
* A keyboard focus ring (FocusRing) around check boxes, radio buttons, combo boxes, sliders and tool buttons -
  Fusion draws no focus for them - in the theme's highlight colour, only while the keyboard moves the focus.
* **Tools > Accessibility Check...**: WCAG contrast ratios of the current theme's colour pairs (and of all
  themes) + focusable widgets of the main window without an accessible name.
* Windows "Contrast themes" on (SPI_GETHIGHCONTRAST) -> the theme "Windows Contrast", made of the Windows system
  colours (GetSysColor), is applied after start-up unless QSettings "accessibility/follow_high_contrast" is false.

docs/ACCESSIBILITY.md has the keyboard map; samples/Tests/Accessibility tests all of it.
"""
from __future__ import annotations

import sys

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer
from PyQt6.QtGui import QColor, QKeySequence, QShortcut
from PyQt6.QtWidgets import (QAbstractButton, QAbstractItemView, QAbstractSpinBox, QApplication, QComboBox,
                             QDialog, QDialogButtonBox, QDockWidget, QLabel, QLineEdit, QMenuBar, QPlainTextEdit,
                             QScrollArea, QTabBar, QTabWidget, QTextBrowser, QTextEdit, QToolBar, QToolButton,
                             QVBoxLayout, QWidget)

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


def _tr(text: str) -> str:
    """The text in the IDE's display language (radide/i18n; English when no translation is active)."""
    try:
        from .. import i18n
        return i18n.tr(text)
    except Exception:  # noqa: BLE001
        return text


def _txt(obj, attr: str = "text") -> str:
    """The text as shown (radide/i18n patches the getters to return English for the code: screen readers
    must get the translated text of the Arabic UI)."""
    try:
        from .. import i18n
        if i18n.language() != "en":
            return i18n.shown(obj, attr) or ""
    except Exception:  # noqa: BLE001
        pass
    return getattr(obj, attr)() or ""


def _tab_page_title(w: QWidget) -> str:
    """The tab text of the QTabWidget page *w* sits on (an editor / designer tab of the IDE), or ""."""
    p = w
    while p is not None:
        par = p.parentWidget()
        if par is not None and isinstance(par.parentWidget(), QTabWidget):
            tw = par.parentWidget()
            i = tw.indexOf(p)
            if i >= 0:
                return _clean(tw.tabText(i)).rstrip("*").strip()
        if isinstance(p, QDockWidget):
            return ""
        p = par
    return ""


def _grid_cell_property(w: QWidget) -> str:
    """Property / event name of a cell editor of the Properties window ("" if *w* is none)."""
    vp = w.parentWidget()
    grid = vp.parentWidget() if vp is not None else None
    if not isinstance(grid, QAbstractItemView) or grid.viewport() is not vp:
        return ""
    panel = grid.parentWidget()
    while panel is not None and not panel.inherits("PropertiesPanel"):
        panel = panel.parentWidget()
    if panel is None:
        return ""
    try:
        idx = grid.indexAt(w.geometry().center())
        item = grid.item(idx.row(), 0) if idx.isValid() else None
    except (AttributeError, RuntimeError):
        return ""
    return _clean(item.text()) if item is not None else ""


def suggested_name(w: QWidget) -> str:
    """A name for a widget that has none ("" = leave it to Qt, e.g. buttons with text)."""
    from ..properties import PropertiesPanel
    from ..toolbox import Toolbox
    on = w.objectName()
    cls = w.metaObject().className()
    if on.startswith("rad_") and on != "rad_page":          # a control on the designed form (preview.py)
        return on[4:]
    if isinstance(w, QDockWidget):
        return _clean(_txt(w, "windowTitle"))
    if isinstance(w, QToolBar):
        d = _dock_of(w)
        base = _clean(_txt(w, "windowTitle")) or (on if on and on != "Toolbar" else "") or \
            (_clean(_txt(d, "windowTitle")) if d is not None else "")
        return _tr("{} toolbar").replace("{}", base or _tr("Tools"))
    if on == "qt_toolbar_ext_button":
        return _tr("More toolbar items")
    if on == "qt_menubar_ext_button":
        return _tr("More menus")
    if isinstance(w, Toolbox):
        return _tr("Toolbox")
    if isinstance(w, PropertiesPanel):
        return _tr("Properties")
    if cls == "StripTab":                                  # a tab of an auto-hidden window (dock_autohide.py)
        try:
            return _tr("{} (auto-hidden window)").replace("{}", _clean(w.label()))
        except Exception:  # noqa: BLE001
            return ""
    if cls == "DesignerView":                              # the scroll area around the form being designed
        title = _tab_page_title(w)
        return _tr("{} designer").replace("{}", title) if title else _tr("Form designer")
    cell = _grid_cell_property(w)
    if cell:                                               # a value editor in the Properties grid
        return cell
    cellname = _table_cell_name(w)
    if cellname and not (isinstance(w, QAbstractButton) and any(ch.isalnum() for ch in w.text())):
        return cellname
    panel = _properties_panel(w)
    if panel is not None and isinstance(w, QAbstractItemView):
        return _tr("Events grid") if w is getattr(panel, "events", None) else _tr("Properties grid")
    if isinstance(w, QAbstractButton):
        if w.text().strip() and any(ch.isalnum() for ch in w.text()):
            return ""
        if w.text().strip():                              # "..." / "+" / "x": read the tool tip or "Browse"
            return _clean(_txt(w, "toolTip")) or (_tr("Browse") if w.text().strip() in ("...", "\u2026") else "")
        if isinstance(w, QToolButton) and w.defaultAction() is not None:
            a = w.defaultAction()
            return _clean(_txt(a) or _txt(a, "toolTip") or a.iconText())
        return _clean(_txt(w, "toolTip")) or _clean(_txt(w, "statusTip")) or _layout_label(w)
    if isinstance(w, (QLineEdit, QComboBox, QAbstractSpinBox, QPlainTextEdit, QTextEdit)):
        if isinstance(w, QLineEdit) and isinstance(w.parentWidget(), (QComboBox, QAbstractSpinBox)):
            outer = w.parentWidget()                      # the inner editor of an editable combo / spin box
            return outer.accessibleName() or suggested_name(outer)
        lab = _buddy_label(w) or _layout_label(w)
        if lab:
            return lab
        ph = w.placeholderText() if hasattr(w, "placeholderText") else ""
        if ph:
            return _clean(ph)
        if _txt(w, "toolTip"):
            return _clean(_txt(w, "toolTip"))
        if isinstance(w, QComboBox) and w.parentWidget() is not None and \
                w.parentWidget().inherits("PropertiesPanel"):
            return _tr("Object")                          # the Properties window's object selector
        d = _dock_of(w)
        if d is not None and isinstance(w, (QComboBox, QAbstractSpinBox)):
            return _tr("{} choice" if isinstance(w, QComboBox) else "{} value").replace("{}", _clean(_txt(d, "windowTitle")))
    if isinstance(w, QTabBar):                             # tabs of a tab widget / of tabified tool windows
        if cls == "QMainWindowTabBar":
            return _tr("Tool window tabs")
        owner = w.parentWidget()
        if isinstance(owner, QTabWidget):
            if getattr(w.window(), "tabs", None) is owner:
                return _tr("Document tabs")
            return owner.accessibleName() or suggested_name(owner) or _tr("Tabs")
    if isinstance(w, (QAbstractItemView, QPlainTextEdit, QTextBrowser, QTabWidget, QScrollArea)):
        if isinstance(w, QTabWidget) and getattr(w.window(), "tabs", None) is w:
            return _tr("Documents")
        d = _dock_of(w)
        if isinstance(w, QTabWidget):                      # pages of a dialog / tool window: "<title> tabs"
            title = _clean(_txt(d, "windowTitle")) if d is not None else _clean(_txt(w.window(), "windowTitle"))
            return _tr("{} tabs").replace("{}", title) if title else _tr("Tabs")
        lab = _layout_label(w)
        if lab:
            return lab
        if d is not None:
            return _clean(_txt(d, "windowTitle"))
        if _txt(w, "toolTip"):
            return _clean(_txt(w, "toolTip"))
    if w.focusPolicy() & Qt.FocusPolicy.TabFocus:          # e.g. the code editor of an editor tab (web view)
        title = _tab_page_title(w)
        if title:
            return title
        d = _dock_of(w)
        if d is not None:
            return _clean(_txt(d, "windowTitle"))
    return ""


def _table_cell_name(w: QWidget) -> str:
    """A check box / combo box put into a table cell (setCellWidget, maybe inside a small container): named
    "<first column of its row>: <column header>" (e.g. "Python: Format on save")."""
    from PyQt6.QtWidgets import QTableWidget
    cell, vp = w, w.parentWidget()
    for _ in range(2):
        if vp is None:
            return ""
        grid = vp.parentWidget()
        if isinstance(grid, QTableWidget) and grid.viewport() is vp:
            break
        cell, vp = vp, vp.parentWidget()
    else:
        return ""
    if _properties_panel(grid) is not None:
        return ""
    try:
        idx = grid.indexAt(cell.geometry().center())
        if not idx.isValid():
            return ""
        first = grid.item(idx.row(), 0)
        head = grid.horizontalHeaderItem(idx.column())
        a = _clean(first.text()) if first is not None else ""
        b = _clean(head.text()) if head is not None else ""
        return f"{a}: {b}" if a and b else (a or b)
    except RuntimeError:
        return ""


def _properties_panel(w: QWidget):
    p = w.parentWidget()
    for _ in range(4):
        if p is None:
            return None
        if p.inherits("PropertiesPanel"):
            return p
        p = p.parentWidget()
    return None


def _layout_label(w: QWidget) -> str:
    """The label in front of a field in its layout (what Windows' MSAA does for dialogs): the label of its
    QFormLayout row, the cell left of it (or above it) in a QGridLayout, the widget before it in a box layout."""
    from PyQt6.QtWidgets import QBoxLayout, QFormLayout, QGridLayout
    par = w.parentWidget()
    if par is None or par.layout() is None or isinstance(par, QAbstractItemView) or \
            isinstance(par.parentWidget(), QAbstractItemView):
        return ""

    def find(lay, outer=None):
        i = lay.indexOf(w)
        if i >= 0:
            return lay, i, outer
        for k in range(lay.count()):
            sub = lay.itemAt(k).layout()
            if sub is not None:
                r = find(sub, (lay, sub))
                if r:
                    return r
        return None

    def text_of(item):
        lw = item.widget() if item is not None else None
        if isinstance(lw, QLabel) and lw.isVisibleTo(par) and lw.text().strip() and "<" not in lw.text() and \
                (lw.buddy() is None or lw.buddy() is w):
            return _clean(_txt(lw)).rstrip(":")
        return ""
    try:
        r = find(par.layout())
        if not r:
            return ""
        lay, i, outer = r
        if outer is not None and isinstance(outer[0], QFormLayout) and (i == 0 or not isinstance(lay, QBoxLayout)):
            lab = outer[0].labelForField(outer[1])         # a row layout (edit + "..." button) of a form row
            if isinstance(lab, QLabel) and lab.text().strip():
                return _clean(_txt(lab)).rstrip(":")
        if isinstance(lay, QFormLayout):
            lab = lay.labelForField(w)
            return _clean(_txt(lab)).rstrip(":") if isinstance(lab, QLabel) and lab.text().strip() else ""
        if isinstance(lay, QGridLayout):
            row, col, _rs, _cs = lay.getItemPosition(i)
            return (text_of(lay.itemAtPosition(row, col - 1)) if col > 0 else "") or \
                (text_of(lay.itemAtPosition(row - 1, col)) if row > 0 and not isinstance(w, QAbstractButton) else "")
        if isinstance(lay, QBoxLayout) and i > 0:
            return text_of(lay.itemAt(i - 1))
    except RuntimeError:
        return ""
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
            b = lab.buddy()
            if b is not None and (b is w or b.focusProxy() is w) and lab.text():
                return _clean(_txt(lab)).rstrip(":")
        except RuntimeError:
            continue
    return ""


def annotate(w: QWidget) -> bool:
    """Give *w* an accessible name (and a description for designer controls) if it has none."""
    try:
        if w.accessibleName():          # (names given in another display language: renew_names)
            return False
        name = suggested_name(w)
    except RuntimeError:
        return False
    except Exception:  # noqa: BLE001 - never break a widget
        return False
    if not name:
        return False
    _set_auto_name(w, name)
    on = w.objectName()
    if on.startswith("rad_") and not w.accessibleDescription():
        w.setAccessibleDescription(f"{w.metaObject().className()} control {name} on the designed form")
    elif isinstance(w, QDockWidget) and (not w.accessibleDescription() or w.property("radA11yAutoDesc")):
        w.setAccessibleDescription(_tr("{} window - F6 / Shift+F6 move between windows").replace("{}", name))
        w.setProperty("radA11yAutoDesc", True)
    return True


def _lang() -> str:
    try:
        from .. import i18n
        return i18n.language()
    except Exception:  # noqa: BLE001
        return "en"


def _set_auto_name(w: QWidget, name: str) -> None:
    w.setAccessibleName(name)
    w.setProperty("radA11yAuto", f"{_lang()}\x00{name}")


def renew_names(root: QWidget) -> int:
    """After a display-language switch: names this module gave (in the old language) are given again."""
    n = 0
    lang = _lang()
    for w in [root, *root.findChildren(QWidget)]:
        try:
            auto = w.property("radA11yAuto")
            if not auto or auto.startswith(f"{lang}\x00"):
                continue
            if w.accessibleName() != auto.split("\x00", 1)[1]:
                w.setProperty("radA11yAuto", None)          # the program named it since: keep that name
                continue
            name = suggested_name(w)
            if name:
                _set_auto_name(w, name)
                n += 1
                if isinstance(w, QDockWidget) and w.property("radA11yAutoDesc"):
                    w.setAccessibleDescription(
                        _tr("{} window - F6 / Shift+F6 move between windows").replace("{}", name))
        except RuntimeError:
            continue
        except Exception:  # noqa: BLE001
            continue
    for v in root.findChildren(QScrollArea):                # designer surfaces: "<control> (<type>) - <form> designer"
        upd = getattr(v, "_update_accessible", None)
        if callable(upd):
            try:
                upd()
            except Exception:  # noqa: BLE001
                pass
    return n


def annotate_tree(root: QWidget) -> int:
    n = int(annotate(root))
    for w in root.findChildren(QWidget):
        n += annotate(w)
    return n


class _Polisher(QObject):
    """Names widgets as they appear (Polish / Show), cheaply: one check per widget; tool buttons of the tool
    bars inside tool windows join the Tab order; the main window's menu bar keeps unique Alt access keys."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self._lang = _lang()
        self._mn = QTimer(self)
        self._mn.setSingleShot(True)
        self._mn.setInterval(0)
        self._mn.timeout.connect(self._menus)

    def _menus(self):
        try:
            fix_menu_mnemonics(self.win.menuBar())
        except RuntimeError:
            pass

    def eventFilter(self, obj, ev):
        try:
            self._filter(obj, ev)
        except Exception:  # noqa: BLE001 - an exception in an event filter would abort the IDE
            pass
        return False

    def _filter(self, obj, ev):
        t = ev.type()
        if t == QEvent.Type.FocusIn and isinstance(obj, QWidget):
            _ring_focus_in(obj, ev.reason())               # (idempotent: one filter per IDE window sees it)
            return
        if t in (QEvent.Type.Polish, QEvent.Type.Show) and isinstance(obj, QWidget):
            annotate(obj)
            if isinstance(obj, QToolButton):
                keyboard_reachable(obj)
            elif t == QEvent.Type.Show and isinstance(obj, QToolBar):
                for b in obj.findChildren(QToolButton):     # buttons polished before the bar was docked
                    keyboard_reachable(b)
            if t == QEvent.Type.Show and isinstance(obj, QDialog) and not obj.property("radA11yKeys"):
                obj.setProperty("radA11yKeys", True)
                QTimer.singleShot(0, lambda d=obj: dialog_access_keys(d))
        elif t in (QEvent.Type.ActionAdded, QEvent.Type.ActionChanged) and isinstance(obj, QMenuBar):
            if not self._mn.isActive():
                self._mn.start()
        elif t in (QEvent.Type.LayoutDirectionChange, QEvent.Type.ApplicationLayoutDirectionChange) and \
                self._lang != _lang():
            self._lang = _lang()                         # the display language changed (i18n.set_language)
            QTimer.singleShot(0, lambda: renew_names(self.win))
            if not self._mn.isActive():
                self._mn.start()


def keyboard_reachable(b: QToolButton) -> bool:
    """A tool button of a tool bar inside a tool window (Databases, Git Changes ...) can be reached with Tab
    (Qt gives tool bar buttons NoFocus: their commands were mouse-only). Main window tool bars keep NoFocus:
    their commands are in the menus / have shortcuts (checked by samples/Tests/Accessibility)."""
    try:
        bar = b.parentWidget()
        if not isinstance(bar, QToolBar) or b.objectName() == "qt_toolbar_ext_button" or \
                b.focusPolicy() != Qt.FocusPolicy.NoFocus or bar.objectName().startswith("radAutoHide"):
            return False
        if _dock_of(bar) is None:
            return False
        b.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        return True
    except RuntimeError:
        return False


class FocusRing(QWidget):
    """A visible keyboard focus indicator for the widgets Fusion draws no focus for (check boxes, radio buttons,
    combo boxes, sliders, tool buttons): a 2-pixel frame in the theme's highlight colour around the focused widget,
    shown only while the keyboard moves the focus (Tab, F6, access keys) - never for mouse clicks."""
    TYPES = ("QCheckBox", "QRadioButton", "QComboBox", "QFontComboBox", "QSlider", "QToolButton", "QDial",
             "QScrollBar")

    def __init__(self):
        super().__init__(None)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setObjectName("radFocusRing")
        self.target: QWidget | None = None

    @classmethod
    def wants(cls, w: QWidget | None) -> bool:
        if w is None:
            return False
        if isinstance(w, QComboBox) and w.isEditable():
            return False                                  # its line edit shows a caret and a frame
        return any(w.inherits(t) for t in cls.TYPES)

    def follow(self, w: QWidget | None, reason_keyboard: bool) -> None:
        if self.target is not None:
            try:
                self.target.removeEventFilter(self)
            except RuntimeError:
                pass
        self.target = None
        if w is None or not reason_keyboard or not self.wants(w) or w.parentWidget() is None:
            self.hide()
            return
        self.target = w
        w.installEventFilter(self)
        if self.parentWidget() is not w.parentWidget():
            self.setParent(w.parentWidget())
        self._place()

    def _place(self) -> None:
        w = self.target
        if w is None:
            return
        try:
            self.setGeometry(w.geometry().adjusted(-2, -2, 2, 2))
            self.raise_()
            self.setVisible(w.isVisible())
        except RuntimeError:
            self.target = None
            self.hide()

    def eventFilter(self, obj, ev):
        try:
            if obj is self.target:
                t = ev.type()
                if t in (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show):
                    self._place()
                elif t in (QEvent.Type.Hide, QEvent.Type.FocusOut):
                    self.hide()
        except Exception:  # noqa: BLE001 - never abort the IDE from an event filter
            pass
        return False

    def paintEvent(self, _e):
        from PyQt6.QtGui import QPainter, QPen
        p = QPainter(self)
        bg = self.parentWidget().palette().color(self.parentWidget().backgroundRole()).name() \
            if self.parentWidget() is not None else None
        p.setPen(QPen(QColor(ring_color(bg)), 2))
        p.drawRect(self.rect().adjusted(1, 1, -1, -1))


def ring_color(window: str | None = None) -> str:
    """The focus ring colour: the theme's highlight, or its text colour when the highlight is below 3:1 on the
    window surface (the palette's Window colour - what panels and dialogs are painted with)."""
    from PyQt6.QtGui import QPalette
    from .. import theme
    bg = window or QApplication.palette().color(QPalette.ColorRole.Window).name()
    hi = theme.color("highlight")
    if contrast(hi, bg) >= 3.0:
        return hi
    txt = QApplication.palette().color(QPalette.ColorRole.WindowText).name()
    return txt if contrast(txt, bg) >= 3.0 else theme.color("text")


_KEY_REASONS = (Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason, Qt.FocusReason.ShortcutFocusReason)


def _install_focus_ring(app) -> list:
    """One ring per application; _Polisher moves it on every FocusIn (the reason tells keyboard from mouse)."""
    holder = [FocusRing()]          # the ring lives in the focused widget's parent: made again if that is deleted

    def lost(_old, new):
        try:
            if new is None and not sip_deleted(holder[0]):
                holder[0].follow(None, False)
        except Exception:  # noqa: BLE001
            pass
    app.focusChanged.connect(lost)
    return holder


def _ring_focus_in(w: QWidget, reason) -> None:
    app = QApplication.instance()
    holder = getattr(app, "_rad_focus_ring", None)
    if not holder:
        return
    if sip_deleted(holder[0]):
        holder[0] = FocusRing()
    kb = reason in _KEY_REASONS or (reason == Qt.FocusReason.OtherFocusReason and
                                    w.window().testAttribute(Qt.WidgetAttribute.WA_KeyboardFocusChange))
    holder[0].follow(w, kb)


def _mnemonic(text: str) -> str | None:
    import re
    m = re.search(r"&([^&\s])", text or "")
    return m.group(1).lower() if m else None


def dialog_access_keys(d: QWidget) -> int:
    """Labels of a dialog's fields ("Name:" with a buddy, e.g. every QFormLayout row) get a free Alt access key
    when they have none, so each field can be reached with Alt+letter (Windows dialog convention). Buttons keep
    their texts. Returns the number of labels changed."""
    try:
        if sip_deleted(d) or not d.isVisible():
            return 0
        used: set[str] = set()
        widgets = d.findChildren(QWidget)
        for w in widgets:
            if not w.isVisible():
                continue
            t = w.text() if isinstance(w, (QAbstractButton, QLabel)) else \
                w.title() if hasattr(w, "title") and callable(getattr(w, "title")) and isinstance(w.title(), str) else ""
            k = _mnemonic(t)
            if k:
                used.add(k)
            if isinstance(w, QTabBar):
                for i in range(w.count()):
                    k = _mnemonic(w.tabText(i))
                    if k:
                        used.add(k)
        n = 0
        for lab in (w for w in widgets if isinstance(w, QLabel)):
            b = lab.buddy()
            if b is not None and b.focusPolicy() == Qt.FocusPolicy.NoFocus and b.focusProxy() is None:
                # a row widget (edit + "..." button) is the buddy: QLabel gives no focus to a NoFocus buddy, so
                # its first field becomes the buddy (access key + the name a screen reader reads)
                inner = next((c for c in b.findChildren(QWidget) if c.focusPolicy() & Qt.FocusPolicy.TabFocus), None)
                if inner is not None:
                    lab.setBuddy(inner)
                    b = inner
                    if not inner.accessibleName() or inner.property("radA11yAuto"):
                        _set_auto_name(inner, _clean(lab.text()).rstrip(":"))
            t = lab.text()
            if b is None or not lab.isVisible() or not b.isVisible() or not t.strip() or "&" in t or "<" in t or \
                    lab.textFormat() == Qt.TextFormat.RichText or \
                    not ((b.focusProxy() or b).focusPolicy() & Qt.FocusPolicy.TabFocus):
                continue
            pos = next((i for i, ch in enumerate(t) if ch.isalnum() and ch.isascii() and ch.lower() not in used), None)
            if pos is None:
                continue
            used.add(t[pos].lower())
            lab.setText(t[:pos] + "&" + t[pos:])
            n += 1
        return n
    except RuntimeError:
        return 0


def sip_deleted(obj) -> bool:
    try:
        from PyQt6 import sip
        return sip.isdeleted(obj)
    except Exception:  # noqa: BLE001
        return False


def fix_menu_mnemonics(mb: QMenuBar) -> int:
    """Every menu of the menu bar gets a unique Alt access key: menus without one ("Python" of the project
    menus) or with a taken one (Te&st / &Share) get the first free letter of their title. Returns the number
    of menus changed. Works on the English titles (radide/i18n shows "(&X)" after the Arabic ones)."""
    import re
    from PyQt6.QtGui import QAction
    used: set[str] = set()
    todo = []
    for a in mb.actions():
        if a.isSeparator() or a.menu() is None or not a.isVisible():
            continue
        en = QAction.text(a)                        # the patched getter returns the English text
        m = re.search(r"&([^&\s])", en)
        k = m.group(1).lower() if m else None
        if k and k not in used:
            used.add(k)
        else:
            todo.append((a, en))
    n = 0
    for a, en in todo:
        plain = en.replace("&&", "\0").replace("&", "").replace("\0", "&&")
        pos = next((i for i, ch in enumerate(plain) if ch.isalnum() and ch.lower() not in used
                    and (i == 0 or plain[i - 1] != "&")), None)
        if pos is None:
            continue
        used.add(plain[pos].lower())
        a.setText(plain[:pos] + "&" + plain[pos:])
        n += 1
    return n


# ------------------------------------------------------------------------------------------ keyboard
def _autohide(win):
    mgr = getattr(win, "autohide", None)
    try:
        return mgr if mgr is not None and mgr._vs() else None
    except Exception:  # noqa: BLE001
        return None


def focus_regions(win) -> list[QWidget]:
    """Editor area first, then the visible, non-floating docks in screen order (top-left first), then the
    auto-hidden tool windows (Visual Studio Auto Hide: F6 slides them out) in the order of their strip tabs."""
    regions = [win.tabs] if getattr(win, "tabs", None) is not None and win.tabs.isVisible() else []
    docks = [d for d in win.findChildren(QDockWidget) if d.isVisible() and d.widget() is not None and
             not d.visibleRegion().isEmpty()]
    docks.sort(key=lambda d: (d.mapTo(win, d.rect().topLeft()).x() // 40, d.mapTo(win, d.rect().topLeft()).y()))
    mgr = _autohide(win)
    hidden = []
    if mgr is not None:
        try:
            hidden = [d for d in mgr.auto_hidden() if d not in docks]
        except Exception:  # noqa: BLE001
            hidden = []
    return regions + docks + hidden


def _region_of(win, w: QWidget | None, regions) -> int:
    mgr = _autohide(win)
    panel = getattr(mgr, "panel", None) if mgr is not None else None
    while w is not None:
        if w in regions:
            return regions.index(w)
        if panel is not None and w is panel:               # inside the slid-out window of an auto-hidden dock
            d = mgr.shown_dock()
            return regions.index(d) if d in regions else -1
        w = w.parentWidget()
    return -1


def _focus_into(region: QWidget) -> None:
    try:          # F6 / Ctrl+Tab are keyboard navigation too: focus rectangles and the focus ring are shown
        region.window().setAttribute(Qt.WidgetAttribute.WA_KeyboardFocusChange, True)
    except RuntimeError:
        pass
    target = region
    if isinstance(region, QDockWidget):
        win = region.parentWidget()
        while win is not None and not hasattr(win, "autohide"):
            win = win.parentWidget()
        mgr = _autohide(win) if win is not None else None
        if mgr is not None and mgr.is_auto_hidden(region):
            mgr.slide_out(region, focus=True)              # Auto Hide: slide the window out and focus it
            return
        region.raise_()
        target = region.widget()
    elif isinstance(region, QTabWidget) and region.currentWidget() is not None:
        target = region.currentWidget()
    fw = None
    last = target.focusWidget()                            # where the focus was last time in this region
    if last is not None and last is not target and target.isAncestorOf(last) and last.isVisible() \
            and last.isEnabled() and last.focusPolicy() & Qt.FocusPolicy.TabFocus:
        fw = last
    if fw is None and target.focusPolicy() != Qt.FocusPolicy.NoFocus:
        fw = target
    if fw is None:
        fw = next((c for c in target.findChildren(QWidget) if c.isVisible() and c.isEnabled() and
                   c.focusPolicy() & Qt.FocusPolicy.TabFocus), None)
    ov = getattr(fw, "overlay", None)
    if isinstance(ov, QWidget) and ov.isVisible():
        fw = ov                                            # the form designer: its keyboard surface
    (fw or target).setFocus(Qt.FocusReason.TabFocusReason)


def cycle_focus(win, step: int = 1) -> QWidget | None:
    regions = focus_regions(win)
    if not regions:
        return None
    cur = _region_of(win, QApplication.focusWidget(), regions)
    nxt = regions[(cur + step) % len(regions)] if cur >= 0 else regions[0]
    _focus_into(nxt)
    title = nxt.windowTitle() if isinstance(nxt, QDockWidget) else _tr("Editor")
    try:
        win.statusBar().showMessage(_tr("Focus: {}").replace("{}", _clean(title)), 2000)
    except Exception:  # noqa: BLE001
        pass
    return nxt


def next_tab(win, step: int = 1) -> bool:
    """Ctrl+Tab: the next tab of the QTabWidget around the focus (the documents when the focus is elsewhere)."""
    w = QApplication.focusWidget()
    tw = None
    while w is not None and w is not win:
        if isinstance(w, QTabWidget):
            tw = w
            break
        w = w.parentWidget()
    if tw is None:
        tw = getattr(win, "tabs", None)
    if tw is None or tw.count() < 2:
        return False
    i = tw.currentIndex()
    for _ in range(tw.count()):
        i = (i + step) % tw.count()
        if tw.isTabEnabled(i) and tw.isTabVisible(i):
            break
    tw.setCurrentIndex(i)
    page = tw.currentWidget()
    if page is not None:
        if tw is getattr(win, "tabs", None):
            _focus_into(tw)
        elif not page.isAncestorOf(QApplication.focusWidget()):
            page.setFocus(Qt.FocusReason.TabFocusReason)
    return True


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
    if getattr(app, "_rad_focus_ring", None) is None:      # one per application (several IDE windows)
        app._rad_focus_ring = _install_focus_ring(app)
    QTimer.singleShot(0, lambda: annotate_tree(win))
    for seq, step in (("F6", 1), ("Shift+F6", -1)):
        sc = QShortcut(QKeySequence(seq), win)
        sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
        sc.activated.connect(lambda s=step: cycle_focus(win, s))
    sc = QShortcut(QKeySequence("Ctrl+F6"), win)
    sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
    sc.activated.connect(lambda: getattr(win, "tabs", None) is not None and _focus_into(win.tabs))
    win.a11y_cycle_focus = lambda step=1: cycle_focus(win, step)
    # Ctrl+Tab / Ctrl+Shift+Tab: next / previous tab of the tab widget that has the focus - also from the code
    # editor (a web view: it kept Ctrl+Tab to itself, so the documents could not be switched with the keyboard)
    for seq, step in (("Ctrl+Tab", 1), ("Ctrl+Shift+Tab", -1), ("Ctrl+Backtab", -1)):
        sc = QShortcut(QKeySequence(seq), win)
        sc.setContext(Qt.ShortcutContext.WindowShortcut)
        sc.activated.connect(lambda s=step: next_tab(win, s))
    try:
        menu = next(a.menu() for a in win.menuBar().actions()
                    if a.menu() is not None and a.text().replace("&", "") == "Tools")
        a = menu.addAction("Accessibility Chec&k...", lambda: show_check(win))
        a.setToolTip("Contrast of the theme colours and widgets without a name for screen readers")
    except StopIteration:
        pass
    # after every feature: Tools > Options (features/settings.py, installed after this one) applies the saved
    # theme at start-up - the contrast theme applied here before it was replaced at once
    QTimer.singleShot(0, lambda: follow_high_contrast(win))
    QTimer.singleShot(0, lambda: fix_menu_mnemonics(win.menuBar()))


def follow_high_contrast(win, on: bool | None = None, colors: dict | None = None) -> str:
    """Windows "Contrast themes" on -> the IDE uses the Windows colours (theme "Windows Contrast", built from
    GetSysColor) unless QSettings "accessibility/follow_high_contrast" is false. Returns the theme applied
    ("" = none). *on* / *colors* let tests simulate Windows."""
    try:
        follow = str(win.settings.value("accessibility/follow_high_contrast", True)).lower() not in ("false", "0")
        if not follow or not (windows_high_contrast() if on is None else on):
            return ""
        from .. import theme
        t = system_contrast_theme(colors)
        name = theme.add_theme(SYSTEM_CONTRAST, t, base="High Contrast" if t["dark"] else "Light")
        if theme.current_name() != name:
            theme.apply(name)
            win.log("[accessibility] Windows contrast theme is on: the IDE uses the Windows colours "
                    "(Tools > Options > Color theme to change).")
        return name
    except Exception:  # noqa: BLE001
        return ""


SYSTEM_CONTRAST = "Windows Contrast"
# GetSysColor indexes
_SYS = {"window": 5, "text": 8, "highlight": 13, "highlight_text": 14, "button": 15, "disabled": 17,
        "button_text": 18, "link": 26}
# the Windows 11 contrast themes (Settings > Accessibility > Contrast themes) - for tests and as a reference
WINDOWS_CONTRAST_THEMES = {
    "Aquatic": dict(window="#202020", text="#FFFFFF", highlight="#8EE3F0", highlight_text="#263B50",
                    button="#202020", button_text="#FFFFFF", disabled="#A6A6A6", link="#75E9FC"),
    "Desert": dict(window="#FFFAEF", text="#3D3D3D", highlight="#903909", highlight_text="#FFF5E3",
                   button="#FFFAEF", button_text="#202020", disabled="#676767", link="#1C5E75"),
    "Dusk": dict(window="#2D3236", text="#FFFFFF", highlight="#A1BFDE", highlight_text="#212D3B",
                 button="#2D3236", button_text="#B6F6F0", disabled="#A6A6A6", link="#70EBDE"),
    "Night sky": dict(window="#000000", text="#FFFFFF", highlight="#D6B4FD", highlight_text="#2B2B2B",
                      button="#000000", button_text="#FFEE32", disabled="#A6A6A6", link="#8080FF"),
}


def system_colors() -> dict:
    """The Windows system colours of the tokens of _SYS (#RRGGBB)."""
    out = {}
    try:
        import ctypes
        for k, idx in _SYS.items():
            v = ctypes.windll.user32.GetSysColor(idx)
            out[k] = f"#{v & 0xFF:02X}{(v >> 8) & 0xFF:02X}{(v >> 16) & 0xFF:02X}"
    except Exception:  # noqa: BLE001 - not Windows
        out = dict(WINDOWS_CONTRAST_THEMES["Night sky"])
    return out


def system_contrast_theme(colors: dict | None = None) -> dict:
    """A complete IDE theme made only of the Windows contrast colours (as Windows asks of programs)."""
    c = dict(colors or system_colors())
    win_, txt, hi, hit = c["window"], c["text"], c["highlight"], c["highlight_text"]
    btn, btxt, gray, link = c["button"], c["button_text"], c["disabled"], c["link"]
    dark = _lum(win_) < 0.4
    t = dict(dark=dark, monaco="hc-black" if dark else "hc-light",
             window=win_, base=win_, alt_base=win_, text=txt, muted=txt, button=btn, button_text=btxt,
             border=txt, light=txt, mid=gray, dark_c=txt, shadow=txt, highlight=hi, highlight_text=hit,
             link=link, link_visited=link, accent=hi, accent_text=hit, title1=win_, title2=win_, title_text=txt,
             toolbar1=win_, toolbar2=win_, toolbar_border=txt, bar_text=txt, menu=win_, menu_text=txt,
             menu_sel=hi, menu_sel_text=hit, menu_border=txt, tab=win_, tab_text=txt, tab_sel=hi, tab_sel_text=hit,
             tab_hover=win_, status=win_, status_text=txt, header=btn, header_text=btxt, tooltip=win_,
             tooltip_text=txt, calltip=win_, calltip_text=txt, note=link, banner=win_, banner_text=txt,
             banner_border=txt, success=txt, error=txt, info_back=win_, designer_back=win_, category_back=win_,
             stage=win_, heading=link, disabled=gray, placeholder=gray)
    if not dark:
        from .. import theme
        t["code"] = dict(theme.THEMES["Light"]["code"])
        t["chrome"] = dict(theme.THEMES["Light"]["chrome"], margin=win_, margin_bp=win_, line_number=txt)
    return t


__all__ = ["annotate", "annotate_tree", "check_report", "contrast", "contrast_report", "cycle_focus",
           "fix_menu_mnemonics", "focus_regions", "follow_high_contrast", "install", "keyboard_reachable",
           "renew_names", "suggested_name", "system_contrast_theme", "unnamed_focusable",
           "windows_high_contrast", "WINDOWS_CONTRAST_THEMES"]
