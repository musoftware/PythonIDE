"""NuGet backend checks (no UI): versions/frameworks, nuget.config, search (live or recorded fixture),
install / update / uninstall on temp copies of an SDK project, a packages.config project and a Central
Package Management solution, then builds. Run:  python samples/Tests/DotNet/NuGetTests/test_nuget_backend.py
(--offline replays the recorded fixtures for the search part)."""
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
FIX = HERE / "fixtures"

from radide.dotnet.nuget import config as C, feed as F, http as H, projects as P, versions as V  # noqa: E402
from radide.foreign import msbuild as MB  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)
    return bool(cond)


def online() -> bool:
    if "--offline" in sys.argv:
        return False
    try:
        H.fetch("https://api.nuget.org/v3/index.json", timeout=10)
        return True
    except Exception:  # noqa: BLE001
        return False


WORK = Path(tempfile.mkdtemp(prefix="radide-nuget-"))
LOG = []


def log(s):
    LOG.append(s)


def copy(name) -> Path:
    dst = WORK / name
    shutil.copytree(HERE.parent / name, dst, ignore=shutil.ignore_patterns("bin", "obj", "packages", ".vs"))
    return dst


def build(target: Path, sdk=True) -> tuple[int, str]:
    argv = MB.build_argv(target, "Debug", "", sdk=sdk)
    return P.run(argv, target.parent, log, timeout=600)


# ---------------------------------------------------------------- versions / frameworks
NV = V.NuGetVersion.parse
check("version order: prerelease < release", NV("1.0.0-beta") < NV("1.0.0") < NV("1.0.1"))
check("version order: numeric labels", NV("1.0.0-beta.2") < NV("1.0.0-beta.10"))
check("4-part versions", NV("1.2.3.4") > NV("1.2.3") and str(NV("1.2.3.0")) == "1.2.3")
r = V.VersionRange.parse("[1.0,2.0)")
check("range [1.0,2.0)", r.satisfies("1.5") and not r.satisfies("2.0") and r.pretty() == ">= 1.0.0 && < 2.0.0")
check("range 4.5.4 picks lowest", V.VersionRange.parse("4.5.4").best_match(["4.5.2", "4.5.4", "4.6.0"]) == "4.5.4")
check("nearest net48", V.nearest("net48", ["net45", "netstandard2.0", "net6.0"]) == "net45")
check("nearest net8.0", V.nearest("net8.0", ["net45", "netstandard2.0", "net6.0"]) == "net6.0")
check("nearest .NETFramework4.6.2 group for net48",
      V.nearest("net48", [".NETFramework4.6.2", ".NETStandard2.0"]) == ".NETFramework4.6.2")
check("net40 cannot use netstandard2.0", V.nearest("net40", ["netstandard2.0"]) is None)

# ---------------------------------------------------------------- nuget.config
cfgdir = WORK / "cfg"
(cfgdir / "sub").mkdir(parents=True)
cf = C.ConfigFile.load(cfgdir / "nuget.config", create=True)
cf.add_source("local", str(cfgdir / "feed"))
cf.add_source("other", "https://example.invalid/v3/index.json", enabled=False)
cf.save()
srcs = C.effective_sources(cfgdir / "sub")
names = [s.name for s in srcs]
check("solution nuget.config sources merged", "local" in names and "nuget.org" in names, names)
check("disabled source read", any(s.name == "other" and not s.enabled for s in srcs))
cf = C.ConfigFile.load(cfgdir / "nuget.config")
cf.section("packageSources").insert(0, __import__("xml.etree.ElementTree", fromlist=["x"]).Element("clear"))
cf.save()
names = [s.name for s in C.effective_sources(cfgdir / "sub")]
check("<clear/> stops inheriting", names == ["local", "other"], names)

# ---------------------------------------------------------------- search
live = online()
if not live:
    os.environ["RADIDE_NUGET_FIXTURES"] = str(FIX)
    os.environ["RADIDE_NUGET_FIXTURE_MODE"] = "replay"
elif "--record" in sys.argv:
    os.environ["RADIDE_NUGET_FIXTURES"] = str(FIX)
    os.environ["RADIDE_NUGET_FIXTURE_MODE"] = "record"
F.clear_feed_cache()
org = F.nuget_org()
rows, total = org.search("Newtonsoft.Json", take=5)
check(f"search ({'live' if live else 'fixture'})", rows and rows[0].id == "Newtonsoft.Json" and total > 0,
      [r.id for r in rows])
check("search: verified badge + downloads", rows and rows[0].verified and rows[0].total_downloads > 10 ** 9)
meta = org.metadata("Newtonsoft.Json", "13.0.3")
check("metadata: license + groups", meta and meta.license_expression == "MIT" and meta.dependency_groups)
check("autocomplete", "Newtonsoft.Json" in org.autocomplete("Newtonso"))
check("versions list", "13.0.3" in org.versions("Newtonsoft.Json"))
gp = F.LocalFeed(C.global_packages_folder(), "Global packages folder")
rows, _ = gp.search("newtonsoft")
check("offline: global packages folder browse", any(r.id.lower() == "newtonsoft.json" for r in rows))
os.environ.pop("RADIDE_NUGET_FIXTURES", None)
os.environ.pop("RADIDE_NUGET_FIXTURE_MODE", None)
if live:
    dep = org.metadata("Microsoft.Azure.ServiceBus")
    check("deprecation info", dep is not None and "deprecated" in dep.deprecation_text())
    vul = org.metadata("System.Text.Encodings.Web", "4.5.0")
    check("vulnerability info", vul is not None and vul.vulnerabilities)

if not live:
    print("offline: project operations skipped")
else:
    # ------------------------------------------------------------ SDK / PackageReference
    sdk = copy("NuGetSdk")
    np = P.NuGetProject(sdk / "NuGetSdk.csproj")
    check("SDK style = PackageReference", np.style == P.STYLE_PR, np.style)
    np.install("Newtonsoft.Json", "13.0.1", log)
    check("SDK install", np.installed_version("Newtonsoft.Json") == "13.0.1", np.installed())
    np.update("Newtonsoft.Json", "13.0.3", log)
    check("SDK update", np.installed_version("Newtonsoft.Json") == "13.0.3")
    prog = sdk / "Program.cs"
    prog.write_text(prog.read_text().replace("// using", "using").replace("// Console", "Console"))
    code, out = build(sdk / "NuGetSdk.csproj")
    check("SDK build after install", code == 0, out[-800:])
    tr = np.installed(include_transitive=True)
    check("SDK installed list has no transitive for Newtonsoft", any(p.id == "Newtonsoft.Json" for p in tr))
    np.uninstall("Newtonsoft.Json", log)
    check("SDK uninstall", not np.installed() and "Newtonsoft" not in (sdk / "NuGetSdk.csproj").read_text())

    # ------------------------------------------------------------ packages.config
    leg = copy("NuGetLegacy")
    lp = P.NuGetProject(leg / "LegacyApp" / "LegacyApp.csproj")
    check("legacy default style = packages.config", lp.style == P.STYLE_PC, lp.style)
    lp.install("Newtonsoft.Json", "13.0.3", log)
    txt = (leg / "LegacyApp" / "LegacyApp.csproj").read_text(encoding="utf-8-sig")
    check("packages.config written", lp.installed_version("Newtonsoft.Json") == "13.0.3" and
          'targetFramework="net48"' in (leg / "LegacyApp" / "packages.config").read_text(encoding="utf-8-sig"))
    check("Reference + HintPath to lib/net45", r"..\packages\Newtonsoft.Json.13.0.3\lib\net45\Newtonsoft.Json.dll" in txt
          and "PublicKeyToken=30ad4fe6b2a6aeed" in txt, txt[-1500:])
    check("packages folder extracted", (leg / "packages" / "Newtonsoft.Json.13.0.3" / "lib" / "net45").is_dir())
    check("<None Include=packages.config>", '<None Include="packages.config" />' in txt)
    lp.install("Microsoft.Bcl.AsyncInterfaces", "8.0.0", log)
    ids = {p.id: p.version for p in lp.installed()}
    check("dependencies installed (lowest applicable)", ids.get("System.Threading.Tasks.Extensions") == "4.5.4"
          and "System.Runtime.CompilerServices.Unsafe" in ids, ids)
    try:
        lp.uninstall("System.Threading.Tasks.Extensions", log)
        check("uninstall refused when a package depends on it", False)
    except P.NuGetError as e:
        check("uninstall refused when a package depends on it", "depends on it" in str(e), e)
    lp.install("Microsoft.Build.Locator", "1.7.8", log)
    txt = (leg / "LegacyApp" / "LegacyApp.csproj").read_text(encoding="utf-8-sig")
    check("build/*.props imported + Ensure target", "Microsoft.Build.Locator.props" in txt and P.ENSURE_TARGET in txt)
    prog = leg / "LegacyApp" / "Program.cs"
    prog.write_text(prog.read_text().replace("// Console", "Console"))
    code, out = build(leg / "NuGetLegacy.sln", sdk=False)
    check("legacy build after install (MSBuild)", code == 0, out[-1200:])
    shutil.rmtree(leg / "packages" / "Newtonsoft.Json.13.0.3")
    check("restore packages.config", P.restore_packages_config(lp, log) and
          (leg / "packages" / "Newtonsoft.Json.13.0.3").is_dir())
    lp.update("Newtonsoft.Json", "13.0.1", log)
    txt = (leg / "LegacyApp" / "LegacyApp.csproj").read_text(encoding="utf-8-sig")
    check("packages.config update (downgrade) rewrites HintPath",
          "Newtonsoft.Json.13.0.1" in txt and "Newtonsoft.Json.13.0.3" not in txt)
    lp.uninstall("Microsoft.Build.Locator", log)
    txt = (leg / "LegacyApp" / "LegacyApp.csproj").read_text(encoding="utf-8-sig")
    check("uninstall removes imports + Ensure target", "Build.Locator" not in txt and P.ENSURE_TARGET not in txt,
          [ln for ln in txt.splitlines() if "Locator" in ln or "Ensure" in ln or "<Error " in ln])
    lp.uninstall("Microsoft.Bcl.AsyncInterfaces", log, remove_dependencies=True)
    ids = {p.id for p in lp.installed()}
    check("uninstall -RemoveDependencies", ids == {"Newtonsoft.Json"}, ids)
    lp.uninstall("Newtonsoft.Json", log)
    check("last uninstall removes packages.config", not (leg / "LegacyApp" / "packages.config").exists())

    # ------------------------------------------------------------ Central Package Management
    cpm = copy("NuGetCpm")
    lib = P.NuGetProject(cpm / "Lib" / "Lib.csproj", solution_folder=cpm)
    app = P.NuGetProject(cpm / "App" / "App.csproj", solution_folder=cpm)
    check("CPM detected", lib.style == P.STYLE_CPM and app.style == P.STYLE_CPM, (lib.style, app.style))
    check("CPM installed version from props", lib.installed()[0].version == "13.0.1" and lib.installed()[0].central)
    app.install("Humanizer.Core", "2.14.1", log)
    props = (cpm / "Directory.Packages.props").read_text(encoding="utf-8-sig")
    apptxt = (cpm / "App" / "App.csproj").read_text(encoding="utf-8-sig")
    check("CPM install: PackageVersion in props, no Version in project",
          'PackageVersion Include="Humanizer.Core" Version="2.14.1"' in props and
          '<PackageReference Include="Humanizer.Core" />' in apptxt, props + apptxt)
    lib.update("Newtonsoft.Json", "13.0.3", log)
    props = (cpm / "Directory.Packages.props").read_text(encoding="utf-8-sig")
    check("CPM update changes the central version", 'Include="Newtonsoft.Json" Version="13.0.3"' in props, props)
    code, out = build(cpm / "NuGetCpm.sln")
    check("CPM solution build", code == 0, out[-800:])

    # ------------------------------------------------------------ solution level
    sol = copy("NuGetSolution")
    projs = [P.NuGetProject(sol / "ConsoleApp" / "ConsoleApp.csproj", solution_folder=sol),
             P.NuGetProject(sol / "LibA" / "LibA.csproj", solution_folder=sol)]
    cons = P.consolidation(projs)
    check("consolidate finds Newtonsoft.Json 13.0.1 vs 13.0.3", "Newtonsoft.Json" in cons, cons)
    ups = P.updates(projs, org)
    check("updates found", "Newtonsoft.Json" in ups and "Humanizer.Core" in ups, list(ups))
    check("restore solution", P.restore_all(projs, sol / "NuGetSolution.sln", log))

ok = sum(1 for _, c in RESULTS if c)
print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
if "--keep" not in sys.argv:
    shutil.rmtree(WORK, ignore_errors=True)
else:
    print("work folder:", WORK)
sys.exit(0 if ok == len(RESULTS) else 1)
