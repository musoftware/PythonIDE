"""Back-end test of Shared Projects + the New Project templates (no Qt).

Creates, in a temp folder (or argv[1]), the solution that ./SharedDemo holds a copy of:

* SharedDemo.sln
  - SharedCode (C# Shared Project) -> used by WinApp (.NET 8 WinForms, dotnet new), FxConsole (.NET Framework 4.8
    old-style console, written by RAD IDE) and SdkFxConsole (SDK-style net48 console)
  - SharedVB (VB Shared Project)   -> used by VbApp (.NET 8 VB console, dotnet new) and VbFxConsole (.NET Framework
    4.8 old-style VB console)
  - MultiLib (net8.0;netstandard2.0 class library) <- ProjectReference from WinApp (multi-targeted reference sanity)

then builds the solution (Visual Studio's MSBuild when present - needed for the old-style projects -, else dotnet
build of the SDK projects), runs the console programs and checks that each prints the text of the #if branch that
the editor's project context leaves un-greyed (old-style net48 = no NETFRAMEWORK symbol; SDK-style net48 = has it).

    python samples/Tests/DotNet/SharedProjects/make_and_build.py [out-folder] [--copy-to-sample]
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from radide.dotnet.shared import context as CX        # noqa: E402
from radide.dotnet.shared import model as SH          # noqa: E402
from radide.dotnet.shared import preprocessor as PP   # noqa: E402
from radide.dotnet.templates import catalog as C      # noqa: E402
from radide.dotnet.templates import create as K       # noqa: E402
from radide.foreign import msbuild as MB              # noqa: E402
from radide.foreign.vs_solution import load_solution_model  # noqa: E402

RESULTS: list[tuple[str, bool]] = []
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:1500]}]"), flush=True)
    return bool(cond)


GREETER_CS = """namespace SharedCode
{
    public static class Greeter
    {
        public static string Hello()
        {
#if NET8_0_OR_GREATER
            return "Hello from .NET 8+ (shared C#)";
#elif NETFRAMEWORK
            return "Hello from SDK-style .NET Framework (shared C#)";
#else
            return "Hello from .NET Framework 4.8 old-style (shared C#)";
#endif
        }

#if DEBUG
        public static string Configuration => "Debug";
#else
        public static string Configuration => "Release";
#endif
    }
}
"""

GREETER_VB = """Public Module SharedGreeter
    Public Function Hello() As String
#If NET8_0_OR_GREATER Then
        Return "Hello from .NET 8+ (shared VB)"
#Else
        Return "Hello from .NET Framework 4.8 (shared VB)"
#End If
    End Function
End Module
"""

MULTI_CS = """namespace MultiLib
{
    public static class Info
    {
#if NETSTANDARD2_0
        public const string Target = "netstandard2.0";
#else
        public const string Target = "net8.0";
#endif
    }
}
"""

SDKFX_PROJ = """<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net48</TargetFramework>
  </PropertyGroup>

</Project>
"""

SDKFX_PROGRAM = """using System;

namespace SdkFxConsole
{
    internal static class Program
    {
        private static void Main()
        {
            Console.WriteLine(SharedCode.Greeter.Hello());
        }
    }
}
"""


def run(argv, cwd=None, timeout=900):
    r = subprocess.run([str(a) for a in argv], cwd=str(cwd) if cwd else None, capture_output=True, timeout=timeout,
                       creationflags=NO_WINDOW, env={**os.environ, "DOTNET_NOLOGO": "1", "DOTNET_CLI_TELEMETRY_OPTOUT": "1"})
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", errors="replace")


def new(ts, key, lang, name, loc, **kw):
    t = C.find(ts, key, lang)
    if not check(f"template {key} ({lang}) is listed", t is not None):
        raise SystemExit(1)
    try:
        r = K.create(K.NewProjectRequest(t, name, loc, **kw))
    except ValueError as e:
        check(f"create {name} from {key}", False, e)
        raise SystemExit(1)
    check(f"create {name} from {key}", r.project_file is not None and r.project_file.is_file(), r.log)
    return r


def write_bom(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8-sig")


def make(loc: Path) -> dict:
    ts = C.all_templates()
    out = {}
    r = new(ts, "winforms", "C#", "WinApp", loc, solution_name="SharedDemo", framework="net8.0")
    sln = r.solution_file
    out["sln"], out["WinApp"] = sln, r.project_file
    check("new solution: <location>/SharedDemo/SharedDemo.sln", sln == loc / "SharedDemo" / "SharedDemo.sln", sln)
    check("new solution written like VS (only Any CPU)", "Debug|x64" not in sln.read_text(encoding="utf-8-sig"))
    sdir = sln.parent
    for key, lang, name in (("rad:fxconsole-cs", "C#", "FxConsole"), ("rad:fxconsole-vb", "VB", "VbFxConsole"),
                            ("rad:shared-cs", "C#", "SharedCode"), ("rad:shared-vb", "VB", "SharedVB")):
        out[name] = new(ts, key, lang, name, sdir, solution=sln, framework="v4.8").project_file
    out["VbApp"] = new(ts, "console", "VB", "VbApp", sdir, solution=sln, framework="net8.0").project_file
    out["MultiLib"] = new(ts, "classlib", "C#", "MultiLib", sdir, solution=sln, framework="net8.0").project_file
    try:
        K.create(K.NewProjectRequest(C.find(ts, "console", "C#"), "VbApp", sdir, solution=sln))
        check("existing project name refused", False)
    except ValueError as e:
        check("existing project name refused (VS's message)", "already exists" in str(e), e)
    for bad in ("", "a/b", "con", "x."):
        check(f"invalid project name {bad!r} refused", K.validate_name(bad) != "")
    # SDK-style net48 (hand-written: dotnet new has no net48 console)
    sdk = sdir / "SdkFxConsole" / "SdkFxConsole.csproj"
    sdk.parent.mkdir()
    sdk.write_text(SDKFX_PROJ, encoding="utf-8")
    (sdk.parent / "Program.cs").write_text(SDKFX_PROGRAM, encoding="utf-8")
    K.add_to_solution(sln, sdk)
    out["SdkFxConsole"] = sdk
    ml = MB.MSBuildProject.load(out["MultiLib"])
    ml.file.text = ml.file.text.replace("<TargetFramework>net8.0</TargetFramework>",
                                        "<TargetFrameworks>net8.0;netstandard2.0</TargetFrameworks>\n"
                                        "    <LangVersion>latest</LangVersion>")   # <Nullable> needs C# 8+
    ml.save()
    for f in out["MultiLib"].parent.glob("Class1.cs"):
        f.unlink()
    (out["MultiLib"].parent / "Info.cs").write_text(MULTI_CS, encoding="utf-8")
    win = MB.MSBuildProject.load(out["WinApp"])
    check("ProjectReference WinApp -> MultiLib (multi-targeted)", win.add_project_reference(out["MultiLib"]))
    win.save()
    text = sln.read_text(encoding="utf-8-sig")
    check(".sln lists the shared projects without configuration lines",
          SH.SHPROJ_TYPE_GUID in text and SH.SharedProject(out["SharedCode"]).guid not in text.split("Global", 1)[1],
          text)

    cs = SH.SharedProject(out["SharedCode"])
    vb = SH.SharedProject(out["SharedVB"])
    check("C# shared project model", cs.language == "C#" and cs.guid and cs.shared_guid == cs.guid.strip("{}").lower())
    check("VB shared project model", vb.language == "VB")
    cs.add_new_item("Class", "", "Greeter")
    write_bom(cs.abs_path("Greeter.cs"), GREETER_CS)
    cs.new_folder("Util")
    cs.add_new_item("Class", "Util", "Helper")
    vb.add_new_item("Module", "", "SharedGreeter")
    write_bom(vb.abs_path("SharedGreeter.vb"), GREETER_VB)
    check("projitems items", cs.files() == ["Greeter.cs", "Util/Helper.cs"] and vb.files() == ["SharedGreeter.vb"],
          (cs.files(), vb.files()))
    pi = cs.projitems_path.read_text(encoding="utf-8-sig")
    check("projitems uses $(MSBuildThisFileDirectory)",
          '<Compile Include="$(MSBuildThisFileDirectory)Util\\Helper.cs" />' in pi, pi)
    check("Folder item dropped once the folder has a file", "<Folder" not in pi, pi)
    model = load_solution_model(sln)
    for proj, sp in (("WinApp", cs), ("FxConsole", cs), ("SdkFxConsole", cs), ("VbApp", vb), ("VbFxConsole", vb)):
        check(f"Add Shared Project Reference {sp.name} -> {proj}", SH.add_shared_reference(out[proj], sp))
        check(f"  {proj} imports it", SH.references_shared(out[proj], sp))
        SH.record_sln_shared_reference(model, out[proj], sp)
    text = sln.read_text(encoding="utf-8-sig")
    check(".sln GlobalSection(SharedMSBuildProjectFiles) like VS (13 = shared, 4 = old-style, 5 = SDK)",
          "SharedItemsImports = 13" in text and "SharedItemsImports = 4" in text and "SharedItemsImports = 5" in text,
          text)
    check("already referenced: no second Import", not SH.add_shared_reference(out["WinApp"], cs))
    try:
        SH.add_shared_reference(out["VbApp"], cs)
        check("C# shared project refused for a VB project", False)
    except ValueError:
        check("C# shared project refused for a VB project", True)
    fx = out["FxConsole"].read_text(encoding="utf-8-sig")
    check("old-style import placed before Microsoft.CSharp.targets",
          fx.index('Label="Shared"') < fx.index("Microsoft.CSharp.targets"))
    # programs that print the shared text
    p = out["FxConsole"].parent / "Program.cs"
    t = p.read_text(encoding="utf-8-sig")
    body = ("            Console.WriteLine(SharedCode.Greeter.Hello());\n"
            "            Console.WriteLine(SharedCode.Greeter.Configuration);\n")
    t = t.replace("        {\r\n        }", "        {\r\n" + body.replace("\n", "\r\n") + "        }") \
         .replace("        {\n        }", "        {\n" + body + "        }")
    write_bom(p, t)
    check("FxConsole Program.cs edited", "Greeter.Hello" in t, t)
    for name, fname in (("VbFxConsole", "Module1.vb"), ("VbApp", "Program.vb")):
        f = out[name].parent / fname
        t = f.read_text(encoding="utf-8-sig")
        t = t.replace('Console.WriteLine("Hello World!")', "Console.WriteLine(SharedGreeter.Hello())")
        if "SharedGreeter" not in t:
            t = t.replace("Sub Main()\r\n", "Sub Main()\r\n        Console.WriteLine(SharedGreeter.Hello())\r\n") \
                 .replace("Sub Main()\n", "Sub Main()\n        Console.WriteLine(SharedGreeter.Hello())\n")
        write_bom(f, t)
        check(f"{name} {fname} edited", "SharedGreeter.Hello" in t, t)
    f = out["WinApp"].parent / "Form1.cs"
    write_bom(f, f.read_text(encoding="utf-8-sig").replace(
        "InitializeComponent();", "InitializeComponent();\n            Text = SharedCode.Greeter.Hello() + \" | \" + "
        "MultiLib.Info.Target;"))
    return out


def greying(out: dict) -> None:
    cs = SH.SharedProject(out["SharedCode"])
    vb = SH.SharedProject(out["SharedVB"])
    text = cs.abs_path("Greeter.cs").read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    i_net8 = next(i for i, ln in enumerate(lines) if "NET 8+" in ln)
    i_sdkfx = next(i for i, ln in enumerate(lines) if "SDK-style" in ln)
    i_old = next(i for i, ln in enumerate(lines) if "old-style" in ln)
    i_dbg = next(i for i, ln in enumerate(lines) if '"Debug"' in ln)
    projects = [out[k] for k in ("WinApp", "FxConsole", "SdkFxConsole", "VbApp", "VbFxConsole", "MultiLib")]
    ctxs = CX.contexts_for_file(cs.abs_path("Greeter.cs"), projects, [out["SharedCode"], out["SharedVB"]])
    by = {c.name: c for c in ctxs}
    check("project contexts of a shared C# file = its 3 consumers", sorted(by) == ["FxConsole", "SdkFxConsole", "WinApp"],
          [c.label for c in ctxs])
    check("context labels show the target framework", by["WinApp"].label == "WinApp (net8.0-windows)"
          and by["FxConsole"].label == "FxConsole (net48)", [c.label for c in ctxs])
    own = CX.contexts_for_file(out["FxConsole"].parent / "Program.cs", projects)
    check("a single-target project's own file: one context, label without a framework",
          [c.label for c in own] == ["FxConsole"], [c.label for c in own])
    sw, sf, ss = by["WinApp"].symbols(), by["FxConsole"].symbols(), by["SdkFxConsole"].symbols()
    check("WinApp context symbols", {"DEBUG", "TRACE", "NET8_0", "NET8_0_OR_GREATER", "WINDOWS"} <= set(sw), sw)
    check("old-style FxConsole: DefineConstants only (no NETFRAMEWORK, like MSBuild)", set(sf) == {"DEBUG", "TRACE"}, sf)
    check("SDK-style net48: NETFRAMEWORK + NET48 defined", {"DEBUG", "TRACE", "NETFRAMEWORK", "NET48"} <= set(ss), ss)
    rw, rf, rs = (by[n].inactive_ranges(text) for n in ("WinApp", "FxConsole", "SdkFxConsole"))
    grey = lambda rr, i: any(a <= i <= b for a, b in rr)   # noqa: E731
    check("#if greying: WinApp keeps only the NET8 branch",
          not grey(rw, i_net8) and grey(rw, i_sdkfx) and grey(rw, i_old), rw)
    check("#if greying: SDK-style net48 keeps only the NETFRAMEWORK branch",
          grey(rs, i_net8) and not grey(rs, i_sdkfx) and grey(rs, i_old), rs)
    check("#if greying: old-style net48 keeps only the #else branch",
          grey(rf, i_net8) and grey(rf, i_sdkfx) and not grey(rf, i_old), rf)
    check("#if greying: Release configuration greys the DEBUG block",
          grey(by["WinApp"].inactive_ranges(text, "Release"), i_dbg))
    vt = vb.abs_path("SharedGreeter.vb").read_text(encoding="utf-8-sig")
    vlines = vt.splitlines()
    vctx = {c.name: c for c in CX.contexts_for_file(vb.abs_path("SharedGreeter.vb"), projects, [out["SharedVB"]])}
    check("project contexts of a shared VB file = its 2 consumers", sorted(vctx) == ["VbApp", "VbFxConsole"], vctx)
    j8 = next(i for i, ln in enumerate(vlines) if ".NET 8+" in ln)
    jf = next(i for i, ln in enumerate(vlines) if "Framework 4.8" in ln)
    ra, rb = vctx["VbApp"].inactive_ranges(vt), vctx["VbFxConsole"].inactive_ranges(vt)
    check("VB #If greying per context", grey(rb, j8) and not grey(rb, jf) and grey(ra, jf) and not grey(ra, j8),
          (ra, rb))
    it = (out["MultiLib"].parent / "Info.cs").read_text(encoding="utf-8")
    mctx = CX.contexts_for_file(out["MultiLib"].parent / "Info.cs", projects)
    check("multi-targeted project: one context per target framework",
          sorted(c.label for c in mctx) == ["MultiLib (net8.0)", "MultiLib (netstandard2.0)"], [c.label for c in mctx])
    a, b = (c.inactive_ranges(it) for c in mctx)
    check("multi-targeted project: each context greys the other branch", a and b and a != b, (a, b))
    # SDK quirk: a plain <DefineConstants> replaces the SDK's DEBUG;TRACE (MSBuild does the same)
    ms = MB.MSBuildProject.load(out["SdkFxConsole"])
    ms.file.text = ms.file.text.replace("</TargetFramework>", "</TargetFramework>\n    <DefineConstants>X</DefineConstants>")
    ms.parse()
    syms = PP.define_constants(ms, "Debug", "AnyCPU", "net48")
    check("SDK: <DefineConstants>X</DefineConstants> drops DEBUG/TRACE but keeps framework symbols",
          "X" in syms and "DEBUG" not in syms and "NET48" in syms, syms)


def build(out: dict) -> None:
    sln = out["sln"]
    msb = MB.find_msbuild()
    if msb and MB.msbuild_is_full(msb):
        code, log = run([msb, sln, "-restore", "-v:m", "-nologo", "-p:Configuration=Debug"], cwd=sln.parent)
        check("MSBuild SharedDemo.sln (Debug): 7 projects incl. 2 old-style .NET Framework 4.8", code == 0, log[-3000:])
    else:
        print("NOTE: Visual Studio MSBuild not found: building the SDK-style projects with dotnet build only")
        for n in ("WinApp", "VbApp", "SdkFxConsole"):
            code, log = run([MB.find_dotnet(), "build", out[n]], cwd=out[n].parent)
            check(f"dotnet build {n}", code == 0, log[-3000:])
    for name, want in (("FxConsole", "old-style (shared C#)"), ("VbFxConsole", "Framework 4.8 (shared VB)")):
        exe = out[name].parent / "bin" / "Debug" / f"{name}.exe"
        if exe.is_file():
            code, text = run([exe])
            check(f"{name} (old-style net48) prints the branch the editor leaves un-greyed", want in text, text)
    exe = out["SdkFxConsole"].parent / "bin" / "Debug" / "net48" / "SdkFxConsole.exe"
    code, text = run([exe]) if exe.is_file() else (1, f"{exe} missing")
    check("SdkFxConsole (SDK-style net48) prints the NETFRAMEWORK branch", "SDK-style .NET Framework" in text, text)
    code, text = run([MB.find_dotnet(), "run", "--no-build", "--project", out["VbApp"]], cwd=out["VbApp"].parent)
    check("VbApp (.NET 8) prints its own #If branch", ".NET 8+ (shared VB)" in text, text)
    dll = out["WinApp"].parent / "bin" / "Debug" / "net8.0-windows" / "MultiLib.dll"
    check("WinApp got the net8.0 build of the multi-targeted MultiLib", dll.is_file())
    check("MultiLib built both targets",
          (out["MultiLib"].parent / "bin" / "Debug" / "netstandard2.0" / "MultiLib.dll").is_file())


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    loc = Path(args[0]) if args else Path(tempfile.mkdtemp(prefix="radide-shared-"))
    if loc.exists() and any(loc.iterdir()):
        shutil.rmtree(loc)
    loc.mkdir(parents=True, exist_ok=True)
    out = make(loc)
    greying(out)
    build(out)
    if "--copy-to-sample" in sys.argv:
        dst = Path(__file__).resolve().parent / "SharedDemo"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(out["sln"].parent, dst, ignore=shutil.ignore_patterns("bin", "obj", ".vs"))
        print("copied to", dst)
    ok = sum(1 for _n, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}  ({loc})", flush=True)
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
