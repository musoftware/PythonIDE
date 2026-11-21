"""Checker for the Ring course: runs every runnable block of radide/tutorials/ring with the real ring.exe.

    python radide/tutorials/ring/tools/check_lessons.py            # all lessons
    python radide/tutorials/ring/tools/check_lessons.py 05 -v      # lessons whose id starts with 05, list every block
"""
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
# inside the repository (radide/tutorials/ring/tools/check_lessons.py) or a copy elsewhere
REPO = HERE.parents[4] if (HERE.parents[4] / "radide" / "tutorials").is_dir() else \
    Path(r"D:\Projects\1AOrganized\PythonProjects\SYSTEMs\PythonIDE")
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from radide import tutorials as T  # noqa: E402
from radide.tutorials import ring_support as R  # noqa: E402


def main(argv):
    verbose = "-v" in argv
    only = [a for a in argv if not a.startswith("-")]
    course = T.course("ring")
    assert course is not None, "course ring not found"
    work_root = Path(tempfile.mkdtemp(prefix="ringcourse-"))
    total = failed = 0
    for les in course.lessons:
        if only and not any(les.id.startswith(o) for o in only):
            continue
        blocks = les.blocks()
        for b in blocks:
            if b.lang == "quiz":
                total += 1
                if not b.quiz or not (0 <= int(b.quiz["answer"]) < len(b.quiz["choices"])):
                    failed += 1
                    print(f"FAIL {les.id} #{b.index} (line {b.line}): bad quiz JSON")
                continue
            if b.lang != "ring" or b.role not in ("run", "solution", "exercise"):
                continue
            total += 1
            work = work_root / f"{les.id}-{b.index}"
            if b.role == "exercise":
                ok, out = R.syntax_only(T.block_files(b), work, b.form)
                if b.solution is None:
                    ok, out = False, "exercise without a solution block"
                status = "ok" if ok else "FAIL"
                if not ok:
                    failed += 1
                if verbose or not ok:
                    print(f"{status} {les.id} #{b.index} exercise (line {b.line})")
                    if not ok:
                        print("   ", out.strip()[:600])
                continue
            r = T.check(b, None, None, work)
            spec = b.spec or {}
            verified = b.expected is not None or spec.get("expect") or spec.get("norun")
            ok = r.ok and bool(verified)
            if not ok:
                failed += 1
            if verbose or not ok:
                kind = "form" if b.form else "console"
                print(f"{'ok' if ok else 'FAIL'} {les.id} #{b.index} {b.role} {kind} (line {b.line})"
                      + ("" if verified else "  [no expected output / test]"))
                if not ok:
                    for p in r.problems:
                        print("    problem:", p)
                    print("    --- got ---\n    " + r.output.strip().replace("\n", "\n    "))
                    if r.expected is not None:
                        print("    --- expected ---\n    " + r.expected.strip().replace("\n", "\n    "))
            # make_project must work too (what "جرّبه" does)
            T.make_project(b, work_root / f"proj-{les.id}-{b.index}")
    shutil.rmtree(work_root, ignore_errors=True)
    print(f"\n{total - failed}/{total} blocks OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
