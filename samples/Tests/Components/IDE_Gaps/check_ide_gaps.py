"""IDE checks of the component package gaps (offscreen IDE, QSettings org RADIDE-TEST, widget.grab only):

1. Mouse drag from the Toolbox onto the designer: QTest presses the RatingBar item in the Toolbox and moves
   the mouse past the drag distance, so the Toolbox's own startDrag() builds the drag (MIME
   application/x-radide-control); the drop is delivered to the designer overlay as QDragEnter / QDragMove /
   QDrop events along the mouse path. (The offscreen platform has no drag implementation - QDrag.exec()
   returns at once - and on the Windows platform QDrag.exec() is OLE DoDragDrop, driven only by the real
   mouse; so the platform part of QDrag.exec is replaced by delivering the same events Qt would.)
   The control is created at the drop point, selected, and one Undo removes it.
2. Multi-select (Properties window): values that differ between the selected controls are blank, equal ones
   are shown; typing a value applies it to all of them in one undo step.
3. F1: a package control opens its help.md; a built-in control opens its built-in package help.md, with a
   link to the language reference (tkinter page for python-tk); words in the code editor keep their help.
4. "commonProperties": MiniGauge (packages/MiniGauge) lists ["position", "appearance", "Enabled"]: the
   Properties window shows only those common properties and the python-tk code passes only them.

Run:  python samples/Tests/Components/IDE_Gaps/check_ide_gaps.py
"""
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
os.environ["QA_NAME"] = "comp_ide_gaps"
os.environ["RADIDE_COMPONENT_PATH"] = str(HERE / "packages") + ";" + str(HERE.parent / "RatingBar")
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ["RADIDE_TEST_NO_DIALOGS"] = "1"
sys.path.insert(0, str(ROOT / "samples" / "Tests" / "QA" / "Integration"))
os.environ["RADIDE_COMPONENTS_DIR"] = str(Path(os.environ.get("TEMP", "/tmp")) / "radide-qa" / "comp_gaps_user")

from qh import WORK, app, check, finish, pump, shot, window  # noqa: E402

from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt  # noqa: E402
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

proj = Path(WORK) / "comp_gaps_tk"
shutil.rmtree(proj, ignore_errors=True)
shutil.copytree(HERE.parent / "RatingBar_PythonTk", proj, ignore=shutil.ignore_patterns("__pycache__"))
shutil.rmtree(proj / ".radide", ignore_errors=True)          # the dev copy (RADIDE_COMPONENT_PATH) is used

w = window()
w.open_project(proj, ask=False)
pump(2)
w.open_designer("Form1")
pump(1.5)
dv = w.designers["Form1"]
doc = dv.doc
tb = w.toolbox
from radide import components as C  # noqa: E402
check("packages loaded (RatingBar, MiniGauge)", C.is_component_type("RatingBar") and C.is_component_type("MiniGauge"))


def tb_item(name):
    for r in range(tb.count()):
        if tb.item(r).data(Qt.ItemDataRole.UserRole) == name:
            return tb.item(r)
    return None


# =============================================================== 1. drag from the Toolbox
import radide.toolbox as TBM  # noqa: E402

DROP_AT = QPoint(260, 150)          # overlay coordinates of the drop
delivered = []


class _Drag(TBM.QDrag):
    """QDrag whose exec() delivers the drag events to the designer overlay like the platform would."""
    def exec(self, *a, **k):
        md = self.mimeData()
        ov = dv.overlay
        start = ov.mapFromGlobal(tb.viewport().mapToGlobal(press_at))
        acts = Qt.DropAction.CopyAction
        btn, mods = Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
        path = [QPointF(start + (DROP_AT - start) * i / 6) for i in range(1, 7)]
        inside = [p for p in path if ov.rect().contains(p.toPoint())]
        e = QDragEnterEvent(inside[0].toPoint(), acts, md, btn, mods)
        QApplication.sendEvent(ov, e)
        delivered.append(("enter", e.isAccepted()))
        if not e.isAccepted():
            return Qt.DropAction.IgnoreAction
        for p in inside[1:]:
            m = QDragMoveEvent(p.toPoint(), acts, md, btn, mods)
            QApplication.sendEvent(ov, m)
            delivered.append(("move", m.isAccepted()))
        d = QDropEvent(QPointF(DROP_AT), acts, md, btn, mods, QEvent.Type.Drop)
        QApplication.sendEvent(ov, d)
        delivered.append(("drop", d.isAccepted()))
        return d.dropAction() if d.isAccepted() else Qt.DropAction.IgnoreAction


TBM.QDrag = _Drag
it = tb_item("RatingBar")
check("Toolbox has RatingBar", it is not None)
tb.scrollToItem(it)
pump(0.3)
press_at = tb.visualItemRect(it).center()
before = {c.name for c in doc.form.controls}
QTest.mousePress(tb.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, press_at)
for k in range(1, 8):
    QTest.mouseMove(tb.viewport(), press_at + QPoint(k * 5, k * 2))
    pump(0.02)
QTest.mouseRelease(tb.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                   press_at + QPoint(35, 14))
pump(0.5)
TBM.QDrag = TBM.QDrag.__mro__[1]
new = [c for c in doc.form.controls if c.name not in before]
check("drag events reached the designer and were accepted",
      [k for k, ok in delivered if ok] and all(ok for _k, ok in delivered) and delivered[-1][0] == "drop", delivered)
check("drop created a RatingBar", len(new) == 1 and new[0].type == "RatingBar", [(c.name, c.type) for c in new])
if new:
    c = new[0]
    px, py = doc.form.client_origin(None)
    check("created at the drop point (snapped)", abs(c.props["Left"] - (DROP_AT.x() - px)) <= 8 and
          abs(c.props["Top"] - (DROP_AT.y() - py)) <= 8, (c.props["Left"], c.props["Top"], px, py))
    check("the new control is selected", doc.selected is c)
    shot(dv, "comp_gaps_drag")
    doc.undo() if hasattr(doc, "undo") else None
    pump(0.3)
    check("Undo removes the dropped control", c.name not in {x.name for x in doc.form.controls})

# =============================================================== 2. multi-select
p = w.properties
b1 = doc.add_control("Button", 20, 200, "")
b2 = doc.add_control("Button", 120, 200, "")
doc.set_prop(b1, "Text", "One")
doc.set_prop(b2, "Text", "Two")
doc.set_prop(b1, "BackColor", "#FF0000")
doc.set_prop(b1, "Visible", False)
doc.select_many([b1, b2])
pump(0.3)


def row_of(name):
    for r in range(p.props.rowCount()):
        d = p._row_def(r)
        if d is not None and d.name == name:
            return r
    return -1


def cell_text(name):
    r = row_of(name)
    if r < 0:
        return None
    wdg = p.props.cellWidget(r, 1)
    if wdg is not None:
        return wdg.currentText() if hasattr(wdg, "currentText") else wdg.text()
    it2 = p.props.item(r, 1)
    return it2.text() if it2 else None


check("multi-select: differing Text is blank", cell_text("Text") == "", cell_text("Text"))
check("multi-select: differing BackColor / Visible are blank", cell_text("BackColor") == "" and
      cell_text("Visible") == "", (cell_text("BackColor"), cell_text("Visible")))
check("multi-select: equal Width / Enabled are shown", cell_text("Width") == "75" and cell_text("Enabled") == "True",
      (cell_text("Width"), cell_text("Enabled")))
check("multi-select: (Name) not shown", row_of("Name") < 0)
shot(p, "comp_gaps_multiselect")
r = row_of("Text")
p.props.item(r, 1).setText("Same")
pump(0.2)
check("multi-select: typed value applied to all", b1.props["Text"] == "Same" and b2.props["Text"] == "Same",
      (b1.props["Text"], b2.props["Text"]))
check("multi-select: now equal -> shown", cell_text("Text") == "Same", cell_text("Text"))
n1, n2 = b1.name, b2.name
doc.undo()                       # an undo restores the form: the controls are new objects
pump(0.2)
b1, b2 = doc.form.find(n1), doc.form.find(n2)
check("multi-select: one Undo restores both", (b1.props["Text"], b2.props["Text"]) == ("One", "Two"),
      (b1.props["Text"], b2.props["Text"]))
doc.select_many([b1, b2])
pump(0.2)
vr = row_of("Visible")
p.props.cellWidget(vr, 1).setCurrentText("True")
pump(0.2)
check("multi-select: picking a value in a blank drop-down applies it to all",
      b1.props["Visible"] is True and b2.props["Visible"] is True)

# =============================================================== 3. F1
from radide.features import help as H  # noqa: E402

w._current_designer = lambda: dv
w._current_code = lambda: None
rb = next(c for c in doc.form.controls if c.type == "RatingBar")
doc.select(rb)
kind, target = H.context_help(w)
v = getattr(w, "_help_viewer", None)
text = v.browser.toPlainText() if v is not None else ""
check("F1 on a package control: its help.md", kind == "control" and
      Path(target) == HERE.parent / "RatingBar" / "help.md" and "RatingBar" in text, (kind, target))
doc.select(b1)
kind, target = H.context_help(w)
text = v.browser.toMarkdown() if v is not None else ""
check("F1 on a built-in Button: its built-in package help.md", kind == "control" and
      Path(target).parts[-3:] == ("builtin", "Button", "help.md") and "Raises an event" in text, (kind, target))
check("... with the language reference link (python-tk -> tkinter)", "docs.python.org/3/library/tkinter" in text,
      text[-400:])
shot(v, "comp_gaps_f1")
check("F1 in code: a package type name -> help.md", H.help_target("python-tk", "RatingBar")[0] == "control")
check("F1 in code: other words unchanged", H.help_target("python-tk", "print") ==
      ("url", "https://docs.python.org/3/library/functions.html#print") and
      H.help_target("vb-basic", "MsgBox")[0] == "vb", (H.help_target("python-tk", "print"),))
check("F1 reference of a control for VB6 = bundled VB topic", H.control_reference("vb-basic", "Button")[0] == "vb")
del w._current_designer, w._current_code

# =============================================================== 4. commonProperties
g = doc.add_control("MiniGauge", 20, 260, "")
doc.select(g)
pump(0.3)
shown = {p._row_def(r).name for r in range(p.props.rowCount()) if p._row_def(r) is not None}
check("commonProperties: Properties shows the chosen sets",
      {"Name", "Left", "Top", "Width", "Height", "BackColor", "ForeColor", "Enabled", "Value"} == shown, shown)
check("commonProperties: the new control has only those properties",
      "FontName" not in g.props and "Anchor" not in g.props and "Visible" not in g.props, sorted(g.props))
w.save_all() if hasattr(w, "save_all") else None
pump(1)
from radide.languages import get_plugin  # noqa: E402
code = get_plugin("python-tk").generate_designer(doc.form, (proj / "Form1.py").read_text(encoding="utf-8"))
line = next((ln for ln in code.splitlines() if "MiniGauge(" in ln and "=" in ln), "")
check("commonProperties: generated python-tk code creates it", line.strip().startswith(f"self.{g.name} = MiniGauge("),
      line)
try:
    compile(code, "Form1_designer.py", "exec")
    ok = True
except SyntaxError as e:
    ok = str(e)
check("generated designer compiles", ok is True, ok)
doc.select_many([g, b2])
pump(0.3)
shown2 = {p._row_def(r).name for r in range(p.props.rowCount()) if p._row_def(r) is not None}
check("multi-select of MiniGauge + Button: only the shared properties", "FontName" not in shown2 and
      "BackColor" in shown2 and "Value" not in shown2, shown2)
finish(w)
