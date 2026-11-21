"""Mouse clicks in the generated DOS programs, in real DOSBox-X: RADMOUSE.COM (radide/retro/dos/helpers_src) stands
in for the INT 33h mouse driver and clicks text cells, then saves the screen (``dosbox.capture_clicks``). For every
target (FreeBASIC, Free Pascal, OpenWatcom C, 16-bit asm) the sample project of New Project > DOS Text-Mode Forms
App is built and clicked:

* the OK button (its Click handler changes the label),
* the File menu title, then its About... item (the handler shows a message box),
* the Cancel button's neighbour - a click on the window's empty area changes nothing;

each screen must equal the run-time simulator (sim.Sim.click) after the same clicks.

    python samples/Tests/Retro/DesignTextMode/test_mouse.py [freebasic pascal c asm]
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from radide.retro.design.textmode import project as tp                         # noqa: E402
from radide.retro.design.textmode.buffer import CellBuffer                      # noqa: E402
from radide.retro.design.textmode.model import load_project_screens             # noqa: E402
from radide.retro.design.textmode.sim import Sim                                # noqa: E402
from radide.retro.dos import dosbox, toolchain                                  # noqa: E402

RESULTS, SKIPS = [], []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:900]}]"), flush=True)


def skip(name, why):
    SKIPS.append(name)
    print(f"SKIP {name}: {why}", flush=True)


def sample_fire(h, sm):
    """What the sample's handlers do (project.SAMPLE_CODE)."""
    if h == "Button1_Click":
        sm.set_text(sm.ctl("Label1"), "You pressed OK!")
    elif h == "mnuAbout_Click":
        sm.msgbox("About", "Made with RAD IDE - Text-Mode Designer")


def find(buf: CellBuffer, text: str) -> tuple[int, int]:
    for r, line in enumerate(buf.plain_text().split("\n")):
        c = line.find(text)
        if c >= 0:
            return c, r
    raise LookupError(text)


def sim_after(screens, target: str, clicks) -> Sim:
    sim = Sim(screens, basic=tp.TARGETS[target][2] in ("basic", "pascal"))
    sim.on_fire = sample_fire
    sim.start()
    for x, y in clicks:
        sim.click(x, y)
    return sim


def test_target(work: Path, target: str) -> None:
    key = {"freebasic": "freebasic", "pascal": "fpc", "c": "openwatcom", "asm": ""}[target]
    if key and not toolchain.ensure_for(key, lambda *_a: None, False):
        skip(target, f"{key} is not installed")
        return
    folder = work / f"m_{target}"
    tp.create(folder, "MouseT", target)
    ok, exe = tp.build(folder, log=lambda *_a: None, download=False)
    check(f"{target}: sample builds", ok and exe is not None)
    if not ok:
        return
    screens = load_project_screens(folder)
    scr = screens[0]
    ok_btn = next(c for c in scr.controls if c.name == "Button1")
    win = next(c for c in scr.controls if c.type == "Window")
    probe = Sim(screens).start()
    file_xy = find(probe.buf, "File")
    probe.click(*file_xy)
    about_xy = find(probe.buf, "About...")
    cases = {
        "click OK -> its Click handler changes the label": [(ok_btn.x + 2, ok_btn.y)],
        "click File, then About... -> message box": [file_xy, about_xy],
        "click on the window's empty area changes nothing": [(win.x + 3, win.y + 6)],
    }
    for name, clicks in cases.items():
        run = dosbox.DosRun(mounts=[("C", folder)], cycles="max")
        data = dosbox.capture_clicks(run, folder, exe.name, clicks, timeout=30, log=lambda *_a: None)
        want = sim_after(screens, target, clicks).buf
        got = CellBuffer.from_bin(data, want.cols) if data else None
        diff = want.diff(got) if got is not None else ["no _MOUSE.BIN (the program did not poll the mouse)"]
        check(f"{target}: {name}", not diff, (diff[:4], got.plain_text()[:1200] if got else ""))


def main() -> None:
    targets = [a for a in sys.argv[1:] if not a.startswith("--")] or ["freebasic", "pascal", "c", "asm"]
    if not toolchain.dosbox_exe(download=False, log=lambda *_a: None):
        skip("mouse clicks", "DOSBox-X is not installed")
    else:
        work = Path(tempfile.mkdtemp(prefix="tui-mouse-"))
        try:
            for t in targets:
                test_target(work, t)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            check("test crashed", False, e)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    ok = sum(1 for _n, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed; skipped: {SKIPS or 'none'}; "
          f"FAILED: {[n for n, c in RESULTS if not c] or 'none'}", flush=True)
    os._exit(0 if ok == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
