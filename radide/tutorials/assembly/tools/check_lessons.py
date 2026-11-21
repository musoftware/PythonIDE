"""Checker for the Assembly course: runs every runnable block of radide/tutorials/assembly.

    python radide/tutorials/assembly/tools/check_lessons.py            # all lessons
    python radide/tutorials/assembly/tools/check_lessons.py 05 -v      # lessons whose id starts with 05, list every block

* ``asm run`` / ``asm solution``: NASM (win64) + gcc (MinGW-w64), output compared with ``text output``;
* ``asm exercise``: the starter code must assemble, and it needs a solution block;
* ``asm form run``: built with the Assembly plugin's build command (assembled only when the plugin is missing);
* ``asm16 run``: the 8086 emulator's headless runner (reported as UNCHECKED when the emulator is not installed);
* quiz JSON is validated; every runnable block's "جرّبه" project is created with make_project().
"""
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4] if (HERE.parents[4] / "radide" / "tutorials").is_dir() else \
    Path(r"D:\Projects\1AOrganized\PythonProjects\SYSTEMs\PythonIDE")
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from radide import tutorials as T  # noqa: E402
from radide.tutorials import asm_support as A  # noqa: E402


def main(argv):
    verbose = "-v" in argv
    only = [a for a in argv if not a.startswith("-")]
    course = T.course("assembly")
    assert course is not None, "course assembly not found"
    tools = A.available()
    print("tools:", tools)
    work_root = Path(tempfile.mkdtemp(prefix="asmcourse-"))
    total = failed = unchecked = 0
    for les in course.lessons:
        if only and not any(les.id.startswith(o) for o in only):
            continue
        for b in les.blocks():
            if b.lang == "quiz":
                total += 1
                if not b.quiz or not (0 <= int(b.quiz["answer"]) < len(b.quiz["choices"])):
                    failed += 1
                    print(f"FAIL {les.id} #{b.index} (line {b.line}): bad quiz JSON")
                continue
            if b.lang not in A.LANGS or b.role not in ("run", "solution", "exercise"):
                continue
            total += 1
            work = work_root / f"{les.id}-{b.index}"
            if b.lang == "asm16" and not tools["emulator"]:
                unchecked += 1
                print(f"UNCHECKED {les.id} #{b.index} asm16 {b.role} (line {b.line}): 8086 emulator not installed")
                continue
            if b.role == "exercise":
                if b.lang == "asm16":            # the emulator's assembler must accept the starter code
                    prog = A.emulator().assemble(b.code, "main.asm")
                    ok, out = prog.ok, "\n".join(str(e) for e in prog.errors)
                elif b.gui:
                    ok, out = A.build_gui(T.block_files(b), work, b.check_target().spec)
                else:
                    ok, out = A.assemble_only(T.block_files(b), work)
                if b.solution is None:
                    ok, out = False, "exercise without a solution block"
                if not ok:
                    failed += 1
                if verbose or not ok:
                    print(f"{'ok' if ok else 'FAIL'} {les.id} #{b.index} exercise (line {b.line})")
                    if not ok:
                        print("   ", out.strip()[:800])
                continue
            r = T.check(b, None, None, work)
            spec = b.spec or {}
            verified = b.expected is not None or spec.get("norun") or b.gui
            ok = r.ok and bool(verified)
            if not ok:
                failed += 1
            if verbose or not ok:
                kind = "form" if b.gui else b.lang
                print(f"{'ok' if ok else 'FAIL'} {les.id} #{b.index} {b.role} {kind} (line {b.line})"
                      + ("" if verified else "  [no expected output / test]"))
                if not ok:
                    for p in r.problems:
                        print("    problem:", p)
                    print("    --- got ---\n    " + r.output.strip().replace("\n", "\n    "))
                    if r.expected is not None:
                        print("    --- expected ---\n    " + r.expected.strip().replace("\n", "\n    "))
            T.make_project(b, work_root / f"proj-{les.id}-{b.index}")
    shutil.rmtree(work_root, ignore_errors=True)
    print(f"\n{total - failed - unchecked}/{total} blocks OK" + (f", {unchecked} unchecked (8086 emulator missing)"
                                                              if unchecked else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
