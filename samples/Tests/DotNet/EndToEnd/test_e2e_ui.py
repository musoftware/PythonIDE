"""End-to-end .NET journey in the IDE window, as a user would do it (qh.py harness: offscreen, QSettings
"RADIDE-TEST", widget.grab screenshots).  It crosses all five VS2022 slices on ONE solution:

open SolutionVS2022.sln -> New Project wizard (class library + shared project + xUnit) -> merge Tools.slnx's
projects -> Reference Manager (project, shared project, browse DLL, framework assembly on an old-style project,
COM) -> NuGet (Package Manager Console Install-Package, project document Update / Uninstall, solution
Consolidate) -> code using all of it -> build -> Configuration Manager (new configuration) -> Project
Properties round trip -> launch profile + multiple startup projects (Ctrl+F5) -> Save As .slnx + reopen +
build -> Test Explorer run (pass + intentional failure) -> Object Browser + decompile -> Code Cleanup.

    python samples/Tests/DotNet/EndToEnd/test_e2e_ui.py
"""
import os
import shutil
import sys
import traceback
from pathlib import Path

os.environ.setdefault("QA_NAME", "dotnet-e2e")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, finish, pump, shot, wait  # noqa: E402
from PyQt6.QtCore import Qt  # noqa: E402

ROLE = Qt.ItemDataRole.UserRole
base = Path(qh.WORK) / "dotnet-e2e"
shutil.rmtree(base, ignore_errors=True)
ign = shutil.ignore_patterns("bin", "obj", ".vs", "TestResults")
shutil.copytree(HERE.parent / "SolutionVS2022", base / "Shop", ignore=ign)
shutil.copytree(HERE.parent / "SolutionMerge", base / "Merge", ignore=ign)
SOL = base / "Shop"
SLN = SOL / "SolutionVS2022.sln"

from radide.foreign import vs_ui  # noqa: E402
from radide.foreign import msbuild as MB  # noqa: E402

w = qh.window()
STATE = {}


def stage(name):
    def deco(fn):
        print(f"---- {name}", flush=True)
        try:
            fn()
        except Exception:  # noqa: BLE001
            check(f"{name}: no exception", False, traceback.format_exc()[-1500:])
        return fn
    return deco


def items():
    out, stack = [], [w.solution.topLevelItem(i) for i in range(w.solution.topLevelItemCount())]
    while stack:
        it = stack.pop(0)
        out.append(it)
        stack.extend(it.child(i) for i in range(it.childCount()))
    return out


def node(kind, name=None):
    for it in items():
        d = it.data(0, ROLE) or ("",)
        if isinstance(d, tuple) and d and d[0] == kind and (name is None or str(d[1]).lower() == str(name).lower()
                                                            or it.text(0).split("  ")[0].lower() == str(name).lower()):
            return it
    return None


def proj(name):
    return w.sln.project(name) if w.sln is not None else None


def ptext(name):
    p = proj(name)
    return p.ms.path.read_text(encoding="utf-8-sig") if p is not None else ""


def sln_text():
    return Path(w.sln.file).read_text(encoding="utf-8-sig")


def build_all(only=None):
    res = vs_ui.build(w, w.sln, only=only, wait=True)
    return res, w.output.toPlainText()[-3000:]


@stage("open solution")
def _():
    ok = vs_ui.open_in_window(w, SLN)
    pump(2)
    check("SolutionVS2022.sln opens with 4 projects", ok and w.sln is not None and len(w.sln.all_projects()) == 4,
          w.sln and [p.name for p in w.sln.all_projects()])
    shot(w, "e2e_01_opened")


@stage("New Project wizard")
def _():
    from radide.dotnet.templates import wizard as WZ
    for key, lang, name, opts in (("classlib", "C#", "Billing", {"Framework": "net8.0"}),
                                  ("rad:shared-cs", "C#", "SharedUtils", {}),
                                  ("xunit", "C#", "Billing.Tests", {"Framework": "net8.0"})):
        wz = WZ.show_wizard(w, add_to=w.sln, exec_=False)
        wz.show()
        ok = wz.select(key, lang)
        wz.next()
        wz.name_edit.setText(name)
        pump(0.1)
        if wz.next_btn.text() == "Next":
            wz.next()
            for k, v in opts.items():
                wz.set_option(k, v)
            if key == "classlib":
                shot(wz, "e2e_02_wizard_options")
        wz.next()
        pump(0.5)
        res = wz.result_info
        check(f"wizard: {key} '{name}' created and added to the .sln", ok and res is not None and
              res.project_file and res.project_file.is_file() and res.project_file.name in sln_text(),
              (ok, wz.error.text(), res))
        wz.close()
    pump(1)
    check("new projects in Solution Explorer", node("project", "Billing") is not None and
          node("foreign_shproj", "SharedUtils") is not None and node("project", "Billing.Tests") is not None,
          [(it.text(0), (it.data(0, ROLE) or ("",))[:2]) for it in items()][:40])


@stage("merge another solution")
def _():
    from radide.dotnet.sln import dialogs as D
    imp = D.import_solution(w, w.sln, base / "Merge" / "Tools.slnx", exec_=False)
    names = {i.text(0) for i in imp.items()}
    check("import checklist lists Tools.slnx's projects", names == {"Tools.Legacy", "Tools.Text"}, names)
    shot(imp, "e2e_03_merge")
    added = imp.apply()
    pump(1)
    check("merged: Tools.Legacy + Tools.Text loaded", len(added) == 2 and proj("Tools.Text") is not None and
          proj("Tools.Legacy") is not None, [p.name for p in w.sln.all_projects()])
    check("folder Libraries recreated", node("foreign_slnfolder", "Libraries") is not None)
    check("merged projects written to the .sln", "Tools.Legacy.vbproj" in sln_text() and "Tools.Text.csproj" in
          sln_text())


@stage("Reference Manager")
def _():
    # project + shared project references: Billing -> SharedUtils (shared); App -> Billing; Billing.Tests -> Billing
    dlg = vs_ui.add_reference_dialog(w, proj("Billing"), "shared", exec_=False)
    dlg.show()
    check("Reference Manager: Shared Projects page lists SharedUtils", dlg.check("shared", "SharedUtils"))
    shot(dlg, "e2e_04_refmgr_shared")
    dlg.apply()
    dlg.close()
    check("Billing imports SharedUtils.projitems", 'SharedUtils.projitems" Label="Shared"' in ptext("Billing"),
          ptext("Billing"))
    for consumer in ("App", "Billing.Tests"):
        dlg = vs_ui.add_reference_dialog(w, proj(consumer), "projects", exec_=False)
        ok = dlg.check("projects", "Billing")
        dlg.apply()
        dlg.close()
        check(f"{consumer} -> Billing project reference", ok and "Billing.csproj" in ptext(consumer), ptext(consumer))
    # circular: Billing -> App refused
    qh.MSGS.clear()
    dlg = vs_ui.add_reference_dialog(w, proj("Billing"), "projects", exec_=False)
    dlg.check("projects", "App")
    ch = dlg.apply()
    dlg.close()
    check("circular reference Billing -> App refused", not ch and "App.csproj" not in ptext("Billing"), qh.MSGS)
    # browse a DLL: build Tools.Text and reference its dll from App
    code = MB.find_dotnet()
    import subprocess
    subprocess.run([code, "build", "-nologo", "-v", "q"], cwd=base / "Merge" / "Tools.Text", capture_output=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    dlls = list((base / "Merge" / "Tools.Text" / "bin").rglob("Tools.Text.dll"))
    check("Tools.Text.dll built for the Browse test", bool(dlls))
    if dlls:
        STATE["dll"] = dlls[0]
        dlg = vs_ui.add_reference_dialog(w, proj("App"), "browse", exec_=False)
        it = dlg.add_browse_file(dlls[0])
        dlg.apply()
        dlg.close()
        check("Browse: App references Tools.Text.dll with a HintPath", it is not None and
              "Tools.Text.dll</HintPath>" in ptext("App"), ptext("App"))
    pump(0.5)
    # framework assembly + COM on an old-style project: create one with the wizard (.NET Framework class library)
    from radide.dotnet.templates import wizard as WZ
    wz = WZ.show_wizard(w, add_to=w.sln, exec_=False)
    wz.show()
    wz.select("rad:fxlib-cs", "C#")
    wz.next()
    wz.name_edit.setText("LegacyLib")
    wz.next()
    if wz.next_btn.text() == "Next" or wz.result_info is None:
        wz.next()
    pump(0.5)
    wz.close()
    check("wizard: .NET Framework class library LegacyLib", proj("LegacyLib") is not None and
          not proj("LegacyLib").ms.is_sdk, wz.error.text())
    if proj("LegacyLib") is not None:
        dlg = vs_ui.add_reference_dialog(w, proj("LegacyLib"), "assemblies", exec_=False)
        dlg.show()
        ok1 = dlg.check("framework", "System.Numerics")
        dlg.select_page("com")
        pump(0.3)
        ok2 = dlg.check("com", "Microsoft Scripting Runtime")
        shot(dlg, "e2e_05_refmgr_com")
        dlg.apply()
        dlg.close()
        t = ptext("LegacyLib")
        check("LegacyLib: framework System.Numerics + COM Scripting", ok1 and ok2 and
              '<Reference Include="System.Numerics" />' in t and '<COMReference Include="Scripting">' in t, t)
    pump(0.5)
    shot(w.solution, "e2e_06_dependencies")


@stage("NuGet")
def _():
    from radide.features import nuget_ide
    pmc = nuget_ide.show_console(w)
    pmc._no_popup = True

    def run_cmd(line, t=300):
        box = []
        pmc.execute(line, lambda ok: box.append(ok))
        wait(lambda: box, t)
        pump(0.3)
        return box[0] if box else None

    check("console lists the solution's projects", pmc.project.findText("Billing") >= 0,
          [pmc.project.itemText(i) for i in range(pmc.project.count())])
    ok = run_cmd("Install-Package Newtonsoft.Json -Version 13.0.1 -ProjectName Billing")
    check("PMC Install-Package Newtonsoft.Json 13.0.1 -> Billing", ok and
          'Include="Newtonsoft.Json" Version="13.0.1"' in ptext("Billing"), pmc.text.toPlainText()[-900:])
    ok = run_cmd("Install-Package Newtonsoft.Json -Version 13.0.3 -ProjectName Tools.Text")
    check("PMC Install-Package 13.0.3 -> Tools.Text", ok and 'Version="13.0.3"' in ptext("Tools.Text"),
          pmc.text.toPlainText()[-900:])
    shot(pmc, "e2e_07_pmc")
    # solution document: consolidate Billing to 13.0.3
    sv = nuget_ide.manage_solution(w)
    sv.show_preview = False

    def idle(view, t=120):
        pump(0.2)
        return wait(lambda: view.busy == 0 and not view._running, t)
    idle(sv)
    wait(lambda: sv.consolidate_count > 0, 90)
    check("solution NuGet: Consolidate badge", sv.consolidate_count >= 1, sv.consolidate_count)
    sv.set_tab("consolidate")
    idle(sv)
    if sv.select_package("Newtonsoft.Json"):
        idle(sv)
        for i in range(1, sv.d_version.count()):
            if sv.d_version.itemData(i) == "13.0.3":
                sv.d_version.setCurrentIndex(i)
        shot(sv, "e2e_08_consolidate")
        sv.install()
        idle(sv, 300)
    check("consolidated Billing to 13.0.3", 'Include="Newtonsoft.Json" Version="13.0.3"' in ptext("Billing"),
          ptext("Billing"))
    # project document: install + uninstall a second package on App
    pv = nuget_ide.manage_project(w, proj("App"))
    pv.show_preview = False
    pv.confirm_licenses = lambda metas: True
    idle(pv)
    pv.search.setText("Humanizer.Core")
    pv.refresh()
    idle(pv)
    pv.select_package("Humanizer.Core")
    idle(pv)
    pv.install()
    idle(pv, 300)
    check("project NuGet: Install Humanizer.Core into App", "Humanizer.Core" in ptext("App"), ptext("App"))
    pv.set_tab("installed")
    idle(pv)
    pv.select_package("Humanizer.Core")
    idle(pv)
    pv.uninstall()
    idle(pv, 300)
    check("project NuGet: Uninstall Humanizer.Core", "Humanizer" not in ptext("App"), ptext("App"))
    for v in (sv, pv):
        i = w.tabs.indexOf(v)
        if i >= 0:
            w.tabs.removeTab(i)


@stage("code + build")
def _():
    shared = SOL / "SharedUtils"
    if not shared.is_dir():
        shared = next((p.parent for p in SOL.rglob("SharedUtils.projitems")), shared)
    from radide.dotnet.shared import model as SM
    sp = SM.SharedProject(next(shared.glob("*.shproj")))
    (shared / "Money.cs").write_text(
        "namespace SharedUtils;\n\npublic static class Money\n{\n"
        "    public static string Format(decimal v) => v.ToString(\"0.00\", System.Globalization.CultureInfo"
        ".InvariantCulture) + \" EGP\";\n}\n", encoding="utf-8")
    sp.add_existing_item(shared / "Money.cs")
    check("Money.cs in SharedUtils.projitems", "Money.cs" in
          shared.joinpath("SharedUtils.projitems").read_text(encoding="utf-8-sig"))
    bill = proj("Billing").folder
    for f in bill.glob("Class1.cs"):
        f.unlink()
    (bill / "Invoice.cs").write_text(
        "using Newtonsoft.Json;\nusing SharedUtils;\n\nnamespace Billing;\n\npublic class Invoice\n{\n"
        "    public List<decimal> Lines { get; } = new();\n    public decimal Total => Lines.Sum();\n"
        "    public string Describe() => $\"{Lines.Count} lines, total {Money.Format(Total)}\";\n"
        "    public string ToJson() => JsonConvert.SerializeObject(new { Total });\n}\n", encoding="utf-8")
    tests = proj("Billing.Tests").folder
    for f in tests.glob("UnitTest1.cs"):
        f.unlink()
    (tests / "InvoiceTests.cs").write_text(
        "using Billing;\n\nnamespace Billing.Tests;\n\npublic class InvoiceTests\n{\n"
        "    [Fact]\n    public void Total_AddsLines()\n    {\n        var i = new Invoice();\n"
        "        i.Lines.AddRange(new[] { 10m, 2.5m });\n        Assert.Equal(12.5m, i.Total);\n    }\n\n"
        "    [Fact]\n    public void Describe_IntentionalFailure()\n    {\n"
        "        Assert.Equal(\"wrong\", new Invoice().Describe());\n    }\n}\n", encoding="utf-8")
    prog = proj("App").folder / "Program.cs"
    prog.write_text(prog.read_text(encoding="utf-8") +
                    "var inv = new Billing.Invoice();\ninv.Lines.Add(7.25m);\n"
                    "Console.WriteLine($\"Invoice: {inv.Describe()} {inv.ToJson()}\");\n"
                    "Console.WriteLine($\"Tools.Text: {Tools.Text.Class1.Name}\");\n", encoding="utf-8")
    cls = base / "Merge" / "Tools.Text" / "Class1.cs"
    if "Name" not in cls.read_text(encoding="utf-8"):
        cls.write_text("namespace Tools.Text;\n\npublic static class Class1\n{\n"
                       "    public static string Name => \"text tools\";\n}\n", encoding="utf-8")
    # Tools.Text changed: rebuild its dll (App references the dll by HintPath)
    w.output.clear()
    res, out = build_all(only=["Tools.Text"])
    res, out = build_all()
    STATE["build"] = res
    check("solution builds (dotnet/MSBuild per project)", res and all(c == 0 for c in res.values()),
          (res, out))


@stage("Configuration Manager")
def _():
    from radide.dotnet.sln import dialogs as D
    from radide.dotnet.sln.model import SolutionDoc
    cm = D.configuration_manager(w, w.sln, exec_=False)
    cm.new_solution_configuration("QA", "Release", True)
    shot(cm, "e2e_09_config_manager")
    cm.apply()
    pump(0.5)
    doc = SolutionDoc.load(Path(w.sln.file))
    check("Configuration Manager: QA|Any CPU in the .sln", "QA|Any CPU" in doc.configs, doc.configs)
    check("config combo lists QA", w.vs_config_combo.findText("QA") >= 0)
    res = vs_ui.build(w, w.sln, only=["Billing"], wait=True)
    check("build Billing in QA", res and all(c == 0 for c in res.values()) and
          list((proj("Billing").folder / "bin" / "QA").rglob("Billing.dll")), (res, w.output.toPlainText()[-1500:]))
    vs_ui.set_configuration(w, "Debug", "Any CPU")


@stage("Project Properties round trip")
def _():
    app = proj("App")
    doc_w = vs_ui.project_properties(w, app)
    pump(0.5)
    doc_w.set_value("DefineConstants", "$(DefineConstants);E2E", "Debug")
    doc_w.set_value("Nullable", "disable")
    shot(w, "e2e_10_properties")
    i = w.tabs.indexOf(doc_w)
    if i >= 0:
        w.tabs.removeTab(i)
    t = ptext("App")
    check("properties written", "E2E" in t and "<Nullable>disable</Nullable>" in t, t)
    doc2 = vs_ui.project_properties(w, proj("App"))
    pump(0.5)
    spec = next(s for s in __import__("radide.dotnet.sln.properties", fromlist=["SPECS"]).SPECS
                if s.name == "Nullable")
    check("reopened Properties shows Nullable=disable", "disable" in str(doc2.value_of(spec)[0]).lower(),
          doc2.value_of(spec))
    i = w.tabs.indexOf(doc2)
    if i >= 0:
        w.tabs.removeTab(i)


@stage("launch profile + multiple startup")
def _():
    from radide.dotnet.sln import dialogs as D
    from radide.dotnet.sln import launch, run
    app = proj("App")
    launch.save(app.folder, {"profiles": {"App": {"commandName": "Project"},
                                          "E2E": {"commandName": "Project", "commandLineArgs": "one two",
                                                  "environmentVariables": {"RADIDE_SAMPLE": "e2e"}}}})
    spp = D.solution_property_pages(w, w.sln, exec_=False)
    spp.rb_multi.setChecked(True)
    spp.set_action("App", "Start")
    spp.set_action("Tools.Text", "None")
    spp.set_action("Core", "None")
    # a second runnable startup: WinUI is a GUI app; use a fresh console created by the wizard instead
    from radide.dotnet.templates import wizard as WZ
    wz = WZ.show_wizard(w, add_to=w.sln, exec_=False)
    wz.show()
    wz.select("console", "C#")
    wz.next()
    wz.name_edit.setText("Worker")
    if wz.next_btn.text() == "Next":
        wz.next()
        wz.set_option("Framework", "net8.0")
    wz.next()
    pump(0.5)
    wz.close()
    spp.apply()
    spp = D.solution_property_pages(w, w.sln, exec_=False)
    spp.rb_multi.setChecked(True)
    spp.set_action("App", "Start")
    spp.set_action("Worker", "Start without debugging")
    shot(spp, "e2e_11_startup")
    spp.apply()
    plan = [(p.name, a) for p, a in run.startup_plan(w.sln)]
    check("multiple startup: App (Start) + Worker (Start without debugging)",
          plan == [("App", "Start"), ("Worker", "Start without debugging")], plan)
    run.refresh_profile_combo(w)
    w.vs_profile_combo.setCurrentText("E2E")
    w.vs_profile_combo.activated.emit(w.vs_profile_combo.currentIndex())
    w.output.clear()
    w.run_project(debug=False)
    wait(lambda: w.session is None or not w.session.running(), 300)
    wait(lambda: "[Worker] Hello, World!" in w.output.toPlainText(), 120)
    pump(2)
    out = w.output.toPlainText()
    check("Ctrl+F5: App ran with profile args + env", "Args: one | two" in out and "RADIDE_SAMPLE=e2e" in out,
          out[-2500:])
    check("Ctrl+F5: App uses Billing + SharedUtils + Newtonsoft + Tools.Text.dll",
          "Invoice: 1 lines, total 7.25 EGP {\"Total\":7.25}" in out and "Tools.Text: text tools" in out, out[-2500:])
    check("Ctrl+F5: Worker ran too", "[Worker] Hello, World!" in out, out[-1500:])
    shot(w, "e2e_12_run")
    if w.session is not None and w.session.running():
        w.session.stop()
        pump(1)


@stage("Save As .slnx")
def _():
    from radide.dotnet import sln as S
    n = len(w.sln.all_projects())
    target = SOL / "SolutionVS2022.slnx"
    S.save_as_dialog(w, w.sln, ".slnx", target=target)
    pump(2)
    check(".slnx reopened with the same projects", w.sln is not None and Path(w.sln.file).suffix == ".slnx" and
          len(w.sln.all_projects()) == n, (w.sln and w.sln.file, n, w.sln and len(w.sln.all_projects())))
    t = target.read_text(encoding="utf-8")
    check(".slnx keeps the shared project, the QA config and folders", "SharedUtils.shproj" in t and
          "QA" in t and '<Folder Name="/Libraries/">' in t, t[:1500])
    check("Solution Explorer after reload: shared project node", node("foreign_shproj", "SharedUtils") is not None)
    w.output.clear()
    res = vs_ui.build(w, w.sln, wait=True)
    check("Build Solution from the .slnx (dotnet + VS MSBuild for the COM project)",
          res and all(c == 0 for c in res.values()), (res, w.output.toPlainText()[-2000:]))


@stage("Test Explorer")
def _():
    te = w.test_explorer
    w.dock_tests.show()
    te.discover(force=True)
    check("Test Explorer discovers Billing.Tests + App.Tests", wait(
        lambda: not te.discovering and any(it.name == "Total_AddsLines" for it in te.items.values()), 300),
        (len(te.items), te.log.toPlainText()[-800:]))
    te.finished_run = False
    te.run(None)
    wait(lambda: getattr(te, "finished_run", False) and not te.running(), 600)
    st = {it.name: it.state for it in te.items.values()}
    check("Run All: pass + intentional failure", st.get("Total_AddsLines") == "passed" and
          st.get("Describe_IntentionalFailure") == "failed", st)
    shot(w.dock_tests, "e2e_13_tests")


@stage("Object Browser + decompile")
def _():
    from radide.dotnet.refs.object_browser import show_object_browser
    ob = show_object_browser(w)
    pump(1)
    tops = [ob.tree.topLevelItem(i).text(0) for i in range(ob.tree.topLevelItemCount())]
    check("Object Browser (My Solution) lists Billing", any(t.startswith("Billing") for t in tops), tops)
    ok = ob.select_type("Billing.Invoice")
    pump(0.3)
    members = [ob.members.item(i).text() for i in range(ob.members.count())]
    check("Object Browser: Invoice members", ok and any(m.startswith("Describe(") for m in members) and
          any(m.startswith("Total") for m in members), members)
    w.dock_object_browser.resize(1100, 420)
    shot(w.dock_object_browser, "e2e_14_object_browser")
    from radide.dotnet.decompile import decompile_to_text
    dll = next(iter((proj("Billing").folder / "bin" / "Debug").rglob("Billing.dll")), None)
    txt = decompile_to_text(dll, "Billing.Invoice", install=True) if dll else ""
    check("decompile Billing.Invoice with ilspycmd", "class Invoice" in txt and "Describe" in txt, txt[:600])


@stage("Code Cleanup")
def _():
    from radide.dotnet.tools import ui as DUI
    bill = proj("Billing")
    messy = bill.folder / "Messy.cs"
    messy.write_text("using System.Text;\nusing System;\nnamespace Billing;\npublic class Messy {\n"
                     "public int Twice(int a){return a*2;}\n}\n", encoding="utf-8")
    w.activate_project(bill)
    w.open_module("Messy.cs")
    pump(2)
    view = w.modviews.get("Messy.cs")
    check("Messy.cs opened", view is not None)
    if view is None:
        return
    w.tabs.setCurrentWidget(view)
    res = []
    DUI.code_cleanup(w, "document", "whitespace", then=lambda code, changed: res.append((code, changed)))
    check("Code Cleanup reformats the document", wait(lambda: bool(res), 300) and res[0][0] == 0 and
          "    public int Twice(int a)" in view.editor.text(), (res, view.editor.text()[:300]))
    done = []
    DUI.remove_and_sort_usings(w, view.editor, then=lambda new, removed, err: done.append((new, removed, err)))
    check("Remove and Sort Usings", wait(lambda: bool(done), 240) and "using System.Text;" not in view.editor.text(),
          (done[:1], view.editor.text()[:200]))


out_lines = w.output.toPlainText().splitlines()
tb = [i for i, ln in enumerate(out_lines) if "Traceback" in ln]
check("no tracebacks in the Output window", not tb, "\n".join(out_lines[tb[0]:tb[0] + 25]) if tb else "")
finish(w)
