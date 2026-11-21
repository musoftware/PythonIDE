"""References slice - back-end test (no window): project-file edits + real builds.

Copies samples/Tests/DotNet/References to a temp folder (the sample is never edited), then:
  1. builds MathKit (net9.0 + netstandard2.0) and reads its metadata (types, members, XML docs)
  2. SDK project: Browse reference to MathKit.dll (HintPath), FrameworkReference, properties round trip,
     dotnet build + run -> "2 + 3 = 5"
  3. .NET Framework 4.8 project: Framework assembly (System.Numerics), Browse (netstandard2.0 MathKit),
     COM (Microsoft Scripting Runtime, tlbimp + EmbedInteropTypes), Add As Link (..\\Common\\SharedHelper.cs)
     -> Visual Studio's MSBuild build + run
  4. native DLL detection, Shared Project import, catalog listings
Run:  python samples/Tests/DotNet/References/tests/test_refs_core.py
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLE = HERE.parent
ROOT = SAMPLE.parents[3]
sys.path.insert(0, str(ROOT))

from radide.dotnet.refs import catalog as CAT, edits as ED, metadata as MD  # noqa: E402
from radide.dotnet.refs.props import apply_value, reference_rows  # noqa: E402
from radide.foreign import msbuild as MB  # noqa: E402
from radide.foreign.vs_solution import load_vs  # noqa: E402

RESULTS = []
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[-1500:]}]"), flush=True)
    return bool(cond)


def run(argv, cwd=None, timeout=600):
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, creationflags=NO_WINDOW)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def add_define(ms, symbol):
    cur = ms.prop("DefineConstants")
    if ms.is_sdk:
        ms.set_property("DefineConstants", f"$(DefineConstants);{symbol}")
        return
    text = ms.file.text
    ms.file.text = text.replace("<DefineConstants>DEBUG;TRACE</DefineConstants>",
                                f"<DefineConstants>DEBUG;TRACE;{symbol}</DefineConstants>", 1)
    if ms.file.text == text and cur:
        ms.file.text = text.replace(f"<DefineConstants>{cur}</DefineConstants>",
                                    f"<DefineConstants>{cur};{symbol}</DefineConstants>", 1)
    ms.parse()


def main():
    work = Path(tempfile.mkdtemp(prefix="radide-refs-"))
    sol = work / "References"
    shutil.copytree(SAMPLE, sol, ignore=shutil.ignore_patterns("bin", "obj", "tests"))
    dotnet = MB.find_dotnet()
    msbuild = MB.find_msbuild()
    print("work:", sol, "| dotnet:", dotnet, "| msbuild:", msbuild, flush=True)

    # ------------------------------------------------------------------ 1. MathKit + metadata
    rc, out = run([dotnet, "build", "-c", "Debug", "-nologo", "-v", "q"], cwd=sol / "MathKit")
    check("MathKit builds (dotnet build)", rc == 0, out)
    dll9 = sol / "MathKit" / "bin" / "Debug" / "net9.0" / "MathKit.dll"
    dll_std = sol / "MathKit" / "bin" / "Debug" / "netstandard2.0" / "MathKit.dll"
    check("MathKit.dll (net9.0 + netstandard2.0) exists", dll9.is_file() and dll_std.is_file())
    a = MD.read_assembly(dll9)
    ns = a.namespaces()
    names = [t.display for t in ns.get("MathKit", [])]
    check("metadata: MathKit namespace lists Calculator/Operation/Vector2", {"Calculator", "Operation", "Vector2"}
          <= set(names), names)
    calc = a.find_type("MathKit.Calculator")
    sigs = [m.signature for m in calc.members()]
    check("metadata: Calculator members with C# signatures",
          "public int Add(int a, int b)" in sigs and "public static int Gcd(int a, int b)" in sigs
          and any("List<int> History { get; }" in s for s in sigs) and any("event EventHandler Calculated" in s
                                                                           for s in sigs), sigs)
    doc = MD.doc_for(dll9, next(m.doc_id for m in calc.members() if m.name == "Add"))
    check("metadata: XML doc summary + params", doc.get("summary") == "Adds two integers." and
          doc.get("params", {}).get("a") == "The first number.", doc)
    v2 = a.find_type("MathKit.Vector2")
    check("metadata: struct + operator", v2.kind == "Struct" and any(m.kind == "Operator" for m in v2.members()),
          [m.signature for m in v2.members()])
    stub = MD.metadata_as_source(calc)
    check("metadata as source stub", "public class Calculator" in stub and "public int Add(int a, int b);" in stub
          and "/// Adds two integers." in stub, stub[:800])
    check("is_managed / pe_kind", MD.is_managed(dll9) and MD.pe_kind(r"C:\Windows\System32\kernel32.dll") == "native")

    # ------------------------------------------------------------------ 2. SDK project
    sln = load_vs(sol / "References.sln")
    sdk = next(p for p in sln.all_projects() if p.name == "SdkConsumer")
    changed, inc = ED.add_browse_reference(sdk.ms, dll9)
    add_define(sdk.ms, "MATHKIT")
    sdk.ms.save()
    sdk.reload()
    ref = next((r for r in sdk.ms.explicit("Reference") if r.include == "MathKit"), None)
    check("SDK: Browse adds <Reference Include=MathKit> with relative HintPath", changed and ref is not None and
          ref.metadata.get("HintPath") == r"..\MathKit\bin\Debug\net9.0\MathKit.dll", sdk.ms.text)
    again, _ = ED.add_browse_reference(sdk.ms, dll9)
    check("SDK: adding the same DLL twice is a no-op", not again)
    rc, out = run([dotnet, "build", "-nologo", "-v", "q"], cwd=sol / "SdkConsumer")
    check("SDK: consumer builds against the browsed DLL", rc == 0, out)
    rc, out = run([dotnet, "run", "--no-build"], cwd=sol / "SdkConsumer")
    check("SDK: consumer calls MathKit (2 + 3 = 5)", "2 + 3 = 5; gcd(12, 18) = 6" in out, out)

    # properties round trip
    rows = {r[0]: r for r in reference_rows(sdk, "assembly", "MathKit")}
    check("props: Path / Version / Copy Local default", rows["Path"][1].lower() == str(dll9).lower() and
          rows["Version"][1] == "1.0.0.0" and rows["Copy Local"][1] == "True", rows)
    apply_value(sdk, "assembly", "MathKit", "Private", "False")
    inc_now = apply_value(sdk, "assembly", "MathKit", "SpecificVersion", "True")
    check("props: Specific Version=True -> full identity Include (like VS)",
          inc_now == "MathKit, Version=1.0.0.0, Culture=neutral, processorArchitecture=MSIL", inc_now)
    apply_value(sdk, "assembly", inc_now, "Aliases", "mk, global")
    apply_value(sdk, "assembly", inc_now, "EmbedInteropTypes", "False")
    sdk.ms.save()
    sdk.reload()

    def mk_md():
        return next(r for r in sdk.ms.explicit("Reference") if r.include.startswith("MathKit")).metadata
    md = mk_md()
    check("props: written back (Private/SpecificVersion/Aliases/EmbedInteropTypes)",
          md.get("Private") == "False" and md.get("SpecificVersion") == "True" and md.get("Aliases") == "mk,global"
          and md.get("EmbedInteropTypes") == "False", sdk.ms.text)
    rows = {r[0]: r for r in reference_rows(sdk, "assembly", inc_now)}
    check("props: read back", rows["Copy Local"][1] == "False" and rows["Specific Version"][1] == "True" and
          rows["Aliases"][1] == "mk,global" and rows["Version"][1] == "1.0.0.0", rows)
    apply_value(sdk, "assembly", inc_now, "Aliases", "global")
    ED.set_metadata(sdk.ms, "Reference", inc_now, "EmbedInteropTypes", None)
    sdk.ms.save()
    sdk.reload()
    md = mk_md()
    check("props: Aliases=global and cleared values are removed", "Aliases" not in md and
          "EmbedInteropTypes" not in md and md.get("HintPath"), sdk.ms.text)
    rc, out = run([dotnet, "build", "-nologo", "-v", "q"], cwd=sol / "SdkConsumer")
    check("SDK: still builds with Copy Local=False / Specific Version", rc == 0, out)

    # FrameworkReference
    check("SDK: FrameworkReference added", ED.add_framework_reference(sdk.ms, "Microsoft.AspNetCore.App"))
    sdk.ms.save()
    rc, out = run([dotnet, "build", "-nologo", "-v", "q"], cwd=sol / "SdkConsumer")
    check("SDK: builds with <FrameworkReference Include=Microsoft.AspNetCore.App>", rc == 0, out)
    check("catalog: implicit + explicit frameworks", CAT.implicit_frameworks(sdk.ms) ==
          ["Microsoft.NETCore.App", "Microsoft.AspNetCore.App"], CAT.implicit_frameworks(sdk.ms))
    check("catalog: framework path resolves to the ASP.NET Core ref pack",
          "Microsoft.AspNetCore.App.Ref" in CAT.resolve_reference_path(sdk, "FrameworkReference",
                                                                        "Microsoft.AspNetCore.App"))
    ED.remove_framework_reference(sdk.ms, "Microsoft.AspNetCore.App")
    sdk.ms.save()
    check("SDK: FrameworkReference removed", "FrameworkReference" not in sdk.ms.text)

    # native DLL
    info = ED.browse_reference_check(r"C:\Windows\System32\kernel32.dll")
    check("Browse: native DLL detected (not referenced)", info["managed"] is False and info["kind"] == "native")
    try:
        ED.browse_reference_check(sol / "SdkConsumer" / "Program.cs")
        check("Browse: a non-PE file is refused", False)
    except ED.BrowseError as e:
        check("Browse: a non-PE file is refused", "valid assembly or COM component" in str(e), e)
    native = work / "native" / "mynative.dll"
    native.parent.mkdir()
    shutil.copy2(r"C:\Windows\System32\version.dll", native)
    check("Browse: native DLL copy to output (None + Link + PreserveNewest)", ED.add_native_copy(sdk.ms, native) and
          "<CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory>" in sdk.ms.text and
          "<Link>mynative.dll</Link>" in sdk.ms.text, sdk.ms.text)
    sdk.ms.save()
    rc, out = run([dotnet, "build", "-nologo", "-v", "q"], cwd=sol / "SdkConsumer")
    check("SDK: native DLL copied next to the program",
          rc == 0 and (sol / "SdkConsumer" / "bin" / "Debug" / "net9.0" / "mynative.dll").is_file(), out)

    # ------------------------------------------------------------------ 3. .NET Framework project
    leg = next(p for p in sln.all_projects() if p.name == "LegacyConsumer")
    fx = CAT.framework_assemblies(CAT.project_netfx_version(leg.ms))
    check("catalog: .NET Framework 4.8 assemblies (FrameworkList.xml)", len(fx) > 100 and
          any(e.name == "System.Numerics" for e in fx), len(fx))
    check("legacy: framework assembly added", ED.add_framework_assembly(leg.ms, "System.Numerics") and
          '<Reference Include="System.Numerics" />' in leg.ms.text, leg.ms.text)
    check("legacy: framework assembly not added twice", not ED.add_framework_assembly(leg.ms, "System.Numerics"))
    add_define(leg.ms, "NUMERICS")
    changed, inc = ED.add_browse_reference(leg.ms, dll_std)
    check("legacy: Browse -> HintPath to netstandard2.0 MathKit", changed and
          r"..\MathKit\bin\Debug\netstandard2.0\MathKit.dll" in leg.ms.text, leg.ms.text)
    add_define(leg.ms, "MATHKIT")
    linked = ED.add_as_link(leg.ms, sol / "Common" / "SharedHelper.cs", "Shared")
    check("legacy: Add As Link (Compile Include=..\\Common\\SharedHelper.cs + Link)", linked and
          r'<Compile Include="..\Common\SharedHelper.cs">' in leg.ms.text and
          r"<Link>Shared\SharedHelper.cs</Link>" in leg.ms.text, leg.ms.text)
    add_define(leg.ms, "LINKED")
    libs = CAT.com_type_libraries()
    scr = next((e for e in libs if e.guid == "420b2830-e718-11cf-893d-00a0c9054228"), None)
    check("catalog: COM type libraries listed (Microsoft Scripting Runtime)", scr is not None and len(libs) > 20,
          len(libs))
    if scr is not None:
        changed, inc = ED.add_com_reference(leg.ms, scr)
        check("legacy: COMReference Scripting (Guid/Version/Lcid/tlbimp/EmbedInteropTypes)", changed and
              inc == "Scripting" and "<Guid>420b2830-e718-11cf-893d-00a0c9054228</Guid>" in leg.ms.text and
              "<WrapperTool>tlbimp</WrapperTool>" in leg.ms.text and
              "<EmbedInteropTypes>true</EmbedInteropTypes>" in leg.ms.text, leg.ms.text)
        add_define(leg.ms, "SCRIPTING")
        rows = {r[0]: r for r in reference_rows(leg, "com", "Scripting")}
        check("props: COM reference rows", rows["Guid"][1] == "{420b2830-e718-11cf-893d-00a0c9054228}" and
              rows["Path"][1].lower().endswith("scrrun.dll") and rows["Embed Interop Types"][1] == "True", rows)
    leg.ms.save()
    leg.reload()
    check("legacy: linked file is an item of the project", any(f.metadata.get("Link") for f in leg.items))
    if msbuild and MB.msbuild_is_full(msbuild):
        rc, out = run([msbuild, str(leg.ms.path), "/nologo", "/v:m", "/p:Configuration=Debug"], timeout=900)
        check("legacy: Visual Studio MSBuild builds (framework + browse + COM + link)", rc == 0, out)
        exe = leg.folder / "bin" / "Debug" / "LegacyConsumer.exe"
        rc, out = run([str(exe)])
        check("legacy: program output uses every reference",
              "BigInteger: 1267650600228229401496703205376" in out and "MathKit: 42" in out and
              "Scripting: temp folder exists = True" in out and "Hello, linked file!" in out, out)
    else:
        print("SKIP legacy build: Visual Studio MSBuild not found")

    # SDK project + COM with VS MSBuild
    if scr is not None and msbuild and MB.msbuild_is_full(msbuild):
        sdk.ms.reload()
        ED.add_com_reference(sdk.ms, scr)
        sdk.ms.set_property("DefineConstants", "$(DefineConstants);MATHKIT")
        sdk.ms.save()
        rc, out = run([msbuild, str(sdk.ms.path), "/restore", "/nologo", "/v:m"], timeout=900)
        check("SDK + COM: builds with Visual Studio MSBuild", rc == 0, out)

    # ------------------------------------------------------------------ 4. Shared project import (fallback writer)
    shdir = sol / "SharedBits"
    shdir.mkdir()
    (shdir / "SharedBits.projitems").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">'
        "\n  <PropertyGroup>\n    <HasSharedItems>true</HasSharedItems>\n  </PropertyGroup>\n  <ItemGroup>\n"
        '    <Compile Include="$(MSBuildThisFileDirectory)Bits.cs" />\n  </ItemGroup>\n</Project>\n', encoding="utf-8")
    (shdir / "Bits.cs").write_text("namespace SharedBits { public static class Bits { public static int Two => 2; } }\n",
                                   encoding="utf-8")
    sdk.ms.reload()
    check("shared: <Import Label=Shared> added (SDK: before </Project>)",
          ED.add_shared_import(sdk.ms, shdir / "SharedBits.projitems") and
          r'<Import Project="..\SharedBits\SharedBits.projitems" Label="Shared" />' in sdk.ms.text, sdk.ms.text)
    check("shared: listed", ED.shared_imports(sdk.ms) == [r"..\SharedBits\SharedBits.projitems"])
    check("shared: not added twice", not ED.add_shared_import(sdk.ms, shdir / "SharedBits.projitems"))
    leg.ms.reload()
    ED.add_shared_import(leg.ms, shdir / "SharedBits.projitems")
    t = leg.ms.text
    check("shared: legacy import placed before Microsoft.CSharp.targets",
          t.index("SharedBits.projitems") < t.index("Microsoft.CSharp.targets"), t)
    check("shared: removed", ED.remove_shared_import(leg.ms, r"..\SharedBits\SharedBits.projitems") and
          "SharedBits" not in leg.ms.text)

    # remove assembly + COM
    sdk.ms.reload()
    check("remove: browse reference", ED.remove_assembly(sdk.ms, "MathKit") and "MathKit.dll" not in sdk.ms.text)
    check("remove: COM reference", ED.remove_com_reference(sdk.ms, "Scripting") and "COMReference" not in sdk.ms.text)

    ok = sum(1 for _, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}", flush=True)
    shutil.rmtree(work, ignore_errors=True)
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
