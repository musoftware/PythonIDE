"""A new Fortran GUI Bridge project from the template builds as a native exe even after F5 / the Error List ran.

    python samples/Tests/Native/test_native_fortran_template.py [scratch folder]

The E2E journey on the frozen IDE failed with "undefined reference to `rad_native_handlers_`": the Error List's
gfortran -fsyntax-only check wrote radgui.mod (the stdin/stdout radgui) into the project folder and the native build
ran gfortran from there, which picks .mod files of the working directory before -I / -J. Checks:
  1. the Error List check (tools.check_project) leaves no .mod next to the sources;
  2. a template project (radide.workspace.create_project, like New Project) with a stale radgui.mod in its folder
     (written the way older IDE versions did) publishes natively, the exe runs and shows Form1 (Load handler ran).
Exit code = number of failures."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))
os.environ.setdefault("RADIDE_NO_BROWSER", "1")

import winauto as w  # noqa: E402
from radide import tools, workspace  # noqa: E402
from radide.deploy import build  # noqa: E402
from radide.deploy.config import PublishConfig  # noqa: E402
from radide.languages import get_plugin  # noqa: E402

SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="radide_native_ftpl_"))
SCRATCH = SCRATCH / "fortran_template"
shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
results: list[tuple[str, bool, str]] = []


def ok(name: str, cond, detail: str = "") -> bool:
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{str(detail)[:600]}]" if detail and not cond else ""), flush=True)
    return bool(cond)


plugin = get_plugin("fortran-bridge")
gf = plugin.compiler() if hasattr(plugin, "compiler") else ""
if not gf:
    print("SKIP: gfortran not available")
    sys.exit(0)

folder = SCRATCH / "FortranTpl"
project = workspace.create_project(folder, "FortranTpl", "fortran-bridge")
ok("template project created", (folder / "Form1.f90").is_file() and project.startup == "Form1",
   sorted(p.name for p in folder.iterdir()))
code = (folder / "Form1.f90").read_text("utf-8")
code = code.replace("    ! runs when the form is shown\n",
                    "    ! runs when the form is shown\n    call rad_set('Form1', 'Caption', 'TPL-LOADED')\n")
(folder / "Form1.f90").write_text(code, "utf-8")
plugin.prepare(folder, project)                       # F5 copies radgui.f90 / radgui.c next to the sources

# 1. the Error List check keeps its .mod files out of the project folder
diags = tools.check_project(project, plugin, {"Form1.f90": code})
errs = [d for d in diags if d.severity == "Error"]
ok("Error List check: no errors", not errs, [d.message for d in errs])
ok("Error List check: no .mod next to the sources", not list(folder.glob("*.mod")),
   [p.name for p in folder.glob("*.mod")])

# 2. a stale radgui.mod in the project folder (older IDE versions) must not break the native build
env = dict(os.environ, PATH=str(Path(gf).parent) + os.pathsep + os.environ.get("PATH", ""))
subprocess.run([gf, "-fsyntax-only", "radgui.f90"], cwd=str(folder), env=env, capture_output=True)
ok("stale radgui.mod present (setup)", (folder / "radgui.mod").is_file())
out = SCRATCH / "publish"
cfg = PublishConfig(app_name="FortranTpl", version="1.0.0", publisher="RAD IDE tests", output_dir=str(out))
log: list[str] = []
res = None
try:
    res = build.build(folder, cfg, log=log.append)
except Exception as e:  # noqa: BLE001
    ok("native publish", False, f"{e}\n" + "\n".join(l for l in log if "undefined" in l or "rror" in l)[-600:])
if res is not None:
    exe = res.dist / res.exe
    ok("native publish (kind native, exe exists)", res.kind == "native" and exe.is_file(), res.kind)
    ok("no 'undefined reference' in the build output", not any("undefined reference" in l for l in log))
    if exe.is_file():
        p = w.start(exe)
        f = None
        try:
            f = w.form_window(p.pid, "Form1")
            ok("the exe shows Form1", f)
            if f:
                ok("Form1_Load ran (caption set by the handler)", w.wait(lambda: w.get_text(f) == "TPL-LOADED"),
                   w.get_text(f))
        finally:
            ok("the exe closes", w.stop(p, f))

shutil.rmtree(SCRATCH, ignore_errors=True)
fails = sum(1 for _n, c, _d in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
sys.exit(fails)
