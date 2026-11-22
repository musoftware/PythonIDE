"""Keyboard-only use of the IDE (no mouse): QTest key events, offscreen.

  * menus: Alt / Alt+letter, a unique access key per top-level menu, every main tool bar command also in a menu or
    on a shortcut, tool bars inside tool windows reachable with Tab
  * windows: F6 / Shift+F6 visit the editor and every visible tool window and come back, Ctrl+F6 = editor, the
    designer surface gets the focus, Auto Hide windows slide out with F6 and Esc returns, Ctrl+Tab switches the
    documents (also from the code editor)
  * Toolbox: Up / Down, Enter adds the control, Enter / Left / Right on a group header, Tab to the search box
  * designer: Tab / Shift+Tab select, arrows move, Shift+arrows resize, Ctrl+arrows snap, Delete, Esc, Ctrl+Z
  * Properties: no focus trap (Tab leaves the grid), Enter edits Text, a True/False editor with the keyboard,
    Esc back to the row, Events tab: Enter writes the handler
  * dialogs (New Project, Options, Publish, Extensions, Add Form, Accessibility Check): Tab and Shift+Tab go round
    without a trap and reach every field, Esc closes, Alt+letter of the field labels moves the focus
  * visible focus indicator: focused and unfocused pictures (widget.grab) differ, in every built-in theme

    .venv\\Scripts\\python samples\\Tests\\Accessibility\\test_keyboard_ide.py       (exit code = failures)
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _a11y_common import (auto_close_modals, check, finish, info, main_window, pump,  # noqa: E402
                          project_copy)

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtGui import QAction  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,  # noqa: E402
                             QDialog, QDockWidget, QLabel, QLineEdit, QListWidget, QPlainTextEdit, QPushButton,
                             QTextEdit, QToolBar, QToolButton, QVBoxLayout, QWidget)

K = Qt.Key
M = Qt.KeyboardModifier


def fw():
    return QApplication.focusWidget()


def key(k, mods=M.NoModifier, target=None, n=1):
    for _ in range(n):
        QTest.keyClick(target or fw() or win, k, mods)
        pump(2)


def desc(w):
    if w is None:
        return "None"
    return f"{w.metaObject().className()}('{w.objectName()}', '{w.accessibleName()}')"


def inside(w, root):
    return w is not None and (w is root or root.isAncestorOf(w))


auto_close_modals(True)
win = main_window()
from radide.features import perf_a11y as A  # noqa: E402

# =========================================================================== menus
mb = win.menuBar()
pump(5)
tops = [a for a in mb.actions() if a.menu() is not None and a.isVisible()]
keys = [A._mnemonic(QAction.text(a)) for a in tops]
missing = [QAction.text(a) for a, k in zip(tops, keys) if not k]
dup = sorted({k for k in keys if k and keys.count(k) > 1})
check("menus: every top-level menu has an Alt access key", not missing, missing)
check("menus: the access keys are unique", not dup, [(k, [QAction.text(a) for a in tops if A._mnemonic(QAction.text(a)) == k])
                                                     for k in dup])
info(f"{len(tops)} top-level menus: " + " ".join(QAction.text(a) for a in tops))

win.activateWindow()
pump(3)
start = fw()
key(K.Key_Alt)
check("menus: Alt alone selects the menu bar (first menu)", mb.activeAction() is tops[0], desc(fw()))
key(K.Key_Escape)
pump(3)
key(K.Key_Escape)
key(K.Key_F, M.AltModifier)
pop = QApplication.activePopupWidget()
check("menus: Alt+F opens the File menu", pop is not None and pop is tops[0].menu(), pop)
if pop is not None:
    key(K.Key_Right, target=pop)              # to the next menu (Edit) with the arrow keys
    pop2 = QApplication.activePopupWidget()
    check("menus: Right arrow moves to the next menu", pop2 is not None and pop2 is not pop and pop2 is tops[1].menu(), pop2)
    while QApplication.activePopupWidget() is not None:
        QApplication.activePopupWidget().close()
        pump(2)
# a menu command run with the keyboard only: Alt+V, then the access key of "Toolbox" -> the Toolbox gets the focus
vmenu = next(a.menu() for a in tops if QAction.text(a).replace("&", "") == "View")
vk = A._mnemonic(QAction.text(next(a for a in tops if a.menu() is vmenu)))
key(getattr(K, f"Key_{vk.upper()}"), M.AltModifier)
pop = QApplication.activePopupWidget()
check("menus: Alt+<View key> opens View", pop is vmenu, pop)
while QApplication.activePopupWidget() is not None:
    QApplication.activePopupWidget().close()
    pump(2)

# items without access key / duplicates inside each menu (reported; arrows + Enter always work in a menu)
no_key, dups = 0, []
for a in tops:
    m = a.menu()
    m.aboutToShow.emit()                       # menus filled on demand
    pump(1)
    ks = []
    for it in m.actions():
        if it.isSeparator() or not it.isVisible() or not QAction.text(it).strip():
            continue
        k = A._mnemonic(QAction.text(it))
        if k:
            ks.append(k)
        else:
            no_key += 1
    d = sorted({k for k in ks if ks.count(k) > 1})
    if d:
        dups.append(f"{QAction.text(a).replace('&', '')}: {','.join(d)}")
info(f"menu items without an access key: {no_key}; menus with a repeated key (Enter needed): {len(dups)} {dups[:8]}")


def all_menu_actions():
    seen, out = set(), set()

    def walk(m):
        if id(m) in seen:
            return
        seen.add(id(m))
        m.aboutToShow.emit()
        for it in m.actions():
            out.add(it)
            if it.menu() is not None:
                walk(it.menu())
    for a in mb.actions():
        if a.menu() is not None:
            walk(a.menu())
    return out


in_menus = all_menu_actions()


def norm(t):
    return (t or "").replace("&", "").replace("...", "").split("	")[0].strip().lower()


menu_texts = {norm(a.text()) for a in in_menus if a.isEnabled() or True}
orphans = []
for tb in win.findChildren(QToolBar):
    if not tb.isVisible() or A._dock_of(tb) is not None or tb.objectName().startswith("radAutoHide"):
        continue
    for a in tb.actions():
        if a.isSeparator() or not a.isVisible() or tb.widgetForAction(a) is None:
            continue
        w_ = tb.widgetForAction(a)
        if not isinstance(w_, QToolButton):         # an embedded widget (combo box): reachable itself?
            if not (w_.focusPolicy() & Qt.FocusPolicy.TabFocus):
                orphans.append(f"{tb.windowTitle()}: widget {w_.metaObject().className()}")
            continue
        if a not in in_menus and a.shortcut().isEmpty() and (a.menu() is None or a.menu().menuAction() not in in_menus)                 and norm(a.text()) not in menu_texts:
            orphans.append(f"{tb.windowTitle()}: {a.text() or a.toolTip()}")
check("main tool bars: every command is also in a menu or has a shortcut", not orphans, orphans)

dock_bars = [tb for tb in win.findChildren(QToolBar) if A._dock_of(tb) is not None and tb.isVisible()]
btns = [b for tb in dock_bars for b in tb.findChildren(QToolButton)
        if b.parentWidget() is tb and b.objectName() != "qt_toolbar_ext_button" and b.defaultAction() is not None]
unreach = [b.defaultAction().text() for b in btns if not (b.focusPolicy() & Qt.FocusPolicy.TabFocus)]
check(f"tool bars inside tool windows: buttons reachable with Tab ({len(btns)})", btns and not unreach, unreach[:10])

# =========================================================================== F6 / Shift+F6 / Ctrl+F6
d = win._current_designer()
d.overlay.setFocus()
pump(3)
regions = A.focus_regions(win)
visible_docks = [r for r in regions if isinstance(r, QDockWidget) and not win.autohide.is_auto_hidden(r)]
titles = [r.windowTitle() for r in visible_docks]
check("F6 regions: editor + Toolbox, Solution Explorer, Properties, Output",
      regions and regions[0] is win.tabs and {"Toolbox", "Solution Explorer", "Properties", "Output"} <= set(titles), titles)
seq = []
for _ in range(len(regions)):
    key(K.Key_F6)
    seq.append(A._region_of(win, fw(), regions))
check("F6 visits every window once and comes back to the editor", sorted(seq) == list(range(len(regions)))
      and seq[-1] == 0, (seq, [desc(fw())]))
back = []
for _ in range(len(regions)):
    key(K.Key_F6, M.ShiftModifier)
    back.append(A._region_of(win, fw(), regions))
check("Shift+F6 visits them in the reverse order", back == list(reversed(seq[:-1])) + [0], (back, seq))
key(K.Key_F6)
key(K.Key_F6, M.ControlModifier)
check("Ctrl+F6 goes back to the editor", A._region_of(win, fw(), regions) == 0, desc(fw()))
check("the editor region focuses the designer surface (keyboard input of the form designer)", fw() is d.overlay, desc(fw()))
for r in visible_docks:
    A._focus_into(r)
    pump(2)
    check(f"F6 into '{r.windowTitle()}' puts the focus inside it", inside(fw(), r), desc(fw()))

# =========================================================================== Auto Hide + F6
from radide.features import dock_autohide as AH  # noqa: E402
AH.ANIM_MS = 0
mgr = win.autohide
tbx = win.dock_toolbox
mgr.auto_hide(tbx)
pump(5)
regions = A.focus_regions(win)
check("Auto Hide: the auto-hidden Toolbox stays an F6 region", tbx in regions, [getattr(r, "windowTitle", lambda: "")() for r in regions])
d.overlay.setFocus()
pump(2)
hops = 0
while A._region_of(win, fw(), regions) != regions.index(tbx) and hops < len(regions) + 1:
    key(K.Key_F6)
    pump(3)
    hops += 1
check("Auto Hide: F6 slides the Toolbox out and focuses its content", mgr.panel.isVisible() and mgr.shown_dock() is tbx
      and inside(fw(), mgr.panel), (mgr.panel.isVisible(), desc(fw())))
key(K.Key_Escape)
pump(5)
check("Auto Hide: Esc slides it back and the focus leaves the panel", not mgr.panel.isVisible() and not inside(fw(), mgr.panel),
      (mgr.panel.isVisible(), desc(fw())))
mgr.restore(tbx, focus=False)
pump(5)
check("Auto Hide: the Toolbox docked again", not mgr.is_auto_hidden(tbx) and tbx.isVisible())

# =========================================================================== Ctrl+Tab documents
win.open_code("Form1")
pump(25)
check("two documents open (designer + code)", win.tabs.count() >= 2, win.tabs.count())
code_idx = win.tabs.currentIndex()
cw = win.tabs.currentWidget()
foc = next((w for w in [cw, *cw.findChildren(QWidget)] if w.isVisible() and w.focusPolicy() & Qt.FocusPolicy.TabFocus), cw)
foc.setFocus()
pump(5)
key(K.Key_Tab, M.ControlModifier)
pump(5)
check("Ctrl+Tab from the code editor switches to the other document", win.tabs.currentIndex() != code_idx,
      (win.tabs.currentIndex(), code_idx, desc(fw())))
key(K.Key_Tab, M.ControlModifier | M.ShiftModifier)
pump(5)
check("Ctrl+Shift+Tab switches back", win.tabs.currentIndex() == code_idx, win.tabs.currentIndex())
win.open_designer("Form1")
pump(10)
d = win._current_designer()

# =========================================================================== Toolbox
tb = win.toolbox
A._focus_into(win.dock_toolbox)
pump(3)
check("Toolbox: F6 region focuses the control list", fw() is tb or inside(fw(), tb), desc(fw()))
tb.setFocus()
tb.setCurrentRow(0)
pump(2)
target_row = next(r for r in range(tb.count()) if tb.item(r).data(Qt.ItemDataRole.UserRole) == "Button"
                  and not tb.item(r).isHidden())
for _ in range(tb.count()):
    if tb.currentRow() == target_row:
        break
    key(K.Key_Down, target=tb)
check("Toolbox: Down arrow reaches 'Button'", tb.currentRow() == target_row, (tb.currentRow(), target_row))
before_ids = {id(x) for x in d.doc.form.controls}
key(K.Key_Return, target=tb)
pump(5)
new_ctrls = [x for x in d.doc.form.controls if id(x) not in before_ids]
added = new_ctrls[0] if len(new_ctrls) == 1 else None
check("Toolbox: Enter adds the control to the form and selects it", added is not None and added.type == "Button"
      and d.doc.selected is added, [(x.type, x.name) for x in new_ctrls] + [d.doc.selected and d.doc.selected.name])
from radide.toolbox import CAT_ROLE, TB_ROLE  # noqa: E402
def shown_items():
    return sum(1 for r in range(tb.count()) if not tb.item(r).isHidden())


hrow = next(r for r in range(tb.count()) if tb.item(r).data(TB_ROLE) == "header" and not tb.item(r).isHidden())
cat = tb.item(hrow).data(CAT_ROLE)
tb.setFocus()
tb.setCurrentRow(hrow)
cnt = shown_items()
was_closed = cat in tb._collapsed
key(K.Key_Return, target=tb)
check("Toolbox: Enter on a group header opens / closes the group", (cat in tb._collapsed) != was_closed and shown_items() != cnt,
      (cat, shown_items(), cnt))
check("Toolbox: the header keeps the keyboard cursor", tb.currentItem() is not None and tb.currentItem().data(CAT_ROLE) == cat
      and tb.currentItem().data(TB_ROLE) == "header")
key(K.Key_Right if cat in tb._collapsed else K.Key_Left, target=tb)
check("Toolbox: Right / Left arrow on the header open / close it", (cat in tb._collapsed) == was_closed)
check("Toolbox: header read as '<group> (expanded/collapsed)' by screen readers",
      re.match(r".+ \((expanded|collapsed)\)$", str(tb.currentItem().data(Qt.ItemDataRole.AccessibleTextRole) or "")),
      tb.currentItem().data(Qt.ItemDataRole.AccessibleTextRole))
tb.setFocus()
key(K.Key_Tab, M.ShiftModifier, target=tb)
key(K.Key_Tab, target=tb) if fw() is not tb.search else None
if fw() is not tb.search:
    tb.setFocus()
    seen = []
    for _ in range(4):
        key(K.Key_Tab)
        seen.append(fw())
        if fw() is tb.search:
            break
check("Toolbox: the search box is reachable with Tab / Shift+Tab", fw() is tb.search, desc(fw()))
QTest.keyClicks(tb.search, "TextBox")
pump(5)
vis = [tb.item(r).data(Qt.ItemDataRole.UserRole) for r in range(tb.count()) if not tb.item(r).isHidden()
       and tb.item(r).data(TB_ROLE) == "item"]
check("Toolbox: typing in the search box filters the controls", vis and all("text" in (v or "").lower() for v in vis), vis[:8])
tb.search.clear()
pump(3)

# =========================================================================== designer with keys
d.overlay.setFocus()
pump(2)
f = d.doc.form
d.doc.select(None)
pump(2)
key(K.Key_Tab, target=d.overlay)
first = d.doc.selected
key(K.Key_Tab, target=d.overlay)
second = d.doc.selected
key(K.Key_Tab, M.ShiftModifier, target=d.overlay)
check("designer: Tab selects the next control, Shift+Tab the previous one (focus stays)",
      first is not None and second is not None and first is not second and d.doc.selected is first and fw() is d.overlay,
      (first and first.name, second and second.name, d.doc.selected and d.doc.selected.name))
c = added if added is not None else next(x for x in f.controls if x.type == "Button")
d.doc.select(c)
pump(2)
g0 = tuple(int(c.props[k]) for k in ("Left", "Top", "Width", "Height"))
key(K.Key_Right, target=d.overlay)
key(K.Key_Down, target=d.overlay)
g1 = tuple(int(c.props[k]) for k in ("Left", "Top", "Width", "Height"))
check("designer: arrow keys move the control by 1 pixel", g1[:2] == (g0[0] + 1, g0[1] + 1) and g1[2:] == g0[2:], (g0, g1))
key(K.Key_Right, M.ShiftModifier, target=d.overlay)
g2 = tuple(int(c.props[k]) for k in ("Left", "Top", "Width", "Height"))
check("designer: Shift+arrow resizes", g2[2] == g1[2] + 1 and g2[:2] == g1[:2], (g1, g2))
key(K.Key_Left, M.ControlModifier, target=d.overlay)
g3 = tuple(int(c.props[k]) for k in ("Left", "Top", "Width", "Height"))
check("designer: Ctrl+arrow snaps (grid / next edge)", g3[0] < g2[0] and g3[1:] == g2[1:], (g2, g3))
nm = d.overlay.accessibleName()
check("designer: the surface names the selected control and type for screen readers",
      c.name in nm and c.type in nm and f.name in nm, nm)
check("designer: the description gives position, size and the keys",
      f"Left {g3[0]}" in d.overlay.accessibleDescription() and "Arrow keys" in d.overlay.accessibleDescription(),
      d.overlay.accessibleDescription())
n_before = len(f.controls)
key(K.Key_Delete, target=d.overlay)
check("designer: Delete removes the selected control", len(f.controls) == n_before - 1, (n_before, len(f.controls)))
d.overlay.setFocus()
key(K.Key_Z, M.ControlModifier, target=d.overlay)
pump(3)
check("designer: Ctrl+Z brings it back", len(d.doc.form.controls) == n_before, (n_before, len(d.doc.form.controls)))
c = d.doc.form.find(c.name) or d.doc.form.controls[-1]       # the undo rebuilt the controls
d.doc.select(c)
key(K.Key_Escape, target=d.overlay)
check("designer: Esc selects the container (the form)", d.doc.selected is None)

# =========================================================================== Properties with keys
pp = win.properties
d.doc.select(c)
pump(3)
A._focus_into(win.dock_props)
pump(2)
check("Properties: F6 region starts at the object selector", fw() is pp.selector, desc(fw()))
key(K.Key_Tab)
order = [fw()]
for _ in range(12):
    if inside(fw(), pp.props):
        break
    key(K.Key_Tab)
    order.append(fw())
check("Properties: Tab reaches the grid", fw() is pp.props, [desc(w) for w in order])
key(K.Key_Tab)
check("Properties: Tab leaves the grid (no focus trap)", not inside(fw(), pp.props), desc(fw()))
key(K.Key_Tab, M.ShiftModifier)
check("Properties: Shift+Tab comes back to the grid", fw() is pp.props, desc(fw()))


def row_of(name):
    for r in range(pp.props.rowCount()):
        it = pp.props.item(r, 0)
        dd = it.data(Qt.ItemDataRole.UserRole) if it is not None else None
        if dd is not None and not isinstance(dd, str) and dd.name == name:
            return r
    return -1


r_text = row_of("Text")
pp.props.setCurrentCell(r_text, 0)
pump(2)
check("Properties: the row is read as '<property>: <value>'",
      pp.props.item(r_text, 0).data(Qt.ItemDataRole.AccessibleTextRole) == f"Text: {c.props.get('Text')}",
      pp.props.item(r_text, 0).data(Qt.ItemDataRole.AccessibleTextRole))
key(K.Key_Return, target=pp.props)
ed = fw()
check("Properties: Enter on 'Text' opens its editor", isinstance(ed, QLineEdit) and inside(ed, pp.props), desc(ed))
if isinstance(ed, QLineEdit):
    ed.selectAll()
    QTest.keyClicks(ed, "Keyboard OK")
    key(K.Key_Return, target=ed)
    pump(3)
check("Properties: typing + Enter changes the control's Text", c.props.get("Text") == "Keyboard OK", c.props.get("Text"))
check("Properties: the focus is back on the grid after Enter", fw() is pp.props, desc(fw()))
r_bool = row_of("Enabled")
pp.props.setCurrentCell(r_bool, 0)
pp.props.setFocus()
key(K.Key_Return, target=pp.props)
cb = fw()
check("Properties: Enter on a True/False row focuses its editor", isinstance(cb, QComboBox) and
      pp.props.cellWidget(r_bool, 1) is cb, desc(cb))
check("Properties: the value editor is named after its property", isinstance(cb, QComboBox) and cb.accessibleName() == "Enabled",
      cb.accessibleName() if cb else None)
if isinstance(cb, QComboBox):
    before = c.props.get("Enabled")
    key(K.Key_Down if cb.currentIndex() == 0 else K.Key_Up, target=cb)
    pump(2)
    check("Properties: arrow key in the editor changes the value", c.props.get("Enabled") != before, (before, c.props.get("Enabled")))
    key(K.Key_Escape, target=cb)
    check("Properties: Esc returns to the grid row", fw() is pp.props and pp.props.currentRow() == r_bool, desc(fw()))
    pp.props.cellWidget(r_bool, 1).setCurrentText("True")
pp.props.setFocus()
key(K.Key_Tab, M.ControlModifier, target=pp.props)
check("Properties: Ctrl+Tab shows the Events tab", pp.tabs.currentWidget() is pp.events, pp.tabs.currentIndex())
pp.events.setFocus()
r_click = next((r for r in range(pp.events.rowCount())
                if pp.events.item(r, 0) and pp.events.item(r, 0).data(Qt.ItemDataRole.UserRole) == "Click"), -1)
pp.events.setCurrentCell(r_click, 0)
n_tabs = win.tabs.count()
key(K.Key_Return, target=pp.events)
pump(25)
code = win._code_text("Form1") if hasattr(win, "_code_text") else ""
check("Events: Enter on 'Click' writes the handler and shows the code", r_click >= 0 and f"{c.name}_Click" in code
      and win.tabs.count() >= n_tabs, (r_click, c.name))
pp.tabs.setCurrentIndex(0)
win.open_designer("Form1")
pump(5)


# =========================================================================== dialogs
def tab_round(dlg, back=False, limit=250):
    """Tab (or Shift+Tab) from the first field until the focus comes back. Returns (visited, trapped_at)."""
    mods = M.ShiftModifier if back else M.NoModifier
    first = fw()
    visited = [first]
    stuck = 0
    for _ in range(limit):
        cur = fw()
        if cur is None or not inside(cur, dlg):
            return visited, f"focus left the dialog: {desc(cur)}"
        accepts_tab = isinstance(cur, (QTextEdit, QPlainTextEdit)) and not cur.tabChangesFocus() and not cur.isReadOnly()
        QTest.keyClick(cur, K.Key_Tab, mods | (M.ControlModifier if accepts_tab else M.NoModifier))
        pump(1)
        nxt = fw()
        if nxt is cur:
            stuck += 1
            if stuck >= 3:
                return visited, f"trapped in {desc(cur)}"
            continue
        stuck = 0
        if nxt is first:
            return visited, ""
        visited.append(nxt)
    return visited, "no way back to the first field"


def focusables(dlg):
    out = []
    for w in dlg.findChildren(QWidget):
        if not w.isVisible() or not w.isEnabled() or not (w.focusPolicy() & Qt.FocusPolicy.TabFocus) or w.focusProxy():
            continue
        if isinstance(w, QLineEdit) and isinstance(w.parentWidget(), QComboBox):
            continue
        p, hidden = w.parentWidget(), False
        while p is not None and p is not dlg:          # pages of a tab widget that are not shown
            if not p.isVisible():
                hidden = True
            p = p.parentWidget()
        if not hidden:
            out.append(w)
    return out


def try_dialog(title, make):
    try:
        dlg = make()
    except Exception as e:  # noqa: BLE001
        check(f"dialog {title}: opens", False, repr(e))
        return
    dlg.show()
    dlg.activateWindow()
    dlg.raise_()
    pump(15)
    check(f"dialog {title}: is the active window with a focused field", QApplication.activeWindow() is dlg and inside(fw(), dlg),
          (QApplication.activeWindow(), desc(fw())))
    if not inside(fw(), dlg):
        dlg.focusNextChild()
        pump(2)
    visited, trap = tab_round(dlg)
    check(f"dialog {title}: Tab goes round and comes back (no focus trap)", not trap, trap)
    want = focusables(dlg)
    miss = [desc(w) for w in want if w not in visited and not any(w.isAncestorOf(v) for v in visited)]
    check(f"dialog {title}: Tab reaches every field ({len(want)})", not miss, miss[:8])
    back, trap2 = tab_round(dlg, back=True)
    check(f"dialog {title}: Shift+Tab goes round too", not trap2 and len(back) == len(visited), (trap2, len(back), len(visited)))
    # access keys of field labels -> their field
    labs = [lab for lab in dlg.findChildren(QLabel) if lab.isVisible() and lab.buddy() is not None and lab.buddy().isVisible()
            and lab.buddy().isEnabled() and A._mnemonic(lab.text())]
    bad = []
    for lab in labs[:12]:
        k = A._mnemonic(lab.text())
        if not k.isalpha():
            continue
        others = [w for w in dlg.findChildren(QWidget) if w is not lab and w.isVisible() and
                  A._mnemonic(w.text() if isinstance(w, (QAbstractButton, QLabel)) else "") == k]
        if others:
            continue                              # a repeated key cycles: tested by the unique case only
        anchor = fw()
        QTest.keyClick(anchor, getattr(K, f"Key_{k.upper()}"), M.AltModifier)
        pump(2)
        bud = lab.buddy()
        if not inside(fw(), bud) and fw() is not bud and fw() is not bud.focusProxy():
            bad.append(f"{lab.text()} -> {desc(fw())}")
    nolab = [lab.text() for lab in dlg.findChildren(QLabel) if lab.isVisible() and lab.buddy() is not None
             and lab.buddy().isVisible() and not A._mnemonic(lab.text()) and lab.text().strip() and "<" not in lab.text()]
    check(f"dialog {title}: Alt+<label key> moves to the field ({len(labs)} labels with keys)", not bad, bad[:6])
    info(f"dialog {title}: {len(visited)} Tab stops, {len(labs)} labelled fields with access keys, "
         f"{len(nolab)} without {nolab[:4]}")
    QTest.keyClick(fw() or dlg, K.Key_Escape)
    pump(5)
    check(f"dialog {title}: Esc closes it", not dlg.isVisible(), dlg.isVisible())
    dlg.deleteLater()
    pump(3)


auto_close_modals(False)
from radide.dialogs import AddItemDialog, NewProjectDialog  # noqa: E402
from radide.features.extensions import ExtensionsDialog  # noqa: E402
from radide.features.installer import PublishDialog  # noqa: E402
from radide.features.settings import OptionsDialog  # noqa: E402
try_dialog("New Project", lambda: NewProjectDialog(win))
try_dialog("Options", lambda: OptionsDialog(win))
try_dialog("Publish", lambda: PublishDialog(win, project_copy(), "HelloPython"))
try_dialog("Extensions", lambda: ExtensionsDialog(win))
try_dialog("Add Windows Form", lambda: AddItemDialog(win, "Add Windows Form", "Form2", "python-tk"))
try_dialog("Accessibility Check", lambda: (lambda d_: (d_.hide(), d_)[1])(A.show_check(win)))
auto_close_modals(True)

# =========================================================================== visible focus indicator
from radide import theme  # noqa: E402
host = QDialog(win)
host.setWindowTitle("focus probe")
lay = QVBoxLayout(host)
probes = [QPushButton("&Push"), QLineEdit("text"), QCheckBox("&Check"), QComboBox(), QListWidget()]
probes[3].addItems(["One", "Two"])
probes[4].addItems(["Item 1", "Item 2"])
probes[4].setCurrentRow(0)
for p in probes:
    lay.addWidget(p)
spare = QPushButton("other")
lay.addWidget(spare)
host.resize(260, 300)
host.show()
host.activateWindow()
pump(10)
for name in theme.BUILTIN_THEMES:
    if name == "System":
        continue
    theme.apply(name)
    pump(5)
    weak = []
    for p in probes:
        spare.setFocus(Qt.FocusReason.TabFocusReason)
        pump(2)
        area = p.geometry().adjusted(-3, -3, 3, 3)          # the indicator may be drawn around the widget
        a = host.grab(area).toImage()
        p.setFocus(Qt.FocusReason.TabFocusReason)
        pump(2)
        b = host.grab(area).toImage()
        if a == b:
            weak.append(p.metaObject().className())
    check(f"focus indicator visible in theme {name} (button, edit, check box, combo box, list)", not weak, weak)
theme.apply("Light")
host.close()
pump(3)

win.close()
pump(5)
sys.exit(finish("Accessibility / keyboard"))
