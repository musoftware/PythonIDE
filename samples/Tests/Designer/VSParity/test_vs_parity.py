"""Visual Studio (2005 / 2022 WinForms designer) parity checks of RAD IDE's classic form designer.

Drives FormDocument, the DesignerView (overlay mouse / keyboard), the Properties window and the IDE's
Format menu offscreen and prints a PASS / FAIL line per behaviour:

  Format > Align (Lefts / Centers / Rights / Tops / Middles / Bottoms / to Grid, relative to the PRIMARY
  selection, also across containers), Make Same Size (Width / Height / Both / Size to Grid), Horizontal /
  Vertical Spacing (Make Equal / Increase / Decrease / Remove), Center in Form (as a group, per container,
  TabControl client area), Order (every selected control), Lock Controls (undoable, blocks moves), Tab
  Order (Ctrl+click restarts), mouse drags (group keeps its spacing, grid + snaplines, Alt = free, Esc
  cancels, one undo step, no empty undo step), group resize, arrow keys (1 px, Ctrl = next grid line /
  edge, Shift = resize), Tab / Shift+Tab, Esc = parent, rubber band (form level, Shift adds, Ctrl
  toggles), Ctrl / Shift+click, copy / paste (cascade, into the selected container / TabControl page),
  click-drag to draw a control, Toolbox double-click, multi-select properties, delete, containers
  (drag in / out by the mouse pointer), anchors / docking when the form is resized, zoom, menu enabling.

Run:  .venv\\Scripts\\python samples\\Tests\\Designer\\VSParity\\test_vs_parity.py
Uses QSettings "RADIDE-TEST" (cleared before / after), QT_QPA_PLATFORM=offscreen, widget.grab only.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["RADIDE_NO_BROWSER"] = "1"
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

import PyQt6.QtWebEngineWidgets  # noqa: E402,F401  (must come before the QApplication)
from PyQt6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, QSettings, Qt  # noqa: E402
from PyQt6.QtGui import QMouseEvent  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
app = QApplication(sys.argv[:1])
QSettings().clear()
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
for _n in ("warning", "critical", "information"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))

from radide.designer import GRID, DesignerView  # noqa: E402
from radide.document import FormDocument  # noqa: E402
from radide.model import Form  # noqa: E402
from radide.toolbox import TOOL_STATE  # noqa: E402

OUT = Path(os.environ.get("VSPARITY_OUT") or Path(tempfile.gettempdir()) / "radide-vsparity")
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True, exist_ok=True)
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)


def pump(n=3):
    for _ in range(n):
        app.processEvents()


Mod = Qt.KeyboardModifier
NoMod = Mod.NoModifier
L = Qt.MouseButton.LeftButton


def mouse(w, kind, pos, mods=NoMod, button=L):
    t = {"press": QEvent.Type.MouseButtonPress, "move": QEvent.Type.MouseMove,
         "release": QEvent.Type.MouseButtonRelease}[kind]
    btn = Qt.MouseButton.NoButton if kind == "move" else button
    btns = button if kind in ("press", "move") else Qt.MouseButton.NoButton
    p = QPointF(QPoint(*pos))
    ev = QMouseEvent(t, p, w.mapToGlobal(p), btn, btns, mods)
    QApplication.sendEvent(w, ev)
    pump(1)


def drag(w, a, b, mods=NoMod, steps=4):
    mouse(w, "press", a, mods)
    for i in range(1, steps + 1):
        mouse(w, "move", (a[0] + (b[0] - a[0]) * i // steps, a[1] + (b[1] - a[1]) * i // steps), mods)
    mouse(w, "release", b, mods)


def key(w, k, mods=NoMod):
    QTest.keyClick(w, k, mods)
    pump(1)


VIEWS = []


def make(spec, width=480, height=360):
    """spec: list of (type, name, left, top[, width, height[, parent[, extra props]]])."""
    f = Form()
    f.props["Width"], f.props["Height"] = width, height
    doc = FormDocument(f, OUT / "Form1.form")
    for s in spec:
        t, name, x, y = s[:4]
        c = f.add(t, x, y, s[6] if len(s) > 6 else "")
        c.props["Name"] = name
        if len(s) > 4 and s[4]:
            c.props["Width"], c.props["Height"] = s[4], s[5]
        if len(s) > 7:
            c.props.update(s[7])
    doc._normalize()
    view = DesignerView(doc)
    view.resize(900, 700)
    view.show()
    pump()
    VIEWS.append(view)
    return doc, view, f


def geo(c):
    return tuple(int(c.props[k]) for k in ("Left", "Top", "Width", "Height"))


def sel(doc, *ctrls):
    """Select in order; the LAST one is the primary (white handles), as with Ctrl+clicks."""
    doc.select_many(list(ctrls))


def undo_n(doc):
    return len(doc._undo)


# ===================================================================== Align
doc, view, f = make([("Button", "b1", 16, 16), ("Button", "b2", 40, 64, 100, 30), ("Button", "b3", 96, 120, 50, 20)])
b1, b2, b3 = (f.find(n) for n in ("b1", "b2", "b3"))
start = {c.name: geo(c) for c in f.controls}


def rebind():
    """An undo rebuilds the controls from the snapshot: look them up again by name."""
    g = globals()
    for c in doc.form.controls:
        g[c.name] = c


def reset():
    rebind()
    for c in f.controls:
        c.props["Left"], c.props["Top"], c.props["Width"], c.props["Height"] = start[c.name]


sel(doc, b1, b3, b2)
n0 = undo_n(doc)
doc.align("left")
check("Align Lefts: every control takes the PRIMARY's Left", [geo(c)[0] for c in (b1, b2, b3)] == [40, 40, 40],
      [geo(c) for c in (b1, b2, b3)])
check("Align Lefts: the primary itself does not move", geo(b2) == start["b2"])
check("Align: one undo step", undo_n(doc) == n0 + 1)
doc.undo()
rebind()
check("Align: undo puts every control back", all(geo(c) == start[c.name] for c in f.controls))
for mode, exp in (("center_v", [40 + (100 - 75) // 2, 40, 40 + (100 - 50) // 2]),
                  ("right", [140 - 75, 40, 140 - 50])):
    reset(); sel(doc, b1, b3, b2); doc.align(mode)
    check(f"Align {mode}: relative to the primary", [geo(c)[0] for c in (b1, b2, b3)] == exp,
          [geo(c) for c in (b1, b2, b3)])
for mode, exp in (("top", [64, 64, 64]), ("middle", [64 + (30 - 23) // 2, 64, 64 + (30 - 20) // 2]),
                  ("bottom", [94 - 23, 64, 94 - 20])):
    reset(); sel(doc, b1, b3, b2); doc.align(mode)
    check(f"Align {mode}: relative to the primary", [geo(c)[1] for c in (b1, b2, b3)] == exp,
          [geo(c) for c in (b1, b2, b3)])
reset()
sel(doc, b2, b1)            # primary b1 now
doc.align("left")
check("Align: the primary is the LAST selected control (white handles)", geo(b2)[0] == 16, geo(b2))
reset()
b1.props["Left"], b1.props["Top"] = 13, 21
sel(doc, b1)
check("Align to Grid: available with one control", doc.can_format("to_grid"))
doc.align("to_grid")
check("Align to Grid: Location to the nearest grid point", geo(b1)[:2] == (16, 24), geo(b1))
check("Align Lefts disabled with one control", not doc.can_format("left"))
reset()

# ---- Make Same Size
sel(doc, b1, b3, b2)
doc.align("same_width")
check("Make Same Size > Width", geo(b1)[2] == geo(b3)[2] == 100 and geo(b1)[3] == 23)
reset(); sel(doc, b1, b3, b2); doc.align("same_height")
check("Make Same Size > Height", geo(b1)[3] == geo(b3)[3] == 30 and geo(b1)[2] == 75)
reset(); sel(doc, b1, b3, b2); doc.align("same_size")
check("Make Same Size > Both", geo(b1)[2:] == geo(b3)[2:] == (100, 30))
reset(); sel(doc, b1); doc.align("size_to_grid")
check("Make Same Size > Size to Grid (75 x 23 -> 72 x 24)", geo(b1)[2:] == (72, 24), geo(b1))
reset()

# ---- Lock Controls
sel(doc, b1, b2)
n0 = undo_n(doc)
view.set_locked(True)
check("Lock Controls is an undo step", undo_n(doc) == n0 + 1)
check("Format commands are disabled while locked", not doc.can_format("left") and not doc.can_format("center_form_h"))
doc.align("left")
check("Align does nothing while locked", geo(b1) == start["b1"])
key(view.overlay, Qt.Key.Key_Right)
check("arrow keys do not move locked controls", geo(b1) == start["b1"])
doc.undo()
check("undo unlocks", not doc.locked)

# ---- Align across containers (form coordinates) and docked controls
doc, view, f = make([("Panel", "pnl", 100, 100, 200, 120), ("Button", "inner", 10, 10, 0, 0, "pnl"),
                     ("Button", "outer", 24, 24), ("Panel", "dock", 0, 0, 100, 40, "", {"Dock": "Top"})])
inner, outer, dockp = f.find("inner"), f.find("outer"), f.find("dock")
doc._relayout(emit=False)
sel(doc, inner, outer)
doc.align("left")
check("Align across containers lines the controls up on screen", f.abs_pos(inner)[0] == f.abs_pos(outer)[0] == 24,
      (f.abs_pos(inner), f.abs_pos(outer)))
before = geo(dockp)
sel(doc, dockp, outer)
check("a docked control is not a Format target", not doc.can_format("left"))
doc.align("left")
check("Align leaves docked controls alone", geo(dockp) == before)

# ===================================================================== spacing
doc, view, f = make([("Button", "s1", 0, 40, 50, 20), ("Button", "s2", 70, 40, 50, 20),
                     ("Button", "s3", 200, 40, 50, 20), ("Button", "s4", 220, 40, 30, 20)])
s1, s2, s3, s4 = (f.find(n) for n in ("s1", "s2", "s3", "s4"))
s4.props["Left"], s4.props["Top"] = 300, 40
start = {c.name: geo(c) for c in f.controls}
reset()
sel(doc, s1, s2)
check("Horizontal Spacing > Make Equal needs 3 controls", not doc.can_format("hspace_equal")
      and doc.can_format("hspace_inc"))
sel(doc, s1, s2, s3, s4)
doc.align("hspace_equal")
gaps = [geo(b)[0] - (geo(a)[0] + geo(a)[2]) for a, b in ((s1, s2), (s2, s3), (s3, s4))]
check("Make Equal: the outermost controls stay, equal gaps", geo(s1)[0] == 0 and geo(s4)[0] == 300
      and max(gaps) - min(gaps) <= 1, gaps)
reset()
sel(doc, s1, s3, s4, s2)          # primary s2
doc.align("hspace_inc")
check("Increase: the primary stays, every gap grows by one grid step",
      geo(s2)[0] == 70 and geo(s1)[0] == -GRID and geo(s3)[0] == 200 + GRID and geo(s4)[0] == 300 + 2 * GRID,
      [geo(c)[0] for c in (s1, s2, s3, s4)])
reset(); sel(doc, s1, s3, s4, s2); doc.align("hspace_dec")
check("Decrease: the primary stays, every gap shrinks by one grid step",
      geo(s2)[0] == 70 and geo(s1)[0] == GRID and geo(s3)[0] == 200 - GRID, [geo(c)[0] for c in (s1, s2, s3, s4)])
reset(); sel(doc, s1, s3, s4, s2); doc.align("hspace_remove")
check("Remove: the controls touch, the primary stays",
      [geo(c)[0] for c in (s1, s2, s3, s4)] == [20, 70, 120, 170], [geo(c)[0] for c in (s1, s2, s3, s4)])
for c in f.controls:          # a column for vertical spacing
    c.props["Left"] = 40
s1.props["Top"], s2.props["Top"], s3.props["Top"], s4.props["Top"] = 0, 30, 100, 200
start = {c.name: geo(c) for c in f.controls}
sel(doc, s1, s2, s3, s4); doc.align("vspace_equal")
vg = [geo(b)[1] - (geo(a)[1] + geo(a)[3]) for a, b in ((s1, s2), (s2, s3), (s3, s4))]
check("Vertical Spacing > Make Equal", geo(s1)[1] == 0 and geo(s4)[1] == 200 and max(vg) - min(vg) <= 1, vg)
reset(); sel(doc, s1, s3, s4, s2); doc.align("vspace_remove")
check("Vertical Spacing > Remove", [geo(c)[1] for c in (s1, s2, s3, s4)] == [10, 30, 50, 70],
      [geo(c)[1] for c in (s1, s2, s3, s4)])
reset(); sel(doc, s1, s3, s4, s2); doc.align("vspace_inc")
check("Vertical Spacing > Increase", geo(s2)[1] == 30 and geo(s3)[1] == 100 + GRID)
reset(); sel(doc, s1, s3, s4, s2); doc.align("vspace_dec")
check("Vertical Spacing > Decrease", geo(s2)[1] == 30 and geo(s3)[1] == 100 - GRID)

# ===================================================================== Center in Form
doc, view, f = make([("Button", "c1", 10, 10), ("Button", "c2", 10, 50),
                     ("TabControl", "tabs", 200, 100, 240, 200), ("Button", "c3", 8, 8, 0, 0, "tabs")])
c1, c2, c3, tabs = (f.find(n) for n in ("c1", "c2", "c3", "tabs"))
sel(doc, c1, c2)
n0 = undo_n(doc)
doc.align("center_form_h")
doc.align("center_form_v")
check("Center in Form keeps the controls apart (moves them as one group)", geo(c2)[1] - geo(c1)[1] == 40,
      (geo(c1), geo(c2)))
check("Center in Form: the group is centred on the form", geo(c1)[0] == (480 - 75) // 2
      and geo(c1)[1] == (360 - (40 + 23)) // 2, (geo(c1), geo(c2)))
check("Center in Form: one undo step per command", undo_n(doc) == n0 + 2)
from radide.layout import client_size  # noqa: E402
sel(doc, c3)
doc.align("center_form_h")
cw, _ch = client_size(f, tabs)
check("Center in Form inside a TabControl uses its page (client) area", geo(c3)[0] == (cw - 75) // 2, (geo(c3), cw))
check("Center in Form available with ONE control", doc.can_format("center_form_v"))

# ===================================================================== Order
doc, view, f = make([("Button", "o1", 10, 10), ("Button", "o2", 20, 20), ("Button", "o3", 30, 30),
                     ("Button", "o4", 40, 40)])
o1, o2, o3, o4 = (f.find(n) for n in ("o1", "o2", "o3", "o4"))
sel(doc, o2, o1)
n0 = undo_n(doc)
doc.reorder(list(doc.selection), True)
check("Bring to Front moves EVERY selected control, keeping their order",
      [c.name for c in f.controls] == ["o3", "o4", "o1", "o2"], [c.name for c in f.controls])
check("Bring to Front: one undo step", undo_n(doc) == n0 + 1)
doc.reorder(list(doc.selection), True)
check("Bring to Front again (already in front): no empty undo step", undo_n(doc) == n0 + 1)
sel(doc, o4)
doc.reorder(list(doc.selection), False)
check("Send to Back", f.controls[0] is o4)

# ===================================================================== mouse: drag a group
doc, view, f = make([("Button", "m1", 13, 13), ("Button", "m2", 30, 51), ("Button", "far", 300, 200, 75, 23)])
m1, m2, far = (f.find(n) for n in ("m1", "m2", "far"))
ov = view.overlay
sel(doc, m2, m1)                           # primary m1
gap0 = (geo(m2)[0] - geo(m1)[0], geo(m2)[1] - geo(m1)[1])
n0 = undo_n(doc)
drag(ov, (20, 20), (61, 41))
check("drag: the group keeps its spacing (not each control snapped alone)",
      (geo(m2)[0] - geo(m1)[0], geo(m2)[1] - geo(m1)[1]) == gap0, (geo(m1), geo(m2)))
check("drag: the primary lands on the grid", geo(m1)[0] % GRID == 0 and geo(m1)[1] % GRID == 0, geo(m1))
check("drag: ONE undo step", undo_n(doc) == n0 + 1, undo_n(doc) - n0)
doc.undo()
rebind()
check("drag undo restores both", geo(m1)[:2] == (13, 13) and geo(m2)[:2] == (30, 51))
m1.props["Left"], m1.props["Top"] = 16, 16          # on the grid now
sel(doc, m1)
n0 = undo_n(doc)
p0 = geo(m1)
drag(ov, (40, 25), (43, 26))              # snaps back to where it was
check("a drag that ends where it started is no undo step", undo_n(doc) == n0 and geo(m1) == p0,
      (undo_n(doc) - n0, geo(m1)))
drag(ov, (40, 25), (81, 48), mods=Mod.AltModifier)
check("Alt+drag: no snapping (pixel exact)", geo(m1)[:2] == (16 + 41, 16 + 23), geo(m1))
doc.undo()
rebind()
# snapline: m1's right edge (16+75=91) next to far's right edge (375): drag so it would land 2 px off
sel(doc, m1)
mouse(ov, "press", (40, 25))
mouse(ov, "move", (100, 60))
mouse(ov, "move", (40 + (375 - 91) - 2, 60))
check("snaplines: the right edge sticks to another control's right edge",
      geo(m1)[0] + geo(m1)[2] == 375, geo(m1))
check("snaplines: a blue line is shown during the drag", bool(ov.snaplines))
img = ov.grab().toImage()
ln = ov.snaplines[0] if ov.snaplines else None
px = img.pixelColor(ln.x1(), (ln.y1() + ln.y2()) // 2) if ln else None
check("snapline painted (blue pixel in widget.grab)", px is not None and px.blue() > 200 and px.red() < 80,
      px.name() if px else None)
key(ov, Qt.Key.Key_Escape)
mouse(ov, "release", (40 + (375 - 91) - 2, 60))
rebind()
check("Esc during a drag puts the control back", geo(m1)[:2] == (16, 16), geo(m1))
check("Esc during a drag leaves no undo / redo step", not doc.can_redo() and doc.form.find("m1") is not None)
check("no snaplines after the drag", not view.overlay.snaplines)

# ---- group resize
doc, view, f = make([("Button", "r1", 16, 16), ("Button", "r2", 16, 64, 100, 30)])
r1, r2 = f.find("r1"), f.find("r2")
ov = view.overlay
sel(doc, r2, r1)
right_handle = (16 + 75 - 1, 16 + 23 // 2)        # handle 3 (right, middle) of the primary
n0 = undo_n(doc)
drag(ov, right_handle, (right_handle[0] + 21, right_handle[1]))
dw = geo(r1)[2] - 75
check("resize: the primary's edge goes to the grid / snapline", dw > 0, geo(r1))
check("resize: every selected control changes by the same amount (VS)", geo(r2)[2] == 100 + dw, (geo(r1), geo(r2)))
check("resize: ONE undo step", undo_n(doc) == n0 + 1)

# ===================================================================== keyboard
doc, view, f = make([("Button", "k1", 16, 16), ("Button", "k2", 16, 64),
                     ("Panel", "kd", 0, 0, 100, 40, "", {"Dock": "Bottom"})])
k1, k2, kd = (f.find(n) for n in ("k1", "k2", "kd"))
ov = view.overlay
ov.setFocus()
sel(doc, k2, k1)
n0 = undo_n(doc)
key(ov, Qt.Key.Key_Right)
check("arrow key moves every selected control 1 px", geo(k1)[0] == 17 and geo(k2)[0] == 17)
check("one undo step per arrow key", undo_n(doc) == n0 + 1)
key(ov, Qt.Key.Key_Right, Mod.ControlModifier)
check("Ctrl+arrow moves to the next grid line", geo(k1)[0] == 24 and geo(k2)[0] == 24, geo(k1))
key(ov, Qt.Key.Key_Down, Mod.ShiftModifier)
check("Shift+arrow resizes every selected control by 1 px", geo(k1)[3] == 24 and geo(k2)[3] == 24)
key(ov, Qt.Key.Key_Right, Mod.ShiftModifier | Mod.ControlModifier)
check("Ctrl+Shift+arrow resizes to the next grid line", (geo(k1)[0] + geo(k1)[2]) % GRID == 0, geo(k1))
sel(doc, kd)
n0 = undo_n(doc)
g0 = geo(kd)
key(ov, Qt.Key.Key_Up)
check("arrow on a docked control: no move, no empty undo step", geo(kd) == g0 and undo_n(doc) == n0)

# ---- Tab / Shift+Tab / Esc
sel(doc, k1)
key(ov, Qt.Key.Key_Tab)
nxt = doc.selected
check("Tab selects the next control", nxt is not None and nxt is not k1, getattr(nxt, "name", None))
key(ov, Qt.Key.Key_Tab, Mod.ShiftModifier)
check("Shift+Tab selects the previous control", doc.selected is k1, getattr(doc.selected, "name", None))
check("focus stays in the designer after Tab", ov.hasFocus() or QApplication.focusWidget() in (ov, None))

doc, view, f = make([("GroupBox", "grp", 40, 40, 200, 120), ("Button", "inb", 16, 24, 0, 0, "grp")])
grp, inb = f.find("grp"), f.find("inb")
ov = view.overlay
ov.setFocus()
sel(doc, inb)
key(ov, Qt.Key.Key_Escape)
check("Esc selects the parent container", doc.selected is grp, getattr(doc.selected, "name", None))
key(ov, Qt.Key.Key_Escape)
check("Esc again selects the form", doc.selected is None and not doc.selection)

# ---- rubber band, Ctrl / Shift click
doc, view, f = make([("Button", "x1", 16, 16), ("Button", "x2", 120, 16),
                     ("Panel", "xp", 16, 80, 200, 100), ("Button", "xin", 8, 8, 0, 0, "xp")])
x1, x2, xp, xin = (f.find(n) for n in ("x1", "x2", "xp", "xin"))
ov = view.overlay
drag(ov, (4, 4), (300, 250))
check("rubber band selects the controls of the form, not those inside a container",
      set(doc.selection) == {x1, x2, xp}, [c.name for c in doc.selection])
sel(doc, x1)
drag(ov, (110, 4), (300, 30), mods=Mod.ShiftModifier)
check("Shift+band adds to the selection", set(doc.selection) == {x1, x2})
drag(ov, (4, 4), (300, 30), mods=Mod.ControlModifier)
check("Ctrl+band toggles (x1, x2 out)", not doc.selection, [c.name for c in doc.selection])
sel(doc, x1)
mouse(ov, "press", (130, 20), Mod.ShiftModifier); mouse(ov, "release", (130, 20), Mod.ShiftModifier)
check("Shift+click adds a control", doc.selection == [x1, x2])
mouse(ov, "press", (20, 20), Mod.ControlModifier); mouse(ov, "release", (20, 20), Mod.ControlModifier)
check("Ctrl+click takes a selected control out again", doc.selection == [x2])

# ===================================================================== clipboard
doc, view, f = make([("Button", "p1", 16, 16), ("Panel", "pp", 160, 120, 200, 120),
                     ("TabControl", "pt", 16, 200, 220, 140)])
p1, pp, pt = (f.find(n) for n in ("p1", "pp", "pt"))
sel(doc, p1)
doc.copy()
n0 = undo_n(doc)
doc.paste()
a = doc.selected
check("paste next to the original shifts the copy", a is not p1 and geo(a)[:2] == (32, 32), geo(a))
check("paste: one undo step", undo_n(doc) == n0 + 1)
doc.paste()
b = doc.selected
check("pasting again cascades (not on top of the first copy)", geo(b)[:2] == (48, 48), geo(b))
sel(doc, pp)
doc.paste()
c = doc.selected
check("paste with a container selected goes INTO the container", c.parent == "pp" and geo(c)[:2] == (16, 16),
      (c.parent, geo(c)))
pt.props["SelectedIndex"] = 1
sel(doc, pt)
doc.paste()
c = doc.selected
check("paste onto a TabControl goes to its selected page", c.parent == "pt" and int(c.props.get("TabPage", 0)) == 1,
      (c.parent, c.props.get("TabPage")))
sel(doc, p1)
doc.copy()
doc2, view2, f2 = make([])
doc2.paste()
check("paste into another (empty) form keeps the Location", geo(doc2.selected)[:2] == (16, 16), geo(doc2.selected))

# ===================================================================== creating controls
doc, view, f = make([("Panel", "cp", 200, 100, 200, 150)])
cp = f.find("cp")
ov = view.overlay
TOOL_STATE.set("Button")
n0 = undo_n(doc)
drag(ov, (16, 16), (130, 58))
new = doc.selected
check("click-drag with a Toolbox tool draws the control (its size)", new is not None and new.type == "Button"
      and geo(new) == (16, 16, 112, 40), geo(new) if new else None)
check("drawing a control is ONE undo step", undo_n(doc) == n0 + 1)
check("the pointer tool is back after placing", TOOL_STATE.current is None)
TOOL_STATE.set("TextBox")
mouse(ov, "press", (240, 140)); mouse(ov, "release", (240, 140))
tb = doc.selected
check("a click with a tool places a default-size control (inside the container under it)",
      tb.type == "TextBox" and tb.parent == "cp" and geo(tb)[2:] == (100, 20), (tb.parent, geo(tb)))
sel(doc, cp)
added = view.add_default("Label")
check("Toolbox double-click adds into the selected container", added is not None and added.parent == "cp")
added2 = view.add_default("Label")
check("Toolbox double-click again cascades", geo(added2)[:2] != geo(added)[:2], (geo(added), geo(added2)))

# ===================================================================== containers: drag in / out
doc, view, f = make([("GroupBox", "g", 200, 40, 200, 160), ("Button", "gb", 16, 16)])
g, gb = f.find("g"), f.find("gb")
ov = view.overlay
sel(doc, gb)
n0 = undo_n(doc)
drag(ov, (40, 28), (260, 100))
check("drag into a GroupBox (mouse pointer over it) reparents", gb.parent == "g", gb.parent)
ax, ay = f.abs_pos(gb)
check("reparenting keeps the control where it was dropped", ax >= 200 and ay >= 40, (ax, ay))
check("move + reparent are ONE undo step", undo_n(doc) == n0 + 1)
drag(ov, (ax + 30, ay + 12), (40, 300))
check("drag out of the GroupBox goes back to the form", gb.parent == "", gb.parent)
doc.undo(); doc.undo()
rebind()
check("undo twice: back at the start", gb.parent == "" and geo(gb)[:2] == (16, 16), (gb.parent, geo(gb)))

# ===================================================================== form resize: anchors / dock
doc, view, f = make([("Button", "ar", 380, 300, 75, 23, "", {"Anchor": "Bottom, Right"}),
                     ("TextBox", "aw", 16, 16, 448, 20, "", {"Anchor": "Top, Left, Right"}),
                     ("Panel", "df", 0, 0, 10, 10, "", {"Dock": "Fill"})])
ar, aw, df = (f.find(n) for n in ("ar", "aw", "df"))
doc._relayout(emit=False)
n0 = undo_n(doc)
doc.checkpoint()
doc.set_prop(None, "Width", 560, record=False)
doc.set_prop(None, "Height", 400, record=False)
check("form resize: Bottom, Right anchored control keeps its distance", geo(ar)[:2] == (460, 340), geo(ar))
check("form resize: Left + Right anchored control stretches", geo(aw)[2] == 528, geo(aw))
check("form resize: Dock Fill fills the form", geo(df) == (0, 0, 560, 400), geo(df))
doc.undo()
rebind()
check("form resize: one undo step back", geo(ar)[:2] == (380, 300) and int(f.props["Width"]) == 480)

# ===================================================================== multi-select properties
from radide.properties import PropertiesPanel  # noqa: E402
doc, view, f = make([("Button", "q1", 16, 16), ("Label", "q2", 16, 64), ("Button", "q3", 16, 100)])
q1, q2, q3 = (f.find(n) for n in ("q1", "q2", "q3"))
q1.props["Text"], q3.props["Text"] = "Same", "Different"
pp_ = PropertiesPanel()
pp_.set_document(doc, None)
sel(doc, q1, q3, q2)
names = {d.name for d in pp_._defs()}
check("multi-select shows only the common properties, never (Name)", "Name" not in names and "Text" in names
      and "Left" in names)
sel(doc, q1, q3)
check("multi-select: differing values are blank", "Text" in pp_._mixed() and "Width" not in pp_._mixed())
n0 = undo_n(doc)
pp_._set("Text", "OK")
check("multi-select edit applies to all, ONE undo step", q1.props["Text"] == q3.props["Text"] == "OK"
      and undo_n(doc) == n0 + 1)
pp_._set("Text", "OK")
check("multi-select edit with no change: no empty undo step", undo_n(doc) == n0 + 1)
q3.props.pop("ForeColor", None)
pp_._set("ForeColor", "#FF0000")
check("multi-select edit reaches a control still at the default value", q3.props.get("ForeColor") == "#FF0000")

# ---- delete
doc, view, f = make([("Panel", "dp", 16, 16, 200, 100), ("Button", "dc", 8, 8, 0, 0, "dp"), ("Button", "dk", 16, 200)])
ov = view.overlay
ov.setFocus()
sel(doc, f.find("dp"))
n0 = undo_n(doc)
key(ov, Qt.Key.Key_Delete)
check("Delete removes the container with its children", [c.name for c in f.controls] == ["dk"])
check("Delete: one undo step", undo_n(doc) == n0 + 1)
doc.undo()
check("undo brings them back", {c.name for c in f.controls} == {"dp", "dc", "dk"})

# ---- Tab Order mode: Ctrl+click restarts the numbering from a control
doc, view, f = make([("Button", "t1", 16, 16), ("Button", "t2", 16, 64), ("Button", "t3", 16, 112)])
t1, t2, t3 = (f.find(n) for n in ("t1", "t2", "t3"))
t2.props["TabIndex"] = 5
view.set_tab_order_mode(True)
ov = view.overlay
mouse(ov, "press", (20, 70), Mod.ControlModifier); mouse(ov, "release", (20, 70), Mod.ControlModifier)
mouse(ov, "press", (20, 118)); mouse(ov, "release", (20, 118))
check("Tab Order: Ctrl+click continues the numbering after that control", int(t3.props["TabIndex"]) == 6,
      t3.props.get("TabIndex"))
key(ov, Qt.Key.Key_Escape)
check("Esc ends Tab Order mode", not view.tab_order_mode)

# ===================================================================== zoom
doc, view, f = make([("Button", "z1", 16, 16), ("Button", "z2", 16, 64)])
z1, z2 = f.find("z1"), f.find("z2")
view.set_zoom(1.5)
pump()
ov = view.overlay
ov.setFocus()
sel(doc, z2, z1)
key(ov, Qt.Key.Key_Right)
check("zoom 150%: arrow key moves the selection 1 form pixel", geo(z1)[0] == 17 and geo(z2)[0] == 17)
drag(ov, (40, 25), (80, 25))
check("zoom 150%: drag moves the group in form coordinates", geo(z1)[0] % GRID == 0 and geo(z2)[0] == geo(z1)[0],
      (geo(z1), geo(z2)))
doc.align("center_form_h")
check("zoom 150%: Center in Form", geo(z1)[0] == (480 - 75) // 2)
shot = OUT / "vsparity_zoom.png"
view.grab().save(str(shot))
print("SHOT", shot)
view.set_zoom(1.0)

# ===================================================================== the IDE's Format menu
from radide.app import MainWindow  # noqa: E402
src = ROOT / "samples/Tests/Languages/PythonTk_Form"
proj = OUT / "PythonTk_Form"
shutil.copytree(src, proj)
w = MainWindow()
w.resize(1400, 900)
w.show()
pump(20)
w.open_project(proj, ask=False)
pump(20)
w.open_designer("Form1")
pump(10)
d = w._current_designer()
check("IDE: designer opened", d is not None)
if d is not None:
    doc = d.doc
    titles = [a.text().replace("&", "") for a in w.format_menu.actions()]
    check("Format menu has Align, Make Same Size, Horizontal / Vertical Spacing, Center in Form, Order, Lock Controls",
          all(t in titles for t in ("Align", "Make Same Size", "Horizontal Spacing", "Vertical Spacing",
                                    "Center in Form", "Order", "Lock Controls")), titles)
    vis = [c for c in doc.form.ordered() if c.props.get("Dock") in (None, "", "None")]
    doc.select_many(vis[:1])
    w._sync_format_menu()
    fa = w.format_actions
    check("one control: Align Lefts disabled, Center in Form + Align to Grid enabled",
          not fa["left"].isEnabled() and fa["center_form_h"].isEnabled() and fa["to_grid"].isEnabled())
    if len(vis) >= 3:
        doc.select_many(vis[:2])
        w._sync_format_menu()
        check("two controls: Align enabled, Make Equal spacing disabled",
              fa["left"].isEnabled() and not fa["hspace_equal"].isEnabled() and fa["hspace_remove"].isEnabled())
        doc.select_many(vis[:3])
        w._sync_format_menu()
        check("three controls: Make Equal enabled", fa["hspace_equal"].isEnabled())
    doc.select_many([])
    w._sync_format_menu()
    check("nothing selected: Align / Center disabled, Order disabled",
          not fa["left"].isEnabled() and not fa["center_form_h"].isEnabled() and not w.a_bring_front.isEnabled())
    am = next(a.menu() for a in w.format_menu.actions() if a.text().replace("&", "") == "Align")
    check("nothing selected: the Align submenu itself is greyed", not am.isEnabled())
    import json  # noqa: E402
    ar = json.loads((ROOT / "radide/i18n/ar.json").read_text(encoding="utf-8"))["strings"]
    missing = [s for s in ("Horizontal Spacing", "Vertical Spacing", "Make Equal", "Increase", "Decrease", "Remove",
                           "to Grid", "Size to Grid", "Order", "Lefts", "Centers", "Rights", "Tops", "Middles",
                           "Bottoms", "Width", "Height", "Both", "Vertically", "Horizontally", "Make Same Size",
                           "Center in Form", "Bring to Front", "Send to Back") if s not in ar]
    check("Arabic translations for the Format menu", not missing, missing)
    d.grab().save(str(OUT / "vsparity_ide.png"))
    w.close()
    pump(5)

ok = sum(1 for _, c in RESULTS if c)
print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}", flush=True)
QSettings().clear()
sys.stdout.flush()
os._exit(0 if ok == len(RESULTS) else 1)
