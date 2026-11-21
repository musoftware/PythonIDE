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
  must be captured), ``"build_only": true``, ``"error_line": N`` (the build must fail with an Error List row at
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


def lines_of(text: str) -> list[str]:
    rows = [ln.rstrip() for ln in text.replace("\r\r\n", "\n").replace("\r\n", "\n").split("\n")]
    while rows and not rows[-1]:
        rows.pop()
    return rows


def contains(hay: list[str], needle: list[str]) -> bool:
    needle = [n for n in needle]
    while needle and not needle[0]:
        needle.pop(0)
    if not needle:
        return True
    for i in range(len(hay) - len(needle) + 1):
        if hay[i:i + len(needle)] == needle:
            return True
    return False


def build_block(block, kind: str, spec: dict, work: Path, log: list):
    """Write the block into a new DOS project and build it -> (ok, folder, settings)."""
    from radide.languages import get_plugin
    from radide.model import Project
    from radide.retro.dos import build as B
    from radide.retro.dos.templates import BY_ID, write_dos_text
    shutil.rmtree(work, ignore_errors=True)
    plugin = get_plugin(B.LANGUAGE_OF_KIND[kind])
    plugin.create_new_project(work, "Lesson", HELLO[kind])
    main = BY_ID[HELLO[kind]].main
    write_dos_text(work / main, block.code)
    if spec.get("com") or spec.get("model"):
        p = Project.load(work)
        dos = p.extra.setdefault("dos", {})
        if spec.get("com"):
            dos["output"] = "com"
        if spec.get("model"):
            dos["model"] = spec["model"]
        p.save()
    ok = B.Builder(work, log=log.append).build()
    return ok, work, B.settings_for(Project.load(work)), main


def check_block(block, kind, role, expected, work: Path) -> tuple[bool, str]:
    from radide.retro.dos import build as B
    from radide.retro.dos import dosbox, helpers
    spec = block.spec or {}
    log: list[str] = []
    ok, folder, s, main = build_block(block, kind, spec, work, log)
    diags = B.read_diagnostics(folder).get("diags", [])
    if "error_line" in spec:
        rows = [d for d in diags if d["severity"] == "Error" and d["file"].upper() == main.upper()
                and d["line"] == spec["error_line"]]
        return (not ok and bool(rows)), "\n".join(log[-12:])
    if not ok:
        return False, "build failed:\n" + "\n".join(log[-15:])
    if role == "exercise" or spec.get("build_only"):
        return True, ""
    cmd = ("CALL " + s["main"]) if kind == "batch" else B.output_name(s)
    run = dosbox.DosRun(mounts=[("C", folder)], path=["Z:\\BIN", "Z:\\DOS"])
    r = dosbox.capture_text(run, folder, cmd, keys=spec.get("keys", ""), timeout=int(spec.get("timeout", 25)),
                            log=lambda *_a: None)
    if r["timed_out"]:
        return False, "timed out (does the program wait for more keys?)\n" + r["stdout"][-400:] + r["screen"][-600:]
    problems = []
    if spec.get("mode13"):
        st = helpers.mode13_stats(r["graphics"]) if r["graphics"] else {}
        if not st or st.get("nonzero", 0) < 1000:
            problems.append(f"no mode 13h frame captured ({st})")
    if expected is not None:
        want = lines_of(expected)
        if not (contains(lines_of(r["stdout"]), want) or contains(lines_of(r["screen"]), want)):
            problems.append("output differs")
    elif not spec.get("mode13"):
        problems.append("no ```text output``` block and no test")
    detail = ""
    if problems:
        detail = ("; ".join(problems) + "\n--- stdout ---\n" + "\n".join(lines_of(r["stdout"])[-25:]) +
                  "\n--- screen ---\n" + "\n".join(x for x in lines_of(r["screen"]) if x.strip())[-1500:] +
                  ("\n--- expected ---\n" + expected if expected else ""))
    return not problems, detail


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
