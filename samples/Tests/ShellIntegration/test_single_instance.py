"""Single instance with real processes (si_child.py): a second launch hands its path to the running IDE
and exits; the first one opens it (text file at a line, project, form, folder; two launches at once);
--new-window opens a separate window.

    .venv\\Scripts\\python samples\\Tests\\ShellIntegration\\test_single_instance.py [scratch folder]

Uses the RADIDE-TEST settings and its own instance name, so a running RAD IDE is never contacted."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PY = str(REPO / ".venv" / "Scripts" / "python.exe")
SCRATCH = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "radide-si-test") / "si"
OUT = SCRATCH / "out"
results: list[tuple[str, bool, str]] = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))


def wait_file(p: Path, timeout=120.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                pass
        time.sleep(0.2)
    return None


def secondary(tag: str, *args: str):
    t0 = time.monotonic()
    p = subprocess.run([PY, str(HERE / "si_child.py"), "secondary", str(OUT), tag, *args], env=ENV,
                       capture_output=True, text=True, timeout=200)
    return p, wait_file(OUT / f"secondary_{tag}.json", 5), time.monotonic() - t0


def main():
    global ENV
    shutil.rmtree(SCRATCH, ignore_errors=True)
    OUT.mkdir(parents=True)
    proj = SCRATCH / "HelloSetup"
    shutil.copytree(REPO / "samples" / "Tests" / "Installer" / "HelloSetup", proj,
                    ignore=shutil.ignore_patterns("tests", "__pycache__", ".radide*", "dist", "build"))
    txt = SCRATCH / "hello.txt"
    txt.write_text("line 1\nline 2\nline 3 - the target\nline 4\n", encoding="utf-8")
    other = SCRATCH / "notes.md"
    other.write_text("# Notes\n", encoding="utf-8")
    third = SCRATCH / "data.json"
    third.write_text("{}\n", encoding="utf-8")
    folder = SCRATCH / "PlainFolder"
    folder.mkdir()
    (folder / "readme.txt").write_text("plain folder\n", encoding="utf-8")
    ENV = dict(os.environ, RADIDE_INSTANCE_NAME=f"radide-test-si-{os.getpid()}", QT_QPA_PLATFORM="offscreen")

    plog = open(OUT / "primary.log", "w", encoding="utf-8", errors="replace")  # noqa: SIM115 - never a PIPE:
    prim = subprocess.Popen([PY, str(HERE / "si_child.py"), "primary", str(OUT)], env=ENV,   # QtWebEngine's log
                            stdout=plog, stderr=subprocess.STDOUT)                         # would fill it and block
    try:
        ready = wait_file(OUT / "ready.json", 150)
        check("first instance listens", bool(ready and ready["ok"]), str(ready))

        p, rep, secs = secondary("txt", str(txt), "--line", "3")
        h = wait_file(OUT / "handled_1.json", 60)
        check(f"second launch hands over and exits without a window ({secs:.1f}s)",
              p.returncode == 0 and rep and rep["code"] == 0 and not rep["window"], p.stdout[-500:] + p.stderr[-800:])
        check("first instance opened the text file at line 3",
              bool(h and "hello.txt" in [t.rstrip("*") for t in h["tabs"]] and h["line"] == 3
                   and h["msg"]["paths"] == [str(txt.resolve())] and h["msg"]["line"] == 3), str(h)[:400])

        p, rep, _ = secondary("proj", str(proj / "project.radproj"))
        h = wait_file(OUT / "handled_2.json", 60)
        check("project file -> open_project", bool(rep and not rep["window"] and h and h["project"]
                                                     and any(t.startswith("Form1") for t in h["tabs"])), str(h)[:400])

        p, rep, _ = secondary("form", str(proj / "Form1.form"))
        h = wait_file(OUT / "handled_3.json", 60)
        check("form -> its designer", bool(h and h["project"] and h["current"].startswith("Form1")), str(h)[:400])

        p, rep, _ = secondary("folder", str(folder))
        h = wait_file(OUT / "handled_4.json", 60)
        check("plain folder -> folder workspace", bool(rep and not rep["window"] and h and h["project"] == "PlainFolder"),
              str(h)[:400])

        # two launches at the same time (Explorer with several files selected)
        args = [[PY, str(HERE / "si_child.py"), "secondary", str(OUT), tag, str(f)]
                for tag, f in (("a", other), ("b", third))]
        procs = [subprocess.Popen(a, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for a in args]
        codes = [pr.wait(200) for pr in procs]
        h5, h6 = wait_file(OUT / "handled_5.json", 60), wait_file(OUT / "handled_6.json", 60)
        got = {Path(x).name for hh in (h5, h6) if hh for x in hh["msg"]["paths"]}
        tabs = [Path(t.rstrip("*")).name for t in (h6 or {}).get("tabs", [])]     # outside the workspace: full path
        check("two simultaneous launches both handed over and opened", codes == [0, 0] and got == {"notes.md", "data.json"}
              and "notes.md" in tabs and "data.json" in tabs, f"{codes} {got} {tabs}")

        p, rep, _ = secondary("new", str(txt), "--new-window")
        win = wait_file(OUT / "secondary_new_window.json", 5)
        check("--new-window opens its own window with the file", bool(rep and rep["window"] and win
                                                                      and "hello.txt" in win["tabs"]), str(win))
        check("--new-window did not hand over", not (OUT / "handled_7.json").exists())
    finally:
        (OUT / "quit").write_text("1")
        try:
            prim.wait(60)
        except subprocess.TimeoutExpired:
            prim.kill()
        plog.close()
        log = "\n".join(x for x in (OUT / "primary.log").read_text(encoding="utf-8", errors="replace").splitlines()
                        if "ERROR:" not in x)
    check("first instance exits cleanly", prim.returncode == 0 and (OUT / "primary_exit.json").exists(), log[-1500:])
    from PyQt6.QtCore import QSettings
    for app in ("RAD IDE", "RADIDE-TEST"):
        QSettings("RADIDE-TEST", app).clear()
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


ENV: dict = {}
if __name__ == "__main__":
    sys.exit(main())
