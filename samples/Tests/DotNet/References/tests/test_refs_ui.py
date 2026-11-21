"""References slice - IDE test (qh.py harness: QSettings org RADIDE-TEST, offscreen, widget.grab screenshots).

Opens a temp copy of samples/Tests/DotNet/References/References.sln in the IDE and drives the Reference
Manager (Framework / Browse / COM / Projects / Shared Projects pages, search), the Dependencies node
(context menus, Properties window editing), Add Existing Item > Add As Link, the Object Browser (types,
members, XML docs, search, Go To Definition) and the language-server reload.
Run:  python samples/Tests/DotNet/References/tests/test_refs_ui.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLE = HERE.parent
ROOT = SAMPLE.parents[3]
os.environ.setdefault("QA_NAME", "dotnet-refs")
sys.path.insert(0, str(ROOT / "samples" / "Tests" / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, shot, wait  # noqa: E402

from PyQt6.QtCore import Qt  # noqa: E402

ROLE = Qt.ItemDataRole.UserRole


def tree_items(w):
    out = []
    stack = [w.solution.topLevelItem(i) for i in range(w.solution.topLevelItemCount())]
    while stack:
        it = stack.pop()
        out.append(it)
        stack.extend(it.child(i) for i in range(it.childCount()))
    return out


def find_dep(w, project_name, text):
    for it in tree_items(w):
        d = it.data(0, ROLE) or ("",)
        if isinstance(d, tuple) and d and d[0] == "foreign_dep" and it.text(0) == text:
            p = it.parent()
            while p is not None and (p.data(0, ROLE) or ("",))[0] != "project":
                p = p.parent()
            if p is not None and p.text(0).startswith(project_name):
                return it
    return None


def find_kind(w, project_name, kind, name=None):
    for it in tree_items(w):
        d = it.data(0, ROLE) or ("",)
        if isinstance(d, tuple) and d and d[0] == kind and (name is None or d[1] == name):
            p = it
            while p is not None and (p.data(0, ROLE) or ("",))[0] != "project":
                p = p.parent()
            if p is not None and p.text(0).startswith(project_name):
                return it
    return None


def actions_of(menu):
    out = []
    for a in menu.actions():
        out.append(a.text().replace("&", ""))
        if a.menu() is not None:
            out += ["  " + t for t in actions_of(a.menu())]
    return out


def main():
    work = Path(tempfile.mkdtemp(prefix="radide-refs-ui-"))
    sol = work / "References"
    shutil.copytree(SAMPLE, sol, ignore=shutil.ignore_patterns("bin", "obj", "tests"))
    from radide.foreign import msbuild as MB
    subprocess.run([MB.find_dotnet(), "build", "-nologo", "-v", "q"], cwd=sol / "MathKit", capture_output=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    dll9 = sol / "MathKit" / "bin" / "Debug" / "net9.0" / "MathKit.dll"
    check("MathKit built for the test", dll9.is_file())

    # a shared project (Shared Projects slice when present)
    try:
        from radide.dotnet.shared import model as SM
        from radide.foreign.vs_solution import load_solution_model
        sp = SM.create_shared_project(sol, "SharedBits", "C#")
        (sp.path.parent / "Bits.cs").write_text("namespace SharedBits { public static class Bits "
                                               "{ public static int Two => 2; } }\n", encoding="utf-8")
        SM.add_to_solution(load_solution_model(sol / "References.sln"), sp)
        have_shared = True
    except Exception as e:  # noqa: BLE001
        print("shared project slice unavailable:", e)
        have_shared = False

    w = qh.window()
    w.open_project(sol / "References.sln", ask=False)
    pump(2)
    from radide.foreign.vs_solution import VsSolution
    check("References.sln opened as a VS solution", isinstance(w.sln, VsSolution) and len(w.sln.all_projects()) == 3,
          type(w.sln))
    sdk = w.sln.project("SdkConsumer")
    leg = w.sln.project("LegacyConsumer")
    mk = w.sln.project("MathKit")

    from radide.foreign import vs_ui
    from radide.dotnet.refs.manager import ReferenceManager
    # ------------------------------------------------------------------ Reference Manager (SDK project)
    dlg = vs_ui.add_reference_dialog(w, sdk, 1, exec_=False)
    check("Add Reference opens the VS2022 Reference Manager", isinstance(dlg, ReferenceManager), type(dlg))
    dlg.show()
    pump(0.5)
    tops = [dlg.nav.topLevelItem(i).text(0) for i in range(dlg.nav.topLevelItemCount())]
    check("category tree: Assemblies / Projects / Shared Projects / COM / Browse",
          tops == ["Assemblies", "Projects", "Shared Projects", "COM", "Browse"], tops)
    fw = dlg.pages["framework"]
    rows = {fw.topLevelItem(i).text(0): fw.topLevelItem(i) for i in range(fw.topLevelItemCount())}
    check("SDK Framework page: implicit framework note + FrameworkReference choices",
          "implicitly" in dlg.notes["framework"].text() and "Microsoft.AspNetCore.App" in rows and
          not rows["Microsoft.NETCore.App"].flags() & Qt.ItemFlag.ItemIsEnabled, list(rows))
    shot(dlg, "refs_manager_sdk_framework")
    item = dlg.add_browse_file(dll9)
    check("Browse: MathKit.dll listed and checked", item is not None and item.checkState(0) == Qt.CheckState.Checked)
    dlg.select_page("browse")
    pump(0.3)
    shot(dlg, "refs_manager_browse")
    changes = dlg.apply()
    dlg.close()
    check("OK writes the Browse reference", changes == ["+MathKit.dll"] and "MathKit.dll</HintPath>" in sdk.ms.text,
          changes)
    pump(0.5)
    dep = find_dep(w, "SdkConsumer", "MathKit")
    check("Solution Explorer: Dependencies > Assemblies > MathKit", dep is not None and dep.parent().text(0) ==
          "Assemblies")

    # ------------------------------------------------------------------ Properties window
    w.solution.setCurrentItem(dep)
    pump(0.3)
    view = getattr(w, "ref_props_view", None)
    check("Properties window shows the reference properties", view is not None and not view.isHidden() and
          w.properties.tabs.isHidden(), view)
    if view is not None:
        check("properties: Path / Version / Copy Local", view.value("Path").lower() == str(dll9).lower() and
              view.value("Version") == "1.0.0.0" and view.value("Copy Local") == "True",
              [view.value(x) for x in ("Path", "Version", "Copy Local")])
        shot(w.dock_props, "refs_properties")
        view.set_value("Copy Local", "False")
        pump(0.8)
        check("properties: Copy Local=False written as <Private>False</Private>",
              "<Private>False</Private>" in sdk.ms.path.read_text(encoding="utf-8"))
        dep = find_dep(w, "SdkConsumer", "MathKit")
        check("the reference stays selected after the edit", dep is not None and w.solution.currentItem() is dep)
        w.solution.setCurrentItem(find_kind(w, "SdkConsumer", "project"))
        pump(0.2)
        check("selecting the project restores the form Properties panel", view.isHidden() and
              not w.properties.tabs.isHidden())

    # ------------------------------------------------------------------ menus
    deps_item = find_kind(w, "SdkConsumer", "foreign_deps")
    m = sdk.build_solution_menu(w, deps_item, "foreign_deps", "Dependencies")
    acts = actions_of(m)
    check("Dependencies menu: Add Project / Shared Project / COM / Assembly Reference",
          acts[:4] == ["Add Project Reference...", "Add Shared Project Reference...", "Add COM Reference...",
                       "Add Assembly Reference..."], acts)
    dep = find_dep(w, "SdkConsumer", "MathKit")
    m = sdk.build_solution_menu(w, dep, "foreign_dep", dep.data(0, ROLE)[1])
    acts = actions_of(m)
    check("reference menu: Open in Object Browser / Remove / Properties",
          acts[0] == "Open in Object Browser" and "Remove" in acts and "Properties" in acts, acts)
    pi = find_kind(w, "SdkConsumer", "project")
    acts = actions_of(sdk.build_solution_menu(w, pi, "project", "SdkConsumer"))
    check("project menu Add: Project / Shared Project / COM / Assembly Reference",
          all(f"  {t}" in acts for t in ("Project Reference...", "Shared Project Reference...", "COM Reference...",
                                          "Assembly Reference...")), acts)

    # ------------------------------------------------------------------ legacy: framework + COM + project
    dlg = vs_ui.add_reference_dialog(w, leg, "assemblies", exec_=False)
    dlg.show()
    fwp = dlg.pages["framework"]
    check(".NET Framework page lists the 4.8 reference assemblies", fwp.topLevelItemCount() > 100 and
          "4.8" in dlg.notes["framework"].text(), fwp.topLevelItemCount())
    dlg.search.setText("numerics")
    pump(0.2)
    visible = [fwp.topLevelItem(i).text(0) for i in range(fwp.topLevelItemCount()) if not fwp.topLevelItem(i).isHidden()]
    check("search filters the list (Ctrl+E box)", visible and all("numerics" in v.lower() for v in visible), visible)
    shot(dlg, "refs_manager_framework_search")
    check("check System.Numerics", dlg.check("framework", "System.Numerics"))
    dlg.search.clear()
    dlg.select_page("com")
    pump(0.3)
    check("COM page lists type libraries", dlg.pages["com"].topLevelItemCount() > 20)
    check("check Microsoft Scripting Runtime", dlg.check("com", "Microsoft Scripting Runtime"))
    dlg.search.setText("scripting runtime")
    pump(0.2)
    shot(dlg, "refs_manager_com")
    dlg.select_page("projects")
    check("Projects page lists the other projects", dlg.pages["projects"].topLevelItemCount() == 2)
    check("check MathKit project", dlg.check("projects", "MathKit"))
    changes = dlg.apply()
    dlg.close()
    text = leg.ms.path.read_text(encoding="utf-8")
    check("legacy: framework + COM + project reference written",
          '<Reference Include="System.Numerics" />' in text and '<COMReference Include="Scripting">' in text and
          r'<ProjectReference Include="..\MathKit\MathKit.csproj">' in text, changes)
    pump(0.5)
    check("References node shows Scripting (COM)", find_dep(w, "LegacyConsumer", "Scripting") is not None)
    com_dep = find_dep(w, "LegacyConsumer", "Scripting")
    w.solution.setCurrentItem(com_dep)
    pump(0.3)
    check("COM reference properties: Guid / Wrapper Tool", view is not None and
          view.value("Guid") == "{420b2830-e718-11cf-893d-00a0c9054228}" and view.value("Wrapper Tool") == "tlbimp")

    # circular reference
    dlg = vs_ui.add_reference_dialog(w, mk, "projects", exec_=False)
    dlg.check("projects", "LegacyConsumer")
    qh.MSGS.clear()
    changes = dlg.apply()
    dlg.close()
    check("circular project reference refused", not changes and any("circular" in str(m_) for m_ in qh.MSGS),
          qh.MSGS)

    # ------------------------------------------------------------------ Shared Projects page
    if have_shared:
        dlg = vs_ui.add_reference_dialog(w, sdk, "shared", exec_=False)
        rows = dlg.pages["shared"]
        check("Shared Projects page lists SharedBits", rows.topLevelItemCount() == 1 and
              rows.topLevelItem(0).text(0) == "SharedBits", rows.topLevelItemCount())
        dlg.check("shared", "SharedBits")
        changes = dlg.apply()
        dlg.close()
        check("shared project import written",
              r'<Import Project="..\SharedBits\SharedBits.projitems" Label="Shared" />' in
              sdk.ms.path.read_text(encoding="utf-8"), changes)
        pump(0.5)
        check("Dependencies > Shared Projects > SharedBits", find_dep(w, "SdkConsumer", "SharedBits") is not None)

    # ------------------------------------------------------------------ Add As Link
    from radide.dotnet.refs.ui import add_existing_item_dialog
    out = add_existing_item_dialog(w, leg, "Shared", files=[str(sol / "Common" / "SharedHelper.cs")], as_link=True)
    pump(0.5)
    check("Add As Link adds Compile + Link", out == ["SharedHelper.cs (link)"] and
          r"<Link>Shared\SharedHelper.cs</Link>" in leg.ms.path.read_text(encoding="utf-8"), out)
    linked = next((it for it in tree_items(w) if it.text(0) == "SharedHelper.cs"), None)
    check("Solution Explorer shows the linked file under its Link folder", linked is not None and
          linked.parent().text(0) == "Shared", linked and linked.parent().text(0))

    # ------------------------------------------------------------------ Object Browser
    check("View > Object Browser (Ctrl+Alt+J)", getattr(w, "a_object_browser", None) is not None and
          w.a_object_browser.shortcut().toString() == "Ctrl+Alt+J")
    from radide.dotnet.refs.ui import open_in_object_browser
    dep = find_dep(w, "SdkConsumer", "MathKit")
    ob = open_in_object_browser(w, sdk, "assembly", dep.data(0, ROLE)[1].split("|", 1)[1])
    pump(0.5)
    cur = ob.tree.currentItem()
    check("Open in Object Browser selects MathKit", cur is not None and cur.text(0) == "MathKit")
    check("Object Browser lists the solution's assemblies (+ framework packs)",
          ob.tree.topLevelItemCount() >= 3, [ob.tree.topLevelItem(i).text(0) for i in range(ob.tree.topLevelItemCount())])
    check("select type MathKit.Calculator", ob.select_type("MathKit.Calculator"))
    pump(0.3)
    members = [ob.members.item(i).text() for i in range(ob.members.count())]
    check("members of Calculator", any(x.startswith("Add(int, int)") for x in members) and
          any(x.startswith("Gcd(") for x in members) and any(x.startswith("History") for x in members), members)
    check("type description with the XML doc summary", "Small arithmetic helpers" in ob.desc.toPlainText(),
          ob.desc.toPlainText())
    ob.members.setCurrentRow(next(i for i, x in enumerate(members) if x.startswith("Add(")))
    pump(0.2)
    check("member description: signature + parameters", "public int Add(int a, int b)" in ob.desc.toPlainText() and
          "The first number." in ob.desc.toPlainText(), ob.desc.toPlainText())
    w.dock_object_browser.resize(1100, 420)
    shot(w.dock_object_browser, "refs_object_browser")
    n = ob.do_search("Gcd")
    check("Object Browser search finds Calculator.Gcd", n >= 1 and any("Calculator.Gcd" in ob.results.item(i).text()
                                                                      for i in range(ob.results.count())))
    ob.do_search("")
    from radide.dotnet.refs.object_browser import open_definition
    from radide.dotnet.refs import metadata as MD
    t = MD.read_assembly(dll9).find_type("MathKit.Calculator")
    res = open_definition(w, t, "Add")
    if hasattr(res, "done"):                         # ilspycmd present: decompiled in the background
        wait(lambda: res.done(), 120)
        pump(1)
    ed_texts = [w.tabs.tabText(i) for i in range(w.tabs.count())]
    check("Go To Definition opens the type source (decompiled or metadata)",
          any("Calculator" in x for x in ed_texts), ed_texts)

    # ------------------------------------------------------------------ language server reload
    from radide.dotnet.refs.lsp_reload import project_file_changed

    class FakeClient:
        def __init__(self):
            self.sent, self.stopped = [], False

        def _notify(self, method, params):
            self.sent.append((method, params))

        def running(self):
            return True

        def stop(self):
            self.stopped = True
    fake = FakeClient()
    w.lsp_manager.clients[("csharp", str(sdk.folder))] = fake
    roots = project_file_changed(w, sdk.ms.path)
    pump(0.6)
    check("C# language server notified + restarted after a reference edit",
          roots == [str(sdk.folder)] and fake.sent and fake.sent[0][0] == "workspace/didChangeWatchedFiles" and
          fake.stopped and ("csharp", str(sdk.folder)) not in w.lsp_manager.clients, (roots, fake.sent))

    shot(w, "refs_ide")
    shutil.rmtree(work, ignore_errors=True)
    qh.finish(w)


if __name__ == "__main__":
    main()
