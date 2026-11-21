"""Checker for the DOS programming course: builds and runs every runnable block of radide/tutorials/dos-programming.

    python radide/tutorials/dos-programming/tools/check_lessons.py            # all lessons
    python radide/tutorials/dos-programming/tools/check_lessons.py 03 -v      # lessons whose id starts with 03

Block info strings (the tutorial engine shows them as plain code; the names are the project types of
New Project > DOS, so a learner pastes the block into MAIN.BAS / MAIN.PAS / MAIN.C / MAIN.ASM / MAIN.BAT):

* ```` ```dos-qbasic run ```` / ``dos-pascal`` / ``dos-c`` / ``dos-asm`` / ``dos-batch``: a whole program. It is
  written into a new DOS project (radide.retro.dos plugin, the "hello" template replaced), built with the free
  compiler (FreeBASIC -lang qb for DOS, Free Pascal i8086-msdos, Open Watcom, JWasm) and run in DOSBox-X without a
  window (``dosbox.capture_text``); the following ```` ```text output ```` must appear, line for line, in what the
  program printed (standard output) or on its text screen;
* ``exercise`` blocks must build; a ``solution`` block after them is run like a ``run`` block;
* hidden ``<!-- test: {...} -->`` before a block: ``"keys"`` typed for the program (RADKEYS syntax: ``~`` Enter,
  `````` ` `````` Esc, ``_`` Space), ``"com": true`` (.COM output), ``"mode13": true`` (a 256-colour mode 13h frame
  must be captured), ``"screen": true`` (standard output is not redirected: only the text screen is compared,
  for programs that draw with LOCATE / COLOR), ``"build_only": true``, ``"error_line": N`` (the build must fail with an Error List row at
  line N of the main file), ``"timeout"``;
* ``dos-tuiforms``, ``qb``, ``text`` ... blocks are snippets, not run; quiz JSON is validated.

Tools missing (offline, nothing downloaded yet) are reported as UNCHECKED, not as failures.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4] if (HERE.parents[4] / "radide" / "tutorials").is_dir() else \
    Path(r"D:\Projects\1AOrganized\PythonProjects\SYSTEMs\PythonIDE")
sys.path.insert(0, str(REPO))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from radide import tutorials as T  # noqa: E402

KINDS = {"dos-qbasic": "qbasic", "dos-pascal": "pascal", "dos-c": "c", "dos-asm": "asm", "dos-batch": "batch"}
HELLO = {"qbasic": "dosqb_hello", "pascal": "dostp_hello", "c": "dostc_hello", "asm": "dosasm_hello",
         "batch": "dosbat_hello"}


def runnable_blocks(lesson):
    """(block, kind, expected text) for every dos-* run / exercise / solution block of *lesson*."""
    blocks = lesson.blocks()
    out = []
    for i, b in enumerate(blocks):
        words = b.info.split()
        if not words or words[0] not in KINDS:
            continue
        role = next((r for r in ("run", "exercise", "solution") if r in words[1:]), "")
        if not role:
            continue
        expected = None
        for nxt in blocks[i + 1:]:
            if nxt.lang == "text" and nxt.role == "output":
                expected = nxt.code
                break
            if nxt.lang != "text":
                break
        out.append((b, KINDS[words[0]], role, expected))
    return out


from radide.tutorials import dos_support as D  # noqa: E402  (the same code as the tutorial's "Check" button)

lines_of, contains = D.lines_of, D.contains


def check_block(block, kind, role, expected, work: Path) -> tuple[bool, str]:
    """Build the block in a new DOS project and run it captured in DOSBox-X (radide/tutorials/dos_support.py)."""
    spec = block.spec or {}
    log: list[str] = []
    ok, folder, s, main = D.build_block(block, None, work, T.block_files, log)
    good, out, problems = D.run_and_compare(block, block, folder, s, main, ok, log, expected=expected)
    if good and expected is None and role != "exercise" and not (spec.get("mode13") or spec.get("build_only")
                                                                 or "error_line" in spec):
        good, problems = False, ["no ```text output``` block and no test"]
    if good:
        return True, ""
    tail = ("\n--- expected ---\n" + expected) if expected else ""
    return False, "; ".join(problems) + "\n" + out[-2500:] + tail


def main(argv: list[str]) -> int:
    verbose = "-v" in argv
    only = [a for a in argv if not a.startswith("-")]
    course = T.course("dos-programming")
    assert course is not None, "course dos-programming not found"
    from radide.retro.dos import toolchain
    have_dosbox = bool(toolchain.dosbox_exe(download=True, log=lambda *_a: None))
    work_root = Path(tempfile.mkdtemp(prefix="doscourse-"))
    total = failed = unchecked = 0
    try:
        for les in course.lessons:
            if only and not any(les.id.startswith(o) for o in only):
                continue
            for b in les.blocks():
                if b.lang == "quiz":
                    total += 1
                    if not b.quiz or not (0 <= int(b.quiz["answer"]) < len(b.quiz["choices"])):
                        failed += 1
                        print(f"FAIL {les.id} #{b.index} (line {b.line}): bad quiz JSON")
            for b, kind, role, expected in runnable_blocks(les):
                total += 1
                comp = toolchain.COMPILER_FOR_KIND.get(kind)
                if (comp and not toolchain.ensure_for(comp, log=lambda *_a: None, download=True)) or \
                        (not have_dosbox and role != "exercise"):
                    unchecked += 1
                    print(f"UNCHECKED {les.id} #{b.index} {b.info} (line {b.line}): {comp or 'DOSBox-X'} missing")
                    continue
                ok, detail = check_block(b, kind, role, expected, work_root / f"{les.id}-{b.index}")
                if not ok:
                    failed += 1
                if verbose or not ok:
                    print(f"{'ok' if ok else 'FAIL'} {les.id} #{b.index} {b.info} (line {b.line})")
                    if not ok:
                        print("    " + detail.strip().replace("\n", "\n    "))
    finally:
        shutil.rmtree(work_root, ignore_errors=True)
    print(f"\n{total - failed - unchecked}/{total} blocks OK" + (f", {unchecked} unchecked" if unchecked else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
