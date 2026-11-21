"""NuGet UI in the IDE (QA harness, QSettings org RADIDE-TEST, screenshots with widget.grab only):
Manage NuGet Packages (project + solution: Browse / Installed / Updates / Consolidate), install / update /
uninstall / consolidate from the document, license acceptance hook, deprecation banner, Package Manager
Console (Get-Package, Find-Package, Install-Package, tab completion, history), Options > NuGet Package
Manager > Package Sources with a local feed, a RAD IDE C# GUI-Bridge project, and a build after install.
Needs network (nuget.org). Run:  python samples/Tests/DotNet/NuGetTests/test_nuget_ui.py"""
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
os.environ.setdefault("QA_NAME", "nuget")
import qh  # noqa: E402
from qh import check, pump, shot, wait  # noqa: E402

from radide.dotnet.nuget import config as C, projects as P  # noqa: E402
from radide.foreign import msbuild as MB, vs_ui  # noqa: E402

WORK = Path(qh.WORK) / f"nuget-ui-{os.getpid()}"   # unique: a language server may still lock an old copy
shutil.rmtree(WORK, ignore_errors=True)
SOL = WORK / "NuGetSolution"
shutil.copytree(HERE.parent / "NuGetSolution", SOL, ignore=shutil.ignore_patterns("bin", "obj", ".vs"))
# a solution nuget.config, so the Options page writes there (never the user's NuGet.Config)
cf = C.ConfigFile.load(SOL / "nuget.config", create=True)
cf.add_source("nuget.org", C.NUGET_ORG)
cf.save()
FEED = WORK / "LocalFeed"
FEED.mkdir(parents=True)
gp = C.global_packages_folder() / "newtonsoft.json" / "13.0.1" / "newtonsoft.json.13.0.1.nupkg"
if gp.is_file():
    shutil.copy2(gp, FEED / gp.name)

w = qh.window()
vs_ui.open_in_window(w, SOL / "NuGetSolution.sln")
pump(2)
check("solution opened", w.sln is not None and len(w.sln.all_projects()) == 2)

# ---------------------------------------------------------------- menus
tools = next(a.menu() for a in w.menuBar().actions() if a.text().replace("&", "") == "Tools")
sub = next((a.menu() for a in tools.actions() if a.menu() is not None and a.text() == "NuGet Package Manager"), None)
check("Tools > NuGet Package Manager menu", sub is not None and
      [a.text() for a in sub.actions() if a.text()][:2] == ["Package Manager Console",
                                                             "Manage NuGet Packages for Solution..."])
sm = vs_ui.solution_menu(w, w.sln, None)
check("solution context menu has NuGet commands", "Manage NuGet Packages for Solution..." in
      [a.text() for a in sm.actions()] and "Restore NuGet Packages" in [a.text() for a in sm.actions()])


def idle(view, t=60):
    pump(0.2)
    return wait(lambda: view.busy == 0 and not view._running, t)


def pick_version(view, v):
    for i in range(1, view.d_version.count()):
        if view.d_version.itemData(i) == v:
            view.d_version.setCurrentIndex(i)
            return True
    return False


# ---------------------------------------------------------------- solution level (consolidate)
from radide.features import nuget_ide  # noqa: E402

sv = nuget_ide.manage_solution(w)
check("solution document opened as a tab", sv is not None and w.tabs.currentWidget() is sv and
      w.tabs.tabText(w.tabs.currentIndex()) == "NuGet - Solution")
sv.show_preview = False
idle(sv)
check("Browse lists packages", sv.list.count() > 5, sv.status.text())
wait(lambda: sv.update_count > 0 and sv.consolidate_count > 0, 60)
check("Updates + Consolidate badges", sv.badges["updates"].isVisible() and sv.badges["consolidate"].text() == "1",
      (sv.update_count, sv.consolidate_count))
sv.set_tab("consolidate")
idle(sv)
check("Consolidate lists Newtonsoft.Json", sv.select_package("Newtonsoft.Json"))
idle(sv)
names = [sv.d_projects.topLevelItem(i).text(0) for i in range(sv.d_projects.topLevelItemCount())]
vers = [sv.d_projects.topLevelItem(i).text(1) for i in range(sv.d_projects.topLevelItemCount())]
check("projects list with installed versions", names == ["ConsoleApp", "LibA"] and vers == ["13.0.1", "13.0.3"],
      (names, vers))
shot(sv, "nuget_solution_consolidate")
pick_version(sv, "13.0.3")
check("Install enabled for checked projects", sv.install_btn.isEnabled())
sv.install()
idle(sv, 240)
txt = (SOL / "ConsoleApp" / "ConsoleApp.csproj").read_text(encoding="utf-8-sig")
check("consolidated ConsoleApp to 13.0.3", 'Include="Newtonsoft.Json" Version="13.0.3"' in txt, txt)
wait(lambda: sv.consolidate_count == 0, 60)
check("Consolidate badge cleared", not sv.badges["consolidate"].isVisible())

# ---------------------------------------------------------------- project level
pv = nuget_ide.manage_project(w, w.sln.project("ConsoleApp"))
check("project document 'NuGet: ConsoleApp'", pv is not None and w.tabs.tabText(w.tabs.currentIndex()) ==
      "NuGet: ConsoleApp" and pv.header.text() == "NuGet Package Manager: ConsoleApp")
pv.show_preview = False
idle(pv)
pv.search.setText("Newtonsoft.Json")
pv.refresh()
idle(pv)
check("search result first = Newtonsoft.Json", pv.list.count() and
      pv.list.item(0).data(256) is not None and pv.list.item(0).data(256).id == "Newtonsoft.Json")
pv.list.setCurrentRow(0)
idle(pv)
check("details: version combo + license + dependencies", pv.d_version.count() > 5 and
      "License" in pv.d_details.toHtml() and "Dependencies" in pv.d_details.toPlainText())
check("installed version shown + Update button", pv.d_installed.text() == "13.0.3" and pv.install_btn.text() == "Update")
pv.d_tabs.setCurrentIndex(1)
wait(lambda: "Loading" not in pv.d_readme.toPlainText(), 30)
check("README tab rendered", len(pv.d_readme.toPlainText()) > 20, pv.d_readme.toPlainText()[:200])
pv.d_tabs.setCurrentIndex(0)
shot(pv, "nuget_project_browse")

# license acceptance: declining installs nothing
pv.search.setText("Humanizer.Core")
pv.refresh()
idle(pv)
pv.select_package("Humanizer.Core")
idle(pv)
pick_version(pv, "2.14.1")
seen = []
m = pv._meta_for("2.14.1")
if m is not None:
    m.require_license_acceptance = True
pv.confirm_licenses = lambda metas: (seen.append([x.id for x in metas]), False)[1]
pv.install()
pump(1)
check("license dialog shown; decline installs nothing", seen == [["Humanizer.Core"]] and
      "Humanizer" not in (SOL / "ConsoleApp" / "ConsoleApp.csproj").read_text(encoding="utf-8-sig"), seen)
pv.confirm_licenses = lambda metas: True
pv.install()
idle(pv, 240)
check("Install from Browse", 'Include="Humanizer.Core" Version="2.14.1"' in
      (SOL / "ConsoleApp" / "ConsoleApp.csproj").read_text(encoding="utf-8-sig"))


def tree_texts(tree):
    out = []

    def walk(it):
        out.append(it.text(0))
        for k in range(it.childCount()):
            walk(it.child(k))
    for k in range(tree.topLevelItemCount()):
        walk(tree.topLevelItem(k))
    return out


check("Solution Explorer shows the package", any("Humanizer.Core" in t for t in tree_texts(w.solution)))

pv.set_tab("installed")
idle(pv)
recs = [pv.list.item(i).data(256) for i in range(pv.list.count())]
ids = [r.id for r in recs if r is not None and not r.transitive]
check("Installed tab: top-level packages", "Newtonsoft.Json" in ids and "Humanizer.Core" in ids, ids)
pv.select_package("Humanizer.Core")
idle(pv)
shot(pv, "nuget_project_installed")
pv.uninstall()
idle(pv, 240)
check("Uninstall", "Humanizer" not in (SOL / "ConsoleApp" / "ConsoleApp.csproj").read_text(encoding="utf-8-sig"))

pv.search.setText("")
pv.set_tab("updates")
idle(pv)
pv.select_all.setChecked(True)
check("Updates tab: checkable rows", pv.checked_records() or pv.list.count() == 0,
      (pv.list.count(), pv.status.text(), [pv.list.item(i).data(256) for i in range(pv.list.count())][:3]))
shot(pv, "nuget_project_updates")

# deprecation banner
pv.set_tab("browse")
pv.search.setText("Microsoft.Azure.ServiceBus")
pv.refresh()
idle(pv)
pv.select_package("Microsoft.Azure.ServiceBus")
idle(pv)
check("deprecation warning banner", pv.d_warn.isVisible() and "deprecated" in pv.d_warn.text(), pv.d_warn.text())
shot(pv, "nuget_deprecated")

# ---------------------------------------------------------------- Package Manager Console
pmc = nuget_ide.show_console(w)
pmc._no_popup = True
check("console dock + default project combo", pmc.project.count() == 2 and "PM>" in pmc.text.toPlainText())


def run_cmd(line, t=240):
    box = []
    pmc.execute(line, lambda ok: box.append(ok))
    wait(lambda: box, t)
    pump(0.3)
    return box[0] if box else None


pmc.project.setCurrentText("LibA")
check("Get-Package", run_cmd("Get-Package") and "Newtonsoft.Json" in pmc.text.toPlainText() and
      "Humanizer.Core" in pmc.text.toPlainText())
check("Find-Package", run_cmd("Find-Package Serilog -First 3") and "Serilog" in pmc.text.toPlainText())
ok = run_cmd("Uninstall-Package Humanizer.Core -ProjectName LibA")
check("Uninstall-Package -ProjectName", ok and "Humanizer" not in
      (SOL / "LibA" / "LibA.csproj").read_text(encoding="utf-8-sig"), pmc.text.toPlainText()[-600:])
ok = run_cmd("Install-Package Humanizer.Core -Version 2.14.1 -ProjectName LibA")
check("Install-Package -Version", ok and 'Humanizer.Core" Version="2.14.1"' in
      (SOL / "LibA" / "LibA.csproj").read_text(encoding="utf-8-sig"), (ok, pmc.text.toPlainText()[-900:]))
check("unknown command error", run_cmd("Install-Packag X") is False and "is not recognized" in pmc.text.toPlainText())
comp = []
pmc.text.set_input("Install-Package Newtonso")
pmc.complete(lambda items: comp.append(items))
wait(lambda: comp, 30)
check("tab completion of package ids", comp and "Newtonsoft.Json" in comp[0] and
      pmc.text.current_input().startswith("Install-Package Newtonsoft.Json"), comp)
pmc.text.set_input("")
from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtGui import QKeyEvent  # noqa: E402
from PyQt6.QtCore import QEvent  # noqa: E402
pmc.text.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier))
check("history (Up)", pmc.text.current_input() == "Install-Packag X", pmc.text.current_input())
pmc.text.set_input("")
shot(w.dock_nuget_console, "nuget_console")

# ---------------------------------------------------------------- Options > Package Sources (local feed)
from radide.features.settings import OptionsDialog  # noqa: E402
dlg = OptionsDialog(w)
tabs = dlg.findChild(__import__("PyQt6.QtWidgets", fromlist=["QTabWidget"]).QTabWidget)
titles = [tabs.tabText(i) for i in range(tabs.count())]
check("Options has 'NuGet Package Manager'", "NuGet Package Manager" in titles, titles)
page = next(tabs.widget(i) for i in range(tabs.count()) if tabs.tabText(i) == "NuGet Package Manager")
check("Package Sources writes the solution nuget.config", page.sources.target.resolve() == (SOL / "nuget.config").resolve(),
      page.sources.target)
page.sources.add_source("LocalFeed", str(FEED))
tabs.setCurrentWidget(page)
page.tabs.setCurrentIndex(1)
shot(dlg, "nuget_options_sources")
dlg.apply() if hasattr(dlg, "apply") else page.apply()
dlg.close()
check("local source saved", any(s.name == "LocalFeed" for s in C.effective_sources(SOL)))
pv._fill_sources()
i = pv.source.findText("LocalFeed")
pv.source.setCurrentIndex(i)
pv.search.setText("newtonsoft")
pv.refresh()
idle(pv)
recs = [pv.list.item(k).data(256) for k in range(pv.list.count())]
check("browse a local folder feed", i >= 0 and any(r and r.id == "Newtonsoft.Json" for r in recs), [r and r.id for r in recs])
pv.source.setCurrentIndex(pv.source.findText("Global packages folder (offline)"))
pv.refresh()
idle(pv)
check("browse the global packages folder (offline)", pv.list.count() > 0)

# ---------------------------------------------------------------- build after the changes
code, out = P.run(MB.build_argv(SOL / "NuGetSolution.sln", "Debug", "", sdk=True), SOL, lambda s: None, timeout=600)
check("solution builds after the NuGet changes", code == 0, out[-800:])

# ---------------------------------------------------------------- RAD IDE C# GUI-Bridge project
bridge = WORK / "CsBridge"
shutil.copytree(HERE.parents[1] / "All" / "agents2" / "qa" / "probe" / "csharp-bridge", bridge,
                ignore=shutil.ignore_patterns("bin", "obj", ".vs"), dirs_exist_ok=True)
w.open_project(bridge, ask=False)
pump(2)
from radide.dotnet.nuget import context as CX  # noqa: E402
nps = CX.dotnet_projects(w)
check("C# GUI-Bridge project has a NuGet project (RadApp.csproj)", len(nps) == 1 and nps[0].path.name == "RadApp.csproj"
      and nps[0].style == P.STYLE_PR, nps)
from radide.features import packages as PK  # noqa: E402
bv = PK.manage_packages(w)
check("Project > Manage Packages opens the NuGet document for C#", bv is not None and
      type(bv).__name__ == "PackageManagerView", type(bv).__name__)
if bv is not None:
    idle(bv)
    shot(bv, "nuget_csharp_bridge")

qh.finish(w)
