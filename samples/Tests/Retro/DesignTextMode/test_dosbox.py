"""Generated programs compile with each toolchain and run in DOSBox-X; their screens (a B800 dump the program
writes itself: ``PROG /DUMP`` or ``/DUMPKEYS`` after typed keys) must equal the designer's rendering and the
run-time simulator. Uses the curated sample samples/Tests/Retro/DesignTUI_Contacts (FreeBASIC + user code) and
the same screens generated for Free Pascal, OpenWatcom C and 16-bit asm (JWasm or RAD IDE's own assembler).

A target is SKIPPED (not failed) when its compiler or DOSBox-X is not installed and cannot be downloaded
(offline). ``--no-download`` never downloads.

    python samples/Tests/Retro/DesignTextMode/test_dosbox.py [freebasic pascal c asm] [--no-download]
"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from radide.retro.design.textmode import project as tp                         # noqa: E402
from radide.retro.design.textmode.model import load_project_screens             # noqa: E402
from radide.retro.design.textmode.render import render                          # noqa: E402
from radide.retro.design.textmode.sim import Sim, alt                           # noqa: E402

SAMPLE = ROOT / "samples" / "Tests" / "Retro" / "DesignTUI_Contacts"
RESULTS = []
SKIPS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:700]}]"), flush=True)


def skip(name, why):
    SKIPS.append(name)
    print(f"SKIP {name}: {why}", flush=True)


def have_dosbox(download: bool) -> bool:
    from radide.retro.dos.toolchain import dosbox_exe
    return bool(dosbox_exe(download=download, log=lambda *_a: None))


def have_compiler(target: str, download: bool) -> bool:
    from radide.retro.dos import toolchain
    if target == "asm":
        return True                     # JWasm, else RAD IDE's own 8086 assembler
    key = {"freebasic": "freebasic", "pascal": "fpc", "c": "openwatcom"}[target]
    return toolchain.ensure_for(key, lambda *_a: None, download)


def sim_for(screens, target: str, keys, fire=None) -> Sim:
    sim = Sim(screens, basic=tp.TARGETS[target][2] in ("basic", "pascal"))
    sim.on_fire = fire
    sim.start()
    for k in keys:
        sim.handle_key(k)
    return sim


def contacts_fire(h, sm):
    """What the sample's BASIC handlers do (for the simulator)."""
    if h == "btnAdd_Click":
        name = sm.get_text(sm.ctl("txtName"))
        if not name:
            sm.msgbox("Contacts", "Type a name first.")
            return
        e = name + (("  " + sm.get_text(sm.ctl("txtPhone"))) if sm.get_text(sm.ctl("txtPhone")) else "")
        i = sm.ctl("lstContacts")
        sm.items[sm.first[i] + sm.count[i]] = e.encode("cp437")
        sm.count[i] += 1
        if sm.v[i] < 0:
            sm.v[i] = 0
        sm.face(i)
        sm.set_text(sm.ctl("txtName"), "")
        sm.set_text(sm.ctl("txtPhone"), "")
        p = sm.ctl("prgCount")
        sm.set_value(p, sm.v[p] + 1)
        sm.set_text(sm.ctl("lblInfo"), "Added: " + name)
    elif h == "mnuAbout_Click":
        sm.show_screen(2)
    elif h == "btnBack_Click":
        sm.show_screen(1)


def test_sample(work: Path, download: bool) -> None:
    folder = work / "Contacts"
    shutil.copytree(SAMPLE, folder)
    if not have_compiler("freebasic", download):
        skip("sample (FreeBASIC)", "FreeBASIC is not installed (offline?)")
        return
    t = time.time()
    log = []
    ok, exe = tp.build(folder, log.append, download)
    check(f"sample builds with FreeBASIC ({time.time() - t:.1f} s)", ok, "\n".join(log[-25:]))
    if not ok:
        return
    screens = load_project_screens(folder)
    check("regeneration kept the sample's user code", "TuiAddItem lstContacts, e$" in
          tp.read_dos_text(folder / "MAIN.BAS"))
    got = tp.capture(folder, exe.name, log=lambda *_a: None)
    check("sample: DOSBox-X screen = designer rendering", got is not None and got == render(screens[0]),
          got.diff(render(screens[0]))[:5] if got else "no SCREEN.BIN")
    cases = {
        "Alt+A with an empty name shows the message box": [alt("a")],
        "typing a contact and Alt+A adds it to the list": [ord(ch) for ch in "Ali"] + [9] +
                                                          [ord(ch) for ch in "123"] + [alt("a")],
        "Help > About shows the second screen": [alt("h"), 13],
        "About > OK returns to the main screen": [alt("h"), 13, 13],
        "F10 opens the File menu": [256 + 68],
    }
    for name, keys in cases.items():
        got = tp.capture(folder, exe.name, keys, log=lambda *_a: None)
        sim = sim_for(screens, "freebasic", keys, contacts_fire)
        d = sim.buf.diff(got) if got is not None else ["no SCREEN.BIN"]
        check(f"sample: {name}", not d, d[:4])
    got = tp.capture(folder, exe.name, [ord(ch) for ch in "Ali"] + [alt("a")], log=lambda *_a: None)
    txt = got.plain_text() if got else ""
    check("sample: the list shows the new contact and the label confirms it", "Ali" in txt and "Added: Ali" in txt,
          txt[:400])


def test_target(work: Path, target: str, download: bool) -> None:
    if not have_compiler(target, download):
        skip(f"{target}", "compiler not installed (offline?)")
        return
    folder = work / f"t_{target}"
    folder.mkdir()
    for f in ("Main.tform", "About.tform", "Splash.ans"):
        shutil.copy2(SAMPLE / f, folder / f)
    tp.create(folder, "TuiTest", target, sample=False)
    t = time.time()
    log = []
    ok, exe = tp.build(folder, log.append, download)
    check(f"{target}: builds ({time.time() - t:.1f} s)", ok, "\n".join(log[-25:]))
    if not ok:
        return
    screens = load_project_screens(folder)
    got = tp.capture(folder, exe.name, log=lambda *_a: None)
    ref = Sim(screens, basic=tp.TARGETS[target][2] in ("basic", "pascal")).start().buf
    check(f"{target}: DOSBox-X screen = designer rendering", got is not None and got == ref,
          got.diff(ref)[:5] if got else "no SCREEN.BIN")
    for name, keys in {"tab + typing": [9, ord("x"), ord("y"), 9, 9, 32],
                       "list + options": [alt("t"), alt("w"), alt("f")],
                       "menu navigation": [256 + 68, 256 + 77, 256 + 75, 256 + 80],
                       "Esc in a menu closes it": [alt("f"), 27]}.items():
        got = tp.capture(folder, exe.name, keys, log=lambda *_a: None)
        sim = sim_for(screens, target, keys)
        d = sim.buf.diff(got) if got is not None else ["no SCREEN.BIN"]
        check(f"{target}: {name}", not d, d[:4])


def test_qbasic_dialect(work: Path, download: bool) -> None:
    """The QBasic 1.1 dialect (no mouse, no COMMAND$ - so no screen dump) still builds with FreeBASIC."""
    if not have_compiler("freebasic", download):
        return
    folder = work / "qbasic11"
    tp.create(folder, "Q11", "qbasic")
    log = []
    ok, _exe = tp.build(folder, log.append, download)
    check("QBasic 1.1 dialect builds with FreeBASIC", ok, "\n".join(log[-15:]))


def test_sizes(work: Path, download: bool) -> None:
    """80x43 and 80x50 screens (EGA / VGA 8x8 font) in the C and asm programs."""
    for target in ("c", "asm"):
        if not have_compiler(target, download):
            continue
        for rows in (43, 50):
            folder = work / f"rows_{target}{rows}"
            tp.create(folder, "Big", target, rows=rows)
            ok, exe = tp.build(folder, lambda *_a: None, download)
            if not ok:
                check(f"{target}: 80x{rows} builds", False)
                continue
            got = tp.capture(folder, exe.name, log=lambda *_a: None)
            ref = Sim(load_project_screens(folder)).start().buf
            check(f"{target}: 80x{rows} screen in DOSBox-X = designer", got is not None and got == ref,
                  got.diff(ref)[:4] if got else "no SCREEN.BIN")


def test_splash_emulator() -> None:
    """The splash art (before the first screen) in the asm program, run in RAD IDE's 8086 emulator."""
    from radide.emu8086.assembler import assemble
    from radide.emu8086.machine import Machine
    from radide.retro.design.textmode.ansi import load_art
    from radide.retro.design.textmode.buffer import CellBuffer
    from radide.retro.design.textmode.codegen import asm
    screens = load_project_screens(SAMPLE)
    screens[0].props["splash_seconds"] = 0
    src, _w = asm.generate(screens)
    prog = assemble(src, "main.asm")
    m = Machine()
    m.load(prog)
    m.record_history = False
    m.run(3_000_000)
    got = CellBuffer.from_bin(bytes(m.mem[0xB8000:0xB8000 + 4000]), 80)
    check("splash art is shown first (asm, 8086 emulator)", got == load_art(SAMPLE / "Splash.ans"),
          got.diff(load_art(SAMPLE / "Splash.ans"))[:4])
    m.push_key(0x39, 32)
    m.run(3_000_000)
    got = CellBuffer.from_bin(bytes(m.mem[0xB8000:0xB8000 + 4000]), 80)
    check("a key after the splash shows the startup screen", got == render(screens[0]), got.diff(render(screens[0]))[:4])


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    download = "--no-download" not in sys.argv
    targets = args or ["freebasic", "pascal", "c", "asm"]
    work = Path(tempfile.mkdtemp(prefix="tui-dosbox-"))
    try:
        test_splash_emulator()
        if not have_dosbox(download):
            skip("DOSBox-X runs", "DOSBox-X is not installed (offline?)")
        else:
            test_sample(work, download)
            for t in targets:
                test_target(work, t, download)
            test_sizes(work, download)
            test_qbasic_dialect(work, download)
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
