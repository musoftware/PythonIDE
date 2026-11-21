"""Regression after the VS2022 .NET work (qh.py harness, QSettings "RADIDE-TEST"): the existing
samples/Tests/ForeignProjects .NET samples (temp copies) still open in place and build, RAD IDE's own C#
GUI-Bridge project (samples/HelloCSharp) still builds and runs, and a Python RAD project still runs.

    python samples/Tests/DotNet/EndToEnd/test_regression_ui.py
"""
import os
import shutil
import sys
import traceback
from pathlib import Path

os.environ.setdefault("QA_NAME", "dotnet-regression")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, finish, pump, shot, wait  # noqa: E402

ROOT = Path(qh.ROOT)
FP = ROOT / "samples" / "Tests" / "ForeignProjects"
base = Path(qh.WORK) / "dotnet-regression"
shutil.rmtree(base, ignore_errors=True)
ign = shutil.ignore_patterns("bin", "obj", ".vs", "_build", "TestResults")

from radide.foreign import vs_ui  # noqa: E402

w = qh.window()
CASES = [("VsSolution", "VsSolution.sln", 5), ("VsSolution", "VsSolution.slnx", 5),
         ("LegacyCsApp", "LegacyCsApp.sln", 1), ("WinFormsCS", "WinFormsCS.csproj", 1),
         ("WinFormsVB", "WinFormsVB.vbproj", 1), ("WinFormsComplexCS", "WinFormsComplexCS.csproj", 1),
         ("WinFormsComplexVB", "WinFormsComplexVB.vbproj", 1), ("MigrateWinFormsCS", "MigrateWinFormsCS.csproj", 1),
         ("MigrateWinFormsVB", "MigrateWinFormsVB.vbproj", 1), ("NativeCpp", "NativeCpp.vcxproj", 1)]
for i, (folder, fname, n) in enumerate(CASES):
    try:
        dst = base / f"{i:02d}_{folder}"
        shutil.copytree(FP / folder, dst, ignore=ign)
        ok = vs_ui.open_in_window(w, dst / fname)
        pump(1.5)
        got = len(w.sln.all_projects()) if w.sln is not None else 0
        check(f"{folder}/{fname}: opens in place ({got} project(s))", ok and got >= n and
              w.solution.topLevelItemCount() >= 1, (ok, got))
        w.output.clear()
        res = vs_ui.build(w, w.sln, wait=True)
        check(f"{folder}/{fname}: builds", bool(res) and all(c == 0 for c in res.values()),
              (res, w.output.toPlainText()[-1500:]))
        if i == 0:
            shot(w, "regression_vssolution")
    except Exception:  # noqa: BLE001
        check(f"{folder}/{fname}: no exception", False, traceback.format_exc()[-1200:])


def run_rad(sample, marker=None, t=240):
    dst = base / sample
    shutil.copytree(ROOT / "samples" / sample, dst, ignore=ign)
    w.open_project(dst, ask=False)
    pump(2)
    check(f"{sample}: opened as a RAD IDE project", w.project is not None and
          Path(w.project.folder).resolve() == dst.resolve(), getattr(w, "project", None))
    w.output.clear()
    w.run_project(debug=False)
    started = wait(lambda: w.session is not None and w.session.running(), t)
    pump(3)
    out = w.output.toPlainText()
    check(f"{sample}: builds and runs (F5 without debugging)", started and "error" not in out.lower().replace(
        "0 error", "") and "Traceback" not in out, out[-1500:])
    shot(w, f"regression_{sample}")
    if w.session is not None and w.session.running():
        w.session.stop()
        pump(1.5)


for sample in ("HelloCSharp", "HelloPython"):
    try:
        run_rad(sample)
    except Exception:  # noqa: BLE001
        check(f"{sample}: no exception", False, traceback.format_exc()[-1200:])
finish(w)
