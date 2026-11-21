"""Course checker for radide/tutorials/visual-studio-projects: every runnable block (``run`` and ``solution``) is
built and run with the IDE's own tutorial checker (radide.tutorials.check: dotnet build + run, output compared
with the following ```text output block); every exercise starter must NOT pass as given (it has something to fix).

    python samples/Tests/Tutorials/VisualStudioProjects/check_course.py              # all lessons
    python samples/Tests/Tutorials/VisualStudioProjects/check_course.py 09 10        # lessons starting with 09 / 10
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from radide import tutorials as T  # noqa: E402


def main() -> int:
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    c = T.course("visual-studio-projects")
    work = Path(tempfile.mkdtemp(prefix="radtut-vsp-"))
    ok_n, bad = 0, []
    for les in c.lessons:
        if only and not any(les.id.startswith(o) for o in only):
            continue
        quiz = [b for b in les.blocks() if b.lang == "quiz"]
        if any(b.quiz is None for b in quiz):
            bad.append(f"{les.id}: invalid quiz JSON")
        for b in les.blocks():
            if b.runnable:
                r = T.check(b, work=work / f"{les.id}-{b.index}")
                good = r.ok and (b.check_target().expected is not None)
                tag = "ok  " if good else "FAIL"
                print(f"{tag} {les.id} block {b.index} ({b.role}, line {b.line})")
                if not good:
                    print("     problems:", r.problems, "\n     output:", (r.output or "")[:800])
                    bad.append(f"{les.id} block {b.index}")
                else:
                    ok_n += 1
            elif b.role == "exercise":
                r = T.check(b, work=work / f"{les.id}-{b.index}-starter")
                good = not r.ok
                print(f"{'ok  ' if good else 'FAIL'} {les.id} block {b.index} (exercise starter must not pass as given)")
                if good:
                    ok_n += 1
                else:
                    bad.append(f"{les.id} block {b.index} starter already passes")
    print(f"{ok_n}/{ok_n + len(bad)} blocks OK; FAILED: {bad or 'none'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
