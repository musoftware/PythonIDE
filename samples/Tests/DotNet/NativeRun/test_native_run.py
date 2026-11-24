"""Native mode of RAD C# projects (radide/dotnet/native_project.py, native_run.py, runtime_lib.py), no Qt.

    .venv\\Scripts\\python samples\\Tests\\DotNet\\NativeRun\\test_native_run.py [scratch]

1. RadIDE.Runtime.dll builds (net8.0-windows) and is cached.
2. MsgBoxApp (a copy in scratch) is in native mode; the build makes bin/native/MsgBoxApp.exe, Form1.Designer.cs
   (read-only WinForms code) and a WinExe csproj that references the dll; MessageBox / Button / Color compile
   without usings.
3. F5 host: the exe runs (RAD_TEST_EXIT=1: the form prints NATIVE-OK and closes itself) - a real WinForms form
   (RadFormBase) - and its Console output reaches the host's stdout.
4. Debug handshake: RAD_BRIDGE_DEBUG=1 prints "@@RADBRIDGE@@pid|<pid>" and the form waits for "go".
5. NuGet packages in the csproj survive switching native -> bridge -> native; bridge mode removes the generated
   designers; a class library stays on the bridge.
Exit code = number of failed checks.
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))

from radide.dotnet import native_project as NP  # noqa: E402
from radide.dotnet import runtime_lib  # noqa: E402
from radide.languages import csharp_bridge as C  # noqa: E402

FAILS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if detail else ""), flush=True)
    if not ok:
        FAILS.append(name)


def host(folder: Path, env_extra: dict, stdin=None, timeout: int = 120) -> subprocess.Popen:
    env = dict(os.environ, PYTHONPATH=str(REPO), PYTHONUNBUFFERED="1", **env_extra)
    return subprocess.Popen([sys.executable, "-u", "-m", "radide.dotnet.native_run", str(folder)], env=env,
                            stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def main() -> int:
    if not C.dotnet():
        print("SKIP: the .NET SDK was not found")
        return 0
    scratch = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="radide_native_run_"))
    app = scratch / "MsgBoxApp"
    if app.exists():
        shutil.rmtree(app)
    shutil.copytree(HERE / "MsgBoxApp", app)

    dll = runtime_lib.build()
    check("runtime dll builds", dll is not None and dll.is_file(), str(dll))

    check("native mode by default", C.native_mode(app))
    buf = io.StringIO()
    rc = C.build(app, buf)
    check("native build", rc == 0 and C.program_file(app).is_file(), buf.getvalue()[-800:])
    check("exe in bin/native", C.program_file(app).name == "MsgBoxApp.exe", str(C.program_file(app)))
    designer = app / "Form1.Designer.cs"
    check("Form1.Designer.cs generated", designer.is_file() and NP.is_generated_designer(designer))
    check("designer has InitializeComponent", "InitializeComponent" in designer.read_text(encoding="utf-8-sig"))
    proj = (C.build_dir(app) / C.CSPROJ).read_text(encoding="utf-8")
    check("csproj is a WinExe with the runtime", "<OutputType>WinExe</OutputType>" in proj and
          "RadIDE.Runtime" in proj and "<UseWindowsForms>true</UseWindowsForms>" in proj)
    buf = io.StringIO()
    C.build(app, buf)
    check("second build is up to date", "up to date" in buf.getvalue(), buf.getvalue().strip())

    p = host(app, {"RAD_TEST_EXIT": "1"}, stdin=subprocess.DEVNULL)
    try:
        out, _ = p.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
    text = out.decode("utf-8", "replace")
    check("F5 runs the native exe", p.returncode == 0 and "NATIVE-OK" in text, text.strip()[-400:])
    check("the form is a WinForms form (RadFormBase)", "form=RadFormBase" in text, text.strip()[-200:])
    check("WinForms / Drawing types usable", "button=Button" in text and "color=Red" in text)

    p = host(app, {"RAD_BRIDGE_DEBUG": "1", "RAD_TEST_EXIT": "1"}, stdin=subprocess.PIPE)
    lines = []
    t0 = time.time()
    while time.time() - t0 < 60:
        ln = p.stdout.readline().decode("utf-8", "replace")
        if not ln:
            break
        lines.append(ln)
        if ln.startswith("@@RADBRIDGE@@pid|"):
            break
    check("debug: pid line", any(ln.startswith("@@RADBRIDGE@@pid|") for ln in lines), "".join(lines)[-300:])
    time.sleep(1.5)
    early = p.poll() is None
    p.stdin.write(b"go\n")
    p.stdin.flush()
    try:
        out, _ = p.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
    check("debug: the form waits for go", early and "NATIVE-OK" in out.decode("utf-8", "replace"))

    pkg = '<PackageReference Include="Humanizer.Core" Version="2.14.1" />'
    cs = C.build_dir(app) / C.CSPROJ
    cs.write_text(NP.with_packages(cs.read_text(encoding="utf-8"), [pkg]), encoding="utf-8")
    NP.set_mode(app, NP.BRIDGE)
    C.ensure_build_dir(app)
    text = cs.read_text(encoding="utf-8")
    check("bridge mode: console csproj, package kept", not NP.csproj_is_native(text) and pkg in text)
    check("bridge mode: generated designer removed", not designer.exists())
    NP.set_mode(app, NP.NATIVE)
    C.ensure_build_dir(app)
    text = cs.read_text(encoding="utf-8")
    check("native again: package kept", NP.csproj_is_native(text) and pkg in text)

    lib = scratch / "CsLib"
    lib.mkdir(exist_ok=True)
    (lib / "project.radproj").write_text('{"name": "CsLib", "language": "csharp-bridge", "forms": [], '
                                         '"modules": ["MathLib.cs"], "kind": "library"}', encoding="utf-8")
    (lib / "MathLib.cs").write_text("public static class MathLib { public static int Add(int a, int b) => a + b; }\n",
                                    encoding="utf-8")
    check("class library stays on the bridge", not C.native_mode(lib))

    print(f"\n{len(FAILS)} failed" + (": " + ", ".join(FAILS) if FAILS else ""))
    return len(FAILS)


if __name__ == "__main__":
    sys.exit(main())
