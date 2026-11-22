# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Example projects of the low-level languages: Assembly (NASM / FASM / MASM / GNU as / 8086 emulator), DOS (QBasic,
Pascal, C, 16-bit assembly, batch, Text-Mode Forms) and retro consoles (Atari 2600, NES, Game Boy, C64, ZX Spectrum).

Run through the runner:   .venv\\Scripts\\python samples\\Tests\\Examples\\test_examples_scripting.py --group lowlevel

How each kind is checked (only processes this test starts are closed):
* Assembly forms   - built with the IDE's build (python -m radide.asm.build), run in the IDE's bridge host in
                     process (exlib.BridgeDriver: the form is a real window of this process, found with EnumWindows)
                     and driven through its controls; console programs run through the F5 run spec with stdin.
* 8086 emulator    - radide.emu8086 (assembler + Machine) headless with typed keys.
* DOS              - the DOS build (radide.retro.dos.build.Builder: FreeBASIC / Free Pascal / OpenWatcom / JWasm),
                     then DOSBox-X without a window (dosbox.capture_text: keys stuffed with RADKEYS, output +
                     text screen saved, mode 13h frames by RADCAP); Text-Mode Forms through textmode.project.capture.
* Retro            - radide.retro.dev.build.Builder; NES / Game Boy run headless in Mesen 2's test runner
                     (mesenshot: frames written by the emulator itself, with and without joypad input), the C64 in
                     VICE (minimized, warp) driven through VICE's binary monitor (keyboard feed + memory reads),
                     the Atari 2600 in Stella (its window must appear), the ZX Spectrum .tap is checked by format.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exlib  # noqa: E402


# ============================================================================ shared helpers
def _asm_env() -> None:
    """What the IDE's run spec adds for assembly projects: radide importable, MinGW gcc on PATH."""
    os.environ["PYTHONPATH"] = str(exlib.ROOT)
    from radide.asm import toolchain as tc
    gcc = tc.mingw("gcc")
    if gcc and os.path.dirname(gcc) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = os.path.dirname(gcc) + os.pathsep + os.environ.get("PATH", "")


def _open_check(folder: Path, res, forms: bool = True) -> None:
    from radide.languages import get_plugin
    from radide.model import Project
    p = Project.load(folder)
    get_plugin(p.language)
    missing = [m for m in p.modules if not (folder / m).exists()]
    if forms and p.forms:
        ok, note = exlib.designer_check(folder)
        res.step("open", ok and not missing, note + (f" missing modules: {missing}" if missing else ""))
    else:
        res.step("open", not missing, f"{p.language}, modules {p.modules}" + (f" missing {missing}" if missing else ""))


def _publish(src: Path, res, opts, **kw) -> dict | None:
    if not opts.get("publish"):
        res.step("publish", "skipped")
        return None
    d = exlib.temp_copy(src, "pub")
    r = exlib.publish(d, log_file=exlib.SCRATCH / "logs" / f"{src.name}_publish.log", **kw)
    if r.get("ok"):
        res["size"] = f"{r['size_mb']} MB ({r['kind']}, python inside: {'yes' if r['python_inside'] else 'no'})"
    res.step("publish", bool(r.get("ok")), r.get("error", "") or f"{r.get('exe')} {r.get('size_mb')} MB")
    return r


# ============================================================================ Assembly
def asm_form_test(script):
    def test(src: Path, res, opts):
        _open_check(src, res)
        _asm_env()
        d = exlib.temp_copy(src, "run")
        try:
            b = exlib.BridgeDriver(d)
        except RuntimeError as e:
            res.step("build", False, str(e)[-300:])
            return
        res.step("build", (d / "_radapp.exe").is_file(), f"_radapp.exe {exlib.mb((d / '_radapp.exe').stat().st_size)} MB")
        try:
            win = b.window(b.form(b.rt.project.startup).model.props.get("Text", ""))
            ok, note = script(b)
            res.step("run", bool(win) and ok, f"window {win[1] if win else None!r}; {note}")
        finally:
            b.close()
        r = _publish(src, res, opts)
        if r and r.get("ok"):                   # the published program must show its own window too
            title = b.form(b.rt.project.startup).model.props.get("Text", "")
            p = subprocess.Popen([str(Path(r["dist"]) / r["exe"])], cwd=r["dist"])
            try:
                w = exlib.wait_window(p, title, 60)
            finally:
                exlib.stop_tree(p)
            res["notes"].append(f"published exe window: {w[1] if w else None!r}")
            if not w:
                res["publish"] = "FAIL"
    return test


def nasm_calculator(b):
    out = []
    b.set("txtA", "7")
    b.set("txtB", "3")
    for btn, want in (("btnAdd", "10"), ("btnSub", "4"), ("btnMul", "21"), ("btnDiv", "2"), ("btnMod", "1"),
                      ("btnPow", "343")):
        b.click(btn)
        out.append(b.get("lblResult") == f"Result: {want}")
    hist = b.list_items("lstHistory")
    b.set("txtB", "0")
    b.click("btnDiv")
    zero = any("zero" in m for m in b.msgs)
    b.click("mnuFileClear")
    cleared = b.list_items("lstHistory") == []
    ok = all(out) and hist[-1] == "7 ^ 3 = 343" and len(hist) == 6 and zero and cleared
    return ok, f"results {out}, history {hist}, divide-by-zero MsgBox {zero}, cleared {cleared}"


def fasm_temperature(b):
    rows = []
    for v, btn, want in (("100", "btnToF", "100 C = 212 F"), ("-40", "btnToF", "-40 C = -40 F"),
                         ("98", "btnToC", "98 F = 37 C")):
        b.set("txtValue", v)
        b.click(btn)
        rows.append((b.get("lblOut"), b.get("barHeat", "Value")))
    ok = [r[0] for r in rows] == ["100 C = 212 F", "-40 C = -40 F", "98 F = 37 C"] and rows[0][1] == "87" \
        and rows[1][1] == "0"
    return ok, f"{rows}; feel: {b.get('lblFeel')!r}"


def gas_guess(b):
    b.set("txtGuess", "500")
    b.click("btnGuess")
    range_msg = bool(b.msgs)
    lo, hi, tries = 1, 100, 0
    hint = ""
    for _ in range(8):
        g = (lo + hi) // 2
        b.set("txtGuess", str(g))
        b.click("btnGuess")
        tries += 1
        hint = b.get("lblHint")
        if "Correct" in hint:
            break
        if "high" in hint:
            hi = g - 1
        else:
            lo = g + 1
    won = "Correct" in hint and b.get("lblTries") == str(tries) and len(b.list_items("lstGuesses")) == tries
    disabled = str(b.get("btnGuess", "Enabled")).lower() in ("false", "0")
    b.click("btnNew")
    reset = b.list_items("lstGuesses") == [] and b.get("lblTries") == "0"
    return range_msg and won and disabled and reset, \
        f"binary search won in {tries} tries ({hint!r}); out-of-range MsgBox {range_msg}; disabled {disabled}; " \
        f"new game resets {reset}"


def asm_console_test(stdin_text: str, expect: list[str]):
    def test(src: Path, res, opts):
        _open_check(src, res, forms=False)
        _asm_env()
        d = exlib.temp_copy(src, "run")
        r = subprocess.run([sys.executable, "-m", "radide.asm.build", str(d)], cwd=str(exlib.ROOT),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        exe = d / "_radapp.exe"
        res.step("build", r.returncode == 0 and exe.is_file(), (r.stdout + r.stderr).strip().splitlines()[-1])
        if not exe.is_file():
            return
        p = exlib.run_spec_proc(d, stdin=subprocess.PIPE)          # the F5 run spec (bridge console mode)
        try:
            out, _ = p.communicate(stdin_text, timeout=120)
        except subprocess.TimeoutExpired:
            exlib.stop_tree(p)
            out = ""
        missing = [e for e in expect if e not in out]
        res.step("run", not missing, f"missing {missing}" if missing else f"{len(out.splitlines())} lines, all expected")
        _publish(src, res, opts)
    return test


def emu8086_test(src: Path, res, opts):
    _open_check(src, res, forms=False)
    from radide.emu8086.assembler import assemble
    from radide.emu8086.machine import Machine
    path = src / "main.asm"
    prog = assemble(path.read_text(encoding="utf-8"), str(path))
    res.step("build", prog.ok, f"{len(prog.listing)} listing lines" if prog.ok else str(prog.errors[:3]))
    if not prog.ok:
        return
    outs = {}
    for keys in ("xd", "a"):
        m = Machine()
        m.record_history = False
        m.load(prog)
        m.feed_keys(keys)
        info = m.run(5_000_000)
        outs[keys] = (info.reason, m.output)
    desc = outs["xd"][1]
    asc = outs["a"][1]
    ok = outs["xd"][0] == "exit" and "Please press A or D" in desc and "120 89 34 15 7 0 -5 -42" in desc and \
        "-42 -5 0 7 15 34 89 120" in asc and "Sorted - bye!" in asc
    res.step("run", ok, "8086 emulator: descending + ascending sorts, invalid key rejected")
    res.step("publish", "n/a", "runs inside the IDE's 8086 emulator (no Windows exe)")


# ============================================================================ DOS
def _dos_build(src: Path, res):
    from radide.model import Project
    from radide.retro.dos import build as B
    d = exlib.temp_copy(src, "run")
    p = Project.load(d)
    log = []
    ok = B.Builder(d, p, log=log.append).build()
    s = B.settings_for(p)
    out = d / B.output_name(s)
    res.step("build", ok and out.is_file(), (log[-1] if log else "") + (f" ({out.stat().st_size} bytes)" if ok else ""))
    return (d, s) if ok else (None, s)


def _dos_capture(d: Path, s: dict, keys: str, timeout=30) -> dict:
    from radide.retro.dos import build as B
    from radide.retro.dos import dosbox
    run = dosbox.DosRun(mounts=[("C", d)], path=["Z:\\BIN", "Z:\\DOS"])
    cmd = ("CALL " + s["main"]) if s["kind"] == "batch" else B.output_name(s)
    r = dosbox.capture_text(run, d, cmd, keys=keys, timeout=timeout, log=lambda *_: None)
    r["text"] = r["stdout"] + "\n" + r["screen"]
    return r


def _is_mz_or_com(path: Path) -> bool:
    data = path.read_bytes()[:2]
    return data == b"MZ" or path.suffix.upper() == ".COM"


def dos_test(runs: list[tuple[str, list[str]]], graphics_keys: str = "", after=None):
    """runs: [(RADKEYS keys, [texts that must appear])]; each run is a separate DOSBox-X session (state such as
    data files carries over between them)."""
    def test(src: Path, res, opts):
        _open_check(src, res, forms=False)
        from radide.retro.dos import toolchain as T
        if not T.dosbox_exe():
            res.step("build", "skipped", "DOSBox-X is not installed (Tools > Retro > Emulators)")
            return
        d, s = _dos_build(src, res)
        if d is None:
            return
        notes, ok = [], True
        if s["kind"] != "batch":
            from radide.retro.dos import build as B
            is_dos = _is_mz_or_com(d / B.output_name(s))
            ok &= is_dos
            notes.append(f"{B.output_name(s)} is a DOS {'MZ .EXE' if s.get('output') != 'com' else '.COM'}: {is_dos}")
        for keys, want in runs:
            r = _dos_capture(d, s, keys)
            miss = [w for w in want if w.lower() not in r["text"].lower()]
            ok &= not miss and not r["timed_out"]
            notes.append(f"keys {keys!r}: " + ("ok" if not miss and not r["timed_out"] else
                                                f"missing {miss} timed_out={r['timed_out']}"))
        if graphics_keys:
            from radide.retro.dos import helpers
            r = _dos_capture(d, s, graphics_keys)
            stats = helpers.mode13_stats(r["graphics"]) if r["graphics"] else {}
            g_ok = bool(stats) and stats.get("nonzero", 0) > 3000 and stats.get("colours", 0) >= 8
            ok &= g_ok
            notes.append(f"mode 13h frame {stats.get('colours')} colours, {stats.get('nonzero')} pixels set")
        if after is not None:
            a_ok, a_note = after(d)
            ok &= a_ok
            notes.append(a_note)
        res.step("run", ok, "; ".join(notes))
        res.step("publish", "n/a", "a DOS program: the .EXE/.COM itself is the deliverable (runs in DOSBox-X)")
    return test


def batch_notes(d: Path):
    t = (d / "NOTES.TXT").read_text(encoding="cp437", errors="replace") if (d / "NOTES.TXT").exists() else ""
    n = t.count("Remember to back up")
    return n == 2, f"NOTES.TXT has {n} added notes"


def tui_test(src: Path, res, opts):
    _open_check(src, res, forms=False)
    from radide.retro.design.textmode import project as tp
    from radide.retro.design.textmode.model import load_project_screens
    from radide.retro.design.textmode.sim import alt
    screens = load_project_screens(src)
    names = [c.name for c in screens[0].controls] if screens else []
    if res["open"] == "ok":
        res["notes"].append(f"open: {len(names)} text-mode controls in Main.tform")
    d = exlib.temp_copy(src, "run")
    log = []
    ok, exe = tp.build(d, log=log.append)
    res.step("build", bool(ok and exe and exe.is_file()), log[-1] if log else "")
    if not ok:
        return
    first = tp.capture(d, exe.name, log=lambda *_: None)
    empty = tp.capture(d, exe.name, [alt("o")], log=lambda *_: None)
    order = tp.capture(d, exe.name, [ord(c) for c in "Ali"] + [alt("r"), alt("i"), alt("o")], log=lambda *_: None)
    t0 = first.plain_text() if first else ""
    t1 = empty.plain_text() if empty else ""
    t2 = order.plain_text() if order else ""
    good = "RAD Coffee" in t0 and "Please type the customer name" in t1 and "Ali L +milk = 23" in t2 and \
        "Total: 23" in t2 and "1 / 10" in t2
    res.step("run", good, "screen drawn; empty name -> message box; Ali Large + milk ordered -> list, total 23, "
                          "progress 1/10" if good else f"screens: {t1[-300:]!r} | {t2[-300:]!r}")
    res.step("publish", "n/a", "a DOS program (TUIORDER.EXE) that runs in DOSBox-X")


# ============================================================================ retro
def _retro_build(src: Path, res):
    from radide.retro.dev.build import Builder
    d = exlib.temp_copy(src, "run")
    log = []
    b = Builder(d, log=log.append)
    ok = b.build()
    res.step("build", ok and b.out_path.is_file(),
             f"{b.out_path.name} {b.out_path.stat().st_size} bytes" if ok else "; ".join(log[-4:]))
    return (d, b) if ok else (None, b)


def _png_rows(path: Path, y0: int, y1: int, x0: int = 0, x1: int | None = None):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    x1 = im.width if x1 is None else x1
    return [im.getpixel((x, y)) for y in range(y0, y1) for x in range(x0, x1)], im


def _mean_x_of(path: Path, y0: int, y1: int, colour_test) -> float:
    from PIL import Image
    im = Image.open(path).convert("RGB")
    xs = [x for y in range(y0, y1) for x in range(im.width) if colour_test(im.getpixel((x, y)))]
    return sum(xs) / len(xs) if xs else -1


def nes_test(src: Path, res, opts):
    _open_check(src, res, forms=False)
    d, b = _retro_build(src, res)
    if d is None:
        return
    data = b.out_path.read_bytes()
    header = data[:4] == b"NES\x1a" and len(data) == 16 + 2 * 16384 + 8192
    from radide.retro.emu import manager
    if not manager.find("mesen"):
        res.step("run", "skipped", "Mesen is not installed (Tools > Retro > Emulators)")
        return
    from radide.retro.emu.mesenshot import mesen_screenshots
    out = exlib.SCRATCH / "shots"
    idle = mesen_screenshots(b.out_path, [200], out, prefix="nes_idle")[0]
    right = mesen_screenshots(b.out_path, [200], out, inputs=[(61, 199, {"right": True})], prefix="nes_right")[0]
    left = mesen_screenshots(b.out_path, [200], out, inputs=[(61, 199, {"left": True, "b": True})],
                             prefix="nes_left")[0]
    def basket(p):                      # orange / brown basket pixels in the rows of the basket
        return lambda c: c[0] > 150 and 60 < c[1] < 200 and c[2] < 90
    xi, xr, xl = (_mean_x_of(p, 196, 207, basket(p)) for p in (idle, right, left))
    ok = header and xi > 0 and xr > xi + 40 and 0 < xl < xi - 40
    res.step("run", ok, f"iNES header {header}; Mesen headless frames: basket x idle {xi:.0f}, Right {xr:.0f}, "
                        f"Left+B {xl:.0f}")
    res.step("publish", "n/a", "the .nes ROM is the deliverable (runs in any NES emulator)")


def gb_test(src: Path, res, opts):
    _open_check(src, res, forms=False)
    d, b = _retro_build(src, res)
    if d is None:
        return
    data = b.out_path.read_bytes()
    from radide.retro.cpu.romfmt import gb_global_checksum, gb_header_checksum
    header = data[0x104:0x108] == bytes([0xCE, 0xED, 0x66, 0x66]) and data[0x14D] == gb_header_checksum(data) \
        and int.from_bytes(data[0x14E:0x150], "big") == gb_global_checksum(data)
    from radide.retro.emu import manager
    if not manager.find("mesen"):
        res.step("run", "skipped", "Mesen is not installed (Tools > Retro > Emulators)")
        return
    from radide.retro.emu.mesenshot import mesen_screenshots
    out = exlib.SCRATCH / "shots"
    ins = [(60, 100, {"right": True}), (110, 112, {"a": True}), (120, 160, {"down": True}), (170, 172, {"a": True})]
    idle = mesen_screenshots(b.out_path, [200], out, prefix="gb_idle")[0]
    play = mesen_screenshots(b.out_path, [200], out, inputs=ins, prefix="gb_play")[0]
    di, _ = _png_rows(idle, 0, 8, 64, 88)          # the two count digits ("FLOWERS 00" / "FLOWERS 02")
    dp, _ = _png_rows(play, 0, 8, 64, 88)
    gi, _ = _png_rows(idle, 16, 144)
    gp, _ = _png_rows(play, 16, 144)
    changed = sum(1 for a, c in zip(gi, gp) if a != c)
    ok = header and di != dp and changed > 60
    res.step("run", ok, f"header logo + checksums {header}; Mesen headless: count digits changed {di != dp}, "
                        f"{changed} garden pixels differ (walked + planted 2 flowers)")
    res.step("publish", "n/a", "the .gb ROM is the deliverable")


def c64_test(src: Path, res, opts):
    _open_check(src, res, forms=False)
    d, b = _retro_build(src, res)
    if d is None:
        return
    data = b.out_path.read_bytes()
    load_ok = data[:2] == b"\x01\x08" and b"2061" in data[:16]
    labels = {}
    for ln in (d / "_build" / "labels.txt").read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"al ([0-9A-Fa-f]+) \.(\w+)", ln)
        if m:
            labels[m.group(2)] = int(m.group(1), 16)
    from radide.retro.emu import manager, run_rom
    if not manager.find("vice"):
        res.step("run", "skipped", "VICE is not installed (Tools > Retro > Emulators)")
        return
    from radide.retro.emu.vice_monitor import ViceMonitor
    proc = run_rom(b.out_path, "c64", emulator="vice", minimized=True, quiet=True, warp=True)
    note, ok = "", False
    try:
        win = exlib.wait(lambda: exlib.windows_of(exlib.process_tree(proc.pid)), 30)
        mon = ViceMonitor(proc.monitor_port).connect(retry_for=30)

        def peek(name):
            for _ in range(10):
                try:
                    v = mon.memory_get(labels[name], labels[name])[0]
                    mon.exit_monitor()
                    return v
                except (TimeoutError, OSError):
                    time.sleep(1)
            return -1
        f0 = peek("frame")
        running = exlib.wait(lambda: peek("frame") != f0, 30, 0.5)
        x0, m0 = peek("spritex"), peek("moves")
        for _ in range(5):
            try:
                mon.keyboard_feed("DDDDDDDD")
                mon.exit_monitor()
                break
            except (TimeoutError, OSError):
                time.sleep(1)
        exlib.wait(lambda: peek("moves") >= m0 + 8, 20, 0.5)
        x1, m1 = peek("spritex"), peek("moves")
        ok = load_ok and bool(win) and bool(running) and x1 > x0 and m1 > m0
        note = (f"PRG load address $0801 {load_ok}; VICE window {win[0][1] if win else None!r}; frame counter "
                f"running {bool(running)}; monitor keyboard feed 'D' x8: balloon x {x0} -> {x1}, moves {m0} -> {m1}")
        mon.close()
    finally:
        proc.stop()
    res.step("run", ok, note)
    res.step("publish", "n/a", "the .prg is the deliverable (runs in VICE or on a real C64)")


def atari_test(src: Path, res, opts):
    _open_check(src, res, forms=False)
    d, b = _retro_build(src, res)
    if d is None:
        return
    data = b.out_path.read_bytes()
    vec_ok = len(data) == 4096 and int.from_bytes(data[-4:-2], "little") == 0xF000
    from radide.retro.emu import manager, run_rom
    if not manager.find("stella"):
        res.step("run", "skipped", "Stella is not installed (Tools > Retro > Emulators)")
        return
    proc = run_rom(b.out_path, "atari2600", emulator="stella", minimized=True, quiet=True)
    try:
        win = exlib.wait(lambda: exlib.windows_of(exlib.process_tree(proc.pid)), 30, 0.25)
        time.sleep(2)
        alive = proc.alive()
    finally:
        proc.stop()
    res.step("run", vec_ok and bool(win) and alive,
             f"4 KB ROM, reset vector $F000 {vec_ok}; Stella window {win[0][1] if win else None!r}, still running "
             f"after 2 s {alive} (Stella has no headless hook in the IDE: window check only)")
    res.step("publish", "n/a", "the .bin ROM is the deliverable")


def zx_test(src: Path, res, opts):
    _open_check(src, res, forms=False)
    d, b = _retro_build(src, res)
    if d is None:
        return
    from radide.retro.cpu import romfmt
    img = romfmt.load(b.out_path, "zx")
    data = b.out_path.read_bytes()
    ok = data[:2] == b"\x13\x00" and data[2] == 0 and img.system == "zx" and len(data) > 300
    emu = os.environ.get("RADIDE_ZX_EMULATOR", "")
    res.step("run", "skipped" if not emu else ok,
             f".tap: BASIC loader + CODE block {ok} ({len(data)} bytes). No ZX Spectrum emulator in the IDE's "
             f"emulator catalog; set RADIDE_ZX_EMULATOR (Fuse / ZEsarUX) to run it")
    if not ok:
        res["run"] = "FAIL"
    res.step("publish", "n/a", "the .tap is the deliverable")


# ============================================================================ the list
EXAMPLES = {
    "Assembly/NasmCalculator": {"lang": "asm-nasm", "test": asm_form_test(nasm_calculator)},
    "Assembly/NasmBaseConverter": {"lang": "asm-nasm", "test": asm_console_test(
        "10\n255\n64\nq\n", ["binary  : 1010", "hex     : 0xFF", "power of two: yes", "Converted 3 number(s)"])},
    "Assembly/FasmTemperature": {"lang": "asm-fasm", "test": asm_form_test(fasm_temperature)},
    "Assembly/MasmTextTools": {"lang": "asm-masm", "test": asm_console_test(
        "Hello RAD IDE from MASM\n", ["Reversed  : MSAM morf EDI DAR olleH", "Uppercase : HELLO RAD IDE FROM MASM",
                                      "Vowels    : 7", "Words     : 5", "Sorted    : -18 -7 0 8 15 23 31 42 64 99"])},
    "Assembly/GasGuessNumber": {"lang": "asm-gas", "test": asm_form_test(gas_guess)},
    "Assembly/Emu8086BubbleSort": {"lang": "emu8086", "test": emu8086_test},
    "DOS/QBasicArtMenu": {"lang": "dos-qbasic", "test": dos_test([
        ("1z`", ["7 x 8 = 56", "Goodbye"]), ("397~z`", ["97 is a prime number", "Binary: 1100001"]),
        ("2z`", ["Goodbye"]), ("4z`", ["this month has"])])},
    "DOS/PascalPhoneBook": {"lang": "dos-pascal", "test": dos_test([
        ("aZed~555~Giza~q", ["Saved: Zed (1 contacts)"]), ("aAli~777~Suez~q", ["Saved: Ali (2 contacts)"]),
        ("sq", ["1. Ali", "2. Zed"]), ("fal~q", ["1 found."])])},
    "DOS/CPixelPainter": {"lang": "dos-c", "test": dos_test(
        [("^R^R^R^D^D2rb^L^U`", ["7 pen moves, 2 boxes"])], graphics_keys="^R^R^D3b^L^L`")},
    "DOS/AsmSysInfo": {"lang": "dos-asm", "test": dos_test([
        ("12x5hi_dos~q", ["DOS version:", "Today is", "Unknown choice", "You said: HI DOS!", "Goodbye"]),
        ("34q", ["The time is", "Conventional memory: 640 KB"])])},
    "DOS/BatchToolbox": {"lang": "dos-batch", "test": dos_test(
        [("1136", ["counting 5", "Goodbye from BatchToolbox"]), ("26", ["Remember to back up"])],
        after=batch_notes)},
    "DOS/TuiOrderForm": {"lang": "dos-tuiforms", "test": tui_test},
    "Retro/Atari2600Runner": {"lang": "retro-atari2600", "test": atari_test},
    "Retro/NesStarCatcher": {"lang": "retro-nes", "test": nes_test},
    "Retro/GameBoyGarden": {"lang": "retro-gameboy", "test": gb_test},
    "Retro/C64RasterScroller": {"lang": "retro-c64", "test": c64_test},
    "Retro/ZxBorderArt": {"lang": "retro-zx", "test": zx_test},
}
