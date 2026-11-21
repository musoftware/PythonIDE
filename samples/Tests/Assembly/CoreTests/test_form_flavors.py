"""Windows Forms (GUI Bridge) in every assembly flavor: NASM x64, NASM x86 (32-bit), FASM x64, GNU as x64 in
AT&T and in Intel syntax.

For each template: New Project -> build (python -m radide.asm.build) -> drive the program over the GUI Bridge
protocol (Load, two clicks, the INPUT / MSGBOX round trip, an event without handler) -> run it in the real
bridge host window (radide.runtimes.bridge), click btnAdd and read the controls back. Then F5-style checks: the
line table of the debug build (gdb `break Form1.<ext>:<line of btnAdd_Click>` resolves to the form file).

    python samples/Tests/Assembly/CoreTests/test_form_flavors.py [template ...]
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from radide.asm.build import Builder, read_diagnostics          # noqa: E402
from radide.asm.templates import BY_ID                           # noqa: E402
from radide.languages import get_plugin                           # noqa: E402

WORK = Path(tempfile.gettempdir()) / "radide-asm-tests" / "flavors"
FLAVORS = ["nasm_forms", "nasm_forms_x86", "fasm_forms", "gas_forms", "gas_forms_intel"]
results: list[tuple[str, bool, str]] = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)


def protocol(exe: Path, folder: Path) -> list[str]:
    p = subprocess.Popen([str(exe)], cwd=folder, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    log: list[str] = []

    def event(line):
        p.stdin.write(line + "\n")
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
            if out.startswith("GET txtNumber Text"):
                p.stdin.write("41\n")
                p.stdin.flush()
            elif out.startswith("INPUT "):
                p.stdin.write("Ali\n")
                p.stdin.flush()
            elif out.startswith("MSGBOX "):
                p.stdin.write("1\n")
                p.stdin.flush()
        log.append(f">> {line}")
        log.extend(f"<< {g}" for g in got)
        return got

    try:
        g1 = event("EVENT Form1 Load")
        g2 = event("EVENT btnAdd Click")
        g3 = event("EVENT btnAdd Click")
        g4 = event("EVENT btnHello Click")
        g5 = event("EVENT lblMessage Click")
        p.stdin.write("QUIT\n")
        p.stdin.flush()
        p.wait(timeout=10)
    finally:
        if p.poll() is None:
            p.kill()
    return [g1, g2, g3, g4, g5, log]


def host_window(folder: Path, plugin) -> tuple[bool, str]:
    from radide.model import Project
    from radide.runtimes.bridge import BridgeRuntime
    project = Project.load(folder)
    handlers = set(plugin.handlers_in_project(folder, project))
    rt = BridgeRuntime(folder, [str(folder / "_radapp.exe")], handlers)
    rt.load()
    rt.start_program()
    vf = rt.forms["form1"]
    rt.startup_form = vf
    vf.load()
    vf.vb_call("show", [])
    rt.root.update()

    def text(name):
        return str(vf.vb_get(name.lower()).vb_get("text"))

    first = text("lblMessage")
    rt.event("btnAdd", "Click")
    rt.root.update()
    got = (text("txtNumber"), text("lblClicks"), text("lblMessage"))
    if rt.proc and rt.proc.poll() is None:          # rt.end() would also end this test process
        rt.send("QUIT")
        try:
            rt.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            rt.proc.kill()
    try:
        rt.root.destroy()
    except Exception:  # noqa: BLE001
        pass
    ok = first.startswith("Hello from") and got == ("42", "1", "The assembly handler added 1.")
    return ok, f"Load: {first!r}, after click: {got}"


def gdb_break(folder: Path, src: str) -> tuple[bool, str]:
    from radide.asm import toolchain as tc
    gdb = tc.mingw("gdb")
    if not gdb:
        return False, "gdb not found"
    lines = (folder / src).read_text(encoding="utf-8").splitlines()
    ln = next(i + 1 for i, l in enumerate(lines) if "rad_get_int txtNumber" in l)
    r = subprocess.run([gdb, "-batch", "-ex", f"break {src}:{ln}", str(folder / "_radapp.exe")], capture_output=True,
                       text=True, errors="replace", timeout=60)
    out = r.stdout + r.stderr
    ok = f"file {src}, line {ln}." in out
    return ok, next((l for l in out.splitlines() if l.startswith("Breakpoint")), out.strip()[-200:])


def main():
    only = sys.argv[1:] or FLAVORS
    for tid in only:
        t = BY_ID[tid]
        folder = WORK / tid
        shutil.rmtree(folder, ignore_errors=True)
        plugin = get_plugin(t.plugin)
        plugin.create_new_project(folder, "Forms" + tid.split("_")[0].title(), tid)
        logs: list[str] = []
        ok = Builder(folder, log=logs.append).build()
        check(f"{tid}: build", ok, "" if ok else "\n".join(logs[-15:]) + str(read_diagnostics(folder)))
        if not ok:
            continue
        exe = folder / "_radapp.exe"
        g1, g2, g3, g4, g5, log = protocol(exe, folder)
        check(f"{tid}: Load sets lblMessage", any(x.startswith("SET lblMessage Text Hello from") for x in g1),
              g1[0] if g1 else "no answer")
        check(f"{tid}: btnAdd_Click (41 -> 42, clicks 1)", "SET txtNumber Text 42" in g2 and "SET lblClicks Text 1" in g2,
              " | ".join(g2))
        check(f"{tid}: second click (clicks 2)", "SET lblClicks Text 2" in g3, " | ".join(g3))
        check(f"{tid}: INPUT / MSGBOX round trip", "SET lblMessage Text Ali" in g4 and any(x.startswith("MSGBOX ") for x in g4),
              " | ".join(g4))
        check(f"{tid}: event without handler", g5 == ["DONE"], " | ".join(g5))
        ok2, detail = host_window(folder, plugin)
        check(f"{tid}: bridge host window click", ok2, detail)
        src = plugin.code_file("Form1")
        ok3, detail = gdb_break(folder, src)
        check(f"{tid}: gdb breakpoint by line in {src}", ok3, detail)
    passed = sum(1 for r in results if r[1])
    print(f"\n{passed} / {len(results)} checks passed")
    print("RESULT", "OK" if passed == len(results) else "FAIL")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
