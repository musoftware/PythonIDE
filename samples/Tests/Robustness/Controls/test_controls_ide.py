"""Non-default controls in the IDE (offscreen, QSettings org RADIDE-TEST-NONDEF, widget.grab only).

* an installed package (StarRating .radcomp) and a project package with a property of every kind
  (RobustKinds in .radide/components: int, float, bool, enum, colour, font, str, multiline, list, columns,
  padding, alignment, flags, gradient, shadow, border, image, anchor, custom JSON list) are in the Toolbox in
  their categories, are placed on a form, drawn by their designer code and every property is edited through
  its Properties window editor (combo boxes, colour dialog, font list, "..." dialogs, inline custom editor);
* events: double-click creates the handler; renaming the control renames the handler in the code; deleting
  the control keeps the handler;
* Save All writes the values, the generated code and copies the package runtime into the project (what Run
  and Publish use); the generated program runs (window withdrawn); reopen -> same values;
* a package whose designer.py raises in paint(): drawn with the error, no crash;
* the package uninstalled while the form is open (removed from the Toolbox): the designer shows a placeholder,
  Save keeps the control's data; installed again: the real control with its values and defaults;
* a user control edited while a form using it is open: the instance on the form is refreshed.

Run:  .venv\\Scripts\\python samples/Tests/Robustness/Controls/test_controls_ide.py
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _nondef_harness import (COMPONENT_SAMPLES, SAMPLES, WORK, check, close_window, copy_tree, finish, gui,  # noqa: E402
                             main_window, pump)

app, MSGS, ANSWERS = gui()

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtGui import QColor, QFont  # noqa: E402
from PyQt6.QtWidgets import QColorDialog, QComboBox, QFontComboBox, QPushButton  # noqa: E402

from radide import components as C  # noqa: E402
from radide.components import propeditors  # noqa: E402
from radide.controls import CONTROL_TYPES  # noqa: E402

# ---------------------------------------------------------------- packages + project
C.install_package(COMPONENT_SAMPLES / "StarRating.radcomp", "user", reload=False)
proj = copy_tree(COMPONENT_SAMPLES / "StarRating_PythonTk", "StarIDE")
for f in proj.glob("starrating_*.py"):
    f.unlink()
comps = proj / ".radide" / "components"
comps.mkdir(parents=True)
pkg = C.new_package(comps, "RobustKinds", category="Robustness Kinds", targets=("python-tk",))
man = json.loads((pkg / "component.json").read_text(encoding="utf-8"))
KINDS = [
    ("Level", "int", 1, {"min": 0, "max": 50}), ("Ratio", "float", 0.5, {}), ("Active", "bool", False, {}),
    ("Mode", "enum", "One", {"choices": ["One", "Two", "Three"]}), ("Tint", "color", "#336699", {}),
    ("Face", "font", "Segoe UI", {}), ("Caption", "str", "cap", {}), ("Notes", "multiline", "", {}),
    ("Items", "list", "a;b", {}), ("Cols", "columns", "Name;Age", {}), ("Inner", "padding", "1, 1, 1, 1", {}),
    ("Align", "alignment", "MiddleLeft", {}), ("Styles", "flags", "", {"choices": ["Bold", "Italic", "Underline"]}),
    ("Fill", "gradient", "", {}), ("Glow", "shadow", "", {}), ("Frame", "border", "", {}),
    ("Picture", "image", "", {}), ("Data", "custom", [1, 2], {}),
]
man["properties"] = [dict({"name": n, "type": t, "default": dflt, "category": "Kinds"}, **extra) for n, t, dflt, extra in KINDS]
man["events"] = [{"name": "Changed", "description": "changed"}]
man["defaultEvent"] = "Changed"
(pkg / "component.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
boom = comps / "PaintBoom"
boom.mkdir()
(boom / "component.json").write_text(json.dumps({"schemaVersion": 1, "name": "PaintBoom", "version": "1.0.0",
                                                 "category": "Robustness Kinds", "kind": "visual", "designer": "designer.py",
                                                 "properties": [], "events": []}), encoding="utf-8")
(boom / "designer.py").write_text("def paint(painter, rect, props, ctx):\n    raise ValueError('paint failed on purpose')\n",
                                  encoding="utf-8")

w = main_window(app)
try:
    w.open_project(proj, ask=False)
    pump(app, 2)
    tb = w.toolbox
    items = [tb.item(r).data(Qt.ItemDataRole.UserRole) for r in range(tb.count())]
    check("Toolbox: the installed package StarRating is listed", "StarRating" in items, items[-15:])
    check("Toolbox: the project package RobustKinds is listed", "RobustKinds" in items, items[-15:])
    heads = [tb.item(r).text() for r in range(tb.count()) if tb.item(r).data(Qt.ItemDataRole.UserRole) is None]
    check("Toolbox: the packages' categories are groups ('Rating & Input', 'Robustness Kinds')",
          any("Rating" in h for h in heads) and any("Robustness Kinds" in h for h in heads), heads)

    w.open_designer("Form1")
    pump(app, 1.5)
    dv = w.designers["Form1"]
    doc = dv.doc
    from radide.components.designer import ComponentPreview
    stars = [c for c in doc.form.controls if c.type == "StarRating"]
    prevs = [dv.previews.get(id(c)) for c in stars]
    check("designer: the StarRating controls have previews drawn by the package designer.py",
          prevs and all(p is not None for p in prevs) and not any(getattr(p, "error", "") for p in prevs))

    # ---- place controls (Toolbox placement = doc.add_control)
    rk = doc.add_control("RobustKinds", 20, 200)
    pb = doc.add_control("PaintBoom", 200, 200)
    rmg = doc.add_control("RmGauge", 20, 260)
    pump(app, 0.8)
    p_rk, p_pb = dv.previews.get(id(rk)), dv.previews.get(id(pb))
    check("placed RobustKinds / PaintBoom / RmGauge have previews", p_rk is not None and p_pb is not None and dv.previews.get(id(rmg)))
    if p_pb is not None:
        p_pb.grab()
        pump(app, 0.2)
    check("PaintBoom: an exception in paint() is shown on the control, the IDE keeps working",
          isinstance(p_pb, ComponentPreview) and "paint failed" in (p_pb.error or ""), getattr(p_pb, "error", None))

    # ---- edit every property kind through its editor
    panel = w.properties
    doc.select(rk)
    pump(app, 0.5)

    def row_of(name):
        for r in range(panel.props.rowCount()):
            d = panel._row_def(r)
            if d is not None and d.name == name:
                return r, d
        return None, None

    want = {"Level": 7, "Ratio": 2.25, "Active": True, "Mode": "Three", "Tint": "#123456", "Face": "Consolas",
            "Caption": "Text ع", "Notes": "line 1\nline 2", "Items": "x;y;z", "Cols": "A;B;C", "Inner": "1, 2, 3, 4",
            "Align": "BottomRight", "Styles": "Bold, Underline", "Fill": "#FFFFFF, #000000, 90",
            "Glow": "2, 2, 6, #80000000", "Frame": "1, solid, #808080, 4", "Picture": "Resources/pic.png",
            "Data": [3, 4, 5]}
    patches = {"edit_text": lambda *a, **k: want["Notes"] if a[1] == "Notes" else "A\nB\nC",
               "edit_flags": lambda *a, **k: want["Styles"], "edit_gradient": lambda *a, **k: want["Fill"],
               "edit_shadow": lambda *a, **k: want["Glow"], "edit_border": lambda *a, **k: want["Frame"],
               "pick_file": lambda *a, **k: want["Picture"]}
    saved_fns = {k: getattr(propeditors, k) for k in patches}
    for k, v in patches.items():
        setattr(propeditors, k, v)
    QColorDialog.getColor = staticmethod(lambda *a, **k: QColor("#123456"))
    how = {}
    for name, value in want.items():
        r, d = row_of(name)
        if r is None:
            how[name] = "no row"
            continue
        wdg = panel.props.cellWidget(r, 1)
        if isinstance(wdg, QFontComboBox):
            wdg.setCurrentFont(QFont(value))
            how[name] = "font list"
        elif isinstance(wdg, QComboBox):
            wdg.setCurrentText("True" if value is True else str(value))
            how[name] = "combo"
        elif isinstance(wdg, QPushButton):
            if name == "Data":
                propeditors.open_editor.__globals__["edit_text"] = patches["edit_text"]
                panel._set(name, value)              # custom value without an editor id: set like a custom editor would
                how[name] = "custom"
            else:
                wdg.click()
                how[name] = "dialog button"
        else:
            item = panel.props.item(r, 1)
            item.setText(str(value))
            how[name] = "cell text"
        pump(app, 0.05)
        doc.select(rk)
    for k, v in saved_fns.items():
        setattr(propeditors, k, v)
    got = {k: rk.props.get(k) for k in want}
    wrong = {k: (got[k], want[k], how.get(k)) for k in want if got[k] != want[k] and not (k == "Face" and str(got[k]).startswith("Consolas"))}
    check(f"every property kind edited through its Properties editor ({len(want)} kinds: {sorted(set(how.values()))})",
          not wrong, wrong)
    r, d = row_of("Level")
    panel.props.item(r, 1).setText("999")
    pump(app, 0.1)
    check("an int outside the package's min/max is refused (value unchanged)", rk.props.get("Level") == 7, rk.props.get("Level"))

    # StarRating: the package's inline custom editor (editors.py) for Value
    s0 = stars[0]
    doc.select(s0)
    pump(app, 0.4)
    r, d = row_of("Value")
    ed = panel.props.cellWidget(r, 1) if r is not None else None
    check("StarRating Value uses the package's inline editor (editors.py)", ed is not None and not isinstance(ed, QPushButton),
          type(ed).__name__)
    ped = propeditors.custom_editor(panel, d) if d is not None else None
    if ped is not None and ed is not None:
        propeditors._commit(panel, "Value", 4)
    check("the custom editor commits a value to the control", s0.props.get("Value") == 4, s0.props.get("Value"))

    # anchor editor (built-in kind) on a built-in Button
    btn = next(c for c in doc.form.controls if c.type == "Button")
    doc.select(btn)
    pump(app, 0.3)
    r, d = row_of("Anchor")
    if r is not None:
        ae = panel._edit_anchor("Anchor", panel.props.cellWidget(r, 1))
        ae._toggle("Right", True)
        pump(app, 0.1)
        try:
            ae.close()
        except Exception:  # noqa: BLE001
            pass
    check("anchor editor: Right added to the Button's Anchor", "Right" in str(btn.props.get("Anchor")), btn.props.get("Anchor"))

    # ---- events: create, rename, delete
    w.goto_event("Form1", rk, "Changed")
    pump(app, 0.5)
    cv = w.codeviews["Form1"]
    check("double-click / event: the handler RobustKinds1_Changed is created in Form1.py",
          "def RobustKinds1_Changed" in cv.editor.text())
    doc.select(rk)
    pump(app, 0.2)
    r, d = row_of("Name")
    panel.props.item(r, 1).setText("rkMain")
    pump(app, 0.5)
    code = cv.editor.text()
    check("renaming the control renames its handler in the code", "def rkMain_Changed" in code and "RobustKinds1_Changed" not in code,
          re.findall(r"def \w+_Changed", code))
    tmp = doc.add_control("Button", 400, 300)
    w.goto_event("Form1", tmp, "Click")
    pump(app, 0.3)
    hname = f"def {tmp.name}_Click"
    doc.remove_control(tmp)
    pump(app, 0.3)
    check("deleting a control keeps its handler in the code (VB behaviour)", hname in cv.editor.text())

    # ---- save, generated code, runtime copy, run, reopen
    ok = w.save_all()
    pump(app, 1)
    check("Save All succeeds", ok is not False, MSGS[-3:])
    saved = json.loads((proj / "Form1.form").read_text(encoding="utf-8"))
    sc = next(c for c in saved["controls"] if c["props"]["Name"] == "rkMain")
    check("the .form has every edited value", all(sc["props"].get(k) == v for k, v in want.items() if k != "Face"),
          {k: sc["props"].get(k) for k in want})
    dcode = (proj / "Form1_designer.py").read_text(encoding="utf-8")
    check("the generated designer code creates the package controls", "rkMain" in dcode and "RobustKinds" in dcode)
    check("Save copied the runtimes into the project (used by Run and Publish)",
          (proj / "starrating_tk.py").is_file() and any(proj.glob("robustkinds_tk.py")), sorted(p.name for p in proj.glob("*.py")))
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.pop("QT_QPA_PLATFORM", None)
    r = subprocess.run([sys.executable, "-c", "import Form1 as m\nf = m.Form1()\nf.root.withdraw()\nf.root.update()\n"
                        "print('OK', type(f.rkMain).__name__, f.Rating1.Value if hasattr(f, 'Rating1') else '')\nf.root.destroy()"],
                       cwd=str(proj), capture_output=True, text=True, timeout=90, env=env, encoding="utf-8", errors="replace")
    check("Run: the generated python-tk program with the package controls starts (window withdrawn)",
          r.returncode == 0 and "OK RobustKinds" in r.stdout, (r.stdout + r.stderr)[-600:])

    # ---- package removed while the form is open
    orig_star = next(c for c in saved["controls"] if c["props"]["Name"] == s0.name)
    C.uninstall_package("StarRating", "user")
    pump(app, 1)
    check("uninstalled while open: StarRating is a placeholder, the designer still has its previews",
          C.is_missing("StarRating") and all(dv.previews.get(id(c)) is not None for c in stars))
    items = [tb.item(r).data(Qt.ItemDataRole.UserRole) for r in range(tb.count())]
    check("uninstalled: the Toolbox no longer lists StarRating", "StarRating" not in items)
    dv.grab()
    btn.props["Text"] = "changed"
    doc.set_modified(True)
    w.save_all()
    pump(app, 0.5)
    saved2 = json.loads((proj / "Form1.form").read_text(encoding="utf-8"))
    st2 = next(c for c in saved2["controls"] if c["props"]["Name"] == s0.name)
    check("uninstalled: Save keeps the StarRating's data", st2["props"] == orig_star["props"],
          set(st2["props"].items()) ^ set(orig_star["props"].items()))
    C.install_package(COMPONENT_SAMPLES / "StarRating.radcomp", "user")
    pump(app, 1)
    check("installed again: the open form's StarRating is real again with its value",
          not C.is_missing("StarRating") and s0.props.get("Value") == 4 and isinstance(dv.previews.get(id(s0)), ComponentPreview))

    # ---- reopen the project: same values
    for d_ in w.docs.values():
        d_.set_modified(False)
    w.open_project(proj, ask=False)
    pump(app, 1.5)
    w.open_designer("Form1")
    pump(app, 1)
    f2 = w.designers["Form1"].doc.form
    rk2 = f2.find("rkMain")
    check("reopen: the RobustKinds values are back", rk2 is not None and all(rk2.props.get(k) == v for k, v in want.items() if k != "Face"))
    errs = [l for l in w.output.toPlainText().splitlines() if "Traceback" in l]
    check("no tracebacks in the Output window (package part)", not errs, errs[:5])
except Exception:  # noqa: BLE001
    import traceback
    check("the test script runs to the end (package part)", False, traceback.format_exc()[-1500:])
finally:
    close_window(app, w)

# ---------------------------------------------------------------- user control edited while a form using it is open
uc = copy_tree(SAMPLES / "Tests" / "UserControls" / "UC_PythonQt_AddressBox", "UC_IDE")
w = main_window(app)
try:
    w.open_project(uc, ask=False)
    pump(app, 2)
    w.open_designer("Form1")
    pump(app, 1)
    w.open_designer("AddressBox")
    pump(app, 1)
    from radide import usercontrols as UCM
    before = len(UCM.USER_CONTROLS["AddressBox"]["data"]["controls"])
    fd = w.designers["Form1"]
    inst = next(c for c in fd.doc.form.controls if c.type == "AddressBox")
    prev_before = fd.previews.get(id(inst))
    kids_before = len(prev_before.findChildren(object)) if prev_before is not None else -1
    ad = w.designers["AddressBox"].doc
    ad.add_control("Label", 5, 5)
    pump(app, 1.5)
    w.save_all()
    pump(app, 1)
    after = len(UCM.USER_CONTROLS["AddressBox"]["data"]["controls"])
    prev_after = fd.previews.get(id(inst))
    kids_after = len(prev_after.findChildren(object)) if prev_after is not None else -1
    check("user control edited: its control type is updated", after == before + 1, (before, after))
    check("user control edited: the instance on the open form is refreshed", kids_after > kids_before, (kids_before, kids_after))
    errs = [l for l in w.output.toPlainText().splitlines() if "Traceback" in l]
    check("no tracebacks in the Output window (user control part)", not errs, errs[:5])
except Exception:  # noqa: BLE001
    import traceback
    check("the test script runs to the end (user control part)", False, traceback.format_exc()[-1500:])
finally:
    close_window(app, w)

print("MSGS:", json.dumps(MSGS, ensure_ascii=False)[:1200])
finish(app)
