"""Solution management without the IDE window (radide/dotnet/sln): .sln/.slnx model, merging, folders,
dependencies, configurations, project properties, launch profiles, user secrets, strong name keys,
publish. Works on a copy of Contoso/ and Fabrikam/ in %TEMP% (the samples are never changed).

    python samples/Tests/DotNet/SolutionManagement/test_solution_core.py [--no-build]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

from radide.dotnet.sln import launch, msprops, publish, secrets, signing  # noqa: E402
from radide.dotnet.sln.model import SolutionDoc  # noqa: E402
from radide.foreign.msbuild import MSBuildProject, find_dotnet  # noqa: E402

BUILD = "--no-build" not in sys.argv
RESULTS = []
ENV = {**os.environ, "DOTNET_NOLOGO": "1", "DOTNET_CLI_TELEMETRY_OPTOUT": "1"}
DN = find_dotnet()


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:1500]}]"), flush=True)
    return bool(cond)


def run(argv, cwd, timeout=900):
    r = subprocess.run([str(a) for a in argv], cwd=str(cwd), capture_output=True, text=True, env=ENV, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def nl(t):
    return t.replace("\r\n", "\n")


work = Path(tempfile.mkdtemp(prefix="radide-sln-"))
shutil.copytree(HERE / "Contoso", work / "Contoso")
shutil.copytree(HERE / "Fabrikam", work / "Fabrikam")
C = work / "Contoso"
print("work:", work)

# ---------------------------------------------------------------- load / round trip
sln = C / "Contoso.sln"
doc = SolutionDoc.load(sln)
check("load: 4 projects, 2 solution folders", len(doc.real_projects()) == 4 and
      sorted(f.name for f in doc.folders()) == ["src", "tests"], [e.name for e in doc.projects])
check("round trip: unchanged .sln is byte-identical", doc.text() == doc.file.text)
check("folder path of Contoso.Core is src", doc.folder_path(doc.find("Contoso.Core")) == ["src"])

# ---------------------------------------------------------------- folders, items, nesting, dependencies
ui = doc.add_folder("ui", doc.find("src").guid)
doc.move(doc.find("Contoso.Desktop").guid, ui.guid)
items = doc.add_folder("Solution Items")
doc.add_item(items.guid, C / "Directory.Build.props")
docs = doc.add_folder("docs")
doc.rename_folder(docs.guid, "documentation")
try:
    doc.move(doc.find("src").guid, ui.guid)
    check("move a folder into its own child is refused", False)
except ValueError:
    check("move a folder into its own child is refused", True)
doc.set_dependencies(doc.find("Contoso.App").guid, [doc.find("Contoso.Desktop").guid])
try:
    doc.set_dependencies(doc.find("Contoso.Desktop").guid, [doc.find("Contoso.App").guid])
    check("circular project dependency is refused", False)
except ValueError:
    check("circular project dependency is refused", True)
doc.save()
d2 = SolutionDoc.load(sln)
check("nested folder src/ui holds Contoso.Desktop", d2.folder_path(d2.find("Contoso.Desktop")) == ["src", "ui"])
check("solution items written", d2.find("Solution Items").items == ["Directory.Build.props"])
check("ProjectDependencies written", d2.find("Contoso.App").deps == [d2.find("Contoso.Desktop").guid] and
      "ProjectSection(ProjectDependencies) = postProject" in d2.file.text)
check("renamed folder", d2.find("documentation") is not None and d2.find("docs") is None)
code, out = run([DN, "sln", str(sln), "list"], C)
check("dotnet sln list reads the edited .sln", code == 0 and out.count(".csproj") == 4, out)

# build order: references from the project files + ProjectDependencies
refs = {}
for e in d2.real_projects():
    ms = MSBuildProject.load(C / e.path)
    refs[e.guid] = [d2.by_file((ms.folder / r.include.replace("\\", "/")).resolve()).guid
                    for r in ms.project_references]
order = [e.name for e in d2.build_order(refs)]
check("build order: Core before App and Tests, Desktop before App",
      order.index("Contoso.Core") < order.index("Contoso.App") and order.index("Contoso.Core") <
      order.index("Contoso.Tests") and order.index("Contoso.Desktop") < order.index("Contoso.App"), order)

# ---------------------------------------------------------------- configurations
d2.add_configuration("Staging", "Release")
tests = d2.find("Contoso.Tests")
d2.set_project_config(tests.guid, "Staging|Any CPU", build=False)
d2.add_platform("ARM64", "Any CPU")
d2.save()
d3 = SolutionDoc.load(sln)
check("configuration Staging for every platform", {"Staging|Any CPU", "Staging|x64", "Staging|x86",
                                                   "Staging|ARM64"} <= set(d3.configs), d3.configs)
pc = d3.project_config(tests.guid, "Staging|Any CPU")
check("Staging maps Tests to Release without Build.0", pc is not None and pc.cfg == "Release" and not pc.build,
      pc)
check("other projects build in Staging", d3.project_config(d3.find("Contoso.App").guid, "Staging|Any CPU").build)
d3.rename_configuration("Staging", "QA")
d3.remove_platform("ARM64")
d3.save()
d4 = SolutionDoc.load(sln)
check("rename configuration / remove platform", "QA|Any CPU" in d4.configs and not any("ARM64" in c for c in d4.configs)
      and not any(c.startswith("Staging") for c in d4.configs), d4.configs)

# ---------------------------------------------------------------- .slnx write / read / round trip
mig = work / "migrate"
mig.mkdir()
shutil.copy2(sln, mig / "Contoso.sln")
code, out = run([DN, "sln", "Contoso.sln", "migrate"], mig)
slnx = C / "Contoso.slnx"
d4.save_as(slnx)
mine = slnx.read_text(encoding="utf-8")
if code == 0:
    theirs = (mig / "Contoso.slnx").read_text(encoding="utf-8-sig")
    if not check(".slnx written like 'dotnet sln migrate'", nl(mine) == nl(theirs)):
        import difflib
        print("".join(difflib.unified_diff(nl(theirs).splitlines(True), nl(mine).splitlines(True), "migrate", "mine")))
x = SolutionDoc.load(slnx)
check(".slnx round trip (read + write unchanged)", x.text() == x.file.text)
check(".slnx keeps folders, items, deps, Tests not built in QA",
      x.folder_path(x.find("Contoso.Desktop")) == ["src", "ui"] and x.find("Solution Items").items ==
      ["Directory.Build.props"] and x.find("Contoso.App").deps == [x.find("Contoso.Desktop").guid] and
      not x.project_config(x.find("Contoso.Tests").guid, "QA|Any CPU").build)
back = work / "back.sln"
back.write_bytes(x.text("sln").encode("utf-8-sig"))
check(".slnx -> .sln -> .slnx is stable", SolutionDoc.load(back).text("slnx") == x.text())
code, out = run([DN, "sln", str(slnx), "list"], C)
check("dotnet sln list reads the written .slnx", code == 0 and out.count(".csproj") == 4, out)

# ---------------------------------------------------------------- merging another solution
fab = SolutionDoc.load(work / "Fabrikam" / "Fabrikam.sln")
d4 = SolutionDoc.load(sln)
merged = d4.import_from(fab, None)
d4.save()
d5 = SolutionDoc.load(sln)
check("merge: Fabrikam's 2 projects added", {"Fabrikam.Utils", "Fabrikam.Cli"} <= {e.name for e in d5.real_projects()},
      [e.name for e in d5.real_projects()])
check("merge: solution folder 'libs' recreated", d5.folder_path(d5.find("Fabrikam.Utils")) == ["libs"])
check("merge: mapping for every configuration (QA too)",
      all(d5.project_config(d5.find("Fabrikam.Cli").guid, c) is not None for c in d5.configs))
again = d5.import_from(fab, None)
check("merge twice adds nothing", again == [])
x2 = SolutionDoc.load(slnx)
x2.import_from(fab, [fab.find("Fabrikam.Utils").guid])
x2.save()
check("merge into .slnx (one project, folder kept)", '<Folder Name="/libs/">' in slnx.read_text(encoding="utf-8") and
      "Fabrikam.Utils.csproj" in slnx.read_text(encoding="utf-8"))
shp = d5.add_project(ROOT / "samples" / "Tests" / "ForeignProjects" / "VsSolution" / "MathLib" / "MathLib.csproj") \
    if False else None
# any project type: a .sqlproj stub gets the SQL type guid and configurations
sq = C / "db" / "Contoso.Db.sqlproj"
sq.parent.mkdir()
sq.write_text('<Project DefaultTargets="Build"><PropertyGroup><Name>Contoso.Db</Name></PropertyGroup></Project>',
              encoding="utf-8")
e = d5.add_project(sq)
d5.remove(e.guid)
check("any project type (.sqlproj type guid)", e.type_guid == "{00D1A9C2-B5F0-4AF3-8072-F6C62B433612}")
d5.save()

# ---------------------------------------------------------------- project properties round trip
app = C / "src" / "Contoso.App" / "Contoso.App.csproj"
ms = MSBuildProject.load(app)
debug, release = msprops.cfg_condition("Debug", "AnyCPU"), msprops.cfg_condition("Release", "AnyCPU")
msprops.set_value(ms, "DefineConstants", "$(DefineConstants);CONTOSO_DEBUG", debug)
msprops.set_value(ms, "TreatWarningsAsErrors", "true", release)
msprops.set_value(ms, "Nullable", "disable")
msprops.set_value(ms, "AssemblyName", "ContosoApp")
msprops.add_using(ms, "System.Text")
msprops.set_build_event(ms, "post", 'echo built "$(TargetName)"')
ms.save()
text = app.read_text(encoding="utf-8-sig")
check("per-configuration PropertyGroup like VS2022",
      "<PropertyGroup Condition=\"'$(Configuration)|$(Platform)'=='Debug|AnyCPU'\">" in text and
      "<DefineConstants>$(DefineConstants);CONTOSO_DEBUG</DefineConstants>" in text, text)
check("PostBuild target with Exec", '<Target Name="PostBuild" AfterTargets="PostBuildEvent">' in text and
      "&quot;$(TargetName)&quot;" in text, text)
ms2 = MSBuildProject.load(app)
check("read back: values per configuration", msprops.get(ms2, "DefineConstants", debug).endswith("CONTOSO_DEBUG") and
      msprops.get(ms2, "TreatWarningsAsErrors", release) == "true" and msprops.get(ms2, "Nullable") == "disable" and
      msprops.build_event(ms2, "post") == 'echo built "$(TargetName)"' and ("System.Text", False) in msprops.usings(ms2))
check("inherited from Directory.Build.props", msprops.inherited(ms2, "Company")[0] == "Contoso Ltd")
msprops.set_value(ms2, "AssemblyName", "")
ms2.save()
check("empty value removes the property", "<AssemblyName>" not in app.read_text(encoding="utf-8-sig"))
core = C / "src" / "Contoso.Core" / "Contoso.Core.csproj"
mc = MSBuildProject.load(core)
msprops.remove(mc, "TargetFramework")
msprops.set_value(mc, "TargetFrameworks", "net9.0;net8.0")
mc.save()
check("multi-targeting TargetFrameworks", MSBuildProject.load(core).target_frameworks == ["net9.0", "net8.0"])

# ---------------------------------------------------------------- strong name key
snk = signing.create_snk(C / "src" / "Contoso.Core" / "Contoso.snk")
k = signing.parse_snk(snk.read_bytes())
check(".snk: 596-byte RSA2 PRIVATEKEYBLOB with a valid key pair", snk.stat().st_size == 596 and k["bits"] == 1024 and
      k["p"] * k["q"] == k["n"] and pow(pow(42, k["e"], k["n"]), k["d"], k["n"]) == 42)
mc = MSBuildProject.load(core)
msprops.set_value(mc, "SignAssembly", "True")
msprops.set_value(mc, "AssemblyOriginatorKeyFile", "Contoso.snk")
mc.save()

# ---------------------------------------------------------------- user secrets
ms3 = MSBuildProject.load(app)
sid = secrets.ensure_id(ms3)
sf = secrets.set_secret(MSBuildProject.load(app), "Contoso:ApiKey", "s3cr3t")
check("user secrets: UserSecretsId + secrets.json in %APPDATA%", MSBuildProject.load(app).prop("UserSecretsId") == sid
      and sf == secrets.secrets_file(sid) and json.loads(sf.read_text())["Contoso:ApiKey"] == "s3cr3t")
code, out = run([DN, "user-secrets", "list", "--project", str(app)], C)
check("dotnet user-secrets sees the secret", "Contoso:ApiKey = s3cr3t" in out, out)

# ---------------------------------------------------------------- launch profile
data = {"profiles": {"Contoso.App": {"commandName": "Project"},
                     "Staging args": {"commandName": "Project", "commandLineArgs": "--mode \"two words\" 3",
                                      "environmentVariables": {"CONTOSO_MODE": "staging"},
                                      "workingDirectory": str(C)}}}
launch.save(app.parent, data)
loaded = launch.load(app.parent)
r = launch.resolve(loaded["profiles"]["Staging args"], {"ProjectDir": str(app.parent)})
check("launch profile resolve: args/env/cwd", r["args"] == ["--mode", "two words", "3"] and
      r["env"]["CONTOSO_MODE"] == "staging" and r["cwd"] == str(C), r)
check("default profile = first Project profile", launch.default_profile(loaded) == "Contoso.App")

# ---------------------------------------------------------------- build, run, publish (dotnet)
if BUILD and DN:
    code, out = run([DN, "build", str(sln), "-c", "QA", "-nologo", "-v:q"], C, 1800)
    check("dotnet build of the merged solution in QA", code == 0, out[-3000:])
    check("QA: Contoso.Tests not built (Build.0 unchecked)",
          not (C / "tests" / "Contoso.Tests" / "bin" / "Release").exists() and
          (C / "src" / "Contoso.App" / "bin" / "Release").exists(), out[-800:])
    code, out = run([DN, "build", str(sln), "-c", "Debug", "-nologo", "-v:q"], C, 1800)
    check("dotnet build Debug (signed multi-target Core, post-build event)", code == 0, out[-3000:])
    dll = C / "src" / "Contoso.Core" / "bin" / "Debug" / "net9.0" / "Contoso.Core.dll"
    ps = subprocess.run(["powershell", "-NoProfile", "-Command",
                         f"[BitConverter]::ToString([Reflection.AssemblyName]::GetAssemblyName('{dll}')"
                         ".GetPublicKeyToken())"], capture_output=True, text=True)
    check("Contoso.Core.dll is strong-name signed (public key token)", len(ps.stdout.strip()) >= 23, ps.stdout + ps.stderr)
    check("multi-targeting built net8.0 too", (C / "src" / "Contoso.Core" / "bin" / "Debug" / "net8.0").is_dir())
    target = C / "src" / "Contoso.App" / "bin" / "Debug" / "net9.0" / "Contoso.App.exe"
    r = launch.resolve(loaded["profiles"]["Staging args"], {"ProjectDir": str(app.parent)})
    p = subprocess.run([str(target), *r["args"]], cwd=r["cwd"], env={**os.environ, **r["env"]},
                       capture_output=True, text=True)
    check("run with the launch profile: args, env, working directory",
          "ARGS=--mode|two words|3" in p.stdout and "ENV=staging" in p.stdout and f"CWD={C}" in p.stdout, p.stdout)
    prof = publish.profiles_dir(app.parent) / "FolderProfile.pubxml"
    publish.write(prof, publish.profile_values(False, "win-x64", True, False, False, "net9.0", "Release",
                                               "bin\\publish\\win-x64\\"))
    vals = publish.read(prof)
    check(".pubxml written/read", vals["RuntimeIdentifier"] == "win-x64" and vals["PublishSingleFile"] == "true")
    code, out = run(publish.publish_argv(DN, app, prof), app.parent, 1800)
    exe = app.parent / "bin" / "publish" / "win-x64" / "Contoso.App.exe"
    check("dotnet publish with the profile -> single-file exe", code == 0 and exe.is_file(), out[-2000:])
    if exe.is_file():
        p = subprocess.run([str(exe), "x"], capture_output=True, text=True)
        check("published exe runs", "GREETING=Hello, Visual Studio!" in p.stdout, p.stdout + p.stderr)

# cleanup of what lives outside the temp folder
shutil.rmtree(secrets.secrets_file(sid).parent, ignore_errors=True)
ok = sum(1 for _n, c in RESULTS if c)
print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
shutil.rmtree(work, ignore_errors=True)
sys.exit(0 if ok == len(RESULTS) else 1)
