"""Beginner-student QA for the smart assembly editor (headless part).

Each folder here is a program a beginner would write, with the usual mistakes. For every program the test:
  1. analyses it (radide.asm_lint) and checks the expected rule ids are reported on the right lines, each with an
     Arabic + English message, a "why" text, a "how to fix" text and a Learn-more link;
  2. applies the offered quick fixes one by one (what Ctrl+. does), like the student would, and does the remaining
     edits by hand exactly as the Arabic explanation says;
  3. checks the fixed program has no errors / warnings left;
  4. builds it with the real toolchain (NASM + gcc / MASM ml + link) and runs it, or runs it in the 8086 emulator,
     and checks the output;
  5. runs "Check by running" (radide.asm_sim) on the half-fixed program (assembler errors fixed, warnings left) to see
     the runtime findings, and on the fixed program to see it come back clean.
Run:  .venv/Scripts/python.exe samples/Tests/Assembly/SmartStudentQA/test_student.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

sys.path.insert(0, str(HERE))
from radide.asm_lint import apply_edits  # noqa: E402

RESULTS: list[tuple[str, bool]] = []
ARABIC = re.compile(r"[؀-ۿ]")


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:900]}]"), flush=True)
    return bool(cond)


from student_programs import PROGRAMS, apply_manual, apply_quick_fixes, lint_at, problems  # noqa: E402


def build_and_run(name, text, stdin=""):
    """Copy the project to a temporary folder, build it with radide.asm.build and run the exe."""
    from radide.asm.build import Builder
    tmp = Path(tempfile.mkdtemp(prefix=f"student_{name}_"))
    for f in (HERE / name).iterdir():
        if f.is_file():
            shutil.copy(f, tmp / f.name)
    (tmp / "main.asm").write_text(text, encoding="utf-8")
    logs = []
    b = Builder(tmp, log=logs.append) if "log" in Builder.__init__.__code__.co_varnames else Builder(tmp)
    ok = b.build()
    if not ok:
        return False, "\n".join(map(str, logs))[-1500:]
    exe = b.output_path
    r = subprocess.run([str(exe)], input=stdin, capture_output=True, text=True, timeout=20, cwd=str(tmp))
    shutil.rmtree(tmp, ignore_errors=True)
    return True, r.stdout


def run_8086(text, keys):
    from radide.emu8086.assembler import assemble
    from radide.emu8086.machine import Machine
    prog = assemble(text, "main.asm")
    errs = [d for d in getattr(prog, "diagnostics", []) if getattr(d, "severity", "") == "error"]
    if errs:
        return None, str(errs[:3])
    m = Machine()
    m.load(prog)
    m.feed_keys(keys)
    stop = m.run(max_steps=200_000)
    return m.screen_text(), str(getattr(stop, "reason", stop))


def sim_rules(text, folder):
    from radide.asm_sim import check as C
    res = C.check(text, str(folder / "main.asm"), download=False)
    return res, {f.rule for f in res.findings if f.severity in ("error", "warning")}


for name, spec in PROGRAMS.items():
    folder = HERE / name
    src = (folder / "main.asm").read_text(encoding="utf-8")
    print(f"\n===== {name}", flush=True)
    issues = lint_at(src, folder)
    got = {(i.rule, i.line + 1) for i in issues}
    for rule_id, line in spec["expect"]:
        check(f"{name}: {rule_id} on line {line}", (rule_id, line) in got, sorted(got))
    for i in issues:
        md = i.markdown("ar")
        check(f"{name}: {i.rule} L{i.line + 1} has Arabic message/why/fix + link",
              ARABIC.search(i.message("ar")) and ARABIC.search(i.why("ar")) and ARABIC.search(i.fix_text("ar"))
              and i.message("en") and "http" in md, (i.message("ar"), md[:300]))
    # half fixed: only assembler errors fixed (the student pressed Ctrl+. on the red squiggles)
    half = src
    for _ in range(10):
        errs = [i for i in lint_at(half, folder) if i.severity == "error" and i.fixes]
        if not errs:
            break
        half = apply_edits(half, errs[0].fixes[0].edits)
    if spec["sim_half"]:
        res, rules_ = sim_rules(half, folder)
        check(f"{name}: Check by running finds {sorted(spec['sim_half'])}", spec["sim_half"] <= rules_,
              (res.status, sorted(rules_), res.note_en, res.errors[:3]))
        for f in res.findings:
            check(f"{name}: runtime finding {f.rule} L{f.line} explained in Arabic",
                  ARABIC.search(f.message("ar")) and ARABIC.search(f.why("ar")), f.message("ar"))
    log: list[str] = []
    fixed = apply_quick_fixes(src, folder, log)
    print("  quick fixes applied:", *log, sep="\n    ")
    fixed, missing = apply_manual(fixed, spec["manual"])
    if not check(f"{name}: manual edits apply", fixed is not None, missing):
        continue
    left = problems(lint_at(fixed, folder))
    check(f"{name}: fixed program has no errors / warnings", not left,
          [(i.rule, i.line + 1, i.message("en")) for i in left] + [fixed])
    if name.startswith("Emu8086"):
        screen, why = run_8086(fixed, "7")
        check(f"{name}: fixed program runs in the 8086 emulator", screen is not None and
              all(s in screen for s in spec["output"]) and "Fail" not in screen, (why, screen))
        res, rules_ = sim_rules(fixed, folder)
        check(f"{name}: Check by running is clean on the fixed program", not rules_, (res.status, rules_))
        res_b, rules_b = sim_rules(half, folder)
        check(f"{name}: Check by running on the half-fixed program reports a runtime problem", rules_b,
              (res_b.status, rules_b, res_b.note_en))
    else:
        ok, out = build_and_run(name, fixed)
        check(f"{name}: fixed program builds", ok, out)
        if ok:
            check(f"{name}: fixed program prints {spec['output']}", all(s in out for s in spec["output"]), out)
        if name.startswith("Nasm"):
            res, rules_ = sim_rules(fixed, folder)
            check(f"{name}: Check by running is clean on the fixed program", res.status in ("ok",) and not rules_,
                  (res.status, sorted(rules_), res.note_en, res.output))
            check(f"{name}: Check by running output matches the real run", all(s in res.output
                                                                                for s in spec["output"]),
                  res.output)

# ---------------------------------------------------------------- explain this line + what-if (student questions)
print("\n===== Explain / What-If", flush=True)
from radide.asm_sim import check as C  # noqa: E402
from radide.asm_sim.whatif import whatif  # noqa: E402

avg = (HERE / "NasmAverage" / "main.asm").read_text(encoding="utf-8")
avg_fixed = apply_manual(apply_quick_fixes(avg, HERE / "NasmAverage", []), PROGRAMS["NasmAverage"]["manual"])[0]
ln = next(i for i, s in enumerate(avg_fixed.splitlines(), 1) if s.strip() == "add eax, [r10]")
ex = C.explain_line(avg_fixed, str(HERE / "NasmAverage" / "main.asm"), ln, iteration=1, download=False)
check("explain 'add eax, [r10]': ran 5 times, 2nd execution explained", ex.get("ok") and ex.get("count") == 5,
      {k: ex.get(k) for k in ("ok", "count", "status", "note_en")})
txt = repr(ex.get("steps"))
check("explain mentions EAX 10 -> 30 on the 2nd pass", "30" in txt and ARABIC.search(txt), txt[:600])
w = whatif("mov al, 200\nadd al, 100", "", bits=32)
wt = repr(w)
check("what-if: 200 + 100 in AL sets CF (carry) and explains it in Arabic", "CF" in wt and ARABIC.search(wt) and
      ("44" in wt or "0x2c" in wt.lower()), wt[:800])
w = whatif("mov ax, 5\nmov bl, 0\ndiv bl", "", bits=16)
wt = repr(w)
check("what-if: div by zero is explained", ARABIC.search(wt) and ("zero" in wt.lower() or "صفر" in wt), wt[:800])

ok = sum(1 for _n, c in RESULTS if c)
print(f"\n{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
sys.exit(0 if ok == len(RESULTS) else 1)
