"""Designer UI of the data widgets (Qt canvas only, no Flutter needed). From the repository root:

    python samples/Tests/FlutterDesigner/DataFormsScreens/test_designer_data.py

Palette defaults (plain Container, named Form, RadioGroup), inspector editors (validators, spans, events menu
validate:), constructor switches ListView <-> ListView.builder and Text <-> Text.rich (with undo), and the
validator handler created by double-click (String? stub).
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "QA", "Integration"))
os.environ.setdefault("QA_NAME", "fd-designer-data")
import qh  # noqa: E402
from qh import check, pump, shot  # noqa: E402

from radide.flutterdesign import inspector as IN, model as M  # noqa: E402
from radide.flutterdesign.designer import FlutterDesigner  # noqa: E402

work = os.path.join(qh.WORK, "fd_designer_data")
shutil.rmtree(work, ignore_errors=True)
for sub in ("screens", "assets", "lib"):
    shutil.copytree(os.path.join(HERE, sub), os.path.join(work, sub))
shutil.copy2(os.path.join(HERE, "pubspec.yaml"), os.path.join(work, "pubspec.yaml"))

# ---- palette defaults
c = M.new_node("Container")
check("palette Container is plain (no box decoration)", "decoration" not in (c.get("props") or {}), c)
scr = M.Screen.new("Tmp")
f = M.new_node("Form", scr)
check("palette Form is named (GlobalKey)", f.get("name") == "form1", f)
rg = M.new_node("RadioGroup", scr)
check("palette RadioGroup has a name and two RadioListTiles",
      rg.get("name", "").startswith("rdo") and len(rg["slots"]["child"]["children"]) == 2, rg.get("name"))

d = FlutterDesigner(os.path.join(work, "screens", "SignUp.fscreen.json"), live=False)
d.resize(1400, 950)
d.show()
pump(0.5)
email = next(n for n, *_ in d.screen.walk() if n.get("name") == "txtEmail")
d.select(email["id"])
pump(0.2)
row = d.inspector.rows.get("validators")
check("inspector: validators editor", row is not None and isinstance(row.ed, IN.ValidatorsEd))
check("validators editor shows the rules", row is not None and len(row.ed.items) == 2)
row.ed.items.append({"rule": "maxLength", "value": 40})
row.ed._emit()
pump(0.2)
check("adding a rule edits the model", email["props"]["validators"][-1] == {"rule": "maxLength", "value": 40})
d.undo_stack.undo()
check("undo removes it", len(email["props"]["validators"]) == 2)
btn = next(n for n, *_ in d.screen.walk() if n.get("type") == "OutlinedButton")
d.select(btn["id"])
pump(0.2)
from PyQt6.QtWidgets import QMenu  # noqa: E402
m = QMenu()
d.inspector._event_menu(m, "onPressed")
labels = [a.text() for a in m.actions() if a.menu() is not None]
va = next(a.menu() for a in m.actions() if a.menu() is not None and a.text() == "Validate form")
check("Validate form menu lists the form", any("validate:form1" in a.text() for a in va.actions()), labels)
shot(d, "fd_designer_signup")
# a validator handler by double-click (VB style): a String? stub
promo = next(n for n, *_ in d.screen.walk() if n.get("name") == "txtName")
name = d.create_handler(promo["id"], "validator")
ev = open(os.path.join(work, "lib", "screens", "sign_up_events.dart"), encoding="utf-8").read()
check("validator stub returns String?", f"String? {name}(String? value)" in ev and "return null;" in ev, name)
d.close()

# ---- Catalog: constructor switches
d = FlutterDesigner(os.path.join(work, "screens", "Catalog.fscreen.json"), live=False)
d.resize(1400, 950)
d.show()
pump(0.5)
lst = next(n for n, *_ in d.screen.walk() if n.get("type") == "ListView")
tmpl_id = lst["slots"]["itemBuilder"]["id"]
d.set_ctor(lst["id"], None)
check("ListView.builder -> ListView: the template becomes the first child",
      not lst.get("ctor") and lst["children"][0]["id"] == tmpl_id and "itemCount" not in lst.get("props", {}))
check("no validation errors after the switch", not [i for i in d.screen.validate() if i.level == "error"])
d.set_ctor(lst["id"], "builder")
check("ListView -> builder: the first child becomes the template",
      lst.get("ctor") == "builder" and lst["slots"]["itemBuilder"]["id"] == tmpl_id and lst["props"]["itemCount"])
d.undo_stack.undo()
d.undo_stack.undo()
check("undo restores the builder", lst.get("ctor") == "builder" and lst["props"].get("items"))
title = d.screen.tree["slots"]["appBar"]["slots"]["title"]
d.set_ctor(title["id"], None)
check("Text.rich -> Text: data from the spans", title["props"].get("data") == "Fruit Market" and
      "spans" not in title["props"], title.get("props"))
d.set_ctor(title["id"], "rich")
check("Text -> Text.rich: one span", title["props"].get("spans") == [{"text": "Fruit Market"}], title.get("props"))
d.select(title["id"])
pump(0.2)
check("inspector: spans editor", isinstance(d.inspector.rows["spans"].ed, IN.TextSpansEd))
shot(d, "fd_designer_catalog")
d.close()
qh.finish()
