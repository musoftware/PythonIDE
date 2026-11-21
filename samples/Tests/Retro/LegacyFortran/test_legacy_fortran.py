"""Legacy (fixed-form) Fortran - headless checks.

    python samples/Tests/Retro/LegacyFortran/test_legacy_fortran.py

1. OrbitTable (an original Fortran 66 style program) compiles with gfortran -std=legacy -ffixed-form
   (preset f66) and prints exactly expected_output.txt
2. the free-form conversion of ORBITS.f compiles as Fortran 90 free form and prints the same table
3. legacy-construct analysis, fixed-form fields, IBM 029 punch codes, gfortran diagnostics parsing
4. the language plugin: templates, .f files, hover, outline; every preset compiles the sample
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from radide.retro import legacy_fortran as lf  # noqa: E402

HERE = Path(__file__).resolve().parent
SAMPLE = HERE / "OrbitTable"
RESULTS: list[tuple[str, bool]] = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)


def norm(text: str) -> list[str]:
    return [l.rstrip() for l in text.replace("\r\n", "\n").strip("\n").split("\n")]


def run_exe(exe: str, cwd: Path) -> str:
    env = dict(os.environ)
    env["PATH"] = str(Path(lf.find_gfortran()).parent) + os.pathsep + env.get("PATH", "")
    return subprocess.run([exe], cwd=str(cwd), capture_output=True, text=True, env=env, timeout=60).stdout


expected = norm((SAMPLE / "expected_output.txt").read_text(encoding="utf-8"))
fc = lf.find_gfortran()
if not fc:
    print("SKIP: gfortran not found")
    sys.exit(0)

with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp) / "OrbitTable"
    work.mkdir()
    (work / "ORBITS.f").write_bytes((SAMPLE / "ORBITS.f").read_bytes())
    ok, exe = lf.build(work, "f66", log=lambda s: None)
    check("ORBITS.f builds with the f66 preset", ok)
    out = norm(run_exe(exe, work)) if ok else []
    check("output matches expected_output.txt", out == expected, "\n".join(out[:12]))
    for preset in ("legacy", "dec"):
        ok2, exe2 = lf.build(work, preset, log=lambda s: None)
        check(f"preset {preset} builds and prints the same", ok2 and norm(run_exe(exe2, work)) == expected)
    r = subprocess.run(lf.compile_command(["ORBITS.f"], "", "strict", syntax_only=True), cwd=str(work),
                       capture_output=True, text=True)
    diags = lf.parse_gfortran(r.stderr)
    check("strict F95 preset reports the deleted features (parsed diagnostics)", diags and
          all(d[1] == "ORBITS.f" and d[2] > 0 for d in diags), r.stderr[-500:])

    # free form
    free = lf.to_free_form((SAMPLE / "ORBITS.f").read_text(encoding="utf-8"))
    (work / "orbits.f90").write_text(free, encoding="utf-8")
    exe3 = str(work / "free.exe")
    r = subprocess.run([fc, "-ffree-form", "-std=legacy", "-fno-automatic", "-o", exe3, "orbits.f90"],
                       cwd=str(work), capture_output=True, text=True,
                       env={**os.environ, "PATH": str(Path(fc).parent) + os.pathsep + os.environ.get("PATH", "")})
    check("free-form conversion compiles", r.returncode == 0, r.stderr[-800:])
    check("free-form program prints the same table", r.returncode == 0 and norm(run_exe(exe3, work)) == expected)
    check("conversion: no Hollerith, no sequence numbers, ! comments", "24H" not in free and "ORBT0" not in free
          and free.splitlines()[0].startswith("!") and "'CIRCULAR ORBITS OF EARTH'" in free)
    keep = lf.to_free_form((SAMPLE / "ORBITS.f").read_text(encoding="utf-8"), keep_sequence=True)
    check("conversion can keep sequence numbers as comments", "! ORBT0150" in keep)
    check("diff preview", lf.diff("A\n", "B\n").startswith("--- fixed.f"))

# ------------------------------------------------------------------ analysis / fields / cards
src = (SAMPLE / "ORBITS.f").read_text(encoding="utf-8")
kinds = {k for _l, k, _e, _a in lf.analyze(src)}
check("analysis finds arithmetic IF, computed GO TO, Hollerith, COMMON", {"arith_if", "computed_goto", "hollerith",
                                                                         "common", "implicit"} <= kinds, kinds)
check("no false 'shared DO' (labels are per program unit)", "shared_do" not in kinds)
check("assigned GO TO detected", "assigned_goto" in {k for _l, k, _e, _a in lf.analyze(
    "      ASSIGN 10 TO K\n      GO TO K\n   10 CONTINUE\n")})
f = lf.fields("   10 CONTINUE" + " " * 58 + "ORBT0350")
check("fixed-form fields", f["label"] == "10" and f["stmt"].strip() == "CONTINUE" and f["seq"] == "ORBT0350")
check("continuation column", lf.fields("     1   X")["cont"] == "1" and lf.fields("     0   X")["cont"] == "")
check("DEC tab format", lf.expand_tabs("\tX = 1").startswith("      X") and lf.fields("\t1 + 2")["cont"] == "1")
check("column notes", "continuation" in lf.column_note("      X", 6) and "sequence" in lf.column_note("x" * 80, 75))
check("IBM 029 punch codes", lf.punch_rows("A") == (12, 1) and lf.punch_rows("Z") == (0, 9) and
      lf.punch_rows("(") == (12, 5, 8) and lf.punch_rows("=") == (6, 8) and lf.punch_rows(" ") == ())
card = lf.card_text("      PRINT 1")
check("card drawing: 80 columns, 12 rows", len(card.splitlines()) == 13 and len(card.splitlines()[1]) == 82)
check("hollerith_to_quotes", lf.hollerith_to_quotes("FORMAT (1X, 5HHELLO, 3H'A')") == "FORMAT (1X, 'HELLO', '''A''')")
check("gfortran one-line diagnostics", lf.parse_gfortran("a.f:3:7: Error: Bad\n") == [("Error", "a.f", 3, "Bad")])

# ------------------------------------------------------------------ plugin
from radide.languages import get_plugin, plugin_for_file  # noqa: E402
plug = get_plugin("fortran-legacy")
check(".f files use the fixed-form plugin, .f90 the modern one", plugin_for_file("X.f").id == "fortran-legacy" and
      plugin_for_file("X.f90").id == "fortran-bridge")
with tempfile.TemporaryDirectory() as tmp:
    p = plug.create_new_project(Path(tmp) / "Orbit", "Orbit", "f66_orbits")
    check("Orbit Table template", (Path(p.folder) / "ORBITS.f").exists() and p.extra["fortran"]["preset"] == "f66")
    p2 = plug.create_new_project(Path(tmp) / "Hello", "Hello", "f77_hello")
    ok, exe = lf.build(Path(p2.folder), "legacy", log=lambda s: None)
    check("Hello, Fortran 77 template builds and runs", ok and "HELLO FROM FORTRAN 77" in run_exe(exe, Path(p2.folder)))
lines = src.splitlines()
k = next(i for i, l in enumerate(lines) if "IF (TA) 15, 16, 16" in l)
check("hover explains arithmetic IF and the column", "Arithmetic IF" in plug.hover(src, k, 8) and
      "statement" in plug.hover(src, k, 8))
check("outline: PROGRAM + FUNCTION", [s["name"] for s in plug.document_symbols(src)] ==
      ["PROGRAM ORBITS", "FUNCTION ECCAN"])
check("Monarch grammar for fixed form", plug.monaco_language("X.f")["id"] == "rad-fortran-fixed")

ok = sum(c for _n, c in RESULTS)
print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
sys.exit(0 if ok == len(RESULTS) else 1)
