"""IDE test (samples/Tests/QA/Integration/qh.py harness, QSettings "RADIDE-TEST", widget.grab only).

Copies SharedDemo/ (made by make_and_build.py) to a temp folder, opens SharedDemo.sln in the IDE and checks:
Solution Explorer (shared project nodes + icon, files/folders, Dependencies > Shared Projects), the shared project
context menu, Add New Item / New Folder / Rename / Exclude inside the shared project (writes .projitems), the
Shared Project Reference dialog (add / remove), the editor's project-context combo and #if greying when switching
WinApp <-> FxConsole, and the VS2022 New Project wizard (template list + filters + search, Configure page,
Additional information page) creating console / classlib / winforms / xunit (dotnet new) and the RAD IDE templates
into the open solution.

    python samples/Tests/DotNet/SharedProjects/ui_test.py
"""
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
os.environ.setdefault("QA_NAME", "dotnet-shared")
import qh  # noqa: E402
from qh import check, pump, shot, finish  # noqa: E402

work = Path(qh.WORK) / "dotnet-shared"
if work.exists():
    shutil.rmtree(work, ignore_errors=True)
shutil.copytree(HERE / "SharedDemo", work / "SharedDemo")
sln_file = work / "SharedDemo" / "SharedDemo.sln"

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QMenu  # noqa: E402

from radide.dotnet.shared import ctxbar as CTX  # noqa: E402
from radide.dotnet.shared import model as SH  # noqa: E402
from radide.dotnet.shared import ui as SUI  # noqa: E402
from radide.features import solution_ui  # noqa: E402

ROLE = Qt.ItemDataRole.UserRole
w = qh.window()
from radide.foreign import vs_ui  # noqa: E402

vs_ui.open_in_window(w, sln_file)
pump(2)


def items():
    return solution_ui.tree_items(w)


def find(kind, name_part):
    stack = [w.solution.topLevelItem(i) for i in range(w.solution.topLevelItemCount())]
    while stack:
        it = stack.pop(0)
        d = it.data(0, ROLE) or ("", "")
        if d[0] == kind and name_part.lower() in str(d[1]).lower():
            return it
        stack.extend(it.child(i) for i in range(it.childCount()))
    return None


def menu_texts(item):
    m = solution_ui.build_menu(w, item)
    if m is None:
        m = QMenu(w)
    solution_ui.apply_menu_hooks(w, item, m)
    out = []
    for a in m.actions():
        out.append(a.text().replace("&", ""))
        if a.menu() is not None:
            out += [a.text().replace("&", "") + ">" + b.text().replace("&", "") for b in a.menu().actions()]
    return m, out


tree = items()
texts = [t for _d, t, _x in tree]
check("solution opened", w.sln is not None and w.sln.file == sln_file.resolve(), w.sln)
sh_cs = find("foreign_shproj", "SharedCode.shproj")
sh_vb = find("foreign_shproj", "SharedVB.shproj")
check("Solution Explorer shows both shared projects", sh_cs is not None and sh_vb is not None, texts)
check("shared project has its own icon", sh_cs is not None and not sh_cs.icon(0).isNull())
check("root counts shared projects", any("(8 of 8 projects)" in t for t in texts), texts[:2])
check("shared files and folders listed", find("foreign_shfile", "Greeter.cs") is not None and
      find("foreign_shfolder", "|Util") is not None and find("foreign_shfile", "Helper.cs") is not None, texts)
check("consumer shows Dependencies > Shared Projects > SharedCode",
      any("SharedCode" in t for d, t, x in tree if x and x[0] in ("foreign_shref", "foreign_dep")), texts)
shot(w, "dotnet_shared_solution_explorer")

m, mt = menu_texts(sh_cs)
check("shared project menu like VS", {"Add>New Item...", "Add>Existing Item...", "Add>New Folder", "Rename", "Remove",
                                      "Properties"} <= set(mt), mt)
proj_item = find("project", "WinApp")
m, mt = menu_texts(proj_item)
check("project menu: Add > Shared Project Reference...", "Add>Shared Project Reference..." in mt, mt)
root = w.solution.topLevelItem(0)
m, mt = menu_texts(root)
check("solution menu: Add > New Shared Project...", "Add>New Shared Project..." in mt, mt)

# ---- edits inside the shared project
sp = SH.SharedProject(work / "SharedDemo" / "SharedCode" / "SharedCode.shproj")
dlg = SUI.new_item_dialog(w, sp, "Util", "Class", exec_=False)
dlg.name_edit.setText("Formatter")
created = dlg.apply()
pump(0.5)
sp.reload()
check("Add New Item in a shared folder writes the .projitems", created == ["Util/Formatter.cs"] and
      "Util/Formatter.cs" in sp.files(), (created, sp.files()))
check("new item shows in Solution Explorer", find("foreign_shfile", "Formatter.cs") is not None)
SUI.new_folder(w, sp, "", "Models")
sp.reload()
check("New Folder (Folder item)", "Models" in sp.folders() and "<Folder" in sp.projitems_path.read_text("utf-8-sig"))
new_rel = SUI.rename_item_dialog(w, sp, "Util/Formatter.cs", "TextFormatter.cs")
sp.reload()
check("Rename a shared file", new_rel == "Util/TextFormatter.cs" and (sp.items_folder / new_rel).is_file()
      and "TextFormatter.cs" in sp.projitems_path.read_text("utf-8-sig"))
check("Exclude From Project", SUI.exclude_item(w, sp, "Util/TextFormatter.cs") and
      "TextFormatter" not in SH.SharedProject(sp.path).projitems_path.read_text("utf-8-sig"))

# ---- Shared Project Reference dialog
vp = w.sln.project("MultiLib")
dlg = SUI.add_shared_reference_dialog(w, vp, exec_=False)
names = [dlg.tab.list.item(i).data(ROLE).name for i in range(dlg.tab.list.count())]
check("reference dialog lists only same-language shared projects", names == ["SharedCode"], names)
dlg.tab.set_checked("SharedCode", True)
ch = dlg.apply()
check("reference added (Import Label=Shared)", ch == ["+SharedCode"] and SH.references_shared(vp.ms.path, sp), ch)
ml_guid = next(e.guid for e in w.sln.model.entries if e.path.endswith("MultiLib.csproj")).lower()
check("the .sln gets MultiLib's SharedItemsImports line (like VS)",
      f"*{ml_guid}*SharedItemsImports = 5" in sln_file.read_text("utf-8-sig"))
pump(0.5)
dlg = SUI.add_shared_reference_dialog(w, w.sln.project("MultiLib"), exec_=False)
dlg.tab.set_checked("SharedCode", False)
check("reference removed", dlg.apply() == ["-SharedCode"] and not SH.references_shared(vp.ms.path, sp))
check("... and its SharedItemsImports line", f"*{ml_guid}*" not in sln_file.read_text("utf-8-sig"))

# ---- project context + #if greying
greeter = sp.abs_path("Greeter.cs")
SUI.open_shared_file(w, greeter)
pump(2)
view = w.tabs.currentWidget()
st = getattr(view, "_rad_ctx_state", None)
check("project context attached to the shared file", st is not None and st.get("bar") is not None, st)
if st and st.get("bar") is not None:
    labels = [st["bar"].combo.itemText(i) for i in range(st["bar"].combo.count())]
    check("contexts = the consuming projects", any(lbl.startswith("WinApp") for lbl in labels) and
          any(lbl.startswith("FxConsole") for lbl in labels), labels)
    lines = view.editor.text().splitlines()
    i8 = next(i for i, ln in enumerate(lines) if "NET 8+" in ln)
    iold = next(i for i, ln in enumerate(lines) if "old-style" in ln)
    win_idx = next(i for i, lbl in enumerate(labels) if lbl.startswith("WinApp"))
    fx_idx = next(i for i, lbl in enumerate(labels) if lbl.startswith("FxConsole"))
    st["bar"].combo.setCurrentIndex(win_idx)
    pump(0.5)
    r1 = CTX.apply_context(view)
    inact = {n for a, b in r1 for n in range(a, b + 1)}
    check("WinApp context: .NET Framework branches greyed", iold in inact and i8 not in inact, r1)
    shot(view, "dotnet_shared_context_winapp")
    st["bar"].combo.setCurrentIndex(fx_idx)
    pump(0.5)
    r2 = getattr(view.editor, "_rad_inactive_ranges", [])
    inact = {n for a, b in r2 for n in range(a, b + 1)}
    check("FxConsole context: the NET8 branch greyed", i8 in inact and iold not in inact, r2)
    isdk = next(i for i, ln in enumerate(lines) if "SDK-style" in ln)
    sdk_idx = next((i for i, lbl in enumerate(labels) if lbl.startswith("SdkFxConsole")), -1)
    st["bar"].combo.setCurrentIndex(sdk_idx)
    pump(0.5)
    r3 = getattr(view.editor, "_rad_inactive_ranges", [])
    inact = {n for a, b in r3 for n in range(a, b + 1)}
    check("SdkFxConsole (SDK-style net48) context: only the NETFRAMEWORK branch active",
          sdk_idx >= 0 and isdk not in inact and i8 in inact and iold in inact, (labels, r3))
    shot(view, "dotnet_shared_context_fxconsole")

# ---- rename the shared project (consumers' imports follow)
sp_vb = SH.SharedProject(work / "SharedDemo" / "SharedVB" / "SharedVB.shproj")
SUI.rename_shared_dialog(w, sp_vb, "SharedBasic")
pump(0.5)
vbapp = w.sln.project("VbApp")
check("Rename shared project: files, consumers and .sln updated",
      (work / "SharedDemo" / "SharedVB" / "SharedBasic.projitems").is_file()
      and "SharedBasic.projitems" in vbapp.ms.path.read_text("utf-8-sig")
      and "SharedBasic.shproj" in sln_file.read_text("utf-8-sig"))

# ---- New Project wizard
from radide.dotnet.templates import wizard as WZ  # noqa: E402

wz = WZ.show_wizard(w, add_to=w.sln, exec_=False)
wz.show()
pump(0.5)
check("wizard page 1: templates listed", wz.list.count() > 20, wz.list.count())
wz.lang_combo.setCurrentIndex(wz.lang_combo.findData("VB"))
check("language filter", all(t.language in ("VB", "") for t in wz.visible_templates()))
wz.clear_filters()
wz.type_combo.setCurrentIndex(wz.type_combo.findData("Test"))
check("project type filter", all("Test" in t.project_types for t in wz.visible_templates()) and wz.list.count() > 0)
wz.clear_filters()
wz.search.setText("shared")
check("search finds Shared Project", any(t.key.startswith("rad:shared") for t in wz.visible_templates()))
wz.clear_filters()
shot(wz, "dotnet_new_project_page1")
made = {}
for key, lang, name, opts in (("console", "C#", "NewConsole", {"Framework": "net8.0"}),
                              ("classlib", "C#", "NewLib", {"Framework": "net8.0"}),
                              ("winforms", "VB", "NewVbForms", {"Framework": "net8.0"}),
                              ("xunit", "C#", "NewTests", {"Framework": "net8.0"}),
                              ("rad:fxlib-cs", "C#", "NewFxLib", {}),
                              ("rad:fxwinforms-vb", "VB", "NewFxVbForms", {}),
                              ("rad:fxwpf-cs", "C#", "NewFxWpf", {}),
                              ("rad:fxservice-cs", "C#", "NewService", {}),
                              ("rad:netstd-cs", "C#", "NewStd", {}),
                              ("rad:shared-cs", "C#", "NewShared", {})):
    wz = WZ.show_wizard(w, add_to=w.sln, exec_=False)
    wz.show()
    ok = wz.select(key, lang)
    wz.next()
    wz.name_edit.setText(name)
    pump(0.1)
    if key == "console":
        shot(wz, "dotnet_new_project_page2")
    has3 = wz.next_btn.text() == "Next"
    wz.next()
    if has3:
        for k, v in opts.items():
            wz.set_option(k, v)
        if key == "console":
            shot(wz, "dotnet_new_project_page3")
        wz.next()
    pump(0.5)
    res = wz.result_info
    made[name] = res
    check(f"wizard creates {key} ({lang}) '{name}' in the solution", ok and res is not None and res.project_file
          and res.project_file.is_file() and res.project_file.name in sln_file.read_text("utf-8-sig"),
          (ok, wz.error.text(), res))
pump(1)
check("new projects show in Solution Explorer", find("project", "NewConsole") is not None and
      find("foreign_shproj", "NewShared") is not None,
      [(t, x[:2]) for _d, t, x in items() if x and x[0] in ("project", "foreign_shproj", "missing")])
shot(w, "dotnet_shared_after_wizard")
out_lines = w.output.toPlainText().splitlines()
for i, ln in enumerate(out_lines):
    if "Traceback" in ln:
        print("OUTPUT TRACEBACK:\n" + "\n".join(out_lines[max(0, i - 2):i + 25]))
        break
finish(w)
