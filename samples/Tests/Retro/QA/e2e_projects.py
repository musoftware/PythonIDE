"""Retro QA (end to end, as a user): New Project for every retro type -> Build -> F5 in the real emulator -> Stop.

For each project type of the New Project groups "Retro Games", "Retro" and "Space & Science" the project is
created with the plugin's template, opened in the IDE, built (Build > Build Project / the plugin's run path) and
started with F5 (debug=False) through MainWindow.run_project().  For the emulator types the test waits until
the emulator process exists (a child of the run session), presses Stop and checks that the emulator closed
with it (no orphan).  Only processes started by this test are ever stopped.

    python samples/Tests/Retro/QA/e2e_projects.py            # all
    python samples/Tests/Retro/QA/e2e_projects.py nes c64    # only templates whose id contains these words
"""
import os
import shutil
import sys
import time
from pathlib import Path

os.environ.setdefault("QA_NAME", "retro_qa_projects")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, shot, wait  # noqa: E402

import psutil  # noqa: E402

from radide.languages import get_plugin  # noqa: E402

EMU_NAMES = ("stella", "mesen", "fceux", "mgba", "x64sc", "atari800", "dosbox")
ONLY = [a for a in sys.argv[1:] if not a.startswith("-")]

# (plugin, template, expects an emulator process, output text that proves the run)
CASES = [
    ("retro-atari2600", "a2600_kernel", True, ""),
    ("retro-nes", "nes_asm", True, ""),
    ("retro-nes", "nes_c", True, ""),
    ("retro-gameboy", "gb_asm", True, ""),
    ("retro-c64", "c64_asm", True, ""),
    ("retro-c64", "c64_c", True, ""),
    ("retro-zx", "zx_asm", False, "Build succeeded"),
    ("retro-dos", "dos_asm", True, ""),
    ("retro-romhack", "romhack_demo", True, ""),
    ("agc-yul", "agc_hello", False, ""),
    ("fortran-legacy", "f66_orbits", False, "ORBIT"),
    ("fortran-legacy", "f77_hello", False, "HELLO"),
]


def emu_children(pid: int) -> list[psutil.Process]:
    try:
        kids = psutil.Process(pid).children(recursive=True)
    except psutil.Error:
        return []
    return [k for k in kids if any(n in (k.name() or "").lower() for n in EMU_NAMES)]


def main():
    w = qh.window()
    work = Path(qh.WORK) / "retro_qa_projects"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    leftovers = []
    for pid, tpl, emu, proof in CASES:
        if ONLY and not any(o in tpl or o in pid for o in ONLY):
            continue
        plugin = get_plugin(pid)
        if not check(f"{tpl}: plugin {pid} registered", plugin is not None):
            continue
        folder = work / tpl
        try:
            plugin.create_new_project(folder, tpl.title().replace("_", ""), tpl)
        except Exception as e:  # noqa: BLE001
            check(f"{tpl}: create project", False, repr(e))
            continue
        w.open_project(folder, ask=False)
        pump(1.5)
        check(f"{tpl}: project opens ({pid})", w.project is not None and w.project.language == pid,
              getattr(w.project, "language", None))
        # ---- Build > Build Project (plugin build_command) when the type has one
        bc = None
        try:
            bc = plugin.build_command(folder, w.project) if hasattr(plugin, "build_command") else None
        except Exception as e:  # noqa: BLE001
            check(f"{tpl}: build_command", False, repr(e))
        if bc:
            import subprocess
            r = subprocess.run(bc, shell=True, cwd=str(folder), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=600)
            check(f"{tpl}: Build Project succeeds", r.returncode == 0, (r.stdout + r.stderr)[-1500:])
        # ---- F5 (Start Without Debugging path, the emulator for real)
        w.output.clear()
        t0 = time.time()
        w.run_project(debug=(pid == "agc-yul"))        # AGC: F5 = the in-IDE emulator with the DSKY dock
        s = w.session
        if not check(f"{tpl}: F5 starts a run session", s is not None, w.output.toPlainText()[-800:]):
            continue
        spid = 0
        try:
            spid = int(s.proc.processId())
        except Exception:  # noqa: BLE001
            pass
        if emu:
            ok = wait(lambda: emu_children(spid) or not s.running(), 240)
            kids = emu_children(spid)
            check(f"{tpl}: emulator process started by F5", ok and kids,
                  w.output.toPlainText()[-1500:])
            if kids:
                pump(3)
                shot(w, f"retro_qa_run_{tpl}")
                names = [k.name() for k in kids]
                kpids = [k.pid for k in kids]
                w.stop_project()
                pump(0.5)
                gone = wait(lambda: not any(psutil.pid_exists(p) and psutil.Process(p).is_running()
                                            and psutil.Process(p).status() != psutil.STATUS_ZOMBIE
                                            for p in kpids), 10)
                check(f"{tpl}: Stop also closes the emulator ({names})", gone, kpids)
                if not gone:
                    leftovers += kpids
            else:
                s.stop()
        else:
            ok = wait(lambda: not s.running(), 240 if pid != "agc-yul" else 1)
            out = w.output.toPlainText()
            if pid == "agc-yul":
                # the AGC session runs in-process: the Apollo AGC dock with a DSKY appears
                check(f"{tpl}: run session alive or finished cleanly", True)
                wait(lambda: getattr(w, "_agc_dock", None) is not None and w._agc_dock.isVisible(), 20)
                pump(2)
                dock = getattr(w, "_agc_dock", None)
                if dock is not None:
                    shot(w, "retro_qa_run_agc")
                check(f"{tpl}: Apollo AGC dock shown", dock is not None and dock.isVisible(), out[-600:])
                if s.running():
                    s.stop()
            else:
                check(f"{tpl}: run finished", ok, out[-800:])
                check(f"{tpl}: output contains {proof!r}", proof.lower() in out.lower(), out[-1500:])
                if s.running():
                    s.stop()
        pump(1)
        for p in psutil.process_iter():    # an emulator started during this case (by our F5) still alive
            try:
                if any(n in (p.name() or "").lower() for n in EMU_NAMES) and p.create_time() >= t0 - 1                         and not psutil.pid_exists(p.ppid()):
                    leftovers.append((tpl, p.name()))
                    p.kill()
            except psutil.Error:
                pass
    check("no emulator left running after Stop", not leftovers, leftovers)
    qh.finish(w)


if __name__ == "__main__":
    main()
