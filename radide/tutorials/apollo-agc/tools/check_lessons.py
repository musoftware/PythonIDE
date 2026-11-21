"""Checker for the apollo-agc course: runs every runnable block of radide/tutorials/apollo-agc.

    python radide/tutorials/apollo-agc/tools/check_lessons.py            # all lessons
    python radide/tutorials/apollo-agc/tools/check_lessons.py 03 -v      # lessons whose id starts with 03

Block kinds (fence info strings):

* ``agc run`` / ``agc solution`` - a complete AGC program (yaYUL syntax, MAIN.agc; ``# #file: NAME.agc`` lines
  split it into files).  It is assembled with RAD IDE's built-in assembler and run in the built-in emulator
  (radide.agc).  A hidden ``<!-- test: {...} -->`` before it says what to print:

      "seconds": 0.1          emulated time before the keys (default 0.1 s)
      "keys": "V35E"          DSKY keys, then "after" seconds (default 1.0)
      "show": ["SUM"]         erasable / fixed symbols, printed as signed decimal (ones' complement)
      "octal": ["MASKED"]     the same in octal
      "dsky": true            the DSKY line (PROG VERB NOUN R1 R2 R3 [lamps])
      "restarts": true        how many times the hardware alarms restarted the AGC
      "alarms": true          keep the hardware alarms on (default off, like "agc": {"alarms": false})
      "base": "hello_dsky"    start from the files of radide/agc/examples/hello_dsky; the block replaces
                              the files it names

  The printout must equal the ``text output`` block after it.  When Virtual AGC's yaYUL is installed
  (Tools > Retro > Apollo AGC > Virtual AGC Toolchain), every block is also assembled with yaYUL and the two
  ropes must be identical word for word.  ``agc exercise`` must assemble and needs a solution.
* ``fortran run`` / ``fortran exercise`` / ``fortran solution`` - gfortran (radide.tutorials.native; a
  ``! #file: name.f`` first line keeps the fixed form), output compared with ``text output``.

Quiz JSON is validated.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from radide import tutorials as T  # noqa: E402

EXAMPLES = REPO / "radide" / "agc" / "examples"


def signed(v: int) -> int:
    v &= 0o77777
    return -(v ^ 0o77777) if v & 0o40000 else v


def agc_files(b, work: Path, spec: dict) -> Path:
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    if spec.get("base"):
        for f in (EXAMPLES / spec["base"]).glob("*.agc"):
            shutil.copy2(f, work / f.name)
    for name, text in T.split_files(b.code, "MAIN.agc").items():
        (work / name).write_text(text, encoding="utf-8")
    return work / "MAIN.agc"


def run_agc(main: Path, spec: dict) -> tuple[bool, str, object]:
    from radide.agc import assembler
    from radide.agc.machine import AgcMachine
    prog = assembler.assemble_file(main)
    if not prog.ok:
        return False, "\n".join(f"{Path(d.file).name}:{d.line}: {d.text('en')}" for d in prog.errors), prog
    m = AgcMachine(prog)
    m.cpu.alarms = bool(spec.get("alarms", False))
    m.run_seconds(float(spec.get("seconds", 0.1)))
    if spec.get("keys"):
        m.keys(spec["keys"])
        m.run_seconds(float(spec.get("after", 1.0)))
    out = []
    for name in spec.get("show", []):
        sv = m.symbol_value(name)
        out.append(f"{name} = {signed(sv[1]) if sv else '(unknown)'}")
    for name in spec.get("octal", []):
        sv = m.symbol_value(name)
        out.append(f"{name} = {sv[1]:05o}" if sv else f"{name} = (unknown)")
    if spec.get("dsky"):
        out.append("DSKY: " + m.dsky.summary())
    if spec.get("restarts"):
        out.append(f"restarts: {m.cpu.restarts}")
    return True, "\n".join(out), prog


def yayul_same(folder: Path, prog) -> tuple[bool | None, str]:
    """None = yaYUL not installed; else (identical?, detail)."""
    from radide.agc import assembler, toolchain
    exe = toolchain.find("yayul")
    if not exe:
        return None, ""
    r = subprocess.run([exe, "MAIN.agc"], cwd=folder, capture_output=True, text=True, errors="replace")
    binf = folder / "MAIN.agc.bin"
    if not binf.is_file():
        return False, "yaYUL wrote no rope: " + (r.stdout + r.stderr)[-600:]
    ya = assembler.load_bin(binf.read_bytes())
    diffs = [(bk, o) for (bk, o) in prog.used if prog.rope[bk][o] != ya[bk][o]]
    return not diffs, (f"{len(diffs)} words differ, first bank {diffs[0][0]:o} offset {diffs[0][1]:o}" if diffs else "")


def expected_after(blocks, i):
    for nxt in blocks[i + 1:]:
        if nxt.role == "output" and nxt.lang == "text":
            return nxt.code
        if nxt.lang != "text":
            return None
    return None


def main(argv):
    verbose = "-v" in argv
    only = [a for a in argv if not a.startswith("-")]
    course = T.course("apollo-agc")
    assert course is not None, "course apollo-agc not found"
    work_root = Path(tempfile.mkdtemp(prefix="agccourse-"))
    total = failed = 0
    yayul_checked = 0
    for les in course.lessons:
        if only and not any(les.id.startswith(o) for o in only):
            continue
        blocks = les.blocks()
        for i, b in enumerate(blocks):
            words = b.info.split()
            head = words[0].lower() if words else ""
            role = words[1].lower() if len(words) > 1 else ""
            if b.lang == "quiz":
                total += 1
                if not b.quiz or not (0 <= int(b.quiz["answer"]) < len(b.quiz["choices"])):
                    failed += 1
                    print(f"FAIL {les.id} #{b.index} (line {b.line}): bad quiz JSON")
                continue
            work = work_root / f"{les.id}-{b.index}"
            if b.lang == "fortran" and b.role in ("run", "solution", "exercise"):
                total += 1
                work.mkdir(parents=True, exist_ok=True)
                if b.role == "exercise":
                    ok, why, r = b.solution is not None, "exercise without a solution block", None
                else:
                    r = T.check(b, None, None, work)
                    ok = r.ok and b.expected is not None
                    why = "; ".join(r.problems)
                if not ok:
                    failed += 1
                if verbose or not ok:
                    print(f"{'ok' if ok else 'FAIL'} {les.id} #{b.index} fortran {b.role} (line {b.line}) {'' if ok else why}")
                    if not ok and r is not None:
                        print("    --- got ---\n    " + r.output.strip().replace("\n", "\n    "))
                continue
            if head == "agc" and role in ("run", "solution", "exercise"):
                total += 1
                spec = b.spec or {}
                main_file = agc_files(b, work, spec)
                ok, got, prog = run_agc(main_file, spec)
                exp = expected_after(blocks, i)
                detail = ""
                if ok and role != "exercise":
                    ok = exp is not None and T.norm(got) == T.norm(exp)
                if role == "exercise" and not any(x.info.split()[:2] == ["agc", "solution"] for x in blocks[i + 1:]):
                    ok, detail = False, "exercise without a solution block"
                if prog is not None and getattr(prog, "ok", False):
                    same, why = yayul_same(work, prog)
                    if same is not None:
                        yayul_checked += 1
                        if not same:
                            ok, detail = False, "yaYUL rope differs: " + why
                if not ok:
                    failed += 1
                if verbose or not ok:
                    print(f"{'ok' if ok else 'FAIL'} {les.id} #{b.index} agc {role} (line {b.line}) {detail}")
                    if not ok:
                        print("    --- got ---\n    " + got.replace("\n", "\n    "))
                        print("    --- expected ---\n    " + str(exp).strip().replace("\n", "\n    "))
    shutil.rmtree(work_root, ignore_errors=True)
    print(f"\n{total - failed}/{total} blocks OK" + (f" ({yayul_checked} AGC blocks also identical in yaYUL)"
                                                    if yayul_checked else " (yaYUL not installed: built-in only)"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
