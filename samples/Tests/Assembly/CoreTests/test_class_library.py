"""The "Assembly Class Library (x64 DLL, NASM)" template: build the DLL and call it from Python (ctypes, the
Ctrl+F5 client), C (gcc + the generated import library) and C# (P/Invoke, a throw-away .NET console project).

    python samples/Tests/Assembly/CoreTests/test_class_library.py

The C# step needs the .NET SDK (dotnet on PATH); it is reported as skipped without it.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from radide.asm import toolchain as tc                   # noqa: E402
from radide.asm.build import Builder, read_diagnostics    # noqa: E402
from radide.languages import get_plugin                   # noqa: E402
from radide.model import Project                          # noqa: E402

WORK = Path(tempfile.gettempdir()) / "radide-asm-tests" / "classlib"
NAME = "MathAsm"
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)


shutil.rmtree(WORK, ignore_errors=True)
folder = WORK / NAME
plugin = get_plugin("asm-nasm")
plugin.create_new_project(folder, NAME, "nasm_dll_x64")
project = Project.load(folder)
check("template files", all((folder / f).is_file() for f in (f"{NAME}.asm", f"{NAME}.h", "UseFromPython.py",
                                                            "UseFromC.c", "UseFromCSharp.cs")),
      ", ".join(sorted(p.name for p in folder.iterdir())))
check("only the .asm is a module", project.modules == [f"{NAME}.asm"], str(project.modules))
logs = []
ok = Builder(folder, log=logs.append).build()
check("build -> MathAsm.dll + libMathAsm.a", ok and (folder / f"{NAME}.dll").is_file() and
      (folder / f"lib{NAME}.a").is_file(), "" if ok else "\n".join(logs[-10:]) + str(read_diagnostics(folder)))
diag = read_diagnostics(folder)
check("diagnostics.json names the DLL", diag.get("exe", "").endswith(f"{NAME}.dll"), diag.get("exe", ""))

objdump = tc.mingw("objdump")
exports = subprocess.run([objdump, "-p", str(folder / f"{NAME}.dll")], capture_output=True, text=True).stdout
names = ["asm_add", "asm_factorial", "asm_sum_array", "asm_strlen", "asm_upper", "asm_version"]
check("export table", all(n in exports for n in names), ", ".join(n for n in names if n in exports))

# Python (ctypes) - the Ctrl+F5 command of a class library
argv = plugin.run_command(folder, project)
r = subprocess.run(argv, capture_output=True, text=True, cwd=folder, timeout=60)
check("Python ctypes client (Ctrl+F5 command)", r.returncode == 0 and "all calls OK" in r.stdout,
      r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:])

# C: gcc + import library
gcc = tc.mingw("gcc")
r = subprocess.run([gcc, "UseFromC.c", "-L.", f"-l{NAME}", "-o", "UseFromC.exe"], cwd=folder, capture_output=True,
                   text=True)
ok = r.returncode == 0
if ok:
    r = subprocess.run([str(folder / "UseFromC.exe")], cwd=folder, capture_output=True, text=True, timeout=30)
    ok = r.returncode == 0 and "asm_add      : 40 + 2 = 42" in r.stdout and "HELLO FROM C" in r.stdout
check("C client (gcc -l MathAsm)", ok, (r.stdout + r.stderr).strip().replace("\n", " | ")[:300])

# C#: P/Invoke from a .NET console project
dotnet = shutil.which("dotnet")
if not dotnet:
    print("SKIP C# client: the .NET SDK (dotnet) was not found")
else:
    cs = WORK / "UseFromCSharp"
    cs.mkdir(parents=True, exist_ok=True)
    (cs / "UseFromCSharp.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup>\n    <OutputType>Exe</OutputType>\n'
        '    <TargetFramework>net9.0</TargetFramework>\n    <PlatformTarget>x64</PlatformTarget>\n'
        '    <Nullable>disable</Nullable>\n  </PropertyGroup>\n  <ItemGroup>\n'
        f'    <None Include="{NAME}.dll" CopyToOutputDirectory="PreserveNewest" />\n  </ItemGroup>\n</Project>\n',
        encoding="utf-8")
    shutil.copy2(folder / "UseFromCSharp.cs", cs / "UseFromCSharp.cs")
    shutil.copy2(folder / f"{NAME}.dll", cs / f"{NAME}.dll")
    env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1")
    r = subprocess.run([dotnet, "run", "--project", str(cs)], cwd=cs, capture_output=True, text=True, timeout=600,
                       env=env)
    check("C# client (DllImport)", r.returncode == 0 and "asm_factorial: 10! = 3628800" in r.stdout,
          (r.stdout + r.stderr).strip().replace("\n", " | ")[-300:])

passed = sum(1 for _n, ok in results if ok)
print(f"\n{passed} / {len(results)} checks passed")
print("RESULT", "OK" if passed == len(results) else "FAIL")
sys.exit(0 if passed == len(results) else 1)
