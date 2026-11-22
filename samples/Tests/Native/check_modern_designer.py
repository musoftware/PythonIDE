"""IDE designer checks of the RAD Modern (Rm*) packages (offscreen IDE, QSettings org RADIDE-TEST, widget.grab only):

the NativeShowcase form opens in the designer with every Rm control drawn by its package (rmpaint), the Toolbox
has the "Modern (RAD)" group, RmTabStrip pages work like TabControl pages (only the selected page's children are
shown, a click on a tab shows that page, a control dropped on the tab strip goes to the shown page), the
generated python-tk code of the form compiles.

Run:  .venv\\Scripts\\python samples/Tests/Native/check_modern_designer.py
"""
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
os.environ["QA_NAME"] = "modern_designer"
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ["RADIDE_TEST_NO_DIALOGS"] = "1"
sys.path.insert(0, str(ROOT / "samples" / "Tests" / "QA" / "Integration"))

from qh import WORK, check, finish, pump, shot, window  # noqa: E402

from PyQt6.QtCore import QPoint, Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402

proj = Path(WORK) / "modern_showcase"
shutil.rmtree(proj, ignore_errors=True)
shutil.copytree(ROOT / "samples" / "Modern" / "NativeShowcase", proj, ignore=shutil.ignore_patterns("__pycache__", "Publish"))

w = window()
try:
    w.open_project(proj, ask=False)
    pump(2)
    w.open_designer("Form1")
    pump(2)
    dv = w.designers["Form1"]
    doc = dv.doc
    form = doc.form
    rm = [c for c in form.controls if c.type.startswith("Rm") and not c.ctype.nonvisual]
    prev = {c.name: dv.previews.get(id(c)) for c in rm}
    check("every visual Rm control has a designer preview", all(prev.values()), [n for n, p in prev.items() if p is None])
    from radide.components.designer import ComponentPreview
    errs = {n: p.error for n, p in prev.items() if isinstance(p, ComponentPreview) and p.error}
    check("the previews draw without errors (rmpaint)", not errs, errs)
    img = prev["RmRibbon1"].grab().toImage()
    colors = {img.pixel(x, y) for x in range(0, img.width(), 7) for y in range(0, img.height(), 7)}
    check("the ribbon preview is drawn (many colours)", len(colors) > 6, len(colors))
    tb = w.toolbox
    names = [tb.item(r).data(Qt.ItemDataRole.UserRole) for r in range(tb.count())] if hasattr(tb, "count") else []
    check("the Toolbox lists the Rm controls", not names or {"RmRibbon", "RmGrid", "RmToast"} <= set(names), names[:10])
    by = {c.name: c for c in form.controls}
    check("tab strip page 0 shown, page 1 hidden", prev["gaCpu"].isVisible() and not prev["RmGrid1"].isVisible())
    ts = by["RmTabStrip1"]
    r = dv.overlay.abs_rect(ts)
    QTest.mouseClick(dv.overlay, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, r.topLeft() + QPoint(170, 16))
    pump(0.5)
    check("a click on the 'Customers' tab shows page 1", int(ts.props.get("SelectedIndex", 0)) == 1 and prev["RmGrid1"].isVisible()
          and not prev["gaCpu"].isVisible(), ts.props.get("SelectedIndex"))
    c = doc.add_control("RmButton", 20, 20, parent="RmTabStrip1")
    pump(0.3)
    check("a control dropped on the tab strip goes to the shown page", c.props.get("TabPage") == 1, c.props.get("TabPage"))
    shot(dv, "modern_designer")
    from radide.languages import get_plugin
    code = get_plugin("python-tk").generate_designer(form, "")
    try:
        compile(code, "<Form1 designer>", "exec")
        compiled = True
    except SyntaxError as e:
        compiled = str(e)
    check("the generated python-tk code compiles", compiled is True, compiled)
finally:
    finish(w)
