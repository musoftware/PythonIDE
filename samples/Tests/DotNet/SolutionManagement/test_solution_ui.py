"""Solutions like Visual Studio 2022 in the IDE window (offscreen, QSettings "RADIDE-TEST", widget.grab only).

Copies Contoso/ and Fabrikam/ to the QA work folder, opens Contoso.sln and drives Solution Explorer
menus, solution folders + drag & drop, Configuration Manager, Project Dependencies, Add Projects from
another solution, Unload/Reload, multiple startup projects with a launch profile (Ctrl+F5 and F5),
the Project Properties document, User Secrets, Publish, Save As .slnx, New Solution from folders and a
RAD IDE C# project added to the VS solution.

    python samples/Tests/DotNet/SolutionManagement/test_solution_ui.py
"""
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QA_NAME", "dotnet_sln")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
from qh import *  # noqa: E402,F401,F403

from radide.dotnet import sln as S  # noqa: E402
from radide.dotnet.sln import dialogs as D  # noqa: E402
from radide.dotnet.sln import launch, ops, run, secrets  # noqa: E402
from radide.dotnet.sln.model import SolutionDoc  # noqa: E402
from radide.features import solution_ui  # noqa: E402
from radide.foreign import vs_ui  # noqa: E402

base = Path(WORK) / "dotnet_sln"
shutil.rmtree(base, ignore_errors=True)
shutil.copytree(HERE / "Contoso", base / "Contoso")
shutil.copytree(HERE / "Fabrikam", base / "Fabrikam")
C = base / "Contoso"
SLN = C / "Contoso.sln"


def items():
    out, stack = [], [w.solution.topLevelItem(i) for i in range(w.solution.topLevelItemCount())]
    while stack:
        it = stack.pop(0)
        out.append(it)
        stack.extend(it.child(i) for i in range(it.childCount()))
    return out


def node(kind, name=None):
    for it in items():
        d = it.data(0, Qt.ItemDataRole.UserRole) or ("",)
        if d[0] == kind and (name is None or str(d[1]).lower() == str(name).lower()):
            return it
    return None


def actions(menu):
    out = []
    for a in menu.actions():
        out.append(a.text().replace("&", ""))
        if a.menu() is not None:
            out += actions(a.menu())
    return out


from PyQt6.QtCore import Qt  # noqa: E402

w = window()
vs_ui.open_in_window(w, SLN)
pump(2)
sln = w.sln
check("solution opened with 4 projects", sln is not None and len(sln.all_projects()) == 4, sln)
check("solution folders src and tests", node("foreign_slnfolder", "src") is not None and
      node("foreign_slnfolder", "tests") is not None)
check("Directory.Build.props shown", node("vs_dirbuild") is not None)
check("launch profile drop-down visible", w.vs_profile_combo_action.isVisible() and w.vs_profile_combo.count() >= 1)

root_menu = solution_ui.build_menu(w, w.solution.topLevelItem(0))
acts = actions(root_menu)
for a in ("Configuration Manager...", "Existing Solution's Projects...", "New Solution Folder",
          "Configure Startup Projects...", "Save Solution As .slnx...", "Project Build Order...",
          "Existing RAD IDE Project..."):
    check(f"solution menu: {a}", a in acts, acts)
pm = solution_ui.build_menu(w, node("project", "Contoso.App"))
pacts = actions(pm)
for a in ("Unload Project", "Publish...", "Manage User Secrets", "Project Dependencies...", "Move To Solution Folder",
          "Configure Startup Projects..."):
    check(f"project menu: {a}", a in pacts, pacts)
fm = solution_ui.build_menu(w, node("foreign_slnfolder", "src"))
check("solution folder menu (Add, Rename, Remove, Build)", fm is not None and
      {"Rename", "Remove", "Build", "New Solution Folder", "Existing Project..."} <= set(actions(fm)),
      actions(fm) if fm else None)
shot(w, "sln_opened")

# ---------------------------------------------------------------- solution folders + drag & drop
src_guid = ops.folder_guid_by_path(sln, "src")
S.new_folder_dialog(w, sln, src_guid, name="ui")
pump(0.5)
check("New Solution Folder src/ui", node("foreign_slnfolder", "src/ui") is not None)
S.drop_on(w, node("project", "Contoso.Desktop"), node("foreign_slnfolder", "src/ui"))
pump(0.5)
doc = SolutionDoc.load(SLN)
check("drag & drop: Contoso.Desktop moved into src/ui", doc.folder_path(doc.find("Contoso.Desktop")) == ["src", "ui"])
it = node("project", "Contoso.Desktop")
check("tree shows Desktop under src/ui", it is not None and it.parent() is not None and
      it.parent().data(0, Qt.ItemDataRole.UserRole)[1] == "src/ui")
S.rename_folder_dialog(w, sln, ops.folder_guid_by_path(sln, "src/ui"), "ui", name="desktop")
check("rename solution folder", node("foreign_slnfolder", "src/desktop") is not None)
S.add_solution_items_dialog(w, sln, "", files=[C / "Directory.Build.props"])
pump(0.3)
check("Add to Solution Items", SolutionDoc.load(SLN).find("Solution Items").items == ["Directory.Build.props"] and
      node("vs_dirbuild") is None)

# ---------------------------------------------------------------- Configuration Manager
cm = D.configuration_manager(w, sln, exec_=False)
cm.new_solution_configuration("Staging", "Release", True)
cm.cell("Contoso.Tests", 3).setChecked(False)
shot(cm, "sln_configuration_manager")
cm.apply()
pump(0.5)
doc = SolutionDoc.load(SLN)
check("Configuration Manager: Staging written to the .sln", "Staging|Any CPU" in doc.configs)
check("Configuration Manager: Tests not built in Staging",
      not doc.project_config(doc.find("Contoso.Tests").guid, "Staging|Any CPU").build)
check("active configuration Staging + combo", sln.configuration == "Staging" and
      w.vs_config_combo.findText("Staging") >= 0)
check("project configuration Staging added (<Configurations>)",
      "Staging" in (C / "src/Contoso.App/Contoso.App.csproj").read_text(encoding="utf-8-sig"))
vs_ui.set_configuration(w, "Debug", "Any CPU")

# ---------------------------------------------------------------- Project Dependencies / Build Order
pd = D.project_dependencies(w, sln, "Contoso.App", exec_=False)
pd.set_dependency("Contoso.Desktop", True)
order = pd.build_order()
shot(pd, "sln_project_dependencies")
pd.apply()
doc = SolutionDoc.load(SLN)
check("Project Dependencies written", doc.find("Contoso.App").deps == [doc.find("Contoso.Desktop").guid])
check("Build Order: Core and Desktop before App", order.index("Contoso.Core") < order.index("Contoso.App") and
      order.index("Contoso.Desktop") < order.index("Contoso.App"), order)

# ---------------------------------------------------------------- merge another solution
imp = D.import_solution(w, sln, base / "Fabrikam" / "Fabrikam.sln", exec_=False)
check("import checklist lists Fabrikam's projects", {i.text(0) for i in imp.items()} == {"Fabrikam.Utils", "Fabrikam.Cli"})
shot(imp, "sln_import_solution")
added = imp.apply()
pump(0.5)
check("Add Projects from Solution: 2 projects loaded", len(sln.all_projects()) == 6 and len(added) == 2,
      [p.name for p in sln.all_projects()])
check("folder libs recreated in the tree", node("foreign_slnfolder", "libs") is not None and
      node("project", "Fabrikam.Utils") is not None and
      node("project", "Fabrikam.Utils").parent().data(0, Qt.ItemDataRole.UserRole)[1] == "libs")

# ---------------------------------------------------------------- unload / reload
utils = sln.project("Fabrikam.Utils")
ops.unload(w, sln, utils)
pump(0.5)
un = node("vs_unloaded", "Fabrikam.Utils")
check("Unload Project: greyed '(unloaded)' node in its folder", un is not None and "(unloaded)" in un.text(0) and
      un.parent().data(0, Qt.ItemDataRole.UserRole)[1] == "libs")
check("root shows '5 of 6 projects'", "(5 of 6 projects)" in w.solution.topLevelItem(0).text(0),
      w.solution.topLevelItem(0).text(0))
um = solution_ui.build_menu(w, un)
check("unloaded menu: Reload Project", um is not None and "Reload Project" in actions(um))
shot(w, "sln_unloaded")
ops.reload_project(w, sln, "Fabrikam.Utils")
pump(0.5)
check("Reload Project", sln.project("Fabrikam.Utils") is not None and node("project", "Fabrikam.Utils") is not None)

# ---------------------------------------------------------------- launch profile + multiple startup
app = sln.project("Contoso.App")
launch.save(app.folder, {"profiles": {"Contoso.App": {"commandName": "Project"},
                                      "Staging args": {"commandName": "Project", "commandLineArgs": "alpha \"b c\"",
                                                       "environmentVariables": {"CONTOSO_MODE": "ui-test"},
                                                       "workingDirectory": str(C)}}})
spp = D.solution_property_pages(w, sln, exec_=False)
spp.rb_multi.setChecked(True)
spp.set_action("Contoso.App", "Start")
spp.set_action("Fabrikam.Cli", "Start without debugging")
shot(spp, "sln_startup_projects")
spp.apply()
check("multiple startup saved", [(p.name, a) for p, a in run.startup_plan(sln)] ==
      [("Contoso.App", "Start"), ("Fabrikam.Cli", "Start without debugging")], run.startup_plan(sln))
run.refresh_profile_combo(w)
check("profile drop-down lists the launch profiles", w.vs_profile_combo.findText("Staging args") >= 0)
w.vs_profile_combo.setCurrentText("Staging args")
w.vs_profile_combo.activated.emit(w.vs_profile_combo.currentIndex())
check("active launch profile stored", run.active_profile_name(sln, app) == "Staging args")
for dbg in (False, True):
    w.output.clear()
    w.run_project(debug=dbg)
    done = wait(lambda: w.session is None or not w.session.running(), 300)
    pump(3)
    out = w.output.toPlainText()
    tag = "F5" if dbg else "Ctrl+F5"
    check(f"{tag}: Contoso.App ran with the profile's arguments", "ARGS=alpha|b c" in out, out[-2500:])
    check(f"{tag}: environment variable from the profile", "ENV=ui-test" in out, out[-1500:])
    check(f"{tag}: working directory from the profile", f"CWD={C}" in out, out[-1500:])
    wait(lambda: "[Fabrikam.Cli] Hello, World!" in w.output.toPlainText(), 60)
    check(f"{tag}: second startup project ran (multiple startup)", "[Fabrikam.Cli] Hello, World!" in
          w.output.toPlainText(), w.output.toPlainText()[-1500:])
    check(f"{tag}: finished", done)
    if w.session is not None and w.session.running():
        w.session.stop()
        pump(1)

# ---------------------------------------------------------------- Project Properties document
doc_w = vs_ui.project_properties(w, app)
pump(0.5)
check("Properties document opens as a tab", w.tabs.currentWidget() is doc_w and doc_w.objectName() ==
      "ProjectPropertiesDocument")
doc_w.search.setText("nullable")
check("search filters the properties", doc_w.visible_labels() == ["Nullable"], doc_w.visible_labels())
doc_w.search.setText("")
doc_w.set_value("DefineConstants", "$(DefineConstants);UI_TEST", "Debug")
doc_w.set_value("Nullable", "disable")
doc_w.add_using("System.Text")
doc_w.set_build_event("post", "echo built")
doc_w.cfg.setCurrentText("All configurations")
shot(w, "sln_project_properties")
text = (C / "src/Contoso.App/Contoso.App.csproj").read_text(encoding="utf-8-sig")
check("properties written to the csproj", "<DefineConstants>$(DefineConstants);UI_TEST</DefineConstants>" in text and
      "<Nullable>disable</Nullable>" in text and '<Using Include="System.Text" />' in text and
      '<Exec Command="echo built" />' in text, text)
check("inherited Company shown from Directory.Build.props", "Inherited from Directory.Build.props" in
      doc_w.value_of(next(s for s in __import__("radide.dotnet.sln.properties", fromlist=["SPECS"]).SPECS
                          if s.name == "Company"))[1])
sp = doc_w.manage_secrets(open_it=False)
check("Manage User Secrets: secrets.json under %APPDATA%", sp.is_file() and "UserSecrets" in str(sp) and
      app.ms.prop("UserSecretsId") in str(sp))
shutil.rmtree(sp.parent, ignore_errors=True)
snk = doc_w.create_snk("ui.snk")
check("Signing: .snk created and SignAssembly set", snk.is_file() and app.ms.prop("SignAssembly") == "True")
lp = launch_dlg = __import__("radide.dotnet.sln.properties", fromlist=["x"]).launch_profiles_dialog(w, app, exec_=False)
n = lp.new_profile("Executable", "Notepad")
lp.set_fields(args="readme.txt", exe="%WINDIR%\\notepad.exe")
lp.save()
check("Launch Profiles UI: Executable profile saved", launch.load(app.folder)["profiles"][n]["executablePath"] ==
      "%WINDIR%\\notepad.exe")
shot(lp, "sln_launch_profiles")

# ---------------------------------------------------------------- publish
pub = D.publish_dialog(w, app, exec_=False)
pub.rid.setCurrentText("win-x64")
pub.single.setChecked(True)
pub.location.setText("bin\\publish-ui\\")
shot(pub, "sln_publish")
rc = pub.publish(wait=True)
check("Publish: dotnet publish with FolderProfile.pubxml", rc == 0 and
      (app.folder / "bin" / "publish-ui" / "Contoso.App.exe").is_file() and
      (app.folder / "Properties" / "PublishProfiles" / "FolderProfile.pubxml").is_file(), w.output.toPlainText()[-1500:])

# ---------------------------------------------------------------- RAD IDE C# project in the solution
rad = base / "HelloCSharp"
shutil.copytree(Path(ROOT) / "samples" / "HelloCSharp", rad, ignore=shutil.ignore_patterns("_build", "bin", "obj"))
S.add_rad_project_dialog(w, sln, rad)
pump(0.5)
check("RAD IDE C# project added (its _build/csharp/RadApp.csproj)", sln.project("HelloCSharp") is not None and
      "RadApp.csproj" in SLN.read_text(encoding="utf-8-sig"))

# ---------------------------------------------------------------- Save As .slnx / New solution from folders
target = C / "Contoso.slnx"
S.save_as_dialog(w, sln, ".slnx", target=target)
pump(2)
check("Save Solution As .slnx: reopened from the .slnx", w.sln is not None and Path(w.sln.file).suffix == ".slnx"
      and len(w.sln.all_projects()) >= 6, w.sln.file if w.sln else None)
check(".slnx tree keeps nested folders", node("foreign_slnfolder", "src/desktop") is not None)
S.new_folder_dialog(w, w.sln, "", name="docs")
check("edit the .slnx (New Solution Folder)", '<Folder Name="/docs/" />' in target.read_text(encoding="utf-8"))
shot(w, "sln_slnx")
nd = D.new_solution_from_folders(w, [base / "Fabrikam"], exec_=False)
nd.name.setText("FromFolders")
nd.location.setText(str(base))
check("New Solution from folders: projects found", nd.found.count() == 2)
p = nd.apply(open_it=False)
d = SolutionDoc.load(p)
check("New Solution from folders: .sln with both projects and folder 'Fabrikam'", p.is_file() and
      len(d.real_projects()) == 2 and d.find("Fabrikam") is not None)
finish(w)
