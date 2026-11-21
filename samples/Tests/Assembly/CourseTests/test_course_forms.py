"""The GUI Bridge forms of the Assembly course (lesson 12) really work: every ``asm form run`` / ``solution`` block
is turned into its "جرّبه" project, built with the IDE's build (python -m radide.asm.build) and driven over the
bridge's stdin/stdout protocol (EVENT -> SET / GET / CALL ... DONE), like samples/Tests/Assembly/CoreTests.

    python samples/Tests/Assembly/CourseTests/test_course_forms.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from radide import tutorials as T  # noqa: E402

# block index in lesson 12 -> (answers to GET / INPUT / MSGBOX, [(event, lines that must appear)])
CASES = {
    "hello": ({}, [("EVENT btnHello Click", ["SET lblOut Text Hello from x64 assembly!"])]),
    "calc": ({"GET txtA Text": "6", "GET txtB Text": "7"},
             [("EVENT btnAdd Click", ["SET lblResult Text 13"]), ("EVENT btnMul Click", ["SET lblResult Text 42"])]),
    "log": ({}, [("EVENT Form1 Load", ["SET lblCount Text No clicks yet"]),
                 ("EVENT btnClick Click", ["SET lblCount Text 1", "AddItem"]),
                 ("EVENT btnClick Click", ["SET lblCount Text 2"]),
                 ("EVENT btnClear Click", ["SET lblCount Text Cleared", "Clear"])]),
    "convert": ({"GET txtC Text": "37"}, [("EVENT btnConvert Click", ["SET lblF Text 98"])]),
}


def drive(exe: Path, answers: dict, script: list) -> list:
    p = subprocess.Popen([str(exe)], cwd=exe.parent, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                         bufsize=1)
    problems = []
    try:
        for ev, want in script:
            p.stdin.write(ev + "\n")
            p.stdin.flush()
            got = []
            while True:
                out = p.stdout.readline().rstrip("\r\n")
                if not out:
                    if p.poll() is not None:
                        break
                    continue
                got.append(out)
                if out == "DONE":
                    break
                if out in answers:
                    p.stdin.write(answers[out] + "\n")
                    p.stdin.flush()
                elif out.startswith(("GET ", "INPUT ", "MSGBOX ", "CALL ")):
                    p.stdin.write("\n")                 # an empty answer for anything else that waits
                    p.stdin.flush()
            for w in want:
                if not any(w in g for g in got):
                    problems.append(f"{ev}: expected '{w}', got {got}")
        p.stdin.write("QUIT\n")
        p.stdin.flush()
        p.wait(timeout=5)
    finally:
        if p.poll() is None:
            p.kill()
    return problems


def main() -> int:
    les = T.course("assembly").lesson("12-gui-form")
    blocks = [b for b in les.blocks() if b.lang == "asm" and b.gui and b.role in ("run", "solution")]
    names = ["hello", "calc", "log", "convert"]
    work = Path(tempfile.mkdtemp(prefix="asmforms-"))
    failed = 0
    try:
        for name, b in zip(names, blocks):
            d = work / name
            T.make_project(b, d, name=name)
            r = subprocess.run([sys.executable, "-m", "radide.asm.build", str(d)], cwd=REPO, capture_output=True,
                               text=True)
            if r.returncode or not (d / "_radapp.exe").exists():
                print(f"FAIL {name}: build\n{r.stdout[-800:]}{r.stderr[-800:]}")
                failed += 1
                continue
            answers, script = CASES[name]
            problems = drive(d / "_radapp.exe", answers, script)
            print(("ok   " if not problems else "FAIL ") + f"{name} (lesson 12 block {b.index})")
            for pr in problems:
                print("    ", pr)
            failed += bool(problems)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\n{len(names) - failed}/{len(names)} forms OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
