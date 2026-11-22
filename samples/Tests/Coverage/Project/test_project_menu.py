"""Coverage: the Project menu, the designer's right-click menu and Site > Publish Preview (functional, offscreen
IDE, sandbox copies of the samples).

* Project > Open Project Folder: Explorer is asked to show the project folder (os.startfile recorded).
* Project > Add Existing Item: QFileDialog.getOpenFileNames returns a sandbox .py file -> it is copied into the
  project folder, listed in project.radproj "modules" and in Solution Explorer.
* Designer right-click on the form > Events > FormClosing (the sample's handler removed first): the handler
  stub "def Form1_FormClosing(self, e)" appears in Form1's code and the code editor is shown; the next menu shows
  FormClosing in bold (handler exists).
* Designer right-click on Button1 > Cut: the control leaves the form and is on the clipboard (radide control
  MIME); right-click on the form > Paste brings it back (type, text, location); Edit > Undo removes the pasted
  control again, a second Undo restores the cut one.
* Project > Add User Control: OK on the "Add User Control" dialog creates CovPanel.form (a user control in
  project.radproj "forms") and opens it in its designer.
* Project > Add Report: OK on the "Add Report" dialog (blank report) writes SalesReport.rpt.json + the
  radreport.py runtime, opens it in the Report Designer and lists it under "Reports" in Solution Explorer.
* Site > Publish Preview (dry run) on the static web sample with a "Local folder" profile into the sandbox: the
  Publish window lists the site's files (index.html, about.html, assets/css/site.css ...) as "Add", leaves out
  project.radproj, and writes nothing to the target; Publish then copies the files.

The editor engine is set to the built-in editor (editor/engine) so code text is read synchronously offscreen.

Run:  .venv\\Scripts\\python samples\\Tests\\Coverage\\Project\\test_project_menu.py
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cov_harness as H  # noqa: E402
from cov_harness import (C, RECORDED, ROOT, action, check, clear_modal_handlers, finish, on_modal,  # noqa: E402
                         open_sample, pump, sandbox, start, wait)

_orig_window = C.window


def _window_builtin_editor():
    from radide.app import ide_settings
    ide_settings().setValue("editor/engine", "builtin")
    return _orig_window()


C.window = _window_builtin_editor

w = start("project_menu")
from PyQt6.QtCore import QPoint  # noqa: E402
from PyQt6.QtWidgets import QApplication, QFileDialog, QLineEdit  # noqa: E402

SB = sandbox()
prep = SB / "prep" / "ProjDemo"
shutil.copytree(ROOT / "samples/Tests/Languages/PythonTk_Form", prep, ignore=C.COPY_IGNORE)
for junk in prep.glob("test_*.py"):
    junk.unlink()
code_file = prep / "Form1.py"
code = code_file.read_text(encoding="utf-8")
code = code.replace("    def Form1_FormClosing(self, e):\n        print('closing'); e.Cancel = False\n\n", "")
code_file.write_text(code, encoding="utf-8")
proj = open_sample(w, str(prep))
check("prepared Python Tk project opened (no FormClosing handler)",
      w.project is not None and Path(w.project.folder) == proj and "Form1_FormClosing" not in code)


def tree_texts():
    out = []
    t = w.solution
    stack = [t.topLevelItem(i) for i in range(t.topLevelItemCount())]
    while stack:
        it = stack.pop()
        out.append(it.text(0))
        stack.extend(it.child(i) for i in range(it.childCount()))
    return out


def radproj():
    return json.loads((proj / "project.radproj").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ Project > Open Project Folder
RECORDED.clear()
a = action(w, "Project", "Open Project Folder")
check("Project > Open Project Folder exists", a is not None)
H.trigger(a, 0.3)
check("Open Project Folder shows the project folder in Explorer (os.startfile)",
      any(k == "startfile" and Path(t).resolve() == proj.resolve() for k, t in RECORDED), RECORDED)

# ------------------------------------------------------------------ Project > Add Existing Item
extra = SB / "extra" / "MathUtil.py"
extra.parent.mkdir(exist_ok=True)
extra.write_text("def square(x):\n    return x * x  # existing-item-marker\n", encoding="utf-8")
calls = []
orig_names = QFileDialog.__dict__["getOpenFileNames"]
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: (calls.append(a), ([str(extra)], ""))[1])
try:
    a = action(w, "Project", "Add Existing Item")
    check("Project > Add Existing Item exists", a is not None)
    H.trigger(a, 1.0)
finally:
    QFileDialog.getOpenFileNames = orig_names
check("Add Existing Item asked for files", len(calls) == 1, calls)
copied = proj / "MathUtil.py"
check("Add Existing Item copies the file into the project folder",
      copied.exists() and "existing-item-marker" in copied.read_text(encoding="utf-8"))
check("Add Existing Item keeps the original", extra.exists())
check("Add Existing Item lists MathUtil.py in project.radproj modules", "MathUtil.py" in radproj().get("modules", []),
      radproj().get("modules"))
check("Add Existing Item lists MathUtil.py in Solution Explorer", wait(lambda: "MathUtil.py" in tree_texts(), 5),
      tree_texts()[:40])

# ------------------------------------------------------------------ Designer: (form) > Events > FormClosing
w.open_designer("Form1")
pump(0.5)
view = w.designers["Form1"]
doc = w._doc("Form1")


def context_menu(ctrl):
    C.CAPTURED_MENUS.clear()
    view.show_context_menu(ctrl, QPoint(10, 10))
    return C.CAPTURED_MENUS[-1] if C.CAPTURED_MENUS else None


def find_act(menu, *path):
    for part in path:
        found = None
        for x in (menu.actions() if menu is not None else []):
            if not x.isSeparator() and C.clean(x.text()) == part:
                found = x
                break
        if found is None:
            return None
        if part != path[-1]:
            menu = found.menu()
        else:
            return found
    return None


m = context_menu(None)
check("designer right-click on the form opens a menu", m is not None)
ev = find_act(m, "Events", "FormClosing")
check("form menu has Events > FormClosing", ev is not None,
      [C.clean(x.text()) for x in (find_act(m, "Events").menu().actions() if find_act(m, "Events") else [])])
check("FormClosing is not bold before (no handler yet)", ev is not None and not ev.font().bold())
if ev is not None:
    ev.trigger()
    pump(0.5)
cv = w.codeviews.get("Form1")
txt = cv.editor.text() if cv is not None else ""
check("Events > FormClosing writes the handler stub into Form1's code",
      "def Form1_FormClosing(self, e)" in txt, txt[-800:])
check("Events > FormClosing shows the code editor", w._current_code() is cv)
ln = cv.editor.getCursorPosition()[0] if cv is not None else -1
check("the cursor is in the new handler", cv is not None and
      any("Form1_FormClosing" in x for x in txt.split("\n")[max(0, ln - 2):ln + 1]), (ln, txt.split("\n")[ln - 2:ln + 1]))
w.open_designer("Form1")
pump(0.3)
ev2 = find_act(context_menu(None), "Events", "FormClosing")
check("FormClosing is bold afterwards (handler exists)", ev2 is not None and ev2.font().bold())

# ------------------------------------------------------------------ Designer: (control) > Cut, then Paste, Undo
from radide.document import CLIP_MIME  # noqa: E402

btn = doc.form.find("Button1")
before = (btn.props["Text"], int(btn.props["Left"]), int(btn.props["Top"])) if btn is not None else None
n0 = len(doc.form.controls)
m = context_menu(btn)
cut = find_act(m, "Cut")
check("Button1 menu has an enabled Cut", cut is not None and cut.isEnabled())
cut.trigger()
pump(0.3)
check("Cut removes Button1 from the form", doc.form.find("Button1") is None and len(doc.form.controls) == n0 - 1,
      [c.name for c in doc.form.controls])
md = QApplication.clipboard().mimeData()
clip = json.loads(bytes(md.data(CLIP_MIME)).decode()) if md is not None and md.hasFormat(CLIP_MIME) else []
check("Cut puts Button1 on the clipboard", any(d.get("props", {}).get("Name") == "Button1" for d in clip),
      clip[:1])
paste = find_act(context_menu(None), "Paste")
check("form menu Paste is enabled after Cut", paste is not None and paste.isEnabled())
paste.trigger()
pump(0.3)
pasted = doc.form.find("Button1")
check("Paste restores the button (one control more)", pasted is not None and len(doc.form.controls) == n0,
      [c.name for c in doc.form.controls])
check("the pasted button keeps type, text and location", pasted is not None and pasted.type == "Button" and
      (pasted.props["Text"], int(pasted.props["Left"]), int(pasted.props["Top"])) == before,
      (before, pasted and pasted.props))
check("the pasted button is selected", pasted is not None and pasted in doc.selection)
w.open_designer("Form1")
undo = action(w, "Edit", "Undo")
check("Edit > Undo is enabled after Paste", undo is not None and undo.isEnabled())
H.trigger(undo, 0.3)
check("Undo removes the pasted button", doc.form.find("Button1") is None, [c.name for c in doc.form.controls])
H.trigger(action(w, "Edit", "Undo"), 0.3)
back = doc.form.find("Button1")
check("a second Undo restores the cut button", back is not None and len(doc.form.controls) == n0 and
      (back.props["Text"], int(back.props["Left"]), int(back.props["Top"])) == before,
      [c.name for c in doc.form.controls])

# ------------------------------------------------------------------ Project > Add User Control
uc_seen = []


def add_uc(dlg):
    if dlg.windowTitle() != "Add User Control":
        return False
    edits = dlg.findChildren(QLineEdit)
    uc_seen.append([e.text() for e in edits])
    edits[0].setText("CovPanel")
    dlg.accept()
    return True


on_modal(add_uc)
a = action(w, "Project", "Add User Control")
check("Project > Add User Control exists", a is not None)
H.trigger(a, 1.0)
check("Add User Control dialog proposes UserControl1", uc_seen and uc_seen[0][0] == "UserControl1", uc_seen)
check("Add User Control writes CovPanel.form", (proj / "CovPanel.form").exists())
check("Add User Control lists CovPanel in project.radproj forms", "CovPanel" in radproj().get("forms", []),
      radproj().get("forms"))
check("Add User Control opens CovPanel in its designer",
      "CovPanel" in getattr(w, "designers", {}) and w.tabs.currentWidget() is w.designers.get("CovPanel"),
      (list(getattr(w, "designers", {})), w.tabs.tabText(w.tabs.currentIndex())))
uc_form = json.loads((proj / "CovPanel.form").read_text(encoding="utf-8")) if (proj / "CovPanel.form").exists() else {}
check("CovPanel is a user control of the default 240x120 size",
      (uc_form.get("props", {}).get("Width"), uc_form.get("props", {}).get("Height")) == (240, 120),
      uc_form.get("props"))
check("Add User Control lists CovPanel in Solution Explorer", any("CovPanel" in t for t in tree_texts()),
      tree_texts()[:40])
clear_modal_handlers()

# ------------------------------------------------------------------ Project > Add Report
rep_seen = []


def add_report(dlg):
    if type(dlg).__name__ != "AddReportDialog":
        return False
    rep_seen.append(dlg.name.text())
    dlg.name.setText("SalesReport")
    dlg.title.setText("Sales by month")
    dlg.kind.setCurrentIndex(1)                      # Blank report
    dlg._ok()
    return True


on_modal(add_report)
a = action(w, "Project", "Add Report")
check("Project > Add Report exists", a is not None)
H.trigger(a, 1.0)
rpt = proj / "SalesReport.rpt.json"
check("Add Report dialog proposes Report1", rep_seen == ["Report1"], rep_seen)
check("Add Report writes SalesReport.rpt.json", rpt.exists())
rj = json.loads(rpt.read_text(encoding="utf-8")) if rpt.exists() else {}
check("the report definition has the name and title", rj.get("name") == "SalesReport" and
      rj.get("title") == "Sales by month", {k: rj.get(k) for k in ("name", "title")})
check("Add Report copies the radreport.py runtime", (proj / "radreport.py").exists())
cur = w.tabs.currentWidget()
check("Add Report opens the Report Designer", type(cur).__name__ == "ReportDesigner" and
      "SalesReport.rpt.json" in w.tabs.tabText(w.tabs.currentIndex()),
      (type(cur).__name__, w.tabs.tabText(w.tabs.currentIndex())))
check("Solution Explorer lists the report under Reports", "Reports" in tree_texts() and
      "SalesReport.rpt.json" in tree_texts(), tree_texts()[:40])
clear_modal_handlers()
w.save_all()

# ------------------------------------------------------------------ Site > Publish Preview (dry run)
web = open_sample(w, "web")
check("static web sample opened", w.project is not None and Path(w.project.folder) == web)
from radide.features.web_tools import _site_project  # noqa: E402
from radide.web_site import publish as pub  # noqa: E402

target = SB / "publish_target"
site = _site_project(w)
pub.save_profiles(site, [pub.PublishProfile(name="LocalCopy", kind="folder", remote_dir=str(target))])
a = action(w, "Site", "Publish Preview (dry run)")
check("Site > Publish Preview (dry run) exists", a is not None and a.isEnabled())
H.trigger(a, 0.5)


def publish_dialog():
    return next((x for x in QApplication.topLevelWidgets() if type(x).__name__ == "PublishDialog" and x.isVisible()),
                None)


check("Publish Preview opens the Publish window", wait(lambda: publish_dialog() is not None, 5))
dlg = publish_dialog()
rows = []
if dlg is not None:
    wait(lambda: dlg.changes.topLevelItemCount() > 0, 20)
    rows = [(dlg.changes.topLevelItem(i).text(0).replace("\\", "/"), dlg.changes.topLevelItem(i).text(1))
            for i in range(dlg.changes.topLevelItemCount())]
names = {r[0] for r in rows}
check("Publish Preview uses the LocalCopy folder profile", dlg is not None and dlg.current() is not None and
      dlg.current().name == "LocalCopy" and dlg.current().kind == "folder", dlg and dlg.current())
check("Publish Preview lists the site's pages and assets",
      {"index.html", "about.html", "contact.html", "assets/css/site.css", "assets/js/site.js"} <= names, rows)
check("Publish Preview marks every file 'Add' (first publish)", rows and all(r[1] == "Add" for r in rows), rows)
check("Publish Preview leaves out project.radproj", "project.radproj" not in names, rows)
check("Publish Preview says what would be published", dlg is not None and
      "Publish preview" in dlg.preview_label.text(), dlg and dlg.preview_label.text())
check("dry run writes nothing to the target folder", not target.exists() or not any(target.rglob("*")),
      list(target.rglob("*"))[:10] if target.exists() else [])
if dlg is not None:
    dlg.b_publish.click()
    check("Publish (after the preview) copies the files to the target",
          wait(lambda: (target / "index.html").exists() and (target / "assets" / "css" / "site.css").exists(), 20),
          list(target.rglob("*"))[:10] if target.exists() else [])
    check("Publish copies the page unchanged", (target / "index.html").exists() and
          (target / "index.html").read_bytes() == (web / "index.html").read_bytes())
    check("Publish does not copy project.radproj", not (target / "project.radproj").exists())
    dlg.close()
    pump(0.3)
check("no modal dialog left open", QApplication.activeModalWidget() is None)
finish(w)
