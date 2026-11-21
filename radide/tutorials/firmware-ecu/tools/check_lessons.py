"""Checker for the firmware-ecu course: runs every runnable block of radide/tutorials/firmware-ecu.

    python radide/tutorials/firmware-ecu/tools/check_lessons.py            # all lessons
    python radide/tutorials/firmware-ecu/tools/check_lessons.py 03 -v      # lessons whose id starts with 03
    python radide/tutorials/firmware-ecu/tools/check_lessons.py --fill     # write the output of blocks whose
                                                                           # expected output is still "TODO"

Block kinds (fence info strings):

* ``python run`` / ``python exercise`` / ``python solution`` - standard-library Python (the lesson viewer runs
  them too); output compared with the ``text output`` block after them (radide.tutorials.check).
  ``python exercise`` needs a ``python solution``.
* ``fwpy run`` - Python that uses RAD IDE's own firmware library (radide.firmware.*). Run here in a fresh
  folder with the repository on PYTHONPATH (the viewer shows it as code; the learner runs it with python from
  the RAD IDE folder). Its output must equal the following ``text output`` block.

Only synthetic firmware written by RAD IDE is used - no manufacturer files, nothing is downloaded.
Quiz JSON is validated.
"""
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
COURSE = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from radide import tutorials as T  # noqa: E402

NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _rm(path: Path) -> None:
    def onerror(func, p, _exc):          # ECU projects keep their original read-only
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onerror=onerror)


def run_python(code: str, work: Path, with_repo: bool) -> tuple[bool, str]:
    work.mkdir(parents=True, exist_ok=True)
    (work / "main.py").write_text(code, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    if with_repo:
        env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    else:
        env.pop("PYTHONPATH", None)
    r = subprocess.run([sys.executable, "-X", "utf8", "main.py"], cwd=work, env=env, capture_output=True,
                       timeout=300, creationflags=NO_WINDOW)
    out = r.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
    if r.returncode:
        return False, out + r.stderr.decode("utf-8", "replace")
    return True, out


def expected_index(blocks, i):
    for j in range(i + 1, len(blocks)):
        nxt = blocks[j]
        if nxt.role == "output" and nxt.lang == "text":
            return j
        if nxt.lang != "text" and nxt.info.split()[:1] != ["python"]:
            return None
        if nxt.info.split()[:2] in (["python", "run"], ["fwpy", "run"]):
            return None
    return None


def fill(course) -> int:
    """Replace ``TODO`` outputs with the real output (maintainer helper)."""
    n = 0
    work_root = Path(tempfile.mkdtemp(prefix="fwcourse-fill-"))
    for les in course.lessons:
        text = les.path.read_text(encoding="utf-8")
        blocks = les.blocks()
        outs = []
        for i, b in enumerate(blocks):
            words = b.info.split()
            if words[:2] not in (["python", "run"], ["python", "solution"], ["fwpy", "run"]):
                continue
            j = expected_index(blocks, i)
            if j is None or blocks[j].code.strip() != "TODO":
                continue
            ok, out = run_python(b.code, work_root / f"{les.id}-{b.index}", words[0] == "fwpy")
            if not ok:
                print(f"FAIL (fill) {les.id} #{b.index}:\n{out}")
                continue
            outs.append(out.rstrip("\n"))
        for out in outs:
            text = re.sub(r"```text output\nTODO\n```", lambda _m, o=out: "```text output\n" + o + "\n```", text,
                          count=1)
            n += 1
        les.path.write_bytes(text.encode("utf-8"))            # keep LF line ends
    _rm(work_root)
    print(f"filled {n} output block(s)")
    return 0


def main(argv):
    verbose = "-v" in argv
    only = [a for a in argv if not a.startswith("-")]
    course = T.course("firmware-ecu")
    assert course is not None, "course firmware-ecu not found"
    if "--fill" in argv:
        return fill(course)
    work_root = Path(tempfile.mkdtemp(prefix="fwcourse-"))
    total = failed = 0
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
            work.mkdir(parents=True, exist_ok=True)
            if b.lang == "py" and b.role in ("run", "solution", "exercise"):
                total += 1
                r = None
                if b.role == "exercise":
                    ok, why = b.solution is not None, "exercise without a solution block"
                else:
                    r = T.check(b, None, None, work)
                    ok = r.ok and b.expected is not None and b.expected.strip() != "TODO"
                    why = "; ".join(r.problems) + ("" if b.expected is not None else " [no expected output]")
                if not ok:
                    failed += 1
                if verbose or not ok:
                    print(f"{'ok' if ok else 'FAIL'} {les.id} #{b.index} python {b.role} (line {b.line}) "
                          f"{'' if ok else why}")
                    if not ok and r is not None:
                        print("    --- got ---\n    " + r.output.strip().replace("\n", "\n    "))
                continue
            if head == "fwpy" and role == "run":
                total += 1
                j = expected_index(blocks, i)
                exp = blocks[j].code if j is not None else None
                ran, got = run_python(b.code, work, True)
                ok = ran and exp is not None and exp.strip() != "TODO" and T.norm(got) == T.norm(exp)
                if not ok:
                    failed += 1
                if verbose or not ok:
                    print(f"{'ok' if ok else 'FAIL'} {les.id} #{b.index} fwpy run (line {b.line})")
                    if not ok:
                        print("    --- got ---\n    " + got.strip().replace("\n", "\n    "))
                        print("    --- expected ---\n    " + str(exp).strip().replace("\n", "\n    "))
                continue
    _rm(work_root)
    print(f"\n{total - failed}/{total} blocks OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
