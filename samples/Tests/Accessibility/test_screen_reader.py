"""Screen readers: names, roles, descriptions and values of the IDE's widgets.

PyQt6 does not wrap QAccessible, so the offscreen scan applies Qt's own naming rules (accessibleName, else the
button / label text without '&', else the buddy label of a field) to every widget of the main window and of the
main dialogs, and reports what a screen reader could not name: buttons, icon-only tool buttons, edits, combo boxes,
lists and their items, images without text, focusable custom widgets without a name (no role either).
Then the designer surface (selected control: name + type), the Properties grid rows ("<property>: <value>"), the
designed controls (name + description), and the names in the Arabic UI (switched live and back).

The last part runs the real thing when comtypes is available: a child process shows a small IDE window (Toolbox,
Properties, a designer) on the Windows platform plugin - off the visible screen - and UI Automation reads its tree
(names, control types, the Properties cells). Only that process is started and closed. A11Y_NO_UIA=1 skips it.

    .venv\\Scripts\\python samples\\Tests\\Accessibility\\test_screen_reader.py      (exit code = failures)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
if len(sys.argv) > 1 and sys.argv[1] == "--uia-child":       # the child process of part 5
    os.environ["QT_QPA_PLATFORM"] = "windows"
from _a11y_common import (SCRATCH, auto_close_modals, check, finish, info, main_window, pump,  # noqa: E402
                          project_copy)

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import (QAbstractButton, QAbstractItemView, QAbstractSpinBox, QComboBox,  # noqa: E402
                             QDockWidget, QLabel, QLineEdit, QListWidget, QMenu, QPlainTextEdit, QTabBar,
                             QTextEdit, QToolButton, QTreeWidget, QWidget)

from radide.features import perf_a11y as A  # noqa: E402

AR = re.compile(r"[؀-ۿ]")


def strip_amp(t: str) -> str:
    return A._clean(t)


def buddy_text(w: QWidget) -> str:
    """Qt's buddyString(): a QLabel of the same parent whose buddy is the widget."""
    p = w.parentWidget()
    if p is None:
        return ""
    for lab in p.findChildren(QLabel, options=Qt.FindChildOption.FindDirectChildrenOnly):
        b = lab.buddy()
        if b is not None and (b is w or b.focusProxy() is w) and lab.text():
            return strip_amp(lab.text())
    # QFormLayout rows: the label is a sibling of the row widget that holds the field
    pp = p.parentWidget()
    if pp is not None:
        for lab in pp.findChildren(QLabel, options=Qt.FindChildOption.FindDirectChildrenOnly):
            b = lab.buddy()
            if b is not None and (b is p and b.focusProxy() is w) and lab.text():
                return strip_amp(lab.text())
    return ""


def qt_name(w: QWidget) -> str:
    """The name Qt's accessible interface reports for *w* (QAccessibleWidget / QAccessibleButton rules)."""
    n = w.accessibleName()
    if n:
        return n
    if isinstance(w, QAbstractButton):
        t = strip_amp(w.text())
        if t and any(ch.isalnum() for ch in t):      # "..." / "+" alone says nothing to a screen reader user
            return t
        if isinstance(w, QToolButton) and w.defaultAction() is not None:
            return strip_amp(w.defaultAction().text())
    if isinstance(w, QLabel):
        return strip_amp(w.text()) if w.textFormat() != Qt.TextFormat.RichText else re.sub("<[^>]+>", "", w.text())
    if isinstance(w, (QLineEdit, QComboBox, QAbstractSpinBox, QPlainTextEdit, QTextEdit, QAbstractItemView)):
        if isinstance(w, QLineEdit) and isinstance(w.parentWidget(), (QComboBox, QAbstractSpinBox)):
            return qt_name(w.parentWidget())
        return buddy_text(w)
    if isinstance(w, QDockWidget):
        return strip_amp(w.windowTitle())
    return ""


def shown(w: QWidget) -> bool:
    if not w.isVisible():
        return False
    return not w.visibleRegion().isEmpty() or w.isWindow()


def scan(root: QWidget, title: str, detail: bool = True) -> dict:
    """Unnamed interactive widgets, images without text, unnamed items of lists / trees."""
    A.annotate_tree(root)
    bad, images, items, unknown = [], [], [], []
    total = 0
    for w in [root, *root.findChildren(QWidget)]:
        try:
            if not shown(w) or w.objectName() in ("radFocusRing",) or isinstance(w, QMenu):
                continue
            focusable = bool(w.focusPolicy() & Qt.FocusPolicy.TabFocus) and w.isEnabled()
            if isinstance(w, QLabel) and w.pixmap() is not None and not w.pixmap().isNull() and not w.text().strip():
                if not w.accessibleName():
                    images.append(f"{w.objectName() or w.parentWidget().metaObject().className()}")
                continue
            interactive = focusable or isinstance(w, (QAbstractButton,)) and w.isEnabled()
            if not interactive:
                continue
            if isinstance(w, QLineEdit) and isinstance(w.parentWidget(), (QComboBox, QAbstractSpinBox)):
                continue
            if w.objectName().startswith("qt_scrollarea") or w.metaObject().className() in ("QScrollBar",):
                continue
            total += 1
            if not qt_name(w).strip():
                cls = w.metaObject().className()
                known = isinstance(w, (QAbstractButton, QLineEdit, QComboBox, QAbstractSpinBox, QPlainTextEdit,
                                       QTextEdit, QAbstractItemView, QTabBar))
                (bad if known else unknown).append(f"{cls}('{w.objectName()}') in "
                                                   f"{w.parentWidget().metaObject().className() if w.parentWidget() else '-'}")
            if isinstance(w, (QListWidget, QTreeWidget)):
                n_empty = 0
                if isinstance(w, QListWidget):
                    for r in range(min(w.count(), 400)):
                        it = w.item(r)
                        if not it.isHidden() and not (it.text().strip() or it.data(Qt.ItemDataRole.AccessibleTextRole)):
                            n_empty += 1
                else:
                    stack = [w.topLevelItem(i) for i in range(min(w.topLevelItemCount(), 400))]
                    while stack:
                        it = stack.pop()
                        if not it.isHidden() and not any(it.text(c).strip() for c in range(w.columnCount())):
                            n_empty += 1
                        stack += [it.child(i) for i in range(min(it.childCount(), 100))]
                if n_empty:
                    items.append(f"{qt_name(w) or w.metaObject().className()}: {n_empty} item(s)")
        except RuntimeError:
            continue
    check(f"{title}: every interactive widget has a name ({total} checked)", not bad, bad[:12])
    check(f"{title}: no focusable custom widget without name / role", not unknown, unknown[:12])
    check(f"{title}: images have a text or a name", not images, images[:8])
    check(f"{title}: list / tree items have a text", not items, items[:8])
    return {"total": total, "bad": bad, "unknown": unknown}


def child_main() -> int:
    """--uia-child: a real (Windows platform) IDE window for UI Automation, written to <out>.json when ready."""
    out = sys.argv[2]
    win = main_window()
    win.move(-3000, 40)                     # off the visible desktop: nothing flashes on the user's screen
    pump(20)
    d = win._current_designer()
    btn = next((c for c in d.doc.form.controls if c.type == "Button"), None)
    if btn is not None:
        d.doc.select(btn)
    pump(10)
    A.annotate_tree(win)
    pump(5)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"hwnd": int(win.winId()), "control": btn.name if btn else "", "form": d.doc.form.name}, fh)
    deadline = time.time() + 90
    stop = out + ".stop"
    while time.time() < deadline and not os.path.exists(stop):
        pump(5, 20)
    win.close()
    pump(5)
    return 0


if len(sys.argv) > 1 and sys.argv[1] == "--uia-child":
    sys.exit(child_main())

# =========================================================================== 1. main window
auto_close_modals(True)
win = main_window()
win.open_code("Form1")
pump(20)
win.open_designer("Form1")
pump(10)
res = scan(win, "main window")
info(f"main window: {res['total']} interactive widgets checked")
docks = [d for d in win.findChildren(QDockWidget) if d.isVisible()]
check("tool windows: name = title, description mentions F6", all(d.accessibleName() == strip_amp(d.windowTitle()) and
      "F6" in d.accessibleDescription() for d in docks), [(d.windowTitle(), d.accessibleName()) for d in docks
                                                          if d.accessibleName() != strip_amp(d.windowTitle())][:6])
tbs = [t for t in win.findChildren(QWidget) if t.metaObject().className() == "QToolBar" and t.isVisible()]
check("tool bars: named '<title> toolbar'", tbs and all(t.accessibleName().endswith("toolbar") for t in tbs),
      [t.accessibleName() for t in tbs][:8])
check("document tabs named", win.tabs.accessibleName() == "Documents" and win.tabs.tabBar().accessibleName() == "Document tabs",
      (win.tabs.accessibleName(), win.tabs.tabBar().accessibleName()))

# =========================================================================== 2. designer + Properties
d = win._current_designer()
f = d.doc.form
btn = next(c for c in f.controls if c.type == "Button")
d.doc.select(btn)
pump(5)
ov = d.overlay
check("designer surface: name = selected control + type + form", ov.accessibleName() == f"{btn.name} (Button) - {f.name} designer",
      ov.accessibleName())
check("designer surface: description = bounds + keys", ov.accessibleDescription().startswith(
      f"Left {int(btn.props['Left'])}, Top {int(btn.props['Top'])}, Width {int(btn.props['Width'])}"),
      ov.accessibleDescription())
d.doc.select_many([btn, next(c for c in f.controls if c is not btn and c.type != "Timer")])
pump(3)
check("designer surface: several selected -> count + primary", ov.accessibleName().startswith("2 controls selected"),
      ov.accessibleName())
d.doc.select(None)
pump(3)
check("designer surface: nothing selected -> the form", ov.accessibleName() == f"{f.name} (Form) - {f.name} designer",
      ov.accessibleName())
check("designer view (scroll area) named after its tab", d.accessibleName().endswith("designer"), d.accessibleName())
prev = [w for w in d.findChildren(QWidget) if w.objectName().startswith("rad_") and w.objectName() != "rad_page"]
named = [w for w in prev if w.accessibleName() == w.objectName()[4:] and "on the designed form" in w.accessibleDescription()]
check(f"designed controls: name + description ({len(prev)})", prev and len(named) == len(prev),
      [w.objectName() for w in prev if w not in named][:6])
d.doc.select(btn)
pump(5)
pp = win.properties
rows = []
for r in range(pp.props.rowCount()):
    it = pp.props.item(r, 0)
    dd = it.data(Qt.ItemDataRole.UserRole) if it is not None else None
    if dd is not None and not isinstance(dd, str):
        rows.append((r, dd, it))
wrong = []
for r, dd, it in rows:
    text = str(it.data(Qt.ItemDataRole.AccessibleTextRole) or "")
    if not text.startswith(it.text().split("  ")[0]):
        wrong.append(f"{it.text()} -> {text!r}")
check(f"Properties grid: every row read as '<property>: <value>' ({len(rows)})", rows and not wrong, wrong[:8])
r_text = next(r for r, dd, it in rows if dd.name == "Text")
check("Properties grid: the Text row carries the value", pp.props.item(r_text, 0).data(Qt.ItemDataRole.AccessibleTextRole)
      == f"Text: {btn.props.get('Text')}", pp.props.item(r_text, 0).data(Qt.ItemDataRole.AccessibleTextRole))
cells = [(pp.props.item(r, 0).text(), pp.props.cellWidget(r, 1)) for r, dd, it in rows if pp.props.cellWidget(r, 1)]
badcells = [f"{n}: {w.accessibleName()!r}" for n, w in cells if w.accessibleName() != n]
check(f"Properties grid: value editors named after their property ({len(cells)})", cells and not badcells, badcells[:8])
helped = [it for r, dd, it in rows if dd.help]
check("Properties grid: the help text is the row's description", all(it.data(Qt.ItemDataRole.AccessibleDescriptionRole)
                                                                      == dd.help for r, dd, it in rows if dd.help),
      len(helped))
check("Properties: object selector / grid / tabs named", pp.selector.accessibleName() == "Object" and
      pp.props.accessibleName() == "Properties grid", (pp.selector.accessibleName(), pp.props.accessibleName()))

# =========================================================================== 3. dialogs
auto_close_modals(False)
from radide.dialogs import AddItemDialog, NewProjectDialog  # noqa: E402
from radide.features.extensions import ExtensionsDialog  # noqa: E402
from radide.features.installer import PublishDialog  # noqa: E402
from radide.features.settings import OptionsDialog  # noqa: E402
for title, make in (("New Project", lambda: NewProjectDialog(win)), ("Options", lambda: OptionsDialog(win)),
                    ("Publish", lambda: PublishDialog(win, project_copy(), "HelloPython")),
                    ("Extensions", lambda: ExtensionsDialog(win)),
                    ("Add Windows Form", lambda: AddItemDialog(win, "Add Windows Form", "Form2", "python-tk"))):
    dlg = make()
    dlg.show()
    pump(15)
    tabs = [t for t in dlg.findChildren(QWidget) if t.metaObject().className() == "QTabWidget"]
    scan(dlg, f"dialog {title}")
    for tw in tabs:                             # every page of the dialog's tab widgets
        for i in range(1, tw.count()):
            tw.setCurrentIndex(i)
            pump(3)
            scan(dlg, f"dialog {title} / {strip_amp(tw.tabText(i))}")
    dlg.close()
    dlg.deleteLater()
    pump(3)
auto_close_modals(True)

# =========================================================================== 4. Arabic UI
from radide import i18n  # noqa: E402
from radide.features.ui_language import apply_language  # noqa: E402
apply_language(win, "ar", notify=False)
pump(30)
tbx = win.dock_toolbox
check("Arabic UI: tool window names in Arabic", AR.search(tbx.accessibleName() or "") is not None, tbx.accessibleName())
check("Arabic UI: the F6 description in Arabic", AR.search(tbx.accessibleDescription() or "") is not None,
      tbx.accessibleDescription())
check("Arabic UI: Toolbox list named in Arabic", AR.search(win.toolbox.accessibleName() or "") is not None,
      win.toolbox.accessibleName())
tbs = [t for t in win.findChildren(QWidget) if t.metaObject().className() == "QToolBar" and t.isVisible()]
check("Arabic UI: tool bar names in Arabic", tbs and all(AR.search(t.accessibleName()) for t in tbs),
      [t.accessibleName() for t in tbs if not AR.search(t.accessibleName())][:6])
d.doc.select(btn)
pump(3)
check("Arabic UI: designer surface name in Arabic (control name kept)", AR.search(ov.accessibleName()) and btn.name in ov.accessibleName(),
      ov.accessibleName())
check("Arabic UI: Properties object selector named in Arabic", AR.search(pp.selector.accessibleName() or ""),
      pp.selector.accessibleName())
res_ar = scan(win, "Arabic UI main window")
leftover = [i18n.missing()[i] for i in range(len(i18n.missing())) if i18n.missing()[i] in
            ("{} toolbar", "Toolbox", "Properties grid", "Document tabs", "Tool window tabs", "Form designer")]
check("Arabic UI: the new accessibility texts are in ar.json", not leftover, leftover)
apply_language(win, "en", notify=False)
pump(30)
check("English again: names back in English", tbx.accessibleName() == "Toolbox" and not AR.search(ov.accessibleName()),
      (tbx.accessibleName(), ov.accessibleName()))

# =========================================================================== 5. real UI Automation (optional)
uia_ok = os.environ.get("A11Y_NO_UIA") != "1" and sys.platform == "win32"
try:
    import comtypes.client  # noqa: F401
except Exception:  # noqa: BLE001
    uia_ok = False
if not uia_ok:
    info("UI Automation part skipped (comtypes missing or A11Y_NO_UIA=1)")
else:
    out = os.path.join(SCRATCH, "uia_child.json")
    for p_ in (out, out + ".stop"):
        if os.path.exists(p_):
            os.remove(p_)
    env = dict(os.environ, QT_QPA_PLATFORM="windows", A11Y_OUT=os.path.join(SCRATCH, "child"))
    for attempt in range(2):          # one retry: a crash at start-up (seen in unrelated features) is not ours
        proc = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--uia-child", out], env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0 = time.time()
        while time.time() - t0 < 120 and not os.path.exists(out) and proc.poll() is None:
            time.sleep(0.5)
        if os.path.exists(out) or proc.poll() is None:
            break
        info(f"UIA child exited with {proc.poll()} before it was ready (attempt {attempt + 1})")
    try:
        ready = os.path.exists(out)
        check("UIA: the child IDE window started (Windows platform plugin)", ready, proc.poll())
        if ready:
            time.sleep(1.0)
            meta = json.load(open(out, encoding="utf-8"))
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen import UIAutomationClient as U
            uia = comtypes.client.CreateObject("{ff48dba4-60ef-4201-aa87-54103eef594e}", interface=U.IUIAutomation)
            root = uia.ElementFromHandle(meta["hwnd"])
            walker = uia.RawViewWalker
            elems = []

            def walk(el, depth=0):
                if el is None or depth > 25 or len(elems) > 6000:
                    return
                try:
                    elems.append((el.CurrentName or "", int(el.CurrentControlType), bool(el.CurrentIsKeyboardFocusable),
                                  bool(el.CurrentIsOffscreen)))
                except Exception:  # noqa: BLE001
                    return
                try:
                    ch = walker.GetFirstChildElement(el)
                except Exception:  # noqa: BLE001
                    ch = None
                while ch:
                    walk(ch, depth + 1)
                    try:
                        ch = walker.GetNextSiblingElement(ch)
                    except Exception:  # noqa: BLE001
                        break
            walk(root)
            names = [e[0] for e in elems]
            info(f"UIA: {len(elems)} elements in the IDE window")
            for want in ("Toolbox", "Solution Explorer", "Properties", "Properties grid", "Object", "Output"):
                check(f"UIA: element named '{want}'", want in names)
            ov_name = f"{meta['control']} (Button) - {meta['form']} designer"
            check("UIA: designer surface reports the selected control", ov_name in names, [n for n in names if "designer" in n][:5])
            check("UIA: a Properties row reads '<property>: <value>'", any(re.match(r"^(BackColor|ForeColor|Text|Font\w*|Enabled|Visible|\(Name\)): ", n) for n in names),
                  [n[:60] for n in names if n.startswith(("Text", "(Name)", "Name", "Enabled"))][:8] or names[-40:])
            BTN, EDIT, COMBO, LIST, TREE = 50000, 50004, 50003, 50008, 50023
            unnamed = [e for e in elems if e[2] and not e[3] and e[1] in (BTN, EDIT, COMBO, LIST, TREE) and not e[0].strip()]
            check("UIA: no keyboard-focusable button / edit / combo / list / tree without a name", not unnamed,
                  unnamed[:10])
    finally:
        with open(out + ".stop", "w") as fh:
            fh.write("stop")
        try:
            proc.wait(30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(10)

win.close()
pump(5)
sys.exit(finish("Accessibility / screen readers"))
